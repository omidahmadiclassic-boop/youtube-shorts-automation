
import os
import math
import random
import subprocess
from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 720, 1280
FPS = 24
DURATION = 18
TOTAL_FRAMES = FPS * DURATION

OUTPUT = "output/curious-world-short.mp4"
os.makedirs("output", exist_ok=True)

# Use fonts already available on GitHub's Ubuntu runner.
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

title_font = ImageFont.truetype(FONT_BOLD, 58)
main_font = ImageFont.truetype(FONT_BOLD, 45)
small_font = ImageFont.truetype(FONT_REGULAR, 27)

scenes = [
    ("WHAT IF EARTH", "STOPPED SPINNING?", "Imagine the entire planet suddenly stopped..."),
    ("THE CONSEQUENCES", "WOULD BE EXTREME", "Everything not attached to the ground would keep moving."),
    ("WOULD WE SURVIVE?", "NOT EASILY.", "A sudden stop could change life on Earth forever."),
]

# Fixed star positions make the animation consistent between runs.
random.seed(12)
stars = [
    (random.randint(0, WIDTH), random.randint(0, HEIGHT),
     random.randint(1, 3), random.uniform(0.5, 2.0))
    for _ in range(90)
]

def centered_text(draw, text, y, font, fill, max_width=650):
    words = text.split()
    lines, current = [], ""

    for word in words:
        test = f"{current} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)

    line_height = font.size + 15
    for i, line in enumerate(lines):
        box = draw.textbbox((0, 0), line, font=font)
        x = (WIDTH - (box[2] - box[0])) // 2
        draw.text((x, y + i * line_height), line, font=font, fill=fill)

def make_frame(frame_number):
    t = frame_number / FPS
    scene_index = min(int(t // 6), 2)
    local_t = t % 6

    image = Image.new("RGB", (WIDTH, HEIGHT), (5, 10, 30))
    draw = ImageDraw.Draw(image)

    # Moving stars.
    for x, y, radius, speed in stars:
        yy = int((y + t * speed * 22) % HEIGHT)
        draw.ellipse(
            (x, yy, x + radius, yy + radius),
            fill=(150, 185, 235)
        )

    # Slowly moving glowing planet.
    pulse = math.sin(t * 1.5) * 12
    cx = WIDTH // 2 + int(math.sin(t * 0.6) * 24)
    cy = 430 + int(math.cos(t * 0.7) * 18)
    r = int(155 + pulse)

    draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(22, 83, 155))
    draw.arc((cx-r, cy-r, cx+r, cy+r), 190, 350,
             fill=(85, 190, 255), width=8)
    draw.arc((cx-r+25, cy-r+25, cx+r-25, cy+r-25),
             15, 170, fill=(50, 135, 205), width=5)

    # Animated text entrance.
    heading, subheading, caption = scenes[scene_index]
    slide = int((1 - min(local_t / 0.8, 1)) * 90)

    centered_text(draw, heading, 720 + slide, title_font,
                  (120, 210, 255))
    centered_text(draw, subheading, 805 + slide, main_font,
                  (255, 255, 255))
    centered_text(draw, caption, 1000, small_font,
                  (210, 220, 240), max_width=610)

    # Progress bar.
    progress = frame_number / TOTAL_FRAMES
    draw.rectangle((40, 1210, 680, 1218), fill=(45, 55, 85))
    draw.rectangle((40, 1210, 40 + int(640 * progress), 1218),
                   fill=(80, 190, 255))

    return image

command = [
    "ffmpeg", "-y",
    "-f", "rawvideo",
    "-vcodec", "rawvideo",
    "-pix_fmt", "rgb24",
    "-s", f"{WIDTH}x{HEIGHT}",
    "-r", str(FPS),
    "-i", "-",
    "-an",
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    OUTPUT
]

process = subprocess.Popen(command, stdin=subprocess.PIPE)

try:
    for frame_number in range(TOTAL_FRAMES):
        frame = make_frame(frame_number)
        process.stdin.write(frame.tobytes())
finally:
    process.stdin.close()

if process.wait() != 0:
    raise RuntimeError("FFmpeg could not create the video.")

print(f"Video created successfully: {OUTPUT}")
