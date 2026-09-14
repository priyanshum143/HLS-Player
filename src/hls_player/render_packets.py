"""
This file contains the code to render the video and audio packets
"""

import time
import threading
import queue

import numpy as np
import pygame
import sounddevice

from src.hls_player.models.models import VideoPacket, AudioPacket
from src.hls_player.utils.loggers import get_logger

logger = get_logger(__name__)


class RenderPackets:
    """
    This class contains the code to render the video and audio packets
    """

    def __init__(self, width: int, height: int) -> None:
        """
        This is a constructor for RenderPackets

        :param width: video frame width in pixels
        :param height: video frame height in pixels
        """

        pygame.init()
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("HLS Player")

        self.stream_start: float | None = None
        self.stream_start_lock = threading.Lock()
        self.stream_started_event = threading.Event()
        self.stop_event = threading.Event()

    def audio_loop(self, audio_queue: queue.Queue) -> None:
        """
        This method consumes AudioPackets, feeds PCM to sounddevice, and sets the master clock
        on the first packet.

        :param audio_queue: queue of audio packets
        :return: None
        """

        logger.info("Audio render loop started.")
        while True:
            audio_packet: AudioPacket = audio_queue.get()
            if audio_packet is None:
                with self.stream_start_lock:
                    if self.stream_start is None:
                        self.stream_start = time.time()
                        self.stream_started_event.set()
                logger.info("Audio render loop finished.")
                return

            # sounddevice expects (samples, channels), PyAV gives (channels, samples)
            pcm = np.ascontiguousarray(audio_packet.pcm.T, dtype=np.float32)

            # Set stream_start once using the first audio packet's pts
            with self.stream_start_lock:
                if self.stream_start is None:
                    self.stream_start = time.time() - audio_packet.pts
                    self.stream_started_event.set()
                    logger.debug(f"Stream start set to {self.stream_start} from audio pts {audio_packet.pts}")

            if self.stop_event.is_set():
                return

            sounddevice.play(pcm, samplerate=audio_packet.sample_rate)
            sounddevice.wait()

    def video_loop(self, video_queue: queue.Queue) -> None:
        """
        This method consumes VideoPackets, syncs each frame to the audio master clock,
        and blits it to the pygame window.

        :param video_queue: queue of video packets
        :return: None
        """

        logger.info("Video render loop started.")

        # Wait until audio thread has set stream_start before attempting any sync
        self.stream_started_event.wait()

        while True:
            video_packet: VideoPacket = video_queue.get()
            if video_packet is None:
                logger.info("Video render loop finished.")
                return

            with self.stream_start_lock:
                stream_start = self.stream_start

            display_at = stream_start + video_packet.pts
            now = time.time()

            if now < display_at:
                time.sleep(display_at - now)
            elif (now - display_at) > 0.1:
                # Frame is more than 100ms late — drop it to catch up
                logger.debug(f"Dropping late frame at pts={video_packet.pts:.3f}, behind by {now - display_at:.3f}s")
                continue

            if self.stop_event.is_set():
                return

            # pygame surfarray expects (width, height, 3), numpy gives (height, width, 3)
            frame = np.transpose(video_packet.rgb_array, (1, 0, 2))
            surface = pygame.surfarray.make_surface(frame)
            self.screen.blit(surface, (0, 0))
            pygame.display.flip()

    def render(self, video_queue: queue.Queue, audio_queue: queue.Queue) -> None:
        """
        This method starts audio and video render threads and runs the pygame event loop
        until playback finishes or the user closes the window.

        :param video_queue: queue of video packets
        :param audio_queue: queue of audio packets
        :return: None
        """

        audio_thread = threading.Thread(target=self.audio_loop, args=(audio_queue,), daemon=True)
        video_thread = threading.Thread(target=self.video_loop, args=(video_queue,), daemon=True)

        audio_thread.start()
        video_thread.start()

        # pygame event loop must run on the main thread
        while audio_thread.is_alive() or video_thread.is_alive():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    logger.info("User closed the window.")
                    self.stop_event.set()
                    sounddevice.stop()
                    pygame.quit()
                    return
            pygame.time.wait(10)

        audio_thread.join()
        video_thread.join()
        pygame.quit()
        logger.info("Playback finished.")
