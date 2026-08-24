"""Снимки настоящих листов для иллюстраций сайта.

Зачем. Канон Site Builders называет картинку ФУНДАМЕНТОМ статьи, а не
украшением, и требует минимум три иллюстрации на страницу — крупные скриншоты
реального результата, а не абстракции. Рисовать их руками бессмысленно: лист
собирает движок, и снимок обязан быть снимком того же листа, который получит
логопед. Отсюда инструмент: он просит у живого сервера материалы и снимает их
headless-браузером ровно так, как они уйдут на печать.

Как устроено и почему так:
  · материал берётся у ЗАПУЩЕННОГО сервера через `/api/*` — это тот же путь,
    которым его получает логопед, значит снимок не может разойтись с бумагой;
  · ответ движка — самодостаточный HTML со встроенными стилями и `@page A4`;
  · картинки героя вшиваются в файл как data:-URI. Без этого Chrome, открывая
    файл с `file://`, не пускает запрос на `http://localhost` и герой выходит
    битым квадратом (поймано 08-22 глазами на первом же снимке);
  · снимок делается в размер листа A4 при 96 dpi с двойной плотностью пикселя,
    затем уменьшается до 1200 px по длинной стороне — это вес, который не жалко
    отдать со страницы.

Запуск (сервер должен быть поднят):
    python3 tools/snimki_listov.py --base http://localhost:8784 --out web/img
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.request
from typing import Any, Dict, List, Tuple

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Что снимаем. Набор покрывает страницы карты сайта: главная и категория Р
# показывают лист, доки — свой материал каждая.
JOBS: Tuple[Tuple[str, str, Dict[str, Any]], ...] = (
    ("list-r",        "/api/sheet",   {"sound": "р", "typ": "direct", "audience": "lesson"}),
    ("list-r-doma",   "/api/sheet",   {"sound": "р", "typ": "direct", "audience": "home"}),
    # Тот же лист, но с профилем ребёнка: на нём видно, как уходят слова с
    # непоставленными звуками. Это иллюстрация рва, и она нужна отдельно.
    ("list-r-profil", "/api/sheet",   {"sound": "р", "typ": "direct",
                                       "audience": "lesson", "profile": "ш,ж,л"}),
    ("dorozhka-r",    "/api/track",   {"sound": "р", "typ": "direct"}),
    ("zvukovaya-r",   "/api/propisi", {"sound": "р", "typ": "direct"}),
    ("frazy-r",       "/api/phrases", {"sound": "р"}),
    ("labirint-r",    "/api/maze",    {"sound": "р", "position": "initial", "colour": True}),
    ("rasskaz-r",     "/api/rasskaz", {"sound": "р"}),
)


def ask(base: str, path: str, body: Dict[str, Any]) -> str:
    req = urllib.request.Request(base + path, data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req, timeout=180))
    return str(data.get("html") or "")


def embed_images(base: str, html: str, cache: Dict[str, bytes]) -> Tuple[str, int]:
    """Вшить картинки героя в файл — иначе Chrome их не получит."""
    n = 0

    def sub(m: "re.Match[str]") -> str:
        nonlocal n
        attr, path = m.group(1), m.group(2)
        if path not in cache:
            try:
                cache[path] = urllib.request.urlopen(base + path, timeout=60).read()
            except Exception:
                return m.group(0)
        n += 1
        return f'{attr}="data:image/png;base64,{base64.b64encode(cache[path]).decode()}"'

    # ⚠ 2026-08-24: вшивались ТОЛЬКО герои. Спрайты сцены приходят по `/fony/`,
    # и на снимке слоговой дорожки вместо них печатались битые иконки — а глазами
    # это читалось как «картинки не сделаны». Пока спрайтов было три, беда не
    # попадалась на глаза. Список путей теперь один и полный.
    return re.sub(r'\b(src|href|xlink:href)="(/(?:geroi|fony)/[^"]+)"', sub, html), n


def shoot(html_path: str, png_path: str) -> bool:
    """Снять страницу в размер A4. Двойная плотность — чтобы текст не мылился."""
    cmd = [CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           "--no-sandbox", "--virtual-time-budget=10000",
           "--force-device-scale-factor=2", "--window-size=794,1123",
           f"--screenshot={png_path}", f"file://{html_path}"]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   check=False)
    return os.path.isfile(png_path)


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base", default="http://localhost:8784")
    ap.add_argument("--out", default="web/img")
    ap.add_argument("--tmp", default="/tmp/listy")
    ap.add_argument("--width", type=int, default=1200,
                    help="до скольких пикселей уменьшить снимок")
    args = ap.parse_args(argv)

    if not os.path.isfile(CHROME):
        print(f"не найден Chrome: {CHROME}", file=sys.stderr)
        return 1

    os.makedirs(args.out, exist_ok=True)
    os.makedirs(args.tmp, exist_ok=True)
    cache: Dict[str, bytes] = {}
    made = 0

    for name, path, body in JOBS:
        html = ask(args.base, path, body)
        if not html:
            print(f"{name:<16} движок не дал материала")
            continue
        html, n_img = embed_images(args.base, html, cache)
        hp = os.path.abspath(os.path.join(args.tmp, name + ".html"))
        with open(hp, "w", encoding="utf-8") as fh:
            fh.write(html)

        pp = os.path.join(args.tmp, name + ".png")
        if os.path.exists(pp):
            os.remove(pp)
        if not shoot(hp, pp):
            print(f"{name:<16} снимок не вышел")
            continue

        dst = os.path.join(args.out, name + ".png")
        with open(pp, "rb") as src, open(dst, "wb") as out:
            out.write(src.read())
        # sips есть в macOS из коробки; лишней зависимости не появляется
        subprocess.run(["sips", "-Z", str(args.width), dst],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                       check=False)
        size = os.path.getsize(dst) // 1024
        print(f"{name:<16} готов · вшито картинок {n_img} · {size} КБ")
        made += 1

    print(f"\nснимков сделано: {made} из {len(JOBS)} → {args.out}")
    print("⚠ Посмотреть глазами до показа автору — закон 6 проекта: "
          "«тесты зелёные» ≠ «сделано».")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
