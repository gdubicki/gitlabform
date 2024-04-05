import pytest


from tests.acceptance import run_gitlabform


@pytest.fixture(scope="class")
def schedules(project):
    another_branch = "scheduled/new-feature"
    project.branches.create({"branch": another_branch, "ref": "main"})

    # fmt: off
    schedules = [
        ("Existing schedule", "main", "0 * * * *", True),
        ("Existing schedule with vars", "main", "30 * * * *", False),
        ("Existing schedule to replace", "main", "30 1 * * *", False),
        ("Existing schedule to replace", another_branch, "30 2 * * *", False),
    ]
    # fmt: on

    gitlab_schedules = []

    for schedule in schedules:
        gitlab_schedule = project.pipelineschedules.create(
            {
                "description": schedule[0],
                "ref": schedule[1],
                "cron": schedule[2],
                "active": schedule[3],
            }
        )
        if schedule[0] == "Existing schedule with vars":
            gitlab_schedule.variables.create(
                {"key": "existing_var", "value": "existing_value"}
            )
            gitlab_schedule.variables.create(
                {"key": "second_var", "value": "second_val"}
            )

        gitlab_schedules.append(gitlab_schedule)

    redundant_schedule = project.pipelineschedules.create(
        {
            "description": "Redundant schedule",
            "ref": "main",
            "cron": "0 * * * *",
        }
    )
    redundant_schedule.variables.create({"key": "test_variable", "value": "test_value"})

    schedules.append(redundant_schedule)

    return schedules  # provide fixture value


class TestSchedules:
    def test__add_new_schedule(self, project, schedules):
        add_schedule = f"""
        projects_and_groups:
          {project.path_with_namespace}:
            schedules:
              "New schedule":
                ref: main
                cron: "0 * * * *"
                cron_timezone: "London"
                active: true
        """

        run_gitlabform(add_schedule, project)

        schedule = self.__find_pipeline_schedule_by_description_and_get_first(
            project, "New schedule"
        )
        assert schedule is not None
        assert schedule.description == "New schedule"
        assert schedule.ref == "main"
        assert schedule.cron == "0 * * * *"
        assert schedule.cron_timezone == "London"
        assert schedule.active is True

    def test__add_new_schedule_with_mandatory_fields_only(self, project, schedules):
        add_schedule_mandatory_fields_only = f"""
        projects_and_groups:
          {project.path_with_namespace}:
            schedules:
              "New schedule with mandatory fields":
                ref: main
                cron: "30 1 * * *"
        """

        run_gitlabform(add_schedule_mandatory_fields_only, project)

        schedule = self.__find_pipeline_schedule_by_description_and_get_first(
            project, "New schedule with mandatory fields"
        )
        assert schedule is not None
        assert schedule.description == "New schedule with mandatory fields"
        assert schedule.ref == "main"
        assert schedule.cron == "30 1 * * *"
        assert schedule.cron_timezone == "UTC"
        assert schedule.active is True

    def test__set_schedule_variables(self, project, schedules):
        add_schedule_with_variables = f"""
        projects_and_groups:
          {project.path_with_namespace}:
            schedules:
              "New schedule with variables":
                ref: main
                cron: "30 1 * * *"
                variables:
                    var1:
                        value: value123
                    var2:
                        value: value987
                        variable_type: file
        """

        run_gitlabform(add_schedule_with_variables, project)

        schedule = self.__find_pipeline_schedule_by_description_and_get_first(
            project, "New schedule with variables"
        )
        assert schedule is not None
        assert schedule.description == "New schedule with variables"
        assert schedule.ref == "main"
        assert schedule.cron == "30 1 * * *"
        assert schedule.cron_timezone == "UTC"
        assert schedule.active is True

        variables = schedule.attributes["variables"]
        assert variables is not None
        assert len(variables) == 2

        assert variables[0]["variable_type"] == "env_var"
        assert variables[0]["key"] == "var1"
        assert variables[0]["value"] == "value123"

        assert variables[1]["variable_type"] == "file"
        assert variables[1]["key"] == "var2"
        assert variables[1]["value"] == "value987"

    def test__update_existing_schedule(self, project, schedules):
        # Schedules fixture creates some schedules onto project
        existing_schedule = self.__find_pipeline_schedule_by_description_and_get_first(
            project, "Existing schedule"
        )

        edit_schedule = f"""
        projects_and_groups:
          {project.path_with_namespace}:
            schedules:
              "Existing schedule":
                ref: scheduled/new-feature
                cron: "0 */4 * * *"
                cron_timezone: "Stockholm"
                active: false
        """

        run_gitlabform(edit_schedule, project)

        schedule = self.__find_pipeline_schedule_by_description_and_get_first(
            project, "Existing schedule"
        )
        assert schedule is not None
        schedules = project.pipelineschedules.list()
        # Only one schedule specified in the new config, so any other existing schedules should be deleted
        assert len(schedules) == 1

        # Verify it updated the schedule rather than creating/deleting
        assert schedule.id == existing_schedule.id
        assert schedule.description == existing_schedule.description

        # Verify updates to schedule
        assert schedule.ref == "scheduled/new-feature"
        assert schedule.cron == "0 */4 * * *"
        assert schedule.cron_timezone == "Stockholm"
        assert schedule.active is False

    def test__update_existing_schedule_with_variables(self, project, schedules):
        # Schedules fixture creates some schedules onto project
        # this schedule has 2 existing variables
        existing_schedule = self.__find_pipeline_schedule_by_description_and_get_first(
            project, "Existing schedule with vars"
        )

        edit_schedule = f"""
        projects_and_groups:
          {project.path_with_namespace}:
            schedules:
              "Existing schedule with vars":
                ref: scheduled/new-feature
                cron: "0 */4 * * *"
                cron_timezone: "Stockholm"
                active: false
                variables:
                    existing_var:
                        value: new_value
        """

        run_gitlabform(edit_schedule, project)

        schedule = self.__find_pipeline_schedule_by_description_and_get_first(
            project, "Existing schedule with vars"
        )
        assert schedule is not None
        schedules = project.pipelineschedules.list()
        # Only one schedule specified in the new config, so any other existing schedules should be deleted
        assert len(schedules) == 1

        # Verify it updated the schedule rather than creating/deleting
        assert schedule.id == existing_schedule.id
        assert schedule.description == existing_schedule.description

        # Verify updates to schedule
        assert len(schedule.variables.list()) == 1
        variable = schedule.variables.list()[0]
        assert variable.key == "existing_var"
        assert variable.value == "new_value"

        assert schedule.ref == "scheduled/new-feature"
        assert schedule.cron == "0 */4 * * *"
        assert schedule.cron_timezone == "Stockholm"
        assert schedule.active is False

    def test__replace_existing_schedules(self, project, schedules):
        replace_schedules = f"""
        projects_and_groups:
          {project.path_with_namespace}:
            schedules:
              "Existing schedule to replace":
                ref: scheduled/new-feature
                cron: "0 */3 * * *"
                cron_timezone: "London"
                active: true
        """

        run_gitlabform(replace_schedules, project)

        existing_schedules = self.__find_pipeline_schedules_by_description(
            project, "Existing schedule to replace"
        )
        assert existing_schedules is not None
        assert len(existing_schedules) == 1

        schedule = existing_schedules[0]
        assert schedule.description == "Existing schedule to replace"
        assert schedule.ref == "scheduled/new-feature"
        assert schedule.cron == "0 */3 * * *"
        assert schedule.cron_timezone == "London"
        assert schedule.active is True

    def test__delete_schedule(self, project, schedules):
        delete_schedule = f"""
        projects_and_groups:
          {project.path_with_namespace}:
            schedules:
              "Redundant schedule":
                delete: True
        """

        run_gitlabform(delete_schedule, project)

        schedule = self.__find_pipeline_schedule_by_description_and_get_first(
            project, "Redundant schedule"
        )
        assert schedule is None

    def test__schedule_enforce_new_schedule(self, project, schedules):
        new_schedule = f"""
        projects_and_groups:
          {project.path_with_namespace}:
            schedules:
              enforce: true
              "New schedule to test enforce config":
                ref: main
                cron: "30 1 * * *"
        """

        schedules_before = project.pipelineschedules.list()

        run_gitlabform(new_schedule, project)

        schedules_after = project.pipelineschedules.list()

        schedule = self.__find_pipeline_schedule_by_description_and_get_first(
            project, "New schedule to test enforce config"
        )
        assert len(schedules_before) == 6
        assert len(schedules_after) == 1
        assert schedule is not None
        assert schedule.description == "New schedule to test enforce config"
        assert schedule.ref == "main"
        assert schedule.cron == "30 1 * * *"
        assert schedule.cron_timezone == "UTC"
        assert schedule.active is True

    def test__schedule_enforce_new_and_existing_schedule(self, project, schedules):
        new_schedule = f"""
        projects_and_groups:
          {project.path_with_namespace}:
            schedules:
              enforce: true
              "New schedule to test enforce config":
                ref: main
                cron: "30 1 * * *"
              "New schedule with variables":
                ref: main
                cron: "30 1 * * *"
                variables:
                    var1:
                        value: value123
                    var2:
                        value: value987
                        variable_type: file
        """

        schedules_before = project.pipelineschedules.list()

        run_gitlabform(new_schedule, project)

        schedules_after = project.pipelineschedules.list()

        schedule1 = self.__find_pipeline_schedule_by_description_and_get_first(
            project, "New schedule to test enforce config"
        )
        schedule2 = self.__find_pipeline_schedule_by_description_and_get_first(
            project, "New schedule with variables"
        )
        assert len(schedules_before) == 1
        assert len(schedules_after) == 2

        assert schedule1 is not None
        assert schedule1.description == "New schedule to test enforce config"
        assert schedule1.ref == "main"
        assert schedule1.cron == "30 1 * * *"
        assert schedule1.cron_timezone == "UTC"
        assert schedule1.active is True

        assert schedule2 is not None
        assert schedule2.description == "New schedule with variables"
        assert schedule2.ref == "main"
        assert schedule2.cron == "30 1 * * *"
        assert schedule2.cron_timezone == "UTC"
        assert schedule2.active is True

        variables = schedule2.attributes["variables"]
        assert variables is not None
        assert len(variables) == 2
        assert variables[0]["variable_type"] == "env_var"
        assert variables[0]["key"] == "var1"
        assert variables[0]["value"] == "value123"

        assert variables[1]["variable_type"] == "file"
        assert variables[1]["key"] == "var2"
        assert variables[1]["value"] == "value987"

    @classmethod
    def __find_pipeline_schedule_by_description_and_get_first(
        cls, project, description
    ):
        try:
            return cls.__find_pipeline_schedules_by_description(project, description)[0]
        except IndexError:
            return None

    @staticmethod
    def __find_pipeline_schedules_by_description(project, description):
        return [
            project.pipelineschedules.get(schedule.id)
            for schedule in project.pipelineschedules.list()
            if schedule.description == description
        ]
