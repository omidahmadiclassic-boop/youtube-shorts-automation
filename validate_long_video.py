import json, subprocess
from pathlib import Path
p=Path("output/long/curious-world-long.mp4")
for f in [p,Path("output/long/narration.srt"),Path("output/long/video-credits.txt"),Path("output/long/thumbnail.jpg")]:
 if not f.exists() or f.stat().st_size<100: raise SystemExit(f"Missing or empty output: {f}")
data=json.loads(subprocess.run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(p)],capture_output=True,text=True,check=True).stdout)
duration=float(data["format"]["duration"])
streams=data["streams"]
video=next((s for s in streams if s["codec_type"]=="video"),None)
audio=next((s for s in streams if s["codec_type"]=="audio"),None)
if not (240<=duration<=900): raise SystemExit(f"Unexpected duration: {duration:.1f}s; expected 4-15 minutes.")
if not video or not audio or int(video["width"])<=int(video["height"]): raise SystemExit("Missing audio/video or video is not landscape.")
if video.get("codec_name")!="h264" or audio.get("codec_name")!="aac": raise SystemExit("Unexpected codecs.")
print(f"PASS: {duration/60:.1f} min, {video['width']}x{video['height']}, H.264/AAC, subtitles and thumbnail present.")
