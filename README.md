# Curious World Daily Shorts Automation

A zero-paid-API-cost YouTube Shorts workflow that runs on GitHub Actions cloud runners. Your home computer does not need to be on.

## Daily workflow

- Runs daily at 13:23 UTC (14:23 in winter / 15:23 in summer in France and Germany), plus manual dispatch.
- Checks Google Trends US for relevant science, nature, space, animal, and technology topics.
- Falls back to a rotating evergreen topic list when no suitable fresh trend has a reliable reference.
- Uses Wikipedia article summaries as a factual research reference and records the selected topic to avoid exact repeats.
- Creates a vertical Short using three scene-specific Pixabay footage searches, a randomly selected English Edge TTS neural voice, synchronized burned-in captions, FFmpeg, and channel graphics.
- Validates the finished MP4 before upload (portrait format, duration, video/audio streams, subtitles, and source credits); a failed check blocks publishing.
- Records published topics and YouTube video IDs to reduce accidental duplicate uploads.
- Builds a topic-specific YouTube title, relevant tags, and up to three hashtags; adds a viewer question and subscription prompt to the description.\n- Uploads the finished video publicly using the YouTube Data API.
- Saves the MP4, credits, description, and selected topic as a seven-day workflow artifact.

## Required GitHub Actions secrets

The topic research and voice generation do not need paid AI API keys. Pixabay and YouTube credentials are needed for footage and publishing:

- `PIXABAY_API_KEY`
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

Add them under repository **Settings → Secrets and variables → Actions → New repository secret**.

### YouTube upload setup

1. In Google Cloud Console, create or select a project and enable **YouTube Data API v3**.
2. Configure the OAuth consent screen and create an OAuth client ID of type **Desktop app**.
3. Authorize the YouTube channel with the scope `https://www.googleapis.com/auth/youtube.upload` and obtain a refresh token for that OAuth client.
4. Save the OAuth client ID, client secret, and refresh token as the three GitHub secrets above.
5. In YouTube Studio, set the channel's audience and upload defaults correctly before enabling public automatic publishing.

Do not put OAuth credentials or refresh tokens in repository files or commit them.

## Manual test

Open **Actions → Curious World Daily Shorts → Run workflow**. Check the run logs and the `curious-world-short` artifact.

## Important limitations

- Topic selection is a free research-and-ranking pipeline with reusable script templates; it does not call a paid generative-AI model or claim to measure YouTube view counts.
- Google Trends and Wikipedia can be unavailable or return unsuitable results. In that case the workflow uses an unused evergreen topic or stops rather than inventing facts.
- Narration length determines scene pacing, and Edge TTS generates subtitle timing that is burned into the final Short. Scene searches are derived from individual research sentences.\n- A trend is not proof that a topic will get views. Titles, clips, and scripts still need periodic quality review. Hashtags and tags provide context but cannot guarantee views; viewer retention, the opening seconds, and topic/clip relevance matter much more.
- Automatic public upload starts only after all YouTube OAuth secrets are configured.
- Pixabay clips are selected by search relevance and popularity; review the included source credits and license before relying on any individual asset.
- GitHub Actions scheduled runs can be delayed by GitHub and may be disabled after prolonged repository inactivity. Check the Actions tab if a scheduled run does not appear.

## Cost

The workflow is designed around GitHub Actions, Google Trends RSS, Wikipedia summaries, Pixabay's API/free footage, Edge TTS, and FFmpeg. It does not require a paid LLM or paid video-rendering API. Free service limits and terms apply.
