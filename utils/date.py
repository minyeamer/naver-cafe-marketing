from __future__ import annotations

import datetime as dt
import re


def cur_time() -> dt.datetime:
    return dt.datetime.now()


def cur_time_str() -> str:
    return dt.datetime.now().strftime("%Y-%m-%dT%H:%M:%S") + "+09:00"


def to_iso_date(text: str, default: dt.datetime | None = None) -> dt.datetime:
    if (match := re.search(r"(\d{4}\.\d{2}\.\d{2}\.)", text)):
        try:
            return dt.datetime.strptime(match.group(1), "%Y.%m.%d.")
        except:
            return cur_time() if default is None else default
    else:
        return cur_time() if default is None else default


def to_iso_date_str(text: str, default: str | None = None) -> str:
    if (match := re.search(r"(\d{4}\.\d{2}\.\d{2}\.)", text)):
        try:
            datetime = dt.datetime.strptime(match.group(1), "%Y.%m.%d.")
            return datetime.strftime("%Y-%m-%d") + "T00:00:00+09:00"
        except:
            return cur_time_str() if default is None else default
    else:
        return cur_time_str() if default is None else default


def to_iso_datetime(text: str, default: dt.datetime | None = None) -> dt.datetime:
    if (match := re.search(r"(\d{4}\.\d{2}\.\d{2}\. \d{2}:\d{2})", text)):
        try:
            return dt.datetime.strptime(match.group(1), "%Y.%m.%d. %H:%M")
        except:
            return cur_time() if default is None else default
    else:
        return cur_time() if default is None else default


def to_iso_datetime_str(text: str, default: str | None = None) -> str:
    if (match := re.search(r"(\d{4}\.\d{2}\.\d{2}\. \d{2}:\d{2})", text)):
        try:
            datetime = dt.datetime.strptime(match.group(1), "%Y.%m.%d. %H:%M")
            return datetime.strftime("%Y-%m-%dT%H:%M") + ":00+09:00"
        except:
            return cur_time_str() if default is None else default
    else:
        return cur_time_str() if default is None else default
