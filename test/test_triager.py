import logging
from test import fixtures as f
from typing import List
from unittest import TestCase
from unittest.mock import Mock, call, create_autospec, patch

from archie import Triager
from archie.actions import Action
from archie.asana.client import Client
from archie.asana.models import Task
from archie.predicates import Predicate
from archie.sorters import Sorter
from archie.sources import TaskSource


class TestWithTriager(TestCase):
    @patch("archie.triager.Client")
    def setUp(self, client_mock: Mock) -> None:
        self.client = client_mock.return_value = create_autospec(Client)
        self.project = self.client.project_by_gid.return_value = f.project()
        self.task_source = create_autospec(TaskSource)
        self.task_source.project_gid = self.project.gid
        self.triager = Triager("access_token", self.task_source)


class TestTriager(TestWithTriager):
    def test_generate_moves(self) -> None:
        tasks = [f.task(str(i)) for i in range(5)]
        index_and_tasks = [
            (3, tasks[3]),
            (2, tasks[2]),
            (4, tasks[4]),
            (0, tasks[0]),
            (1, tasks[1]),
        ]
        result = Triager._generate_moves(index_and_tasks)
        self.assertListEqual(
            result,
            [
                (tasks[2], "before", tasks[3]),
                (tasks[0], "before", tasks[2]),
                (tasks[1], "after", tasks[0]),
            ],
        )

    def test_triage_task(self) -> None:
        pass


class TestSorting(TestWithTriager):
    def setUp(self) -> None:
        super().setUp()
        self.section = f.section(gid="2", name="Section 2")
        self.client.sections_by_project.return_value = [
            f.section(gid="1", name="Section 1"),
            self.section,
            f.section(gid="3", name="Section 3"),
        ]

    def test_sort_section(self) -> None:
        sorter = create_autospec(Sorter)
        self.triager.order("Section 2", sorter)
        self.client.tasks_by_section.return_value = tasks = [
            f.task(gid="1"),
            f.task(gid="2"),
        ]
        sorter.sort.return_value = tasks[::-1]
        self.triager.sort()
        self.client.tasks_by_section.assert_called_once_with(self.section)
        sorter.sort.assert_called_once_with(tasks)
        self.client.reorder_in_project.assert_called_once_with(
            tasks[1], self.project, tasks[0], "before"
        )

    def test_missing_section(self) -> None:
        sorter = create_autospec(Sorter)
        logger = logging.getLogger("archie.triager")
        with self.assertLogs(logger, logging.WARNING) as logs:
            self.triager.order("Unknown section", sorter)
        self.assertListEqual(
            logs.output,
            [
                "WARNING:archie.triager:Project(project-gid) "
                "has no section 'Unknown section'"
            ],
        )

    def test_duplicated_section(self) -> None:
        sorter = create_autospec(Sorter)
        self.triager.order("Section 2", sorter)
        logger = logging.getLogger("archie.triager")
        with self.assertLogs(logger, logging.WARNING) as logs:
            self.triager.order("Section 2", sorter)
        self.assertListEqual(
            logs.output,
            ["WARNING:archie.triager:Sorter already defined for Section(2)"],
        )


class TestTriaging(TestWithTriager):
    def setUp(self) -> None:
        super().setUp()
        self.task_source.iterator.return_value = (self.task,) = [f.task(gid="1")]
        self.predicate = create_autospec(Predicate, return_value=True)
        self.action = create_autospec(Action)

    def sample_rule(self, task: Task) -> List[Action]:
        return [self.action]

    def test_rule(self) -> None:
        self.triager.when(self.predicate)(self.sample_rule)

        self.triager.triage()
        self.predicate.assert_called_once_with(self.task, self.client)
        self.action.assert_called_once_with(self.task, self.client)

    def test_ignore(self) -> None:
        ignore_predicate = create_autospec(Predicate, return_value=True)
        self.triager.ignore(ignore_predicate)
        self.triager.when(self.predicate)(self.sample_rule)

        self.triager.triage()
        ignore_predicate.assert_called_once_with(self.task, self.client)
        self.predicate.assert_not_called()
        self.action.assert_not_called()


class TestWorkflow(TestWithTriager):
    def test_workflow(self) -> None:
        self.task_source.iterator.return_value = task1, task2 = [
            f.task(gid="1"),
            f.task(gid="2"),
        ]
        workflow = Mock()
        self.triager.apply(workflow)
        workflow.assert_has_calls(
            [call(task1, self.client), call(task2, self.client)], any_order=True
        )
