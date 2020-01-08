import logging
from test import fixtures as f
from typing import List, Tuple
from unittest import TestCase
from unittest.mock import Mock, create_autospec

from archie.actions import Action
from archie.asana.client import Client
from archie.predicates import Predicate
from archie.workflows import Workflow, WorkflowStage
from archie.workflows.workflow import (
    WorkflowGetStageContext,
    WorkflowSetStageContext,
    WorkflowStageManager,
)


class TestWorkflowGetStageContext(WorkflowGetStageContext):
    pass


class TestWorkflowSetContext(WorkflowSetStageContext):
    pass


get_context = TestWorkflowGetStageContext()
set_context = TestWorkflowSetContext()
task = f.task()
client = create_autospec(Client)


class TestWorkflow(TestCase):
    def setUp(self) -> None:
        self.manager = create_autospec(WorkflowStageManager)
        self.predicates = predicate_a, predicate_b = (
            create_autospec(Predicate),
            create_autospec(Predicate),
        )
        self.actions = action_a, action_b = [
            create_autospec(Action),
            create_autospec(Action),
        ]
        self.stages = [
            WorkflowStage("A", predicate_a, [action_a]),
            WorkflowStage("B", predicate_b, [action_b]),
        ]

        self.workflow: Workflow = Workflow("Workflow", self.stages, self.manager)

    def set_predicates(self, a: bool, b: bool) -> None:
        self.predicates[0].return_value = a
        self.predicates[1].return_value = b

    def test_no_get_context(self) -> None:
        self.manager.get_current_stage.return_value = "get warning"
        with self.assertLogs(self.workflow._logger, logging.WARNING) as logs:
            self.workflow(task, client)
        self.manager.get_current_stage.assert_called_once_with(task)
        self.assertListEqual(
            logs.output,
            ["WARNING:archie.workflows.workflow.Workflow(Workflow):get warning"],
        )
        self.manager.can_set_stage.assert_not_called()
        self.manager.set_stage.assert_not_called()

    def test_no_set_context(self) -> None:
        self.manager.get_current_stage.return_value = self.stages[0], get_context
        self.manager.can_set_stage.return_value = "set warning"
        self.set_predicates(True, True)
        with self.assertLogs(self.workflow._logger, logging.WARNING) as logs:
            self.workflow(task, client)
        self.manager.get_current_stage.assert_called_once_with(task)
        self.manager.can_set_stage.assert_called_once_with(
            self.stages[1], client, get_context
        )
        self.assertListEqual(
            logs.output,
            ["WARNING:archie.workflows.workflow.Workflow(Workflow):set warning"],
        )
        self.manager.set_stage.assert_not_called()

    def test_advance_none(self) -> None:
        self.manager.get_current_stage.return_value = None, get_context
        self.set_predicates(False, False)
        self.workflow(task, client)
        self.manager.get_current_stage.assert_called_once_with(task)
        self.manager.can_set_stage.assert_not_called()
        self.manager.set_stage.assert_not_called()

    def expect_set_stage(
        self,
        predicate_return_values: Tuple[bool, bool],
        expected_stage: WorkflowStage,
        expected_actions: List[Mock],
    ) -> None:
        for action in expected_actions:
            action.return_value = None
        self.manager.get_current_stage.return_value = None, get_context
        self.manager.can_set_stage.return_value = set_context
        self.manager.set_stage.return_value = None
        self.set_predicates(*predicate_return_values)
        self.workflow(task, client)
        self.manager.get_current_stage.assert_called_once_with(task)
        self.manager.can_set_stage.assert_called_once_with(
            expected_stage, client, get_context
        )
        for action in expected_actions:
            action.assert_called_once_with(task, client)
        self.manager.set_stage.assert_called_once_with(task, client, set_context)

    def test_advance_one(self) -> None:
        self.expect_set_stage((True, False), self.stages[0], self.actions[:1])

    def test_advance_multiple(self) -> None:
        self.expect_set_stage((True, True), self.stages[1], self.actions)
