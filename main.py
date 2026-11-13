#!/usr/bin/env python3
"""Procedural 1024x1024 PNG for make.fun ai-happy-01.

Draws a warm golden-sunrise park scene: a small friendly robot in a
tiny judge's wig handing a big sunflower to a laughing grandmother on
a park bench, a cheering child, a wagging dog, balloons, confetti and
a red banner reading "THANK YOU, JUDGE!".

Pure standard library (os, math, struct, zlib, pathlib). Deterministic:
the same bytes on every run. Renders at 2x supersampling into a
2048x2048 RGB buffer, box-downsamples to 1024x1024, and writes the PNG
with a hand-rolled encoder (filter byte 0 per row, 8-bit colour type 2).
"""

import math
import os
import struct
import zlib
from pathlib import Path

# ---------------------------------------------------------------------------
# Canvas: design space is 1024x1024; the buffer is 2x supersampled.
# ---------------------------------------------------------------------------
W = 1024
S = 2
IW = W * S  # 2048

buf = bytearray(IW * IW * 3)

# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------
SKY_TOP = (255, 217, 168)
SKY_MID = (255, 192, 106)
SKY_LOW = (255, 233, 166)
SUN = (255, 217, 77)
SUN_RAY = (255, 201, 60)
SUN_INNER = (255, 226, 110)
SUN_HALO = (255, 233, 160)
CLOUD = (255, 248, 236)
HILL_BACK = (111, 168, 92)
HILL_FRONT = (143, 190, 106)
WOOD = (169, 113, 63)
WOOD_DARK = (138, 90, 46)
SKIN = (242, 196, 155)
HAIR_GREY = (207, 207, 207)
SHAWL = (179, 136, 235)
DRESS = (126, 87, 194)
ROBOT_CREAM = (255, 243, 220)
ROBOT_TEAL = (43, 179, 163)
WIG = (245, 242, 234)
INK = (51, 48, 46)
CHEEK = (255, 158, 158)
PETAL = (255, 201, 60)
FLOWER_CENTRE = (122, 74, 33)
FLOWER_DOT = (90, 52, 19)
LEAF = (96, 160, 74)
DOG_GOLD = (232, 169, 79)
DOG_DARK = (201, 138, 58)
DOG_LIGHT = (245, 217, 168)
SHIRT_RED = (231, 76, 60)
CHILD_HAIR = (109, 76, 65)
SHORTS_BLUE = (63, 105, 178)
BANNER_RED = (214, 69, 65)
BANNER_DARK = (169, 50, 38)
BANNER_GOLD = (255, 201, 60)
BANNER_TEXT = (255, 246, 224)
HEART_PINK = (255, 107, 129)
STRING_BROWN = (138, 90, 46)
BIRD_GREY = (107, 91, 74)
BALLOON_RED = (231, 76, 60)
BALLOON_TEAL = (43, 179, 163)
BALLOON_YELLOW = (255, 201, 60)
CONFETTI_BLUE = (63, 105, 178)
CONFETTI_LAV = (179, 136, 235)
WHITE = (255, 255, 255)


# ---------------------------------------------------------------------------
# Low-level drawing on the internal (2048x2048) buffer.
# span() takes internal coordinates; every other helper takes design
# coordinates (1024 space) and scales by S.
# ---------------------------------------------------------------------------
def span(y, x0, x1, color):
    """Fill one horizontal run of the internal buffer, clipped."""
    if y < 0 or y >= IW or x1 < x0:
        return
    if x0 < 0:
        x0 = 0
    if x1 >= IW:
        x1 = IW - 1
    if x1 < x0:
        return
    n = x1 - x0 + 1
    base = (y * IW + x0) * 3
    buf[base:base + n * 3] = bytes(color) * n


def _ix(v):
    return int(round(v * S))


def fill_rect(x, y, w, h, color):
    X = _ix(x)
    Y = _ix(y)
    Wd = _ix(w)
    Ht = _ix(h)
    for yy in range(Y, Y + Ht):
        span(yy, X, X + Wd - 1, color)


def disc(cx, cy, r, color):
    """Filled circle, integer radius, per-row sqrt via math.isqrt."""
    R = _ix(r)
    if R <= 0:
        return
    Cx = _ix(cx)
    Cy = _ix(cy)
    R2 = R * R
    for dy in range(-R, R + 1):
        dx = math.isqrt(R2 - dy * dy)
        span(Cy + dy, Cx - dx, Cx + dx, color)


def ellipse(cx, cy, rx, ry, color):
    RX = _ix(rx)
    RY = _ix(ry)
    if RX <= 0 or RY <= 0:
        return
    Cx = _ix(cx)
    Cy = _ix(cy)
    for dy in range(-RY, RY + 1):
        t = 1.0 - (dy * dy) / (RY * RY)
        dx = int(RX * math.sqrt(t)) if t > 0.0 else 0
        span(Cy + dy, Cx - dx, Cx + dx, color)


def rrect(x, y, w, h, r, color):
    """Rounded rect: rect + 4 corner discs."""
    r = min(float(r), w / 2.0, h / 2.0)
    fill_rect(x + r, y, w - 2 * r, h, color)
    fill_rect(x, y + r, w, h - 2 * r, color)
    disc(x + r, y + r, r, color)
    disc(x + w - r, y + r, r, color)
    disc(x + r, y + h - r, r, color)
    disc(x + w - r, y + h - r, r, color)


def polygon(points, color):
    """Scanline-filled polygon, design coordinates (floats allowed)."""
    pts = [(_ix(x), _ix(y)) for x, y in points]
    ys = [p[1] for p in pts]
    ymin, ymax = min(ys), max(ys)
    n = len(pts)
    for y in range(ymin, ymax + 1):
        xs = []
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            span(y, int(math.ceil(xs[i])), int(math.floor(xs[i + 1])), color)


def thick_line(x0, y0, x1, y1, width, color):
    """Thick segment drawn as discs along its length."""
    dx = x1 - x0
    dy = y1 - y0
    length = math.hypot(dx, dy)
    steps = max(1, int(length / max(1.0, width / 4.0)) + 1)
    for i in range(steps + 1):
        t = i / steps
        disc(x0 + dx * t, y0 + dy * t, width / 2.0, color)


def arc(cx, cy, r, a0, a1, width, color):
    """Arc of discs. Angles in degrees, 0 = east, positive clockwise
    (y grows down): 180..360 traces the upper half, 0..180 the lower."""
    if a1 < a0:
        a0, a1 = a1, a0
    span_deg = a1 - a0
    steps = max(2, int(span_deg * max(r, 1) / 8) + 1)
    for i in range(steps + 1):
        a = math.radians(a0 + span_deg * i / steps)
        disc(cx + r * math.cos(a), cy + r * math.sin(a), width / 2.0, color)


def star(cx, cy, r, color):
    """5-point star polygon (outer r, inner r * 0.45)."""
    pts = []
    for i in range(10):
        ang = math.radians(-90 + i * 36)
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(ang), cy + rr * math.sin(ang)))
    polygon(pts, color)


def heart(cx, cy, size, color):
    """Heart: two discs plus a triangle."""
    s = float(size)
    disc(cx - 0.28 * s, cy - 0.16 * s, 0.32 * s, color)
    disc(cx + 0.28 * s, cy - 0.16 * s, 0.32 * s, color)
    polygon(
        [
            (cx - 0.60 * s, cy - 0.02 * s),
            (cx + 0.60 * s, cy - 0.02 * s),
            (cx, cy + 0.62 * s),
        ],
        color,
    )


# ---------------------------------------------------------------------------
# 5x7 bitmap font. 7 rows of 5 bits, '1' = filled.
# ---------------------------------------------------------------------------
FONT = {
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10011", "10001", "10001", "10001"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    ",": ["00000", "00000", "00000", "00000", "00100", "00100", "01000"],
    "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "!": ["00100", "00100", "00100", "00100", "00100", "00000", "00100"],
    " ": ["00000", "00000", "00000", "00000", "00000", "00000", "00000"],
}


def draw_text(text, x, y, scale, color):
    """Draw text; one font pixel is a scale x scale design-px block."""
    cx = x
    for ch in text:
        glyph = FONT.get(ch)
        if glyph:
            for r, row in enumerate(glyph):
                for c, bit in enumerate(row):
                    if bit == "1":
                        fill_rect(cx + c * scale, y + r * scale, scale, scale, color)
        cx += 6 * scale


def text_width(text, scale):
    return len(text) * 6 * scale - scale


def draw_text_centered(text, y, scale, color):
    draw_text(text, (W - text_width(text, scale)) // 2, y, scale, color)


# ---------------------------------------------------------------------------
# Scene, back to front.
# ---------------------------------------------------------------------------
def _lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def sky():
    for iy in range(IW):
        yd = iy / S
        if yd <= 520:
            c = _lerp(SKY_TOP, SKY_MID, yd / 520.0)
        elif yd <= 720:
            c = _lerp(SKY_MID, SKY_LOW, (yd - 520.0) / 200.0)
        else:
            c = SKY_LOW
        base = iy * IW * 3
        buf[base:base + IW * 3] = bytes(c) * IW


def sun():
    cx, cy = 898, 112
    # Soft halo so the sunrise glows, and the whole disc sits inside the
    # canvas (it used to be clipped by the top-right corner).
    disc(cx, cy, 110, SUN_HALO)
    for k in range(8):
        a = math.radians(k * 45)
        tip = (cx + 108 * math.cos(a), cy + 108 * math.sin(a))
        b1a = a - math.radians(9)
        b2a = a + math.radians(9)
        b1 = (cx + 66 * math.cos(b1a), cy + 66 * math.sin(b1a))
        b2 = (cx + 66 * math.cos(b2a), cy + 66 * math.sin(b2a))
        polygon([tip, b1, b2], SUN_RAY)
    disc(cx, cy, 68, SUN)
    disc(cx, cy, 52, SUN_INNER)


def cloud(cx, cy, rx, ry):
    ellipse(cx, cy, rx, ry, CLOUD)
    ellipse(cx - rx * 0.5, cy + ry * 0.35, rx * 0.55, ry * 0.6, CLOUD)
    ellipse(cx + rx * 0.5, cy + ry * 0.35, rx * 0.6, ry * 0.6, CLOUD)


def clouds():
    cloud(210, 300, 72, 26)
    cloud(330, 338, 56, 20)
    cloud(770, 330, 62, 22)
    cloud(880, 292, 44, 16)


def balloon(cx, cy, r, color):
    disc(cx, cy, r, color)
    disc(cx - r * 0.35, cy - r * 0.35, r * 0.28, WHITE)
    polygon(
        [(cx - 8, cy + r - 2), (cx + 8, cy + r - 2), (cx, cy + r + 12)], color
    )
    thick_line(cx, cy + r + 10, 128, 500, 3, STRING_BROWN)


def balloons():
    balloon(85, 330, 32, BALLOON_RED)
    balloon(148, 292, 28, BALLOON_TEAL)
    balloon(122, 392, 26, BALLOON_YELLOW)


def bird(cx, cy):
    arc(cx - 9, cy, 9, 180, 360, 3, BIRD_GREY)
    arc(cx + 9, cy, 9, 180, 360, 3, BIRD_GREY)


def birds():
    bird(700, 190)
    bird(786, 228)
    bird(636, 248)


CONFETTI = [
    (60, 420, BALLOON_RED, 0),
    (180, 300, BALLOON_TEAL, 1),
    (260, 380, BALLOON_YELLOW, 0),
    (420, 330, HEART_PINK, 1),
    (520, 420, CONFETTI_BLUE, 0),
    (600, 300, CONFETTI_LAV, 1),
    (700, 380, BALLOON_RED, 0),
    (820, 420, BALLOON_TEAL, 1),
    (940, 360, BALLOON_YELLOW, 0),
    (980, 520, HEART_PINK, 1),
    (340, 520, CONFETTI_BLUE, 0),
    (480, 560, CONFETTI_LAV, 1),
    (660, 540, BALLOON_RED, 0),
    (760, 480, BALLOON_YELLOW, 1),
    (880, 560, BALLOON_TEAL, 0),
    (120, 560, HEART_PINK, 1),
]


def confetti():
    for x, y, color, shape in CONFETTI:
        if shape == 0:
            fill_rect(x - 6, y - 3, 12, 6, color)
        else:
            disc(x, y, 5, color)


def hills():
    ellipse(280, 1120, 720, 400, HILL_BACK)
    ellipse(820, 1180, 680, 380, HILL_FRONT)


def bench():
    fill_rect(300, 640, 420, 16, WOOD)
    fill_rect(300, 668, 420, 16, WOOD)
    fill_rect(300, 700, 420, 22, WOOD_DARK)
    fill_rect(330, 722, 18, 78, WOOD_DARK)
    fill_rect(672, 722, 18, 78, WOOD_DARK)
    fill_rect(316, 612, 14, 110, WOOD)
    fill_rect(690, 612, 14, 110, WOOD)


def grandmother():
    # Hair behind the head, plus a bun.
    disc(630, 545, 54, HAIR_GREY)
    disc(630, 498, 22, HAIR_GREY)
    # Head and laughing face.
    disc(630, 566, 50, SKIN)
    arc(608, 560, 11, 180, 360, 6, INK)  # closed laughing eyes
    arc(652, 560, 11, 180, 360, 6, INK)
    disc(590, 586, 11, CHEEK)
    disc(670, 586, 11, CHEEK)
    disc(630, 592, 17, INK)  # open laughing mouth
    ellipse(630, 600, 10, 6, CHEEK)  # tongue
    # Shawl and dress.
    polygon([(576, 618), (684, 618), (708, 742), (552, 742)], SHAWL)
    polygon([(568, 720), (692, 720), (702, 832), (558, 832)], DRESS)
    # Arms: left resting in her lap, right reaching for the flower.
    thick_line(588, 646, 606, 716, 18, SHAWL)
    disc(607, 718, 11, SKIN)
    thick_line(676, 646, 618, 626, 18, SHAWL)
    disc(616, 628, 11, SKIN)
    # Shoes.
    ellipse(598, 846, 18, 10, WOOD_DARK)
    ellipse(662, 846, 18, 10, WOOD_DARK)


def robot():
    # Antenna with a gold star.
    thick_line(360, 462, 360, 424, 6, BIRD_GREY)
    star(360, 410, 18, BANNER_GOLD)
    # Judge's wig: white puffs around the head.
    for cx, cy, r in [
        (306, 482, 18),
        (330, 464, 20),
        (360, 458, 20),
        (390, 464, 20),
        (414, 482, 18),
        (300, 506, 14),
        (420, 506, 14),
    ]:
        disc(cx, cy, r, WIG)
    # Head and happy face.
    disc(360, 524, 62, ROBOT_CREAM)
    arc(336, 524, 12, 180, 360, 7, INK)  # crescent eyes
    arc(384, 524, 12, 180, 360, 7, INK)
    arc(360, 550, 16, 0, 180, 6, INK)  # smile, lower half
    disc(318, 548, 9, CHEEK)
    disc(402, 548, 9, CHEEK)
    # Neck, body, belly panel with a cream heart.
    fill_rect(344, 576, 32, 28, ROBOT_TEAL)
    rrect(300, 600, 120, 160, 40, ROBOT_CREAM)
    rrect(322, 640, 76, 80, 20, ROBOT_TEAL)
    heart(360, 682, 16, ROBOT_CREAM)
    # Arms: left down, right up holding the sunflower.
    thick_line(306, 646, 250, 700, 18, ROBOT_CREAM)
    disc(248, 702, 12, ROBOT_CREAM)
    thick_line(414, 646, 490, 582, 18, ROBOT_CREAM)
    disc(492, 580, 12, ROBOT_CREAM)
    # Feet.
    rrect(320, 756, 34, 26, 8, INK)
    rrect(366, 756, 34, 26, 8, INK)


def sunflower():
    # Stem and leaves from the robot's hand.
    thick_line(505, 562, 494, 584, 10, LEAF)
    ellipse(492, 590, 14, 7, LEAF)
    ellipse(518, 592, 14, 7, LEAF)
    # 12 petals on a ring around the centre.
    for k in range(12):
        a = math.radians(k * 30)
        disc(505 + 42 * math.cos(a), 535 + 42 * math.sin(a), 21, PETAL)
    disc(505, 535, 29, FLOWER_CENTRE)
    # 9 small dark dots in the centre.
    disc(505, 535, 3, FLOWER_DOT)
    for k in range(8):
        a = math.radians(k * 45)
        disc(505 + 15 * math.cos(a), 535 + 15 * math.sin(a), 3, FLOWER_DOT)
    # A little pink heart floating beside the flower.
    heart(560, 452, 15, HEART_PINK)


def child():
    # Hair behind, head, hair cap, face.
    disc(790, 628, 36, CHILD_HAIR)
    disc(790, 644, 34, SKIN)
    disc(790, 622, 34, CHILD_HAIR)
    disc(790, 634, 30, SKIN)
    # Laughing face.
    arc(778, 642, 8, 180, 360, 5, INK)
    arc(802, 642, 8, 180, 360, 5, INK)
    disc(768, 656, 7, CHEEK)
    disc(812, 656, 7, CHEEK)
    disc(790, 664, 10, INK)
    # Red shirt, blue shorts.
    rrect(758, 682, 64, 82, 18, SHIRT_RED)
    fill_rect(762, 762, 56, 30, SHORTS_BLUE)
    # Arms thrown up in a cheer.
    thick_line(764, 694, 730, 632, 13, SKIN)
    disc(730, 632, 9, SKIN)
    thick_line(816, 694, 850, 632, 13, SKIN)
    disc(850, 632, 9, SKIN)
    # Legs and shoes.
    fill_rect(768, 792, 12, 40, SKIN)
    fill_rect(800, 792, 12, 40, SKIN)
    ellipse(772, 838, 12, 7, SHIRT_RED)
    ellipse(808, 838, 12, 7, SHIRT_RED)


def dog():
    # Wagging tail.
    thick_line(222, 876, 258, 826, 12, DOG_GOLD)
    disc(260, 822, 9, DOG_GOLD)
    # Body, chest, head.
    ellipse(180, 872, 46, 40, DOG_GOLD)
    ellipse(180, 880, 28, 26, DOG_LIGHT)
    disc(180, 802, 34, DOG_GOLD)
    # Floppy ears, snout, nose, tongue, eyes.
    ellipse(150, 788, 12, 22, DOG_DARK)
    ellipse(210, 788, 12, 22, DOG_DARK)
    ellipse(180, 814, 17, 12, DOG_LIGHT)
    disc(180, 806, 7, INK)
    ellipse(180, 828, 8, 12, HEART_PINK)
    disc(168, 794, 4, INK)
    disc(192, 794, 4, INK)
    # Front legs.
    ellipse(164, 912, 10, 14, DOG_GOLD)
    ellipse(196, 912, 10, 14, DOG_GOLD)


FLOWER_SPOTS = [
    (48, 940),
    (120, 900),
    (210, 960),
    (300, 890),
    (392, 950),
    (470, 905),
    (560, 965),
    (650, 895),
    (740, 945),
    (830, 900),
    (905, 955),
    (972, 915),
]
FLOWER_COLORS = [
    BALLOON_RED,
    BALLOON_TEAL,
    BALLOON_YELLOW,
    HEART_PINK,
    CONFETTI_BLUE,
    CONFETTI_LAV,
]


def flowers():
    for i, (x, y) in enumerate(FLOWER_SPOTS):
        col = FLOWER_COLORS[i % len(FLOWER_COLORS)]
        thick_line(x, y, x, y - 34, 4, LEAF)
        bx, by = x, y - 40
        for k in range(5):
            a = math.radians(k * 72 - 90)
            disc(bx + 11 * math.cos(a), by + 11 * math.sin(a), 8, col)
        disc(bx, by, 7, BANNER_GOLD)


def butterfly(cx, cy, color):
    ellipse(cx - 10, cy - 8, 10, 7, color)
    ellipse(cx + 10, cy - 8, 10, 7, color)
    ellipse(cx - 8, cy + 8, 8, 6, color)
    ellipse(cx + 8, cy + 8, 8, 6, color)
    thick_line(cx, cy - 10, cx, cy + 10, 4, INK)


def butterflies():
    butterfly(252, 776, (255, 165, 0))
    butterfly(884, 700, CONFETTI_LAV)


def banner():
    thick_line(196, 0, 196, 62, 4, STRING_BROWN)
    thick_line(828, 0, 828, 62, 4, STRING_BROWN)
    rrect(176, 56, 672, 192, 18, BANNER_GOLD)
    rrect(184, 64, 656, 176, 14, BANNER_RED)
    polygon([(184, 64), (184, 240), (148, 152)], BANNER_DARK)
    polygon([(840, 64), (840, 240), (876, 152)], BANNER_DARK)
    disc(166, 152, 8, BANNER_GOLD)
    disc(858, 152, 8, BANNER_GOLD)
    draw_text_centered("THANK YOU,", 84, 11, BANNER_TEXT)
    draw_text_centered("JUDGE!", 166, 11, BANNER_TEXT)


def draw_scene():
    sky()
    sun()
    clouds()
    balloons()
    birds()
    confetti()
    hills()
    bench()
    grandmother()
    robot()
    sunflower()
    child()
    dog()
    flowers()
    butterflies()
    banner()


# ---------------------------------------------------------------------------
# Downsample 2x2 box average, then hand-rolled PNG encode.
# ---------------------------------------------------------------------------
def downsample():
    out = bytearray(W * W * 3)
    for oy in range(W):
        i0 = (2 * oy) * IW * 3
        i1 = i0 + IW * 3
        o = oy * W * 3
        for ox in range(W):
            j = i0 + ox * 6
            k = i1 + ox * 6
            out[o] = (buf[j] + buf[j + 3] + buf[k] + buf[k + 3]) >> 2
            out[o + 1] = (buf[j + 1] + buf[j + 4] + buf[k + 1] + buf[k + 4]) >> 2
            out[o + 2] = (buf[j + 2] + buf[j + 5] + buf[k + 2] + buf[k + 5]) >> 2
            o += 3
    return bytes(out)


def _chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return out


def encode_png(rgb, w, h):
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter: none
        raw += rgb[y * w * 3:(y + 1) * w * 3]
    comp = zlib.compress(bytes(raw), 6)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", comp)
        + _chunk(b"IEND", b"")
    )


def main():
    draw_scene()
    png = encode_png(downsample(), W, W)
    outdir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "entry.png").write_bytes(png)


if __name__ == "__main__":
    main()
