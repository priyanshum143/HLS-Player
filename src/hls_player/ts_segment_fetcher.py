"""
This file contains the code to download the ts segments and to store them in a byte
"""

import queue
import requests

from src.hls_player.utils.string_utils import resolve_url
from src.hls_player.models.models import (
    Segment,
    DownloadedSegment,
)
from src.hls_player.utils.loggers import get_logger

logger = get_logger(__name__)


class TsSegmentsFetcher:
    """
    This class contains the code to download the ts segments and to store them in a byte
    """

    def __init__(self, media_playlist_url: str) -> None:
        """
        This is the constructor of the Fetcher class

        :param media_playlist_url: url of the media playlist
        """

        self.media_playlist_url = media_playlist_url
        self.downloaded_segment_que = queue.Queue()
        self.request_client = requests.Session()

    def download_segments(self, segment: Segment) -> bytes:
        """
        This method is to download the ts segment and then return it as bytes

        :param segment: Segment object that needs to be downloaded
        :return: ts segments as bytes
        """

        # Resolving the absolute TS segment path
        segment_uri = segment.uri
        ts_segment_uri = resolve_url(self.media_playlist_url, segment_uri)

        logger.debug(
            f"Downloading segment with media seq number [{segment.sequence}] "
            f"and URL [{ts_segment_uri}]"
        )
        ts_seg = self.request_client.get(ts_segment_uri, timeout=5)
        ts_seg.raise_for_status()
        return ts_seg.content

    def generate_downloaded_segment(self, segment: Segment) -> DownloadedSegment | None:
        """
        This method is to download the ts segments and then to return the DownloadedSegment object

        :param segment: Segment object that needs to be downloaded
        :return: DownloadedSegment object
        """

        try:
            downloaded_seg = self.download_segments(segment)
            return DownloadedSegment(
                sequence=segment.sequence,
                data=downloaded_seg,
                discontinuity=segment.discontinuity,
            )
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in (401, 403, 404):
                logger.error(f"Non-retryable HTTP {e.response.status_code} for {segment}, Skipping the segment.")
                return None

    def push_downloaded_segment_in_que(self, segment_que: queue.Queue) -> None:
        """
        This method will keep downloading the ts segments present in PlaylistParser.seg_que
        and will push the downloaded segment in the decoded_queue

        :param segment_que: PlaylistParser.seg_que
        :return: None
        """

        logger.info("Starting to pull segments from queue and download them.")
        while True:
            segment = segment_que.get()
            if segment is None:
                self.downloaded_segment_que.put(None)
                logger.info("All the segments have been downloaded.")
                break
            logger.debug(f"Got the segment: {segment} from segments queue.")

            downloaded_seg = self.generate_downloaded_segment(segment)
            if not downloaded_seg:
                continue
            logger.debug(f"Made the downloaded segment: {downloaded_seg.sequence}")

            self.downloaded_segment_que.put(downloaded_seg)
