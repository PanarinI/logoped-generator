"""Механический пунктир: режем НАРИСОВАННУЮ линию, не заказывая вторую картинку.

Идея опирается на форму: спираль — это концентрические витки вокруг центра.
Значит достаточно стирать белым по дугам равной длины: разрывы ложатся поперёк
витка сами собой, и на любом радиусе выходят одинаковыми по бумаге.

Что НЕ трогаем. Герой, награда и мелочь по углам тоже имеют чёрный контур.
Различаем не по месту, а по соседству: у контура рисунка рядом ЕСТЬ цвет,
у линии спирали цвета рядом нет — она чёрная на белой бумаге.
"""
import sys, math, pathlib, zlib, struct
sys.path.insert(0, 'logoped_slovar')
import imgbw

DARK = 110      # ниже этой яркости пиксель считаем чернилами
SAT  = 40       # выше этой насыщенности пиксель считаем цветным
NEAR = 14       # на сколько пикселей смотрим вокруг в поисках цвета
DASH = 46.0     # шаг «штрих + пробел» в пикселях дуги
GAP  = 17.0     # длина пробела

def write_rgb(path, w, h, rows):
    raw = b"".join(b"\x00" + bytes(r) for r in rows)
    def chunk(t, d):
        c = t + d
        return struct.pack(">I", len(d)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    path.write_bytes(b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))

def dash(src, dst):
    w, h, rows = imgbw.read_png(src)
    rows = [bytearray(r) for r in rows]
    colour = [bytearray(w) for _ in range(h)]
    ink    = [bytearray(w) for _ in range(h)]
    for y in range(h):
        r_ = rows[y]
        for x in range(w):
            R, G, B = r_[x*3], r_[x*3+1], r_[x*3+2]
            hi, lo = max(R, G, B), min(R, G, B)
            if hi - lo >= SAT: colour[y][x] = 1
            elif hi < DARK:    ink[y][x] = 1
    # «есть ли цвет поблизости» — быстрым двухпроходным расширением по столбцам/строкам
    near = [bytearray(w) for _ in range(h)]
    for y in range(h):
        run = -10**9
        for x in range(w):
            if colour[y][x]: run = x
            if x - run <= NEAR: near[y][x] = 1
        run = 10**9
        for x in range(w-1, -1, -1):
            if colour[y][x]: run = x
            if run - x <= NEAR: near[y][x] = 1
    for x in range(w):
        run = -10**9
        for y in range(h):
            if near[y][x] and colour[y][x]: run = y
            if y - run <= NEAR: near[y][x] = 1
        run = 10**9
        for y in range(h-1, -1, -1):
            if colour[y][x]: run = y
            if run - y <= NEAR: near[y][x] = 1
    # центр спирали — центр тяжести «чистых» чернил
    sx = sy = n = 0
    for y in range(h):
        for x in range(w):
            if ink[y][x] and not near[y][x]: sx += x; sy += y; n += 1
    if not n: raise SystemExit('линии не нашёл')
    cx, cy = sx / n, sy / n
    cut = 0
    for y in range(h):
        r_ = rows[y]
        for x in range(w):
            if not ink[y][x] or near[y][x]: continue
            dx, dy = x - cx, y - cy
            rad = math.hypot(dx, dy)
            if rad < 8: continue
            s = (math.atan2(dy, dx) + math.pi) * rad     # длина дуги
            if s % DASH < GAP:
                r_[x*3] = r_[x*3+1] = r_[x*3+2] = 255
                cut += 1
    write_rgb(dst, w, h, rows)
    return {'чернил вырезано': cut, 'центр': (round(cx), round(cy))}

if __name__ == '__main__':
    print(dash(pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])))
