import json
import os
import re
import random
import shutil
import subprocess
import textwrap
from pathlib import Path
from urllib.parse import urlencode

import requests
from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 720, 1280, 30
OUT_DIR = Path("output")
ASSET_DIR = OUT_DIR / "assets"
OUT_DIR.mkdir(exist_ok=True)
ASSET_DIR.mkdir(exist_ok=True)

API_KEY = os.environ.get("PIXABAY_API_KEY", "").strip()
if not API_KEY:
    raise SystemExit(
        "Missing PIXABAY_API_KEY. Add it in GitHub repo Settings > Secrets and variables > Actions."
    )

# The daily research workflow writes this file before video production.
TOPIC_FILE = Path("topic.json")
if not TOPIC_FILE.exists():
    raise SystemExit("Missing topic.json. Run discover_topic.py before create_short.py.")
TOPIC = json.loads(TOPIC_FILE.read_text(encoding="utf-8"))
TITLE = TOPIC["title"]
NARRATION = TOPIC["narration"]
SCENES = TOPIC["scenes"]

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def run(cmd):
    subprocess.run(cmd, check=True)

def get_pixabay_video(query, index, scene_seconds):
    # One API request per scene; do not loop or mass-download search results.
    params = {
        "key": API_KEY,
        "q": query,
        "video_type": "film",
        "safesearch": "true",
        "order": "popular",
        "per_page": 10,
    }
    response = requests.get(
        "https://pixabay.com/api/videos/",
        params=params,
        timeout=45,
        headers={"User-Agent": "CuriousWorldShorts/1.0"},
    )
    response.raise_for_status()
    data = response.json()
    hits = data.get("hits", [])
    if not hits:
        raise RuntimeError(f"No Pixabay videos found for query: {query}")

    # Pixabay exposes tags, not a reliable visual-content classifier.
    query_terms = {term.lower() for term in re.findall(r"[A-Za-z][A-Za-z-]{2,}", query)}
    blocked_tags = {"news", "breaking", "report", "reporter", "television", "tv",
        "broadcast", "screen", "monitor", "subtitle", "subtitles", "caption",
        "captions", "text", "typography", "logo", "watermark", "advertisement",
        "commercial", "interface", "screenshot", "poster", "headline"}
    def relevance(hit):
        raw_tags = (hit.get("tags") or "").lower()
        tags = set(re.findall(r"[A-Za-z][A-Za-z-]{2,}", raw_tags))
        if tags & blocked_tags:
            return -1
        return len(query_terms & tags)

    ranked = [(relevance(hit), hit) for hit in hits]
    ranked = [(score, hit) for score, hit in ranked if score >= 2]
    if not ranked:
        raise RuntimeError(
            f"Pixabay results did not match the scene keywords closely enough: {query}"
        )
    candidates = [
        hit for _, hit in sorted(
            ranked,
            key=lambda pair: (
                pair[0],
                pair[1].get("duration", 0) >= scene_seconds,
                pair[1].get("videos", {}).get("large", {}).get("width", 0),
                pair[1].get("downloads", 0),
            ),
            reverse=True,
        )
    ]
    for hit in candidates:
        variants = hit.get("videos", {})
        variant = variants.get("large") or variants.get("medium") or variants.get("small")
        if variant and variant.get("url"):
            target = ASSET_DIR / f"scene_{index:02d}.mp4"
            with requests.get(variant["url"], stream=True, timeout=90) as r:
                r.raise_for_status()
                with target.open("wb") as f:
                    for chunk in r.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
            if target.stat().st_size > 50_000:
                return target, {
                    "id": hit.get("id"),
                    "pageURL": hit.get("pageURL"),
                    "creator": hit.get("user", "Pixabay contributor"),
                    "query": query,
                }
            target.unlink(missing_ok=True)
    raise RuntimeError(f"Pixabay returned no downloadable video for: {query}")

def make_title_card(path, caption, number):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    bold = ImageFont.truetype(FONT_BOLD, 35)
    small = ImageFont.truetype(FONT_BOLD, 18)
    d.rounded_rectangle((24, 28, 310, 72), radius=18,
                        fill=(5, 18, 38, 205), outline=(110, 205, 255, 220), width=2)
    d.text((42, 40), "CURIOUS WORLD", font=small, fill=(170, 230, 255, 255))
    d.rounded_rectangle((28, 135, 692, 295), radius=24,
                        fill=(3, 12, 28, 205), outline=(85, 175, 235, 220), width=2)
    lines = textwrap.wrap(caption, width=27)
    y = 170 if len(lines) == 1 else 152
    for line in lines[:2]:
        box = d.textbbox((0, 0), line, font=bold, stroke_width=1)
        x = (W - (box[2] - box[0])) // 2
        d.text((x, y), line, font=bold, fill=(255, 255, 255, 255),
               stroke_width=1, stroke_fill=(0, 0, 0, 255))
        y += 48
    d.rounded_rectangle((632, 28, 692, 72), radius=16, fill=(5, 18, 38, 205))
    d.text((650, 40), f"{number}/3", font=small, fill=(230, 245, 255, 235))
    im.save(path)

def main():
    # Remove leftovers from previous runs so a failed render can never reuse stale media.
    for item in OUT_DIR.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()
    ASSET_DIR.mkdir(parents=True, exist_ok=True)

    credits = []
    segment_files = []

    # Generate the narration first so the visual pacing follows the actual speech.
    narration_file = OUT_DIR / "narration.mp3"
    subtitles_file = OUT_DIR / "narration.srt"
    voice_choices = [
        "en-US-AriaNeural",
        "en-US-JennyNeural",
        "en-US-GuyNeural",
        "en-US-EricNeural",
        "en-US-MichelleNeural",
        "en-US-ChristopherNeural",
        "en-US-AnaNeural",
        "en-US-SteffanNeural",
    ]
    selected_voice = random.choice(voice_choices)
    print(f"Selected narration voice: {selected_voice}")
    run([
        "edge-tts",
        "--voice", selected_voice,
        "--rate=+2%",
        "--text", NARRATION,
        "--write-media", str(narration_file),
        "--write-subtitles", str(subtitles_file),
    ])
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", str(narration_file)],
        check=True, capture_output=True, text=True
    )
    narration_seconds = float(probe.stdout.strip())
    scene_seconds = max(8, narration_seconds / max(1, len(SCENES)) + 0.6)
    print(f"Narration: {narration_seconds:.1f}s; scene pacing: {scene_seconds:.1f}s.")

    for i, scene in enumerate(SCENES, start=1):
        clip, credit = get_pixabay_video(scene["query"], i, scene_seconds)
        credits.append(credit)
        segment = ASSET_DIR / f"segment_{i:02d}.mp4"
        base_filter = (
            f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={W}:{H},fps={FPS},setsar=1,format=yuv420p"
        )
        if i == 1:
            overlay = ASSET_DIR / "opening_title.png"
            make_title_card(overlay, TITLE, i)
            run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-stream_loop", "-1", "-i", str(clip),
                "-loop", "1", "-i", str(overlay),
                "-filter_complex",
                f"[0:v]{base_filter}[base];"
                f"[base][1:v]overlay=0:0:shortest=1,format=yuv420p[v]",
                "-map", "[v]", "-t", str(scene_seconds),
                "-an", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "21", "-movflags", "+faststart", str(segment)
            ])
        else:
            run([
                "ffmpeg", "-y", "-loglevel", "error",
                "-stream_loop", "-1", "-i", str(clip),
                "-vf", base_filter, "-t", str(scene_seconds),
                "-an", "-c:v", "libx264", "-preset", "veryfast",
                "-crf", "21", "-movflags", "+faststart", str(segment)
            ])
        segment_files.append(segment)

    concat_file = OUT_DIR / "concat.txt"
    concat_file.write_text(
        "".join(f"file '{p.resolve()}'\n" for p in segment_files),
        encoding="utf-8"
    )
    silent = OUT_DIR / "video_silent.mp4"
    run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", str(silent)
    ])

    # Burn synchronized captions into the vertical video.
    fade_start = max(0, narration_seconds - 2.0)
    # No paid API is used; Edge TTS supplies both audio and subtitle timings.
    run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(silent),
        "-i", str(narration_file),
        "-filter_complex",
        "[1:a]highpass=f=75,lowpass=f=14000,"
        "loudnorm=I=-16:TP=-1.5:LRA=11,"
        f"afade=t=in:st=0:d=0.18,afade=t=out:st={fade_start:.2f}:d=2[a]",
        "-map", "0:v:0", "-map", "[a]",
        "-vf", "subtitles=output/narration.srt:force_style='FontName=DejaVu Sans,FontSize=14,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=65'",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", "-movflags", "+faststart",
        str(OUT_DIR / "curious-world-short.mp4")
    ])

    # Keep an auditable source/creator record beside the generated video.
    credit_lines = [
        "Visual footage: Pixabay (used under the Pixabay Content License).",
        "Please review each source page and the license before publishing.",
        "Pixabay: https://pixabay.com/service/license-summary/",
        "",
    ]
    for item in credits:
        credit_lines.append(
            f"Scene query: {item['query']} | Creator: {item['creator']} | "
            f"Source: {item['pageURL']} | Asset ID: {item['id']}"
        )
    (OUT_DIR / "video-credits.txt").write_text("\n".join(credit_lines), encoding="utf-8")
    (OUT_DIR / "youtube-description.txt").write_text(
        f"{TITLE}\n\nOriginal Curious World narration and edit. "
        "Stock footage sourced from Pixabay under its Content License.\n"
        "Footage credits and source links are included in video-credits.txt.\n\n"
        "More science mysteries: subscribe to Curious World!\n",
        encoding="utf-8"
    )
    print(f"Created {OUT_DIR / 'curious-world-short.mp4'}")

if __name__ == "__main__":
    main()
