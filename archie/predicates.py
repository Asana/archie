"""
A predicate represents some condition that a task may or may not satisfy. The are used
to define rules that apply only to tasks that fit some criteria, such as being
unassigned, being overdue, or having a particular custom field.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta, timezone, tzinfo
from functools import partial
from typing import Callable, List, Optional, Union

from archie._easy_timedelta import EasyTimedelta, convert_timedelta
from archie._itertools import find, find_by_name
from archie.asana._stories import comments_by_task
from archie.asana.client import Client
from archie.asana.models import External, Story, Task, User


class Predicate(ABC):
    """Abstract base class for all predicates, providing logical operations."""

    @abstractmethod
    def __call__(self, task: Task, client: Client) -> bool:
        """Check if a given task satisfies this predicate.

        :param task: The task being checked.
        :param client: A client to access the Asana API for additional data.
        :return: Whether the task is considered a match for the predicate.
        """
        pass

    def __and__(self, other: Predicate) -> Predicate:
        """Create a new predicate from the logical "and" of two others.

        Predicates should be combined by using the ``&`` operator.

        :param other: Another predicate to combine with this one.
        :return: A new predicate that returns true only if both original predicates do.
        """
        return _And(self, other)

    def __or__(self, other: Predicate) -> Predicate:
        """Create a new predicate from the logical "or" of two others.

        Predicates should be combined by using the ``|`` operator.

        :param other: Another predicate to combine with this one.
        :return: A new predicate that returns true if either original predicate does.
        """
        return _Or(self, other)

    def __invert__(self) -> Predicate:
        """Create a new predicate from the logical negation of another.

        Predicates should be negated by using the ``~`` operator.

        :return: A new predicate that returns true if and only if the original returns
            false.
        """
        return _Not(self)

    def __str__(self) -> str:
        return self.__class__.__name__


class _And(Predicate):
    """The logical "and" of two predicates."""

    def __init__(self, first: Predicate, second: Predicate) -> None:
        self.first = first
        self.second = second

    def __call__(self, task: Task, client: Client) -> bool:
        return self.first(task, client) and self.second(task, client)

    def __str__(self) -> str:
        return f"({self.first} and {self.second})"


class _Or(Predicate):
    """The logical "or" of two predicates."""

    def __init__(self, first: Predicate, second: Predicate) -> None:
        self.first = first
        self.second = second

    def __call__(self, task: Task, client: Client) -> bool:
        return self.first(task, client) or self.second(task, client)

    def __str__(self) -> str:
        return f"({self.first} or {self.second})"


class _Not(Predicate):
    """The negation of a predicate."""

    def __init__(self, predicate: Predicate) -> None:
        self.predicate = predicate

    def __call__(self, task: Task, client: Client) -> bool:
        return not self.predicate(task, client)

    def __str__(self) -> str:
        return f"(not {self.predicate})"


class AlwaysTrue(Predicate):
    """A predicate that is always true, useful for initiating workflows."""

    def __call__(self, task: Task, client: Client) -> bool:
        return True


def _now(tz: tzinfo = timezone.utc) -> datetime:
    return datetime.now(tz)


def _today(tz: tzinfo = timezone.utc) -> date:
    return _now(tz).date()


def _duration_suffix(duration: Optional[timedelta]) -> str:
    """Return an appropriate suffix for ``__str__`` on predicates with a duration."""
    if duration and duration != timedelta.max:
        return f" for at least {duration}"
    return ""


def _for_at_least(
    task: Task,
    stories: List[Story],
    story_matcher: Callable[[Story], bool],
    duration: timedelta,
) -> bool:
    """Determine if a task has been in a given state for a minimum duration"""
    story = find(reversed(stories), story_matcher)
    # If there's a story reflecting the correct state, inspect time since that story
    if story is not None:
        return _now() - story.created_at > duration
    # If there isn't a story, assume that the task was created in the correct state
    return _now() - task.created_at > duration


class Assigned(Predicate):
    """Check if a task is assigned.

    If provided with a name, this will attempt to match the name of the assignee of the
    task, if any. If not provided, this will consider a match if there is any assignee.

    :param to: The name of the matching user.
    """

    def __init__(self, to: Optional[str] = None) -> None:
        self._name = to

    def __call__(self, task: Task, _: Client) -> bool:
        return task.assignee is not None and (
            self._name is None or task.assignee.name == self._name
        )

    def __str__(self) -> str:
        if self._name != "":
            return f"{self.__class__.__name__} to '{self._name}'"
        else:
            return self.__class__.__name__


class DueWithin(Predicate):
    """Check if a task is due within some time window.

    If, after the specified time window has elapsed, the task would be considered
    overdue, this predicate will return ``True``.

    :param window: How soon the task must be due to match.
    """

    def __init__(self, window: EasyTimedelta) -> None:
        self._window = convert_timedelta(window)

    def __call__(self, task: Task, _: Client) -> bool:
        if task.due_at is not None:
            return _now() < task.due_at <= _now() + self._window
        elif task.due_on is not None:
            return _today() < task.due_on <= _today() + self._window
        return False


class HasComment(Predicate):
    """Check if a task has a matching comment.

    If `comment_matcher` is a callable, it will be given the text of the comment and is
    expected to return a bool indicating whether that comment is considered a match.
    If `comment_matcher` is a string, it will be searched for literally within the text
    of the comment and, if found, the comment is considered a match.
    If `comment_matcher` is `None`, any comment will match.

    :param comment_matcher: Either a predicate to check comments again, a string
        to search for literally, or `None` to match any comment.
    """

    def __init__(
        self, comment_matcher: Union[Callable[[str], bool], str, None] = None
    ) -> None:
        self.comment_matcher = comment_matcher

    def match_comment(self, story: Story) -> bool:
        if self.comment_matcher is None:
            return True
        elif isinstance(self.comment_matcher, str):
            return self.comment_matcher in story.text
        else:
            return self.comment_matcher(story.text)

    def __call__(self, task: Task, client: Client) -> bool:
        return any(map(self.match_comment, comments_by_task(task, client)))


class _EnumValuePredicate(Predicate, ABC):
    custom_field_name: str
    duration: timedelta

    def __call__(self, task: Task, client: Client) -> bool:
        if not self._is_in_correct_state(task):
            return False
        if not self.duration:
            return True
        return _for_at_least(
            task, client.stories_by_task(task), self._story_matcher, self.duration
        )

    @abstractmethod
    def _is_in_correct_state(self, task: Task) -> bool:
        pass

    def _story_matcher(self, story: Story) -> bool:
        return (
            story.resource_subtype == "enum_custom_field_changed"
            and story.custom_field is not None
            and story.custom_field.name == self.custom_field_name
        )


# FIXME: This doesn't work with both a duration and "any value"
class HasEnumValue(_EnumValuePredicate):
    """Check if a custom field has a set value.

    If the task doesn't have the custom field at all, it will not match this predicate.

    :param custom_field_name: The name of the custom field to check.
    :param enum_option_name: The name of the enum option to match. If omitted, this will
        match any option.
    :param for_at_least: How long the task must have had the current custom field value.
    """

    def __init__(
        self,
        custom_field_name: str,
        enum_option_name: Optional[str] = None,
        for_at_least: EasyTimedelta = timedelta(),
    ) -> None:
        self.custom_field_name = custom_field_name
        self.enum_value_name = enum_option_name
        self.duration = convert_timedelta(for_at_least)

    def _is_in_correct_state(self, task: Task) -> bool:
        custom_field = find_by_name(task.custom_fields, self.custom_field_name)
        return (
            custom_field is not None
            and custom_field.enum_value is not None
            and (
                self.enum_value_name is None
                or custom_field.enum_value.name == self.enum_value_name
            )
        )

    def __str__(self) -> str:
        return (
            f"Has '{self.custom_field_name}' set to '{self.enum_value_name}'"
            + _duration_suffix(self.duration)
        )


class HasExternal(Predicate):
    """Check if a task has matching external data.

    Takes an optional callable that will be given the external object (both ID and data)
    and is expected to return whether that object is considered a match. If not given,
    any external object is considered a match.

    External data on a task is a separate object only accessible via the API for apps
    to store information on a task directly within Asana. Refer to the official Asana
    API docs for more details: https://developers.asana.com/docs/#custom-external-data

    :param predicate: An optional predicate to check the external object against.
    """

    def __init__(self, predicate: Optional[Callable[[External], bool]] = None) -> None:
        self.predicate = predicate

    def __call__(self, task: Task, _: Client) -> bool:
        if self.predicate is not None and task.external is not None:
            return self.predicate(task.external)
        return task.external is not None


class HasNoDueDate(Predicate):
    """Check if a task has no due date set."""

    def __call__(self, task: Task, _: Client) -> bool:
        return task.due_at is None and task.due_on is None


class HasDescription(Predicate):
    """Check if a task has a matching description.

    If a matcher is provided, it is used to check the description. If no matcher is
    provided, this returns ``True`` if the task has a non-empty description.

    :param matcher: An predicate to apply to the task description. Defaults to a check
        for a non-empty description.
    """

    def __init__(self, matcher: Callable[[str], bool] = bool) -> None:
        self.matcher = matcher

    def __call__(self, task: Task, _: Client) -> bool:
        return self.matcher(task.notes)


class HasUnsetEnum(_EnumValuePredicate):
    """Check if a custom field has no set value.

    If the task doesn't have the custom field at all, it will not match this predicate.

    :param custom_field_name: The name of the custom field to check.
    :param for_at_least: How long the task must have had the current custom field unset.
    """

    def __init__(
        self, custom_field_name: str, for_at_least: EasyTimedelta = timedelta()
    ) -> None:
        self.custom_field_name = custom_field_name
        self.duration = convert_timedelta(for_at_least)

    def _is_in_correct_state(self, task: Task) -> bool:
        custom_field = find_by_name(task.custom_fields, self.custom_field_name)
        return custom_field is not None and custom_field.enum_value is None

    def __str__(self) -> str:
        return f"Has '{self.custom_field_name}' unset" + _duration_suffix(self.duration)


class IsComplete(Predicate):
    """Check if a task is complete."""

    def __call__(self, task: Task, _: Client) -> bool:
        return task.completed


class IsIncomplete(Predicate):
    """Check if a task is incomplete."""

    def __call__(self, task: Task, _: Client) -> bool:
        return not task.completed


class IsInProject(Predicate):
    """Check if a task is in a specified project.

    :param project_name: The name of the project that the task must be in.
    :param for_at_least: If set, only match if the task has been in the project for at
        least this amount of time.
    """

    def __init__(
        self, project_name: str, for_at_least: EasyTimedelta = timedelta()
    ) -> None:
        self.project_name = project_name
        self.duration = convert_timedelta(for_at_least)

    def __call__(self, task: Task, client: Client) -> bool:
        if not self._is_in_correct_state(task):
            return False
        if not self.duration:
            return True
        return _for_at_least(
            task, client.stories_by_task(task), self._story_matcher, self.duration
        )

    def _is_in_correct_state(self, task: Task) -> bool:
        return any(m.project.name == self.project_name for m in task.memberships)

    def _story_matcher(self, story: Story) -> bool:
        # Check for added_to_project story
        if story.resource_subtype == "added_to_project" and story.project is not None:
            return story.project.name == self.project_name
        return False

    def __str__(self) -> str:
        return f"In '{self.project_name}' project" + _duration_suffix(self.duration)


class IsInProjectAndSection(Predicate):
    """Check if a task is in a specified project and section.

    :param project_name: The name of the project that the task must be in.
    :param section_name: The name of the section within that project that the task must
        be in.
    :param for_at_least: If set, only match if the task has been in the project and
        section for at least this amount of time.
    """

    def __init__(
        self,
        project_name: str,
        section_name: str,
        for_at_least: EasyTimedelta = timedelta(),
    ) -> None:
        self.project_name = project_name
        self.section_name = section_name
        self.duration = convert_timedelta(for_at_least)

    def __call__(self, task: Task, client: Client) -> bool:
        if not self._is_in_correct_state(task):
            return False
        if not self.duration:
            return True
        return _for_at_least(
            task, client.stories_by_task(task), self._story_matcher, self.duration
        )

    def _is_in_correct_state(self, task: Task) -> bool:
        return any(
            m.project.name == self.project_name
            and m.section is not None
            and m.section.name == self.section_name
            for m in task.memberships
        )

    def _story_matcher(self, story: Story) -> bool:
        # Check for section_changed story
        if (
            story.resource_subtype == "section_changed"
            and story.new_section is not None
        ):
            return (
                story.new_section.name == self.section_name
                and story.new_section.project.name == self.project_name
            )
        # Check for added_to_project story
        # If we didn't see a section changed story in the above check, then the task
        # is assumed to have been added directly to the section it's currently in, which
        # must be the correct section because of the ``_is_in_correct_state`` check,
        if story.resource_subtype == "added_to_project" and story.project is not None:
            return story.project.name == self.project_name
        return False

    def __str__(self) -> str:
        return (
            f"In '{self.project_name}' project and '{self.section_name}' section"
            + _duration_suffix(self.duration)
        )


class Overdue(Predicate):
    """Check if a task is overdue.

    If the task has a due date and time, it's compared to the current time.
    If the task only has a due date, it's compared to the current date.
    Tasks due today are not considered overdue.
    If a task has no due date, it's not considered overdue.
    """

    def __call__(self, task: Task, _: Client) -> bool:
        if task.due_at is not None:
            return task.due_at < _now()
        elif task.due_on is not None:
            return task.due_on < _today()
        return False


class Unassigned(Predicate):
    """Check if a task has no assignee."""

    def __call__(self, task: Task, _: Client) -> bool:
        return task.assignee is None


class Untriaged(Predicate):
    """Check if a task has not recently been triaged.

    If the triager has taken any action on this task within the specified window (as
    determined by the stories on the task) then this returns ``False``. The triager
    identifies itself by the user account associated with the API credentials it's been
    given.

    This can also be used to ignore tasks that have seen recent action by taking the
    negation. For example, ``triager.ignore(~Untriaged(for_at_least="2d"))`` will ignore
    tasks that the triager has interacted with in the past two days.

    If the duration is left unspecified, this predicate will pass if the triager has
    taken any action on the task at all. This can be used to ensure that the triager
    only interacts with each task once.

    :param for_at_least: The duration in which the triager has not taken action.
    """

    def __init__(self, for_at_least: EasyTimedelta = timedelta.max) -> None:
        self.duration = convert_timedelta(for_at_least)

    def __call__(self, task: Task, client: Client) -> bool:
        story = find(
            reversed(client.stories_by_task(task)),
            partial(self._story_matcher, client.me()),
        )
        if story is not None:
            return _now() - story.created_at > self.duration
        return True

    @staticmethod
    def _story_matcher(me: User, story: Story) -> bool:
        return story.created_by == me

    def __str__(self) -> str:
        return self.__class__.__name__ + _duration_suffix(self.duration)
