from datetime import timedelta
from typing import Union

EasyTimedelta = Union[timedelta, str]


_UNIT_TO_TIMEDELTA = {
    "m": timedelta(minutes=1),
    "h": timedelta(hours=1),
    "d": timedelta(days=1),
    "w": timedelta(days=7),
}


def convert_timedelta(delta: EasyTimedelta) -> timedelta:
    """Convert strings representing time windows into true `timedelta`s

    >>> convert_timedelta("2h")
    datetime.timedelta(seconds=7200)
    >>> convert_timedelta("3w")
    datetime.timedelta(days=21)
    >>> convert_timedelta(timedelta(days=1))
    datetime.timedelta(days=1)
    """
    if isinstance(delta, timedelta):
        return delta
    multiple, unit = delta[:-1], delta[-1]
    base = _UNIT_TO_TIMEDELTA.get(unit)
    if base is None:
        raise ValueError(f"Unknown time unit: {unit}")
    return int(multiple) * base
