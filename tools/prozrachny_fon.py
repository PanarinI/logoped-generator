# -*- coding: utf-8 -*-
"""
prozrachny_fon.py — СДЕЛАТЬ ВНЕШНИЙ БЕЛЫЙ ФОН КАРТИНКИ ПРОЗРАЧНЫМ.

Зачем. Поймал автор 2026-08-26 на звуковой дорожке: «спрайт прям своим белым
фоном заслоняет дорожку». И правда — у картинок банка фон непрозрачный белый,
поэтому гараж в центре спирали и машина у старта закрывали линию белым
прямоугольником. На бумаге это читается как дыра в дорожке.

Чинить это наложением в стилях (`mix-blend-mode`) было бы лечением экрана, а не
материи: тот же белый ящик уехал бы в PDF и в Word. Поэтому прозрачность
делается В САМИХ ФАЙЛАХ — один раз и для всех выходов.

Как. Заливкой ОТ КРАЁВ, а не «все белые пиксели»: внутренняя белизна рисунка
(белок глаза, окно гаража, брюхо самолёта) обязана уцелеть. Заливка идёт с
рамки картинки по светлым пикселям и останавливается о чёрный контур — то есть
снимается ровно тот белый, который лежит СНАРУЖИ предмета.

Порог светлоты 236, а не 255: у рисунков генератора фон не идеально белый
(бывает 250-254), и на 255 заливка не пошла бы вовсе.

⚠ Защита от протечки. Если контур предмета разомкнут, заливка утечёт внутрь и
съест рисунок. Поэтому доля снятого считается и печатается: больше 88 % —
подозрение на протечку, файл НЕ переписывается и попадает в отчёт. Правило
дома: печатный материал проверяется глазами, но сперва цифрой.

Запуск:
    python3 tools/prozrachny_fon.py --dir pictures/dorozhka/colour --dry
    python3 tools/prozrachny_fon.py --dir pictures/dorozhka/colour
"""
from __future__ import annotations

import argparse
import os
import struct
import sys
import zlib
from collections import deque
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "logoped_slovar"))
import imgbw  # noqa: E402  — свой читатель PNG, чистый stdlib

LIGHT = 236          # светлее этого — «бумага», заливка по ней идёт
MAX_SHARE = 0.88     # сняли больше — считаем протечкой и файл не трогаем


def write_rgba(path: Path, w: int, h: int, rows: list) -> None:
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(t: bytes, d: bytes) -> bytes:
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)

    png = imgbw._SIG + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def strip_paper(src: Path, dry: bool = False) -> str:
    w, h, rows = imgbw.read_png(src)
    n = len(rows[0]) // w                      # 1 = серый, 3 = RGB
    def px(x: int, y: int):
        r = rows[y]
        if n == 1:
            v = r[x]; return (v, v, v)
        return (r[x * n], r[x * n + 1], r[x * n + 2])

    light = bytearray(w * h)
    for y in range(h):
        for x in range(w):
            r, g, b = px(x, y)
            if min(r, g, b) >= LIGHT:
                light[y * w + x] = 1

    seen = bytearray(w * h)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if light[y * w + x] and not seen[y * w + x]:
                seen[y * w + x] = 1; q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if light[y * w + x] and not seen[y * w + x]:
                seen[y * w + x] = 1; q.append((x, y))
    while q:
        x, y = q.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and light[ny * w + nx] and not seen[ny * w + nx]:
                seen[ny * w + nx] = 1
                q.append((nx, ny))

    cut = sum(seen)
    share = cut / float(w * h)
    if share > MAX_SHARE:
        return f"⚠ {src.name}: снялось бы {share*100:.0f} % — похоже на протечку, не трогаю"
    if dry:
        return f"  {src.name}: снимется {share*100:.0f} % ({cut} пикселей)"

    out = []
    for y in range(h):
        line = bytearray(w * 4)
        for x in range(w):
            r, g, b = px(x, y)
            i = x * 4
            line[i] = r; line[i + 1] = g; line[i + 2] = b
            line[i + 3] = 0 if seen[y * w + x] else 255
        out.append(line)
    write_rgba(src, w, h, out)
    return f"✓ {src.name}: прозрачно {share*100:.0f} %"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="внешний белый фон → прозрачность")
    ap.add_argument("--dir", required=True, help="папка с png")
    ap.add_argument("--dry", action="store_true", help="только посчитать")
    ap.add_argument("--only", default="", help="имена через запятую")
    args = ap.parse_args(argv)

    d = Path(args.dir)
    files = sorted(d.glob("*.png"))
    if args.only:
        want = {s.strip() for s in args.only.split(",") if s.strip()}
        files = [f for f in files if f.stem in want]
    if not files:
        print("нечего обрабатывать", file=sys.stderr); return 1
    bad = 0
    for f in files:
        line = strip_paper(f, args.dry)
        if line.startswith("⚠"):
            bad += 1
        print(line, flush=True)
    print(f"\nвсего файлов: {len(files)} · подозрительных: {bad}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
