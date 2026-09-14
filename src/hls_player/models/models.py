"""
This class contains all the models / dataclasses required for HLS player
"""

from dataclasses import dataclass


@dataclass
class Rendition:
    uri: str
    bandwidth: int
    resolution: str
    codecs: str


@dataclass
class Segment:
    uri: str
    duration: float
    discontinuity: bool
    sequence: int
    program_date_time: datetime | None