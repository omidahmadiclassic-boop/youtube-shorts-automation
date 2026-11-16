import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests
import xml.etree.ElementTree as ET

HISTORY_FILE = Path("topic_history.json")
OUTPUT_FILE = Path("topic.json")
HEADERS = {
    "User-Agent": "CuriousWorldTopicResearch/2.0 (educational YouTube Shorts project; contact: repository owner)"
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)

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
    r"artificial intelligence|\bai\b|discovery|physics|biology|human body|"
    r"brain|dinosaur|fossil|volcano|earthquake|aurora|solar|star|galaxy|"
    r"cat|octopus|bee|shark|tree|butterfly|penguin|dolphin|flamingo|black hole)\b",
    re.I,
)
BLOCK = re.compile(
    r"\b(election|politic|president|war|weapon|murder|death|shooting|"
    r"crime|celebrity|scandal|adult|gambling|stock|crypto|betting|"
    r"sports league|match result)\b",
    re.I,
)

def request_json(url, params=None, attempts=3):
    last_error = None
    for attempt in range(attempts):
        try:
            response = SESSION.get(url, params=params, timeout=20)
            if response.status_code == 429 or response.status_code >= 500:
                wait = min(2 ** attempt, 8)
                print(f"Temporary HTTP {response.status_code}; retrying in {wait}s.")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt + 1 < attempts:
                time.sleep(min(2 ** attempt, 8))
    if last_error:
        raise last_error
    raise RuntimeError("Request failed after retries.")

def history():
    try:
        data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"used": []}
    except (OSError, json.JSONDecodeError):
        return {"used": []}

def wikipedia_summary(topic):
    # Search first and use Wikipedia's canonical page title. This is much more
    # reliable than sending a full question-style topic to the summary endpoint.
    search_data = request_json(
        "https://en.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "list": "search",
            "srsearch": topic,
            "format": "json",
            "srlimit": 5,
        },
    )
    results = search_data.get("query", {}).get("search", [])
    for result in results:
        page_title = result.get("title", "").strip()
        if not page_title:
            continue
        try:
            data = request_json(
                "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(page_title.replace(" ", "_"))
            )
            extract = re.sub(r"\s+", " ", data.get("extract", "")).strip()
            if len(extract) >= 180 and data.get("type") != "disambiguation":
                page_url = (
                    data.get("content_urls", {}).get("desktop", {}).get("page")
                    or "https://en.wikipedia.org/wiki/" + quote(page_title.replace(" ", "_"))
                )
                return extract, page_url, page_title
        except Exception as exc:
            print(f"Skipping Wikipedia result {page_title!r}: {exc}")
    return "", "", ""

def trends_candidates():
    # Google has changed its RSS endpoints before. Try both public RSS variants;
    # failure is non-fatal because the evergreen rotation is always available.
    urls = [
        "https://trends.google.com/trending/rss?geo=US",
        "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US",
    ]
    last_error = None
    for url in urls:
        try:
            response = SESSION.get(url, timeout=20)
            response.raise_for_status()
            root = ET.fromstring(response.content)
            items = []
            for item in root.findall(".//item"):
                title = (item.findtext("title") or "").strip()
                if not title or BLOCK.search(title) or not ALLOW.search(title):
                    continue
                items.append({
                    "topic": title,
                    "source": "Google Trends US",
                    "traffic": item.findtext("{https://trends.google.com/trending/rss}approx_traffic") or "",
                })
            if items:
                return items
        except Exception as exc:
            last_error = exc
            print(f"Google Trends RSS unavailable ({url}): {exc}")
    if last_error:
        print("Continuing with evergreen topics; Google Trends is optional.")
    return []

def make_narration(topic, extract):
    # A concise script paced for a 30–40 second Short.
    sentences = re.split(r"(?<=[.!?])\\s+", extract)
    facts = " ".join(sentences[:3]).strip()
    if len(facts) > 360:
        facts = facts[:360].rsplit(" ", 1)[0].rstrip(" ,;:") + "."
    return (
        f"Here is something surprising about {topic}. "
        f"{facts} "
        "And that is only part of the story. "
        "Follow Curious World for more quick discoveries."
    )

def main():
    used = {str(x).casefold() for x in history().get("used", [])}
    candidates = []

    try:
        candidates = trends_candidates()
        print(f"Google Trends supplied {len(candidates)} relevant candidates.")
    except Exception as exc:
        print(f"Trend discovery skipped safely: {exc}")

    # Do not depend on YouTube's undocumented/public search feed: it may return
    # HTTP 400. Google Trends is a bonus signal, not a hard requirement.
    ordered = [
        (item, "trending") for item in candidates
        if item["topic"].casefold() not in used
    ]
    ordered.extend(
        (
            {
                "topic": topic,
                "source": "Curious World evergreen research list",
                "traffic": "",
            },
            "evergreen",
        )
        for topic in EVERGREEN
        if topic.casefold() not in used
    )

    selected = None
    for item, kind in ordered:
        topic = item["topic"]
        try:
            extract, source_url, canonical_title = wikipedia_summary(topic)
        except Exception as exc:
            print(f"Research lookup failed for {topic!r}: {exc}")
            continue
        if extract:
            selected = {
                **item,
                "topic": topic,
                "research_title": canonical_title,
                "extract": extract,
                "source_url": source_url,
                "kind": kind,
            }
            break

    if selected is None:
        raise SystemExit(
            "No topic could be verified from Wikipedia after retries. "
            "No video was generated; try again later."
        )

    topic = selected["topic"]
    title = topic if len(topic) < 65 else topic[:62].rsplit(" ", 1)[0] + "..."
    query = topic.replace("?", "").replace(":", " ")
    payload = {
        "topic": topic,
        "title": title,
        "kind": selected["kind"],
        "research_source": selected["source"],
        "research_title": selected["research_title"],
        "reference_url": selected["source_url"],
        "narration": make_narration(topic, selected["extract"]),
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
    print(f"Selected {selected['kind']} topic: {topic}")
    print(f"Verified Wikipedia reference: {selected['source_url']}")

if __name__ == "__main__":
    main()
