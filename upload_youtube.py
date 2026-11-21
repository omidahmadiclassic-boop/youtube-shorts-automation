import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Keep metadata relevant to each topic instead of pasting the same generic tags.
TOPIC_TAGS = {
    "space": ["space", "universe", "astronomy", "planets", "NASA"],
    "planet": ["space", "universe", "astronomy", "planets", "NASA"],
    "moon": ["space", "astronomy", "moon", "universe"],
    "animal": ["animals", "wildlife", "nature", "animal facts"],
    "ocean": ["ocean", "marine life", "deep sea", "nature"],
    "nature": ["nature", "wildlife", "earth", "science"],
    "science": ["science", "science facts", "explained", "education"],
    "technology": ["technology", "tech", "innovation", "explained"],
    "artificial intelligence": ["AI", "artificial intelligence", "technology", "future"],
    "brain": ["brain", "human body", "neuroscience", "science"],
    "earth": ["Earth", "nature", "planet", "science"],
}

def make_metadata(topic, description):
    raw_topic = topic.get("topic", "Curious World discovery").strip()
    title = topic.get("title", raw_topic).strip()
    # Keep the researched title readable; never add unrelated clickbait.
    title = re.sub(r"\s+", " ", title)[:100].strip()

    haystack = (raw_topic + " " + topic.get("narration", "")).casefold()
    tags = ["Curious World", "science", "facts", "education", "shorts"]
    for keyword, additions in TOPIC_TAGS.items():
        if keyword in haystack:
            tags.extend(additions)
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", raw_topic)
    tags.extend(words)
    # YouTube tags are metadata, not a keyword dump: deduplicate and cap.
    unique_tags = []
    seen = set()
    for tag in tags:
        normalized = tag.casefold()
        if normalized not in seen:
            seen.add(normalized)
            unique_tags.append(tag[:30])
    unique_tags = unique_tags[:15]

    hashtags = ["#Shorts", "#Science"]
    if any(word in haystack for word in ("animal", "wildlife", "cat", "shark", "octopus", "bee")):
        hashtags.append("#Nature")
    elif any(word in haystack for word in ("space", "planet", "moon", "star", "galaxy", "black hole")):
        hashtags.append("#Space")
    elif any(word in haystack for word in ("technology", "artificial intelligence", "robot", " ai ")):
        hashtags.append("#Technology")
    else:
        hashtags.append("#DidYouKnow")
    hashtags = list(dict.fromkeys(hashtags))[:3]

    clean_description = description.strip()
    if topic.get("reference_url"):
        clean_description += "\n\nResearch reference: " + topic["reference_url"]
    clean_description += (
        "\n\nWhat do you think? Share your answer in the comments! "
        "Subscribe to Curious World for more quick discoveries.\n\n"
        + " ".join(hashtags)
    )
    return title, clean_description[:5000], unique_tags

def main():
    client_id = os.environ.get("YOUTUBE_CLIENT_ID", "")
    client_secret = os.environ.get("YOUTUBE_CLIENT_SECRET", "")
    refresh_token = os.environ.get("YOUTUBE_REFRESH_TOKEN", "")
    missing = [name for name, value in [
        ("YOUTUBE_CLIENT_ID", client_id),
        ("YOUTUBE_CLIENT_SECRET", client_secret),
        ("YOUTUBE_REFRESH_TOKEN", refresh_token),
    ] if not value]
    if missing:
        raise SystemExit(
            "Automatic YouTube upload is not configured. Add these GitHub Actions secrets: "
            + ", ".join(missing)
        )

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    youtube = build("youtube", "v3", credentials=credentials)

    topic = json.loads(Path("topic.json").read_text(encoding="utf-8"))
    topic_name = " ".join(topic["topic"].casefold().split())
    history_path = Path("upload_history.json")
    try:
        upload_history = json.loads(history_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        upload_history = {"published_topics": []}
    published = upload_history.get("published_topics", [])
    if any(
        " ".join(str(item.get("topic", "")).casefold().split()) == topic_name
        for item in published if isinstance(item, dict)
    ):
        raise SystemExit(
            f"This topic was already published: {topic['topic']!r}. "
            "Skipping upload to prevent a duplicate."
        )

    description = Path("output/youtube-description.txt").read_text(encoding="utf-8")
    title, description, tags = make_metadata(topic, description)
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags,
            "categoryId": "27",
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
        },
    }
    print(f"YouTube title: {title}")
    print(f"YouTube hashtags: {' '.join(description.splitlines()[-1].split())}")
    print(f"YouTube tags ({len(tags)}): {', '.join(tags)}")

    media = MediaFileUpload(
        "output/curious-world-short.mp4",
        mimetype="video/mp4",
        resumable=True,
    )
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )
    response = request.execute()
    video_id = response.get("id")
    if not video_id:
        raise SystemExit("YouTube did not return a video ID; upload status is uncertain.")
    published.append({
        "topic": topic["topic"],
        "video_id": video_id,
        "url": f"https://www.youtube.com/shorts/{video_id}",
        "title": title,
        "published_at_utc": datetime.now(timezone.utc).isoformat(),
    })
    upload_history["published_topics"] = published[-500:]
    history_path.write_text(
        json.dumps(upload_history, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Uploaded successfully: https://www.youtube.com/shorts/{video_id}")

if __name__ == "__main__":
    main()
