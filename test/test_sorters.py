from datetime import date
from test import fixtures as f
from typing import List, Optional, Tuple
from unittest import TestCase
from unittest.mock import Mock, create_autospec

from archie.asana.models import CustomField, Task
from archie.sorters import (
    AssigneeSorter,
    DueDateSorter,
    EnumCustomFieldSorter,
    LikeSorter,
    NumberCustomFieldSorter,
    Sorter,
    StartDateSorter,
    _Merged,
)


class TestMerged(TestCase):
    task = f.task()

    @staticmethod
    def make_sorters(n: int) -> List[Mock]:
        def sorter_with_key(key: int) -> Mock:
            sorter = create_autospec(Sorter)
            sorter.key.return_value = (key,)
            return sorter

        return list(map(sorter_with_key, range(n)))

    def test_two(self) -> None:
        first, second = self.make_sorters(2)
        sorter = _Merged(first, second)
        key: Tuple[int, ...] = sorter.key(self.task)
        self.assertTupleEqual(key, (0, 1))
        first.key.assert_called_once_with(self.task)
        second.key.assert_called_once_with(self.task)

    def test_three(self) -> None:
        first, second, third = self.make_sorters(3)
        sorter = _Merged(third, _Merged(first, second))
        key: Tuple[int, ...] = sorter.key(self.task)
        self.assertTupleEqual(key, (2, 0, 1))
        first.key.assert_called_once_with(self.task)
        second.key.assert_called_once_with(self.task)
        third.key.assert_called_once_with(self.task)

    def test_and_then(self) -> None:
        class DummySorter(Sorter):
            def key(self, task: Task) -> Tuple[int, ...]:
                return (0,)

        first, second = DummySorter(), DummySorter()
        merged = first.and_then(second)
        self.assertIsInstance(merged, _Merged)
        self.assertIs(merged.first, first)  # type: ignore
        self.assertIs(merged.second, second)  # type: ignore


class TestLikeSorter(TestCase):
    tasks = [
        f.task(gid="1", num_likes=2),
        f.task(gid="2", num_likes=1),
        f.task(gid="3", num_likes=4),
        f.task(gid="4", num_likes=3),
    ]

    def test(self) -> None:
        sorter = LikeSorter()
        sorted_tasks = sorter.sort(self.tasks)
        ids = [t.gid for t in sorted_tasks]
        self.assertListEqual(ids, ["3", "4", "1", "2"])

    def test_ascending(self) -> None:
        sorter = LikeSorter(ascending=True)
        sorted_tasks = sorter.sort(self.tasks)
        ids = [t.gid for t in sorted_tasks]
        self.assertListEqual(ids, ["2", "1", "4", "3"])


class TestDueDateSorter(TestCase):
    tasks = [
        f.task(gid="1", due_on=date(2019, 1, 2)),
        f.task(gid="2", due_on=date(2019, 1, 1)),
        f.task(gid="3", due_on=None),
        f.task(gid="4", due_on=date(2019, 1, 3)),
    ]

    def test_ascending_missing_last(self) -> None:
        sorter = DueDateSorter()
        sorted_tasks = sorter.sort(self.tasks)
        ids = [t.gid for t in sorted_tasks]
        self.assertListEqual(ids, ["2", "1", "4", "3"])

    def test_descending(self) -> None:
        sorter = DueDateSorter(ascending=False)
        sorted_tasks = sorter.sort(self.tasks)
        ids = [t.gid for t in sorted_tasks]
        self.assertListEqual(ids, ["4", "1", "2", "3"])

    def test_missing_first(self) -> None:
        sorter = DueDateSorter(missing_first=True)
        sorted_tasks = sorter.sort(self.tasks)
        ids = [t.gid for t in sorted_tasks]
        self.assertListEqual(ids, ["3", "2", "1", "4"])


class TestStartDateSorter(TestCase):
    tasks = [
        f.task(gid="1", start_on=date(2019, 1, 2)),
        f.task(gid="2", start_on=date(2019, 1, 1)),
        f.task(gid="3", start_on=None),
        f.task(gid="4", start_on=date(2019, 1, 3)),
    ]

    def test_ascending_missing_last(self) -> None:
        sorter = StartDateSorter()
        sorted_tasks = sorter.sort(self.tasks)
        ids = [t.gid for t in sorted_tasks]
        self.assertListEqual(ids, ["2", "1", "4", "3"])

    def test_descending(self) -> None:
        sorter = StartDateSorter(ascending=False)
        sorted_tasks = sorter.sort(self.tasks)
        ids = [t.gid for t in sorted_tasks]
        self.assertListEqual(ids, ["4", "1", "2", "3"])

    def test_missing_first(self) -> None:
        sorter = StartDateSorter(missing_first=True)
        sorted_tasks = sorter.sort(self.tasks)
        ids = [t.gid for t in sorted_tasks]
        self.assertListEqual(ids, ["3", "2", "1", "4"])


class TestAssigneeSorter(TestCase):
    def test(self) -> None:
        tasks = [
            f.task(gid="6", assignee=f.user(name="Other user")),
            f.task(gid="1", assignee=f.user(name="A")),
            f.task(gid="2", assignee=f.user(name="B")),
            f.task(gid="3", assignee=f.user(name="C")),
            f.task(gid="4", assignee=f.user(name="D")),
            f.task(gid="5", assignee=None),
        ]

        sorter = AssigneeSorter(["B", None, "D", "C", "A"])
        sorted_tasks = sorter.sort(tasks)
        ids = [t.gid for t in sorted_tasks]
        self.assertListEqual(ids, ["2", "5", "4", "3", "1", "6"])


class TestEnumCustomFieldSorter(TestCase):
    sorter = EnumCustomFieldSorter("My custom field", ["B", None, "D", "C", "A"])

    @staticmethod
    def custom_field(value: str) -> CustomField:
        return f.custom_field(
            name="My custom field", enum_value=f.enum_option(name=value)
        )

    def test_normal(self) -> None:
        tasks = [
            f.task(gid="1", custom_fields=[self.custom_field("A")]),
            f.task(gid="2", custom_fields=[self.custom_field("B")]),
            f.task(gid="3", custom_fields=[self.custom_field("C")]),
            f.task(gid="4", custom_fields=[self.custom_field("D")]),
        ]

        sorted_tasks = self.sorter.sort(tasks)
        ids = [t.gid for t in sorted_tasks]
        self.assertListEqual(ids, ["2", "4", "3", "1"])

    def test_missing_custom_field(self) -> None:
        tasks = [
            f.task(gid="1", custom_fields=[f.custom_field(name="Other custom field")]),
            f.task(gid="2", custom_fields=[self.custom_field("A")]),
        ]

        sorted_tasks = self.sorter.sort(tasks)
        ids = [t.gid for t in sorted_tasks]
        self.assertListEqual(ids, ["2", "1"])

    def test_missing_enum_option(self) -> None:
        tasks = [
            f.task(gid="1", custom_fields=[self.custom_field("Z")]),
            f.task(gid="2", custom_fields=[self.custom_field("A")]),
        ]

        sorted_tasks = self.sorter.sort(tasks)
        ids = [t.gid for t in sorted_tasks]
        self.assertListEqual(ids, ["2", "1"])

    def test_unset_enum_option(self) -> None:
        tasks = [
            f.task(
                gid="1",
                custom_fields=[f.custom_field(name="My custom field", enum_value=None)],
            ),
            f.task(gid="2", custom_fields=[self.custom_field("B")]),
        ]

        sorted_tasks = self.sorter.sort(tasks)
        ids = [t.gid for t in sorted_tasks]
        self.assertListEqual(ids, ["2", "1"])


class TestNumberCustomFieldSorter(TestCase):
    sorter = NumberCustomFieldSorter("My custom field")

    @staticmethod
    def custom_field(value: Optional[float]) -> CustomField:
        return f.custom_field(name="My custom field", number_value=value)

    def test_ascending(self) -> None:
        tasks = [
            f.task(gid="1", custom_fields=[self.custom_field(5)]),
            f.task(gid="2", custom_fields=[self.custom_field(9)]),
            f.task(gid="3", custom_fields=[self.custom_field(1)]),
            f.task(gid="4", custom_fields=[self.custom_field(2)]),
        ]

        sorted_tasks = self.sorter.sort(tasks)
        ids = [t.gid for t in sorted_tasks]
        self.assertListEqual(ids, ["3", "4", "1", "2"])

    def test_descending(self) -> None:
        sorter = NumberCustomFieldSorter("My custom field", ascending=False)
        tasks = [
            f.task(gid="1", custom_fields=[self.custom_field(5)]),
            f.task(gid="2", custom_fields=[self.custom_field(9)]),
            f.task(gid="3", custom_fields=[self.custom_field(1)]),
            f.task(gid="4", custom_fields=[self.custom_field(2)]),
        ]

        sorted_tasks = sorter.sort(tasks)
        ids = [t.gid for t in sorted_tasks]
        self.assertListEqual(ids, ["2", "1", "4", "3"])

    def test_missing_custom_field(self) -> None:
        tasks = [
            f.task(gid="1", custom_fields=[f.custom_field(name="Other custom field")]),
            f.task(gid="2", custom_fields=[self.custom_field(3)]),
        ]

        sorted_tasks = self.sorter.sort(tasks)
        ids = [t.gid for t in sorted_tasks]
        self.assertListEqual(ids, ["2", "1"])

    def test_unset_number_value(self) -> None:
        tasks = [
            f.task(gid="1", custom_fields=[self.custom_field(None)]),
            f.task(gid="2", custom_fields=[self.custom_field(0)]),
        ]

        sorted_tasks = self.sorter.sort(tasks)
        ids = [t.gid for t in sorted_tasks]
        self.assertListEqual(ids, ["2", "1"])
