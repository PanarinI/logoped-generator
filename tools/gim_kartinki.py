#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Картинки упражнений гимнастики: банк → web/img (копии для страницы и ч/б для печати).

Запуск:  python3 -I tools/gim_kartinki.py

Решение автора 24.11: у каждого упражнения ОБРАЗ (предмет из названия: чашечка, заборчик,
лошадка…), а ЛИЦО с положением губ и языка — только там, где рисунок совпал с описанием
источника (`gymnastics.json` → description). Сложный язык генератор не держит: «Чашечка» мимо
трижды, «Вкусное варенье» лизало сбоку при «не из стороны в сторону» — у них только образ.
«Горка» — своя, не банковая (24.11, вечер): в банке слов горка детская, со спуском, а спинку языка
выгибают вверх — у Фомичёвой «Киска сердится» и «снежинки с горки». Нарисована снежным бугром.
Пробы и разбор — `pictures/probes/2026-11-24-gimnastika*` (в git не идут), промпты —
`logoped_slovar/gimnastika_prompts.json`.

Откуда берётся образ:
  · `bank:<слово>`  — уже нарисованный предмет корпуса `pictures/objects_colour/` (не заказываем);
  · `gim:<имя>`     — заказанный для гимнастики `pictures/gimnastika/<имя>.png`.
Что получается в `web/img/` (сервер отдаёт оттуда без своих правок):
  · gim-<id>-obraz.png     — образ, цвет, 280 px по большей стороне (экран);
  · gim-<id>-obraz-bw.png  — образ, ч/б, снятый с цветного (`imgbw.strip_colour`, закон 13);
  · gim-<id>-litso.png     — лицо, цвет, 280 px — только у тех, где оно есть;
  · gim-<id>-litso-bw.png  — лицо, ч/б — только у тех, где лицо единственная картинка.
Файла нет — экран картинку не показывает (закон 14), так что строку можно убрать без правки кода.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "logoped_slovar"))
import imgbw  # noqa: E402

BANK = ROOT / "pictures" / "objects_colour"
GIM = ROOT / "pictures" / "gimnastika"
OUT = ROOT / "web" / "img"
SIDE = 280

# упражнение (id из gymnastics.json) → (образ, лицо или None)
MAP = {
    "zaborchik":          ("bank:заборчик",              "gim:litso_zaborchik"),
    "trubochka":          ("gim:obraz_trubochka",        "gim:litso_trubochka"),
    "blinchik":           ("bank:блинчик",               "gim:litso_blinchik"),
    "nakazat_yazyk":      (None,                         "gim:litso_nakazat_yazyk"),
    "gorka":              ("gim:obraz_gorka",            None),   # не банковая: там горка-спуск, вогнутая
    "teeth_lower":        ("gim:obraz_zubnaya_shchetka", None),
    "teeth_upper":        ("gim:obraz_zubnaya_shchetka", None),
    "vkusnoe_varenye":    ("bank:варенье",               None),
    "chashechka":         ("gim:obraz_chashechka",       None),
    "fokus":              ("gim:obraz_vatka",            None),
    "gribok":             ("bank:грибок",                None),
    "garmoshka":          ("bank:гармошка",              None),
    "malyar":             ("gim:obraz_kist_malyara",     None),
    "loshadka":           ("bank:лошадь",                None),
    "kacheli":            ("bank:качели",                None),
    "indyuk":             ("gim:obraz_indyuk",           None),
    "parokhod_gudit":     ("bank:пароход",               None),
    "chasiki":            ("bank:часы",                  "gim:litso_chasiki"),
    "zagnat_myach":       ("bank:ворота",                None),
    "kto_dalshe_zagonit": ("bank:мяч",                   None),
}


def src_path(ref: str) -> pathlib.Path:
    kind, name = ref.split(":", 1)
    return (BANK if kind == "bank" else GIM) / f"{name}.png"


def shrink(src: pathlib.Path, dst: pathlib.Path) -> None:
    subprocess.run(["sips", "-Z", str(SIDE), str(src), "--out", str(dst)],
                   check=True, capture_output=True)


def main() -> None:
    made = 0
    for ex, (obraz, litso) in MAP.items():
        if obraz:
            src = src_path(obraz)
            shrink(src, OUT / f"gim-{ex}-obraz.png")
            with tempfile.TemporaryDirectory() as tmp:
                bw = pathlib.Path(tmp) / "bw.png"
                imgbw.strip_colour(src, bw)
                shrink(bw, OUT / f"gim-{ex}-obraz-bw.png")
            made += 2
        if litso:
            shrink(src_path(litso), OUT / f"gim-{ex}-litso.png")
            made += 1
            if not obraz:  # лицо — единственная картинка: ему тоже нужен ч/б для печати (баг 25.11)
                with tempfile.TemporaryDirectory() as tmp:
                    bw = pathlib.Path(tmp) / "bw.png"
                    imgbw.strip_colour(src_path(litso), bw)
                    shrink(bw, OUT / f"gim-{ex}-litso-bw.png")
                made += 1
    print(f"готово: {made} файлов в {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
