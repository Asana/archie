import logging
from concurrent.futures import Future, ThreadPoolExecutor
from typing import Any, Callable, Optional


class LoggingThreadPoolExecutor(ThreadPoolExecutor):
    """A thread pool executor that logs exceptions in threads.

    The thread pool executor from the standard library does not automatically surface
    errors encountered in its threads. This executor will log any error encountered with
    the given logger.

    :param logger: The logger to use to surface errors.
    :param args: Arguments to pass to the parent class.
    :param kwargs: Keyword arguments to pass to the parent class.
    """

    def __init__(
        self, logger: Optional[logging.Logger] = None, *args: Any, **kwargs: Any
    ) -> None:
        self._logger = logger or logging.getLogger(__name__)
        super().__init__(*args, **kwargs)

    def submit(self, fn: Callable, *args: Any, **kwargs: Any) -> Future:
        future = super().submit(fn, *args, **kwargs)
        future.add_done_callback(self._log_failure)
        return future

    def _log_failure(self, future: Future) -> None:
        try:
            future.result()
        except Exception:
            self._logger.error("Exception encountered in thread", exc_info=True)
