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


# ═══════════════════════════════════════════════════════════════════════
#  ДОВОДКА ЛИНИИ: наращивание штриха до печатной толщины
# ═══════════════════════════════════════════════════════════════════════
#
# Зачем. Сцена слоговой дорожки печатается линией 0.95 мм и бледно (opacity
# 0.42). Спрайт для неё рисует генератор — и толщину линии он НЕ СЛУШАЕТСЯ:
# проба 08-22 показала 0.32-0.48 мм на просьбу «столько-то процентов ширины»,
# и 0.58-0.67 мм после втрое более настойчивой формулировки («широким чёрным
# маркером, ошибись в сторону слишком толстого»). До нужного не дошёл ни разу.
#
# Поэтому толщина не выпрашивается, а доводится здесь — это тот же локальный
# закон 7 проекта: правило врёт, таблица работает. Меряем и правим механически.


def _gray(w: int, rows: list[bytes]) -> list[bytearray]:
    """Свести любые каналы к одному байту на пиксель."""
    n = len(rows[0]) // w
    if n == 1:
        return [bytearray(r) for r in rows]
    out = []
    for r in rows:
        out.append(bytearray((r[x * n] + r[x * n + 1] + r[x * n + 2]) // 3
                             for x in range(w)))
    return out


def _dark_mask(g: list[bytearray], thr: int) -> list[bytearray]:
    return [bytearray(1 if v < thr else 0 for v in row) for row in g]


def stroke_px(mask: list[bytearray]) -> float:
    """Медиана длины тёмного отрезка в строке — оценка толщины штриха.

    Медиана, а не среднее: у рисунка есть и длинные заливки-пересечения, и
    короткие хвосты, и среднее по ним ничего не говорит о линии.
    """
    runs: list[int] = []
    for row in mask:
        cur = 0
        for v in row:
            if v:
                cur += 1
            elif cur:
                runs.append(cur)
                cur = 0
        if cur:
            runs.append(cur)
    if not runs:
        return 0.0
    runs.sort()
    return float(runs[len(runs) // 2])


def ink_box(mask: list[bytearray]) -> tuple[int, int, int, int]:
    """Границы чернил: x0, y0, x1, y1. Пустая картинка → нули."""
    h = len(mask)
    w = len(mask[0]) if h else 0
    x0, y0, x1, y1 = w, h, -1, -1
    for y, row in enumerate(mask):
        if 1 not in row:
            continue
        y0 = min(y0, y)
        y1 = max(y1, y)
        x0 = min(x0, row.index(1))
        # последний тёмный в строке
        for x in range(len(row) - 1, -1, -1):
            if row[x]:
                x1 = max(x1, x)
                break
    if x1 < 0:
        return 0, 0, 0, 0
    return x0, y0, x1, y1


def _grow(mask: list[bytearray], r: int) -> list[bytearray]:
    """Нарастить тёмное на r пикселей. Раздельно по осям — так быстрее.

    Раздельная дилатация квадратом даёт тот же результат, что один проход
    квадратным окном, но за два линейных прохода вместо квадратичного.
    """
    h = len(mask)
    w = len(mask[0]) if h else 0
    # горизонталь скользящим счётчиком
    tmp = []
    for row in mask:
        acc = 0
        out = bytearray(w)
        # префиксные суммы дешевле пересчёта окна
        pref = [0] * (w + 1)
        for x in range(w):
            pref[x + 1] = pref[x] + row[x]
        for x in range(w):
            a = max(0, x - r)
            b = min(w, x + r + 1)
            out[x] = 1 if pref[b] - pref[a] else 0
        tmp.append(out)
    # вертикаль тем же приёмом по столбцам
    col_pref = [[0] * (h + 1) for _ in range(w)]
    for y in range(h):
        rowy = tmp[y]
        for x in range(w):
            col_pref[x][y + 1] = col_pref[x][y] + rowy[x]
    out_rows = []
    for y in range(h):
        out = bytearray(w)
        a = max(0, y - r)
        b = min(h, y + r + 1)
        for x in range(w):
            out[x] = 1 if col_pref[x][b] - col_pref[x][a] else 0
        out_rows.append(out)
    return out_rows


def thicken(src: Path, dst: Path, *, box_w_mm: float, target_mm: float = 0.95,
            thr: int = 200, max_grow: int = 60) -> dict:
    """Нарастить линию так, чтобы на бумаге она вышла нужной толщины.

    `box_w_mm` — ширина, которой картинка будет напечатана. Именно она, а не
    размер файла, задаёт цену пикселя: наращивать надо до печатной толщины,
    а не до красивого числа в пикселях.

    Возвращает замер до и после — чтобы результат был проверяем, а не на веру.
    """
    w, h, rows = read_png(Path(src))
    g = _gray(w, rows)
    mask = _dark_mask(g, thr)

    x0, y0, x1, y1 = ink_box(mask)
    ink_w = max(1, x1 - x0 + 1)
    mm_per_px = box_w_mm / ink_w

    was_px = stroke_px(mask)
    was_mm = was_px * mm_per_px
    need_px = target_mm / mm_per_px

    # ⚠ Формула «наращивание на r прибавляет 2r» НЕВЕРНА, и это проверено:
    # 08-22 она дала 1.45 · 2.55 · 1.10 мм при цели 0.95. Причина в том, что
    # наращивание не только утолщает штрих, но и СЛИВАЕТ соседние линии — у
    # ванны с частой решёткой крана промах был восьмикратным.
    # Поэтому формула служит только верхней границей, а величину подбираем
    # ЗАМЕРОМ: наименьшее наращивание, при котором штрих дошёл до цели.
    hi = max(0, min(max_grow, round((need_px - was_px) / 2) + 2))
    best, best_mask, best_px = 0, mask, was_px
    lo = 0
    while lo <= hi:
        mid = (lo + hi) // 2
        cand = _grow(mask, mid) if mid else mask
        px = stroke_px(cand)
        if px >= need_px:
            best, best_mask, best_px = mid, cand, px
            hi = mid - 1
        else:
            lo = mid + 1
            if mid >= best:
                best, best_mask, best_px = mid, cand, px

    grow, mask, now_px = best, best_mask, best_px
    out = [bytearray(0 if v else 255 for v in row) for row in mask]
    write_png_gray(Path(dst), w, h, [bytes(r) for r in out])

    return {
        "grow_px": grow,
        "mm_per_px": round(mm_per_px, 5),
        "stroke_was_mm": round(was_mm, 2),
        "stroke_now_mm": round(now_px * mm_per_px, 2),
        "target_mm": target_mm,
        "ink": (ink_w, y1 - y0 + 1),
    }


if __name__ == "__main__":
    import sys
    print(strip_colour(Path(sys.argv[1]), Path(sys.argv[2])))
