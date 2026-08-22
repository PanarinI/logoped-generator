"""Конвейер картинок: заказ рисунков у генератора по словарю промптов.

Зачем файл существует. Корпус из 979 предметных картинок гнали разовым скриптом,
которого нет ни в одном коммите — конвейер жил в памяти сессии, и повторить его
нельзя. Спрайты фона точно будут перерисовываться по глазам автора, поэтому
второй прогон обязан быть однокнопочным. Отсюда правило: заказ идёт ТОЛЬКО этим
файлом, а словарь промптов лежит рядом в репозитории.

Что важно в устройстве:
  · СТИЛЬ не в данных, а здесь. В словаре — только описание предмета; правила
    рисунка (толщина линии, запрет заливки, запрет опоры) одни на весь заказ,
    иначе стиль расползётся по строкам и разойдётся.
  · ТОЛЩИНА ЛИНИИ считается из ПЕЧАТНОГО размера, а не берётся числом. Корпус
    рисовался под 25 мм и просил «2.5 % ширины». Спрайт фона печатается шириной
    10 мм — та же доля дала бы линию втрое тоньше нужной, и сцена пропала бы с
    бумаги. Поэтому доля вычисляется под каждый бокс.
  · ПРОПОРЦИЯ. Модель умеет только 1:1, 2:3 и 3:2. Боксы спрайтов бывают 1:2.8 —
    поэтому берём ближайшую из трёх по форме бокса, а не квадрат всегда: у
    квадрата вытянутый предмет вышел бы мелким внутри пустого поля.
  · ЗАПРЕТ он выполняет хуже, чем задание («на месте Х нарисуй пусто» бьёт
    «не рисуй Х»), и опоры надо запрещать всем семейством сразу — это доказано
    на корпусе, см. DECISIONS 08-18.

Запуск:
    python3 tools/gen_kartinki.py --slovar logoped_slovar/scenes_prompts.json \\
                                  --out pictures/probes/<дата> [--only tree,bath] [--dry]

`--dry` печатает промпты и НЕ тратит деньги. Прогон на 8 предметов стоил 8 центов
(проба 08-17), то есть примерно цент за картинку на `quality: low`.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Tuple

KEY_PATH = os.path.expanduser("~/.config/logoped/openai.key")
API = "https://api.openai.com/v1/images/generations"

# Толщина печатной линии сцены. Ровно та, какой рисует нынешний вектор
# (`scenes.scene_svg`, stroke=0.95): спрайт обязан лечь в один вес с ней,
# иначе растровые предметы будут спорить с векторными поверхностями.
STROKE_MM = 0.95

# Общие правила рисунка. Ч/б блок корпуса, из которого убран цвет: фону заливка
# запрещена жёстче, чем предмету — «серое пятно на дешёвом принтере станет
# грязью» (research/logoped_geroi_fony_2026-08-19.md).
STYLE_BASE = (
    "Black-and-white line drawing for a children's speech-therapy worksheet. "
    "One single object, isolated, canonical recognizable view, pure white background. "
    "BOLD THICK black outline of uniform weight, closed and continuous. "
    "Correct real-life proportions, no cartoon deformation. "
    "No hatching, no shading, no texture fill, no gray tones, no colour. "
    "IMPORTANT: keep every feature that tells this object apart from the object it could be "
    "confused with, and draw those features with the same thick line as the outline - "
    "a thick line must never mean a simplified or emptied object. Drop only ornament. "
    "No text, no numbers, no frame, no shadow, "
    "no ground line, no floor, no base, no platform, no surface under the object: "
    "the drawing fades out unfinished at the bottom edge."
)


def style_for(box_w_mm: float, box_h_mm: float) -> str:
    """Стилевой блок под конкретный печатный размер.

    ⚠ Проценту генератор не подчиняется. Проба 08-22: на просьбу «4-10 % ширины»
    он нарисовал линию 0.32-0.48 мм там, где сцене нужны 0.95 — вдвое-втрое
    тоньше, и на бледном фоне (opacity 0.42) она пропала бы с бумаги. Поэтому
    толщина просится не долей, а ОБРАЗОМ ИНСТРУМЕНТА: «нарисовано толстым
    маркером» модель понимает, «десять процентов ширины» — нет. Доля оставлена
    рядом вторым сигналом, но опираться на неё нельзя.
    """
    pct = STROKE_MM / box_w_mm * 100.0
    return (
        f"{STYLE_BASE} "
        f"CRITICAL - LINE WEIGHT: the whole drawing must look as if it was drawn "
        f"with a BROAD BLACK FELT-TIP MARKER on paper, not with a thin pen. "
        f"Every line, including inner details, is a heavy slab of black about "
        f"{pct:.0f} percent of the image width - deliberately much thicker than "
        f"a normal illustration. Err on the side of far too thick. "
        f"The drawing is printed only {box_w_mm:g} mm wide and {box_h_mm:g} mm tall "
        f"and then faded to 40 percent grey, so a thin line disappears completely."
    )


def size_for(box_w_mm: float, box_h_mm: float) -> str:
    """Ближайшая из трёх пропорций, какие умеет модель."""
    ratio = box_h_mm / box_w_mm
    if ratio >= 1.25:
        return "1024x1536"        # вертикаль
    if ratio <= 0.8:
        return "1536x1024"        # горизонталь
    return "1024x1024"


def build(item: Dict[str, Any]) -> Tuple[str, str]:
    box = item.get("box") or [25, 25]
    return (f"{item['prompt']}\n\n{style_for(float(box[0]), float(box[1]))}",
            size_for(float(box[0]), float(box[1])))


def draw(name: str, item: Dict[str, Any], out_dir: str, key: str) -> str:
    prompt, size = build(item)
    body = json.dumps({"model": "gpt-image-1", "prompt": prompt, "n": 1,
                       "size": size, "quality": "low",
                       "output_format": "png"}).encode("utf-8")
    req = urllib.request.Request(API, data=body, headers={
        "Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            data = json.load(r)
    except Exception as e:                       # один упавший предмет не роняет заказ
        return f"✗ {name}: {type(e).__name__}: {e}"
    path = os.path.join(out_dir, f"{name}.png")
    with open(path, "wb") as fh:
        fh.write(base64.b64decode(data["data"][0]["b64_json"]))
    return f"✓ {name}  {size}  {os.path.getsize(path) // 1024} КБ"


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--slovar", required=True, help="json: имя → {prompt, box}")
    ap.add_argument("--out", required=True, help="куда складывать png")
    ap.add_argument("--only", default="", help="список имён через запятую")
    ap.add_argument("--dry", action="store_true", help="показать промпты, не тратить")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)

    with open(args.slovar, encoding="utf-8") as fh:
        slovar: Dict[str, Dict[str, Any]] = json.load(fh)

    if args.only:
        want = {s.strip() for s in args.only.split(",") if s.strip()}
        missing = want - set(slovar)
        if missing:
            print(f"нет в словаре: {', '.join(sorted(missing))}", file=sys.stderr)
            return 1
        slovar = {k: v for k, v in slovar.items() if k in want}

    if args.dry:
        for name, item in slovar.items():
            prompt, size = build(item)
            print(f"\n═══ {name}  ({size}, бокс {item.get('box')}) ═══\n{prompt}")
        print(f"\nвсего предметов: {len(slovar)} — деньги НЕ потрачены (--dry)")
        return 0

    if not os.path.isfile(KEY_PATH):
        print(f"нет ключа: {KEY_PATH}", file=sys.stderr)
        return 1
    with open(KEY_PATH, encoding="utf-8") as fh:
        key = fh.read().strip()

    os.makedirs(args.out, exist_ok=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for line in pool.map(lambda kv: draw(kv[0], kv[1], args.out, key),
                             slovar.items()):
            print(line, flush=True)

    print(f"\nготово → {args.out}")
    print("⚠ Смотреть глазами в ПЕЧАТНОМ размере до того, как класть в банк: "
          "закон 6 проекта.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
