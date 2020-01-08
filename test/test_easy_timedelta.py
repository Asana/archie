import doctest
from datetime import timedelta
from unittest import TestCase, TestLoader, TestSuite

import archie._easy_timedelta
from archie._easy_timedelta import convert_timedelta


def load_tests(loader: TestLoader, tests: TestSuite, pattern: str) -> TestSuite:
    tests.addTests(doctest.DocTestSuite(archie._easy_timedelta))
    return tests


class TestEasyTimedelta(TestCase):
    def test_convert_string(self) -> None:
        for s, td in [
            ("1h", timedelta(hours=1)),
            ("4h", timedelta(hours=4)),
            ("24h", timedelta(days=1)),
            ("1d", timedelta(days=1)),
            ("3d", timedelta(days=3)),
            ("7d", timedelta(days=7)),
            ("1w", timedelta(days=7)),
            ("2w", timedelta(days=14)),
        ]:
            with self.subTest(string=s, timedelta=td):
                self.assertEqual(td, convert_timedelta(s))

    def test_convert_timedelta(self) -> None:
        td = timedelta(hours=1)
        self.assertIs(convert_timedelta(td), td)

    def test_unknown_base(self) -> None:
        with self.assertRaises(ValueError):
            convert_timedelta("1s")

    def test_unknown_mulitple(self) -> None:
        with self.assertRaises(ValueError):
            convert_timedelta("xm")
        with self.assertRaises(ValueError):
            convert_timedelta("m")
