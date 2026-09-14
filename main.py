"""
This is the main file to run the HLS player
"""

import threading

from src.hls_player import Configs
from src.hls_player.playlist_parser import PlaylistParser
from src.hls_player.ts_segment_fetcher import TsSegmentsFetcher
from src.hls_player.decode_bytes import DecodeBytes
from src.hls_player.utils.string_utils import resolve_url
from src.hls_player.utils.loggers import get_logger

master_playlist_url = Configs.MASTER_PLAYLIST_URL
playlist_fetcher = PlaylistParser(master_playlist_url)
decode_bytes = DecodeBytes()

logger = get_logger(__name__)


def main():
    """
    This is main method to run the HLS player

    :return: None
    """

    # The duration for which we need to run our player
    duration = Configs.DEFAULT_PLAYER_DURATION

    # Fetching the renditions from master playlist
    logger.info(f"Fetching the master playlist for {master_playlist_url} to extract the renditions.")
    renditions = playlist_fetcher.fetch_and_parse_renditions_from_master_playlist()
    logger.debug(f"Renditions found: {renditions}")

    # Resolving the media playlist URL
    lowest_bandwidth_rendition_uri = renditions[0].uri
    complete_media_playlist_url = resolve_url(master_playlist_url, lowest_bandwidth_rendition_uri)

    # Creating an object of fetcher
    ts_segment_fetcher = TsSegmentsFetcher(complete_media_playlist_url)

    # Creating a thread to parse media playlist
    playlist_thread = threading.Thread(
        target=playlist_fetcher.push_media_playlist_segments,
        args=(complete_media_playlist_url, duration),
    )

    # Creating a thread to download the ts segment
    ts_segment_thread = threading.Thread(
        target=ts_segment_fetcher.push_downloaded_segment_in_que,
        args=(playlist_fetcher.seg_que,)
    )

    # Creating a thread to decode the ts segment bytes
    decode_bytes_thread = threading.Thread(
        target=decode_bytes.generate_audio_and_video_queue,
        args=(ts_segment_fetcher.downloaded_segment_que,)
    )

    # Starting the thread to fetch the media playlist
    logger.info(f"Starting to fetch the media playlist for variant: {complete_media_playlist_url}")
    playlist_thread.start()

    # Starting the thread to download the TS segments present in media playlist
    logger.info("Starting to download the TS segments.")
    ts_segment_thread.start()

    # Starting the thread to decode the downloaded TS segments Bytes
    logger.info("Starting the decode bytes thread.")
    decode_bytes_thread.start()

    # Finishing the thread which was fetching the media playlist
    try:
        playlist_thread.join()
    finally:
        playlist_fetcher.seg_que.put(None)

    # Finishing the thread which was downloading the TS segments
    ts_segment_thread.join()

    # Finishing the thread which was decoding the TS segments bytes.
    decode_bytes_thread.join()

if __name__ == "__main__":
    main()
