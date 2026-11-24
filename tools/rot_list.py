#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Все позы схемы рта на одном листе — чтобы сверить глазами с описаниями (закон 6).

Запуск:  python3 -I tools/rot_list.py <папка>   → <папка>/rot_list.svg и .png (через qlmanage)
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "web"))
import rot  # noqa: E402

out = sys.argv[1] if len(sys.argv) > 1 else "."
only = sys.argv[2].split(",") if len(sys.argv) > 2 else None
names = [n for n in rot.POZY if not only or n in only]
per, cell = 4, 220
rows = (len(names) + per - 1) // per
parts = []
for i, n in enumerate(names):
    x, y = (i % per) * cell, (i // per) * (cell + 24)
    parts.append(f'<g transform="translate({x},{y})"><svg x="10" y="0" width="200" height="200" viewBox="{rot.VIEWBOX}">'
                 f'{rot.FACE}<g>{rot.POZY[n]()}</g></svg>'
                 f'<text x="110" y="214" font-family="Helvetica" font-size="15" text-anchor="middle">{n}</text></g>')
w, h = per * cell, rows * (cell + 24)
svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
       f'<rect width="100%" height="100%" fill="#fff"/>{"".join(parts)}</svg>')
path = os.path.join(out, (sys.argv[3] if len(sys.argv) > 3 else "rot_list") + ".svg")
open(path, "w", encoding="utf-8").write(svg)
subprocess.run(["qlmanage", "-t", "-s", str(w), "-o", out, path], capture_output=True)
print(path, "+ png:", os.path.exists(path + ".png"))
