from typing import List, Optional, Tuple, Union

import attr

from archie._itertools import find_by_name
from archie.asana.client import Client
from archie.asana.models import CustomField, EnumOption, Task
from archie.workflows.workflow import (
    Workflow,
    WorkflowGetStageContext,
    WorkflowSetStageContext,
    WorkflowStage,
    WorkflowStageManager,
)


@attr.s(auto_attribs=True, frozen=True)
class _EnumCustomFieldWorkflowGetStageContext(WorkflowGetStageContext):
    """Get context for a custom field-powered workflow.

    :ivar CustomField custom_field: The relevant custom field from the task.
    :ivar List[EnumOption] enum_options: The enum options from that custom field.
    """

    custom_field: CustomField
    enum_options: List[EnumOption]


@attr.s(auto_attribs=True, frozen=True)
class _EnumCustomFieldWorkflowSetStageContext(WorkflowSetStageContext):
    """Set context for a custom field-powered workflow.

    :ivar CustomField custom_field: The relevant custom field from the task.
    :ivar EnumOption enum_option: The enum option to set on the task.
    """

    custom_field: CustomField
    enum_option: EnumOption


class _EnumCustomFieldWorkflowStageManager(
    WorkflowStageManager[
        _EnumCustomFieldWorkflowGetStageContext, _EnumCustomFieldWorkflowSetStageContext
    ]
):
    """A stage manager for custom field workflows.

    This stage manager reads/writes the state of the workflow to a particular enum
    custom field on the task.

    :param name: The name of the custom field to read/write.
    :param stages: The list of stages for the workflow.
    """

    def __init__(self, name: str, stages: List[WorkflowStage]):
        self._name = name
        self._stages = stages

    def get_current_stage(
        self, task: Task
    ) -> Union[
        Tuple[Optional[WorkflowStage], _EnumCustomFieldWorkflowGetStageContext], str
    ]:
        custom_field = find_by_name(task.custom_fields, self._name)
        if custom_field is None or custom_field.enum_options is None:
            return f"Unable to find enum custom field '{self._name}'"
        context = _EnumCustomFieldWorkflowGetStageContext(
            custom_field=custom_field, enum_options=custom_field.enum_options
        )
        if custom_field.enum_value is None:
            stage = None
        else:
            stage_name = custom_field.enum_value.name
            stage = find_by_name(self._stages, stage_name)
            if stage is None:
                return f"Unable to find stage '{stage_name}'"
        return stage, context

    def can_set_stage(
        self,
        stage: WorkflowStage,
        client: Client,
        context: _EnumCustomFieldWorkflowGetStageContext,
    ) -> Union[_EnumCustomFieldWorkflowSetStageContext, str]:
        enum_option = find_by_name(context.enum_options, stage.name)
        if enum_option is None:
            return f"Unable to find enum option '{stage.name}'"
        return _EnumCustomFieldWorkflowSetStageContext(
            context.custom_field, enum_option
        )

    def set_stage(
        self,
        task: Task,
        client: Client,
        context: _EnumCustomFieldWorkflowSetStageContext,
    ) -> None:
        client.set_enum_custom_field(task, context.custom_field, context.enum_option)


class EnumCustomFieldWorkflow(
    Workflow[
        _EnumCustomFieldWorkflowGetStageContext, _EnumCustomFieldWorkflowSetStageContext
    ]
):
    """A workflow that saves state in an enum custom field on the task.

    :param name: The name of the enum custom field to use.
    :param stages: The list of stages for the workflow.
    """

    def __init__(self, name: str, stages: List[WorkflowStage]) -> None:
        manager = _EnumCustomFieldWorkflowStageManager(name, stages)
        super().__init__(name, stages, manager)
