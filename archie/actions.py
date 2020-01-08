"""
An action represents some mutation that should be applied to Asana. They are used to
indicate what should happen as a result of some task satisfying a predicate, such as
that task being assigned, receiving a comment, or having a custom field set to some
value. Actions to not have to be restricted to the provided task, and can change any
state in Asana, such as creating a brand new task in a separate project.
"""

import logging
from abc import ABC, abstractmethod
from typing import Optional

from archie._itertools import find_by_name
from archie.asana.client import Client
from archie.asana.models import External, Task

_logger = logging.getLogger(__name__)


class Action(ABC):
    """Abstract base class for all actions."""

    @abstractmethod
    def __call__(self, task: Task, client: Client) -> None:
        """Apply this action to a task.

        :param task: The task to apply the action to
        :param client: A client to access the Asana API.
        """

    def __str__(self) -> str:
        return self.__class__.__name__


class AddComment(Action):
    """Add a plain-text comment to a task.

    :param text: The text of the comment.
    """

    def __init__(self, text: str) -> None:
        self.text = text

    def __call__(self, task: Task, client: Client) -> None:
        client.add_comment(task, self.text)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.text})"


class AddFollower(Action):
    """Add a follower to a task.

    :param follower: The email of the user to add as a follower.
    """

    def __init__(self, follower: str) -> None:
        self.follower = follower

    def __call__(self, task: Task, client: Client) -> None:
        client.add_follower(task, self.follower)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.follower})"


class AssignTo(Action):
    """Assign or unassign a task.

    :param assignee: The email of the new assignee, or ``None`` to unassign.
    """

    def __init__(self, assignee: Optional[str]) -> None:
        self.assignee = assignee

    def __call__(self, task: Task, client: Client) -> None:
        client.set_assignee(task, self.assignee)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.assignee})"


class SetEnumCustomField(Action):
    """Set an enum custom field on a task.

    If the custom field is not present on the task, a warning will be logged and the
    action will not be applied. If the custom field is present but does not have an enum
    option with a matching name, then a warning will be logged and the action will not
    be applied. If the value of the custom field is already correct, then no API call
    will be made and the task will be left as-is in the desired state.

    :param custom_field_name: The name of the enum custom field to change.
    :param enum_value_name: The name of the enum option to choose.
    """

    def __init__(self, custom_field_name: str, enum_value_name: str) -> None:
        self.custom_field_name = custom_field_name
        self.enum_value_name = enum_value_name

    def __call__(self, task: Task, client: Client) -> None:
        custom_field = find_by_name(task.custom_fields, self.custom_field_name)
        if custom_field is None:
            _logger.warning(f"{task} has no custom field '{self.custom_field_name}'")
            return
        new_enum_value = find_by_name(
            custom_field.enum_options or [], self.enum_value_name
        )
        if new_enum_value is None:
            _logger.warning(
                f"{custom_field} has no enum option '{self.enum_value_name}'"
            )
            return None
        if new_enum_value != custom_field.enum_value:
            client.set_enum_custom_field(task, custom_field, new_enum_value)

    def __str__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"({self.custom_field_name}, {self.enum_value_name})"
        )


class SetExternal(Action):
    """Set the external object on a task.

    External data on a task is a separate object only accessible via the API for apps
    to store information on a task directly within Asana. Refer to the official Asana
    API docs for more details: https://developers.asana.com/docs/#custom-external-data

    Caution: this action may conflict with other actions of the same type, where the
    last to take effect will overwrite the external data.

    Caution: external data is tied to the app that created it. Changing the triager's
    access token will cause it to lose access to any previously stored external data.

    :param external: The new external object to replace the existing external object.
    """

    def __init__(self, external: External) -> None:
        self.external = external
        super().__init__()

    def __call__(self, task: Task, client: Client) -> None:
        client.set_external(task, self.external)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.external})"
