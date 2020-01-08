from typing import List, Optional, Tuple, Union

import attr

from archie._itertools import find_by_name, first_or_none
from archie.asana.client import Client
from archie.asana.models import Project, Section, Task
from archie.workflows.workflow import (
    Workflow,
    WorkflowGetStageContext,
    WorkflowSetStageContext,
    WorkflowStage,
    WorkflowStageManager,
)


@attr.s(auto_attribs=True, frozen=True)
class _SectionWorkflowGetStageContext(WorkflowGetStageContext):
    """Get context for a section-powered workflow.

    :ivar Project project: The project the task is moving through.
    """

    project: Project


@attr.s(auto_attribs=True, frozen=True)
class _SectionWorkflowSetStageContext(WorkflowSetStageContext):
    """Set Context for a section-powered workflow.

    :ivar Section section: The section to insert the task into.
    """

    section: Section


class _SectionWorkflowStageManager(
    WorkflowStageManager[
        _SectionWorkflowGetStageContext, _SectionWorkflowSetStageContext
    ]
):
    """A stage manager for section workflows.

    This stage manager reads the state of the workflow from the name of the section the
    task is in, and writes is by moving the task to the section with the matching name.

    :param project_name: The name of the project whose sections should be used.
    :param stages: The list of stages for the workflow.
    """

    def __init__(self, project_name: str, stages: List[WorkflowStage]):
        self._project_name = project_name
        self._stages = stages

    def get_current_stage(
        self, task: Task
    ) -> Union[Tuple[Optional[WorkflowStage], _SectionWorkflowGetStageContext], str]:
        membership = first_or_none(
            m for m in task.memberships if m.project.name == self._project_name
        )
        if membership is None:
            return f"Unable to find membership in '{self._project_name}'"
        context = _SectionWorkflowGetStageContext(membership.project)
        return find_by_name(self._stages, membership.section.name), context

    def can_set_stage(
        self,
        stage: WorkflowStage,
        client: Client,
        context: _SectionWorkflowGetStageContext,
    ) -> Union[_SectionWorkflowSetStageContext, str]:
        sections = client.sections_by_project(context.project)
        new_section = find_by_name(sections, stage.name)
        if new_section is None:
            return f"Unable to find section '{stage.name}' in '{self._project_name}'"
        return _SectionWorkflowSetStageContext(new_section)

    def set_stage(
        self, task: Task, client: Client, context: _SectionWorkflowSetStageContext
    ) -> None:
        client.add_to_section(task, context.section)


class SectionWorkflow(
    Workflow[_SectionWorkflowGetStageContext, _SectionWorkflowSetStageContext]
):
    """A workflow that saves state in section a task is in.

    The current stage of the workflow is determined by which section a task is already
    in, and it's updated by moving the task into a new section.

    :param project_name: The name of the project the task is moving through.
    :param stages: The list of stages for the workflow.
    """

    def __init__(self, project_name: str, stages: List[WorkflowStage]) -> None:
        manager = _SectionWorkflowStageManager(project_name, stages)
        super().__init__(project_name, stages, manager)
