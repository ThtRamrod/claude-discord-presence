"""Renders assets/icon.png: a close-up of the hero bot from bot-fight.gif, for Discord Rich Presence.
Drawn on a 32x32 grid, scaled up 32x to 1024x1024 (Discord's recommended art asset size).
Run:  python assets/make_icon.py
"""
import os

from PIL import Image, ImageDraw

GRID = 32
SCALE = 32

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")

# Same palette as make_gif.py, plus a highlight tone for the larger body.
BG = (20, 20, 43)
STAR = (90, 90, 140)
BODY = (232, 131, 79)
LIGHT = (246, 168, 118)
SHADE = (160, 80, 50)
EYE = (127, 245, 255)
GOLD = (255, 220, 90)
STEEL = (120, 120, 140)
WHITE = (255, 255, 255)

STARS = [(3, 3), (28, 2), (2, 9), (29, 8), (24, 4), (7, 2), (1, 24), (30, 22)]
BOLT = [(16, 25), (17, 25), (15, 26), (16, 26), (14, 27), (15, 27), (16, 27), (17, 27), (15, 28), (16, 28), (14, 29), (15, 29)]


def main():
    img = Image.new("RGB", (GRID, GRID), BG)
    d = ImageDraw.Draw(img)
    box = lambda x0, y0, x1, y1, color: d.rectangle((x0, y0, x1, y1), fill=color)

    for star in STARS:
        d.point(star, fill=STAR)

    # Antenna
    box(15, 1, 16, 2, GOLD)
    box(15, 3, 16, 5, STEEL)

    # Ears
    box(3, 11, 5, 16, STEEL)
    box(26, 11, 28, 16, STEEL)

    # Head, with cut corners and shading
    box(6, 6, 25, 21, BODY)
    for x, y in [(6, 6), (25, 6), (6, 21), (25, 21)]:
        d.point((x, y), fill=BG)
    box(7, 6, 24, 7, LIGHT)
    box(7, 20, 24, 21, SHADE)
    box(24, 8, 25, 20, SHADE)

    # Visor and eyes
    box(8, 10, 23, 16, BG)
    box(10, 11, 13, 15, EYE)
    box(18, 11, 21, 15, EYE)
    box(10, 11, 11, 12, WHITE)
    box(18, 11, 19, 12, WHITE)

    # Neck and shoulders, cropped by the bottom edge
    box(11, 22, 20, 23, SHADE)
    box(6, 24, 25, 31, BODY)
    box(6, 24, 25, 24, LIGHT)
    box(24, 25, 25, 31, SHADE)
    d.point((6, 24), fill=BG)
    d.point((25, 24), fill=BG)

    # Charge bolt on the chest
    for point in BOLT:
        d.point(point, fill=GOLD)

    img.resize((GRID * SCALE, GRID * SCALE), Image.NEAREST).save(OUT, optimize=True)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
