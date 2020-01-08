"""
The triager is the execution core of this framework. The vast majority of other
components all represent configuration or data, and they're assembled together into the
triager which makes use of them. Predicates define what tasks match, but the triager is
what gives each predicate a task to check. Similarly, task sources define where to pull
data from, but the triager is what iterates over tasks and triggers API calls.

The triager also creates and stores the client for talking to the Asana API. All other
components that need the client can expect that the triager will provide it when
necessary. For example, actions are called with both the task to act on and the client
used to perform the mutation.
"""

import logging
from bisect import bisect_left
from concurrent.futures import Executor
from typing import Callable, List, MutableMapping, Set, Tuple

from archie._executor import LoggingThreadPoolExecutor
from archie._itertools import find, find_by_name
from archie.actions import Action
from archie.asana.client import Client
from archie.asana.models import Section, Task
from archie.predicates import Predicate
from archie.sorters import Sorter
from archie.sources import TaskSource
from archie.workflows.workflow import Workflow

_logger = logging.getLogger(__name__)
_TaskToActions = Callable[[Task], List[Action]]


class Triager:
    """Your new best friend.

    :param access_token: Credentials to access the Asana API.
    :param task_source: A source to provide tasks to triage.
    """

    def __init__(self, access_token: str, task_source: TaskSource) -> None:
        self._client = Client(access_token)
        self.task_source = task_source
        self.project = self._client.project_by_gid(task_source.project_gid)
        self._section_to_sorter: MutableMapping[Section, Sorter] = {}
        self._predicate_action_pairs: List[Tuple[Predicate, _TaskToActions]] = []
        self._ignored_predicates: Set[Predicate] = set()
        self._workflows: List[Workflow] = []

    @staticmethod
    def _executor() -> Executor:
        return LoggingThreadPoolExecutor()

    def order(self, section_name: str, by: Sorter) -> None:
        """Register that a given section should be sorted with a given sorter.

        :param section_name: The name of the section to sort.
        :param by: The sorter defining a sort order.
        """
        section = find_by_name(
            self._client.sections_by_project(self.project), section_name
        )
        if section is None:
            _logger.warning(f"{self.project} has no section '{section_name}'")
            return
        if section in self._section_to_sorter:
            _logger.warning(f"Sorter already defined for {section}")
            return
        self._section_to_sorter[section] = by

    def sort(self) -> None:
        """Sort the sections in the project with the registered sorters."""
        _logger.info(f"Sorting {self.project.name}")
        with self._executor() as executor:
            for section, sorter in self._section_to_sorter.items():
                executor.submit(self._sort_section, section, sorter)

    def _sort_section(self, section: Section, sorter: Sorter) -> None:
        _logger.info(f"Sorting {section.name}")
        tasks = self._client.tasks_by_section(section)
        sorted_tasks = sorter.sort(tasks)
        correct_index_for_tasks = [(sorted_tasks.index(task), task) for task in tasks]
        moves = self._generate_moves(correct_index_for_tasks)
        for task, direction, reference in moves:
            self._client.reorder_in_project(task, self.project, reference, direction)
        _logger.info(f"Finished sorting {section.name}")

    @staticmethod
    def _generate_moves(seq: List[Tuple[int, Task]]) -> List[Tuple[Task, str, Task]]:
        """Given a list of tasks and their rank, return moves to sort the items.

        The generated moves are of the form "move (task) to be (before/after)
        (other task). This directly translates to how tasks are reordered in the Asana
        API. This method should return the fewest number of moves necessary to put the
        tasks in sorted order.

        :param seq: A list of (rank, task) tuples.
        :return: A list of moves that transform the input into the desired order.
        """
        moves: List[Tuple[Task, str, Task]] = []
        output = seq[:1]
        for elem in seq[1:]:
            index = bisect_left(output, elem)
            if seq[index] != elem:
                if index == 0:
                    moves.append((elem[1], "before", output[index][1]))
                else:
                    moves.append((elem[1], "after", output[index - 1][1]))
            output.insert(index, elem)
        return moves

    def ignore(self, predicate: Predicate) -> None:
        """Indicate that tasks matching the given predicate should not be triaged.

        :param predicate: The predicate to ignore.
        """
        self._ignored_predicates.add(predicate)

    def when(self, predicate: Predicate) -> Callable[[_TaskToActions], _TaskToActions]:
        """Map a predicate to a function that will return actions to apply to a task.

        :param predicate: The predicate to match tasks against.
        :return: decorator to apply to a function that will return actions for tasks
            matching the predicate.
        """

        def register(action: _TaskToActions) -> _TaskToActions:
            self._predicate_action_pairs.append((predicate, action))
            return action

        return register

    def apply(self, workflow: Workflow) -> None:
        """Apply a multi-stage workflow to tasks in the project.

        :param workflow: The workflow to apply to the tasks.
        """
        iterator = self.task_source.iterator(self._client)
        with self._executor() as executor:
            for task in iterator:
                executor.submit(workflow, task, self._client)

    def triage(self) -> None:
        """Triage tasks in the project according to the registered predicates/actions.
        """
        _logger.info(f"Triaging {self.project.name}")
        iterator = self.task_source.iterator(self._client)
        with self._executor() as executor:
            for task in iterator:
                executor.submit(self._triage_task, task)

    def _triage_task(self, task: Task) -> None:
        ignored = find(self._ignored_predicates, lambda pred: pred(task, self._client))
        if ignored is not None:
            _logger.debug(f"{task} passed ignored predicate {ignored}, skipping")
            return

        actions = [
            action
            for predicate, create_action in self._predicate_action_pairs
            if predicate(task, self._client)
            for action in create_action(task)
        ]

        self._apply_actions(task, actions)

    def _apply_actions(self, task: Task, actions: List[Action]) -> None:
        for action in actions:
            action(task, self._client)
