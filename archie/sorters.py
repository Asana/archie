"""
Sorters are used to order tasks relative to each other within sections, based any number
of attributes of each task. For example, tasks could be sorted by likes, by due date, or
by a custom field. Sorters can also be combined with each other to perform multi-level
sorts within the same section, such as ordering tasks first by the assignee and then
within those groups ordering tasks by their start dates.

These sorts will be evident when the project is *not* sorted in Asana's UI. If you sort
within Asana's UI, the tasks will first be sorted by the UI, and then sorted by any
sorters you've run against the project.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from datetime import date
from typing import Generic, List, Optional, Tuple, TypeVar

from archie._itertools import find_by_name
from archie._types import Comparable
from archie.asana.models import Task

_T = TypeVar("_T")
_C = TypeVar("_C", bound=Comparable)


class Sorter(ABC, Generic[_C]):
    """Abstract base class for task sorters.

    Subclasses must provide a key for each task.
    """

    @abstractmethod
    def key(self, task: Task) -> Tuple[_C, ...]:
        """Return the key that should be used to sort the task.

        The final sort order of a list of tasks is determined by key alone. The key
        should be a tuple of a comparable type so that this sorter can be merged with
        other sorters.

        :param task: A task being sorted.
        :return: The key the task should be sorted by.
        """
        pass

    def sort(self, tasks: List[Task]) -> List[Task]:
        """Sort a list of tasks, returning a new list.

        :param tasks: The tasks to sort.
        :return: A new list of the same tasks in sorted order.
        """
        return sorted(tasks, key=self.key)

    def and_then(self, other: Sorter) -> Sorter:
        """Merge this sorter with another sorter.

        Tasks will be sorted first by this sorter, and then within those groups be
        sorted by the ``other`` sorter.

        :param other: The next sorter to sort by.
        :return: A merged sorter that will sort by all inner sorters.
        """
        return _Merged(self, other)


class _Merged(Sorter):
    """The combination of multiple sorts."""

    def __init__(self, first: Sorter, second: Sorter) -> None:
        self.first = first
        self.second = second

    def key(self, task: Task) -> Tuple[_C, ...]:
        return (*self.first.key(task), *self.second.key(task))

    def __str__(self) -> str:
        return f"({self.first} and then {self.second})"


class _ListSorter(Sorter[int], ABC, Generic[_T]):
    """An abstract sorter that will sort tasks based on a predetermined list of values.

    :param ordered_items: The list of field values in the desired order.
    """

    def __init__(self, ordered_items: List[_T]) -> None:
        self.ordered_items = ordered_items

    @abstractmethod
    def _get_attr(self, task: Task) -> _T:
        """Extract the task attribute to sort by."""
        pass

    def _default(self) -> int:
        """Return a default location for values not in the ordered list."""
        return len(self.ordered_items)

    def key(self, task: Task) -> Tuple[int, ...]:
        attr: _T = self._get_attr(task)
        try:
            return (self.ordered_items.index(attr),)
        except ValueError:
            return (self._default(),)


class AssigneeSorter(_ListSorter[Optional[str]]):
    """Sort tasks by assignee name according to a list.

    Use ``None`` to specify where unassigned tasks go in the result. Tasks with
    assignees not in the list are put at the end.

    :param assignee_names: The list of assignee names in the desired sort order.
    """

    def __init__(self, assignee_names: List[Optional[str]]) -> None:
        super().__init__(ordered_items=assignee_names)

    def _get_attr(self, task: Task) -> Optional[str]:
        return task.assignee.name if task.assignee else None

    def __str__(self) -> str:
        return self.__class__.__name__


class DueDateSorter(Sorter):
    """Sort tasks by due dates.

    Tasks can be sorted in either ascending or descending order. Tasks without due dates
    can be put at either the start or the end of the section.

    :param ascending: Direction of the sort.
    :param missing_first: Whether to place tasks without a due date at the start or end.
    """

    def __init__(self, *, ascending: bool = True, missing_first: bool = False) -> None:
        self.order = 1 if ascending else -1
        self.missing_value = (
            date.max if (ascending ^ missing_first) else date.min
        ).toordinal()

    def key(self, task: Task) -> Tuple[int, ...]:
        if task.due_on:
            return (self.order * task.due_on.toordinal(),)
        return (self.missing_value,)

    def __str__(self) -> str:
        return self.__class__.__name__


class EnumCustomFieldSorter(_ListSorter[Optional[str]]):
    """Sort tasks by an enum custom field.

    Use ``None`` to specify where tasks without a set value for the field go in the
    result. Tasks with a value not in the list are put at the end.

    :param custom_field_name: The name of the custom field for sorting.
    :param enum_option_names: The names of the enum options in the desired sort order.
    """

    def __init__(
        self, custom_field_name: str, enum_option_names: List[Optional[str]]
    ) -> None:
        self.custom_field_name = custom_field_name
        super().__init__(ordered_items=enum_option_names)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.custom_field_name})"

    def _get_attr(self, task: Task) -> Optional[str]:
        custom_field = find_by_name(task.custom_fields, self.custom_field_name)
        if custom_field is None:
            return ""
        value = custom_field.enum_value
        if value is None:
            return None
        return value.name


class LikeSorter(Sorter):
    """Sort tasks by likes.

    :param ascending: Direction of the sort. Defaults to most-liked first.
    """

    def __init__(self, *, ascending: bool = False) -> None:
        self.order = 1 if ascending else -1

    def key(self, task: Task) -> Tuple[int, ...]:
        return (self.order * task.num_likes,)

    def __str__(self) -> str:
        return self.__class__.__name__


class NumberCustomFieldSorter(Sorter):
    """Sort tasks by a number custom field.

    Tasks without a set value are put at the end.

    :param custom_field_name: The name of the custom field for sorting.
    :param ascending: Direction of the sort.
    """

    def __init__(self, custom_field_name: str, *, ascending: bool = True) -> None:
        self.order = 1 if ascending else -1
        self.custom_field_name = custom_field_name

    def key(self, task: Task) -> Tuple[float, ...]:
        custom_field = find_by_name(task.custom_fields, self.custom_field_name)
        if custom_field is None or custom_field.number_value is None:
            return (math.inf,)
        return (self.order * custom_field.number_value,)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.custom_field_name})"


class StartDateSorter(Sorter):
    """Sort tasks by start dates.

    Tasks can be sorted in either ascending or descending order. Tasks without start
    dates can be put at either the start or the end of the section.

    :param ascending: Direction of the sort.
    :param missing_first: Whether to place tasks without a due date at the start or end.
    """

    def __init__(self, *, ascending: bool = True, missing_first: bool = False) -> None:
        self.order = 1 if ascending else -1
        self.missing_value = (
            date.max if (ascending ^ missing_first) else date.min
        ).toordinal()

    def key(self, task: Task) -> Tuple[int, ...]:
        if task.start_on:
            return (self.order * task.start_on.toordinal(),)
        return (self.missing_value,)

    def __str__(self) -> str:
        return self.__class__.__name__
