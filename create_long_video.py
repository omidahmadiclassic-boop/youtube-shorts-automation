import json, os, re, random, shutil, subprocess, textwrap
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont

W,H,FPS=1920,1080,25
OUT=Path("output/long"); ASSETS=OUT/"assets"
KEY=os.environ.get("PIXABAY_API_KEY","").strip()
if not KEY: raise SystemExit("Missing PIXABAY_API_KEY")
topic=json.loads(Path("long_topic.json").read_text(encoding="utf-8"))
TITLE=topic["title"]; SCRIPT=topic["script"]
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
def run(cmd): subprocess.run(cmd,check=True)
def terms(s,n=8):
 stop={"about","after","also","because","being","between","could","during","first","from","have","into","more","most","often","other","over","some","such","than","that","their","there","these","they","this","those","through","under","using","very","were","when","where","which","while","with","would","your","the","and","for","are","was","its","has","had","not","but","can","may","one","two","how","why","what","world","thought","understood","hiding","bigger","story","today","exploring","curious","we","our","you","see","subject","fascinating","appears","first","might","just","like","many","much","every","even","only","known","called","make","made","take","takes","show","shows","look","looks","way","ways","thing","things","people","something","anything","everything","really","still","back","new","old","large","small"}
 out=[]
 for x in re.findall(r"[A-Za-z][A-Za-z-]{2,}",s.lower()):
  if x not in stop and x not in out: out.append(x)
  if len(out)>=n: break
 return out
def fetch_clip(query,idx,used_ids,anchor_terms=None):
 anchor=set(anchor_terms or [])
 scene=set(terms(query,10))
 variants=[" ".join(list(anchor)[:4]+list(scene)[:3])," ".join(list(anchor)[:3])," ".join(list(anchor)[:2]+["space","astronomy"])," ".join(list(anchor)[:2])]
 variants=list(dict.fromkeys(q.strip() for q in variants if q.strip()))
 candidates={}
 for search_query in variants:
  try:
   resp=requests.get("https://pixabay.com/api/videos/",params={"key":KEY,"q":search_query,"video_type":"film","safesearch":"true","order":"popular","per_page":50},timeout=40)
   resp.raise_for_status()
   data=resp.json()
  except Exception as e:
   print(f"Pixabay search failed for {search_query!r}: {e}")
   continue
  for h in data.get("hits",[]):
   if h.get("id") in used_ids: continue
   tags=set(re.findall(r"[a-z][a-z-]{2,}",(h.get("tags") or "").lower()))
   blocked={"news","reporter","television","broadcast","subtitle","subtitles","caption","captions","text","typography","logo","watermark","screenshot","poster","headline"}
   if tags & blocked: continue
   ah=len(anchor & tags); sh=len(scene & tags)
   if ah<1: continue
   score=ah*4+sh
   if score>=2: candidates[h.get("id")]=(score,ah,sh,h,search_query)
 ranked=sorted(candidates.values(),key=lambda z:(z[0],z[1],z[2],z[3].get("downloads",0)),reverse=True)
 for score,ah,sh,h,used_query in ranked:
  videos=h.get("videos",{})
  v=videos.get("large") or videos.get("medium") or videos.get("small")
  if not v or not v.get("url"): continue
  p=ASSETS/f"clip_{idx:02d}.mp4"
  try:
   with requests.get(v["url"],stream=True,timeout=90) as r:
    r.raise_for_status()
    with p.open("wb") as f:
     for chunk in r.iter_content(1024*1024):
      if chunk: f.write(chunk)
   if p.stat().st_size>50000:
    return p,{"query":query,"pixabay_query":used_query,"creator":h.get("user","Pixabay contributor"),"url":h.get("pageURL"),"id":h.get("id"),"matched_anchor_terms":ah,"matched_scene_terms":sh,"relevance_score":score}
  except Exception as e:
   print(f"Could not download Pixabay clip {h.get('id')}: {e}")
   p.unlink(missing_ok=True)
 raise RuntimeError("No relevant, unused Pixabay footage found after fallback searches for scene: "+query+"; no unrelated footage was substituted.")
def main():
 if OUT.exists(): shutil.rmtree(OUT)
 ASSETS.mkdir(parents=True)
 # Sentence-led 12-scene sequence; each visual query is anchored to the researched topic.
 sentences=re.split(r"(?<=[.!?])\s+",SCRIPT)
 chunks=[]
 per=max(2,(len(sentences)+11)//12)
 for i in range(12):
  part=sentences[i*per:(i+1)*per]
  if not part: part=sentences[-2:]
  chunks.append(" ".join(part))
 narration=OUT/"narration.mp3"; srt=OUT/"narration.srt"
 voice=random.choice(["en-US-AriaNeural","en-US-JennyNeural","en-US-GuyNeural","en-US-EricNeural","en-US-MichelleNeural","en-US-ChristopherNeural","en-US-SteffanNeural"])
 Path(OUT/"script.txt").write_text(SCRIPT,encoding="utf-8")
 run(["edge-tts","--voice",voice,"--rate=+0%","--text",SCRIPT,"--write-media",str(narration),"--write-subtitles",str(srt)])
 dur=float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","default=nw=1:nk=1",str(narration)],capture_output=True,text=True,check=True).stdout.strip())
 scene_sec=dur/12
 credits=[]; segments=[]; used_ids=set()
 topic_terms=terms(TITLE,6)
 topic_text=(TITLE+" "+SCRIPT[:1200]).lower()
 if any(k in topic_text for k in ("black hole","black holes","galax")):
  topic_terms=list(dict.fromkeys(["black","hole","holes","galaxy","galaxies","space","astronomy"]+topic_terms))
 for i,chunk in enumerate(chunks,1):
  scene_terms=terms(chunk,8)
  combined=list(dict.fromkeys(topic_terms+scene_terms))
  query=" ".join(combined[:8])
  clip,credit=fetch_clip(query,i,used_ids,topic_terms); used_ids.add(credit['id']); credits.append(credit)
  seg=ASSETS/f"segment_{i:02d}.mp4"; vf=f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},fps={FPS},setsar=1,format=yuv420p"
  run(["ffmpeg","-y","-loglevel","error","-stream_loop","-1","-i",str(clip),"-vf",vf,"-t",f"{scene_sec:.3f}","-an","-c:v","libx264","-preset","veryfast","-crf","22",str(seg)])
  segments.append(seg)
 concat=OUT/"concat.txt"; concat.write_text("".join(f"file '{p.resolve()}'\n" for p in segments),encoding="utf-8")
 silent=OUT/"silent.mp4"
 run(["ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(silent)])
 final=OUT/"curious-world-long.mp4"; fade=max(0,dur-2)
 run(["ffmpeg","-y","-loglevel","error","-i",str(silent),"-i",str(narration),"-vf","subtitles=output/long/narration.srt:force_style='FontName=DejaVu Sans,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=2,MarginV=35'","-af",f"highpass=f=75,lowpass=f=14000,loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.2,afade=t=out:st={fade:.2f}:d=2","-c:v","libx264","-preset","veryfast","-crf","21","-c:a","aac","-b:a","192k","-shortest","-movflags","+faststart",str(final)])
 # Generate a thumbnail as a separate artifact.
 im=Image.new("RGB",(1280,720),(8,20,38)); d=ImageDraw.Draw(im); font=ImageFont.truetype(FONT,64)
 lines=textwrap.wrap(TITLE.upper(),28)[:3]; y=230
 for line in lines:
  box=d.textbbox((0,0),line,font=font); d.text(((1280-(box[2]-box[0]))/2,y),line,font=font,fill="white",stroke_width=2,stroke_fill=(0,0,0)); y+=90
 d.text((50,640),"CURIOUS WORLD",font=ImageFont.truetype(FONT,30),fill=(130,210,255)); im.save(OUT/"thumbnail.jpg",quality=92)
 (OUT/"visual-match-report.json").write_text(json.dumps(credits,ensure_ascii=False,indent=2),encoding="utf-8")
 (OUT/"video-credits.txt").write_text("Research: "+topic["reference_url"]+"\nVisual footage: Pixabay Content License. Review individual asset terms.\n"+ "\n".join(f"{x['query']} | matched {x['matched_terms']}/{x['query_terms']} | {x['creator']} | {x['url']} | {x['id']}" for x in credits),encoding="utf-8")
 (OUT/"youtube-description.txt").write_text(f"{TITLE}\n\nA researched Curious World story. Sources and footage credits are included in the accompanying credits file.\n\nWhat surprised you most? Share your thoughts below.\n\n#Science #CuriousWorld #Documentary",encoding="utf-8")
 print(f"Created {final}; narration {dur/60:.1f} minutes; {len(SCRIPT.split())} words; voice {voice}")
if __name__=="__main__": main()
