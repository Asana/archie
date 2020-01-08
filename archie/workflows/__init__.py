"""
A workflow is a multi-step process through which tasks advance. Each of these steps is a
"stage" defined by a ``WorkflowStage``. A ``Workflow`` then inspects tasks to determine
their current stage, advances it through any stages it can, and then updates the
recorded stage for that task. A number of typical workflows are already implemented:

- ``SectionWorkflow`` which maps stages of the workflow into sections of a project.
- ``EnumCustomFieldWorkflow`` which maps stages into values of an enum custom field.
- ``ExternalDataWorkflow`` which stores the stage in the external data of a task.

Workflow stages have three components to them:

- A name or label—this corresponds to the name of the section or enum option in section
  and custom field workflows respectively.
- A predicate—this predicate must be matched for a task to advance into the stage.
- Actions—these actions (of which there may be any number, including zero) are applied
  as a result of tasks entering that stage, i.e. as a side-effect of advancement.

Once defined, stages can be used to create a workflow that the triager will then drive.
A workflow may advance a task through multiple stages if the task satisfies all the
necessary conditions. If this happens, the actions of all the stages it passes through
will be applied.
"""

from archie.workflows.enum import EnumCustomFieldWorkflow
from archie.workflows.external import ExternalDataWorkflow
from archie.workflows.section import SectionWorkflow
from archie.workflows.workflow import Workflow, WorkflowStage, WorkflowStageManager

__all__ = [
    "EnumCustomFieldWorkflow",
    "ExternalDataWorkflow",
    "SectionWorkflow",
    "Workflow",
    "WorkflowStage",
    "WorkflowStageManager",
]
