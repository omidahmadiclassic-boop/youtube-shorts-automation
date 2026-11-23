# Curious World YouTube Automation

This repository contains two separate workflows. They use free research sources, Pixabay footage, Edge TTS, FFmpeg, and GitHub Actions. No paid LLM or paid video-rendering API is required.

## Daily Shorts
- Runs daily at 13:23 UTC, plus manual dispatch.
- Researches science, nature, space, animals, and technology; filters weather and general news.
- Produces a vertical Short with scene-specific Pixabay searches, English Edge TTS narration, and small bottom subtitles.
- Adds topic-specific title, description, tags, and hashtags; validates the MP4 before upload.
- Uploads publicly using the configured YouTube OAuth secrets and records duplicate history.

## Weekly long-form video (new pilot workflow)
- Runs every Sunday at 15:00 UTC, plus manual dispatch.
- Chooses a fresh topic from a curated evergreen list and retrieves a supporting English Wikipedia article extract.
- Builds a researched narration from the source text, divides it into 12 visual sections, searches Pixabay for relevant footage, and produces a 16:9 H.264/AAC video with synchronized subtitles.
- Produces a separate 1280x720 thumbnail, script, description, and footage/source credits.
- Validates the result (4–15 minute duration, landscape video, audio/video streams, subtitles, thumbnail, and credits).
- Uploads a 14-day review artifact. **It does not publish long-form videos automatically.** Review the first outputs for factual accuracy, narration quality, visual relevance, and audience suitability before enabling public upload.

## Required GitHub Actions secrets
- `PIXABAY_API_KEY`
- `YOUTUBE_CLIENT_ID`
- `YOUTUBE_CLIENT_SECRET`
- `YOUTUBE_REFRESH_TOKEN`

Add them under repository **Settings → Secrets and variables → Actions**. The long-form review workflow needs only `PIXABAY_API_KEY`; the Shorts upload workflow uses the YouTube OAuth secrets.

## Testing
- Shorts: **Actions → Curious World Daily Shorts → Run workflow**.
- Long-form pilot: **Actions → Curious World Weekly Long Video → Run workflow**.
- Open the successful run and download its artifact named `curious-world-long-video-review`. Review the MP4 and thumbnail before publishing.

## Important quality and monetization notes
- A video workflow cannot guarantee views, full watch-through, or monetization approval.
- Long-form narration is based on the retrieved source article, not an AI fact-checking or editorial model. Check the script against its cited source before publishing.
- Pixabay search tags are only a relevance signal. They do not provide frame-level visual understanding or reliable detection of text embedded in footage. Inspect the rendered video.
- The first long-form version uses stock footage and narration. To strengthen originality and viewer retention, review the edit, add meaningful original explanation and visual storytelling, and avoid repetitive templated uploads.
- Check YouTube Analytics audience-retention graphs after publication. Improve the opening, pacing, and sections where viewers leave.
- Correctly set the channel's audience (made for kids or not) based on the actual content. Do not choose an audience setting merely to gain features.
- Public long-form auto-upload is intentionally not enabled until the first review outputs pass a human quality check.

## Cost
The workflows use GitHub Actions, public Wikipedia endpoints, Pixabay API/free footage, Edge TTS, and FFmpeg. Free-tier limits, licensing terms, and service availability apply.
