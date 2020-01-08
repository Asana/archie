"""
A task source represents some feed of tasks from Asana that the triager should process.
They provide an iterator over tasks that the triager will draw from and pass on to
internal machinery such as predicates, actions, and workflows. Sources can either be
fixed in size (such as polling incomplete tasks in a project once) or infinite (such as
repeatedly polling for tasks that have changed).
"""

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from time import sleep
from typing import Iterator, Optional

from archie._easy_timedelta import EasyTimedelta, convert_timedelta
from archie.asana.client import Client
from archie.asana.models import Task


class TaskSource(ABC):
    """An abstract base class for all task sources.

    :ivar str project_gid: The GID of the project that the source pulls from. This is
        used for the triager to fetch the actual project object.
    """

    project_gid: str

    @abstractmethod
    def iterator(self, client: Client) -> Iterator[Task]:
        """Return an iterator over tasks in the project.

        :param client: A client used to access the Asana API.
        :return: An iterator of tasks that the triager should process.
        """
        pass


class PollingSource(TaskSource):
    """A task source that fetches all tasks in a project, optionally filtered.

    If ``repeat_after`` is provided, the source will fetch tasks, then delay for that
    amount of time, and then fetch tasks again, repeating the process indefinitely.

    Consequences of using this task source:

    * Extremely large projects can be slow to iterate over, especially if not filtered
      to only incomplete tasks.

    :param project_gid: The project the source draws from.
    :param repeat_after: How long the source should wait before polling again.
    :param only_incomplete: Whether the source should pull only incomplete tasks.
    """

    def __init__(
        self,
        project_gid: str,
        *,
        repeat_after: Optional[EasyTimedelta] = None,
        only_incomplete: bool = True
    ) -> None:
        self.project_gid = project_gid
        self.repeat_after = (
            convert_timedelta(repeat_after) if repeat_after is not None else None
        )
        self.only_incomplete = only_incomplete

    def iterator(self, client: Client) -> Iterator[Task]:
        project = client.project_by_gid(self.project_gid)
        if self.repeat_after is None:
            yield from client.tasks_by_project(
                project, only_incomplete=self.only_incomplete
            )
        else:
            while True:
                yield from client.tasks_by_project(
                    project, only_incomplete=self.only_incomplete
                )
                sleep(self.repeat_after.total_seconds())


class ModifiedSinceSource(TaskSource):
    """A task source that fetches tasks that have changed since the last fetch.

    This source uses the API's ``modified_since`` query parameter to limit tasks to only
    those that have recently changed. This source waits 60 second between fetching tasks
    to process. This source can be subclassed and have its :py:meth:`_set_last_run` and
    :py:meth:`_get_last_run` overridden so that the source can persist state about when
    it last fetched tasks, allowing the triager to be stopped and then later resumed
    without missing any modified tasks.

    Consequences of using this task source:

    * Tasks that do not see any activity are never returned from this source. This makes
      it impossible, e.g., triage neglected tasks that Asana users have ignored.
    * A task constantly undergoing changes, such as where a user is typing out a
      description over the course of several minutes, will appear frequently in each
      iteration of the source.
    * Tracking of changed tasks only starts when the source is first created.

    :param project_gid: The project the source draws from.
    """

    POLLING_DELAY = timedelta(seconds=60)

    def __init__(self, project_gid: str) -> None:
        self.project_gid = project_gid
        self._set_last_run(datetime.utcnow())

    def _set_last_run(self, last_run: datetime) -> None:
        """Set the time when the source last fetched tasks.

        This can be overridden to save the state to some persistent storage.

        :param last_run: When the source last fetched tasks.
        """
        self._last_run = last_run

    def _get_last_run(self) -> datetime:
        """Get the time when the source last fetched tasks.

        This can be overridden to load the state to some persistent storage.

        :return: When the source last fetched tasks.
        """
        return self._last_run

    def iterator(self, client: Client) -> Iterator[Task]:
        project = client.project_by_gid(self.project_gid)
        while True:
            modified_since, now = self._get_last_run(), datetime.utcnow()
            tasks = client.tasks_by_project(
                project, only_incomplete=False, modified_since=modified_since
            )
            self._set_last_run(now)
            yield from tasks
            sleep(self.POLLING_DELAY.total_seconds())
