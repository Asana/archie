import datetime
import types
from typing import Any, List, Optional, Union

TimeTypes = Optional[
    Union[
        str, datetime.date, datetime.timedelta, types.FunctionType, types.GeneratorType
    ]
]

def freeze_time(
    time_to_freeze: TimeTypes = None,
    tz_offset: int = 0,
    ignore: Optional[List[str]] = None,
    tick: bool = False,
    as_arg: bool = False,
    auto_tick_seconds: int = 0,
) -> Any: ...
