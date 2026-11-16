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

FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REGULAR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

scenes = [
    ("WHAT IF EARTH", "STOPPED SPINNING?", "Imagine the entire planet suddenly stopped..."),
    ("THE CONSEQUENCES", "WOULD BE EXTREME", "Everything not attached to the ground would keep moving."),
    ("WOULD WE SURVIVE?", "NOT EASILY.", "A sudden stop could change life on Earth forever."),
]

random.seed(12)
stars = [
    (random.randint(0, WIDTH), random.randint(0, HEIGHT),
     random.randint(1, 3), random.uniform(0.5, 2.0))
    for _ in range(90)
]

def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=font)[2] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

def draw_text_box(draw, text, box, font_path, start_size, min_size,
                  fill, max_lines, spacing=12, stroke_width=0):
    """Fit wrapped text inside a fixed box; never draw outside its bounds."""
    left, top, right, bottom = box
    max_width = right - left
    max_height = bottom - top
    chosen_font = None
    chosen_lines = None

    for size in range(start_size, min_size - 1, -2):
        font = ImageFont.truetype(font_path, size)
        lines = wrap_text(draw, text, font, max_width)
        line_height = size + spacing
        total_height = len(lines) * line_height - spacing
        if len(lines) <= max_lines and total_height <= max_height:
            chosen_font, chosen_lines = font, lines
            break

    if chosen_font is None:
        chosen_font = ImageFont.truetype(font_path, min_size)
        chosen_lines = wrap_text(draw, text, chosen_font, max_width)

    line_height = chosen_font.size + spacing
    total_height = len(chosen_lines) * line_height - spacing
    y = top + max(0, (max_height - total_height) // 2)

    for line in chosen_lines:
        bounds = draw.textbbox((0, 0), line, font=chosen_font,
                               stroke_width=stroke_width)
        text_width = bounds[2] - bounds[0]
        x = left + (max_width - text_width) // 2
        draw.text((x, y), line, font=chosen_font, fill=fill,
                  stroke_width=stroke_width, stroke_fill=(0, 0, 0))
        y += line_height

def make_frame(frame_number):
    t = frame_number / FPS
    scene_index = min(int(t // 6), 2)
    local_t = t % 6

    image = Image.new("RGB", (WIDTH, HEIGHT), (5, 10, 30))
    draw = ImageDraw.Draw(image)

    # Moving stars in the background.
    for x, y, radius, speed in stars:
        yy = int((y + t * speed * 22) % HEIGHT)
        draw.ellipse((x, yy, x + radius, yy + radius),
                     fill=(150, 185, 235))

    # Planet stays clear of the text area.
    pulse = math.sin(t * 1.5) * 8
    cx = WIDTH // 2 + int(math.sin(t * 0.6) * 18)
    cy = 365 + int(math.cos(t * 0.7) * 12)
    r = int(132 + pulse)
    draw.ellipse((cx-r, cy-r, cx+r, cy+r), fill=(22, 83, 155))
    draw.arc((cx-r, cy-r, cx+r, cy+r), 190, 350,
             fill=(85, 190, 255), width=8)
    draw.arc((cx-r+22, cy-r+22, cx+r-22, cy+r-22),
             15, 170, fill=(50, 135, 205), width=5)

    heading, subheading, caption = scenes[scene_index]

    # A subtle panel separates typography from the animated planet.
    draw.rounded_rectangle((34, 555, 686, 1125), radius=28,
                           fill=(8, 18, 43), outline=(35, 85, 135), width=2)

    # Short entrance animation moves the complete text group, not individual
    # lines, so wrapping can never cause the text blocks to collide.
    entrance = int((1 - min(local_t / 0.65, 1)) * 28)

    draw_text_box(
        draw, heading, (65, 590 + entrance, 655, 735 + entrance),
        FONT_BOLD, 48, 36, (120, 210, 255), max_lines=2, spacing=12
    )
    draw_text_box(
        draw, subheading, (65, 755 + entrance, 655, 890 + entrance),
        FONT_BOLD, 43, 32, (255, 255, 255), max_lines=2, spacing=12
    )
    draw_text_box(
        draw, caption, (75, 930, 645, 1080),
        FONT_REGULAR, 29, 23, (215, 225, 242), max_lines=3, spacing=13
    )

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
        process.stdin.write(make_frame(frame_number).tobytes())
finally:
    process.stdin.close()

if process.wait() != 0:
    raise RuntimeError("FFmpeg could not create the video.")

print(f"Video created successfully: {OUTPUT}")
