from __future__ import annotations

import datetime as dt
import time

from typing import TypeVar, TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any, Hashable
    _KT = TypeVar("_KT", Hashable)
    _VT = TypeVar("_VT", Any)


class ActionTimer(dict):

    def start_timer(self, key: _KT):
        self.update({key: time.time()})

    def end_timer(self, key: _KT, ndigits: int | None = None) -> float | None:
        try:
            return self.get_elapsed_time(key, ndigits)
        finally:
            self.pop(key, None)

    def set_timer(self, key: _KT, value: _VT):
        if isinstance(value, dt.datetime):
            value = value.timestamp()
        if isinstance(value, (float,int)):
            self.update({key: value})

    def get_elapsed_time(self, key: _KT, ndigits: int | None = None) -> float | None:
        if key in self:
            elapsed_time = time.time() - self[key]
            return round(elapsed_time, ndigits) if isinstance(ndigits, int) else elapsed_time
        else:
            return None

    def get_all_elapsed_times(self, ndigits: int | None = None) -> dict[_KT, float]:
        round_n = (lambda x: round(x, ndigits)) if isinstance(ndigits, int) else (lambda x: x)
        return {key: round_n(time.time() - start_time) for key, start_time in self.items()}

    def gte(self, key: _KT, value: float) -> bool:
        if (key in self) and isinstance(value, (float,int)):
            return (time.time() - self[key]) >= value
        else:
            return True
