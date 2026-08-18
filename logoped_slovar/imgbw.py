# -*- coding: utf-8 -*-
"""
imgbw.py — СНЯТЬ ЦВЕТ С КАРТИНКИ, оставив чёрный контур.

Зачем (08-18). Решение автора: рисуем всё в цвете, а ч/б получаем из того же
файла — тогда у каждого слова два полноценных варианта по цене одной генерации.

Но «обесцветить» в лоб НЕЛЬЗЯ, и это проверено глазами в тот же день: перевод
в градации серого превращает заливку в ровное серое пятно, которое глушит
внутренние линии, и такой лист выходит ХУЖЕ нарисованного ч/б.

Работает другое: заливки не гасить, а УБИРАТЬ. Рисунок нашего канона — чёрный
контур плюс плоские цветные заливки, поэтому цвет отделяется от линии не
яркостью, а НАСЫЩЕННОСТЬЮ: контур ахроматичен (R≈G≈B), заливка хроматична.
Тёмно-красный борщ по яркости темнее серого, но по насыщенности — заливка.

Ограничение, которое отсюда следует: у слов, где различение несёт сам цвет
(`colour_critical.json`), после снятия заливок остаётся пустая тарелка. Им
ч/б-версия по-прежнему рисуется отдельно, там различение обязано быть линией.

Чистый stdlib: PNG читается и пишется руками (zlib в стандартной поставке).
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

__all__ = ["strip_colour", "read_png", "write_png_gray"]

_SIG = b"\x89PNG\r\n\x1a\n"


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    return a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)


def read_png(path: Path) -> tuple[int, int, list[bytes]]:
    """→ (ширина, высота, строки RGB по 3 байта на пиксель)."""
    raw = Path(path).read_bytes()
    if raw[:8] != _SIG:
        raise ValueError(f"{path}: не PNG")
    pos, idat, plte, ihdr = 8, [], b"", None
    while pos < len(raw):
        (ln,) = struct.unpack(">I", raw[pos:pos + 4])
        typ = raw[pos + 4:pos + 8]
        data = raw[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            ihdr = struct.unpack(">IIBBBBB", data)
        elif typ == b"PLTE":
            plte = data
        elif typ == b"IDAT":
            idat.append(data)
        elif typ == b"IEND":
            break
        pos += 12 + ln
    if ihdr is None:
        raise ValueError(f"{path}: нет IHDR")
    w, h, depth, ctype, _comp, _filt, interlace = ihdr
    if depth != 8 or interlace:
        raise ValueError(f"{path}: поддержан только 8 бит без интерлейса (depth={depth})")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ctype]
    stride = w * channels
    data = zlib.decompress(b"".join(idat))

    rows, prev = [], bytearray(stride)
    p = 0
    for _ in range(h):
        ft = data[p]; p += 1
        line = bytearray(data[p:p + stride]); p += stride
        if ft == 1:
            for i in range(channels, stride):
                line[i] = (line[i] + line[i - channels]) & 0xFF
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ft == 3:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                line[i] = (line[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ft == 4:
            for i in range(stride):
                a = line[i - channels] if i >= channels else 0
                c = prev[i - channels] if i >= channels else 0
                line[i] = (line[i] + _paeth(a, prev[i], c)) & 0xFF
        elif ft != 0:
            raise ValueError(f"{path}: неизвестный фильтр строки {ft}")
        prev = line

        # Прозрачное кладём НА БЕЛОЕ: под альфой у генератора лежит чёрный RGB,
        # и без композита прозрачный фон читался бы как сплошная линия (08-18).
        if ctype == 2:
            rows.append(bytes(line))
        elif ctype == 6:
            px = bytearray(w * 3)
            for i in range(w):
                a = line[i * 4 + 3]
                for k in range(3):
                    v = line[i * 4 + k]
                    px[i * 3 + k] = v if a == 255 else (v * a + 255 * (255 - a)) // 255
            rows.append(bytes(px))
        elif ctype == 0:
            rows.append(bytes(b for v in line for b in (v, v, v)))
        elif ctype == 4:
            px = bytearray(w * 3)
            for i in range(w):
                v, a = line[i * 2], line[i * 2 + 1]
                g = v if a == 255 else (v * a + 255 * (255 - a)) // 255
                px[i * 3:i * 3 + 3] = bytes((g, g, g))
            rows.append(bytes(px))
        else:  # палитра
            rows.append(bytes(b for v in line for b in plte[v * 3:v * 3 + 3]))
    return w, h, rows


def write_png_gray(path: Path, w: int, h: int, rows: list[bytes]) -> None:
    """Записать 8-битный серый PNG (по байту на пиксель, фильтр 0)."""
    body = b"".join(b"\x00" + r for r in rows)
    def chunk(typ: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))
    Path(path).write_bytes(
        _SIG
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(body, 9))
        + chunk(b"IEND", b""))


def strip_colour(src: Path, dst: Path, *, sat: int = 28, dark: int = 128) -> dict:
    """Снять заливки, оставив чёрную линию. → счётчик, что куда ушло.

    sat  — от какой насыщенности (max-min канала) пиксель считается ЗАЛИВКОЙ;
    dark — ниже какой яркости ахроматический пиксель считается ЛИНИЕЙ.
    """
    w, h, rows = read_png(src)
    out, stat = [], {"line": 0, "fill": 0, "paper": 0}
    for row in rows:
        line = bytearray(w)
        for x in range(w):
            r, g, b = row[x * 3], row[x * 3 + 1], row[x * 3 + 2]
            hi, lo = max(r, g, b), min(r, g, b)
            if hi - lo >= sat:                 # цветное — это заливка, убираем
                line[x] = 255; stat["fill"] += 1
            elif lo < dark:                    # серо-чёрное и тёмное — это линия
                line[x] = 0; stat["line"] += 1
            else:
                line[x] = 255; stat["paper"] += 1
        out.append(bytes(line))
    write_png_gray(dst, w, h, out)
    return stat


if __name__ == "__main__":
    import sys
    print(strip_colour(Path(sys.argv[1]), Path(sys.argv[2])))
