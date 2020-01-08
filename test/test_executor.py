from logging import Logger
from unittest import TestCase
from unittest.mock import Mock, create_autospec

from archie._executor import LoggingThreadPoolExecutor


class TestLoggingThreadPoolExecutor(TestCase):
    def setUp(self) -> None:
        self.logger = create_autospec(Logger)
        self.callable = Mock()
        self.executor = LoggingThreadPoolExecutor(self.logger)

    def test_success(self) -> None:
        self.callable.return_value = sentinel = object()
        with self.executor as e:
            future = e.submit(self.callable, 1, key="value")
        self.callable.assert_called_once_with(1, key="value")

        self.logger.error.assert_not_called()
        self.assertIs(future.result(), sentinel)

    def test_failure(self) -> None:
        self.callable.side_effect = sentinel = RuntimeError()
        with self.executor as e:
            future = e.submit(self.callable, 1, key="value")
        self.executor.shutdown()
        self.callable.assert_called_once_with(1, key="value")

        self.logger.error.assert_called_once_with(
            "Exception encountered in thread", exc_info=True
        )
        self.assertIs(future.exception(), sentinel)
