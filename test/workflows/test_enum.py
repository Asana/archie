from test import fixtures as f
from typing import List
from unittest import TestCase
from unittest.mock import create_autospec

from archie.asana.client import Client
from archie.asana.models import CustomField
from archie.predicates import Predicate
from archie.workflows import EnumCustomFieldWorkflow, WorkflowStage
from archie.workflows.enum import (
    _EnumCustomFieldWorkflowGetStageContext,
    _EnumCustomFieldWorkflowSetStageContext,
    _EnumCustomFieldWorkflowStageManager,
)

predicate_a = create_autospec(Predicate)
predicate_b = create_autospec(Predicate)

stages = [WorkflowStage("A", predicate_a), WorkflowStage("B", predicate_b)]
enum_options = [f.enum_option(name="A"), f.enum_option(name="B")]
custom_field = f.custom_field(name="Custom Field", enum_options=enum_options)


class TestEnumCustomFieldWorkflow(TestCase):
    def setUp(self) -> None:
        self.manager = _EnumCustomFieldWorkflowStageManager("Custom Field", stages)

    def expect_no_context(
        self, custom_fields: List[CustomField], expected_warning: str
    ) -> None:
        task = f.task(custom_fields=custom_fields)
        warning = self.manager.get_current_stage(task)
        self.assertEqual(expected_warning, warning)

    def test_missing_custom_field(self) -> None:
        self.expect_no_context(
            custom_fields=[],
            expected_warning="Unable to find enum custom field 'Custom Field'",
        )

    def test_wrong_custom_field_type(self) -> None:
        self.expect_no_context(
            custom_fields=[f.custom_field(name="Custom Field", enum_options=None)],
            expected_warning="Unable to find enum custom field 'Custom Field'",
        )

    def test_missing_stage(self) -> None:
        self.expect_no_context(
            custom_fields=[
                f.custom_field(
                    name="Custom Field",
                    enum_options=enum_options,
                    enum_value=f.enum_option(name="C"),
                )
            ],
            expected_warning="Unable to find stage 'C'",
        )

    def test_unset_custom_field_value(self) -> None:
        task = f.task(custom_fields=[custom_field])
        stage, context = self.manager.get_current_stage(task)
        expected_context = _EnumCustomFieldWorkflowGetStageContext(
            custom_field, enum_options
        )
        self.assertIsNone(stage)
        self.assertEqual(expected_context, context)

    def test_matching_stage(self) -> None:
        set_custom_field = f.custom_field(
            name="Custom Field", enum_options=enum_options, enum_value=enum_options[0]
        )
        task = f.task(custom_fields=[set_custom_field])
        stage, context = self.manager.get_current_stage(task)
        expected_context = _EnumCustomFieldWorkflowGetStageContext(
            set_custom_field, enum_options
        )
        self.assertIs(stage, stages[0])
        self.assertEqual(expected_context, context)

    def test_can_set_stage_missing_enum_option(self) -> None:
        client = create_autospec(Client)
        get_context = _EnumCustomFieldWorkflowGetStageContext(custom_field, [])
        warning = self.manager.can_set_stage(stages[0], client, get_context)
        self.assertEqual("Unable to find enum option 'A'", warning)

    def test_can_set_stage_matching_enum_option(self) -> None:
        client = create_autospec(Client)
        get_context = _EnumCustomFieldWorkflowGetStageContext(
            custom_field, enum_options
        )
        set_context = self.manager.can_set_stage(stages[0], client, get_context)
        expected_context = _EnumCustomFieldWorkflowSetStageContext(
            custom_field, enum_options[0]
        )
        self.assertEqual(expected_context, set_context)

    def test_set_stage(self) -> None:
        task = f.task()
        client = create_autospec(Client)
        context = _EnumCustomFieldWorkflowSetStageContext(custom_field, enum_options[0])
        self.manager.set_stage(task, client, context)
        client.set_enum_custom_field.assert_called_once_with(
            task, custom_field, enum_options[0]
        )

    def test_correct_manager(self) -> None:
        workflow = EnumCustomFieldWorkflow("name", [])
        self.assertIsInstance(
            workflow._stage_manager, _EnumCustomFieldWorkflowStageManager
        )
