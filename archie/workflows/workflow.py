import logging
from abc import ABC, abstractmethod
from typing import Generic, List, Optional, Tuple, TypeVar, Union

import attr

from archie.actions import Action
from archie.asana.client import Client
from archie.asana.models import Task
from archie.predicates import Predicate

_logger = logging.getLogger(__name__)


@attr.s(auto_attribs=True, frozen=True)
class WorkflowStage:
    """A stage in a workflow.

    :ivar str name: The name of the workflow stage.
    :ivar Predicate to_enter: The condition required to enter this workflow stage.
    :ivar List[Action] on_enter: The actions to apply to a task that has just
        entered this workflow stage.
    """

    name: str
    to_enter: Predicate
    on_enter: List[Action] = attr.ib(factory=list)


class WorkflowGetStageContext(ABC):
    """Context that should be carried into the ``_WorkflowStageManager.can_set_stage``
    method.

    Information about the task discovered in ``_WorkflowStageManager.get_stage`` is
    often needed again in ``_WorkflowStageManager.can_set_stage``. This context is used
    to carry that information from the first to the second.
    """

    pass


class WorkflowSetStageContext(ABC):
    """Context that should be carried into the ``_WorkflowStageManager.set_stage``
    method.

    Information about the task discovered in ``_WorkflowStageManager.can_set_stage``
    is often needed again in ``Workflow._set_stage``. This context is used to carry that
    information from the first to the second.
    """

    pass


_GSC = TypeVar("_GSC", bound=WorkflowGetStageContext)
_SSC = TypeVar("_SSC", bound=WorkflowSetStageContext)


class WorkflowStageManager(ABC, Generic[_GSC, _SSC]):
    """A manager that can handle getting and setting the workflow stage of a task.

    The stage manager is responsible for extracting the current stage of a task in a
    given workflow as well as setting a new stage if necessary. How stages are stored
    is independent of the logic that advanced the stage, so new methods of capturing
    progress of a task in a workflow only need to define a new stage manager.
    """

    @abstractmethod
    def get_current_stage(
        self, task: Task
    ) -> Union[Tuple[Optional[WorkflowStage], _GSC], str]:
        """Given a task, returns the workflow stage it is currently in, with context.

        If the task cannot be linked to any stage in the workflow, this instead returns
        a warning string to be logged by the ``Workflow``.

        :param task: The task being handled.
        :return: If the task can be linked to a ``WorkflowStage``, the return value is a
            tuple of ``(stage, context)``. If no stage can be linked, the return
            value is a warning string.
        """
        pass

    @abstractmethod
    def can_set_stage(
        self, stage: WorkflowStage, client: Client, context: _GSC
    ) -> Union[_SSC, str]:
        """Given a new workflow stage and previous context, determine how to set the
        stage.

        If the stage cannot be set, this instead returns a warning string to be logged
        by the ``Workflow``.

        :param stage: The desired stage to set on the task.
        :param client: A client to make any needed API requests with.
        :param context: The context returned from the ``get_current_stage`` method.
        :return: If the stage can be set, the return value is the set context. If it
            cannot be set, the return value is a warning string.
        """
        pass

    @abstractmethod
    def set_stage(self, task: Task, client: Client, context: _SSC) -> None:
        """Set the new workflow stage on the task.

        :param task: The task to set the stage on.
        :param client: A client to use to set the stage.
        :param context: The context with information from the ``can_set_stage`` method
            needed to set the stage on the task.
        """
        pass


class Workflow(Generic[_GSC, _SSC]):
    """A multi-stage sequential workflow.

    This class encapsulates the logic used to advance a task through a workflow and
    apply actions to the task as it moves. Workflows will automatically get and set the
    stage using a ``WorkflowStageManager`` so the individual stages do not need to
    include checks on the stage in their predicate or include actions to advance the
    stage in their actions.

    :param stages: The list of ``WorkflowStage`` for this workflow.
    :param stage_manager: A ``WorkflowStageManager`` that can be used to get and set the
        workflow stage of a task.
    """

    def __init__(
        self,
        name: str,
        stages: List[WorkflowStage],
        stage_manager: WorkflowStageManager[_GSC, _SSC],
    ) -> None:
        self._name = name
        self._stages = stages
        self._stage_manager = stage_manager
        self._logger = logging.getLogger(f"{self.__module__}.{self}")

    def __call__(self, task: Task, client: Client) -> None:
        """Apply this workflow to a task.

        If the task's stage cannot be determined, a warning will be logged and no action
        will be taken. Similarly, if a task's stage cannot be set, a warning will be
        logged and no action will be taken. A task can advance through multiple stages
        if it meets all intermediate conditions, and all actions from all stages will
        be applied to the task.

        :param task: The task moving through this workflow.
        :param client: A client to use to apply this workflow.
        """
        result_or_warning = self._stage_manager.get_current_stage(task)
        # If we can't map the task to stages, return
        if isinstance(result_or_warning, str):
            self._logger.warning(result_or_warning)
            return
        current_stage, get_stage_context = result_or_warning
        original_stage = current_stage
        if current_stage is not None:
            next_stage = self._next_stage(current_stage)
        else:
            next_stage = self._stages[0]
        actions = []
        while next_stage is not None and next_stage.to_enter(task, client):
            actions.extend(next_stage.on_enter)
            current_stage, next_stage = next_stage, self._next_stage(next_stage)
        # If we aren't advancing the stage, return
        if current_stage is None or current_stage is original_stage:
            return
        set_stage_context_or_warning = self._stage_manager.can_set_stage(
            current_stage, client, get_stage_context
        )
        # If we can't advance the stage, return (and don't apply intermediate actions)
        if isinstance(set_stage_context_or_warning, str):
            self._logger.warning(set_stage_context_or_warning)
            return
        for action in actions:
            action(task, client)
        self._stage_manager.set_stage(task, client, set_stage_context_or_warning)

    def _next_stage(self, stage: WorkflowStage) -> Optional[WorkflowStage]:
        """Given the current stage, determine the next stage in the sequence.

        If the task has no workflow stage, the next stage will be the first of the
        stages, i.e., the task will start on the first stage of the workflow. If the
        task is in the last stage, the next stage will be ``None``

        :param stage: The current workflow stage of the task.
        :return: The next stage the task should move into, or ``None`` if it cannot
            advance any farther.
        """
        next_index = self._stages.index(stage) + 1
        if not next_index < len(self._stages):
            return None
        return self._stages[next_index]

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self._name})"
