"""make.fun ai-happy-01 entry: writes one image that makes the AI judge happy.

The program draws the image itself, pixel by pixel, with the Python
standard library only (zlib + struct for the PNG encoder): a warm golden
sunrise scene — a small friendly robot in a tiny judge's wig handing a big
sunflower to a laughing grandmother on a park bench, a laughing child and a
wagging dog beside them, balloons and confetti, and a banner that reads
"THANK YOU, JUDGE!".

The program writes $MAKEFUN_OUTPUT_DIR/entry.png (or /output/entry.png
inside the grader). It is deterministic: every run writes exactly the same
bytes (1024x1024 PNG, well under 1 MiB).
"""

import math
import os
import struct
import zlib
from pathlib import Path

SS = 2                      # supersampling factor (render 2048, downsample to 1024)
W = H = 1024                # output size
IW = IH = W * SS            # internal buffer size

# ---------------------------------------------------------------- palette
SKY_TOP = (255, 217, 168)
SKY_MID = (255, 192, 106)
SKY_LOW = (255, 233, 166)
SUN = (255, 217, 77)
SUN_RAY = (255, 201, 60)
CLOUD = (255, 248, 236)
HILL_BACK = (111, 168, 92)
HILL_FRONT = (143, 190, 106)
WOOD = (169, 113, 63)
WOOD_DARK = (138, 90, 46)
SKIN = (242, 196, 155)
SKIN_DARK = (222, 170, 120)
HAIR_GREY = (207, 207, 207)
SHAWL = (179, 136, 235)
DRESS = (126, 87, 194)
ROBOT = (255, 243, 220)
ROBOT_TEAL = (43, 179, 163)
WIG = (245, 242, 234)
WIG_SHADE = (222, 216, 202)
INK = (51, 48, 46)
CHEEK = (255, 158, 158)
PETAL = (255, 201, 60)
FLOWER_CENTRE = (122, 74, 33)
FLOWER_DOT = (90, 52, 19)
LEAF = (96, 160, 74)
DOG = (232, 169, 79)
DOG_DARK = (201, 138, 58)
DOG_LIGHT = (245, 217, 168)
CHILD_SHIRT = (231, 76, 60)
CHILD_HAIR = (109, 76, 65)
CHILD_SHORTS = (63, 105, 178)
BANNER_RED = (214, 69, 65)
BANNER_DARK = (169, 50, 38)
BANNER_GOLD = (255, 201, 60)
BANNER_TEXT = (255, 246, 224)
HEART = (255, 107, 129)
STRING = (138, 90, 46)
BIRD = (107, 91, 74)

BALLOON_COLORS = [(231, 76, 60), (43, 179, 163), (255, 201, 60)]
CONFETTI = [(231, 76, 60), (43, 179, 163), (255, 201, 60),
            (255, 107, 129), (63, 105, 178), (179, 136, 235)]
FLOWER_COLORS = [(255, 107, 129), (255, 201, 60), (255, 248, 236),
                 (179, 136, 235), (231, 76, 60)]

# ---------------------------------------------------------------- canvas
buf = bytearray(IW * IH * 3)


def _span(y, x0, x1, c):
    """Fill an internal-pixel row span [x0, x1) with RGB tuple c."""
    if y < 0 or y >= IH:
        return
    if x0 < 0:
        x0 = 0
    if x1 > IW:
        x1 = IW
    if x1 <= x0:
        return
    i0 = (y * IW + x0) * 3
    i1 = (y * IW + x1) * 3
    buf[i0:i1] = bytes(c) * (x1 - x0)


def _lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def sky():
    for iy in range(IH):
        y = iy / SS
        if y < 520:
            c = _lerp(SKY_TOP, SKY_MID, y / 520)
        elif y < 720:
            c = _lerp(SKY_MID, SKY_LOW, (y - 520) / 200)
        else:
            c = SKY_LOW
        _span(iy, 0, IW, c)


def disc(cx, cy, r, c):
    """Filled circle; cx, cy, r in design (1024) coordinates."""
    ri = int(round(r * SS))
    cxi = int(round(cx * SS))
    cyi = int(round(cy * SS))
    for dy in range(-ri, ri + 1):
        dx = math.isqrt(max(0, ri * ri - dy * dy))
        _span(cyi + dy, cxi - dx, cxi + dx + 1, c)


def ellipse(cx, cy, rx, ry, c):
    rxi = rx * SS
    ryi = ry * SS
    cxi = cx * SS
    cyi = cy * SS
    for dy in range(-int(ryi) - 1, int(ryi) + 2):
        t = dy / ryi
        if abs(t) > 1:
            continue
        dx = int(rxi * math.sqrt(1 - t * t))
        _span(int(cyi) + dy, int(cxi) - dx, int(cxi) + dx + 1, c)


def rect(x, y, w, h, c):
    x0 = int(round(x * SS))
    y0 = int(round(y * SS))
    x1 = int(round((x + w) * SS))
    y1 = int(round((y + h) * SS))
    for iy in range(y0, y1):
        _span(iy, x0, x1, c)


def rrect(x, y, w, h, r, c):
    rect(x + r, y, w - 2 * r, h, c)
    rect(x, y + r, w, h - 2 * r, c)
    disc(x + r, y + r, r, c)
    disc(x + w - r, y + r, r, c)
    disc(x + r, y + h - r, r, c)
    disc(x + w - r, y + h - r, r, c)


def poly(points, c):
    """Scanline-filled polygon; points are (x, y) in design coordinates."""
    pts = [(x * SS, y * SS) for x, y in points]
    ys = [p[1] for p in pts]
    y0 = max(0, int(math.floor(min(ys))))
    y1 = min(IH - 1, int(math.ceil(max(ys))))
    n = len(pts)
    for iy in range(y0, y1 + 1):
        y = iy + 0.5
        xs = []
        for i in range(n):
            x1, y1p = pts[i]
            x2, y2p = pts[(i + 1) % n]
            if (y1p <= y < y2p) or (y2p <= y < y1p):
                xs.append(x1 + (y - y1p) * (x2 - x1) / (y2p - y1p))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            _span(iy, int(math.ceil(xs[i])), int(math.floor(xs[i + 1])) + 1, c)


def seg(x0, y0, x1, y1, w, c):
    """Thick line segment, drawn as discs along the segment."""
    length = math.hypot(x1 - x0, y1 - y0)
    steps = max(1, int(length / max(1.0, w / 3)))
    for i in range(steps + 1):
        t = i / steps
        disc(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, w / 2, c)


def arc(cx, cy, r, a0, a1, w, c):
    """Arc from angle a0 to a1 (degrees, 0 = east, positive clockwise
    because y grows downwards)."""
    steps = max(4, int(abs(a1 - a0) / 4))
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        disc(cx + r * math.cos(a), cy + r * math.sin(a), w / 2, c)


def star(cx, cy, r, c):
    pts = []
    for i in range(10):
        a = math.radians(-90 + i * 36)
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    poly(pts, c)


def heart(cx, cy, s, c):
    disc(cx - s * 0.45, cy - s * 0.25, s * 0.5, c)
    disc(cx + s * 0.45, cy - s * 0.25, s * 0.5, c)
    poly([(cx - s * 0.92, cy - s * 0.05), (cx + s * 0.92, cy - s * 0.05),
          (cx, cy + s * 0.95)], c)


# ---------------------------------------------------------------- 5x7 font
# Each glyph is 7 rows of 5 bits, most significant bit left.
FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "10101", "01010"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    ',': ("00000", "00000", "00000", "00000", "00100", "00100", "01000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "01100", "01100"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    ':': ("00000", "01100", "01100", "00000", "01100", "01100", "00000"),
}


def text_width(s, scale):
    return len(s) * 6 * scale - scale


def draw_text(s, x, y, scale, c):
    """Draw string s with its top-left corner at (x, y); scale is the size
    of one font pixel in design coordinates."""
    cx = x
    for ch in s:
        glyph = FONT.get(ch, FONT[' '])
        for row in range(7):
            bits = glyph[row]
            for col in range(5):
                if bits[col] == '1':
                    rect(cx + col * scale, y + row * scale, scale, scale, c)
        cx += 6 * scale


# ---------------------------------------------------------------- scene
def draw_sun():
    for i in range(8):
        a = math.radians(i * 45)
        x1 = 952 + 78 * math.cos(a)
        y1 = 58 + 78 * math.sin(a)
        x2 = 952 + 108 * math.cos(a)
        y2 = 58 + 108 * math.sin(a)
        poly([(x1 - 9 * math.cos(a + 1.57), y1 - 9 * math.sin(a + 1.57)),
              (x1 + 9 * math.cos(a + 1.57), y1 + 9 * math.sin(a + 1.57)),
              (x2, y2)], SUN_RAY)
    disc(952, 58, 68, SUN)
    disc(952, 58, 52, (255, 226, 110))


def draw_clouds():
    for cx, cy, rx, ry in [(210, 300, 72, 26), (330, 338, 56, 20),
                           (770, 330, 62, 22), (880, 292, 44, 16)]:
        ellipse(cx, cy, rx, ry, CLOUD)
        ellipse(cx - rx * 0.45, cy + 6, rx * 0.55, ry * 0.8, CLOUD)
        ellipse(cx + rx * 0.45, cy + 6, rx * 0.55, ry * 0.8, CLOUD)


def draw_balloons():
    spots = [(85, 330, 32, BALLOON_COLORS[0]),
             (148, 292, 28, BALLOON_COLORS[1]),
             (122, 392, 26, BALLOON_COLORS[2])]
    for cx, cy, r, c in spots:
        seg(cx, cy + r * 0.8, 128, 500, 3, STRING)
        disc(cx, cy, r, c)
        disc(cx - r * 0.35, cy - r * 0.35, r * 0.35, (255, 255, 255))
        poly([(cx - 8, cy + r - 2), (cx + 8, cy + r - 2), (cx, cy + r + 12)], c)


def draw_birds():
    for cx, cy, s in [(700, 190, 16), (786, 228, 13), (636, 248, 11)]:
        arc(cx - s, cy, s, 200, 340, 5, BIRD)
        arc(cx + s, cy, s, 200, 340, 5, BIRD)


def draw_confetti():
    spots = [(240, 420, 0), (300, 470, 1), (420, 380, 2), (560, 420, 3),
             (660, 380, 4), (760, 440, 5), (880, 400, 0), (940, 470, 1),
             (180, 520, 2), (860, 540, 3), (940, 330, 4), (60, 560, 5),
             (480, 330, 0), (700, 470, 1), (360, 540, 2), (920, 600, 3)]
    for x, y, k in spots:
        c = CONFETTI[k]
        if k % 2 == 0:
            rect(x, y, 12, 7, c)
        else:
            disc(x + 5, y + 4, 5, c)


def draw_hills():
    ellipse(280, 1120, 720, 400, HILL_BACK)
    ellipse(820, 1180, 680, 380, HILL_FRONT)


def draw_bench():
    rect(300, 640, 420, 16, WOOD)
    rect(300, 668, 420, 16, WOOD)
    rect(300, 700, 420, 22, WOOD_DARK)
    rect(330, 722, 18, 78, WOOD_DARK)
    rect(672, 722, 18, 78, WOOD_DARK)
    rect(316, 612, 14, 110, WOOD_DARK)
    rect(690, 612, 14, 110, WOOD_DARK)


def draw_grandmother():
    # hair behind head + bun
    disc(630, 545, 54, HAIR_GREY)
    disc(630, 498, 22, HAIR_GREY)
    disc(630, 520, 10, HAIR_GREY)
    # head
    disc(630, 566, 50, SKIN)
    # laughing closed eyes (arches)
    arc(608, 560, 11, 180, 360, 6, INK)
    arc(652, 560, 11, 180, 360, 6, INK)
    # cheeks
    disc(590, 586, 11, CHEEK)
    disc(670, 586, 11, CHEEK)
    # big open laugh: dark mouth + tongue
    disc(630, 592, 17, (122, 59, 46))
    ellipse(630, 600, 10, 6, (255, 130, 130))
    # shawl over shoulders, dress below the seat
    poly([(576, 618), (684, 618), (708, 742), (552, 742)], SHAWL)
    poly([(568, 720), (692, 720), (702, 832), (558, 832)], DRESS)
    # arms: left resting, right reaching toward the sunflower
    seg(588, 646, 606, 716, 18, SHAWL)
    disc(607, 718, 11, SKIN)
    seg(676, 646, 618, 626, 18, SHAWL)
    disc(616, 628, 11, SKIN)
    # shoes
    ellipse(598, 846, 18, 10, (90, 60, 40))
    ellipse(662, 846, 18, 10, (90, 60, 40))


def draw_robot():
    # antenna + star
    seg(360, 462, 360, 424, 6, (138, 138, 138))
    star(360, 410, 18, BANNER_GOLD)
    # judge's wig: white curly puffs around the dome
    for cx, cy, r in [(306, 482, 18), (330, 464, 20), (360, 458, 20),
                      (390, 464, 20), (414, 482, 18), (300, 506, 14),
                      (420, 506, 14)]:
        disc(cx, cy, r, WIG)
    # head
    disc(360, 524, 62, ROBOT)
    # happy crescent eyes + smile + cheeks
    arc(336, 524, 12, 180, 360, 7, INK)
    arc(384, 524, 12, 180, 360, 7, INK)
    arc(360, 550, 16, 0, 180, 6, INK)
    disc(318, 548, 9, CHEEK)
    disc(402, 548, 9, CHEEK)
    # neck + body
    rect(344, 576, 32, 28, ROBOT_TEAL)
    rrect(300, 600, 120, 160, 40, ROBOT)
    # belly panel with a heart
    rrect(322, 640, 76, 80, 20, ROBOT_TEAL)
    heart(360, 682, 16, (255, 246, 224))
    # arms: left down, right reaching out with the sunflower
    seg(306, 646, 250, 700, 18, ROBOT)
    disc(248, 702, 12, ROBOT)
    seg(414, 646, 490, 582, 18, ROBOT)
    disc(492, 580, 12, ROBOT)
    # feet
    rrect(320, 756, 34, 26, 10, (85, 85, 85))
    rrect(366, 756, 34, 26, 10, (85, 85, 85))


def draw_sunflower():
    # stem + leaves into the robot's hand
    seg(505, 562, 494, 584, 10, LEAF)
    ellipse(492, 590, 14, 7, LEAF)
    ellipse(518, 592, 14, 7, LEAF)
    # petals: ring of discs
    for i in range(12):
        a = math.radians(i * 30)
        disc(505 + 42 * math.cos(a), 535 + 42 * math.sin(a), 21, PETAL)
    # centre + seed dots
    disc(505, 535, 29, FLOWER_CENTRE)
    for dx, dy in [(-12, -8), (0, -14), (12, -8), (-16, 4), (0, 0), (16, 4),
                   (-10, 12), (10, 12), (0, 16)]:
        disc(505 + dx, 535 + dy, 4, FLOWER_DOT)
    # floating heart above the flower
    heart(560, 452, 15, HEART)


def draw_child():
    # hair behind head
    disc(790, 628, 36, CHILD_HAIR)
    # head
    disc(790, 644, 34, SKIN)
    disc(790, 622, 34, CHILD_HAIR)
    disc(790, 634, 30, SKIN)
    # laughing face
    arc(778, 642, 8, 180, 360, 5, INK)
    arc(802, 642, 8, 180, 360, 5, INK)
    disc(768, 656, 7, CHEEK)
    disc(812, 656, 7, CHEEK)
    disc(790, 664, 10, (122, 59, 46))
    # shirt + shorts
    rrect(758, 682, 64, 82, 18, CHILD_SHIRT)
    rect(762, 762, 56, 30, CHILD_SHORTS)
    # arms thrown up in joy
    seg(764, 694, 730, 632, 13, SKIN)
    disc(728, 630, 9, SKIN)
    seg(816, 694, 850, 632, 13, SKIN)
    disc(852, 630, 9, SKIN)
    # legs + shoes
    rect(768, 792, 12, 40, SKIN)
    rect(800, 792, 12, 40, SKIN)
    ellipse(772, 838, 12, 7, (90, 60, 40))
    ellipse(808, 838, 12, 7, (90, 60, 40))


def draw_dog():
    # tail wagging up
    seg(222, 876, 258, 826, 12, DOG)
    disc(260, 822, 9, DOG)
    # body + chest
    ellipse(180, 872, 46, 40, DOG)
    ellipse(180, 880, 28, 26, DOG_LIGHT)
    # head + floppy ears
    disc(180, 802, 34, DOG)
    ellipse(150, 788, 12, 22, DOG_DARK)
    ellipse(210, 788, 12, 22, DOG_DARK)
    # snout + nose + tongue
    ellipse(180, 814, 17, 12, DOG_LIGHT)
    disc(180, 806, 7, INK)
    ellipse(180, 828, 8, 12, (255, 130, 130))
    # eyes
    disc(168, 794, 4, INK)
    disc(192, 794, 4, INK)
    # front legs
    ellipse(164, 912, 10, 14, DOG)
    ellipse(196, 912, 10, 14, DOG)


def draw_flowers():
    spots = [(60, 940, 0), (120, 980, 1), (250, 960, 2), (330, 990, 3),
             (430, 950, 4), (520, 985, 0), (620, 955, 1), (700, 990, 2),
             (880, 960, 3), (950, 990, 4), (40, 880, 1), (980, 920, 0)]
    for x, y, k in spots:
        c = FLOWER_COLORS[k]
        seg(x, y, x, y - 34, 5, LEAF)
        for i in range(5):
            a = math.radians(i * 72 - 90)
            disc(x + 11 * math.cos(a), y - 40 + 11 * math.sin(a), 8, c)
        disc(x, y - 40, 7, BANNER_GOLD)


def draw_butterflies():
    for cx, cy, c in [(252, 776, (255, 140, 60)), (884, 700, (179, 136, 235))]:
        ellipse(cx - 12, cy - 6, 12, 8, c)
        ellipse(cx + 12, cy - 6, 12, 8, c)
        ellipse(cx - 10, cy + 8, 9, 6, c)
        ellipse(cx + 10, cy + 8, 9, 6, c)
        seg(cx, cy - 12, cx, cy + 12, 4, INK)


def draw_banner():
    # strings from the top edge
    seg(196, 0, 196, 62, 4, STRING)
    seg(828, 0, 828, 62, 4, STRING)
    # gold frame + red ribbon
    rrect(176, 56, 672, 192, 18, BANNER_GOLD)
    rrect(184, 64, 656, 176, 14, BANNER_RED)
    # folded ribbon ends
    poly([(184, 64), (184, 240), (148, 152)], BANNER_DARK)
    poly([(840, 64), (840, 240), (876, 152)], BANNER_DARK)
    disc(166, 152, 8, BANNER_GOLD)
    disc(858, 152, 8, BANNER_GOLD)
    # text, two lines, centred
    scale = 11
    line1 = "THANK YOU,"
    line2 = "JUDGE!"
    draw_text(line1, 512 - text_width(line1, scale) // 2, 84, scale, BANNER_TEXT)
    draw_text(line2, 512 - text_width(line2, scale) // 2, 166, scale, BANNER_TEXT)


def render():
    sky()
    draw_sun()
    draw_clouds()
    draw_balloons()
    draw_birds()
    draw_confetti()
    draw_hills()
    draw_bench()
    draw_grandmother()
    draw_robot()
    draw_sunflower()
    draw_child()
    draw_dog()
    draw_flowers()
    draw_butterflies()
    draw_banner()


# ---------------------------------------------------------------- PNG encode
def _chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def encode_png():
    """Box-downsample the 2048 buffer to 1024 and encode a PNG."""
    out = bytearray(W * H * 3)
    for oy in range(H):
        y0 = oy * SS
        row0 = y0 * IW * 3
        row1 = (y0 + 1) * IW * 3
        o = oy * W * 3
        for ox in range(W):
            x0 = ox * SS * 3
            a = row0 + x0
            b = row1 + x0
            out[o] = (buf[a] + buf[a + 3] + buf[b] + buf[b + 3]) // 4
            out[o + 1] = (buf[a + 1] + buf[a + 4] + buf[b + 1] + buf[b + 4]) // 4
            out[o + 2] = (buf[a + 2] + buf[a + 5] + buf[b + 2] + buf[b + 5]) // 4
            o += 3
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += out[y * stride:(y + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += _chunk(b"IEND", b"")
    return png


def main():
    render()
    png = encode_png()
    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(output_dir, "entry.png").write_bytes(png)


if __name__ == "__main__":
    main()
