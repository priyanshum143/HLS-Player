"""
This file will contain the utils related to date time
"""

from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo


def convert_float_timestamp_to_IST(ts: float) -> str:
    """
    This method will convert the given timestamp to IST format

    :param ts: timestamp
    :return: IST formatted timestamp
    """

    _IST = timezone(timedelta(hours=5, minutes=30))
    return datetime.fromtimestamp(ts, tz=_IST).strftime('%Y-%m-%d %H:%M:%S IST')


def convert_datetime_to_timezone(dt: datetime, tz: str) -> str | None:
    """
    Converts a datetime object to the given timezone.

    :param dt: datetime object to convert
    :param tz: timezone string, defaults to IST
    :return: timezone-aware datetime or None
    """

    if dt is None:
        return None
    converted = dt.astimezone(ZoneInfo(tz))
    tz_abbr = converted.strftime("%Z")
    return converted.strftime(f"%Y-%m-%d %H:%M:%S {tz_abbr}")
