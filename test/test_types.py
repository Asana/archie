import doctest
from typing import List, Optional
from unittest import TestCase, TestLoader, TestSuite

import archie._types
from archie._types import innermost_type, optional_to_list, partition_by_type


def load_tests(loader: TestLoader, tests: TestSuite, pattern: str) -> TestSuite:
    tests.addTests(doctest.DocTestSuite(archie._types))
    return tests


class TestTypes(TestCase):
    def test_partition_by_type(self) -> None:
        mixture = [1, "1", (1,), 2, "2", (2,)]
        matching, rest = partition_by_type(mixture, str)
        self.assertListEqual(matching, ["1", "2"])
        self.assertListEqual(rest, [1, (1,), 2, (2,)])

    def test_innermost_type(self) -> None:
        for full_type, inner_type in [
            (str, str),
            (List[str], str),
            (Optional[List[str]], str),
            (None, type(None)),
        ]:
            with self.subTest(full_type=full_type, inner_type=inner_type):
                self.assertIs(innermost_type(full_type), inner_type)

    def test_option_to_list(self) -> None:
        self.assertListEqual(optional_to_list("a"), ["a"])
        self.assertListEqual(optional_to_list(None), [])
