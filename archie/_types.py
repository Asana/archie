from typing import Any, List, Optional, Tuple, Type, TypeVar

from typing_extensions import Protocol

_T = TypeVar("_T")
_S = TypeVar("_S")

_C = TypeVar("_C", bound="Comparable")


class Comparable(Protocol):
    def __eq__(self, other: Any) -> bool:
        ...

    def __lt__(self: _C, other: _C) -> bool:
        ...

    def __gt__(self: _C, other: _C) -> bool:
        ...

    def __le__(self: _C, other: _C) -> bool:
        ...

    def __ge__(self: _C, other: _C) -> bool:
        ...


class HasName(Protocol):
    @property
    def name(self) -> str:
        ...


def partition_by_type(seq: List[_T], cls: Type[_S]) -> Tuple[List[_S], List[_T]]:
    """Partition a list into two by extracting those of a given type

    >>> partition_by_type([1, "1", 2, "2"], str)
    (['1', '2'], [1, 2])
    """
    matching = [i for i in seq if isinstance(i, cls)]
    rest = [i for i in seq if not isinstance(i, cls)]
    return matching, rest


def innermost_type(cls: Optional[Type]) -> Type:
    """Return the innermost type from a potentially nested type.

    >>> innermost_type(str)
    <class 'str'>
    >>> innermost_type(List[str])
    <class 'str'>
    >>> innermost_type(Optional[List[str]])
    <class 'str'>
    >>> innermost_type(None)
    <class 'NoneType'>
    """
    if cls is None:
        return type(None)
    inner = cls
    while getattr(inner, "__args__", None):
        inner = inner.__args__[0]
    return inner


def optional_to_list(option: Optional[_T]) -> List[_T]:
    """Coerces an optional value into a list of one or zero elements.

    >>> optional_to_list("a")
    ['a']
    >>> optional_to_list(None)
    []
    """
    if option is not None:
        return [option]
    return []
