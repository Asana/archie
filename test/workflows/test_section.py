from test import fixtures as f
from unittest import TestCase
from unittest.mock import create_autospec

from archie.asana.client import Client
from archie.predicates import Predicate
from archie.workflows import SectionWorkflow, WorkflowStage
from archie.workflows.section import (
    _SectionWorkflowGetStageContext,
    _SectionWorkflowSetStageContext,
    _SectionWorkflowStageManager,
)

predicate = create_autospec(Predicate)
stages = [WorkflowStage("A", create_autospec(Predicate))]
project = f.project(name="Project")
sections = [f.section(name="A", project=project)]


class TestSectionWorkflow(TestCase):
    def setUp(self) -> None:
        self.manager = _SectionWorkflowStageManager("Project", stages)

    def test_missing_project(self) -> None:
        warning = self.manager.get_current_stage(f.task(memberships=[]))
        self.assertEqual("Unable to find membership in 'Project'", warning)

    def test_missing_stage(self) -> None:
        stage, context = self.manager.get_current_stage(
            f.task(
                memberships=[
                    f.task_membership(project, f.section(name="C", project=project))
                ]
            )
        )
        expected_context = _SectionWorkflowGetStageContext(project)
        self.assertIsNone(stage)
        self.assertEqual(expected_context, context)

    def test_matching_section(self) -> None:
        stage, context = self.manager.get_current_stage(
            f.task(memberships=[f.task_membership(project, sections[0])])
        )
        expected_context = _SectionWorkflowGetStageContext(project)
        self.assertIs(stages[0], stage)
        self.assertEqual(expected_context, context)

    def test_can_set_stage_missing_section(self) -> None:
        client = create_autospec(Client)
        get_context = _SectionWorkflowGetStageContext(project)
        client.sections_by_project.return_value = sections
        warning = self.manager.can_set_stage(
            WorkflowStage("B", predicate), client, get_context
        )
        client.sections_by_project.assert_called_once_with(project)
        self.assertEqual("Unable to find section 'B' in 'Project'", warning)

    def test_can_set_stage_matching_section(self) -> None:
        client = create_autospec(Client)
        get_context = _SectionWorkflowGetStageContext(project)
        client.sections_by_project.return_value = sections
        set_context = self.manager.can_set_stage(
            WorkflowStage("A", predicate), client, get_context
        )
        expected_context = _SectionWorkflowSetStageContext(sections[0])
        client.sections_by_project.assert_called_once_with(project)
        self.assertEqual(expected_context, set_context)

    def test_set_stage(self) -> None:
        task = f.task()
        client = create_autospec(Client)
        context = _SectionWorkflowSetStageContext(sections[0])
        client.add_to_section.return_value = None
        self.manager.set_stage(task, client, context)
        client.add_to_section.assert_called_once_with(task, sections[0])

    def test_correct_manager(self) -> None:
        workflow = SectionWorkflow("name", [])
        self.assertIsInstance(workflow._stage_manager, _SectionWorkflowStageManager)
