"""Renders assets/claude-spark.gif: a glowing, rotating Claude-orange starburst.
Run:  python assets/make_gif.py
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter

SIZE = 256
SS = 3  # supersampling for smooth edges
FRAMES = 36
FRAME_MS = 50
RAYS = 12
ORANGE = (217, 119, 87)
HOT = (255, 196, 150)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "claude-spark.gif")


def background(size):
    """Dark warm radial gradient."""
    bg = Image.new("RGB", (size, size))
    px = bg.load()
    c = size / 2
    for y in range(size):
        for x in range(size):
            d = min(1.0, math.hypot(x - c, y - c) / (size * 0.72))
            px[x, y] = (int(46 - 32 * d), int(26 - 18 * d), int(20 - 14 * d))
    return bg


def starburst(size, angle, scale):
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    c = size / 2
    for i in range(RAYS):
        a = angle + i * (2 * math.pi / RAYS)
        length = size * (0.36 if i % 2 == 0 else 0.26) * scale
        width = size * 0.045 * scale
        tip = (c + math.cos(a) * length, c + math.sin(a) * length)
        perp = a + math.pi / 2
        base_r = size * 0.04 * scale
        bx, by = c + math.cos(a) * base_r, c + math.sin(a) * base_r
        left = (bx + math.cos(perp) * width, by + math.sin(perp) * width)
        right = (bx - math.cos(perp) * width, by - math.sin(perp) * width)
        draw.polygon([left, tip, right, (c, c)], fill=ORANGE + (255,))
    r = size * 0.075 * scale
    draw.ellipse([c - r, c - r, c + r, c + r], fill=ORANGE + (255,))
    return layer


def sparkle(draw, x, y, r, alpha):
    """Four-point twinkle."""
    col = HOT + (int(255 * alpha),)
    w = r * 0.28
    draw.polygon([(x, y - r), (x + w, y), (x, y + r), (x - w, y)], fill=col)
    draw.polygon([(x - r, y), (x, y - w), (x + r, y), (x, y + w)], fill=col)


def main():
    S = SIZE * SS
    bg = background(SIZE).resize((S, S)).convert("RGBA")
    rng = random.Random(7)
    twinkles = [
        (rng.uniform(0.12, 0.88), rng.uniform(0.12, 0.88), rng.uniform(0.025, 0.05), rng.random())
        for _ in range(7)
    ]
    frames = []
    for f in range(FRAMES):
        t = f / FRAMES
        angle = t * 2 * (2 * math.pi / RAYS)  # long/short rays alternate, so the pattern repeats every 2 rays
        pulse = 1 + 0.07 * math.sin(t * 2 * math.pi)

        star = starburst(S, angle, pulse)
        glow = star.filter(ImageFilter.GaussianBlur(S * 0.07))
        glow_strength = 0.75 + 0.25 * math.sin(t * 2 * math.pi)
        glow.putalpha(glow.getchannel("A").point(lambda v: int(v * glow_strength)))

        frame = Image.alpha_composite(bg, glow)
        frame = Image.alpha_composite(frame, glow)
        frame = Image.alpha_composite(frame, star)

        # Orbiting embers
        fx = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        d = ImageDraw.Draw(fx)
        c = S / 2
        for k in range(3):
            a = t * 2 * math.pi + k * (2 * math.pi / 3)
            orbit = S * 0.42
            x, y = c + math.cos(a) * orbit, c + math.sin(a) * orbit
            rr = S * 0.018
            d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=HOT + (230,))
        # Twinkling stars, each on its own phase
        for (tx, ty, tr, phase) in twinkles:
            alpha = max(0.0, math.sin((t + phase) * 2 * math.pi))
            sparkle(d, tx * S, ty * S, tr * S * (0.6 + 0.4 * alpha), alpha)
        fx_glow = fx.filter(ImageFilter.GaussianBlur(S * 0.012))
        frame = Image.alpha_composite(frame, fx_glow)
        frame = Image.alpha_composite(frame, fx)

        frames.append(frame.resize((SIZE, SIZE), Image.LANCZOS).convert("RGB"))

    palette_src = frames[0].quantize(colors=255, method=Image.Quantize.MEDIANCUT)
    paletted = [fr.quantize(palette=palette_src, dither=Image.Dither.NONE) for fr in frames]
    paletted[0].save(
        OUT, save_all=True, append_images=paletted[1:], duration=FRAME_MS, loop=0, optimize=True, disposal=1
    )
    print(f"wrote {OUT} ({os.path.getsize(OUT) // 1024} KB, {FRAMES} frames)")


if __name__ == "__main__":
    main()
