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

import characters as CH          # noqa: E402
import scenes as SC              # noqa: E402
import content as C
import phonetics as _P            # noqa: E402


class TrackError(Exception):
    """Дорожку собрать нельзя — с человеческим объяснением."""


# Типы слога, которые дорожка умеет: только «чистые», без второго согласного.
TRACK_TYPES = ("direct", "reverse", "intervocal")

COLS = 5           # кружков в ряду
ROWS_DEFAULT = 6   # рядов на А4

# Шрифт — тот же гротеск, что у листа и остальных материалов. Здесь стояла
# Georgia, и слоговая дорожка оказалась единственной антиквой в наборе. Обе
# найденные нормы для дошкольников (СанПиН 2.4.7.960-00 п. 4.2.1 · ОСТ 29.127-96
# п. 5.1.2) требуют рубленых или новых малоконтрастных шрифтов, и практика
# (BDA Style Guide 2023) говорит то же: у ребёнка, который только узнаёт букву,
# засечки — лишняя деталь. Заменено 08-10 по решению автора.
_FONT = "'PT Sans','Helvetica Neue',Arial,'Liberation Sans',sans-serif"


def _safe_last_phoneme(syllable: str) -> str:
    """Последняя фонема печатной записи — для ЧЕЛОВЕЧЕСКОГО объяснения отказа.

    Разбор многосложной единицы требует ударение; без него он падает. Падать
    внутри текста ошибки нельзя: логопед получил бы трейсбек вместо фразы.
    """
    for stress in (None, 1, 2, 3):
        try:
            a = (_P.analyze(syllable) if stress is None
                 else _P.analyze(syllable, stress))
        except Exception:
            continue
        return a.transcription[-1]
    return syllable[-1]


def build_track(sound: str = "р",
                syl_type: str = "direct",
                rows: int = ROWS_DEFAULT,
                seed: int = 0,
                scene: Optional[str] = None) -> Dict[str, Any]:
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
    # Персонаж нужен уже здесь: фон — это КОНТЕКСТ ГЕРОЯ, и годность сцены
    # проверяется по нему, а не по общему списку (решение автора 08-10).
    import propisi as _PR
    hero = (_PR.image_for(sound).get("name") or "").strip()
    if scene is not None and scene and not SC.fits(hero, scene):
        worlds = SC.worlds_for(hero)
        raise TrackError(
            f"фон «{scene}» не из мира этого героя; "
            + (f"для «{hero}» есть: " + ", ".join(worlds) + " (или без фона)"
               if worlds else "у этого героя миров не задано"))

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
    # Целевой звук обязан уцелеть в печатной записи слога. У звонких в конце
    # слова оглушение обязательно: тропа на [Ж] печатала бы «аж · ож · ыж»,
    # а ребёнок читал бы [аш · ош · ыш] — то есть отрабатывал бы Ш вместо Ж.
    probe = C.ortho(C._syllable_text(sound, vowels[0], syl_type))
    if not C.syllable_keeps_sound(sound, probe):
        raise TrackError(
            f"обратного слога у звука [{_P.sound_label(sound)}] не бывает: "
            f"звонкий согласный в конце слова оглушается, «{probe}» звучит "
            f"как [{_P.sound_label(_safe_last_phoneme(probe))}]. "
            f"Такая дорожка учила бы ребёнка не тому звуку. Возьмите прямой слог.")

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

    # Персонаж маршрута — канонный образ ЭТОГО звука (взят выше), тот же, что в
    # блоке [2] листа и у старта звуковой дорожки. Ребёнок встречает одно
    # существо во всех материалах: это не украшение, а связность.
    # Глагол не подбираем: мотор едет, комарик летит, водичка течёт — под
    # каждый образ пришлось бы вести таблицу спряжений. «Проведи по тропе»
    # верно для любого существа и ничего не обещает сверх того, что нарисовано.
    # scene=None — «реши сам»: берём умолчание по персонажу. Пустая строка —
    # осознанный выбор логопеда «без фона», и его мы не переопределяем.
    if scene is None:
        scene = SC.default_scene(hero)
    # Как назвать путь. «Тропа» была одна на все листы, и «проведи щётку по
    # тропе» звучало сюрреально (слово автора 08-10). Слово берётся от сцены:
    # в лесу тропинка, на дороге дорога, в комнате дорожка. Таблица, а не
    # правило: угадывать по имени сцены — тот же локальный закон 7.
    path_word = SC.path_word(scene)
    task = (f"Проведи {CH.accusative(hero)} по {path_word['dative']} до финиша."
            if hero else
            f"Пройди {path_word['accusative']} от старта до финиша.")

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
            "hero": hero,
            "scene": scene,
        },
        "cells": cells,
        "instruction": task,
        "lead": f"Веди пальчиком по {path_word['dative']} от старта. На каждом "
                f"кружке — шаг, и на каждом шаге скажи слог вслух.",
        "adult": "Идите вместе. Если звук «сорвался» — вернитесь на кружок назад "
                 "и скажите его медленно.",
    }


# ═══════════════════════════════════════════════════════════════════════
#  ПЕЧАТЬ
# ═══════════════════════════════════════════════════════════════════════

_CSS = """
@page { size: A4; margin: 12mm 12mm 12mm 16mm; }
* { box-sizing: border-box; }
html, body { margin:0; padding:0; font-family: 'PT Sans','Helvetica Neue',Arial,'Liberation Sans',sans-serif; color:#000; }
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
.lead { display:flex; align-items:center; gap:4mm; margin:0 0 3mm; }
.hero { width:30mm; height:24mm; border:0; border-radius:2mm;
        display:flex; align-items:center; justify-content:center; flex:0 0 auto;
        font-size:13pt; font-weight:700; color:#000; text-align:center;
        padding:1mm; line-height:1.15; }
.route { display:block; margin:0 auto; }
.adult { font-size:10pt; font-style:italic; color:#444; margin-top:5mm;
         border-top:0.4pt solid #000; padding-top:1.5mm; }
"""


# ── МАРШРУТ, А НЕ ТАБЛИЦА ────────────────────────────────────────────
# До 2026-08-06 дорожка печаталась сеткой 6×5 со стрелками между клетками.
# Ребёнок видел таблицу и ЧИТАЛ её; у практика на образце — извилистая тропа,
# по которой ИДУТ. Автор назвал это прямо: «не таблица, которую читаем, а
# проход по маршруту».
#
# Что здесь метод, а что оформление — разделено честно:
#   ✅ МЕТОД. Персонаж у старта — наш канонный ОБРАЗ ЗВУКА (мотор · комарик ·
#      водичка), тот же, что печатает блок [2] листа и звуковая дорожка.
#      Провенанс у него уже есть (Фомичёва / Спивак). Ничего нового не выдумано:
#      взято существо, которое у ребёнка уже связано с этим звуком.
#   ✅ МЕТОД. Кружок = шаг, и на каждом шаге произносится слог. «Шагание» по
#      дорожке — засвидетельствованное бытование приёма (у практиков ребёнок
#      «надевает на пальцы тапочки-игрушки и начинает шагать по дорожке»).
#   🔶 ОФОРМЛЕНИЕ. Что тропа именно извилистая, что у неё есть финиш и что
#      задание сформулировано как «помоги доехать» — наше. Ни одного
#      методического утверждения это не добавляет: маршрут ничего не обещает
#      про речь, он только держит внимание.
#
# ⛔ Чего здесь намеренно НЕТ: слова у финиша. Слово — речевой материал, оно
# обязано пройти фильтр чистоты по профилю ребёнка, а профиля у дорожки нет.
# Поставить слово «просто для красоты» — ровно тот брак, который проект ловит.
# Финиш обозначен флажком: он ничего не требует произнести.

_W = 178.0         # рабочая ширина, мм
_R = 9.0           # радиус кружка, мм — меньше кружок, виднее тропа
_ROW_H = 34.0      # шаг между рядами, мм
_AMP = 7.0         # размах волны: тропа должна ВИДНО вилять, иначе снова ряды
_TURN = 13.0       # вынос разворота наружу
_MARGIN = _TURN + 3.0   # поля, чтобы развороты не уезжали за край листа
_TOP = _R + _AMP + 2.0


def _row_y(r: int) -> float:
    return _TOP + r * _ROW_H


# ФОРМА ПУТИ ЗАВИСИТ ОТ МИРА (решение автора 08-10: «нам важно разнообразие»).
#
# Раньше на всех листах шла одна волна. Но путь — это и есть сцена в действии:
# по дороге и по взлётной полосе едут прямо и поворачивают под угол, в лесу и
# в траве тропинка вьётся, в комнате дорожка идёт спокойно. Форма не украшение:
# ребёнок ведёт по ней пальцем, и «улица» с прямыми углами читается иначе, чем
# «тропинка». Речевой материал при этом НЕ меняется — кружки те же и на тех же
# местах вдоль пути; меняется только линия между ними.
#
# ⚠ Чего здесь нельзя: делать путь настолько извилистым, что кружки начнут
# налезать друг на друга. Отсюда амплитуды ниже подобраны глазами на 6 рядах.
SHAPE_BY_SCENE: Dict[str, str] = {
    "дорога": "straight", "город": "straight", "аэродром": "straight",
    "лес": "winding", "трава": "winding", "камни": "winding", "пруд": "winding",
    "море": "winding",
    "двор": "wave", "гараж": "wave", "ванная": "wave", "прихожая": "wave",
}
SHAPE_DEFAULT = "wave"


_FLAG_W = 7.5      # ширина полотнища флажка; нужна и расчёту места, и рисунку


def shape_for(scene: str) -> str:
    """Какой формы путь на этой сцене."""
    return SHAPE_BY_SCENE.get(scene or "", SHAPE_DEFAULT)


def _wave(x0: float, x1: float, y: float, t: float,
          shape: str = SHAPE_DEFAULT) -> tuple:
    """Точка на пути ряда: доля пути t → (x, y). Форма задаётся сценой."""
    x = x0 + (x1 - x0) * t
    if shape == "straight":
        # Улица и полоса: ровный ход с одним мягким уступом посередине ряда —
        # иначе ряд читается линейкой и лист снова становится таблицей.
        y_off = -_AMP * 0.45 * (1.0 if t > 0.5 else -1.0)
        edge = min(abs(t - 0.5) * 6.0, 1.0)      # сглаживание уступа
        return x, y + y_off * edge
    if shape == "winding":
        # Тропинка: вьётся чаще и неровно — две гармоники вместо одной.
        return x, y - _AMP * (0.75 * math.sin(2 * math.pi * 2.0 * t)
                              + 0.35 * math.sin(2 * math.pi * 1.0 * t + 0.7))
    return x, y - _AMP * math.sin(2 * math.pi * 1.5 * t)


def _row_ends(r: int) -> tuple:
    left, right = _MARGIN, _W - _MARGIN
    return (right, left) if (r % 2 == 1) else (left, right)


def _route_path(rows: int, cols: int, shape: str = SHAPE_DEFAULT) -> str:
    """Непрерывный путь змейкой: ряд + разворот на краю. Форма ряда — от сцены."""
    d: List[str] = []
    for r in range(rows):
        y, (x0, x1) = _row_y(r), _row_ends(r)
        pts = [f"{px:.1f} {py:.1f}"
               for px, py in (_wave(x0, x1, y, i / 60, shape) for i in range(61))]
        d.append(("M " if r == 0 else "L ") + " L ".join(pts))
        if r < rows - 1:
            out = _TURN if x1 > x0 else -_TURN
            if shape == "straight":
                # Улица поворачивает УГЛОМ, а не петлёй: два прямых отрезка.
                d.append(f"L {x1 + out * 0.62:.1f} {y:.1f} "
                         f"L {x1 + out * 0.62:.1f} {_row_y(r + 1):.1f} "
                         f"L {x1:.1f} {_row_y(r + 1):.1f}")
            else:
                d.append(f"C {x1 + out:.1f} {y:.1f} "
                         f"{x1 + out:.1f} {_row_y(r + 1):.1f} "
                         f"{x1:.1f} {_row_y(r + 1):.1f}")
    return " ".join(d)


def _cell_xy(r: int, i: int, cols: int, shape: str = SHAPE_DEFAULT) -> tuple:
    x0, x1 = _row_ends(r)
    t = 0.0 if cols == 1 else i / (cols - 1)
    return _wave(x0, x1, _row_y(r), t, shape)


def _occupied(rows: int, cols: int, n_cells: int,
              shape: str = SHAPE_DEFAULT) -> List[tuple]:
    """Круги, занятые материалом: кружки со слогами и коридор самой тропы.

    Это карта для сцены — по ней она раскладывает свои предметы (см. `Canvas`
    в scenes.py). Тропа считается не по её кривой Безье, а по точкам волны и
    разворотам: для «занято/свободно» этого хватает, а кода вдвое меньше.
    """
    out: List[tuple] = []
    for idx in range(n_cells):
        r, i = divmod(idx, cols)
        if r >= rows:
            break
        x, y = _cell_xy(r, i, cols, shape)
        out.append((x, y, _R + 2.0))          # кружок со слогом + поле вокруг
    for r in range(rows):
        y, (x0, x1) = _row_y(r), _row_ends(r)
        for k in range(25):                    # коридор вдоль ряда
            px, py = _wave(x0, x1, y, k / 24, shape)
            out.append((px, py, 3.4))
        if r < rows - 1:                       # разворот на краю
            out.append((x1 + (_TURN if x1 > x0 else -_TURN) * 0.7,
                        (y + _row_y(r + 1)) / 2, 6.0))
    return out


def render_track(track: Dict[str, Any], colour: bool = False) -> str:
    m = track["meta"]
    cells = track["cells"]
    e = lambda s: html.escape(str(s), quote=False)   # noqa: E731
    hero = m.get("hero") or m["sound_label"]

    rows, cols = m["rows"], m["cols"]
    height = _TOP + (rows - 1) * _ROW_H + _R + _AMP + 8.0

    # Тропа должна быть ВИДНА ребёнку: по ней ведут пальцем. При opacity 0.22
    # она пропадала между кружками и лист снова читался как ряды.
    # Сцена идёт ПЕРВЫМ слоем: тропа и кружки ложатся поверх неё, а кружки
    # залиты белым — слоги «пробивают» фон насквозь, как на образце Ольги.
    # Сцена должна знать, где идёт дорожка: иначе её предметы окажутся под
    # кружками (поймано автором 08-10 — «фон рисуется без учёта кружков»).
    # Отдаём ей занятые круги: сами кружки со слогами и коридор тропы.
    shape = shape_for(m.get("scene", ""))
    svg = [SC.scene_svg(m.get("scene", ""), _W, height,
                        avoid=_occupied(rows, cols, len(cells), shape))] \
        if m.get("scene") else []
    svg += [f'<path d="{_route_path(rows, cols, shape)}" fill="none" stroke="#000" '
           f'stroke-width="3.0" stroke-linecap="round" opacity="0.42"/>']
    last = None
    for idx, c in enumerate(cells):
        r, i = divmod(idx, cols)
        if r >= rows:
            break
        x, y = _cell_xy(r, i, cols, shape)
        last = (x, y)
        svg.append(
            f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{_R:.1f}" fill="#fff" '
            f'stroke="#000" stroke-width="0.9"/>'
            f'<text x="{x:.1f}" y="{y + 2.3:.1f}" text-anchor="middle" '
            f'font-size="6.6" font-weight="700" font-family="{_FONT}">'
            f'{e(c["syllable"].upper())}</text>')
    # старт и финиш — концы маршрута, а не украшения по краям листа
    sx, sy = _cell_xy(0, 0, cols, shape)
    svg.insert(1,
        f'<path d="M {sx - _R - 8.0:.1f} {sy:.1f} L {sx - _R - 1.5:.1f} {sy:.1f} '
        f'M {sx - _R - 4.5:.1f} {sy - 2.6:.1f} l 3.0 2.6 l -3.0 2.6" '
        f'fill="none" stroke="#000" stroke-width="1.4" stroke-linecap="round" '
        f'stroke-linejoin="round"/>'
        f'<text x="{sx:.1f}" y="{sy - _R - 3.2:.1f}" font-size="4.2" '
        f'text-anchor="middle">старт</text>')
    if last:
        fx, fy = last
        # Флажок ставим ПО ХОДУ движения: на обратном ряду ребёнок идёт справа
        # налево, и цель у него слева. Иначе финиш оказывается позади него.
        last_row = (len(cells) - 1) // cols
        fwd = -1.0 if (last_row % 2 == 1) else 1.0

        def _flag_fits(px: float, d: float) -> bool:
            lo, hi = sorted((px, px + d * _FLAG_W))
            return lo >= 1.0 and hi <= _W - 1.0

        px = fx + fwd * (_R + 2.5)
        # ⚠ Прежде здесь стоял ЗАЖИМ в границы листа, и он молча ставил флажок
        # ПОВЕРХ слога: на [щ] кружок занимал 7.0-25.0 мм, а зажатый флажок
        # оказывался на 8.1 — внутри кружка (замер 08-22, поймано автором
        # глазами). Это ровно та молчаливая подмена, которую запрещает закон 12:
        # материал делал не то, что обещал, и никак об этом не говорил.
        # Теперь: не помещается по ходу — флажок уходит на ДРУГУЮ сторону
        # кружка. Сторона хуже, чем задумано, но слог остаётся читаемым, а это
        # важнее: по слогу ребёнок говорит, по флажку только понимает, что дошёл.
        if not _flag_fits(px, fwd):
            fwd = -fwd
            px = fx + fwd * (_R + 2.5)
        # Подпись уходит ПОД кружок с зазором, а не впритык к нему: на [щ] она
        # начиналась в полумиллиметре от края кружка и читалась как его часть.
        tx = max(8.0, min(_W - 8.0, px))
        svg.append(
            f'<path d="M {px:.1f} {fy + 5.0:.1f} L {px:.1f} {fy - 7.0:.1f} '
            f'L {px + fwd * _FLAG_W:.1f} {fy - 4.6:.1f} L {px:.1f} {fy - 2.2:.1f}" '
            f'fill="#000" stroke="#000" stroke-width="1.4" '
            f'stroke-linejoin="round"/>'
            f'<text x="{tx:.1f}" y="{fy + _R + 4.8:.1f}" font-size="4.2" '
            f'text-anchor="middle">финиш</text>')

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<title>Слоговая дорожка [{e(m['sound_label'])}]</title>
<style>{_CSS}</style>
</head>
<body>
<div class="page">
  <div class="doc">
    <span class="badge">Звук [{e(m['sound_label'])}]</span>
    <span>Слоговая дорожка · {e(m['type_label'])}</span>
    <span>Имя: <span class="fill"></span></span>
    <span>Дата: <span class="fill" style="min-width:24mm"></span></span>
  </div>
  <h1>{e(track['instruction'])}</h1>
  <div class="lead">
    <div class="hero">{CH.character_svg(hero, 30.0, 2.4, colour=colour)
      or f'<span>{e(hero)}</span>'}</div>
    <p class="hint">{e(track['lead'])}</p>
  </div>
  <svg class="route" viewBox="0 0 {_W:.0f} {height:.0f}"
       width="{_W:.0f}mm" height="{height:.0f}mm"
       xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    {''.join(svg)}
  </svg>
  <div class="adult">{e(track['adult'])}</div>
</div>
</body>
</html>"""


if __name__ == "__main__":
    t = build_track("р", "direct")
    Path("track_demo.html").write_text(render_track(t), encoding="utf-8")
    print("track_demo.html —", t["meta"]["n_cells"], "кружков:",
          " ".join(c["syllable"] for c in t["cells"][:10]), "…")
