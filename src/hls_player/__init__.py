"""
This file is to control the configurations for HLS player
"""

class Configs:
    """
    This class is to control the configurations for HLS player
    """

    MASTER_PLAYLIST_URL = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"
    MAX_RETRIES_TO_LOAD_M3U8 = 3
    DEFAULT_PLAYER_DURATION = None
    MAX_PARALLEL_DOWNLOADS = 4
    DISPLAY_WIDTH = 1280
    DISPLAY_HEIGHT = 720
    TIMEZONE = "Asia/Kolkata"
    TARGETED_RENDITION = 0      # 0 being the lowest
