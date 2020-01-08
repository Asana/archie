from test import fixtures as f
from typing import Mapping
from unittest import TestCase
from unittest.mock import create_autospec

from archie.asana.client import Client
from archie.asana.models import External
from archie.predicates import Predicate
from archie.workflows import WorkflowStage
from archie.workflows.external import (
    ExternalDataWorkflow,
    _ExternalDataWorkflowGetStageContext,
    _ExternalDataWorkflowSetStageContext,
    _ExternalDataWorkflowStageManager,
)

predicate = create_autospec(Predicate)
stages = [WorkflowStage("A", create_autospec(Predicate))]


class TestExternalDataWorkflow(TestCase):
    def setUp(self) -> None:
        self.manager = _ExternalDataWorkflowStageManager("External workflow", stages)

    def test_no_external_object(self) -> None:
        task = f.task(external=None)
        stage, context = self.manager.get_current_stage(task)
        expected_context = _ExternalDataWorkflowGetStageContext(
            external=External(None, {}), workflows={}
        )
        self.assertIsNone(stage)
        self.assertEqual(expected_context, context)

    def test_no_workflow_mapping(self) -> None:
        external = f.external(data={})
        task = f.task(external=external)
        stage, context = self.manager.get_current_stage(task)
        expected_context = _ExternalDataWorkflowGetStageContext(
            external=external, workflows={}
        )
        self.assertIsNone(stage)
        self.assertEqual(expected_context, context)

    def expect_context_without_stage(self, workflow_data: Mapping[str, str]) -> None:
        external = f.external(data={"workflows": workflow_data})
        task = f.task(external=external)
        stage, context = self.manager.get_current_stage(task)
        expected_context = _ExternalDataWorkflowGetStageContext(
            external=external, workflows=workflow_data
        )
        self.assertIsNone(stage)
        self.assertEqual(expected_context, context)

    def test_no_workflow_stage(self) -> None:
        workflow_data: Mapping[str, str] = {}
        self.expect_context_without_stage(workflow_data)

    def test_missing_stage(self) -> None:
        workflow_data = {"External workflow": "B"}
        self.expect_context_without_stage(workflow_data)

    def test_matching_stage(self) -> None:
        workflow_data = {"External workflow": "A"}
        external = f.external(data={"workflows": workflow_data})
        task = f.task(external=external)
        stage, context = self.manager.get_current_stage(task)
        expected_context = _ExternalDataWorkflowGetStageContext(
            external=external, workflows=workflow_data
        )
        self.assertIs(stage, stages[0])
        self.assertEqual(expected_context, context)

    def test_can_set_stage(self) -> None:
        workflow_data = {"External workflow": "A"}
        external = f.external(data={"workflows": workflow_data})
        client = create_autospec(Client)
        get_context = _ExternalDataWorkflowGetStageContext(external, workflow_data)
        set_context = self.manager.can_set_stage(stages[0], client, get_context)
        expected_context = _ExternalDataWorkflowSetStageContext(
            external, workflow_data, "A"
        )
        self.assertEqual(expected_context, set_context)

    def expect_set(self, original_workflow_data: Mapping[str, str]) -> None:
        external = f.external(data={"workflows": original_workflow_data})
        task = f.task(external=external)
        client = create_autospec(Client)
        context = _ExternalDataWorkflowSetStageContext(
            external, original_workflow_data, "new stage name"
        )
        client.set_external.return_value = None
        self.manager.set_stage(task, client, context)
        client.set_external.assert_called_once_with(
            task,
            External(
                context.external.gid,
                {
                    "workflows": {
                        "External workflow": "new stage name",
                        "other workflow": "other stage name",
                    }
                },
            ),
        )

    def test_set_stage(self) -> None:
        original_workflow_data = {"other workflow": "other stage name"}
        self.expect_set(original_workflow_data)

    def test_overwrite_stage(self) -> None:
        original_workflow_data = {
            "External workflow": "old stage name",
            "other workflow": "other stage name",
        }
        self.expect_set(original_workflow_data)

    def test_correct_manager(self) -> None:
        workflow = ExternalDataWorkflow("name", [])
        self.assertIsInstance(
            workflow._stage_manager, _ExternalDataWorkflowStageManager
        )
