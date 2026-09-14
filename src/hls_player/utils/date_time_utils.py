"""
This file will contain the utils related to date time
"""

from datetime import datetime, timezone, timedelta


def convert_float_timestamp_to_IST(ts: float) -> str:
    """
    This method will convert the given timestamp to IST format

    :param ts: timestamp
    :return: IST formatted timestamp
    """

    _IST = timezone(timedelta(hours=5, minutes=30))
    return datetime.fromtimestamp(ts, tz=_IST).strftime('%Y-%m-%d %H:%M:%S IST')
