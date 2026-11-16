import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

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

    topic = __import__("json").loads(Path("topic.json").read_text(encoding="utf-8"))
    description = Path("output/youtube-description.txt").read_text(encoding="utf-8")
    description += "\nResearch reference: " + topic.get("reference_url", "")
    body = {
        "snippet": {
            "title": topic["title"][:100],
            "description": description[:5000],
            "tags": ["Curious World", "science", "facts", "education", "shorts"],
            "categoryId": "27",
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": "public",
        },
    }
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
    print(f"Uploaded successfully: https://www.youtube.com/shorts/{video_id}")

if __name__ == "__main__":
    main()
