# HLS Player

A from-scratch HLS player built in Python, alongside a lightweight web-based player using hls.js.

---

## Python Player

A fully custom HLS playback pipeline built without any high-level media player library. Every stage — from playlist parsing to frame rendering — is implemented explicitly.

### Pipeline

```
Playlist Parser → Segment Fetcher → Decoder → Renderer
```

| Stage | File | What it does |
|---|---|---|
| Playlist Parser | `playlist_parser.py` | Fetches and parses the m3u8 playlist, pushes `Segment` objects into a queue. Logs every fetched playlist and checks for MSN skips or regressions between consecutive playlist windows |
| Segment Fetcher | `ts_segment_fetcher.py` | Downloads `.ts` segments concurrently, pushes `DownloadedSegment` bytes into a queue |
| Decoder | `decode_bytes.py` | Demuxes and decodes each segment using PyAV, produces `VideoPacket` and `AudioPacket` objects |
| Renderer | `render_packets.py` | Renders video frames via pygame and audio via sounddevice, with A/V sync anchored to the hardware audio clock |

Each stage runs in its own thread and communicates via queues.

### A/V Sync

Video frames are timed against the hardware audio clock (`sounddevice.OutputStream.time`) rather than wall time. This ensures video stays locked to what is actually coming out of the speaker, not just how fast data is being written to the buffer. On stream discontinuities (e.g. ad splices), the sync clock is re-anchored to the new PTS to avoid incorrect sleep durations.

### Requirements

```
python >= 3.11
pygame
sounddevice
av (PyAV)
numpy
requests
m3u8
```

Dependencies are managed with [uv](https://github.com/astral-sh/uv). Install them with:

```bash
uv sync
```

### Configuration

Edit `src/hls_player/__init__.py`:

```python
MASTER_PLAYLIST_URL = "your_m3u8_url_here"
DEFAULT_PLAYER_DURATION = 15   # seconds
MAX_PARALLEL_DOWNLOADS = 4
DISPLAY_WIDTH = 1280
DISPLAY_HEIGHT = 720
```

### Run

```bash
python main.py
```

### Logging

Every step of the pipeline is logged to `logs/` — `hls_player_<date>.log` for the full pipeline, `msn_logs.log` for raw playlist dumps, and `msn_skips.log` for MSN skip/regression detections.

---

## Web Player

A browser-based HLS player using [hls.js](https://github.com/video-dev/hls.js). The user pastes any public m3u8 URL and the browser handles fetching, decoding, and playback entirely — no server required.

### Location

```
web-player/index.html
```

### How to use

Open `web-player/index.html` directly in any modern browser. Paste an m3u8 URL into the input field and press **Play** or **Enter**.

### How it works

- **hls.js** replicates the entire Python pipeline inside the browser — it parses the playlist, downloads segments, and feeds decoded data to the `<video>` element via the browser's Media Source Extensions (MSE) API.
- On Safari, native HLS support is used instead of hls.js.
- No build step, no npm, no server.

### Limitation

If the stream server does not include CORS headers (`Access-Control-Allow-Origin`), the browser will block the request. This is a browser security restriction that does not affect the Python player. Streams that require server-side authentication or proxying are not supported in this setup.

---

## Project Structure

```
hls-player/
├── main.py
├── src/
│   └── hls_player/
│       ├── __init__.py          # Configuration
│       ├── playlist_parser.py
│       ├── ts_segment_fetcher.py
│       ├── decode_bytes.py
│       ├── render_packets.py
│       ├── models/
│       │   └── models.py
│       └── utils/
│           ├── loggers.py
│           ├── date_time_utils.py
│           └── string_utils.py
├── logs/
│   ├── hls_player_<date>.log
│   ├── msn_logs.log
│   └── msn_skips.log
└── web-player/
    └── index.html
```

---

## License

No license required — clone or fork the repo and enjoy.

---

## Author

**Priyanshu** — CSE 2025 Graduate | Software Engineer at Amagi Media Labs

- LinkedIn: [Priyanshu Mehta](https://www.linkedin.com/in/priyanshu-mehta)
- Project Repository: 

Feel free to reach out for collaborations or if you encounter any issues!
