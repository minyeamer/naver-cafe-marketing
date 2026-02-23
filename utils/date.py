from __future__ import annotations

from typing import Literal
import datetime as dt
import re


def cur_time() -> dt.datetime:
    return dt.datetime.now()


def cur_time_str() -> str:
    return cur_time().strftime("%Y-%m-%dT%H:%M:%S") + "+09:00"


def to_iso_date(text: str, default: dt.datetime | Literal[":now:"] | None = ":now:") -> dt.datetime:
    try:
        if (match := re.search(r"(\d{4}\.\d{2}\.\d{2}\.)", text)):
            return dt.datetime.strptime(match.group(1), "%Y.%m.%d.")
        elif (match := re.search(r"(\d{2}:\d{2})", text)):
            hour, minute = match.group(1).split(':')
            return dt.datetime(*dt.datetime.today().timetuple()[:3], int(hour), int(minute))
    except:
        pass
    return cur_time() if default == ":now:" else default


def to_iso_date_str(text: str, default: str | None = None) -> str:
    try:
        if isinstance((datetime := to_iso_date(text, default=None)), dt.datetime):
            return datetime.strftime("%Y-%m-%d") + "T00:00:00+09:00"
    except:
        pass
    return cur_time_str() if default is None else default


def to_iso_datetime(text: str, default: dt.datetime | Literal[":now:"] | None = ":now:") -> dt.datetime:
    try:
        if (match := re.search(r"(\d{4}\.\d{2}\.\d{2}\. \d{2}:\d{2})", text)):
            return dt.datetime.strptime(match.group(1), "%Y.%m.%d. %H:%M")
        elif (match := re.search(r"(\d{2}:\d{2})", text)):
            hour, minute = match.group(1).split(':')
            return dt.datetime(*dt.datetime.today().timetuple()[:3], int(hour), int(minute))
    except:
        pass
    return cur_time() if default == ":now:" else default


def to_iso_datetime_str(text: str, default: str | None = None) -> str:
    try:
        if isinstance((datetime := to_iso_datetime(text, default=None)), dt.datetime):
            return datetime.strftime("%Y-%m-%dT%H:%M") + ":00+09:00"
    except:
        pass
    return cur_time_str() if default is None else default



    if (match := re.search(r"(\d{4}\.\d{2}\.\d{2}\. \d{2}:\d{2})", text)):
        try:
            datetime = dt.datetime.strptime(match.group(1), "%Y.%m.%d. %H:%M")
            return datetime.strftime("%Y-%m-%dT%H:%M") + ":00+09:00"
        except:
            return cur_time_str() if default is None else default
    else:
        return cur_time_str() if default is None else default
