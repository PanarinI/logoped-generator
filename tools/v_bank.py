# -*- coding: utf-8 -*-
"""v_bank.py — разложить принятые пробы генератора по банку картинок.

Зачем файл. До 11-23 этот шаг жил ручными командами: корпус 979 предметов
раскладывали разовым скриптом, которого нет в коммитах, а героев 09-20 —
командами в сессии (порядок записан только словами в `geroi_lista_prompts.json`).
Повторить его без памяти сессии было нельзя. Здесь тот же путь одной командой.

Что делает — три рода картинок, у каждого свой формат банка (замерено по файлам):

  predmety  ПРЕДМЕТ ДЛЯ КЛЕТКИ ЛАБИРИНТА
            цвет  → pictures/objects_colour/<имя>.png   512×512, RGB без альфы
                    pictures/objects_colour/small/…      295×295 (клетка 25 мм при 300 dpi)
            ч/б   → pictures/objects/<имя>.png          512×512, серый — снят с цвета
                    pictures/objects/small/…             295×295
  geroi     ГЕРОЙ БЛОКА [2] ЛИСТА
            цвет  → pictures/geroi/<имя>.png             как пришёл (1536×1024), внешний фон прозрачен
            ч/б   → pictures/geroi_bw/<имя>.png          снят с цвета, внешний фон прозрачен
  dorozhka  ВИД ГЕРОЯ И ЦЕЛЬ ЗВУКОВОЙ ДОРОЖКИ
            цвет  → pictures/dorozhka/colour/<имя>.png   как пришёл, внешний фон прозрачен
            ч/б   → pictures/dorozhka/bw/<имя>.png       снят с цвета, внешний фон прозрачен

Правила, на которых стоит (CLAUDE.md, законы 13 и 6):
  · ч/б только снимается с цвета (`imgbw.strip_colour`), обратно — нельзя;
  · внешний белый фон прозрачен у ВСЕГО, что ложится на дорожку (`tools/prozrachny_fon.py`,
    08-26: «спрайт своим белым фоном заслоняет дорожку») — и у цвета, и у ч/б;
  · существующий файл банка не перезаписывается без `--force`: перезаказ кладётся
    рядом в пробах, а в банк — по слову того, кто смотрел глазами.

Запуск:
    python3 tools/v_bank.py predmety pictures/probes/<дата>/objects чайник мяч
    python3 tools/v_bank.py geroi    pictures/probes/<дата>/geroi паровозик
    python3 tools/v_bank.py dorozhka pictures/probes/<дата>/vidy parovoz_1 parovoz_vagon
"""
from __future__ import annotations

import argparse
import os
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "logoped_slovar"))
sys.path.insert(0, str(ROOT / "tools"))
import imgbw            # noqa: E402
import prozrachny_fon   # noqa: E402

PIC = ROOT / "pictures"
OBJ_SIZE, OBJ_SMALL = 512, 295


def _write_rgb(path: Path, w: int, h: int, rows) -> None:
    raw = b"".join(b"\x00" + bytes(r) for r in rows)

    def chunk(t: bytes, d: bytes) -> bytes:
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)

    png = imgbw._SIG + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b"")
    path.write_bytes(png)


def _resize(src: Path, dst: Path, size: int) -> None:
    """Квадрат `size`×`size` штатным `sips` macOS (как раскладывался корпус)."""
    subprocess.run(["sips", "-z", str(size), str(size), str(src), "--out", str(dst)],
                   check=True, capture_output=True)


def _flatten_rgb(path: Path) -> None:
    """RGB без альфы: прозрачное — на белое (так лежит весь корпус)."""
    w, h, rows = imgbw.read_png(path)          # read_png сам кладёт альфу на белое
    _write_rgb(path, w, h, rows)


def _guard(dst: Path, force: bool) -> bool:
    if dst.exists() and not force:
        print(f"  ⚠ {dst.relative_to(ROOT)} уже есть — пропуск (перезапись только с --force)")
        return False
    return True


def predmety(src_dir: Path, names, force: bool) -> None:
    for n in names:
        src = src_dir / f"{n}.png"
        col, bw = PIC / "objects_colour" / f"{n}.png", PIC / "objects" / f"{n}.png"
        if not _guard(col, force) or not _guard(bw, force):
            continue
        _resize(src, col, OBJ_SIZE)
        _flatten_rgb(col)
        imgbw.strip_colour(col, bw)
        _resize(col, PIC / "objects_colour" / "small" / f"{n}.png", OBJ_SMALL)
        _resize(bw, PIC / "objects" / "small" / f"{n}.png", OBJ_SMALL)
        print(f"  ✓ {n}: цвет и ч/б 512 + клетка 295")


def _two_banks(src_dir: Path, names, col_dir: Path, bw_dir: Path, force: bool) -> None:
    for n in names:
        src = src_dir / f"{n}.png"
        col, bw = col_dir / f"{n}.png", bw_dir / f"{n}.png"
        if not _guard(col, force) or not _guard(bw, force):
            continue
        shutil.copyfile(src, col)
        imgbw.strip_colour(col, bw)            # ч/б — с цвета, пока фон ещё белый
        for f in (col, bw):
            print("  " + prozrachny_fon.strip_paper(f))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="разложить пробы по банку картинок")
    ap.add_argument("kind", choices=("predmety", "geroi", "dorozhka"))
    ap.add_argument("src", help="папка проб с <имя>.png")
    ap.add_argument("names", nargs="+")
    ap.add_argument("--force", action="store_true", help="перезаписать файл банка")
    a = ap.parse_args(argv)
    src = Path(a.src)
    missing = [n for n in a.names if not (src / f"{n}.png").exists()]
    if missing:
        print("нет в пробах:", ", ".join(missing), file=sys.stderr)
        return 1
    if a.kind == "predmety":
        predmety(src, a.names, a.force)
    elif a.kind == "geroi":
        _two_banks(src, a.names, PIC / "geroi", PIC / "geroi_bw", a.force)
    else:
        _two_banks(src, a.names, PIC / "dorozhka" / "colour", PIC / "dorozhka" / "bw", a.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
