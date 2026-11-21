import json
import subprocess
from pathlib import Path

VIDEO = Path("output/curious-world-short.mp4")
SUBTITLES = Path("output/narration.srt")
CREDITS = Path("output/video-credits.txt")
MIN_BYTES = 100_000
MIN_SECONDS = 10
MAX_SECONDS = 180


def fail(message):
    raise SystemExit("VIDEO QUALITY CHECK FAILED: " + message)


def main():
    for path in (VIDEO, SUBTITLES, CREDITS):
        if not path.is_file():
            fail(f"Required file is missing: {path}")
    if VIDEO.stat().st_size < MIN_BYTES:
        fail(f"Video is unexpectedly small ({VIDEO.stat().st_size} bytes).")
    if SUBTITLES.stat().st_size < 20:
        fail("Subtitle file is empty or too short.")
    if CREDITS.stat().st_size < 50:
        fail("Footage credits file is empty or too short.")

    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration:stream=codec_type,codec_name,width,height",
            "-of", "json", str(VIDEO),
        ],
        check=True, capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    duration = float(data.get("format", {}).get("duration", 0))
    streams = data.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if not video:
        fail("No video stream was found.")
    if not audio:
        fail("No narration/audio stream was found.")
    if duration < MIN_SECONDS or duration > MAX_SECONDS:
        fail(f"Unexpected duration: {duration:.1f}s (expected {MIN_SECONDS}-{MAX_SECONDS}s).")
    width, height = int(video.get("width", 0)), int(video.get("height", 0))
    if width < 360 or height < 640 or height <= width:
        fail(f"Video is not a suitable vertical format: {width}x{height}.")
    if video.get("codec_name") != "h264":
        fail(f"Unexpected video codec: {video.get('codec_name')}.")
    if audio.get("codec_name") != "aac":
        fail(f"Unexpected audio codec: {audio.get('codec_name')}.")

    print(
        f"Quality check passed: {width}x{height}, {duration:.1f}s, "
        f"{VIDEO.stat().st_size:,} bytes; video, audio, subtitles and credits present."
    )


if __name__ == "__main__":
    main()
