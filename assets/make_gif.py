"""Renders assets/bot-fight.gif: a little pixel bot that stomps one enemy bot,
then turns around and zaps another. Drawn on a 32x32 grid, scaled up 8x so the bots stay readable at Discord's small size.
Run:  python assets/make_gif.py
"""
import math
import os
import random

from PIL import Image

GRID = 32
SCALE = 8
FRAMES = 48
FRAME_MS = 80
GROUND_Y = 27  # first row of ground
E1_STOP = 21
HOME_X = 10    # hero's resting x (left edge of sprite)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bot-fight.gif")

COLORS = {
    "bg": (20, 20, 43),
    "star": (90, 90, 140),
    "ground": (58, 58, 92),
    "ground_top": (110, 110, 160),
    "O": (232, 131, 79),    # hero body
    "D": (160, 80, 50),     # hero shading
    "C": (127, 245, 255),   # hero eyes
    "Y": (255, 220, 90),    # antenna tip / laser
    "G": (120, 120, 140),   # antenna stem
    "S": (138, 143, 163),   # enemy body
    "K": (80, 84, 100),     # enemy shading
    "R": (255, 77, 77),     # enemy eyes
    "W": (255, 255, 255),
}

# Sprites face right; '.' is transparent.
HERO = [
    "...Y....",
    "...G....",
    ".OOOOOO.",
    ".OOOCOC.",
    ".OOOOOO.",
    "..DDDD..",
    ".OOOOOO.",
    ".OOOOOO.",
]
HERO_LEGS = ["..O..O..", "..O..O.."]
HERO_LEGS_JUMP = [".O....O.", "........"]

ENEMY = [
    ".K....K.",
    ".SSSSSS.",
    ".SRSRSS.",
    ".SSSSSS.",
    "..KKKK..",
    ".SSSSSS.",
    ".SSSSSS.",
]
ENEMY_LEGS = [[".S....S.", ".S....S."], ["..S..S..", "..S..S.."]]
ENEMY_SQUASHED = [
    "SRSRSSSS",
    "SSSSSSSS",
]


def flip(rows):
    return [r[::-1] for r in rows]


def blit(px, rows, x, y, facing_right=True):
    if not facing_right:
        rows = flip(rows)
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch == ".":
                continue
            X, Y = int(x) + dx, int(y) + dy
            if 0 <= X < GRID and 0 <= Y < GRID:
                px[X, Y] = COLORS[ch]


def sprite_height(rows):
    return len(rows)


def draw_hero(px, x, y_offset, facing_right, airborne):
    body = HERO + (HERO_LEGS_JUMP if airborne else HERO_LEGS)
    top = GROUND_Y - sprite_height(body) - y_offset
    blit(px, body, x, top, facing_right)


def draw_enemy(px, x, step, facing_right):
    body = ENEMY + ENEMY_LEGS[step % 2]
    blit(px, body, x, GROUND_Y - sprite_height(body), facing_right)


class Burst:
    """Pixels flying out from a destroyed bot, with gravity."""

    def __init__(self, cx, cy, seed):
        rng = random.Random(seed)
        self.parts = []
        for _ in range(12):
            a = rng.uniform(math.pi, 2 * math.pi)  # upward half
            v = rng.uniform(0.4, 1.1)
            col = rng.choice(["S", "K", "R", "Y", "W"])
            self.parts.append((cx, cy, math.cos(a) * v, math.sin(a) * v, col))

    def draw(self, px, t):
        for (x, y, vx, vy, col) in self.parts:
            X = int(x + vx * t)
            Y = int(y + vy * t + 0.09 * t * t)
            if 0 <= X < GRID and 0 <= Y < GROUND_Y:
                px[X, Y] = COLORS[col]


def flash(px, cx, cy, r):
    for k in range(8):
        a = k * math.pi / 4
        X, Y = int(cx + math.cos(a) * r), int(cy + math.sin(a) * r)
        if 0 <= X < GRID and 0 <= Y < GROUND_Y:
            px[X, Y] = COLORS["W"]


def scene():
    base = Image.new("RGB", (GRID, GRID), COLORS["bg"])
    px = base.load()
    rng = random.Random(3)
    for _ in range(9):
        px[rng.randrange(GRID), rng.randrange(GROUND_Y - 4)] = COLORS["star"]
    for y in range(GROUND_Y, GRID):
        for x in range(GRID):
            px[x, y] = COLORS["ground_top"] if y == GROUND_Y else COLORS["ground"]
    for x in range(1, GRID, 5):
        px[x, GROUND_Y + 2] = COLORS["ground_top"]
    return base


def render(f, base, burst1, burst2):
    img = base.copy()
    px = img.load()

    # --- Enemy 1 walks in from the right, gets stomped (frames 0-31) ---
    e1_x = None
    if f < 18:
        e1_x = GRID - f * (GRID - E1_STOP) / 18           # walks left toward the hero
        draw_enemy(px, e1_x, f // 3, facing_right=False)
    elif f < 22:
        blit(px, ENEMY_SQUASHED, E1_STOP, GROUND_Y - 2)
    elif f < 32:
        burst1.draw(px, f - 22)
        if f < 24:
            flash(px, E1_STOP + 4, GROUND_Y - 4, 2 + (f - 22) * 2)

    # --- Enemy 2 walks in from the left, gets zapped (frames 30-47) ---
    if 30 <= f < 40:
        draw_enemy(px, -8 + (f - 30) * 0.9, f // 3, facing_right=True)
    elif 40 <= f < 48:
        burst2.draw(px, f - 40)
        if f < 42:
            flash(px, 4, GROUND_Y - 4, 2 + (f - 40) * 2)

    # --- Hero ---
    landing_x = E1_STOP - 1
    if 12 <= f < 18:
        # hop up and over onto the enemy
        t = (f - 12) / 6
        x = HOME_X + (landing_x - HOME_X) * t
        y = int(8 * math.sin(math.pi * t * 0.92) + 2 * t)
        draw_hero(px, x, y, True, True)
    elif 18 <= f < 22:
        draw_hero(px, landing_x, 2, True, False)  # standing on the squashed bot
    elif 22 <= f < 30:
        # bounce back home
        t = (f - 22) / 8
        x = landing_x + (HOME_X - landing_x) * t
        y = int(6 * math.sin(math.pi * t))
        draw_hero(px, x, y, t < 0.5, y > 0)
    elif 30 <= f < 48:
        facing = False  # faces the second enemy
        recoil = 1 if 37 <= f < 40 else 0
        draw_hero(px, HOME_X + recoil, 0, facing, False)
        if 37 <= f < 40:
            # laser from the hero's eye to the enemy
            eye_y = GROUND_Y - 10 + 3
            enemy_x = -8 + (f - 30) * 0.9 + 6
            col = COLORS["Y"] if f % 2 else COLORS["W"]
            for X in range(int(enemy_x), HOME_X + 2):
                if 0 <= X < GRID:
                    px[X, eye_y] = col
    else:
        bob = 1 if (f // 3) % 2 else 0  # idle bob
        draw_hero(px, HOME_X, bob, True, False)

    return img.resize((GRID * SCALE, GRID * SCALE), Image.NEAREST)


def main():
    base = scene()
    burst1 = Burst(E1_STOP + 4, GROUND_Y - 3, seed=1)
    burst2 = Burst(4, GROUND_Y - 4, seed=2)
    frames = [render(f, base, burst1, burst2) for f in range(FRAMES)]
    pal = [fr.quantize(colors=32, method=Image.Quantize.MEDIANCUT) for fr in frames]
    pal[0].save(OUT, save_all=True, append_images=pal[1:], duration=FRAME_MS, loop=0, optimize=False, disposal=1)
    print(f"wrote {OUT} ({os.path.getsize(OUT) // 1024} KB, {FRAMES} frames)")


if __name__ == "__main__":
    main()
