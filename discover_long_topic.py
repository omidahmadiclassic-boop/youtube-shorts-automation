import json, re, time
from pathlib import Path
from urllib.parse import quote
import requests

HISTORY=Path("long_topic_history.json")
OUT=Path("long_topic.json")
EVERGREEN=[
 "The mystery of black holes and how they shape galaxies",
 "How octopuses became masters of camouflage and problem solving",
 "The hidden world of deep ocean creatures",
 "How the northern lights are created",
 "Why the dinosaurs disappeared and what fossils reveal",
 "How the human brain builds and stores memories",
 "The surprising science of animal migration",
 "How volcanoes build and reshape the Earth",
 "The search for water and life on Mars",
 "How bees communicate and help ecosystems",
 "The science behind sleep and dreams",
 "How the universe began and how scientists study it",
 "Why the ocean is still largely unexplored",
 "How the largest trees survive for thousands of years",
]
S=requests.Session()
S.headers["User-Agent"]="CuriousWorldLongform/1.0 (educational project)"
def get(url,params=None):
 r=S.get(url,params=params,timeout=35); r.raise_for_status(); return r.json()
def main():
 try: used=set(json.loads(HISTORY.read_text()).get("used",[]))
 except Exception: used=set()
 for topic in EVERGREEN:
  if topic in used: continue
  try:
   data=get("https://en.wikipedia.org/w/api.php",{"action":"query","list":"search","srsearch":topic,"format":"json","srlimit":5})
   for hit in data.get("query",{}).get("search",[]):
    title=hit["title"]
    page=get("https://en.wikipedia.org/w/api.php",{"action":"query","prop":"extracts","explaintext":1,"exsectionformat":"plain","titles":title,"format":"json","redirects":1})
    pages=page.get("query",{}).get("pages",{})
    article=next(iter(pages.values()),{})
    extract=re.sub(r"\s+"," ",article.get("extract","")).strip()
    if len(extract)<2600: continue
    sentences=re.split(r"(?<=[.!?])\s+",extract)
    sentences=[x.strip() for x in sentences if len(x.strip())>45]
    # Use a curated factual passage, not fabricated filler. Target about 650-850 spoken words.
    body=" ".join(sentences[:75])
    if len(body)<4000: continue
    intro=f"What if the world we thought we understood was hiding a much bigger story? Today on Curious World, we're exploring {topic.lower()}. And by the end, you'll see why this subject is far more fascinating than it first appears."
    outro="So the next time you look at this part of our world, remember how much is still waiting to be discovered. Which detail surprised you most? Share it in the comments, and subscribe to Curious World for more carefully researched stories."
    script= intro+" "+body+" "+outro
    # Keep the first pilot to a realistic 5-8 minute narration range.
    words=script.split()
    if len(words)>1050: script=" ".join(words[:1050])
    payload={"topic":topic,"title":title,"research_title":title,"reference_url":"https://en.wikipedia.org/wiki/"+quote(title.replace(" ","_")),"script":script,"word_count":len(script.split()),"selected_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    OUT.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    used.add(topic); HISTORY.write_text(json.dumps({"used":sorted(used)},indent=2),encoding="utf-8")
    print(f"Selected long-form topic: {topic}; {payload['word_count']} words; source {payload['reference_url']}")
    return
  except Exception as e: print(f"Skipping {topic}: {e}")
 raise SystemExit("No unused long-form topic had enough verifiable source material. No video was generated.")
if __name__=="__main__": main()
