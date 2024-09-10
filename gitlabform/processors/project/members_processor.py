from logging import debug
from cli_ui import debug as verbose, warning
from cli_ui import fatal
from gitlab import GitlabGetError
from gitlab.v4.objects import Project

from gitlabform.constants import EXIT_INVALID_INPUT
from gitlabform.gitlab import GitLab
from gitlabform.processors.abstract_processor import AbstractProcessor


class MembersProcessor(AbstractProcessor):
    def __init__(self, gitlab: GitLab):
        super().__init__("members", gitlab)

    def _process_configuration(self, project_and_group: str, configuration: dict):
        keep_bots = configuration.get("members|keep_bots", False)

        enforce_members = configuration.get("members|enforce", False)

        groups = configuration.get("members|groups", {})

        users = configuration.get("members|users", {})

        if not groups and not users and not enforce_members:
            fatal(
                "Project members configuration section has to contain"
                " either 'users' or 'groups' non-empty keys"
                " (unless you want to enforce no direct members).",
                exit_code=EXIT_INVALID_INPUT,
            )

        self._process_groups(project_and_group, groups, enforce_members)
        self._process_users(project_and_group, users, enforce_members, keep_bots)

    def _process_groups(
        self, project_and_group: str, groups: dict, enforce_members: bool
    ):
        if groups:
            verbose("Processing groups as members...")

            current_groups = self.gitlab.get_groups_from_project(project_and_group)
            for group in groups:
                expires_at = (
                    groups[group]["expires_at"].strftime("%Y-%m-%d")
                    if "expires_at" in groups[group]
                    else None
                )
                access_level = (
                    groups[group]["group_access"]
                    if "group_access" in groups[group]
                    else None
                )

                # we only add the group if it doesn't have the correct settings
                common_group_name = group.lower()
                if (
                    common_group_name in current_groups
                    and expires_at == current_groups[common_group_name]["expires_at"]
                    and access_level
                    == current_groups[common_group_name]["group_access_level"]
                ):
                    debug(
                        "Ignoring group '%s' as it is already a member",
                        common_group_name,
                    )
                    debug(
                        "Current settings for '%s' are: %s"
                        % (common_group_name, current_groups[common_group_name])
                    )
                else:
                    debug("Setting group '%s' as a member", common_group_name)
                    access = access_level
                    expiry = expires_at

                    # we will remove group access first and then re-add them,
                    # to ensure that the groups have the expected access level
                    self.gitlab.unshare_with_group(project_and_group, common_group_name)
                    self.gitlab.share_with_group(
                        project_and_group, common_group_name, access, expiry
                    )

        if enforce_members:
            current_groups = self.gitlab.get_groups_from_project(project_and_group)

            groups_in_config = [group_name.lower() for group_name in groups.keys()]
            groups_in_gitlab = current_groups.keys()
            groups_not_in_config = set(groups_in_gitlab) - set(groups_in_config)

            for group_not_in_config in groups_not_in_config:
                debug(
                    f"Removing group '{group_not_in_config}' that is not configured to be a member."
                )
                self.gitlab.unshare_with_group(project_and_group, group_not_in_config)
        else:
            debug("Not enforcing group members.")

    def _process_users(
        self,
        project_and_group: str,
        users: dict,
        enforce_members: bool,
        keep_bots: bool,
    ):

        project: Project = self.gl.projects.get(project_and_group)

        project_members = project.members.list()
        current_members = dict()
        for member in project_members:
            current_members[member.username] = member

        if users:
            verbose("Processing users as members...")

            for user in users:

                try:
                    user_id = self.gl.get_user_by_username_cached(user).get_id()
                except GitlabGetError:
                    warning(f"Could not find user '{user}' in Gitlab, skipping...")
                    continue

                expires_at = (
                    users[user]["expires_at"].strftime("%Y-%m-%d")
                    if "expires_at" in users[user]
                    else None
                )
                access_level = (
                    users[user]["access_level"]
                    if "access_level" in users[user]
                    else None
                )
                member_role_id_or_name = (
                    users[user]["member_role"] if "member_role" in users[user] else None
                )
                if member_role_id_or_name:
                    # For self-managed member_roles are at an instance level, for SaaS on a Group level
                    if self.gl.is_gitlab_saas():
                        project = self.gl.get_project_by_path_cached(project_and_group)
                        group_id = project.namespace["id"]
                    else:
                        group_id = None

                    member_role_id = self.gl.get_member_role_id_cached(
                        member_role_id_or_name, group_id
                    )
                else:
                    member_role_id = None

                # we only add the user if it doesn't have the correct settings.
                # To make sure that the user hasn't been added in a different
                # case, we enforce that the username is always in lowercase for
                # checks.
                common_username = user.lower()

                if common_username in current_members:
                    current_member = current_members[common_username]
                    if hasattr(current_member, "member_role"):
                        member_role_id_before = current_member.member_role["id"]
                    else:
                        member_role_id_before = None
                    if (
                        expires_at == current_member.expires_at
                        and access_level == current_member.access_level
                        and member_role_id == member_role_id_before
                    ):
                        debug(
                            "Nothing to change for user '%s' - same config now as to set.",
                            common_username,
                        )
                        debug(
                            "Current settings for '%s' are: %s"
                            % (common_username, current_members[common_username])
                        )
                    else:
                        debug(
                            "Editing user '%s' membership to change their access level or expires at",
                            common_username,
                        )
                        update_data = {
                            "user_id": common_username,
                            "access_level": access_level,
                            "member_role_id": member_role_id_before,
                        }

                        if expires_at:
                            update_data["expires_at"] = expires_at

                        project.members.update(new_data=update_data)

                else:
                    debug(
                        "Adding user '%s' who previously was not a member.",
                        common_username,
                    )
                    create_data = {
                        "user_id": user_id,
                        "access_level": access_level,
                    }

                    if expires_at:
                        create_data["expires_at"] = expires_at

                    if member_role_id:
                        create_data["member_role_id"] = member_role_id

                    project.members.create(data=create_data)

        if enforce_members:

            # Enforce that all usernames are lowercase for comparisons.
            users_in_config = [username.lower() for username in users.keys()]
            users_in_gitlab = current_members.keys()
            users_not_in_config = set(users_in_gitlab) - set(users_in_config)
            for user_not_in_config in users_not_in_config:
                if (
                    keep_bots
                    and self.gitlab.get_user_by_name(user_not_in_config)["bot"]
                ):
                    debug(
                        f"Will not remove bot user '{user_not_in_config}' as the 'keep_bots' option is true."
                    )
                    continue

                debug(
                    f"Removing user '{user_not_in_config}' that is not configured to be a member."
                )
                cached_user_id = self.gl.get_user_by_username_cached(
                    user_not_in_config
                ).get_id()
                project.members.delete(id=cached_user_id)
        else:
            debug("Not enforcing user members.")
