from typing import List, Mapping, Optional, Tuple, Union

import attr

from archie._itertools import find_by_name
from archie.asana.client import Client
from archie.asana.models import External, Task
from archie.workflows.workflow import (
    Workflow,
    WorkflowGetStageContext,
    WorkflowSetStageContext,
    WorkflowStage,
    WorkflowStageManager,
)


@attr.s(auto_attribs=True, frozen=True)
class _ExternalDataWorkflowGetStageContext(WorkflowGetStageContext):
    """Get context for an external data-powered workflow.

    :ivar Mapping[str,str] workflows: The map of workflow names to stage names.
    """

    external: External
    workflows: Mapping[str, str]


@attr.s(auto_attribs=True, frozen=True)
class _ExternalDataWorkflowSetStageContext(WorkflowSetStageContext):
    """Set context for an external data-powered workflow.

    :ivar Mapping[str,str] workflows: The map of workflow names to stage names.
    """

    external: External
    workflows: Mapping[str, str]
    stage_name: str


class _ExternalDataWorkflowStageManager(
    WorkflowStageManager[
        _ExternalDataWorkflowGetStageContext, _ExternalDataWorkflowSetStageContext
    ]
):
    """A stage manager for external data workflows.

    This stage manager reads/writes the state of the workflow from the external data
    blob on a task, specifically in a map stored under the ``"workflows"`` key.

    :param name: The name of the workflow. Used as the key in the map storing workflow
        states.
    :param stages: The list of stages for the workflow.
    """

    def __init__(self, name: str, stages: List[WorkflowStage]) -> None:
        self._name = name
        self._stages = stages

    def get_current_stage(
        self, task: Task
    ) -> Tuple[Optional[WorkflowStage], _ExternalDataWorkflowGetStageContext]:
        external = task.external or External(None, {})
        workflows = (external.data or {}).get("workflows", {})
        stage_name = workflows.get(self._name)
        return (
            find_by_name(self._stages, stage_name),
            _ExternalDataWorkflowGetStageContext(external, workflows),
        )

    def can_set_stage(
        self,
        stage: WorkflowStage,
        client: Client,
        context: _ExternalDataWorkflowGetStageContext,
    ) -> Union[_ExternalDataWorkflowSetStageContext, str]:
        return _ExternalDataWorkflowSetStageContext(
            context.external, context.workflows, stage.name
        )

    def set_stage(
        self, task: Task, client: Client, context: _ExternalDataWorkflowSetStageContext
    ) -> None:
        new_external_data = {
            **(context.external.data or {}),
            "workflows": {**context.workflows, self._name: context.stage_name},
        }
        new_external = External(context.external.gid, new_external_data)
        client.set_external(task, new_external)


class ExternalDataWorkflow(
    Workflow[_ExternalDataWorkflowGetStageContext, _ExternalDataWorkflowSetStageContext]
):
    """A workflow that saves state in the external data of a task.

    :param name: The name of the workflow.
    :param stages: The list of stages for the workflow.
    """

    def __init__(self, name: str, stages: List[WorkflowStage]) -> None:
        manager = _ExternalDataWorkflowStageManager(name, stages)
        super().__init__(name, stages, manager)
