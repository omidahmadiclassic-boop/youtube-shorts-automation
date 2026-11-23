import json, os, re
from datetime import datetime, timezone
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

def main():
    env = {k: os.environ.get(k, "").strip() for k in ("YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN")}
    missing = [k for k, v in env.items() if not v]
    if missing:
        raise SystemExit("Missing YouTube secrets: " + ", ".join(missing))
    topic = json.loads(Path("long_topic.json").read_text(encoding="utf-8"))
    history_path = Path("long_upload_history.json")
    try:
        history = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        history = {"published_topics": []}
    key = " ".join(topic.get("topic", "").casefold().split())
    if not key:
        raise SystemExit("Long-form topic is empty; refusing upload.")
    published = history.get("published_topics", [])
    if any(" ".join(str(x.get("topic", "")).casefold().split()) == key for x in published if isinstance(x, dict)):
        raise SystemExit("This long-form topic was already uploaded; duplicate blocked.")
    video = Path("output/long/curious-world-long.mp4")
    thumb = Path("output/long/thumbnail.jpg")
    desc = Path("output/long/youtube-description.txt").read_text(encoding="utf-8")
    title = re.sub(r"\s+", " ", topic.get("title", topic["topic"])).strip()[:100]
    credentials = Credentials(None, refresh_token=env["YOUTUBE_REFRESH_TOKEN"], token_uri="https://oauth2.googleapis.com/token", client_id=env["YOUTUBE_CLIENT_ID"], client_secret=env["YOUTUBE_CLIENT_SECRET"], scopes=SCOPES)
    youtube = build("youtube", "v3", credentials=credentials)
    body = {"snippet": {"title": title, "description": desc[:5000], "tags": ["Curious World", "science", "education", "documentary", "explained"], "categoryId": "27", "defaultLanguage": "en"}, "status": {"privacyStatus": "public"}}
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=MediaFileUpload(str(video), mimetype="video/mp4", resumable=True))
    result = req.execute()
    vid = result.get("id")
    if not vid:
        raise SystemExit("YouTube did not return a video ID; upload state is uncertain.")
    try:
        youtube.thumbnails().set(videoId=vid, media_body=MediaFileUpload(str(thumb), mimetype="image/jpeg")).execute()
    except Exception as exc:
        print("WARNING: video uploaded, but custom thumbnail failed:", exc)
    published.append({"topic": topic["topic"], "title": title, "video_id": vid, "url": "https://www.youtube.com/watch?v=" + vid, "published_at_utc": datetime.now(timezone.utc).isoformat()})
    history["published_topics"] = published[-300:]
    history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Uploaded public long-form video:", "https://www.youtube.com/watch?v=" + vid)

if __name__ == "__main__":
    main()
