import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests
import xml.etree.ElementTree as ET

HISTORY_FILE = Path("topic_history.json")
OUTPUT_FILE = Path("topic.json")
HEADERS = {"User-Agent": "CuriousWorldTopicResearch/1.0 (educational video project)"}

EVERGREEN = [
    "Why do cats always land on their feet",
    "How octopuses solve problems",
    "Why the sky changes color at sunset",
    "How astronauts sleep in space",
    "The deepest place in the ocean",
    "Why some animals glow in the dark",
    "How bees communicate with dances",
    "What causes the northern lights",
    "How the human brain creates memories",
    "Why sharks have existed for millions of years",
    "How trees communicate underground",
    "Why Saturn has rings",
    "How butterflies transform",
    "The science of thunder and lightning",
    "Why flamingos are pink",
    "How penguins survive extreme cold",
    "What makes black holes so mysterious",
    "How your body fights germs",
    "Why some planets have two moons",
    "How dolphins use sound to understand the world",
]

ALLOW = re.compile(
    r"\b(space|planet|earth|moon|mars|nasa|astronomy|science|animal|wildlife|"
    r"ocean|deep sea|nature|weather|climate|invention|technology|robot|"
    r"artificial intelligence|ai|discovery|physics|biology|human body|"
    r"brain|dinosaur|fossil|volcano|earthquake|aurora|solar|star|galaxy)\b",
    re.I,
)
BLOCK = re.compile(
    r"\b(election|politic|president|war|weapon|murder|death|shooting|"
    r"crime|celebrity|scandal|adult|gambling|stock|crypto|betting|"
    r"sports league|match result)\b",
    re.I,
)

def get_json(url):
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    return response.json()

def history():
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"used": []}

def wikipedia_summary(topic):
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(topic.replace(" ", "_"))
    try:
        data = get_json(url)
        extract = re.sub(r"\s+", " ", data.get("extract", "")).strip()
        if len(extract) >= 180 and data.get("type") != "disambiguation":
            return extract, data.get("content_urls", {}).get("desktop", {}).get("page", "")
    except Exception as exc:
        print(f"Wikipedia lookup skipped for {topic!r}: {exc}")
    return "", ""

def trends_candidates():
    url = "https://trends.google.com/trending/rss?geo=US"
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    items = []
    for item in root.findall(".//item"):
        title = (item.findtext("title") or "").strip()
        traffic = (item.findtext("{https://trends.google.com/trending/rss}approx_traffic") or "")
        if not title or BLOCK.search(title) or not ALLOW.search(title):
            continue
        items.append({"topic": title, "source": "Google Trends US", "traffic": traffic})
    return items

def youtube_candidates():
    # Public YouTube search feed: recent science/nature uploads provide an extra topic signal.
    url = "https://www.youtube.com/feeds/videos.xml?search_query=science+space+animals+technology"
    response = requests.get(url, headers=HEADERS, timeout=25)
    response.raise_for_status()
    root = ET.fromstring(response.content)
    atom = "{http://www.w3.org/2005/Atom}"
    items = []
    for entry in root.findall(f"{atom}entry"):
        title = (entry.findtext(f"{atom}title") or "").strip()
        if not title or BLOCK.search(title) or not ALLOW.search(title):
            continue
        items.append({"topic": title, "source": "Recent YouTube science/nature uploads", "traffic": ""})
    return items

def make_narration(topic, extract):
    sentences = re.split(r"(?<=[.!?])\s+", extract)
    facts = " ".join(sentences[:4]).strip()
    facts = facts[:560].rsplit(" ", 1)[0] if len(facts) > 560 else facts
    return (
        f"What makes {topic} so fascinating? "
        f"{facts} "
        "Scientists keep studying questions like this because every discovery "
        "can reveal something surprising about our world. "
        "Follow Curious World for more amazing discoveries."
    )

def main():
    used = set(x.casefold() for x in history().get("used", []))
    candidates = []
    try:
        candidates = trends_candidates()
        print(f"Google Trends supplied {len(candidates)} safe science/nature candidates.")
    except Exception as exc:
        print(f"Google Trends unavailable: {exc}")

    try:
        yt_candidates = youtube_candidates()
        candidates.extend(yt_candidates)
        print(f"YouTube recent-upload feed supplied {len(yt_candidates)} additional candidates.")
    except Exception as exc:
        print(f"YouTube topic feed unavailable: {exc}")

    # Prefer a fresh, relevant trend or recent video topic with a usable reference article.
    for item in candidates[:30]:
        topic = item["topic"]
        if topic.casefold() in used:
            continue
        extract, source_url = wikipedia_summary(topic)
        if extract:
            item.update({"extract": extract, "source_url": source_url, "kind": "trending"})
            break
    else:
        item = None

    # Mix mode: use a relevant daily trend when available; otherwise rotate evergreen topics.
    if item is None:
        for topic in EVERGREEN:
            if topic.casefold() not in used:
                extract, source_url = wikipedia_summary(topic)
                if extract:
                    item = {
                        "topic": topic,
                        "source": "Curious World evergreen research list",
                        "traffic": "",
                        "extract": extract,
                        "source_url": source_url,
                        "kind": "evergreen",
                    }
                    break

    if item is None:
        raise SystemExit("Could not find a fresh topic with a usable factual reference. No video was generated.")

    topic = item["topic"]
    title = topic if len(topic) < 65 else topic[:62].rsplit(" ", 1)[0] + "..."
    query = topic.replace("?", "").replace(":", " ")
    payload = {
        "topic": topic,
        "title": title,
        "kind": item["kind"],
        "research_source": item["source"],
        "reference_url": item["source_url"],
        "narration": make_narration(topic, item["extract"]),
        "scenes": [
            {"query": query, "caption": title.upper()},
            {"query": query + " documentary close up", "caption": "THE SCIENCE BEHIND IT"},
            {"query": query + " nature science cinematic", "caption": "WHAT WILL WE DISCOVER NEXT?"},
        ],
        "selected_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    OUTPUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    record = history()
    record.setdefault("used", []).append(topic)
    record["used"] = record["used"][-180:]
    HISTORY_FILE.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Selected {item['kind']} topic: {topic}")
    print(f"Research reference: {item['source_url']}")

if __name__ == "__main__":
    main()
