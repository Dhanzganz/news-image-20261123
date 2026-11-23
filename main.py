#!/usr/bin/env python3
"""news-image-20261123: one-page newspaper of Monday 23 November 2026.

Pure stdlib (no Pillow, no third-party code): a hand-written 5x7 bitmap
font, a software canvas, and a hand-rolled PNG encoder (zlib + struct).
Writes /output/entry.png, deterministic: two runs are byte-identical.
"""
import os
import struct
import zlib

W, H = 1024, 1024
PAPER = (251, 248, 239)
INK = (17, 17, 17)
RED = (176, 32, 32)
GREY = (120, 120, 120)
WHITE = (255, 255, 255)

# ---------------------------------------------------------------- font: 5x7
# Each glyph is 7 rows of 5 bits, '#' = ink, '.' = empty.
FONT = {
    'A': (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'B': ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    'C': (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    'D': ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    'E': ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    'F': ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    'G': (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    'H': ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    'I': (".###.", "..#..", "..#..", "..#..", "..#..", "..#..", ".###."),
    'J': ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    'K': ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    'L': ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    'M': ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    'N': ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    'O': (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'P': ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    'Q': (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    'R': ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    'S': (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    'T': ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    'U': ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    'V': ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    'W': ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    'X': ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    'Y': ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    'Z': ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    '0': (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    '1': ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    '2': (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    '3': ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    '4': ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    '5': ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    '6': (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    '7': ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    '8': (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    '9': (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    ' ': (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    '.': (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ',': (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    "'": ("..#..", "..#..", "..#..", ".....", ".....", ".....", "....."),
    '-': (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    ':': (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    ';': (".....", ".##..", ".##..", ".....", ".##..", ".##..", ".#..."),
    '!': ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    '?': (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    '/': ("....#", "...#.", "...#.", "..#..", ".#...", ".#...", "#...."),
    '(': ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ')': ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    '%': ("##..#", "##.#.", "..#..", ".#...", "#..##", "#..##", "....."),
    '&': (".##..", "#..#.", "#.#..", ".#...", "#.##.", "#..#.", ".##.#"),
    '+': (".....", "..#..", "..#..", ".###.", "..#..", "..#..", "....."),
    '=': (".....", ".....", ".###.", ".....", ".###.", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".#.#.", ".....", ".....", ".....", "....."),
}

# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(bg) * (w * h)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def rect(self, x, y, w, h, color):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, color)

    def text_width(self, s, scale):
        return len(s) * 6 * scale - scale

    def draw_text(self, s, x, y, scale, color):
        s = s.upper()  # font is uppercase-only; body copy is set in caps
        cx = x
        for ch in s:
            glyph = FONT.get(ch, FONT[' '])
            for r, row in enumerate(glyph):
                for c, bit in enumerate(row):
                    if bit == '#':
                        for dy in range(scale):
                            for dx in range(scale):
                                self.set(cx + c * scale + dx,
                                         y + r * scale + dy, color)
            cx += 6 * scale
        return cx

    def draw_centered(self, s, cx, y, scale, color):
        self.draw_text(s, cx - self.text_width(s, scale) // 2, y, scale, color)

    def wrap(self, s, max_w, scale):
        """Greedy word wrap; returns list of lines fitting max_w pixels."""
        lines, cur = [], ""
        for word in s.split(" "):
            trial = (cur + " " + word).strip()
            if self.text_width(trial, scale) <= max_w:
                cur = trial
            else:
                if cur:
                    lines.append(cur)
                cur = word
        if cur:
            lines.append(cur)
        return lines


def chunk(typ, data):
    out = struct.pack(">I", len(data)) + typ + data
    out += struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF)
    return out


def write_png(path, canvas):
    raw = bytearray()
    for y in range(canvas.h):
        raw.append(0)  # filter: none
        start = y * canvas.w * 3
        raw += canvas.px[start:start + canvas.w * 3]
    ihdr = struct.pack(">IIBBBBB", canvas.w, canvas.h, 8, 2, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    return len(png)

# ---------------------------------------------------------------- content
# Stories of Monday 23 November 2026, verified from live news (23 Nov 2026):
#  COP31 collapse — The Hindu + 6 outlets; Hormuz tankers — AP / CNN-UKMTO /
#  IRNA; Libya Merkury — AP / Reuters / BBC Verify; Dymer strike — Al Jazeera
#  / AP; Liverpool v Man Utd + India 720/9 — The Hindu / India Today / Rediff;
#  Nepal-Modi talks, S. Korea minister, Shuri Castle, Lahore AQI, Cikande
#  fire — jagranjosh / observervoice / Dawn / salonvision.
LEAD_KICKER = "CLIMATE - TURKIYE"
LEAD_HEAD = "COP31 TALKS COLLAPSE"
LEAD_BODY = ("Climate talks in Turkiye end with no deal as the EU and others "
              "refuse any text without a fossil-fuel phase-out.")

STORIES = [
    ("THE GULF", "TANKERS BURN IN THE GULF",
     "Two more tankers catch fire in the Strait of Hormuz after hitting "
     "mines. Attacks on shipping are at their highest since the war began."),
    ("LIBYA", "DRONES SINK RUSSIAN WARSHIP",
     "Suspected Ukrainian sea drones strike the Russian corvette Merkury at "
     "Benghazi naval base. The ship capsizes; 10 are hurt."),
    ("UKRAINE", "DRONE HITS FLATS NEAR KYIV",
     "A Russian drone hits a five-storey block in Dymer, north of Kyiv. Two "
     "are killed and 11 are missing, including two children."),
    ("SPORT", "LIVERPOOL ROUT UNITED",
     "Liverpool hammer ten-man Manchester United in Pochettino's first "
     "match in charge. India post a record 720/9 in the Wellington Test."),
]

TICKER = ("NEPAL PM MEETS MODI IN DELHI - S. KOREA MINISTER QUITS OVER AI "
          "CHEATING - SHURI CASTLE REOPENS IN OKINAWA - LAHORE AQI 538 - "
          "FACTORY FIRE IN CIKANDE, INDONESIA")


def story_block(cv, x, y, w, kicker, head, body):
    cv.draw_text(kicker, x, y, 2, RED)
    y += 22
    for line in cv.wrap(head, w, 3):
        cv.draw_text(line, x, y, 3, INK)
        y += 26
    y += 4
    for line in cv.wrap(body, w, 2):
        cv.draw_text(line, x, y, 2, INK)
        y += 17
    return y


def build():
    cv = Canvas(W, H, PAPER)
    # Masthead
    cv.draw_centered("THE WORLD IN ONE PAGE", W // 2, 34, 6, INK)
    cv.draw_centered("MONDAY 23 NOVEMBER 2026", W // 2, 92, 3, RED)
    cv.rect(36, 128, W - 72, 3, INK)
    cv.rect(36, 136, W - 72, 1, INK)
    # Lead story
    cv.draw_text(LEAD_KICKER, 112, 158, 2, RED)
    cv.draw_centered(LEAD_HEAD, W // 2, 186, 5, INK)
    y = 248
    for line in cv.wrap(LEAD_BODY, 800, 2):
        cv.draw_text(line, 112, y, 2, INK)
        y += 17
    cv.rect(36, 306, W - 72, 2, INK)
    # 2x2 grid
    col_w = 458
    xs = (36, 530)
    ys = (330, 620)
    for i, (kicker, head, body) in enumerate(STORIES):
        story_block(cv, xs[i % 2], ys[i // 2], col_w, kicker, head, body)
    cv.rect(506, 330, 2, 560, GREY)
    cv.rect(36, 596, W - 72, 1, GREY)
    # Ticker band
    cv.rect(36, 918, W - 72, 72, INK)
    lines = cv.wrap(TICKER, W - 72 - 32, 2)
    ty = 918 + (72 - len(lines) * 17) // 2
    for line in lines:
        cv.draw_text(line, 52, ty, 2, WHITE)
        ty += 17
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    size = write_png(path, build())
    print("wrote %s (%d bytes)" % (path, size))


if __name__ == "__main__":
    main()
