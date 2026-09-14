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
        self._screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("HLS Player")

        # sync clock anchored to HW audio output, not wall time
        self._audio_stream: sounddevice.OutputStream | None = None
        self._sync_lock = threading.Lock()
        self._pts_base: float = 0.0
        self._stream_time_base: float = 0.0

        # Stream start and end events
        self._stream_started_event = threading.Event()
        self._stop_event = threading.Event()

    def _display_at(self, video_pts: float) -> float:
        """
        Return the wall-clock time at which a video frame at video_pts should be displayed,
        derived from the hardware audio clock so video stays locked to actual audio output.

        :param video_pts: presentation timestamp of the video frame in seconds
        :return: wall-clock time (time.time() scale) at which to display the frame
        """

        with self._sync_lock:
            audio_stream = self._audio_stream
            pts_base = self._pts_base
            stream_time_base = self._stream_time_base

        if audio_stream is None:
            return time.time()

        elapsed = audio_stream.time - stream_time_base
        current_audio_pts = pts_base + elapsed
        return time.time() + (video_pts - current_audio_pts)

    def _audio_loop(self, audio_queue: queue.Queue) -> None:
        """
        This method consumes AudioPackets, feeds PCM to a single continuous OutputStream,
        and maintains the A/V sync clock anchored to the hardware audio clock.

        :param audio_queue: queue of audio packets
        :return: None
        """

        logger.debug("Audio render loop started.")
        stream: sounddevice.OutputStream | None = None

        while True:
            audio_packet: AudioPacket | None = audio_queue.get()
            if audio_packet is None:
                if stream is not None:
                    stream.stop()
                    stream.close()
                self._stream_started_event.set()
                logger.debug("Audio render loop finished.")
                return

            # sounddevice expects (samples, channels), PyAV gives (channels, samples)
            pcm = np.ascontiguousarray(audio_packet.pcm.T, dtype=np.float32)
            channels = pcm.shape[1] if pcm.ndim > 1 else 1

            if stream is None:
                # Creating the stream object and starting the stream
                stream = sounddevice.OutputStream(
                    samplerate=audio_packet.sample_rate,
                    channels=channels,
                    dtype='float32',
                )
                stream.start()

                with self._sync_lock:
                    self._audio_stream = stream
                    self._pts_base = audio_packet.pts
                    self._stream_time_base = stream.time + stream.latency

                self._stream_started_event.set()
                logger.debug(
                    f"Audio stream started: first_pts={audio_packet.pts:.3f}, "
                    f"latency={stream.latency:.3f}s"
                )

            # content timeline jumped — re-anchor sync clock to new PTS
            if audio_packet.discontinuity:
                with self._sync_lock:
                    self._stream_time_base = stream.time + stream.latency
                    self._pts_base = audio_packet.pts
                    logger.debug(
                        f"Audio sync reset on discontinuity: "
                        f"pts={audio_packet.pts:.3f}, stream.time={stream.time:.3f}"
                    )

            # Stopping the audio stream
            if self._stop_event.is_set():
                stream.stop()
                stream.close()
                return

            # Writing to the stream
            stream.write(pcm)

    def _video_loop(self, video_queue: queue.Queue) -> None:
        """
        This method consumes VideoPackets, syncs each frame to the hardware audio clock,
        and blits it to the pygame window.

        :param video_queue: queue of video packets
        :return: None
        """

        logger.debug("Video render loop started.")

        # Wait until the audio stream is running before starting sync
        self._stream_started_event.wait()

        while True:
            video_packet: VideoPacket | None = video_queue.get()
            if video_packet is None:
                logger.debug("Video render loop finished.")
                return

            # content timeline jumped — re-anchor sync clock before display calc
            if video_packet.discontinuity:
                with self._sync_lock:
                    self._pts_base = video_packet.pts
                    if self._audio_stream is not None:
                        self._stream_time_base = self._audio_stream.time
                    logger.debug(f"Video sync reset on discontinuity: pts={video_packet.pts:.3f}")

            display_at = self._display_at(video_packet.pts)
            now = time.time()

            if now < display_at:
                if display_at - now > 30:
                    logger.debug(f"Dropping stale pre-discontinuity frame at pts={video_packet.pts:.3f}")
                    continue
                time.sleep(display_at - now)
            elif now - display_at > 0.1:
                logger.debug(f"Dropping late frame at pts={video_packet.pts:.3f}, behind by {now - display_at:.3f}s")
                continue

            if self._stop_event.is_set():
                return

            # pygame surfarray expects (width, height, 3), numpy gives (height, width, 3)
            frame = np.transpose(video_packet.rgb_array, (1, 0, 2))
            surface = pygame.surfarray.make_surface(frame)
            if surface.get_size() != self._screen.get_size():
                surface = pygame.transform.scale(surface, self._screen.get_size())
            self._screen.blit(surface, (0, 0))
            pygame.display.flip()

    def render(self, video_queue: queue.Queue, audio_queue: queue.Queue) -> None:
        """
        This method starts audio and video render threads and runs the pygame event loop
        until playback finishes or the user closes the window.

        :param video_queue: queue of video packets
        :param audio_queue: queue of audio packets
        :return: None
        """

        audio_thread = threading.Thread(target=self._audio_loop, args=(audio_queue,), daemon=True)
        video_thread = threading.Thread(target=self._video_loop, args=(video_queue,), daemon=True)

        audio_thread.start()
        video_thread.start()

        # pygame event loop must run on the main thread
        while audio_thread.is_alive() or video_thread.is_alive():
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    logger.info("User closed the window.")
                    self._stop_event.set()
                    pygame.quit()
                    return
            pygame.time.wait(10)

        # Joining the threads
        audio_thread.join()
        video_thread.join()

        # Quiting PyGame
        pygame.quit()
        logger.info("Playback finished.")
