import math
import os
import random
import subprocess
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, SECONDS = 720, 1280, 24, 36
FRAMES = FPS * SECONDS
OUT = "output/curious-world-short.mp4"
os.makedirs("output", exist_ok=True)

BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
REG = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
font_hook = ImageFont.truetype(BOLD, 54)
font_head = ImageFont.truetype(BOLD, 39)
font_body = ImageFont.truetype(REG, 27)
font_tag = ImageFont.truetype(BOLD, 19)

random.seed(23)
STARS = [(random.randrange(W), random.randrange(H), random.choice([1, 1, 2, 3]))
         for _ in range(110)]

NARRATION = (
    "What if Earth stopped spinning... right now? "
    "The ground might stop, but the atmosphere and everything not firmly attached "
    "would keep moving. Near the equator, the speed is over one thousand six hundred "
    "kilometers per hour. The result could be devastating: extreme winds, flying debris, "
    "and enormous ocean surges. But here is the twist. Earth would not simply become "
    "a quiet, motionless planet. Its rotation shapes our days, our weather, and our oceans. "
    "A sudden stop would be a global catastrophe. Would you want to see what happens next?"
)

def fit_lines(draw, text, font, max_width):
    words, lines, current = text.split(), [], ""
    for word in words:
        test = (current + " " + word).strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

def centered(draw, text, y, font, fill, max_width=620, gap=10):
    lines = fit_lines(draw, text, font, max_width)
    line_h = font.size + gap
    total = len(lines) * line_h - gap
    yy = y - total // 2
    for line in lines:
        b = draw.textbbox((0, 0), line, font=font, stroke_width=1)
        x = (W - (b[2] - b[0])) // 2
        draw.text((x, yy), line, font=font, fill=fill,
                  stroke_width=1, stroke_fill=(3, 8, 20))
        yy += line_h

def background(t):
    im = Image.new("RGB", (W, H))
    pix = im.load()
    for y in range(H):
        q = y / H
        c = (int(4 + 4*q), int(9 + 13*q), int(28 + 28*q))
        for x in range(W):
            pix[x, y] = c
    d = ImageDraw.Draw(im)
    for x, y, r in STARS:
        yy = int((y + t * (8 + r*5)) % H)
        d.ellipse((x, yy, x+r, yy+r), fill=(135, 174, 220))
    return im

def draw_earth(draw, t, cx=360, cy=405, radius=185):
    # Atmosphere and ocean
    draw.ellipse((cx-radius-13, cy-radius-13, cx+radius+13, cy+radius+13),
                fill=(30, 115, 205))
    draw.ellipse((cx-radius, cy-radius, cx+radius, cy+radius),
                fill=(20, 74, 150))
    # Stylized continents that drift around the globe
    shift = int((t * 26) % 150)
    shapes = [
        [(270,300),(300,265),(345,275),(365,310),(340,340),(325,380),(290,360),(275,330)],
        [(385,365),(425,350),(455,380),(445,420),(420,445),(405,420)],
        [(285,430),(325,450),(340,500),(320,545),(290,520),(275,475)],
        [(430,270),(470,290),(480,320),(450,335),(425,315)]
    ]
    for poly in shapes:
        moved = [((x-360+shift) % 330 + 195, y) for x,y in poly]
        draw.polygon(moved, fill=(45, 153, 111))
    draw.arc((cx-radius-4,cy-radius-4,cx+radius+4,cy+radius+4),
             205, 330, fill=(125, 210, 255), width=5)
    # Highlight
    draw.ellipse((cx-radius+35, cy-radius+28, cx-radius+62, cy-radius+55),
                 fill=(75, 145, 215))

def scene_one(im, t):
    d = ImageDraw.Draw(im)
    draw_earth(d, t)
    # Rotation arrows
    angle = t * 2.4
    for k in range(3):
        y = 185 + k*18
        x = 360 + int(math.sin(angle+k)*95)
        d.arc((x-80,y-30,x+80,y+30), 190, 340, fill=(104,205,255), width=4)
    centered(d, "WHAT IF EARTH", 700, font_hook, (115,220,255))
    centered(d, "STOPPED SPINNING?", 775, font_head, (255,255,255))
    centered(d, "The planet stops. Everything else keeps moving.", 890,
             font_body, (215,228,246), max_width=600)

def scene_two(im, t):
    d = ImageDraw.Draw(im)
    # Fast-moving wind streaks
    for i in range(18):
        y = 210 + (i*61) % 650
        x = int((i*97 + t*310) % (W+180)) - 90
        d.line((x,y,x+95+(i%4)*24,y-12), fill=(80,174,225), width=2+(i%3))
    # City skyline
    base = 760
    buildings = [(15,260,150),(95,190,130),(185,300,165),(290,215,140),
                 (390,330,180),(500,230,145),(600,290,170)]
    for x,w,h in buildings:
        d.rectangle((x,base-h,x+w,base), fill=(12,28,58), outline=(61,111,155), width=3)
        for wx in range(x+15,x+w-8,28):
            for wy in range(base-h+20,base-15,35):
                d.rectangle((wx,wy,wx+8,wy+12), fill=(245,184,92))
    # Flying debris silhouettes
    for i in range(9):
        x = int((i*111 + t*390) % (W+100))-50
        y = 390 + int(math.sin(t*2+i)*95)
        d.polygon([(x,y),(x+18,y-8),(x+31,y+5),(x+9,y+13)], fill=(190,205,220))
    centered(d, "THE AIR KEEPS MOVING", 875, font_head, (255,205,120))
    centered(d, "Extreme winds could sweep across the surface.", 965,
             font_body, (230,238,248), max_width=610)

def scene_three(im, t):
    d = ImageDraw.Draw(im)
    # Stylized rising ocean waves
    for layer in range(5):
        y0 = 700 + layer*75
        pts = [(0,H)]
        for x in range(0,W+1,12):
            y = y0 + int(math.sin(x/65 + t*2.4 + layer)*24)
            pts.append((x,y))
        pts.append((W,H))
        d.polygon(pts, fill=(10+layer*3, 65+layer*12, 115+layer*13))
        d.line(pts[1:-1], fill=(80,185,220), width=3)
    # Sun / horizon
    d.ellipse((275,275,445,445), fill=(245,158,85))
    d.rectangle((0,530,W,555), fill=(40,112,155))
    centered(d, "OCEANS IN MOTION", 860, font_head, (255,210,145))
    centered(d, "Enormous surges could reshape coastlines.", 955,
             font_body, (235,243,250), max_width=610)

def draw_overlay(im, t):
    d = ImageDraw.Draw(im)
    # Top channel tag
    d.rounded_rectangle((26,28,250,70), radius=18, fill=(9,25,52), outline=(60,130,190))
    d.text((43,39), "CURIOUS WORLD", font=font_tag, fill=(155,220,255))
    # Scene progress
    progress = min(t / SECONDS, 1)
    d.rounded_rectangle((30,1220,690,1230), radius=5, fill=(38,55,78))
    d.rounded_rectangle((30,1220,30+int(660*progress),1230), radius=5, fill=(75,190,255))

def make_frame(n):
    t = n/FPS
    im = background(t)
    if t < 12:
        scene_one(im,t)
    elif t < 24:
        scene_two(im,t-12)
    else:
        scene_three(im,t-24)
    draw_overlay(im,t)
    return im

# Build narration locally with a free system voice (no API key).
subprocess.run([
    "espeak-ng", "-v", "en-us", "-s", "155", "-p", "48",
    "-a", "175", "-w", "output/narration.wav", NARRATION
], check=True)

# Render silent video frames to H.264.
cmd = [
    "ffmpeg","-y","-loglevel","error",
    "-f","rawvideo","-vcodec","rawvideo","-pix_fmt","rgb24",
    "-s",f"{W}x{H}","-r",str(FPS),"-i","-",
    "-an","-c:v","libx264","-preset","ultrafast",
    "-pix_fmt","yuv420p","-movflags","+faststart","output/video_silent.mp4"
]
proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
try:
    for n in range(FRAMES):
        proc.stdin.write(make_frame(n).tobytes())
finally:
    proc.stdin.close()
if proc.wait() != 0:
    raise RuntimeError("FFmpeg video rendering failed.")

# Add a quiet cinematic tone bed under narration; voice remains foreground.
subprocess.run([
    "ffmpeg","-y","-loglevel","error",
    "-i","output/video_silent.mp4","-i","output/narration.wav",
    "-f","lavfi","-i","sine=frequency=110:sample_rate=44100:duration=36",
    "-filter_complex",
    "[1:a]volume=1.0,apad=pad_dur=36[voice];"
    "[2:a]volume=0.035,lowpass=f=240,afade=t=in:st=0:d=2,afade=t=out:st=32:d=4[bed];"
    "[voice][bed]amix=inputs=2:duration=longest:dropout_transition=2,"
    "alimiter=limit=0.95[a]",
    "-map","0:v:0","-map","[a]","-c:v","copy","-c:a","aac",
    "-b:a","128k","-shortest","-movflags","+faststart",OUT
], check=True)

print(f"Professional-style short created: {OUT}")
