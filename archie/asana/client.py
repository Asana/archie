from __future__ import annotations

import logging
from datetime import datetime
from multiprocessing import cpu_count
from typing import List, Optional, Type, TypeVar

from asana import Client as AsanaClient  # type: ignore
from requests.adapters import HTTPAdapter

from archie.__version__ import __version__
from archie.asana.models import (
    CustomField,
    EnumOption,
    External,
    Project,
    Section,
    Story,
    Task,
    User,
    Workspace,
    _Model,
)

_T = TypeVar("_T")
_M = TypeVar("_M", bound=_Model)

_logger = logging.getLogger(__name__)


# Here, we increase the maximum number of connections we save in the pool.
# Using the default value of 10 results in us discarding a large number of
# connections as we triage more than 10 tasks in parallel.
# The new value matches the default number of threads in a ThreadPoolExecutor.
_CONNECTION_POOL_SIZE = (cpu_count() or 1) * 5


class Client:
    """A client to access the Asana API.

    :param access_token: Credentials for the Asana API.
    """

    def __init__(self, access_token: str) -> None:
        self._client = AsanaClient.access_token(access_token)
        self._client.headers.update(
            {
                "Asana-Enable": "new_sections,string_ids",
                "User-Agent": f"asana-archie/{__version__}",
            }
        )
        self._client.session.mount(
            "https://", HTTPAdapter(pool_maxsize=_CONNECTION_POOL_SIZE)
        )

    def project_by_gid(self, gid: str) -> Project:
        """Return the project for the given ID."""
        _logger.debug(f"Fetching Project({gid})")
        obj = self._client.projects.find_by_id(gid, fields=Project.fields())
        return Project.from_dict(obj)

    def task_by_gid(self, gid: str) -> Task:
        """Return the task for the given ID."""
        _logger.debug(f"Fetching Task({gid})")
        obj = self._client.tasks.find_by_id(gid, fields=Task.fields())
        return Task.from_dict(obj)

    def me(self) -> User:
        """Return the user that the credentials belong to."""
        _logger.debug(f"Fetching current user")
        user = self._client.users.me(fields=User.fields())
        return User.from_dict(user)

    def tasks_by_project(
        self,
        project: Project,
        *,
        only_incomplete: bool = True,
        modified_since: Optional[datetime] = None,
    ) -> List[Task]:
        """Given a project, return all tasks in that project.

        :param project: The project to fetch tasks for.
        :param only_incomplete: Whether to return only incomplete tasks. Returning all
            tasks may take a long time for extremely large projects.
        :param modified_since: If set, only tasks modified since this datetime will be
            returned.
        """
        _logger.debug(f"Fetching tasks in {project}")
        params = {}
        if only_incomplete:
            params["completed_since"] = "now"
        if modified_since:
            params["modified_since"] = modified_since.isoformat()
        tasks = self._client.tasks.find_by_project(
            project.gid, params=params, fields=Task.fields()
        )
        return [Task.from_dict(task) for task in tasks]

    def sections_by_project(self, project: Project) -> List[Section]:
        """Given a project, return all sections in that project.

        :param project: The project to fetch sections for.
        """
        _logger.debug(f"Fetching sections in {project}")
        sections = self._client.sections.find_by_project(
            project.gid, fields=Section.fields()
        )
        return [Section.from_dict(section) for section in sections]

    def tasks_by_section(
        self, section: Section, only_incomplete: bool = True
    ) -> List[Task]:
        """Given a section, return all tasks in that section.

        :param section: The section to fetch tasks for.
        :param only_incomplete: Whether to return only incomplete tasks. Returning all
            tasks may take a long time for extremely large projects.
        """
        _logger.debug(f"Fetching tasks in {section}")
        # TODO: Filter in GET /sections/:section/tasks if/when API supports this
        # Right now you can only get *all* tasks in a section. It's safer and faster to
        # fetch all incomplete tasks in the project and then filter to the right section
        if only_incomplete:
            tasks = self.tasks_by_project(
                section.project, only_incomplete=only_incomplete
            )
            return [
                t for t in tasks if any(m.section == section for m in t.memberships)
            ]
        else:
            task_dicts = self._client.tasks.find_by_section(
                section.gid, fields=Task.fields()
            )
            return [Task.from_dict(task) for task in task_dicts]

    def stories_by_task(self, task: Task) -> List[Story]:
        """Given a task, return all stories on that task.

        :param task: The task to fetch stories for.
        """
        _logger.debug(f"Fetching stories on {task}")
        stories = self._client.tasks.stories(task.gid, fields=Story.fields())
        return [Story.from_dict(story) for story in stories]

    def typeahead(
        self, workspace: Workspace, cls: Type[_M], name: str, count: int = 100
    ) -> List[_M]:
        _logger.debug(f"Searching typeahead in {workspace}")
        results = self._client.workspaces.typeahead(
            workspace.gid,
            params={
                "resource_type": cls.__name__.lower(),
                "query": name,
                "count": count,
            },
            fields=cls.fields(),
        )
        return [cls.from_dict(item) for item in results]

    # Writes

    def reorder_in_project(
        self, task: Task, project: Project, reference: Task, direction: str
    ) -> None:
        """Move a task inside a project.

        :param task: The task to move.
        :param project: The project in which to relocate it.
        :param reference: What other task should be used as the insertion point.
        :param direction: Whether to put this task before or after the reference.
        """
        _logger.debug(f"Moving {task} {direction} {reference} in {project}")
        params = {"project": project.gid, f"insert_{direction}": reference.gid}
        self._client.tasks.add_project(task.gid, params)

    def add_to_project(self, task: Task, project: Project) -> None:
        """Add a task to a project.

        :param task: The task to move.
        :param project: The project in which to put it.
        """
        _logger.debug(f"Adding {task} to {project}")
        params = {"project": project.gid}
        self._client.tasks.add_project(task.gid, params)

    def add_to_section(self, task: Task, section: Section) -> None:
        """Add a task to a section.

        :param task: The task to move.
        :param section: The section in which to put it.
        """
        _logger.debug(f"Adding {task} to {section}")
        params = {"project": section.project.gid, "section": section.gid}
        self._client.tasks.add_project(task.gid, params)

    def add_comment(self, task: Task, comment: str) -> None:
        """Add a comment to a task.

        :param task: The task to receive the comment.
        :param comment: The plain text of the comment.
        """
        _logger.debug(f"Adding comment {comment} to {task}")
        self._client.tasks.add_comment(task.gid, {"text": comment})

    def add_follower(self, task: Task, follower: str) -> None:
        """Add a follower to a task.

        :param task: The task to receive the follower.
        :param follower: The follower to add, represented as a string. This can be the
            user's GID or their email.
        """
        _logger.debug(f"Adding follower {follower} to {task}")
        self._client.tasks.add_followers(task.gid, {"followers": [follower]})

    def set_assignee(self, task: Task, assignee: Optional[str]) -> None:
        """Change the assignee of the task.

        :param task: The task to change the assignee on.
        :param assignee: The new assignee, represented as a string. This can be the
            user's GID or their email. If ``None``, this unassigns the task.
        """
        _logger.debug(f"Setting assignee on {task} to {assignee}")
        self._client.tasks.update(task.gid, {"assignee": assignee})

    def set_enum_custom_field(
        self, task: Task, custom_field: CustomField, enum_value: Optional[EnumOption]
    ) -> None:
        """Set an enum custom field to a particular value.

        :param task: The task to change the field on.
        :param custom_field: The custom field to change the value of.
        :param enum_value: The new enum value to set on the task.
        """
        _logger.debug(f"Setting {custom_field} to {enum_value} on {task}")
        enum_value_gid: Optional[
            str
        ] = enum_value.gid if enum_value is not None else None
        self._client.tasks.update(
            task.gid, {"custom_fields": {custom_field.gid: enum_value_gid}}
        )

    def set_external(self, task: Task, external: External) -> None:
        _logger.debug(f"Setting external data to {external} on {task}")
        self._client.tasks.update(task.gid, {"external": external.to_dict()})
