import doctest
from collections import namedtuple
from unittest import TestCase, TestLoader, TestSuite

import archie._itertools
from archie._itertools import find, find_by_name, first_or_none


def load_tests(loader: TestLoader, tests: TestSuite, pattern: str) -> TestSuite:
    tests.addTests(doctest.DocTestSuite(archie._itertools))
    return tests


class TestFirstOrNone(TestCase):
    def test_empty(self) -> None:
        first = first_or_none([1, 2, 3])
        self.assertEqual(1, first)

    def test_nonempty(self) -> None:
        none = first_or_none([])
        self.assertIsNone(none)


class TestFind(TestCase):
    def test_find_some(self) -> None:
        found = find([1, 2, 3], lambda x: x % 2 == 0)
        self.assertEqual(2, found)

    def test_find_none(self) -> None:
        found = find(["a", "b", "c"], lambda x: x.startswith("d"))
        self.assertIsNone(found)


class TestFindByName(TestCase):
    Named = namedtuple("Named", ["name"])
    items = _, second = [Named("First"), Named("Second")]

    def test_find_some(self) -> None:
        found = find_by_name(self.items, "Second")
        self.assertIs(found, self.second)

    def test_find_none(self) -> None:
        found = find_by_name(self.items, "Third")
        self.assertIsNone(found)
