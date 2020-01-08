from datetime import datetime, timedelta
from test import fixtures as f
from typing import Iterator
from unittest import TestCase
from unittest.mock import create_autospec, patch

from freezegun import freeze_time

from archie.asana.client import Client
from archie.asana.models import Task
from archie.sources import ModifiedSinceSource, PollingSource, TaskSource


class TestPollingSource(TestCase):
    def setUp(self) -> None:
        self.client = create_autospec(Client)
        self.project = f.project()
        self.client.project_by_gid.return_value = self.project

    def check_first_poll(
        self, source: TaskSource, only_incomplete: bool
    ) -> Iterator[Task]:
        iterator = source.iterator(self.client)
        self.client.tasks_by_project.return_value = task1, task2 = [
            f.task(gid="1"),
            f.task(gid="2"),
        ]
        self.client.tasks_by_project.assert_not_called()
        self.assertIs(next(iterator), task1)
        self.client.tasks_by_project.assert_called_once_with(
            self.project, only_incomplete=only_incomplete
        )
        self.assertIs(next(iterator), task2)
        return iterator

    def test_no_repeat(self) -> None:
        source = PollingSource(self.project.gid, repeat_after=None)
        iterator = self.check_first_poll(source, only_incomplete=True)
        with self.assertRaises(StopIteration):
            next(iterator)

    def test_include_complete(self) -> None:
        source = PollingSource(self.project.gid, only_incomplete=False)
        iterator = self.check_first_poll(source, only_incomplete=False)
        with self.assertRaises(StopIteration):
            next(iterator)

    def test_repeat(self) -> None:
        source = PollingSource(self.project.gid, repeat_after="0m")
        iterator = self.check_first_poll(source, only_incomplete=True)

        self.client.tasks_by_project.reset_mock()
        self.client.tasks_by_project.return_value = task3, task4 = [
            f.task(gid="3"),
            f.task(gid="4"),
        ]
        self.assertIs(next(iterator), task3)
        self.client.tasks_by_project.assert_called_once_with(
            self.project, only_incomplete=True
        )
        self.assertIs(next(iterator), task4)


class TestModifiedSinceSource(TestCase):
    def setUp(self) -> None:
        self.client = create_autospec(Client)
        self.project = f.project()
        self.client.project_by_gid.return_value = self.project

    @patch("archie.sources.ModifiedSinceSource.POLLING_DELAY", timedelta())
    @freeze_time(datetime(2019, 1, 1, 12, 0, 0), auto_tick_seconds=60)
    def test(self) -> None:
        source = ModifiedSinceSource(self.project.gid)
        self.client.tasks_by_project.return_value = task1, task2 = [
            f.task(gid="1"),
            f.task(gid="2"),
        ]
        iterator = source.iterator(self.client)
        self.client.tasks_by_project.assert_not_called()
        self.assertIs(next(iterator), task1)
        self.client.tasks_by_project.assert_called_once_with(
            self.project,
            only_incomplete=False,
            modified_since=datetime(2019, 1, 1, 12, 0, 0),
        )
        self.assertIs(next(iterator), task2)

        self.client.tasks_by_project.reset_mock()
        self.client.tasks_by_project.return_value = task3, task4 = [
            f.task(gid="3"),
            f.task(gid="4"),
        ]
        self.assertIs(next(iterator), task3)
        self.client.tasks_by_project.assert_called_once_with(
            self.project,
            only_incomplete=False,
            modified_since=datetime(2019, 1, 1, 12, 1, 0),
        )
        self.assertIs(next(iterator), task4)
