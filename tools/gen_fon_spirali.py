# -*- coding: utf-8 -*-
"""
gen_fon_spirali.py — ЗАКАЗ ФОНА ДЛЯ ЛИСТА-СПИРАЛИ, герой идёт РЕФЕРЕНСОМ.

Зачем отдельный инструмент, а не `gen_kartinki.py`. Тот заказывает ПРЕДМЕТ по
одному тексту (`/v1/images/generations`) — и этого хватает, пока предмет один и
стиль задан словами. Фон устроен иначе: он обязан сесть с уже нарисованным
героем в ОДИН ПОЧЕРК — та же толщина линии, та же манера, та же палитра. Словами
это не берётся (проверено на самих героях: «bold thick black outline» модель
исполняла по-своему у каждого предмета). Берётся картинкой: цветной герой этого
мира уходит в запрос РЕФЕРЕНСОМ через `/v1/images/edits`, и фон рисуется от него.

Слово автора 2026-08-26: «не надо заполнять мир элементами — нарисуй фон, да
даже вместе с героем, возьми героя за референс и сделай из этого классно».
Герой в САМ фон не рисуется, и это не спор с автором, а сохранение того, что уже
выиграно: герой и цель живут в банке — три вида на звук, одушевлённые, цель по
виду. Вшитый в фон герой вернул бы ровно те беды, из-за которых рисованные
спирали и разбирались. Поэтому фон — только МИР.

Правило дома соблюдено: рисуем ЦВЕТНОЕ, ч/б снимается технически
(`imgbw.strip_colour`), обратно нельзя.

Запуск:
    python3 tools/gen_fon_spirali.py --dry            # показать промпты, не тратить
    python3 tools/gen_fon_spirali.py --only fon_nebo  # заказать один, на пробу
    python3 tools/gen_fon_spirali.py                  # заказать все
Готовое кладётся в `pictures/probes/` — в банк переносит человек, посмотрев
глазами (локальный закон: визуальный приём проверяют картинками).
"""
from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SLOVAR = os.path.join(ROOT, "logoped_slovar", "fony_spirali_prompts.json")
GEROI = os.path.join(ROOT, "pictures", "dorozhka", "colour")
OUT = os.path.join(ROOT, "pictures", "probes")
KEY_PATH = os.path.expanduser("~/.config/logoped/openai.key")
API = "https://api.openai.com/v1/images/edits"

# Середина листа должна остаться пустой — туда ложится спираль. Модель ошибается
# здесь чаще всего, поэтому требование стоит трижды и разными словами.
STYLE = (
    "Draw a BACKGROUND for a printable children's speech-therapy worksheet page, "
    "portrait orientation. "
    "THE PAGE IS WHITE PAPER. The paper stays pure white EVERYWHERE — behind the "
    "objects, between them, and across the whole middle of the page. "
    "DO NOT fill the page or its edges with any colour. DO NOT draw a coloured "
    "band, a strip, a frame, a border or a rounded white panel in the middle: "
    "there is no frame of any kind on this page. "
    "Instead draw only A FEW SEPARATE SMALL OBJECTS, standing apart from each "
    "other near the outer edges and in the corners of the page, with plenty of "
    "empty white paper between them. Six to nine small objects on the whole page, "
    "no more. "
    "THE ENTIRE MIDDLE OF THE PAGE MUST STAY COMPLETELY EMPTY: a large drawing "
    "will be placed there afterwards. Nothing at all in the central area. "
    "THE OBJECTS: {world}. "
    "STYLE — copy it from the reference picture, exactly: the same bold thick "
    "black outline of even weight, the same flat solid colour fills with one even "
    "tone per area, the same simple friendly children's-book manner, the same "
    "palette. Each object is a small separate drawing with a black outline on "
    "white paper. No gradients, no shading, no highlights, no texture. "
    "DO NOT DRAW THE OBJECT FROM THE REFERENCE PICTURE. The reference is given "
    "only to show the drawing style. No characters, no vehicles, no animals with "
    "faces, no eyes, no people. "
    "THERE MUST BE NO LETTERS, WORDS, LABELS OR WRITING ANYWHERE — not on "
    "the page and not on any object; a soap bar, a box or a sign carries no "
    "text at all. No numbers, no shadow, no ground line running across the page. "
    "The objects must be calm, light and sparse — a quiet edge to the page, not "
    "its subject. Again: white paper everywhere, no frame, empty middle."
)


def multipart(fields: dict, files: list) -> tuple:
    """Тело multipart/form-data руками: ставить зависимость ради одной формы
    незачем — так же собран заказ PDF в `web/server.py`."""
    boundary = "----logofon-" + uuid.uuid4().hex[:16]
    parts: list = []
    for name, value in fields.items():
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"'
            f"\r\n\r\n{value}\r\n".encode("utf-8"))
    for name, path in files:
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as fh:
            blob = fh.read()
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
            f'filename="{os.path.basename(path)}"\r\n'
            f"Content-Type: {ctype}\r\n\r\n".encode("utf-8") + blob + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    return b"".join(parts), boundary


def order(name: str, item: dict, key: str) -> str:
    hero = os.path.join(GEROI, item["hero"] + ".png")
    if not os.path.isfile(hero):
        return f"✗ {name}: нет героя-референса {hero}"
    prompt = STYLE.format(world=item["world"])
    body, boundary = multipart(
        {"model": "gpt-image-1", "prompt": prompt, "n": "1",
         "size": "1024x1024", "quality": "medium", "output_format": "png"},
        [("image[]", hero)])
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            data = json.load(r)
    except Exception as exc:                     # один упавший фон не роняет заказ
        detail = ""
        if hasattr(exc, "read"):
            try:
                detail = " · " + exc.read().decode("utf-8", "replace")[:300]
            except Exception:
                pass
        return f"✗ {name}: {type(exc).__name__}: {exc}{detail}"
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, f"{name}.png")
    with open(path, "wb") as fh:
        fh.write(base64.b64decode(data["data"][0]["b64_json"]))
    return f"✓ {name}  референс {item['hero']}  {os.path.getsize(path) // 1024} КБ"


def main(argv: list | None = None) -> int:
    ap = argparse.ArgumentParser(description="фоны листа-спирали, герой референсом")
    ap.add_argument("--only", default="", help="имена через запятую")
    ap.add_argument("--dry", action="store_true", help="показать промпты, не тратить")
    args = ap.parse_args(argv)

    with open(SLOVAR, encoding="utf-8") as fh:
        slovar = json.load(fh)
    slovar = {k: v for k, v in slovar.items()
              if not k.startswith("_") and isinstance(v, dict)}
    if args.only:
        want = {s.strip() for s in args.only.split(",") if s.strip()}
        missing = want - set(slovar)
        if missing:
            print("нет в словаре: " + ", ".join(sorted(missing)), file=sys.stderr)
            return 1
        slovar = {k: v for k, v in slovar.items() if k in want}

    if args.dry:
        for name, item in slovar.items():
            print(f"\n═══ {name}  (референс {item['hero']}) ═══\n"
                  + STYLE.format(world=item["world"]))
        print(f"\nвсего фонов: {len(slovar)} — деньги НЕ потрачены (--dry)")
        return 0

    if not os.path.isfile(KEY_PATH):
        print(f"нет ключа: {KEY_PATH}", file=sys.stderr)
        return 1
    with open(KEY_PATH, encoding="utf-8") as fh:
        key = fh.read().strip()

    for name, item in slovar.items():
        print(order(name, item, key), flush=True)
    print(f"\nготовое лежит в {OUT} — в банк переносит человек, посмотрев глазами")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
