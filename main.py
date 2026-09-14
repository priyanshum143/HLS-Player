"""
This is the main file to run the HLS player
"""

import threading

from src.hls_player import Configs
from src.hls_player.playlist import PlaylistFetcher
from src.hls_player.fetcher import Fetcher
from src.hls_player.utils.string_utils import resolve_url
from src.hls_player.utils.loggers import get_logger

master_playlist_url = Configs.MASTER_PLAYLIST_URL
playlist_fetcher = PlaylistFetcher(master_playlist_url)

logger = get_logger(__name__)


def main():
    """
    This is main method to run the HLS player

    :return: None
    """

    # The duration for which we need to run our player
    duration = 120

    # Fetching the renditions from master playlist
    logger.info(f"Fetching the master playlist for {master_playlist_url} to extract the renditions.")
    renditions = playlist_fetcher.fetch_and_parse_renditions_from_master_playlist()
    logger.debug(f"Renditions found: {renditions}")

    # Resolving the media playlist URL
    lowest_bandwidth_rendition_uri = renditions[0].uri
    complete_media_playlist_url = resolve_url(master_playlist_url, lowest_bandwidth_rendition_uri)

    # Creating an object of fetcher
    ts_segment_fetcher = Fetcher(complete_media_playlist_url)

    # Starting the thread to parse media playlist
    logger.debug(f"Starting to fetch the media playlist for variant: {complete_media_playlist_url}")
    playlist_thread = threading.Thread(
        target=playlist_fetcher.push_media_playlist_segments,
        args=(complete_media_playlist_url, duration),
    )

    # Starting the thread to download the ts segment
    ts_segment_thread = threading.Thread(
        target=ts_segment_fetcher.push_downloaded_segment_in_que,
        args=(playlist_fetcher.seg_que,)
    )

    playlist_thread.start()
    ts_segment_thread.start()

    try:
        playlist_thread.join()
    finally:
        playlist_fetcher.seg_que.put(None)

    ts_segment_thread.join()

if __name__ == "__main__":
    main()
