#!/usr/bin/env python3
"""Generate the Deep Value ASX app icons (full-bleed square; iOS masks corners)."""
from PIL import Image, ImageDraw, ImageFont

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
TEAL, CREAM, GOLD = (13, 92, 104), (242, 239, 230), (232, 184, 75)
S = 1024

img = Image.new("RGB", (S, S), TEAL)
d = ImageDraw.Draw(img)

# soft radial lift so the flat ground isn't dead
for i in range(28):
    a = int(6 - i * 0.2)
    if a <= 0:
        break
    d.ellipse([-S * 0.3 + i * 12, -S * 0.45 + i * 12, S * 1.3 - i * 12, S * 0.9 - i * 12],
              fill=(TEAL[0] + a, TEAL[1] + a + 2, TEAL[2] + a + 2))

def centred(text, font, cy, fill):
    f = ImageFont.truetype(FONT, font)
    x0, y0, x1, y1 = d.textbbox((0, 0), text, font=f)
    d.text((S / 2 - (x1 + x0) / 2, cy - (y1 + y0) / 2), text, font=f, fill=fill)

centred("P/E", 300, S * 0.37, CREAM)
centred("<10", 340, S * 0.68, GOLD)

for size, name in [(180, "apple-touch-icon.png"), (192, "icon-192.png"),
                   (512, "icon-512.png"), (1024, "icon-1024.png")]:
    img.resize((size, size), Image.LANCZOS).save(name, optimize=True)
    print("wrote", name)
