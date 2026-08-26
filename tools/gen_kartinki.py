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
    # ⚠ 08-25, ДВЕ НЕУДАЧНЫЕ ПРАВКИ ПОДРЯД — записаны, чтобы не повторять.
    # На пробе грузовик и гараж получили опору (тень и чёрную полосу земли).
    # Я дописал сюда абзац «CRITICAL - ничего ниже предмета»:
    #   1) с перечнем «не линия, не размывка, не серое пятно» — гараж пришёл
    #      НА СЕРОМ ФОНЕ ЦЕЛИКОМ: перечисляя, мы называем, а названное рисуется;
    #   2) чисто утвердительно, «бумага внизу как в верхних углах» — серый фон
    #      остался. Слова «floats», «cut out» тянут за собой рендер с подложкой.
    # Обе правки ДОБАВЛЯЛИ сущность, и обе сделали хуже исходного — это закон 4
    # проекта. Блок вернулся к прежнему виду.
    # Опора здесь лечится не промптом, а отбором: бракованное уходит
    # в `pictures/otkloneno/` и перезаказывается. Так собран весь корпус 979.
)

# ЦВЕТНОЙ БЛОК. Правило дома, забытое мной 08-25 и напомненное автором:
# **рисуем ЦВЕТНОЕ, ч/б снимаем технически. Обратно — нельзя.**
# Так собран весь корпус: 979 цветных предметов и цветные герои, а `objects/`
# и `geroi_bw/` сняты с них `imgbw.strip_colour`. Два варианта по цене одной
# генерации; заказать ч/б значит закрыть цветную ветку навсегда.
#
# ⚡ ЧЕМ ЭТО СВЯЗЫВАЕТ РИСУНОК. `strip_colour` убирает пиксель, у которого
# насыщенность (max-min канала) ≥ 28, и оставляет тёмный ахроматический. То есть
# ч/б-версия — это ровно ЧЁРНЫЙ КОНТУР рисунка. Отсюда два жёстких требования,
# и оба идут в промпт заданием, а не запретом:
#   · контур ЧЁРНЫЙ. Цветной контур снимется вместе с заливкой, и в ч/б
#     останется пустая бумага;
#   · заливка ПЛОСКАЯ. Градиент и мягкая тень частью переживут порог и лягут
#     грязью — в цвете этого не видно, в ч/б видно сразу.
# ⚠ Здесь стояло сравнение «как детская НАКЛЕЙКА» — и гараж пришёл наклейкой:
# коричневый градиентный фон и падающая тень под ней. Сравнение назвало модели
# предмет, лежащий НА ПОВЕРХНОСТИ, и поверхность нарисовалась. Убрано вычитанием,
# а не новым абзацем (закон 4). Показательно: ч/б, снятый с той же картинки,
# вышел чистым — `strip_colour` снёс и фон, и тень вместе с заливкой.
STYLE_BASE_COLOUR = (
    "Colour line drawing for a children's speech-therapy worksheet. "
    "One single object, isolated, canonical recognizable view, pure white background. "
    "CRITICAL - HOW IT IS COLOURED: the whole drawing is built from a BOLD THICK BLACK "
    "outline of uniform weight, closed and continuous, and the areas inside that black "
    "outline are filled with FLAT SOLID COLOUR, one even tone per area, the way a clean "
    "printed worksheet is coloured. Every line in the drawing - the outline and every "
    "inner detail line - is BLACK, never coloured. The colours are bright, simple and "
    "true to life. Each area is one single flat tone from edge to edge, with the black "
    "line separating it from the next area. "
    "Correct real-life proportions, no cartoon deformation. "
    "No gradients, no airbrush, no soft shading, no highlights, no textures. "
    "IMPORTANT: keep every feature that tells this object apart from the object it could be "
    "confused with, and draw those features with the same thick black line as the outline - "
    "a thick line must never mean a simplified or emptied object. Drop only ornament. "
    "No text, no numbers, no frame, no shadow, "
    "no ground line, no floor, no base, no platform, no surface under the object: "
    "the drawing fades out unfinished at the bottom edge."
)


def style_for(box_w_mm: float, box_h_mm: float, faded: bool = True,
              colour: bool = False) -> str:
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
        f"{STYLE_BASE_COLOUR if colour else STYLE_BASE} "
        f"CRITICAL - LINE WEIGHT: the whole drawing must look as if it was drawn "
        f"with a BROAD BLACK FELT-TIP MARKER on paper, not with a thin pen. "
        f"Every line, including inner details, is a heavy slab of black about "
        f"{pct:.0f} percent of the image width - deliberately much thicker than "
        f"a normal illustration. Err on the side of far too thick. "
        f"The drawing is printed only {box_w_mm:g} mm wide and {box_h_mm:g} mm tall "
        + (f"and then faded to 40 percent grey, so a thin line disappears completely."
           if faded else
           f"at full black, so a thin line disappears completely.")
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
    """Промпт + размер.

    Два необязательных ключа, оба со значением по умолчанию «как было», чтобы
    старые словари (`scenes_prompts.json`) не изменились ни на символ:

    · `faded` — приглушается ли рисунок на бумаге. Спрайты фона приглушаются, и
      промпт честно этим объясняет, зачем линия толстая. ГЕРОЙ И ЦЕЛЬ звуковой
      дорожки печатаются в полный вес: просить модель рисовать под выцветание,
      которого не будет, — значит получить лишнюю жирность (08-25).
    · `colour` — рисуем В ЦВЕТЕ, а ч/б снимается технически (`strip_colour`).
      Умолчание False, чтобы спрайты фона остались ч/б, как были: они печатаются
      приглушёнными, заливка им запрещена жёстче, чем предмету.
    · `raw` — рисунок сам себе стиль. Стилевой блок написан под ПРЕДМЕТ в
      боксе 10-26 мм: «один предмет, изолированно», «толстым маркером». Для
      ЦЕЛОГО ЛИСТА (спираль-улитка, 148x210 мм) он врёт в обоих словах, и лист
      несёт свой стиль внутри промпта.
    """
    box = item.get("box") or [25, 25]
    if item.get("raw"):
        return (item["prompt"], size_for(float(box[0]), float(box[1])))
    # ЦВЕТ ПРЕДМЕТА — из словаря, а не из головы модели. Пришивается ПОСЛЕ
    # стилевого блока и до него не относится: стиль говорит, КАК красить
    # (плоско, чёрный контур), таблица — ЧЕМ. Первый цветной прогон 08-26 без
    # этой строки дал 63% банка в жёлто-оранжевом и четыре неверных предмета.
    style = style_for(float(box[0]), float(box[1]),
                      bool(item.get("faded", True)),
                      bool(item.get("colour", False)))
    hint = str(item.get("colour_hint") or "").strip()
    if hint and item.get("colour"):
        style += (" COLOURS OF THIS OBJECT, use exactly these and no others: "
                  + hint + ".")
    return (f"{item['prompt']}\n\n{style}",
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
    # ⚠ 08-26. Словари несут служебные ключи с подчёркивания — почему словарь
    # такой и по какому правилу собран. Конвейер брал их за предметы и падал
    # посреди заказа («'list' object has no attribute 'get'»), уже потратив
    # деньги на часть картинок. Комментарий в данных законен, падать на нём —
    # нет.
    slovar = {k: v for k, v in slovar.items()
              if not k.startswith("_") and isinstance(v, dict)}

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
