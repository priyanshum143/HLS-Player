"""
This class contains all the models / dataclasses required for HLS player
"""

import numpy as np
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
    program_date_time: str | None


@dataclass
class DownloadedSegment:
    sequence: int
    data: bytes
    discontinuity: bool


@dataclass
class VideoPacket:
    rgb_array: np.ndarray
    pts: float

@dataclass
class AudioPacket:
    pcm: np.ndarray
    pts: float
    sample_rate: int