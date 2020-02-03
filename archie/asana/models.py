"""
These models provide a Python translation of Asana's API data model for easier,
type-safe use in code. This is not a complete list of all Asana's models, nor does each
model have its complete list of fields defined. Instances of models are also frozen and
cannot be modified after creation/deserialization, to make it clear that mutations must
be done through the API client and not on the model.

Caution: Defining new fields on these models will cause the client to request them from
the API for every task, even if the field isn't ever used in code.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, ClassVar, List, Mapping, Optional, Type, TypeVar, Union

import attr
import cattr  # type: ignore

from archie._types import innermost_type

_S = TypeVar("_S", bound="_Serializable")
_M = TypeVar("_M", bound="_Model")


def _structure_date(obj: str, cls: Type[date]) -> date:
    return cls.fromisoformat(obj)


def _unstructure_date(obj: date) -> str:
    return obj.isoformat()


def _structure_datetime(obj: str, cls: Type[datetime]) -> datetime:
    return cls.fromisoformat(obj.replace("Z", "+00:00"))


def _unstructure_datetime(obj: datetime) -> str:
    # If no timezone is present, assume UTC
    if not obj.tzinfo:
        obj = obj.replace(tzinfo=timezone.utc)
    return obj.isoformat(timespec="milliseconds")


cattr.register_structure_hook(date, _structure_date)
cattr.register_unstructure_hook(date, _unstructure_date)
cattr.register_structure_hook(datetime, _structure_datetime)
cattr.register_unstructure_hook(datetime, _unstructure_datetime)


@attr.s
class _HasFields:
    """A class that has fields in the API."""

    @classmethod
    def fields(cls) -> List[str]:
        """Build a list of field names needed to create the Python model.

        :return: A list of field names for the ``opt_fields`` input to the Asana API.
        """
        fields = attr.fields(cls)
        field_types = [
            (f.name, innermost_type(f.type)) for f in fields if f.name != "gid"
        ]
        field_names = [
            [f"{name}.{f}" for f in typ.fields()]
            if issubclass(typ, _HasFields)
            else [name]
            for (name, typ) in field_types
        ]
        return [name for names in field_names for name in names]


class _Serializable:
    """An interface for converting a class to/from a dictionary of primitives."""

    @classmethod
    def from_dict(cls: Type[_S], d: dict) -> _S:
        """Deserialize a dictionary into this class.

        :param d: The dictionary of instance values.
        :return: The deserialized class.
        """
        return cattr.structure(d, cls)  # type: ignore

    def to_dict(self) -> dict:
        """Convert this instance into a dictionary.

        :return: The dictionary of instance values.
        """
        return cattr.unstructure(self)  # type: ignore


# TODO: Make enums for resource subtypes
class ResourceType(Enum):
    """The fixed resource types encountered in the API."""

    CUSTOM_FIELD = "custom_field"
    ENUM_OPTION = "enum_option"
    PROJECT = "project"
    SECTION = "section"
    STORY = "story"
    TASK = "task"
    TASK_MEMBERSHIP = "task_membership"
    USER = "user"
    WORKSPACE = "workspace"


@attr.s(frozen=True)
class _Model(_HasFields, _Serializable):
    """Base class for all Asana models.

    :ivar str gid: The unique global ID of the object.
    :ivar ResourceType resource_type: The type of the object.
    """

    gid = attr.ib(type=str)
    resource_type: ClassVar[ResourceType]

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.gid})"


@attr.s(frozen=True)
class Workspace(_Model):
    """A workspace, the largest scope of data in Asana.

    :ivar str gid: The unique global ID of the workspace.
    :ivar str name: The name of the workspace.
    """

    name = attr.ib(type=str)
    resource_type: ClassVar[ResourceType] = ResourceType.WORKSPACE


@attr.s(frozen=True)
class User(_Model):
    """A user.

    :ivar str gid: The unique global ID of the user.
    :ivar str name: The user's name.
    :ivar str email: The user's primary email address.
    """

    name = attr.ib(type=str)
    email = attr.ib(type=str)
    resource_type: ClassVar[ResourceType] = ResourceType.USER


@attr.s(frozen=True)
class Project(_Model):
    """A project, a collection of tasks within sections.

    :ivar str gid: The unique global ID of the project.
    :ivar str name: The name of the project.
    :ivar Workspace workspace: The workspace the project exists in.
    """

    name = attr.ib(type=str)
    workspace = attr.ib(type=Workspace)
    resource_type: ClassVar[ResourceType] = ResourceType.PROJECT


@attr.s(frozen=True)
class Section(_Model):
    """A section, a collection of tasks.

    :ivar str gid: The unique global ID of the section.
    :ivar str name: The name of the section.
    :ivar Project project: The project the section belongs to.
    """

    name = attr.ib(type=str)
    project = attr.ib(type=Project)
    resource_type: ClassVar[ResourceType] = ResourceType.SECTION


@attr.s(frozen=True)
class EnumOption(_Model):
    """An enum option for a custom field.

    :ivar str gid: The unique global ID of the enum option.
    :ivar str name: The name of the enum option.
    :ivar Optional[str]: The color of the enum option.
    """

    name = attr.ib(type=str)
    color = attr.ib(type=Optional[str])
    resource_type: ClassVar[ResourceType] = ResourceType.ENUM_OPTION


# TODO: Make subclasses for each custom field subtype
@attr.s(frozen=True)
class CustomField(_Model):
    """A custom field.

    :ivar str gid: The unique global ID of the custom field.
    :ivar str resource_subtype: The subtype of the custom field.
    :ivar str name: The name of the custom field.
    :ivar Optional[EnumOption] enum_value: The current enum value of the custom field,
        if the value is set and the field is of the appropriate type.
    :ivar Optional[List[EnumOption]] enum_options:
    :ivar str text_value: The current number value of the custom field, if the value is
        set and the field is of the appropriate type.
    :ivar float number_value: The current text value of the custom field, if the value
        is set and the field is of the appropriate type.
    """

    resource_subtype = attr.ib(type=str)
    name = attr.ib(type=str)
    enum_value = attr.ib(type=Optional[EnumOption], default=None)
    enum_options = attr.ib(type=Optional[List[EnumOption]], default=None)
    text_value = attr.ib(type=Optional[str], default=None)
    number_value = attr.ib(type=Optional[float], default=None)
    resource_type: ClassVar[ResourceType] = ResourceType.CUSTOM_FIELD


@attr.s(frozen=True)
class TaskMembership(_HasFields, _Serializable):
    """A task's membership in some project-section pair.

    :ivar Project project: The name of the project the task is in.
    :ivar Section section: The name of the section the task is in within that project.
    """

    project = attr.ib(type=Project)
    section = attr.ib(type=Section)
    resource_type: ClassVar[ResourceType] = ResourceType.TASK_MEMBERSHIP


@attr.s(frozen=True)
class External(_HasFields, _Serializable):
    """An external data object.

    :ivar Optional[str] id: The external ID of the parent object.
    :ivar Optional[str] data: The external data of the object.
    """

    gid = attr.ib(type=Optional[str])
    data = attr.ib(type=Mapping[str, Any])


def _structure_external(obj: dict, cls: Type[External]) -> External:
    data = obj.get("data")
    return cls(gid=obj.get("gid"), data=json.loads(data or "{}"))


def _unstructure_external(obj: External) -> dict:
    data = obj.data if obj.data is None else json.dumps(obj.data)
    return {"gid": obj.gid, "data": data}


cattr.register_structure_hook(External, _structure_external)
cattr.register_unstructure_hook(External, _unstructure_external)


@attr.s(frozen=True)
class Task(_Model):
    """A task.

    :ivar str gid: The unique global ID of the task.
    :ivar str name: The name of the task.
    :ivar str notes: The plain-text description of the task.
    :ivar bool completed: Whether the task is complete.
    :ivar List[CustomField] custom_fields: Custom field values on the task.
    :ivar List[TaskMembership] memberships: The task's memberships in other projects and
        sections.
    :ivar int num_likes: The number of likes the task has received.
    :ivar datetime created_at: The datetime when the task was created, in UTC.
    :ivar User created_by: The user that created the task.
    :ivar Optional[User] assignee: The user currently assigned to the task.
    :ivar Optional[date] due_on: The due date of the task. Meaningless if the due
        datetime is set.
    :ivar Optional[datetime] due_at: The due datetime of the task.
    :ivar Optional[date] start_on: The start date of the task.
    :ivar Optional[External] external: The external object associated with the task.
    """

    name = attr.ib(type=str)
    notes = attr.ib(type=str)
    completed = attr.ib(type=bool)
    custom_fields = attr.ib(type=List[CustomField])
    memberships = attr.ib(type=List[TaskMembership])
    num_likes = attr.ib(type=int)
    created_at = attr.ib(type=datetime)
    created_by = attr.ib(type=User)
    assignee = attr.ib(type=Optional[User])
    due_on = attr.ib(type=Optional[date])
    due_at = attr.ib(type=Optional[datetime])
    start_on = attr.ib(type=Optional[date])
    external = attr.ib(type=Optional[External], default=None)
    resource_type: ClassVar[ResourceType] = ResourceType.TASK


# TODO: Make subclasses for individual story types
@attr.s(frozen=True)
class Story(_Model):
    """A story on a task, representing some piece of history.

    :ivar str gid: The unique global ID of the task.
    :ivar str resource_subtype: The subtype of the story.
    :ivar str text: The plain-text contents of the story.
    :ivar datetime created_at: The datetime when the story was created, in UTC.
    :ivar Optional[User] created_by: The user that created the story, if any.
    :ivar Optional[Project] project: If the story is about a task being added to,
        removed from, or moved within a project, this is that project.
    :ivar Optional[Section] new_section: If the story is about a task changing section,
        this is the new section the task was moved to.
    :ivar Optional[CustomField] custom_field: If the story is about a custom field
        changing on the task, this is the custom field that changed.
    :ivar Optional[EnumOption] new_enum_value: If this story is about an enum custom
        field changing on the task, this is the new value it was changed to.
    :ivar Optional[User] assignee: If the story is about the assignee changing on a
        task, this is the new assignee.
    """

    resource_subtype = attr.ib(type=str)
    text = attr.ib(type=str)
    created_at = attr.ib(type=datetime)
    created_by = attr.ib(type=Optional[User])
    # Subtype-specific fields
    project = attr.ib(type=Optional[Project], default=None)
    new_section = attr.ib(type=Optional[Section], default=None)
    custom_field = attr.ib(type=Optional[CustomField], default=None)
    new_enum_value = attr.ib(type=Optional[EnumOption], default=None)
    assignee = attr.ib(type=Optional[User], default=None)
    resource_type: ClassVar[ResourceType] = ResourceType.STORY


class EventAction(Enum):
    """The different kinds of actions that can be described by events."""

    ADDED = "added"
    CHANGED = "changed"
    DELETED = "deleted"
    REMOVED = "removed"
    UNDELETED = "undeleted"


@attr.s(frozen=True)
class Event(_HasFields, _Serializable):
    """An event, such as from an event stream.

    :ivar EventAction action: The kind of action this event represents.
    :ivar datetime created_at: The datetime when the event occurred, in UTC.
    :ivar Optional[Union[Project,Task]] parent: The parent of the resource, if any.
    :ivar Union[Task,Story] resource: The resource the event is about.
    :ivar User user: The user that caused the event.
    """

    action = attr.ib(type=EventAction)
    created_at = attr.ib(type=datetime)
    parent = attr.ib(type=Optional[Union[Project, Task]])
    resource = attr.ib(type=Union[Task, Story])
    user = attr.ib(type=User)

    # TODO: Update _HasFields.fields() to handle unions.
    @classmethod
    def fields(cls) -> List[str]:
        fields = set(super().fields())
        typ: Type[_HasFields]
        for typ in [Task, Story]:
            fields.update(f"resource.{f}" for f in typ.fields())
        for typ in [Project, Task]:
            fields.update(f"parent.{f}" for f in typ.fields())
        return list(fields)
