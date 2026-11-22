#!/usr/bin/env python3
"""The picture that tastes of one ingredient.

A top-down bowl of ramen, rendered procedurally, pixel by pixel.
Pure Python stdlib only (the sandbox has no network and no PIL):
the image is drawn with distance fields and soft shading, then
encoded as a PNG with zlib.

Writes /output/entry.png (512x512 RGB PNG, deterministic).
"""
import math
import os
import struct
import zlib

W = H = 512
OUT = "/output/entry.png"

CX, CY = 256.0, 276.0          # bowl centre
BOWL_R = 205.0                 # outer rim
BROTH_R = 178.0                # broth surface


def clamp(x, a, b):
    return a if x < a else (b if x > b else x)


def sstep(a, b, x):
    t = (x - a) / (b - a)
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return t * t * (3.0 - 2.0 * t)


def mix(a, b, t):
    return a + (b - a) * t


def hash2(x, y):
    n = (x * 374761393 + y * 668265263) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    n = (n ^ (n >> 16)) & 0xFFFFFFFF
    return n / 4294967296.0


# ---- palette -------------------------------------------------------------
TABLE_DARK = (20, 12, 7)
TABLE_WARM = (58, 36, 23)
BOWL_OUT = (30, 42, 68)
BOWL_RIM = (52, 70, 102)
BOWL_GOLD = (201, 162, 39)
BROTH_C = (201, 123, 37)
BROTH_M = (168, 90, 20)
BROTH_E = (124, 61, 12)
NOODLE = (235, 203, 126)
NOODLE_D = (199, 154, 69)
NOODLE_H = (247, 227, 168)


def render():
    img = bytearray(W * H * 3)
    sqrt = math.sqrt
    sin = math.sin
    cos = math.cos
    atan2 = math.atan2
    pi = math.pi

    # noodle rings: (radius, phase, width)
    rings = []
    for k in range(9):
        rings.append((42.0 + k * 15.5, k * 1.7 + 0.6, 5.2))

    for y in range(H):
        dy = y - CY
        row = y * W * 3
        for x in range(W):
            dx = x - CX
            r = sqrt(dx * dx + dy * dy)

            # ---- table: warm dark wood, spotlight on the bowl ------------
            tr = clamp(1.0 - r / 420.0, 0.0, 1.0)
            wood = 0.5 + 0.5 * sin((x * 0.9 + y * 0.35) * 0.045
                                   + 1.6 * sin(y * 0.021))
            pr = mix(TABLE_DARK[0], TABLE_WARM[0], tr) * (0.88 + 0.12 * wood)
            pg = mix(TABLE_DARK[1], TABLE_WARM[1], tr) * (0.88 + 0.12 * wood)
            pb = mix(TABLE_DARK[2], TABLE_WARM[2], tr) * (0.88 + 0.12 * wood)

            if r < BOWL_R + 26.0:
                # ---- soft drop shadow under the bowl ---------------------
                sh = sstep(BOWL_R + 26.0, BOWL_R - 6.0, r) * 0.42
                pr *= 1.0 - sh
                pg *= 1.0 - sh
                pb *= 1.0 - sh

            if r < BOWL_R:
                # ---- ceramic bowl ----------------------------------------
                # radial ceramic shading: lighter toward upper-left
                lx = (dx * -0.6 + dy * -0.8) / BOWL_R
                shade = 0.82 + 0.30 * clamp(lx * 0.5 + 0.5, 0.0, 1.0)
                pr = BOWL_OUT[0] * shade
                pg = BOWL_OUT[1] * shade
                pb = BOWL_OUT[2] * shade
                # rim band
                if r > 186.0:
                    t = sstep(186.0, 205.0, r)
                    pr = mix(pr, BOWL_RIM[0], t)
                    pg = mix(pg, BOWL_RIM[1], t)
                    pb = mix(pb, BOWL_RIM[2], t)
                    # thin gold line on the rim
                    gl = 1.0 - abs(r - 198.0) / 2.2
                    if gl > 0.0:
                        pr = mix(pr, BOWL_GOLD[0], gl)
                        pg = mix(pg, BOWL_GOLD[1], gl)
                        pb = mix(pb, BOWL_GOLD[2], gl)
                # inner rim shadow just inside the broth edge
                if r < BROTH_R + 7.0:
                    sh2 = sstep(BROTH_R + 7.0, BROTH_R - 2.0, r) * 0.30
                    pr *= 1.0 - sh2
                    pg *= 1.0 - sh2
                    pb *= 1.0 - sh2

            if r < BROTH_R:
                # ---- broth: golden, deeper toward the rim ----------------
                t = clamp(r / BROTH_R, 0.0, 1.0)
                br = mix(BROTH_C[0], BROTH_E[0], t * t)
                bg = mix(BROTH_C[1], BROTH_E[1], t * t)
                bb = mix(BROTH_C[2], BROTH_E[2], t * t)
                # warm light from upper-left
                lx = (dx * -0.7 + dy * -0.7) / BROTH_R
                glow = 0.88 + 0.24 * clamp(lx * 0.5 + 0.5, 0.0, 1.0)
                br *= glow
                bg *= glow
                bb *= glow
                # glossy specular arc, upper-left
                sa = atan2(dy, dx)
                sd = abs(((sa + 2.4 + pi) % (2 * pi)) - pi)
                spec = sstep(0.85, 0.0, sd) * sstep(50.0, 110.0, r) * 0.65
                br = mix(br, 245.0, spec)
                bg = mix(bg, 201.0, spec)
                bb = mix(bb, 106.0, spec)
                pr, pg, pb = br, bg, bb

                # ---- noodle swirls: wavy concentric strands -------------
                ang = atan2(dy, dx)
                for (rr, ph, wdt) in rings:
                    wob = 3.6 * sin(3.0 * ang + ph) + 1.8 * sin(5.0 * ang + ph * 2.0)
                    d = abs(r - (rr + wob))
                    if d < wdt:
                        nm = 1.0 - d / wdt
                        nm = nm * nm
                        # strand shading: bright centre, dark edge
                        nr = mix(NOODLE_D[0], NOODLE_H[0], nm)
                        ng = mix(NOODLE_D[1], NOODLE_H[1], nm)
                        nb = mix(NOODLE_D[2], NOODLE_H[2], nm)
                        a = 0.55 + 0.45 * nm
                        pr = mix(pr, nr, a)
                        pg = mix(pg, ng, a)
                        pb = mix(pb, nb, a)
                        break

            # ---- vignette ------------------------------------------------
            vg = 1.0 - 0.22 * sstep(300.0, 420.0, r)
            pr *= vg
            pg *= vg
            pb *= vg

            i = row + x * 3
            img[i] = int(clamp(pr, 0, 255))
            img[i + 1] = int(clamp(pg, 0, 255))
            img[i + 2] = int(clamp(pb, 0, 255))
    return img


def _blend(img, x, y, col, a):
    """Alpha-blend one pixel (clamped to the canvas)."""
    if 0 <= x < W and 0 <= y < H and a > 0.0:
        i = (y * W + x) * 3
        img[i] = int(img[i] * (1.0 - a) + col[0] * a)
        img[i + 1] = int(img[i + 1] * (1.0 - a) + col[1] * a)
        img[i + 2] = int(img[i + 2] * (1.0 - a) + col[2] * a)


def disc(img, cx, cy, rad, col, a=1.0):
    """Soft-edged filled disc."""
    r0 = int(cx - rad - 2)
    r1 = int(cx + rad + 2)
    c0 = int(cy - rad - 2)
    c1 = int(cy + rad + 2)
    for yy in range(max(0, c0), min(H, c1 + 1)):
        for xx in range(max(0, r0), min(W, r1 + 1)):
            d = math.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
            al = a * (1.0 - sstep(rad - 1.5, rad + 1.5, d))
            if al > 0.01:
                _blend(img, xx, yy, col, al)


def ring(img, cx, cy, rad, wdt, col, a=1.0):
    """Soft-edged ring (green-onion slice)."""
    r0 = int(cx - rad - wdt - 2)
    r1 = int(cx + rad + wdt + 2)
    c0 = int(cy - rad - wdt - 2)
    c1 = int(cy + rad + wdt + 2)
    for yy in range(max(0, c0), min(H, c1 + 1)):
        for xx in range(max(0, r0), min(W, r1 + 1)):
            d = abs(math.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) - rad)
            al = a * (1.0 - sstep(wdt - 1.0, wdt + 1.0, d))
            if al > 0.01:
                _blend(img, xx, yy, col, al)


def ellipse(img, cx, cy, rx, ry, rot, col, a=1.0):
    """Soft-edged filled rotated ellipse."""
    r0 = int(cx - rx - 3)
    r1 = int(cx + rx + 3)
    c0 = int(cy - ry - 3)
    c1 = int(cy + ry + 3)
    cr, sr = math.cos(rot), math.sin(rot)
    for yy in range(max(0, c0), min(H, c1 + 1)):
        for xx in range(max(0, r0), min(W, r1 + 1)):
            px, py = xx - cx, yy - cy
            ux = (px * cr + py * sr) / rx
            uy = (-px * sr + py * cr) / ry
            d = math.sqrt(ux * ux + uy * uy)
            al = a * (1.0 - sstep(0.94, 1.0, d))
            if al > 0.01:
                _blend(img, xx, yy, col, al)


def toppings(img):
    # ---- soft egg, upper right ------------------------------------------
    disc(img, 345, 195, 44, (247, 241, 227), 1.0)          # white
    disc(img, 345, 195, 40, (250, 246, 236), 1.0)
    # yolk: deep orange, glossy highlight
    for yy in range(170, 221):
        for xx in range(320, 371):
            d = math.sqrt((xx - 345) ** 2 + (yy - 195) ** 2)
            if d < 23:
                t = d / 23.0
                col = (mix(255, 232, t), mix(158, 93, t), mix(27, 0, t))
                hl = sstep(14.0, 2.0, math.sqrt((xx - 338) ** 2 + (yy - 187) ** 2)) * 0.55
                _blend(img, xx, yy, (mix(col[0], 255, hl), mix(col[1], 210, hl), mix(col[2], 122, hl)), 1.0)

    # ---- chashu slices, lower left --------------------------------------
    ellipse(img, 168, 318, 52, 40, -0.5, (126, 59, 30), 1.0)
    ellipse(img, 168, 318, 46, 34, -0.5, (180, 101, 58), 1.0)
    ellipse(img, 168, 318, 40, 28, -0.5, (196, 122, 74), 1.0)
    ellipse(img, 205, 345, 46, 36, -0.3, (126, 59, 30), 1.0)
    ellipse(img, 205, 345, 40, 30, -0.3, (180, 101, 58), 1.0)
    # seared edge highlight on the first slice
    ellipse(img, 160, 308, 34, 22, -0.5, (226, 158, 104), 0.5)

    # ---- nori sheet, upper left, leaning on the rim ---------------------
    ellipse(img, 150, 168, 34, 48, 0.35, (22, 40, 26), 1.0)
    ellipse(img, 150, 168, 30, 44, 0.35, (38, 66, 42), 0.85)

    # ---- green onion rings ----------------------------------------------
    onion_spots = [
        (300, 330, 7), (270, 360, 6), (330, 300, 6), (240, 320, 7),
        (310, 250, 6), (215, 280, 6), (285, 200, 6), (250, 235, 7),
        (360, 270, 6), (195, 240, 6), (330, 350, 7), (230, 360, 6),
        (295, 165, 6), (260, 160, 6), (375, 320, 6), (185, 300, 7),
    ]
    for (ox, oy, orad) in onion_spots:
        ring(img, ox, oy, orad, 2.6, (124, 181, 24), 0.95)
        ring(img, ox, oy, orad, 1.2, (168, 217, 78), 0.8)

    # ---- chili oil droplets, glossy --------------------------------------
    for (ox, oy, orad) in [(280, 285, 8), (320, 225, 6), (230, 205, 7),
                            (355, 300, 5), (260, 335, 6), (300, 175, 5)]:
        disc(img, ox, oy, orad, (194, 46, 10), 0.95)
        disc(img, ox - orad * 0.3, oy - orad * 0.3, orad * 0.35, (255, 220, 180), 0.8)

    # ---- sesame seeds ----------------------------------------------------
    for k in range(34):
        sx = 130 + int(hash2(k, 7) * 250)
        sy = 150 + int(hash2(k, 13) * 240)
        dx = sx - CX
        dy = sy - CY
        if math.sqrt(dx * dx + dy * dy) < BROTH_R - 12:
            disc(img, sx, sy, 1.6, (242, 227, 192), 0.9)


def chopsticks(img):
    # two wooden sticks resting diagonally across the bowl rim
    for (ax, ay, bx, by, off) in [(392, 92, 168, 402, 0), (404, 104, 180, 414, 0)]:
        vx, vy = bx - ax, by - ay
        ln2 = vx * vx + vy * vy
        r0 = int(min(ax, bx) - 10)
        r1 = int(max(ax, bx) + 10)
        c0 = int(min(ay, by) - 10)
        c1 = int(max(ay, by) + 10)
        for yy in range(max(0, c0), min(H, c1 + 1)):
            for xx in range(max(0, r0), min(W, r1 + 1)):
                t = ((xx - ax) * vx + (yy - ay) * vy) / ln2
                t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
                px = ax + t * vx - xx
                py = ay + t * vy - yy
                d = math.sqrt(px * px + py * py)
                if d < 5.0:
                    # wood with a bright upper edge and dark tip
                    edge = sstep(5.0, 2.0, d)
                    col = (mix(122, 169, edge), mix(74, 118, edge), mix(31, 63, edge))
                    if t > 0.86:
                        col = (74, 44, 16)
                    _blend(img, xx, yy, col, 0.97 * (1.0 - sstep(4.2, 5.0, d)))


def steam(img):
    # three soft wavy columns of steam above the bowl
    for col_x, ph in [(196, 0.0), (256, 2.1), (316, 4.2)]:
        for yy in range(8, 150):
            rise = (150 - yy) / 142.0
            wx = col_x + 16.0 * math.sin(yy * 0.045 + ph) + 6.0 * math.sin(yy * 0.11 + ph * 2.0)
            for xx in range(int(wx - 26), int(wx + 27)):
                if 0 <= xx < W:
                    d = abs(xx - wx) / 26.0
                    a = (1.0 - d * d) * 0.16 * rise * sstep(0.0, 0.35, rise)
                    if a > 0.004:
                        _blend(img, xx, yy, (255, 250, 244), a)


def grain(img):
    for y in range(H):
        for x in range(W):
            n = (hash2(x, y) - 0.5) * 9.0
            i = (y * W + x) * 3
            img[i] = int(clamp(img[i] + n, 0, 255))
            img[i + 1] = int(clamp(img[i + 1] + n, 0, 255))
            img[i + 2] = int(clamp(img[i + 2] + n, 0, 255))


def write_png(img, path):
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)  # filter: none
        raw += img[y * stride:(y + 1) * stride]
    data = zlib.compress(bytes(raw), 6)
    png = bytearray()
    png += b"\x89PNG\r\n\x1a\n"

    def chunk(tag, payload):
        png.extend(struct.pack(">I", len(payload)))
        png.extend(tag)
        png.extend(payload)
        png.extend(struct.pack(">I", zlib.crc32(tag + payload) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    chunk(b"IHDR", ihdr)
    chunk(b"IDAT", data)
    chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    return len(png)


def main():
    img = render()
    toppings(img)
    chopsticks(img)
    steam(img)
    grain(img)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    size = write_png(img, OUT)
    print(f"wrote {OUT} ({W}x{H}, {size} bytes)")


if __name__ == "__main__":
    main()
