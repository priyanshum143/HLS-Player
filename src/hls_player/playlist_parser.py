"""
This file contains the methods and code to fetch and parse the playlist
"""

import time
import urllib.error
import m3u8
import queue

from src.hls_player import Configs
from src.hls_player.models.models import (
    Segment,
    Rendition,
)
from src.hls_player.utils.loggers import get_logger
from src.hls_player.utils.date_time_utils import convert_float_timestamp_to_IST

logger = get_logger(__name__)


class PlaylistFetcher:
    """
    This class is used to fetch playlist and push the segments into queue
    """

    def __init__(self, master_playlist_url: str) -> None:
        """
        This is constructor for PlaylistFetcher

        :param master_playlist_url: master playlist url
        """

        self.master_playlist_url = master_playlist_url
        self.seg_que = queue.Queue()

    @staticmethod
    def fetch_m3u8_playlist(m3u8_url: str) -> m3u8.M3U8:
        """
        This method will load the m3u8 URL as m3u8 playlist and will return the same.

        :param m3u8_url: m3u8 url to fetch
        :return: m3u8 Playlist
        """

        try:
            return m3u8.load(m3u8_url, headers={
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            })
        except urllib.error.HTTPError as e:
            logger.error(f"HTTP {e.code} fetching playlist: {m3u8_url}")
            raise
        except urllib.error.URLError as e:
            logger.error(f"Network error fetching playlist: {e.reason}")
            raise
        except Exception as e:
            logger.error(f"Failed to parse playlist {m3u8_url}: {e}")
            raise

    def _fetch_m3u8_with_retry(self, m3u8_url: str) -> m3u8.M3U8:
        """
        Fetches the m3u8 playlist with retry logic.

        :param m3u8_url: m3u8 url to fetch
        :return: m3u8 Playlist
        """

        max_retries = Configs.MAX_RETRIES_TO_LOAD_M3U8
        last_exception = None

        for attempt in range(1, max_retries + 1):
            logger.debug(f"Attempt {attempt}/{max_retries} to fetch m3u8: {m3u8_url}")
            try:
                return self.fetch_m3u8_playlist(m3u8_url)
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 404):
                    logger.error(f"Non-retryable HTTP {e.code} for {m3u8_url}, aborting.")
                    raise
                last_exception = e
                logger.warning(f"HTTP {e.code} on attempt {attempt}/{max_retries}, retrying...")
            except (urllib.error.URLError, Exception) as e:
                last_exception = e
                logger.warning(f"Attempt {attempt}/{max_retries} failed: {e}, retrying...")

        logger.error(f"Exhausted {max_retries} retries for {m3u8_url}.")
        raise last_exception

    def fetch_and_parse_renditions_from_master_playlist(self) -> list[Rendition]:
        """
        Fetches and parses renditions from the master playlist with retry logic.

        :return: List of renditions sorted by bandwidth
        """

        master_playlist = self._fetch_m3u8_with_retry(self.master_playlist_url)
        renditions = []
        for rendition in master_playlist.playlists:
            renditions.append(
                Rendition(
                    uri=rendition.uri,
                    bandwidth=rendition.stream_info.bandwidth,
                    resolution=str(rendition.stream_info.resolution),
                    codecs=rendition.stream_info.codecs,
                )
            )
        return sorted(renditions, key=lambda r: r.bandwidth)

    def push_media_playlist_segments(self, m3u8_url: str, duration: int = None) -> None:
        """
        This method is to keep capturing the media playlist segments

        :param m3u8_url: m3u8 url
        :param duration: duration in seconds, if none then it will capture forever
        :return: list of Segments
        """

        last_sequence = -1
        start_time = time.time()
        logger.info(f"Start time of pushing the segments in queue: {convert_float_timestamp_to_IST(start_time)}")

        while True:
            if duration is not None and (time.time() - start_time) >= duration:
                self.seg_que.put(None)
                logger.info(
                    f"Duration for which segments needs to be pushed [{duration} seconds] is over. "
                    f"Current time: {convert_float_timestamp_to_IST(time.time())}"
                )
                break

            logger.debug("Fetching the media playlist.")
            media_playlist = self._fetch_m3u8_with_retry(m3u8_url)
            sleep_time = getattr(media_playlist, 'target_duration', 0) / 2

            base_sequence = getattr(media_playlist, 'media_sequence', 0)
            logger.debug(f"Base sequence of the media playlist: {base_sequence}")

            for idx, seg in enumerate(media_playlist.segments):
                seq = base_sequence + idx
                if seq > last_sequence:
                    logger.debug(f"Found a new segment [{seq}], Adding to the queue.")
                    last_sequence = seq
                    self.seg_que.put(
                        Segment(
                            uri=seg.uri,
                            sequence=seg.media_sequence,
                            duration=seg.duration,
                            discontinuity=seg.discontinuity,
                            program_date_time=None
                        )
                    )

            if getattr(media_playlist, 'is_endlist', False):
                self.seg_que.put(None)
                logger.info("Playlist has ended.")
                break

            logger.debug(f"Sleeping for {sleep_time} seconds before fetching the media playlist again.")
            time.sleep(sleep_time)
