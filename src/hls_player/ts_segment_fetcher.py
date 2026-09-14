"""
This file contains the code to download the ts segments and to store them in a byte
"""

import queue
import collections
import requests
from concurrent.futures import ThreadPoolExecutor

from src.hls_player import Configs
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

        self._media_playlist_url = media_playlist_url
        self.downloaded_segment_que = queue.Queue()
        self._request_client = requests.Session()

    def _download_segments(self, segment: Segment) -> bytes:
        """
        This method is to download the ts segment and then return it as bytes

        :param segment: Segment object that needs to be downloaded
        :return: ts segments as bytes
        """

        # Resolving the absolute TS segment path
        segment_uri = segment.uri
        ts_segment_uri = resolve_url(self._media_playlist_url, segment_uri)

        logger.debug(
            f"Downloading segment with media seq number [{segment.sequence}] "
            f"and URL [{ts_segment_uri}]"
        )
        ts_seg = self._request_client.get(ts_segment_uri, timeout=5)
        ts_seg.raise_for_status()
        return ts_seg.content

    def _generate_downloaded_segment(self, segment: Segment) -> DownloadedSegment | None:
        """
        This method is to download the ts segments and then to return the DownloadedSegment object

        :param segment: Segment object that needs to be downloaded
        :return: DownloadedSegment object
        """

        try:
            downloaded_seg = self._download_segments(segment)
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
        and will push the downloaded segment in the decoded_queue. Downloads are done
        concurrently using a thread pool while preserving segment order.

        :param segment_que: PlaylistParser.seg_que
        :return: None
        """

        max_parallel_downloads = Configs.MAX_PARALLEL_DOWNLOADS
        logger.debug(f"Starting parallel segment downloads with window size [{max_parallel_downloads}].")

        with ThreadPoolExecutor(max_workers=max_parallel_downloads) as executor:
            pending = collections.deque()

            while True:
                segment = segment_que.get()
                if segment is None:
                    logger.debug("Received end-of-playlist signal. Draining remaining in-flight downloads.")
                    break

                logger.debug(f"Submitting segment [{segment.sequence}] for download.")
                pending.append(executor.submit(self._generate_downloaded_segment, segment))

                # Once the window is full, drain the oldest future to free a slot
                while len(pending) >= max_parallel_downloads:
                    result = pending.popleft().result()
                    if result:
                        logger.debug(f"Download complete for segment [{result.sequence}], pushing to queue.")
                        self.downloaded_segment_que.put(result)
                    else:
                        logger.warning("A segment was skipped (download returned None).")

            # Drain all remaining in-flight downloads after end-of-playlist
            logger.debug(f"Draining [{len(pending)}] remaining in-flight downloads.")
            for future in pending:
                result = future.result()
                if result:
                    logger.debug(f"Download complete for segment [{result.sequence}], pushing to queue.")
                    self.downloaded_segment_que.put(result)
                else:
                    logger.warning("A segment was skipped (download returned None).")

        self.downloaded_segment_que.put(None)
        logger.debug("All segments have been downloaded and pushed to the queue.")
