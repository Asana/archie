import re
from pathlib import Path
from unittest import TestCase

from archie import __version__


class TestVersion(TestCase):
    def test(self) -> None:
        pyproject_path = Path(__file__).parents[1] / "pyproject.toml"
        with pyproject_path.open() as file:
            pyproject_toml = file.read()
        match = re.search('^version = "(.*)"$', pyproject_toml, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertTupleEqual(match.groups(), (__version__,))  # type: ignore
