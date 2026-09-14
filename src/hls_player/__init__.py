"""
This file is to control the configurations for HLS player
"""


class Configs:
    """
    This class is to control the configurations for HLS player
    """

    # MASTER_PLAYLIST_URL = "https://amg02004-amg02004c2-amgplt0735.integration.amaginow.tv/playout/amg02004/amg02004c2/amgplt0735/amgplt0735.m3u8"
    # MASTER_PLAYLIST_URL = "https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8"
    MASTER_PLAYLIST_URL = "https://playout-amg00000c103p1.playout.now3.amagi.tv/playout/amg00000/amg00000c103/amg00000c103p1/amgplt0056.m3u8"
    MAX_RETRIES_TO_LOAD_M3U8 = 3
    DEFAULT_PLAYER_DURATION = 15
    MAX_PARALLEL_DOWNLOADS = 4
    DISPLAY_WIDTH = 1280
    DISPLAY_HEIGHT = 720
    TIMEZONE = "Asia/Kolkata"
