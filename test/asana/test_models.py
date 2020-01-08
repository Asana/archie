from datetime import date, datetime
from typing import List
from unittest import TestCase

from archie.asana.models import (
    Event,
    External,
    Project,
    Story,
    Task,
    _structure_date,
    _structure_datetime,
    _unstructure_date,
    _unstructure_datetime,
)


class TestConverter(TestCase):
    def test_structure_date(self) -> None:
        structured_date = _structure_date("2019-01-02", date)
        self.assertEqual(structured_date, date(2019, 1, 2))

    def test_enstructure_date(self) -> None:
        unstructured_date = _unstructure_date(date(2019, 1, 2))
        self.assertEqual(unstructured_date, "2019-01-02")

    def test_structure_datetime(self) -> None:
        structured_datetime = _structure_datetime("2019-01-02T12:34:56.789Z", datetime)
        self.assertEqual(structured_datetime, datetime(2019, 1, 2, 12, 34, 56, 789000))

    def test_enstructure_datetime(self) -> None:
        unstructured_datetime = _unstructure_datetime(
            datetime(2019, 1, 2, 12, 34, 56, 789000)
        )
        self.assertEqual(unstructured_datetime, "2019-01-02T12:34:56.789Z")


class TestEvents(TestCase):
    @staticmethod
    def filter_and_strip_prefix(prefix: str, fields: List[str]) -> List[str]:
        prefix = prefix + "."
        prefix_len = len(prefix)
        return [f[prefix_len:] for f in fields if f.startswith(prefix)]

    def test_resource_fields(self) -> None:
        fields = Event.fields()
        resource_fields = set(self.filter_and_strip_prefix("resource", fields))
        expected_fields = set(Task.fields()) | set(Story.fields())
        self.assertSetEqual(expected_fields, resource_fields)

    def test_parent_fields(self) -> None:
        fields = Event.fields()
        resource_fields = set(self.filter_and_strip_prefix("parent", fields))
        expected_fields = set(Project.fields()) | set(Task.fields())
        self.assertSetEqual(expected_fields, resource_fields)


class TestExternal(TestCase):
    def test_json(self) -> None:
        serialized_data = """
        {
            "string": "abc",
            "integer": 1,
            "float": 2.3,
            "array": [1,2,3],
            "object": {"key": "value"}
        }
        """
        external = External.from_dict({"data": serialized_data})
        expected = {
            "string": "abc",
            "integer": 1,
            "float": 2.3,
            "array": [1, 2, 3],
            "object": {"key": "value"},
        }
        self.assertIsNotNone(external.data)
        self.assertDictEqual(external.data, expected)  # type: ignore

    def test_none(self) -> None:
        external = External.from_dict({})
        self.assertDictEqual(external.data, {})  # type: ignore

    def test_missing(self) -> None:
        external = External.from_dict({"data": None})
        self.assertDictEqual(external.data, {})  # type: ignore

    def test_unstructure(self) -> None:
        external = External(gid=None, data={})
        self.assertDictEqual(external.to_dict(), {"gid": None, "data": "{}"})
