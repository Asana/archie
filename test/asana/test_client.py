from __future__ import annotations

from datetime import datetime
from test import fixtures as f
from typing import Any
from unittest import TestCase
from unittest.mock import Mock, create_autospec, patch

from asana import resources  # type: ignore

from archie.asana.client import Client
from archie.asana.models import Task


class ListMatcher:
    def __eq__(self, other: Any) -> bool:
        return isinstance(other, list)


list_matcher = ListMatcher()


class TestCaseWithClient(TestCase):
    @patch("archie.asana.client.AsanaClient")
    def setUp(self, asana_client_mock: Mock) -> None:
        self.inner_mock = asana_client_mock.access_token.return_value = Mock()
        self.inner_mock.projects = create_autospec(resources.projects.Projects)
        self.inner_mock.users = create_autospec(resources.users.Users)
        self.inner_mock.tasks = create_autospec(resources.tasks.Tasks)
        self.inner_mock.sections = create_autospec(resources.sections.Sections)
        self.inner_mock.workspaces = create_autospec(resources.workspaces.Workspaces)
        self.client = Client(access_token="token")


class TestClient(TestCaseWithClient):
    def test_project_by_gid(self) -> None:
        project = f.project()
        self.inner_mock.projects.find_by_id.return_value = project.to_dict()
        returned_project = self.client.project_by_gid("1")
        self.assertEqual(project, returned_project)
        self.inner_mock.projects.find_by_id.assert_called_once_with(
            "1", fields=list_matcher
        )

    def test_task_by_gid(self) -> None:
        task = f.task()
        self.inner_mock.tasks.find_by_id.return_value = task.to_dict()
        returned_task = self.client.task_by_gid("1")
        self.assertEqual(task, returned_task)
        self.inner_mock.tasks.find_by_id.assert_called_once_with(
            "1", fields=list_matcher
        )

    def test_me(self) -> None:
        user = f.user()
        self.inner_mock.users.me.return_value = user.to_dict()
        returned_user = self.client.me()
        self.assertEqual(user, returned_user)
        self.inner_mock.users.me.assert_called_once_with(fields=list_matcher)

    def test_stories_by_task(self) -> None:
        task = f.task(gid="1")
        stories = [f.story(gid="2"), f.story(gid="3")]
        self.inner_mock.tasks.stories.return_value = [s.to_dict() for s in stories]
        returned_stories = self.client.stories_by_task(task)
        self.assertListEqual(returned_stories, stories)
        self.inner_mock.tasks.stories.assert_called_once_with(
            task.gid, fields=list_matcher
        )

    def test_sections_by_project(self) -> None:
        project = f.project(gid="1")
        sections = [f.section(gid="2"), f.section(gid="3")]
        self.inner_mock.sections.find_by_project.return_value = [
            s.to_dict() for s in sections
        ]
        returned_sections = self.client.sections_by_project(project)
        self.assertListEqual(returned_sections, sections)
        self.inner_mock.sections.find_by_project.assert_called_once_with(
            project.gid, fields=list_matcher
        )

    def test_typeahead(self) -> None:
        workspace = f.workspace()
        tasks = [f.task(gid="1"), f.task(gid="2")]
        self.inner_mock.workspaces.typeahead.return_value = [t.to_dict() for t in tasks]
        result = self.client.typeahead(workspace, Task, "some text", count=15)

        self.inner_mock.workspaces.typeahead.assert_called_once_with(
            workspace.gid,
            fields=list_matcher,
            params={"resource_type": "task", "query": "some text", "count": 15},
        )
        self.assertListEqual(result, tasks)


# The following tests share the same data and so are grouped into separate classes


class TestTasksByProject(TestCaseWithClient):
    project = f.project()
    tasks = [f.task(gid="1"), f.task(gid="2")]

    def setUp(self) -> None:
        super().setUp()
        self.inner_mock.tasks.find_by_project.return_value = [
            t.to_dict() for t in self.tasks
        ]

    def test_tasks_by_project(self) -> None:
        returned_tasks = self.client.tasks_by_project(self.project)
        self.assertListEqual(returned_tasks, self.tasks)
        self.inner_mock.tasks.find_by_project.assert_called_once_with(
            self.project.gid, params={"completed_since": "now"}, fields=list_matcher
        )

    def test_modified_tasks_by_project(self) -> None:
        returned_tasks = self.client.tasks_by_project(
            self.project, modified_since=datetime(2019, 1, 1, 12, 0, 0)
        )
        self.assertListEqual(returned_tasks, self.tasks)
        self.inner_mock.tasks.find_by_project.assert_called_once_with(
            self.project.gid,
            params={"completed_since": "now", "modified_since": "2019-01-01T12:00:00"},
            fields=list_matcher,
        )

    def test_all_tasks_by_project(self) -> None:
        returned_tasks = self.client.tasks_by_project(
            self.project, only_incomplete=False
        )
        self.assertListEqual(returned_tasks, self.tasks)
        self.inner_mock.tasks.find_by_project.assert_called_once_with(
            self.project.gid, params={}, fields=list_matcher
        )


class TestTasksBySection(TestCaseWithClient):
    project = f.project()
    section = f.section(gid="1", project=project)
    other_section = f.section(gid="2", project=project)
    tasks = [
        f.task(
            gid="3", memberships=[f.task_membership(project=project, section=section)]
        ),
        f.task(
            gid="4", memberships=[f.task_membership(project=project, section=section)]
        ),
        f.task(
            gid="5",
            memberships=[f.task_membership(project=project, section=other_section)],
        ),
    ]

    def setUp(self) -> None:
        super().setUp()
        self.inner_mock.tasks.find_by_project.return_value = [
            t.to_dict() for t in self.tasks
        ]
        self.inner_mock.tasks.find_by_section.return_value = [
            t.to_dict() for t in self.tasks[:-1]
        ]

    def test_tasks_by_section(self) -> None:
        returned_tasks = self.client.tasks_by_section(self.section)
        self.assertListEqual(returned_tasks, self.tasks[:-1])
        self.inner_mock.tasks.find_by_project.assert_called_once_with(
            self.project.gid, params={"completed_since": "now"}, fields=list_matcher
        )

    def test_all_tasks_by_section(self) -> None:
        returned_tasks = self.client.tasks_by_section(
            self.section, only_incomplete=False
        )
        self.assertListEqual(returned_tasks, self.tasks[:-1])
        self.inner_mock.tasks.find_by_section.assert_called_once_with(
            self.section.gid, fields=list_matcher
        )


class TestMutations(TestCaseWithClient):
    task = f.task()

    def test_reorder(self) -> None:
        project = f.project()
        task = f.task(gid="1")
        reference = f.task(gid="2")
        self.inner_mock.tasks.add_project.return_value = None
        self.client.reorder_in_project(task, project, reference, "direction")
        self.inner_mock.tasks.add_project.assert_called_once_with(
            task.gid, {"project": project.gid, "insert_direction": reference.gid}
        )

    def test_add_to_project(self) -> None:
        project = f.project()
        task = f.task()
        self.inner_mock.tasks.add_project.return_value = None
        self.client.add_to_project(task, project)
        self.inner_mock.tasks.add_project.assert_called_once_with(
            task.gid, {"project": project.gid}
        )

    def test_add_to_section(self) -> None:
        section = f.section()
        task = f.task()
        self.inner_mock.tasks.add_project.return_value = None
        self.client.add_to_section(task, section)
        self.inner_mock.tasks.add_project.assert_called_once_with(
            task.gid, {"project": section.project.gid, "section": section.gid}
        )

    def test_add_comment(self) -> None:
        self.inner_mock.tasks.add_comment.return_value = None
        self.client.add_comment(self.task, "Comment text")
        self.inner_mock.tasks.add_comment.assert_called_once_with(
            self.task.gid, {"text": "Comment text"}
        )

    def test_add_follower(self) -> None:
        self.inner_mock.tasks.add_followers.return_value = None
        self.client.add_follower(self.task, "user@domain.com")
        self.inner_mock.tasks.add_followers.assert_called_once_with(
            self.task.gid, {"followers": ["user@domain.com"]}
        )

    def test_set_assignee(self) -> None:
        self.inner_mock.update.return_value = None
        self.client.set_assignee(self.task, "user@domain.com")
        self.inner_mock.tasks.update.assert_called_once_with(
            self.task.gid, {"assignee": "user@domain.com"}
        )

    def test_set_enum_custom_field(self) -> None:
        custom_field = f.custom_field()
        enum_option = f.enum_option()
        self.inner_mock.tasks.update.return_value = None
        self.client.set_enum_custom_field(self.task, custom_field, enum_option)
        self.inner_mock.tasks.update.assert_called_once_with(
            self.task.gid, {"custom_fields": {custom_field.gid: enum_option.gid}}
        )

    def test_set_external(self) -> None:
        external = f.external("1", {"a": "b"})
        self.inner_mock.tasks.update.return_value = None
        self.client.set_external(self.task, external)
        self.inner_mock.tasks.update.assert_called_once_with(
            self.task.gid, {"external": {"gid": "1", "data": '{"a": "b"}'}}
        )
