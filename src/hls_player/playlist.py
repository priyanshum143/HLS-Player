"""
This file contains the methods and code to fetch and parse the playlist
"""


import m3u8
from urllib.parse import urljoin


def fetch_master_playlist(master_url: str) -> list[Rendition]:
    """
    This method will fetch the master playlist and will make a list of renditions

    :param master_url: master m3u8 url
    :return: List of renditions
    """

    master_playlist = m3u8.load(master_url)
    renditions = []
    for rendition in master_playlist.playlists:
        renditions.append(
            Rendition(
                uri=urljoin(master_url, rendition.uri),
                bandwidth=rendition.stream_info.bandwidth,
                resolution=str(rendition.stream_info.resolution),
                codecs=rendition.stream_info.codecs,
            )
        )
    return sorted(renditions, key=lambda r: r.bandwidth)


def fetch_media_playlist(media_playlist_url: str) -> list:
    """
    This method will fetch, parse and print the media playlist details

    :param media_playlist_url: media playlist url
    :return: None
    """

    media_playlist = m3u8.load(media_playlist_url)
    segments = []
    for seg in media_playlist.segments:
        segments.append(
            Segment(
                uri=urljoin(media_playlist_url, seg.uri),
                sequence=seg.media_sequence,
                duration=seg.duration,
                discontinuity=seg.discontinuity,
                program_date_time=None
            )
        )
    return segments



def main():
    # master_url = input("Enter the master m3u8 url: ")
    master_url = "https://amg02004-amg02004c2-amgplt0735.integration.amaginow.tv/playout/amg02004/amg02004c2/amgplt0735/amgplt0735.m3u8"
    renditions = fetch_master_playlist(master_url)

    lowest_bandwidth_rendition_uri = renditions[0].uri
    segments = fetch_media_playlist(lowest_bandwidth_rendition_uri)
    print(segments)

if __name__ == "__main__":
    main()
