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
from src.hls_player.utils.loggers import get_logger, get_msn_logs_logger, get_msn_skip_logger
from src.hls_player.utils.date_time_utils import convert_float_timestamp_to_IST, convert_datetime_to_timezone

logger = get_logger(__name__)
msn_skip_logger = get_msn_skip_logger()
msn_logs = get_msn_logs_logger()


class PlaylistParser:
    """
    This class is used to fetch and parser playlist and push the segments into queue
    """

    def __init__(self, master_playlist_url: str) -> None:
        """
        This is constructor for PlaylistParser

        :param master_playlist_url: master playlist url
        """

        self.master_playlist_url = master_playlist_url
        self.seg_que = queue.Queue()

    @staticmethod
    def check_if_media_playlist_is_valid(curr: m3u8.M3U8 | None, prev: m3u8.M3U8 | None) -> None:
        """
        This method is used to check if there is any msn jump

        :param curr: current playlist
        :param prev: previous playlist
        :return: None
        """

        prev_media_sequence = getattr(prev, 'media_sequence', None)
        curr_media_sequence = getattr(curr, 'media_sequence', None)
        if prev_media_sequence is None or curr_media_sequence is None:
            msn_skip_logger.info("Skipping the check, as one of the playlist is None.")
            return

        prev_window_end = prev_media_sequence + len(prev.segments)
        curr_window_end = curr_media_sequence + len(curr.segments)

        if curr_media_sequence > prev_window_end:
            skipped = curr_media_sequence - prev_window_end
            msn_skip_logger.error(
                f"MSN SKIP: prev_base={prev_media_sequence}, curr_base={curr_media_sequence}, "
                f"prev_window_end={prev_window_end} | "
                f"{skipped} segment(s) never seen in any playlist window "
                f"(missing MSN {prev_window_end}..{curr_media_sequence - 1})"
            )
        elif curr_media_sequence < prev_media_sequence:
            msn_skip_logger.error(
                f"MSN REGRESSION: sequence went backwards "
                f"prev_base={prev_media_sequence} -> curr_base={curr_media_sequence} "
                f"(dropped by {prev_media_sequence - curr_media_sequence})"
            )
        else:
            overlap = prev_window_end - curr_media_sequence
            advanced = curr_media_sequence - prev_media_sequence
            msn_skip_logger.info(
                f"Playlist OK: advanced by {advanced} segment(s), "
                f"{overlap} segment(s) overlap | "
                f"prev=[{prev_media_sequence}..{prev_window_end - 1}] "
                f"curr=[{curr_media_sequence}..{curr_window_end - 1}]"
            )

    @staticmethod
    def fetch_m3u8_playlist(m3u8_url: str) -> m3u8.M3U8:
        """
        This method will load the m3u8 URL as m3u8 playlist and will return the same
        with error handling.

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
            except (urllib.error.URLError, OSError, ConnectionError) as e:
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
                    resolution=f"{rendition.stream_info.resolution[0]}x{rendition.stream_info.resolution[1]}" if rendition.stream_info.resolution else "1280x720",
                    codecs=rendition.stream_info.codecs,
                )
            )
        return sorted(renditions, key=lambda r: r.bandwidth)

    def push_media_playlist_segments(self, m3u8_url: str, duration: int = None) -> None:
        """
        This method is to keep capturing the media playlist segments and pushing them in a queue

        :param m3u8_url: m3u8 url
        :param duration: duration in seconds, if none then it will capture forever
        :return: list of Segments
        """

        last_sequence = -1
        is_first_fetch = True
        prev_media_playlist = None
        start_time = time.time()
        logger.debug(f"Start time of pushing the segments in queue: {convert_float_timestamp_to_IST(start_time)}")

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
            PlaylistParser.check_if_media_playlist_is_valid(media_playlist, prev_media_playlist)
            fetch_time = convert_float_timestamp_to_IST(time.time())
            msn_logs.debug(f"# Fetched at: {fetch_time}\n{media_playlist.dumps()}\n")

            sleep_time = getattr(media_playlist, 'target_duration', 0) / 2
            base_sequence = getattr(media_playlist, 'media_sequence', 0)
            logger.debug(f"Base sequence of the media playlist: {base_sequence}")

            if is_first_fetch:
                total = len(media_playlist.segments)
                last_sequence = base_sequence + max(0, total - 2) - 1
                logger.debug(f"First fetch: skipping to last 2 segments, starting from seq {last_sequence + 1}.")
                is_first_fetch = False

            for idx, seg in enumerate(media_playlist.segments):
                seq = base_sequence + idx
                if seq > last_sequence:
                    logger.debug(f"Found a new segment [{seq}], Adding to the queue.")
                    last_sequence = seq
                    segment = Segment(
                        uri=seg.uri,
                        sequence=seq,
                        duration=seg.duration,
                        discontinuity=seg.discontinuity,
                        program_date_time=convert_datetime_to_timezone(
                            seg.program_date_time, Configs.TIMEZONE
                        ),
                    )
                    self.seg_que.put(segment)
                    logger.debug(f"Added segment [{segment}] in the queue.")

            if getattr(media_playlist, 'is_endlist', False):
                self.seg_que.put(None)
                logger.info("Playlist has ended.")
                break

            prev_media_playlist = media_playlist
            logger.debug(f"Sleeping for {sleep_time} seconds before fetching the media playlist again.")
            time.sleep(sleep_time)
