from logging import debug
from typing import List

from gitlabform.gitlab import GitLab
from gitlab.v4.objects import Group
from gitlabform.processors.abstract_processor import AbstractProcessor


class GroupSAMLLinksProcessor(AbstractProcessor):

    def __init__(self, gitlab: GitLab):
        super().__init__("group_saml_links", gitlab)

    def _process_configuration(self, group_path: str, configuration: dict) -> None:
        """Process the SAML links configuration for a group."""

        configured_links = configuration.get("group_saml_links",{})
        enforce_links = configuration.get("group_saml_links|enforce", False)

        group: Group = self.gl.get_group_by_path_cached(group_path)        
        existing_links: List[dict] = self._fetch_saml_links(group)

        # Remove 'enforce' key from the config so that it's not treated as a "link"
        if enforce_links:
            configured_links.pop("enforce")
        
        for name, link_config in configured_links.items():
            if self._needs_update(link_config.asdict(), enforce_links):
                if name not in [l["saml_group_name"] for l in existing_links]:
                    group.saml_group_links.create(link_config)
        if enforce_links:
            self._delete_extra_links(group, existing_links, configured_links)

    def _fetch_saml_links(self, group: Group) -> List[dict]:
        """Fetch the existing SAML links for a group."""
        links = group.saml_group_links.list()
        return [link.attributes for link in links]

    def _delete_extra_links(self, group: Group, existing: List[dict], configured: dict)-> None:
        """Delete any SAML links that are not in the configuration."""
        known_names = [c['saml_group_name'] for c in configured.values() if c != 'enforce']        
        for link in existing:
            if link['saml_group_name'] not in known_names:
                debug(f"Deleting extra SAML link: {link['saml_group_name']}")
                group.saml_group_links.delete(link['id'])

