from typing import Callable, Iterable, Optional, TypeVar

from archie._types import HasName

_T = TypeVar("_T")


def first_or_none(iterable: Iterable[_T]) -> Optional[_T]:
    """Returns the first value in the iterable or ``None``.

    >>> first_or_none([1, 2, 3])
    1
    >>> first_or_none([])
    """
    iterator = iter(iterable)
    return next(iterator, None)


def find(iterable: Iterable[_T], predicate: Callable[[_T], bool]) -> Optional[_T]:
    """Returns the first value in the iterable matching a predicate or ``None``.

    >>> find([1, 2, 3], lambda x: x > 1)
    2
    >>> find([1, 2, 3], lambda x: x > 3)
    """
    filtered = filter(predicate, iterable)
    return first_or_none(filtered)


_S = TypeVar("_S", bound=HasName)


def find_by_name(iterable: Iterable[_S], name: str) -> Optional[_S]:
    """Returns the first item with a matching ``name`` attribute.

    >>> from collections import namedtuple
    >>> Named = namedtuple("Named", ["name"])
    >>> items = [Named("First"), Named("Second")]
    >>> find_by_name(items, "Second")
    Named(name='Second')
    >>> find_by_name(items, "Third")
    """
    return find(iterable, lambda item: item.name == name)
