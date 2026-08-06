# -*- coding: utf-8 -*-
"""
track.py — ЗВУКОВАЯ ДОРОЖКА: тропа из кружков со слогами.

Это буквально то, что просила логопед Ольга Субботина (см. ГОЛОСА.md):
«Например генерация таких звуковых дорожек» + фото — подводная сцена, поверх неё
жёлтые кружки со слогами РА · РО · РУ · РЫ · РЭ, выложенные тропой, красная
стрелка отмечает старт.

МЕХАНИКА: ребёнок ведёт пальцем по тропе и на каждом кружке произносит слог.
Взрослый идёт рядом и следит за звуком.

ЧЕМ ДОРОЖКА ОТЛИЧАЕТСЯ ОТ ЛИСТА — И ПОЧЕМУ ЭТО ВАЖНО
─────────────────────────────────────────────────────────────────────
• На листе каждая слоговая строка ОБЯЗАНА кончаться словом («ра — рак»):
  канон не разрешает слогу остаться самому по себе. На дорожке слов нет
  вовсе — и это не нарушение, а другой жанр: здесь слог и есть материал.
• Поэтому здесь работает гласная Э. На листе она ломает канонное правило 11
  (слоговой блок ≤ ¼ словесного) — словесного материала нет, правило не
  применяется. На образце Ольги РЭ стоит, и здесь он законен.
• Картинки дорожке не нужны: содержание — слоги. Фон (сюжетная сцена) —
  украшение; ребёнок его не называет, значит фильтр чистоты его не касается.

ЧТО ЗДЕСЬ ГАРАНТИРОВАНО КОДОМ
─────────────────────────────────────────────────────────────────────
• Слоги строятся тем же движком, что и лист (content._syllable_text), поэтому
  орфография верна: после Ш печатается «ши», а не «шы».
• Один тип слога на дорожку — как и на листе (канон, правило 8).
• Порядок кружков не даёт двум одинаковым слогам встать подряд.

ЧЕГО ЗДЕСЬ ПОКА НЕТ (называю вслух, а не умалчиваю)
─────────────────────────────────────────────────────────────────────
• Стечения (КРА, АРТ). В них есть второй согласный — и он может оказаться
  звуком, которого у ребёнка нет. Пока фрейм стечения берётся из отобранных
  СЛОВ, а слов здесь нет, — поэтому типы со стечением дорожка не строит.
• Фона-сюжета нет. Ольга просила «менять фон» — это следующий шаг.
"""

from __future__ import annotations

import html
import math
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import content as C
import phonetics as _P            # noqa: E402


class TrackError(Exception):
    """Дорожку собрать нельзя — с человеческим объяснением."""


# Типы слога, которые дорожка умеет: только «чистые», без второго согласного.
TRACK_TYPES = ("direct", "reverse", "intervocal")

COLS = 5           # кружков в ряду
ROWS_DEFAULT = 6   # рядов на А4


def build_track(sound: str = "р",
                syl_type: str = "direct",
                rows: int = ROWS_DEFAULT,
                seed: int = 0) -> Dict[str, Any]:
    """Кружки дорожки. Возвращает структуру, рендер — отдельно."""
    if sound not in C.WORDS_BY_SOUND:
        raise TrackError(
            f"звука [{sound}] в генераторе нет; собраны: "
            f"{', '.join(sorted(C.WORDS_BY_SOUND))}")
    if syl_type not in TRACK_TYPES:
        raise TrackError(
            f"дорожка строится на прямых, обратных и межгласных слогах; "
            f"«{syl_type}» — со стечением, а в стечении есть второй согласный, "
            f"и его чистоту без словаря не проверить")
    if not (3 <= rows <= 8):
        raise TrackError("рядов на дорожке — от 3 до 8")

    # Порядок слогов ПЕРЕМЕШИВАЕТСЯ по рядам. Строгий цикл РА-РО-РУ-РЫ-РЭ
    # ребёнок выучивает наизусть и перестаёт читать кружки — тренируется
    # память, а не звук. На образце логопеда слоги стоят вперемешку.
    rnd = random.Random(f"{sound}|{syl_type}|{rows}|{seed}")
    base = list(C.SYL_VOWELS_TRACK)
    order: List[str] = []
    while len(order) < rows * COLS + len(base):
        chunk = base[:]
        rnd.shuffle(chunk)
        if order and chunk[0] == order[-1] and len(chunk) > 1:
            chunk[0], chunk[1] = chunk[1], chunk[0]
        order += chunk

    vowels = base
    cells: List[Dict[str, Any]] = []
    n = rows * COLS
    prev = None
    i = 0
    while len(cells) < n:
        v = order[i % len(order)]
        i += 1
        syl = C._syllable_text(sound, v, syl_type)
        if syl == prev and len(vowels) > 1:      # два одинаковых подряд не даём
            continue
        prev = syl
        # На бумагу идёт ОРФОГРАФИЧЕСКАЯ запись: после Ш пишется «ши», а не
        # «шы», и «ше», а не «шэ». Фонемную оставляем — по ней движок считает.
        cells.append({"syllable": C.ortho(syl), "syllable_phon": syl, "vowel": v})

    return {
        "meta": {
            "sound": sound,
            "sound_label": _P.sound_label(sound),
            "syl_type": syl_type,
            "type_label": C.SYL_TYPE_LABEL.get(syl_type, syl_type),
            "rows": rows,
            "cols": COLS,
            "n_cells": len(cells),
            "vowels": vowels,
        },
        "cells": cells,
        "instruction": "Веди пальчиком по дорожке и называй каждый кружок.",
        "adult": "Идите вместе. Если звук «сорвался» — вернитесь на кружок назад "
                 "и скажите его медленно.",
    }


# ═══════════════════════════════════════════════════════════════════════
#  ПЕЧАТЬ
# ═══════════════════════════════════════════════════════════════════════

_CSS = """
@page { size: A4; margin: 12mm 12mm 12mm 16mm; }
* { box-sizing: border-box; }
html, body { margin:0; padding:0; font-family: Georgia, 'Times New Roman', serif; color:#000; }
body { background:#f2f2f2; padding:10px; }
.page { width:210mm; min-height:297mm; margin:0 auto; background:#fff;
        border:1px solid #bbb; padding:12mm 12mm 12mm 16mm; }
@media print { body{background:#fff;padding:0} .page{width:auto;border:0;margin:0;padding:0;min-height:0} }
.doc { display:flex; gap:6mm; align-items:baseline; flex-wrap:wrap;
       font-size:10.5pt; padding-bottom:1.5mm; border-bottom:0.4pt solid #000; }
.badge { border:0.8pt solid #000; padding:0.4mm 1.6mm; font-weight:700; }
.fill { display:inline-block; border-bottom:0.4pt solid #000; min-width:34mm; }
h1 { font-size:15pt; margin:5mm 0 1mm; font-weight:700; }
.hint { font-size:10pt; font-style:italic; color:#444; margin:0 0 4mm; }
.track { margin-top:2mm; }
.row { display:flex; align-items:center; gap:3mm; margin-bottom:2mm; }
.row.rtl { flex-direction:row-reverse; }
.cell { width:31mm; height:31mm; border-radius:50%; border:1.1pt solid #000;
        display:flex; align-items:center; justify-content:center;
        font-size:19pt; font-weight:700; letter-spacing:0.5pt; }
.arr { font-size:13pt; line-height:1; }
.turn { display:flex; justify-content:flex-end; margin:0 6mm 2mm 0; font-size:13pt; }
.row.rtl + .turn { justify-content:flex-start; margin:0 0 2mm 6mm; }
.start { position:relative; }
.start::before { content:"★"; position:absolute; left:-6mm; top:-1mm; font-size:13pt; }
.adult { font-size:10pt; font-style:italic; color:#444; margin-top:5mm;
         border-top:0.4pt solid #000; padding-top:1.5mm; }
"""


def render_track(track: Dict[str, Any]) -> str:
    m = track["meta"]
    cells = track["cells"]
    e = lambda s: html.escape(str(s), quote=False)   # noqa: E731

    rows_html: List[str] = []
    for r in range(m["rows"]):
        chunk = cells[r * m["cols"]:(r + 1) * m["cols"]]
        if not chunk:
            break
        rtl = (r % 2 == 1)
        parts = []
        for i, c in enumerate(chunk):
            cls = "cell start" if (r == 0 and i == 0) else "cell"
            parts.append(f'<div class="{cls}">{e(c["syllable"].upper())}</div>')
            if i < len(chunk) - 1:
                parts.append(f'<div class="arr">{"←" if rtl else "→"}</div>')
        rows_html.append(f'<div class="row{" rtl" if rtl else ""}">{"".join(parts)}</div>')
        if r < m["rows"] - 1:
            rows_html.append('<div class="turn">↓</div>')

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Звуковая дорожка [{e(m['sound_label'])}]</title>
<style>{_CSS}</style>
</head>
<body>
<div class="page">
  <div class="doc">
    <span class="badge">Звук [{e(m['sound_label'])}]</span>
    <span>Звуковая дорожка · {e(m['type_label'])}</span>
    <span>Имя: <span class="fill"></span></span>
    <span>Дата: <span class="fill" style="min-width:24mm"></span></span>
  </div>
  <h1>{e(track['instruction'])}</h1>
  <p class="hint">Начни у звёздочки. На каждом кружке произнеси слог вслух.</p>
  <div class="track">{''.join(rows_html)}</div>
  <div class="adult">{e(track['adult'])}</div>
</div>
</body>
</html>"""


if __name__ == "__main__":
    t = build_track("р", "direct")
    Path("track_demo.html").write_text(render_track(t), encoding="utf-8")
    print("track_demo.html —", t["meta"]["n_cells"], "кружков:",
          " ".join(c["syllable"] for c in t["cells"][:10]), "…")
