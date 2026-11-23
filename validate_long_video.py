import json, subprocess
from pathlib import Path
base=Path("output/long")
video=base/"curious-world-long.mp4"
required=[video,base/"narration.srt",base/"video-credits.txt",base/"thumbnail.jpg",base/"visual-match-report.json"]
for f in required:
    if not f.exists() or f.stat().st_size<100:
        raise SystemExit(f"Missing or empty output: {f}")
matches=json.loads((base/"visual-match-report.json").read_text(encoding="utf-8"))
if len(matches)!=12:
    raise SystemExit(f"Expected 12 scene-specific visual matches, found {len(matches)}.")
ids=[str(x.get("id")) for x in matches]
if len(set(ids))!=12:
    raise SystemExit("Repeated Pixabay clip detected; refusing upload.")
for i,item in enumerate(matches,1):
    if item.get("matched_terms",0)<2 or item.get("coverage",0)<0.30 or not item.get("url"):
        raise SystemExit(f"Scene {i} failed visual relevance threshold.")
data=json.loads(subprocess.run(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(video)],capture_output=True,text=True,check=True).stdout)
duration=float(data["format"]["duration"])
streams=data["streams"]
v=next((s for s in streams if s["codec_type"]=="video"),None)
a=next((s for s in streams if s["codec_type"]=="audio"),None)
if not (240<=duration<=900):
    raise SystemExit(f"Unexpected duration: {duration:.1f}s; expected 4-15 minutes.")
if not v or not a or int(v["width"])<=int(v["height"]):
    raise SystemExit("Missing audio/video or video is not landscape.")
if v.get("codec_name")!="h264" or a.get("codec_name")!="aac":
    raise SystemExit("Unexpected codecs.")
print(f"PASS: {duration/60:.1f} min, {v['width']}x{v['height']}, H.264/AAC; 12 unique scene matches passed tag-overlap checks.")
