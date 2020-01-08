from datetime import date, datetime
from typing import Any, List, Mapping, Optional

from archie.asana.models import (
    CustomField,
    EnumOption,
    External,
    Project,
    Section,
    Story,
    Task,
    TaskMembership,
    User,
    Workspace,
)


def workspace(gid: str = "workspace-gid", name: str = "Workspace") -> Workspace:
    return Workspace(gid=gid, name=name)


def user(
    gid: str = "user-gid", name: str = "User", email: str = "user@domain.com"
) -> User:
    return User(gid=gid, name=name, email=email)


def task(
    gid: str = "task-gid",
    name: str = "Task name",
    notes: str = "Task description",
    completed: bool = False,
    custom_fields: Optional[List[CustomField]] = None,
    memberships: Optional[List[TaskMembership]] = None,
    num_likes: int = 0,
    created_at: datetime = datetime(2019, 1, 1, 0, 0, 0),
    created_by: User = user(),
    assignee: Optional[User] = None,
    due_on: Optional[date] = None,
    due_at: Optional[datetime] = None,
    start_on: Optional[date] = None,
    external: Optional[External] = None,
) -> Task:
    return Task(
        gid=gid,
        name=name,
        notes=notes,
        completed=completed,
        custom_fields=custom_fields or [],
        memberships=memberships or [],
        num_likes=num_likes,
        created_at=created_at,
        created_by=created_by,
        assignee=assignee,
        due_on=due_on,
        due_at=due_at,
        start_on=start_on,
        external=external,
    )


def project(
    gid: str = "project-gid",
    name: str = "Project name",
    workspace: Workspace = workspace(),
) -> Project:
    return Project(gid=gid, name=name, workspace=workspace)


def section(
    gid: str = "section-gid", name: str = "Section name", project: Project = project()
) -> Section:
    return Section(gid=gid, name=name, project=project)


def enum_option(
    gid: str = "enum-option-gid",
    name: str = "Enum option name",
    color: Optional[str] = None,
) -> EnumOption:
    return EnumOption(gid=gid, name=name, color=color)


def custom_field(
    gid: str = "custom-field-gid",
    resource_subtype: str = "text",
    name: str = "Custom field name",
    enum_value: Optional[EnumOption] = None,
    enum_options: Optional[List[EnumOption]] = None,
    text_value: Optional[str] = None,
    number_value: Optional[float] = None,
) -> CustomField:
    return CustomField(
        gid=gid,
        resource_subtype=resource_subtype,
        name=name,
        enum_value=enum_value,
        enum_options=enum_options,
        text_value=text_value,
        number_value=number_value,
    )


def task_membership(
    project: Project = project(), section: Section = section()
) -> TaskMembership:
    return TaskMembership(project=project, section=section)


def external(
    gid: Optional[str] = None, data: Optional[Mapping[str, Any]] = None
) -> External:
    return External(gid=gid, data=data or {})


def story(
    gid: str = "story-gid",
    resource_subtype: str = "comment_added",
    text: str = "Comment text",
    created_by: Optional[User] = None,
    created_at: datetime = datetime(2019, 1, 1, 0, 0, 0),
    project: Optional[Project] = None,
    new_section: Optional[Section] = None,
    new_enum_value: Optional[EnumOption] = None,
    custom_field: Optional[CustomField] = None,
    assignee: Optional[User] = None,
) -> Story:
    return Story(
        gid=gid,
        resource_subtype=resource_subtype,
        text=text,
        created_by=created_by,
        created_at=created_at,
        project=project,
        new_section=new_section,
        new_enum_value=new_enum_value,
        custom_field=custom_field,
        assignee=assignee,
    )
