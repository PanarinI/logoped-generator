# -*- coding: utf-8 -*-
"""
maze.py — генератор СТРАНИЦЫ-ЛАБИРИНТА 3×3 (канон Комаровой Л. А.,
«Автоматизация звука [X] в игровых упражнениях. Альбом дошкольника», ГНОМ и Д).

    from maze import build_maze, render_maze
    m = build_maze(sound="р", position="initial", profile={"ш","ж"}, seed=0)
    open("maze.html","w",encoding="utf-8").write(render_maze(m))

───────────────────────────────────────────────────────────────────────────
ЧТО ТАКОЕ СТРАНИЦА-ЛАБИРИНТ (канон, не наша выдумка)
───────────────────────────────────────────────────────────────────────────
• Сетка 3×3 = 9 клеток с картинками, соединённых стрелками в ОДИН маршрут.
• ★ отмечает старт.
• Одна клетка из девяти может быть служебной: «?» (ребёнок сам придумывает
  слово со звуком в заданной позиции) или звуковая схема.
• Рядом — 2-3 текстовых задания к ТОМУ ЖЕ набору картинок, адресованных
  ВЗРОСЛОМУ.
• ЧЕТЫРЕ РЕЖИМА ходьбы по одному лабиринту: по порядку · с проговариванием
  направления · с пропуском хода (через одну) · наоборот.
• Надстроечные игры на том же наборе: «Чего не стало?», «Волшебная палочка»
  (один — много), «Хлопушки» (по слогам), «Посчитай 1-5», «Четвёртый лишний».
• ⭐ СМЫСЛ ФОРМЫ: ОДИН набор из 9 картинок обслуживает 3-4 упражнения —
  максимальный выход на единицу иллюстрации (иллюстрация здесь самый
  дорогой ресурс).
• Лабиринтов на альбом = число позиционных вариантов звука: Ш — 6, Р — 8,
  С — 9. Этот модуль печатает ОДИН лабиринт: (звук × позиция × seed).

───────────────────────────────────────────────────────────────────────────
ЧТО ЗДЕСЬ ГАРАНТИРОВАНО КОДОМ (а не обещанием)
───────────────────────────────────────────────────────────────────────────
1. ЧИСТОТА. Все слова клеток чисты по профилю ребёнка: banned = профиль
   ∪ смешиваемые с целевым ∪ мягко-твёрдый близнец цели (`content.banned_phonemes`).
   Фильтр по ЗВУКАМ, не по буквам. `verify_purity()` ПАДАЕТ, а не предупреждает.
   Под фильтр попадают и производные формы игр (мн. ч., счётные формы), и
   СЛОВА-НАПРАВЛЕНИЯ («влево» несёт [л] — для цели [р] это грязь), поэтому
   маршрут выбирается из тех, чьи направления чисты (см. п. 4).
2. ПОЗИЦИЯ. У каждого слова целевой звук стоит в ЗАПРОШЕННОЙ позиции —
   проверяется постфактум, `verify_purity()` падает и на этом.
3. РАЗНООБРАЗИЕ. Не более `max_per_category` слов одной крупной семантической
   категории (по умолчанию 2) и раскладка по гласным круговым обходом —
   «9 животных подряд» невозможны. Ослабление порога попадает в warnings.
4. МАРШРУТ. Гамильтонов путь по 3×3 только ортогональными шагами; каждая
   клетка ровно один раз; `verify_route()` падает. Маршрут детерминирован по
   seed и выбирается из ЧИСТЫХ по направлениям (для [р] «влево» отпадает).
5. ДЕТЕРМИНИРОВАННОСТЬ. Один (sound, position, profile, seed, service_cell) —
   один и тот же лабиринт, включая порядок слов, маршрут и набор игр.
6. НЕДОБОР НЕ МОЛЧИТ. `maze["warnings"]` — человекочитаемые строки. Если
   чистых слов не хватает даже на 8 клеток — MazeError с подсказкой, чем
   расширять (позиция · profile · position_mode · ambiguous).

───────────────────────────────────────────────────────────────────────────
ГРАНИЦА ФИЛЬТРА ЧИСТОТЫ (та же, что на текстовом листе — `content.py`)
───────────────────────────────────────────────────────────────────────────
Фильтр применён к тому, что ПРОИЗНОСИТ РЕБЁНОК: 9 слов клеток · производные
формы в играх · слова-направления. НЕ применён к: заголовкам, названиям игр,
инструкциям взрослому и подписям под картинками — подписи читает взрослый,
ребёнку показывают картинку, а не слово. Поле `maze["purity_scope"]` фиксирует
границу явно.
Если канонная рамка ответа оказывается грязной («Не стало ракеты» несёт [л]
и [с]), игра не выбрасывается, а переводится на однословный ответ — и это
записывается в warnings, а не проглатывается.

───────────────────────────────────────────────────────────────────────────
КАРТИНОК ПОКА НЕТ — И ЭТО ВИДНО
───────────────────────────────────────────────────────────────────────────
Клетка рисуется плейсхолдером: пунктирная рамка + крупная подпись слова +
мелко «[картинка]». Пунктир — сознательный сигнал «здесь будет картинка», а
не готовая страница.
ЕДИНСТВЕННАЯ ТОЧКА ЗАМЕНЫ — функция `render_image(word) -> svg_fragment`.
Она возвращает <svg viewBox="0 0 100 85">…</svg>, который CSS растягивает на
клетку. Чтобы поставить настоящие картинки, достаточно вернуть из неё
<svg …><image href="pictures/rak.png" width="100" height="85"/></svg>.
⚠ Здесь стояло: «Жалоба логопедов на ИИ-картинки — неузнаваемы для детей».
ИСТОЧНИКА В ПРОЕКТЕ НЕТ — снято 2026-08-04. Больше того, единственный живой
голос говорит обратное: логопед Ольга Субботина считала генерацию картинок
лёгкой частью («картинки нейросеть сама может делать», ГОЛОСА.md).
Что остаётся верным и БЕЗ этой жалобы: узкое место — не генерация, а ПРИЁМКА,
и мера приёмки известна — name agreement (каким словом человек спонтанно
называет изображение), а не «красиво нарисовано». Поэтому подпись под клеткой
остаётся всегда: взрослый видит, что́ должно быть нарисовано, и бракует.

───────────────────────────────────────────────────────────────────────────
ЧЕСТНЫЕ ОГРАНИЧЕНИЯ
───────────────────────────────────────────────────────────────────────────
* «Хлопушки» печатают ЧИСЛО слогов из движка, но не деление на слоги:
  слоги движка фонетические («мороз» = ма-рос), и в орфографической записи
  они смотрелись бы ошибкой. Число хлопков = число гласных — оно верно.
* «Четвёртый лишний» по умолчанию строится ПО ЧИСЛУ СЛОГОВ, а не по смыслу:
  правило разнообразия (≤2 слова одной категории) сознательно не даёт собрать
  на одной странице семантическую тройку. Смысловой вариант строится только
  если порог разнообразия был ослаблен и тройка появилась.
* Счётные формы («два рака — пять раков») берутся у морфологии `content.py`
  (правила + таблицы исключений), а не из словаря форм.
* Ударение в подписи ставится политикой `put_stress` из `sheet.py`; на
  чистоту оно не влияет (все корригируемые фонемы — согласные).
* Модель высоты грубее, чем в `sheet.py`: считается только блок заданий, и
  единственная ступень сокращения — снять последнюю надстроечную игру.
"""

from __future__ import annotations

import argparse
import unicodedata
import base64
import html
import json
import math
import random
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:                      # чтобы модуль работал из любой cwd
    sys.path.insert(0, str(HERE))

import phonetics as ph                             # noqa: E402
import content as C
import phonetics as _P                                # noqa: E402
import sheet as S                                  # noqa: E402

__all__ = [
    "build_maze", "render_maze", "render_image",
    "verify_purity", "verify_route", "expand_profile",
    "POSITIONS", "ROUTES", "SERVICE_KINDS", "MODES",
    "CELL_MM", "GAP_MM", "GRID_MM",
    "MazeError", "RouteViolation", "PurityViolation",
]


# ═══════════════════════════════════════════════════════════════════════
#  0. ОШИБКИ
# ═══════════════════════════════════════════════════════════════════════

class MazeError(Exception):
    """Лабиринт собрать невозможно (материала не хватает / параметр вне канона)."""


class RouteViolation(MazeError):
    """Маршрут не гамильтонов путь по сетке 3×3 ортогональными шагами."""


# Тот же контракт, что на текстовом листе: один тип исключения на весь проект.
PurityViolation = C.PurityViolation


# ═══════════════════════════════════════════════════════════════════════
#  1. КАНОН-КОНСТАНТЫ
# ═══════════════════════════════════════════════════════════════════════

GRID = 3
N_CELLS = GRID * GRID                       # 9 — канон, не параметр

POSITIONS: Tuple[str, ...] = ("initial", "medial", "final")

POSITION_LABEL: Dict[str, str] = {
    "initial": "звук в начале слова",
    "medial":  "звук в середине слова",
    "final":   "звук в конце слова",
}

# Короткая форма — для подписи служебной клетки: длинная переносится на вторую
# строку, отнимает высоту у картинки, и служебная клетка выходит мельче соседних.
POSITION_SHORT: Dict[str, str] = {
    "initial": "звук в начале",
    "medial":  "звук в середине",
    "final":   "звук в конце",
}

SERVICE_KINDS: Tuple[str, ...] = ("question", "scheme", "none")

# Клетка не меньше 55×55 мм — иначе ребёнок не разглядит картинку.
CELL_MM = 55.0
GAP_MM = 7.0                                # зазор, в нём живёт стрелка
GRID_MM = GRID * CELL_MM + (GRID - 1) * GAP_MM          # 179 мм из 180 доступных

# Плейсхолдер рисуется в этой системе координат; CSS растягивает на клетку.
PIC_VB_W, PIC_VB_H = 100.0, 85.0
PIC_PAD = 0.06          # поле вокруг рисунка, долей высоты клетки (08-18)

DIR_RU: Dict[str, str] = {"right": "вправо", "left": "влево",
                          "down": "вниз", "up": "вверх"}

# ───────────────────────────────────────────────────────────────────────
#  Маршруты. Все — гамильтоновы пути ортогональными шагами (проверяется).
#  Первые два не содержат хода «влево»: для цели [р] слово «влево» несёт
#  запрещённый [л], и режим 2 («с проговариванием направления») на таком
#  маршруте был бы грязным. Выбор маршрута это учитывает.
# ───────────────────────────────────────────────────────────────────────
ROUTES: Dict[str, Tuple[Tuple[int, int], ...]] = {
    "snake_cols": ((0, 0), (1, 0), (2, 0), (2, 1), (1, 1), (0, 1), (0, 2), (1, 2), (2, 2)),
    "snake_cols_up": ((2, 0), (1, 0), (0, 0), (0, 1), (1, 1), (2, 1), (2, 2), (1, 2), (0, 2)),
    "snake_rows": ((0, 0), (0, 1), (0, 2), (1, 2), (1, 1), (1, 0), (2, 0), (2, 1), (2, 2)),
    "snake_rows_up": ((2, 0), (2, 1), (2, 2), (1, 2), (1, 1), (1, 0), (0, 0), (0, 1), (0, 2)),
    "snake_cols_right": ((0, 2), (1, 2), (2, 2), (2, 1), (1, 1), (0, 1), (0, 0), (1, 0), (2, 0)),
    "spiral_in": ((0, 0), (0, 1), (0, 2), (1, 2), (2, 2), (2, 1), (2, 0), (1, 0), (1, 1)),
    "spiral_out": ((1, 1), (1, 0), (2, 0), (2, 1), (2, 2), (1, 2), (0, 2), (0, 1), (0, 0)),
}

ROUTE_LABEL: Dict[str, str] = {
    "snake_cols": "змейка по столбцам, сверху вниз",
    "snake_cols_up": "змейка по столбцам, снизу вверх",
    "snake_rows": "змейка по строкам",
    "snake_rows_up": "змейка по строкам, снизу",
    "snake_cols_right": "змейка по столбцам справа налево",
    "spiral_in": "спираль внутрь",
    "spiral_out": "спираль наружу",
}

# Названия четырёх режимов ходьбы — канон Комаровой, порядок жёсткий.
MODES: Tuple[str, ...] = ("По порядку", "С направлением", "Через одну", "Наоборот")

# Числительные для «Посчитай 1-5» — сами речевой материал, проверяются на чистоту.
NUMERALS = {"m": ("один", "два"), "f": ("одна", "две"), "n": ("одно", "два")}

MAX_GAMES = 3                 # «2-3 надстроечные игры» — канон страницы
MIN_GAMES = 2
MAX_PER_CATEGORY = 2          # правило разнообразия: не «9 животных подряд»
GAME_ITEMS = 5                # сколько пар/строк печатать в игре


# ═══════════════════════════════════════════════════════════════════════
#  2. МАРШРУТ
# ═══════════════════════════════════════════════════════════════════════

def _direction(a: Tuple[int, int], b: Tuple[int, int]) -> str:
    dr, dc = b[0] - a[0], b[1] - a[1]
    if (abs(dr) + abs(dc)) != 1:
        raise RouteViolation(f"шаг {a}→{b} не ортогональный соседний")
    if dc == 1:
        return "right"
    if dc == -1:
        return "left"
    return "down" if dr == 1 else "up"


def _route_directions(path: Sequence[Tuple[int, int]]) -> List[str]:
    return [_direction(path[i], path[i + 1]) for i in range(len(path) - 1)]


def verify_route(path: Sequence[Tuple[int, int]]) -> None:
    """Падает, если путь не обходит все 9 клеток ровно по разу ортогонально."""
    if len(path) != N_CELLS:
        raise RouteViolation(f"в маршруте {len(path)} клеток, а нужно {N_CELLS}")
    seen = {tuple(p) for p in path}
    if len(seen) != N_CELLS:
        raise RouteViolation("маршрут проходит клетку дважды")
    for r, c in path:
        if not (0 <= r < GRID and 0 <= c < GRID):
            raise RouteViolation(f"клетка ({r},{c}) вне сетки 3×3")
    _route_directions(path)                 # сам бросит на неортогональном шаге


for _name, _p in ROUTES.items():            # константы проверяются при импорте
    verify_route(_p)


# ═══════════════════════════════════════════════════════════════════════
#  3. ПРОФИЛЬ И СЛОВАРЬ
# ═══════════════════════════════════════════════════════════════════════

def expand_profile(raw: Any) -> FrozenSet[str]:
    """'л,ш,ж' | 'шипящие,л' | {'ш','ж'} -> множество фонемных ключей.

    Строку разбирает тот же помощник, что и CLI листа (`sheet._expand_profile`):
    держать в паре — иначе одна и та же строка означала бы на двух листах разное.
    """
    if raw is None:
        return frozenset()
    if isinstance(raw, str):
        return frozenset(S._expand_profile(raw))
    return frozenset(raw)


def _words_path(sound: str, words_path: Optional[str]) -> str:
    if words_path:
        return words_path
    if sound not in C.WORDS_BY_SOUND:
        raise MazeError(
            f"для звука [{sound}] словаря нет; есть только: "
            f"{', '.join(sorted(C.WORDS_BY_SOUND))}. Передайте words_path=…")
    return str(HERE / C.WORDS_BY_SOUND[sound])


def _coarse_category(row: Dict[str, Any]) -> str:
    """'животные/водные' -> 'животные'. Разнообразие считаем по крупной ветке."""
    return str(row.get("semantic_category") or "прочее").split("/")[0]


def _cand_vowel(occ: Dict[str, Any], position: str) -> Optional[str]:
    """Гласная, «окрашивающая» целевой звук: для начала — следующая, для конца —
    предыдущая. Внутри стечения гласной может не быть вовсе (тигр) — тогда None."""
    after, before = occ.get("vowel_after"), occ.get("vowel_before")
    order = (before, after) if position == "final" else (after, before)
    for v in order:
        if v:
            return v
    return None


# ═══════════════════════════════════════════════════════════════════════
#  4. ОТБОР 9 СЛОВ: ворота движка + разнообразие
# ═══════════════════════════════════════════════════════════════════════

def _candidates(sound: str, position: str, banned: FrozenSet[str],
                rows: Sequence[Dict[str, Any]], *, position_mode: str,
                min_familiarity: int, allow_ambiguous: bool,
                markova_max: Optional[int]
                ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], Dict[str, int]]:
    """Все слова, годные для клетки: ворота движка + пригодность к РИСОВАНИЮ."""
    pre: List[Dict[str, Any]] = []
    dropped = {"нерисуемое": 0, "неоднозначное": 0, "частотность": 0, "чувствительное": 0}
    for row in rows:
        if row.get("sensitive"):
            dropped["чувствительное"] += 1
            continue
        if not row.get("imageable", True):
            dropped["нерисуемое"] += 1                 # клетка — это картинка
            continue
        if row.get("ambiguous") and not allow_ambiguous:
            dropped["неоднозначное"] += 1              # «рама» рисуется двояко
            continue
        if int(row.get("familiarity", 0)) < min_familiarity:
            dropped["частотность"] += 1
            continue
        pre.append(row)

    sel = ph.select(pre, sound, position=position, exclude_phonemes=banned,
                    markova_max=markova_max, n=max(1, len(pre)),
                    position_mode=position_mode)
    by_word = {r["word"]: r for r in pre}
    pos_key = "position" if position_mode == "strict" else "position_wide"

    out: List[Dict[str, Any]] = []
    for a in sel:
        row = by_word[a.word]
        occ = next(o for o in a.sound_occurrences
                   if o["phoneme"] == sound and o[pos_key] == position)
        out.append({
            "word": a.word,
            "stress_syllable": a.stress_syllable,
            "transcription": a.transcription_display,
            "n_syllables": a.n_syllables,
            "vowel": _cand_vowel(occ, position),
            "stressed": bool(occ["stressed"]),
            "category": _coarse_category(row),
            "semantic_category": row.get("semantic_category"),
            "familiarity": int(row.get("familiarity", 0)),
            "ambiguous": bool(row.get("ambiguous")),
            "plural": row.get("plural"),
            "gender": row.get("gender"),
            "markova_v1": a.markova_v1,
        })
    return out, sel.report, dropped


def _pick_diverse(cands: Sequence[Dict[str, Any]], n: int, rnd: random.Random,
                  max_per_category: int, warnings: List[str]
                  ) -> List[Dict[str, Any]]:
    """Круговой обход: сперва новая категория, потом новая гласная, потом ранг.

    Порядок ключей не косметика: «не 9 животных подряд» — требование к набору,
    поэтому категория весомее гласной. Порог не хватило — он растёт на 1 и это
    попадает в warnings, а не проглатывается.
    """
    pool = list(cands)
    rnd.shuffle(pool)
    # ⚠ Последним ключом сортировки стояло САМО СЛОВО — и оно гасило
    # перемешивание полностью: при равных familiarity/ударении/слогах порядок
    # определялся алфавитом, а не сидом. Из-за этого кубик у лабиринта был
    # выключен «потому что на узких пулах seed даёт перестановку тех же слов» —
    # объяснение неверное: seed не участвовал в отборе ВООБЩЕ, и пулы не узкие
    # (у [с] в начале 63 слова на 8 клеток). Разобрано 08-23.
    #
    # Теперь при полном равенстве ключей порядок решает перемешивание, то есть
    # сид. Всё, что было детерминированным ПО СМЫСЛУ (частотность, ударность,
    # число слогов), таким и осталось — случайность входит только там, где
    # выбирать было не из чего.
    pool.sort(key=lambda c: (-c["familiarity"], 0 if c["stressed"] else 1,
                             c["n_syllables"]))
    for i, c in enumerate(pool):
        c["_rank"] = i

    picked: List[Dict[str, Any]] = []
    cat_used: Dict[str, int] = {}
    vow_used: Dict[Optional[str], int] = {}
    cap = max_per_category
    rest = list(pool)

    while len(picked) < n:
        free = [c for c in rest if cat_used.get(c["category"], 0) < cap]
        if not free:
            cap += 1
            warnings.append(
                f"разнообразие: порог «не более {cap - 1} слов одной категории» "
                f"поднят до {cap} — чистых слов других категорий не нашлось")
            continue
        best = min(free, key=lambda c: (cat_used.get(c["category"], 0),
                                        vow_used.get(c["vowel"], 0),
                                        c["_rank"]))
        picked.append(best)
        rest.remove(best)
        cat_used[best["category"]] = cat_used.get(best["category"], 0) + 1
        vow_used[best["vowel"]] = vow_used.get(best["vowel"], 0) + 1

    for c in picked:
        c.pop("_rank", None)
    return picked


def _shortfall(report: Dict[str, Any], dropped: Dict[str, int],
               need: int, have: int, position: str, position_mode: str) -> str:
    parts = [f"чистых слов на клетки: {have} из {need}"]
    rej = report.get("rejected") or {}
    if rej:
        parts.append("движок отсеял: " + ", ".join(f"{k} {v}" for k, v in
                                                   sorted(rej.items(), key=lambda kv: -kv[1])))
    lost = {k: v for k, v in dropped.items() if v}
    if lost:
        parts.append("к рисованию не годны: " + ", ".join(f"{k} {v}" for k, v in lost.items()))
    how = []
    if position_mode == "strict":
        how.append("position_mode='wide' (звук внутри начального стечения — «трава»)")
    how.append("allow_ambiguous=True (слова с неоднозначной картинкой)")
    how.append(f"другая позиция звука (сейчас {position})")
    how.append("расширить словник этого звука")
    parts.append("чем расширить: " + " · ".join(how))
    return "; ".join(parts)


# ═══════════════════════════════════════════════════════════════════════
#  5. НАДСТРОЕЧНЫЕ ИГРЫ (на ТОМ ЖЕ наборе картинок)
# ═══════════════════════════════════════════════════════════════════════

def _clean(text: str, banned: FrozenSet[str]) -> bool:
    """Чист ли ПРОИЗНОСИМЫЙ фрагмент: каждое слово отдельно через движок."""
    return all(C.is_clean(tok, banned) for tok in text.replace("—", " ").split() if tok)


def _game_missing(cells: Sequence[Dict[str, Any]], banned: FrozenSet[str]
                  ) -> Dict[str, Any]:
    """«Чего не стало?» — закрыть картинку. Рамка ответа сама речевой материал."""
    notes: List[str] = []
    text = ("Закройте одну картинку ладонью — ребёнок называет, чего не стало. "
            "Повторите 4-5 раз, каждый раз закрывая новую.")
    if _clean("не стало", banned):
        text += " Ответ полной фразой: «Не стало …»."
    else:
        dirty = sorted(C.corrigible_of("стало") & banned)
        text += (" Ответ ОДНИМ СЛОВОМ: рамка «не стало» несёт "
                 f"{', '.join('[' + d + ']' for d in dirty)} и не проговаривается.")
        notes.append(
            "«Чего не стало?»: канонная рамка ответа грязна по профилю "
            f"({', '.join(dirty)}) — игра переведена на однословный ответ")
    return {"kind": "missing", "title": "Чего не стало?", "text": text,
            "items": [], "_notes": notes}


def _countable(c: Dict[str, Any]) -> bool:
    pl = c.get("plural")
    return bool(pl) and pl != c["word"] and c.get("gender") in ("m", "f", "n")


def _game_one_many(cells: Sequence[Dict[str, Any]], banned: FrozenSet[str]
                   ) -> Optional[Dict[str, Any]]:
    """«Волшебная палочка»: один — много. Мн. ч. — тоже речь ребёнка, фильтруем."""
    pairs, blocked, notes = [], [], []
    for c in cells:
        if not _countable(c):
            continue
        if not C.is_clean(c["plural"], banned):
            blocked.append(f"{c['word']} → {c['plural']}")
            continue
        pairs.append({"prompt": c["word"], "answer": c["plural"]})
    if blocked:
        notes.append("«Один — много»: формы мн. ч. грязны по профилю и убраны: "
                     + ", ".join(blocked))
    if len(pairs) < 4:
        return None
    return {
        "kind": "one_many",
        "title": "Волшебная палочка (один — много)",
        "text": ("Взмах палочки — предмет становится многим. Образец: "
                 f"{pairs[0]['prompt']} — {pairs[0]['answer']}. Пары: "
                 + " · ".join(f"{p['prompt']} — {p['answer']}"
                              for p in pairs[1:GAME_ITEMS]) + "."),
        "items": pairs,
        "_notes": notes,
    }


def _game_claps(cells: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """«Хлопушки»: число слогов — из движка (число гласных), не на глаз."""
    items = [{"word": c["word"], "n": c["n_syllables"]} for c in cells]
    return {
        "kind": "claps",
        "title": "Хлопушки",
        "text": ("Ребёнок называет слово по слогам и отхлопывает каждый слог. "
                 "Хлопков: "
                 + " · ".join(f"{i['word']} {i['n']}" for i in items) + "."),
        "items": items,
        "_notes": [],
    }


def _game_count(cells: Sequence[Dict[str, Any]], banned: FrozenSet[str]
                ) -> Optional[Dict[str, Any]]:
    """«Посчитай 1-5». Морфология заимствована у content.py (правила + таблицы
    исключений) — единственный склад падежных форм в проекте, дублировать его
    здесь значило бы завести второй источник истины. Слово, на которое правило
    не отвечает (беглая гласная: рынок, ковёр), молча выпадает из игры — лучше
    короче, чем «пять рыноков»."""
    if not C.is_clean("пять", banned):
        return None
    rows: List[Dict[str, Any]] = []
    for c in cells:
        if not _countable(c):
            continue
        g = c["gender"]
        gs, gp = C._gen_sg(c["word"], g), C._gen_pl(c["word"], g)
        if not gs or not gp:
            continue
        one, two = NUMERALS[g]
        if not (C.is_clean(gs, banned) and C.is_clean(gp, banned)
                and C.is_clean(one, banned) and C.is_clean(two, banned)):
            continue
        rows.append({"prompt": c["word"],
                     "answer": f"{one} {c['word']} — {two} {gs} — пять {gp}"})
    if len(rows) < 4:
        return None
    return {
        "kind": "count_1_5",
        "title": "Посчитай 1-5",
        "text": ("Образец: " + rows[0]["answer"] + ". Так же: "
                 + " · ".join(r["answer"] for r in rows[1:3])
                 + ". Остальные картинки — по тому же образцу."),
        "items": rows,
        "_notes": [],
    }


def _game_fourth(cells: Sequence[Dict[str, Any]], rnd: random.Random
                 ) -> Optional[Dict[str, Any]]:
    """«Четвёртый лишний». Смысловой вариант — только если тройка одной
    категории на странице вообще есть (правило разнообразия обычно не даёт);
    иначе честный фонологический вариант — по числу слогов."""
    by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for c in cells:
        by_cat.setdefault(c["category"], []).append(c)
    for cat in sorted(by_cat):
        if len(by_cat[cat]) >= 3:
            three = by_cat[cat][:3]
            others = [c for c in cells if c["category"] != cat]
            if not others:
                continue
            odd = others[rnd.randrange(len(others))]
            four = three + [odd]
            return {
                "kind": "fourth_extra",
                "title": "Четвёртый лишний",
                "text": ("Назовите четыре картинки: "
                         + " · ".join(c["word"] for c in four)
                         + f". Ребёнок находит лишнюю и объясняет выбор. "
                           f"Лишняя — «{odd['word']}»: остальные — {cat}."),
                "items": [c["word"] for c in four],
                "_notes": [],
            }
    by_n: Dict[int, List[Dict[str, Any]]] = {}
    for c in cells:
        by_n.setdefault(c["n_syllables"], []).append(c)
    for n in sorted(by_n):
        if len(by_n[n]) >= 3:
            three = by_n[n][:3]
            others = [c for c in cells if c["n_syllables"] != n]
            if not others:
                continue
            odd = min(others, key=lambda c: (abs(c["n_syllables"] - n), c["word"]))
            four = three + [odd]
            return {
                "kind": "fourth_extra_syllables",
                "title": "Четвёртый лишний (по числу слогов)",
                "text": ("Назовите четыре картинки: "
                         + " · ".join(c["word"] for c in four)
                         + f". Ребёнок отхлопывает каждое и находит лишнее. "
                           f"Лишнее — «{odd['word']}» ({odd['n_syllables']}): "
                           f"в остальных по {n}."),
                "items": [c["word"] for c in four],
                "_notes": [],
            }
    return None


def _build_games(cells: Sequence[Dict[str, Any]], banned: FrozenSet[str],
                 rnd: random.Random, n_games: int, warnings: List[str]
                 ) -> List[Dict[str, Any]]:
    """Пул строится весь, на лист идут n_games. Замечания игры (`_notes`) едут
    с ней и выливаются в warnings уже после лестницы сокращений — предупреждение
    о том, чего на бумаге нет, это шум, из-за которого перестают читать настоящие."""
    pool: List[Dict[str, Any]] = [_game_missing(cells, banned)]
    for g in (_game_one_many(cells, banned),
              _game_claps(cells),
              _game_count(cells, banned),
              _game_fourth(cells, rnd)):
        if g:
            pool.append(g)
    if len(pool) < MIN_GAMES:
        warnings.append(f"надстроечных игр удалось построить {len(pool)} — "
                        f"меньше канонного минимума {MIN_GAMES}")
        chosen = list(pool)
    else:
        k = min(n_games, len(pool))
        idx = sorted(rnd.sample(range(len(pool)), k))   # порядок канона сохранён
        chosen = [pool[i] for i in idx]
    for g in pool:                                      # неотобранные молчат
        if g not in chosen:
            g.pop("_notes", None)
    return chosen


def _flush_game_notes(maze: Dict[str, Any]) -> None:
    """Замечания игр, ДОЖИВШИХ до бумаги, — в warnings."""
    for g in maze["tasks"]["games"]:
        maze["warnings"].extend(g.pop("_notes", []))


# ═══════════════════════════════════════════════════════════════════════
#  6. ЗАДАНИЯ ВЗРОСЛОМУ: четыре режима ходьбы
# ═══════════════════════════════════════════════════════════════════════

def _chain(pairs: Sequence[str], sep: str = " · ") -> str:
    return sep.join(pairs)


def _build_modes(order: Sequence[Dict[str, Any]], dirs: Sequence[str],
                 speak_dirs: bool) -> List[Dict[str, Any]]:
    """order — клетки в порядке маршрута (служебная тоже, под своим именем)."""
    names = [c["speak"] for c in order]
    steps = [f"{names[i]} — {DIR_RU[dirs[i]]}" for i in range(len(dirs))]

    # цепочку не печатаем целиком: стрелки на той же странице, повтор съедает
    # место, которое нужнее режимам 3 и 4 (там порядок ДРУГОЙ, чем на картинке).
    m2 = ("Тот же путь, но ребёнок называет и направление хода: "
          + _chain(steps[:3], ", ") + "… — и так по стрелкам до финиша.")
    if not speak_dirs:
        m2 = ("Тот же путь, но направление ребёнок ПОКАЗЫВАЕТ рукой, а не называет: "
              "слова-направления этого маршрута грязны по профилю "
              f"({', '.join(sorted({DIR_RU[d] for d in dirs}))}).")

    return [
        {"n": 1, "title": MODES[0], "text":
            "Ребёнок ставит фишку (игрушку) на картинку со звёздочкой и ведёт её "
            "по стрелкам, называя каждую картинку. Если слово названо неправильно, "
            "следующий ход делать нельзя, пока слово не будет названо верно."},
        {"n": 2, "title": MODES[1], "text": m2},
        {"n": 3, "title": MODES[2], "text":
            "Сначала пройдите весь путь подряд. Потом — с пропуском хода: ребёнок "
            "называет каждую вторую картинку: " + _chain(names[::2]) + "."},
        {"n": 4, "title": MODES[3], "text":
            "От последней картинки в обратном направлении, против стрелок: "
            + _chain(names[::-1]) + "."},
    ]


# ═══════════════════════════════════════════════════════════════════════
#  7. МОДЕЛЬ ВЫСОТЫ БЛОКА ЗАДАНИЙ (одна ступень сокращения)
# ═══════════════════════════════════════════════════════════════════════

FS_TASK = 9.5                 # pt — взрослому, мельче канонного минимума ребёнку
LH_TASK = 1.28
TASK_COLS = 2
TASK_COL_GAP = 6.0            # мм

HEADER_MM = 7.0               # шапка листа + линейка (одна строка 11 pt)
MAZE_TOP_MM = 3.0             # воздух над сеткой
TASKS_TOP_MM = 3.5            # воздух под сеткой


def _task_line_mm() -> float:
    return FS_TASK * S.PT_MM * LH_TASK


def _chars_per_line() -> float:
    col_w = (S.CONTENT_W - TASK_COL_GAP * (TASK_COLS - 1)) / TASK_COLS
    return col_w / (FS_TASK * S.PT_MM * S.CHAR_W)


def _item_lines(text: str) -> int:
    """Заголовок стоит в подбор с телом, поэтому считаем одну строку запаса."""
    return 1 + max(1, math.ceil(len(text) / _chars_per_line()))


def estimate_tasks_mm(tasks: Dict[str, Any]) -> float:
    """Высота блока заданий в мм по тем же метрикам, что заданы в CSS."""
    lines = 0
    for it in list(tasks["modes"]) + list(tasks["games"]):
        lines += _item_lines(it["text"])
    lines += math.ceil(len(tasks["legend"]) / _chars_per_line())
    per_col = math.ceil(lines / TASK_COLS)
    return 4.6 + per_col * _task_line_mm()              # 4.6 — заголовок блока


def tasks_budget_mm(cell_mm: float) -> float:
    grid = GRID * cell_mm + (GRID - 1) * GAP_MM
    return S.CONTENT_H - HEADER_MM - MAZE_TOP_MM - grid - TASKS_TOP_MM


def _fit_tasks(maze: Dict[str, Any]) -> None:
    """Единственная ступень: снять последнюю надстроечную игру. Режимы — канон,
    они не снимаются никогда; если и без игр не влезает — говорим прямо."""
    budget = tasks_budget_mm(maze["meta"]["cell_mm"])
    tasks = maze["tasks"]
    while (estimate_tasks_mm(tasks) > budget
           and len(tasks["games"]) > MIN_GAMES):
        dropped = tasks["games"].pop()
        maze["warnings"].append(
            f"блок заданий не влезал — снята игра «{dropped['title']}» "
            f"(модель: {estimate_tasks_mm(tasks):.0f} мм при бюджете {budget:.0f} мм)")
    est = estimate_tasks_mm(tasks)
    maze["meta"]["tasks_mm"] = round(est, 1)
    maze["meta"]["tasks_budget_mm"] = round(budget, 1)
    if est > budget:
        maze["warnings"].append(
            f"блок заданий по модели {est:.0f} мм при бюджете {budget:.0f} мм — "
            f"второй лист или меньше клетка (--cell)")


# ═══════════════════════════════════════════════════════════════════════
#  8. ПРОВЕРКИ (падают, а не предупреждают)
# ═══════════════════════════════════════════════════════════════════════

def verify_purity(maze: Dict[str, Any]) -> None:
    """Ни одна произносимая ребёнком единица не несёт запрещённой фонемы,
    и целевой звук у каждого слова стоит в запрошенной позиции."""
    banned = frozenset(maze["meta"]["banned"])
    sound = maze["meta"]["sound"]
    position = maze["meta"]["position"]
    mode = maze["meta"]["position_mode"]
    pos_key = "position" if mode == "strict" else "position_wide"

    words = [c["word"] for c in maze["cells"] if c["kind"] == "picture"]
    if len(set(words)) != len(words):
        raise MazeError(f"слово повторяется в клетках: {sorted(words)}")

    for c in maze["cells"]:
        if c["kind"] != "picture":
            continue
        dirty = sorted(C.corrigible_of(c["word"], c.get("stress_syllable")) & banned)
        if dirty:
            raise PurityViolation(
                f"клетка {c['order']}: «{c['word']}» {c['transcription']} несёт "
                f"{dirty} — запрещено профилем {sorted(maze['meta']['profile'])}")
        a = ph.analyze(c["word"], c.get("stress_syllable"))
        if not any(o["phoneme"] == sound and o[pos_key] == position
                   for o in a.sound_occurrences):
            raise PurityViolation(
                f"клетка {c['order']}: «{c['word']}» {a.transcription_display} — "
                f"[{sound}] не в позиции {position} (режим {mode})")

    # производные формы игр — тоже речь ребёнка
    for g in maze["tasks"]["games"]:
        for it in g.get("items", []):
            forms: List[str] = []
            if isinstance(it, dict):
                forms = [str(it.get("answer", ""))]
            for f in forms:
                for tok in f.replace("—", " ").split():
                    if tok and not C.is_clean(tok, banned):
                        raise PurityViolation(
                            f"игра «{g['title']}»: форма «{tok}» несёт "
                            f"{sorted(C.corrigible_of(tok) & banned)}")


# ═══════════════════════════════════════════════════════════════════════
#  9. ГЛАВНАЯ ФУНКЦИЯ
# ═══════════════════════════════════════════════════════════════════════

def build_maze(sound: str = "р",
               position: str = "initial",
               profile: Iterable[str] = frozenset(),
               seed: int = 0,
               service_cell: str = "question",
               *,
               position_mode: str = "strict",
               allow_ambiguous: bool = False,
               min_familiarity: int = 2,
               markova_max: Optional[int] = None,
               max_per_category: int = MAX_PER_CATEGORY,
               n_games: int = MAX_GAMES,
               cell_mm: float = CELL_MM,
               words_path: Optional[str] = None,
               route: Optional[str] = None,
               child_name: str = "") -> Dict[str, Any]:
    """Собрать страницу-лабиринт 3×3.

    sound        — целевой звук (ключ фонемы движка: 'р').
    position     — initial | medial | final: где в слове стоит целевой звук.
    profile      — НАРУШЕННЫЕ у ребёнка фонемы (строка «л,ш» тоже принимается).
    seed         — детерминированная вариативность: маршрут, набор слов, игры.
    service_cell — question | scheme | none: одна из девяти клеток служебная.
    """
    if position not in POSITIONS:
        raise MazeError(f"position={position!r}; допустимы: {', '.join(POSITIONS)}")
    if service_cell is None:
        service_cell = "none"
    if service_cell not in SERVICE_KINDS:
        raise MazeError(f"service_cell={service_cell!r}; допустимы: "
                        f"{', '.join(SERVICE_KINDS)}")
    if position_mode not in ("strict", "wide"):
        raise MazeError("position_mode: 'strict' | 'wide'")
    if cell_mm < CELL_MM:
        raise MazeError(f"клетка {cell_mm} мм меньше канонных {CELL_MM} мм — "
                        f"ребёнок не разглядит картинку")
    if GRID * cell_mm + (GRID - 1) * GAP_MM > S.CONTENT_W:
        raise MazeError(f"сетка шире полосы набора ({S.CONTENT_W} мм)")
    if route is not None and route not in ROUTES:
        raise MazeError(f"route={route!r}; есть: {', '.join(sorted(ROUTES))}")

    profile = expand_profile(profile)
    banned = C.banned_phonemes(sound, profile)
    rnd = random.Random(f"{sound}|{position}|{sorted(profile)}|{seed}|{service_cell}")
    warnings: List[str] = []

    # ── маршрут: предпочитаем тот, чьи слова-направления чисты ─────────
    clean_routes = [name for name, path in sorted(ROUTES.items())
                    if all(C.is_clean(DIR_RU[d], banned)
                           for d in _route_directions(path))]
    if route is not None:
        route_name = route
    elif clean_routes:
        route_name = rnd.choice(clean_routes)
    else:
        route_name = rnd.choice(sorted(ROUTES))
        warnings.append(
            "ни один маршрут не даёт чистых слов-направлений "
            f"(запрещено: {sorted(banned)}) — режим «С направлением» переведён "
            "на показ рукой")
    path = ROUTES[route_name]
    verify_route(path)
    dirs = _route_directions(path)
    speak_dirs = all(C.is_clean(DIR_RU[d], banned) for d in dirs)
    if route is not None and not speak_dirs:
        warnings.append(
            f"маршрут «{route_name}» задан вручную, его направления "
            f"({', '.join(sorted({DIR_RU[d] for d in dirs}))}) грязны по профилю — "
            f"режим «С направлением» переведён на показ рукой")

    # ── слова ──────────────────────────────────────────────────────────
    rows = C.load_words(_words_path(sound, words_path))
    cands, report, dropped = _candidates(
        sound, position, banned, rows, position_mode=position_mode,
        min_familiarity=min_familiarity, allow_ambiguous=allow_ambiguous,
        markova_max=markova_max)

    n_words = N_CELLS - (0 if service_cell == "none" else 1)
    if len(cands) < n_words:
        # канон разрешает одной клетке из девяти быть служебной — используем это
        # как честный запас, а не как затычку: факт попадает в warnings.
        if service_cell == "none" and len(cands) >= N_CELLS - 1:
            service_cell = "question"
            n_words = N_CELLS - 1
            warnings.append(
                "чистых слов хватило только на 8 клеток — девятая сделана "
                "служебной «?» (канон разрешает одну служебную из девяти)")
        else:
            raise MazeError(
                "лабиринт 3×3 не собрать: " +
                _shortfall(report, dropped, n_words, len(cands), position, position_mode))
    # report["shortfall"] здесь всегда велик и ничего не значит: у движка
    # запрошен ВЕСЬ словник (n=len(pre)), чтобы отбор разнообразия шёл по полному
    # полю кандидатов. Настоящий недобор ловится сравнением len(cands) выше.

    picked = _pick_diverse(cands, n_words, rnd, max_per_category, warnings)

    n_cats = len({c["category"] for c in picked})
    n_vows = len({c["vowel"] for c in picked})
    if n_cats < 4:
        warnings.append(f"разнообразие: всего {n_cats} семантических категорий "
                        f"на {n_words} слов")
    if n_vows < 2:
        warnings.append(f"разнообразие: все слова с одной гласной у целевого звука "
                        f"({picked[0]['vowel']}) — набор звучит однообразно")
    if allow_ambiguous and any(c["ambiguous"] for c in picked):
        warnings.append("в наборе есть слова с неоднозначной картинкой: "
                        + ", ".join(c["word"] for c in picked if c["ambiguous"])
                        + " — проверьте иллюстрацию глазами ребёнка")

    # ── раскладка по маршруту ──────────────────────────────────────────
    svc_order = None
    if service_cell != "none":
        # старт всегда картинка: с «?» ребёнку некуда поставить фишку
        svc_order = rnd.randrange(3, N_CELLS)
    cells: List[Dict[str, Any]] = []
    it = iter(picked)
    for order, (r, c) in enumerate(path):
        if svc_order is not None and order == svc_order:
            cells.append({
                "index": r * GRID + c, "row": r, "col": c, "order": order + 1,
                "kind": service_cell, "word": None,
                "speak": "«?»" if service_cell == "question" else "схема",
                "caption": (f"придумай слово: {POSITION_SHORT[position]}"
                            if service_cell == "question"
                            else f"слово по схеме: {POSITION_SHORT[position]}"),
            })
            continue
        w = next(it)
        cells.append({
            "index": r * GRID + c, "row": r, "col": c, "order": order + 1,
            "kind": "picture", "speak": w["word"],
            "caption": S.put_stress(w["word"], w.get("stress_syllable")),
            **w,
        })
    cells.sort(key=lambda c: c["index"])
    order_cells = sorted(cells, key=lambda c: c["order"])
    picture_cells = [c for c in order_cells if c["kind"] == "picture"]

    modes = _build_modes(order_cells, dirs, speak_dirs)
    games = _build_games(picture_cells, banned, rnd, n_games, warnings)

    legend = ("★ — старт · стрелки — путь фишки · подписи под клетками для "
              "взрослого: ребёнку показывают картинку, а не слово.")

    maze: Dict[str, Any] = {
        "meta": {
            "sound": sound,
            "position": position,
            "position_label": POSITION_LABEL[position],
            "position_mode": position_mode,
            "profile": sorted(profile),
            "banned": sorted(banned),
            "seed": seed,
            "service_cell": service_cell,
            "route": route_name,
            "route_label": ROUTE_LABEL[route_name],
            "route_clean_dirs": speak_dirs,
            "routes_clean": len(clean_routes),
            "routes_total": len(ROUTES),
            "n_pictures": len(picture_cells),
            "n_candidates": len(cands),
            "cell_mm": float(cell_mm),
            "gap_mm": GAP_MM,
            "child_name": child_name,
            "source": _words_path(sound, words_path),
        },
        "purity_scope": (
            "фильтр чистоты применён к тому, что произносит РЕБЁНОК: слова клеток · "
            "производные формы игр (мн. ч., счётные) · слова-направления маршрута. "
            "Не подпадают: заголовки, названия игр, инструкции взрослому и подписи "
            "под клетками — их читает взрослый, ребёнку показывают картинку"),
        "cells": cells,
        "route": {
            "name": route_name,
            "label": ROUTE_LABEL[route_name],
            "path": [list(p) for p in path],
            "start": list(path[0]),
            "directions": dirs,
            "directions_ru": [DIR_RU[d] for d in dirs],
            "speak_directions": speak_dirs,
        },
        "tasks": {"modes": modes, "games": games, "legend": legend},
        "selection_report": report,
        "dropped": {k: v for k, v in dropped.items() if v},
        "warnings": warnings,
    }

    _fit_tasks(maze)
    _flush_game_notes(maze)
    verify_purity(maze)                 # падает, а не предупреждает
    return maze


# ═══════════════════════════════════════════════════════════════════════
#  10. КАРТИНКА КЛЕТКИ — ЕДИНСТВЕННАЯ ТОЧКА ЗАМЕНЫ
# ═══════════════════════════════════════════════════════════════════════

_BANK = Path(__file__).resolve().parent.parent / "pictures"
OWN_PICTURES = _BANK / "objects" / "small"      # НАШИ ч/б: выкладывать можно
OWN_COLOUR = _BANK / "objects_colour" / "small"  # они же в цвете (08-18)
PICTURES = _BANK / "small"                      # чужие: только для своего экрана


def _name_forms(word: str) -> Tuple[str, ...]:
    """Имена, под которыми файл мог лечь на диск.

    macOS пишет «ё» разложенной (NFD), Linux хранит байты как есть — файл,
    созданный на ноутбуке, на хостинге не находился бы по слову из картотеки
    (она вся в NFC). Поймано 08-18 на 107 файлах: локально всё работало,
    потому что APFS сравнивает имена с нормализацией, а Railway — нет.
    """
    forms = []
    for w in (word, word.replace("ё", "е")):
        for form in ("NFC", "NFD"):
            n = unicodedata.normalize(form, w)
            if n not in forms:
                forms.append(n)
    return tuple(forms)


@lru_cache(maxsize=1024)
def _picture_data(word: str, colour: bool = False) -> str:
    """data:-URI картинки слова, если она есть в банке. Иначе пустая строка.

    Свои идут ПЕРВЫМИ и вытесняют чужую картинку того же слова: чужие лежат
    здесь временно, до конца корпуса (08-18), и выкладывать их нельзя.
    """
    banks = ((OWN_COLOUR, OWN_PICTURES) if colour else (OWN_PICTURES,))
    for bank in banks:
        for name in _name_forms(word):
            own = bank / f"{name}.png"
            if own.is_file():
                return ("data:image/png;base64,"
                        + base64.b64encode(own.read_bytes()).decode("ascii"))
    for name in (word, word.replace("ё", "е")):
        p = PICTURES / f"{name}.jpg"
        if p.is_file():
            return ("data:image/jpeg;base64,"
                    + base64.b64encode(p.read_bytes()).decode("ascii"))
    return ""


def has_picture(word: str, colour: bool = False) -> bool:
    return bool(_picture_data(word, colour))


def render_image(word: str, colour: bool = False) -> str:
    """Плейсхолдер картинки: пунктирная рамка + крупное слово + «[картинка]».

    Возвращает самодостаточный <svg viewBox="0 0 100 85">; CSS растягивает его
    на клетку. ЗАМЕНА НА НАСТОЯЩИЕ КАРТИНКИ — только здесь, например:

        return (f'<svg class="pic" viewBox="0 0 {PIC_VB_W} {PIC_VB_H}" '
                f'preserveAspectRatio="xMidYMid meet">'
                f'<image href="pictures/{word}.png" width="{PIC_VB_W}" '
                f'height="{PIC_VB_H}" preserveAspectRatio="xMidYMid meet"/></svg>')

    Пунктир — сигнал «здесь будет картинка»: страница не притворяется готовой.
    """
    w = html.escape(word, quote=False)

    # Настоящая картинка, если она есть в банке: pictures/small/<слово>.jpg.
    # Встраивается в сам SVG (data:), поэтому страница остаётся самодостаточной
    # и печатается без обращения к сети.
    pic = _picture_data(word, colour)
    if pic:
        # Поле вокруг рисунка: холст картинки квадратный, а клетка шире, чем выше,
        # поэтому по вертикали предмет упирался в рамку («роза не вошла», автор 08-18).
        pad = PIC_VB_H * PIC_PAD
        return (
            f'<svg class="pic" viewBox="0 0 {PIC_VB_W:g} {PIC_VB_H:g}" '
            f'preserveAspectRatio="xMidYMid meet" role="img" aria-label="{w}">'
            f'<image href="{pic}" x="{pad:g}" y="{pad:g}" '
            f'width="{PIC_VB_W - 2 * pad:g}" height="{PIC_VB_H - 2 * pad:g}" '
            f'preserveAspectRatio="xMidYMid meet"/>'
            f'</svg>'
        )

    fs = max(6.5, min(15.0, 92.0 / (0.55 * max(1, len(word)))))
    return (
        f'<svg class="pic" viewBox="0 0 {PIC_VB_W:g} {PIC_VB_H:g}" '
        f'preserveAspectRatio="xMidYMid meet" role="img" aria-label="{w}">'
        f'<rect x="1.5" y="1.5" width="{PIC_VB_W - 3:g}" height="{PIC_VB_H - 3:g}" '
        f'fill="none" stroke="#000" stroke-width="0.6" stroke-dasharray="3 2.4"/>'
        f'<text x="{PIC_VB_W / 2:g}" y="46" text-anchor="middle" '
        f'font-size="{fs:.1f}">{w}</text>'
        f'<text x="{PIC_VB_W / 2:g}" y="68" text-anchor="middle" font-size="6" '
        f'fill="#555">[картинка]</text>'
        f'</svg>'
    )


def _render_question(sound: str) -> str:
    """Служебная клетка «?»: ребёнок сам придумывает слово (канон)."""
    return (
        f'<svg class="pic" viewBox="0 0 {PIC_VB_W:g} {PIC_VB_H:g}" '
        f'preserveAspectRatio="xMidYMid meet" role="img" aria-label="придумай слово">'
        f'<rect x="1.5" y="1.5" width="{PIC_VB_W - 3:g}" height="{PIC_VB_H - 3:g}" '
        f'fill="none" stroke="#000" stroke-width="0.9"/>'
        f'<text x="{PIC_VB_W / 2:g}" y="58" text-anchor="middle" font-size="42">?</text>'
        f'</svg>'
    )


def _render_scheme(sound: str, position: str) -> str:
    """Служебная клетка «звуковая схема»: три окошка слова, целевое помечено
    буквой. Ребёнок придумывает слово, где звук стоит в помеченном окне."""
    idx = {"initial": 0, "medial": 1, "final": 2}[position]
    boxes = []
    for i in range(3):
        x = 12 + i * 26
        hit = (i == idx)
        boxes.append(
            f'<rect x="{x}" y="30" width="22" height="22" fill="none" '
            f'stroke="#000" stroke-width="{1.4 if hit else 0.6}"/>')
        if hit:
            boxes.append(
                f'<text x="{x + 11}" y="47" text-anchor="middle" font-size="15" '
                f'font-weight="700">{html.escape(_P.sound_label(sound))}</text>')
    return (
        f'<svg class="pic" viewBox="0 0 {PIC_VB_W:g} {PIC_VB_H:g}" '
        f'preserveAspectRatio="xMidYMid meet" role="img" aria-label="звуковая схема">'
        f'<rect x="1.5" y="1.5" width="{PIC_VB_W - 3:g}" height="{PIC_VB_H - 3:g}" '
        f'fill="none" stroke="#000" stroke-width="0.9"/>'
        + "".join(boxes) +
        f'<text x="{PIC_VB_W / 2:g}" y="70" text-anchor="middle" font-size="6" '
        f'fill="#555">звуковая схема</text>'
        f'</svg>'
    )


# ═══════════════════════════════════════════════════════════════════════
#  11. СТРЕЛКИ И ЗВЁЗДОЧКА (SVG-слой поверх сетки, координаты в мм)
# ═══════════════════════════════════════════════════════════════════════

ARROW_W = 0.45              # мм — толще волосяной: ребёнок ведёт по ней фишку
ARROW_HEAD = 2.4            # мм
ARROW_HALF = 1.5            # мм — половина ширины наконечника
STAR_R = 4.6                # мм
STAR_INSET = 6.6            # мм от угла стартовой клетки


def _cell_xy(row: int, col: int, cell: float) -> Tuple[float, float]:
    return col * (cell + GAP_MM), row * (cell + GAP_MM)


def _arrow(a: Tuple[int, int], b: Tuple[int, int], cell: float) -> str:
    ax, ay = _cell_xy(*a, cell=cell)
    d = _direction(a, b)
    pad = 0.9
    if d in ("right", "left"):
        y = ay + cell / 2
        if d == "right":
            x1, x2 = ax + cell + pad, ax + cell + GAP_MM - pad
        else:
            x1, x2 = ax - pad, ax - GAP_MM + pad
        sign = 1 if d == "right" else -1
        tip = (x2, y)
        base = (x2 - sign * ARROW_HEAD, y)
        wing1 = (base[0], y - ARROW_HALF)
        wing2 = (base[0], y + ARROW_HALF)
    else:
        x = ax + cell / 2
        if d == "down":
            y1, y2 = ay + cell + pad, ay + cell + GAP_MM - pad
        else:
            y1, y2 = ay - pad, ay - GAP_MM + pad
        sign = 1 if d == "down" else -1
        tip = (x, y2)
        base = (x, y2 - sign * ARROW_HEAD)
        wing1 = (x - ARROW_HALF, base[1])
        wing2 = (x + ARROW_HALF, base[1])
        x1, x2 = x, x
        y = None
    if d in ("right", "left"):
        line = f'<line x1="{x1:.2f}" y1="{y:.2f}" x2="{base[0]:.2f}" y2="{y:.2f}"/>'
    else:
        line = f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{base[1]:.2f}"/>'
    poly = (f'<polygon points="{tip[0]:.2f},{tip[1]:.2f} {wing1[0]:.2f},{wing1[1]:.2f} '
            f'{wing2[0]:.2f},{wing2[1]:.2f}"/>')
    return line + poly


def _star(row: int, col: int, cell: float) -> str:
    cx, cy = _cell_xy(row, col, cell)
    cx += STAR_INSET
    cy += STAR_INSET
    pts = []
    for i in range(10):
        r = STAR_R if i % 2 == 0 else STAR_R * 0.40
        ang = -math.pi / 2 + i * math.pi / 5
        pts.append(f"{cx + r * math.cos(ang):.2f},{cy + r * math.sin(ang):.2f}")
    return (f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{STAR_R + 0.9:.2f}" '
            f'fill="#fff" stroke="none"/>'
            f'<polygon points="{" ".join(pts)}" fill="#000" stroke="none"/>')


def _overlay(maze: Dict[str, Any]) -> str:
    cell = maze["meta"]["cell_mm"]
    side = GRID * cell + (GRID - 1) * GAP_MM
    path = [tuple(p) for p in maze["route"]["path"]]
    arrows = "".join(_arrow(path[i], path[i + 1], cell) for i in range(len(path) - 1))
    star = _star(path[0][0], path[0][1], cell)
    return (f'<svg class="arrows" viewBox="0 0 {side:g} {side:g}" '
            f'preserveAspectRatio="none" aria-hidden="true">'
            f'<g fill="#000" stroke="#000" stroke-width="{ARROW_W}" '
            f'stroke-linecap="round">{arrows}</g>{star}</svg>')


# ═══════════════════════════════════════════════════════════════════════
#  12. CSS  (значения дублируются в модели высоты — держать в паре)
# ═══════════════════════════════════════════════════════════════════════

def _css(cell: float) -> str:
    side = GRID * cell + (GRID - 1) * GAP_MM
    A4 = S.A4
    return f"""
@page {{ size: A4; margin: {A4['margin_top']}mm {A4['margin_right']}mm {A4['margin_bottom']}mm {A4['margin_left']}mm; }}

:root {{
  --fs-doc:  11pt;
  --fs-task: {FS_TASK}pt;
  --fs-cap:  8.5pt;
  --hair: 0.4pt solid #000;
}}

* {{ box-sizing: border-box; }}

html, body {{
  margin: 0; padding: 0; background: #fff; color: #000;
  font-family: 'PT Sans','Helvetica Neue',Arial,'Liberation Sans',sans-serif;
  font-size: var(--fs-task); line-height: {LH_TASK};
  hyphens: none; -webkit-hyphens: none; word-break: keep-all; overflow-wrap: normal;
  text-rendering: geometricPrecision;
}}

.sheet {{ width: {S.CONTENT_W}mm; }}

@media screen {{
  body {{ background: #f2f2f2; padding: 10px; }}
  .sheet {{
    width: {A4['width_mm']}mm; min-height: {A4['height_mm']}mm;
    padding: {A4['margin_top']}mm {A4['margin_right']}mm {A4['margin_bottom']}mm {A4['margin_left']}mm;
    margin: 0 auto; background: #fff; border: 1px solid #bbb;
  }}
}}
@media print {{
  .screen-only {{ display: none !important; }}
  .sheet {{ width: auto; padding: 0; border: 0; margin: 0; }}
}}

/* операторские предупреждения: экран да, бумага нет */
.warnbox {{
  max-width: {A4['width_mm']}mm; margin: 0 auto 10px; padding: 8px 12px;
  border: 1px solid #999; background: #fff; font-size: 10pt; line-height: 1.4; color: #333;
}}
.warnbox ul {{ margin: 4px 0 0; padding-left: 18px; }}

/* ── шапка ─────────────────────────────────────────────────────────── */
.doc {{ font-size: var(--fs-doc); line-height: 1.35; }}
.doc-row {{ display: flex; flex-wrap: nowrap; align-items: center; gap: 4mm; }}
.f {{ white-space: nowrap; }}
.fill {{ display: inline-block; border-bottom: var(--hair); }}
.fill-name {{ width: 46mm; }}
.fill-date {{ width: 20mm; }}
.sound-badge {{ border: var(--hair); padding: 0.2mm 1.8mm; font-weight: 700; white-space: nowrap; }}
.doc-line {{ border-bottom: var(--hair); margin-top: 0.8mm; }}

/* ── сетка 3×3 ─────────────────────────────────────────────────────── */
.maze {{
  position: relative; width: {side:g}mm; height: {side:g}mm;
  margin: {MAZE_TOP_MM}mm auto 0; break-inside: avoid; page-break-inside: avoid;
}}
.cell {{
  position: absolute; width: {cell:g}mm; height: {cell:g}mm;
  border: 0.7pt solid #000; padding: 1.2mm;
  display: flex; flex-direction: column; overflow: hidden;
}}
.pic-wrap {{ flex: 1 1 auto; min-height: 0; display: flex; align-items: center; justify-content: center; }}
.pic {{ width: 100%; height: 100%; }}
.cap {{
  flex: 0 0 auto; text-align: center; font-size: var(--fs-cap); color: #555;
  line-height: 1.15; white-space: nowrap; overflow: hidden;
}}
.cap.svc {{ white-space: normal; font-style: italic; }}
.ord {{ font-size: 7pt; color: #555; margin-right: 0.8mm; }}
.arrows {{ position: absolute; left: 0; top: 0; width: 100%; height: 100%; pointer-events: none; }}

/* ── задания взрослому ─────────────────────────────────────────────── */
.tasks {{ margin-top: {TASKS_TOP_MM}mm; border-top: var(--hair); padding-top: 1.2mm; }}
.tasks h2 {{
  margin: 0 0 0.8mm; font-size: 10pt; font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.4pt;
}}
.tcols {{ column-count: {TASK_COLS}; column-gap: {TASK_COL_GAP}mm; }}
.t {{ break-inside: avoid; margin: 0 0 0.9mm; }}
.t b {{ font-weight: 700; }}
.t .num {{
  display: inline-block; min-width: 4mm; height: 4mm; line-height: 3.7mm;
  border: var(--hair); border-radius: 50%; text-align: center;
  font-size: 7pt; font-weight: 700; margin-right: 1mm;
}}
.legend {{ margin-top: 0.8mm; font-style: italic; color: #555; break-inside: avoid; }}
"""


# ═══════════════════════════════════════════════════════════════════════
#  13. РЕНДЕР СТРАНИЦЫ
# ═══════════════════════════════════════════════════════════════════════

def _e(s: Any) -> str:
    return html.escape(str(s), quote=False)


def _cell_html(c: Dict[str, Any], maze: Dict[str, Any], colour: bool = False) -> str:
    cell = maze["meta"]["cell_mm"]
    x, y = _cell_xy(c["row"], c["col"], cell)
    if c["kind"] == "picture":
        pic = render_image(c["word"], colour)
        cap = (f'<div class="cap"><span class="ord">{c["order"]}</span>'
               f'{_e(c["caption"])}</div>')
    elif c["kind"] == "scheme":
        pic = _render_scheme(maze["meta"]["sound"], maze["meta"]["position"])
        cap = (f'<div class="cap svc"><span class="ord">{c["order"]}</span>'
               f'{_e(c["caption"])}</div>')
    else:
        pic = _render_question(maze["meta"]["sound"])
        cap = (f'<div class="cap svc"><span class="ord">{c["order"]}</span>'
               f'{_e(c["caption"])}</div>')
    return (f'<div class="cell" style="left:{x:.2f}mm;top:{y:.2f}mm">'
            f'<div class="pic-wrap">{pic}</div>{cap}</div>')


def _header_html(maze: Dict[str, Any]) -> str:
    m = maze["meta"]
    name = _e(m["child_name"]) if m["child_name"] else '<span class="fill fill-name"></span>'
    return (
        '<div class="doc">'
        '<div class="doc-row">'
        f'<span class="f sound-badge">Звук [{_e(_P.sound_label(m["sound"]))}]</span>'
        f'<span class="f">Дорожка · {_e(m["position_label"])}</span>'
        f'<span class="f">Имя: {name}</span>'
        f'<span class="f">Дата: <span class="fill fill-date"></span></span>'
        '</div>'
        '<div class="doc-line"></div>'
        '</div>'
    )


def _dot(title: str) -> str:
    """Точка после заголовка — но не после «Чего не стало?»."""
    return title if title[-1:] in "?!." else title + "."


def _tasks_html(maze: Dict[str, Any]) -> str:
    t = maze["tasks"]
    items = []
    for m in t["modes"]:
        items.append(f'<p class="t"><span class="num">{m["n"]}</span>'
                     f'<b>{_e(_dot(m["title"]))}</b> {_e(m["text"])}</p>')
    for g in t["games"]:
        items.append(f'<p class="t"><b>{_e(_dot(g["title"]))}</b> {_e(g["text"])}</p>')
    return ('<div class="tasks">'
            '<h2>Задания взрослому — к этим же девяти картинкам</h2>'
            f'<div class="tcols">{"".join(items)}</div>'
            f'<p class="legend">{_e(t["legend"])}</p>'
            '</div>')


def _warnbox_html(maze: Dict[str, Any]) -> str:
    w = list(maze.get("warnings") or [])
    if not w:
        return ""
    li = "".join(f"<li>{_e(x)}</li>" for x in w)
    return (f'<div class="warnbox screen-only"><b>Предупреждения сборщика '
            f'(на печать не идут):</b><ul>{li}</ul></div>')


def render_maze(maze: Dict[str, Any], options: Optional[Dict[str, Any]] = None) -> str:
    """Страница-лабиринт целиком: HTML под печать A4.

    options["colour"] — печатать цветные картинки вместо ч/б (08-18).
    Набор слов от этого не зависит: цвет выбирается на рендере.
    """
    options = options or {}
    cell = maze["meta"]["cell_mm"]
    colour = bool(options.get("colour"))
    cells = "".join(_cell_html(c, maze, colour) for c in maze["cells"])
    title = (f'Дорожка · звук [{_P.sound_label(maze["meta"]["sound"])}] · '
             f'{maze["meta"]["position_label"]}')
    return (
        "<!DOCTYPE html>\n"
        '<html lang="ru"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{_e(title)}</title><style>{_css(cell)}</style></head><body>"
        + ("" if options.get("no_warnbox") else _warnbox_html(maze))
        + '<div class="sheet">'
        + _header_html(maze)
        + f'<div class="maze">{cells}{_overlay(maze)}</div>'
        + _tasks_html(maze)
        + "</div></body></html>\n"
    )


# ═══════════════════════════════════════════════════════════════════════
#  14. ТЕКСТОВЫЙ ПРЕДПРОСМОТР (глазами проверить содержимое, не вёрстку)
# ═══════════════════════════════════════════════════════════════════════

def render_preview(maze: Dict[str, Any]) -> str:
    m = maze["meta"]
    lines = [
        f"ДОРОЖКА  звук [{_P.sound_label(m['sound'])}]  {m['position_label']}"
        f"  (позиция {m['position']}, режим {m['position_mode']})",
        f"профиль: {m['profile'] or 'чистый'}   запрещено: {m['banned']}",
        f"маршрут: {m['route']} — {m['route_label']}"
        f"   направления проговариваются: {'да' if m['route_clean_dirs'] else 'НЕТ'}"
        f"   (чистых маршрутов {m['routes_clean']} из {m['routes_total']})",
        f"клетка {m['cell_mm']:g}×{m['cell_mm']:g} мм · картинок {m['n_pictures']}"
        f" · кандидатов было {m['n_candidates']}",
        "",
        "СЕТКА (в скобках — номер по маршруту):",
    ]
    grid = {(c["row"], c["col"]): c for c in maze["cells"]}
    for r in range(GRID):
        row = []
        for c in range(GRID):
            cell = grid[(r, c)]
            mark = "★" if cell["order"] == 1 else " "
            name = cell["word"] or ("?" if cell["kind"] == "question" else "схема")
            row.append(f"{mark}{cell['order']}. {name:<12}")
        lines.append("   " + "".join(row))
    lines.append("")
    lines.append("ПО МАРШРУТУ: " + " → ".join(
        c["speak"] for c in sorted(maze["cells"], key=lambda c: c["order"])))
    lines.append("НАПРАВЛЕНИЯ: " + ", ".join(maze["route"]["directions_ru"]))
    lines.append("")
    lines.append("ЗАДАНИЯ ВЗРОСЛОМУ:")
    for it in maze["tasks"]["modes"]:
        lines.append(f"  [{it['n']}] {_dot(it['title'])} {it['text']}")
    for g in maze["tasks"]["games"]:
        lines.append(f"  [ ] {_dot(g['title'])} {g['text']}")
    lines.append(f"  {maze['tasks']['legend']}")
    lines.append("")
    lines.append(f"блок заданий по модели: {m['tasks_mm']} мм "
                 f"из {m['tasks_budget_mm']} мм бюджета")
    if maze["warnings"]:
        lines.append("ПРЕДУПРЕЖДЕНИЯ:")
        for w in maze["warnings"]:
            lines.append(f"  · {w}")
    else:
        lines.append("предупреждений нет")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
#  15. CLI
# ═══════════════════════════════════════════════════════════════════════

def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Страница-лабиринт 3×3 для автоматизации звука (канон Комаровой).")
    p.add_argument("--sound", default="р", help="целевой звук (пока только «р»)")
    p.add_argument("--position", default="initial", choices=list(POSITIONS),
                   help="где стоит целевой звук в слове")
    p.add_argument("--profile", default="",
                   help="нарушенные звуки ребёнка через запятую («ш,ж» или класс "
                        "«шипящие,свистящие»)")
    p.add_argument("--seed", type=int, default=0, help="зерно: маршрут, слова, игры")
    p.add_argument("--service", default="question", choices=list(SERVICE_KINDS),
                   help="служебная клетка: «?» · звуковая схема · без неё")
    p.add_argument("--route", default=None, choices=sorted(ROUTES),
                   help="задать маршрут вручную (по умолчанию — по seed)")
    p.add_argument("--position-mode", default="strict", choices=["strict", "wide"],
                   help="wide считает звук внутри начального стечения начальным (трава)")
    p.add_argument("--cell", type=float, default=CELL_MM,
                   help=f"сторона клетки в мм (не меньше {CELL_MM:g})")
    p.add_argument("--games", type=int, default=MAX_GAMES,
                   help="сколько надстроечных игр печатать (2-3)")
    p.add_argument("--allow-ambiguous", action="store_true",
                   help="разрешить слова с неоднозначной картинкой")
    p.add_argument("--min-familiarity", type=int, default=2, choices=[1, 2, 3])
    p.add_argument("--child", default="", help="имя ребёнка в шапку")
    p.add_argument("--out", default="maze.html")
    p.add_argument("--dump-json", help="сохранить структуру лабиринта в JSON")
    p.add_argument("--preview", action="store_true", help="текстовый предпросмотр в консоль")
    a = p.parse_args(argv)

    try:
        m = build_maze(sound=a.sound, position=a.position, profile=a.profile,
                       seed=a.seed, service_cell=a.service,
                       position_mode=a.position_mode, cell_mm=a.cell,
                       n_games=a.games, allow_ambiguous=a.allow_ambiguous,
                       min_familiarity=a.min_familiarity, route=a.route,
                       child_name=a.child)
    except MazeError as exc:
        print(f"лабиринт не собран: {exc}", file=sys.stderr)
        return 2

    Path(a.out).write_text(render_maze(m), encoding="utf-8")
    if a.dump_json:
        Path(a.dump_json).write_text(json.dumps(m, ensure_ascii=False, indent=2),
                                     encoding="utf-8")
    if a.preview:
        print(render_preview(m))
        print()

    mm = m["meta"]
    print(f"лист: {a.out}")
    print(f"слова: " + " → ".join(c["speak"] for c in
                                  sorted(m["cells"], key=lambda c: c["order"])))
    print(f"маршрут: {mm['route']} ({mm['route_label']}), "
          f"старт {tuple(m['route']['start'])}, "
          f"направления {'проговариваются' if mm['route_clean_dirs'] else 'показываются рукой'}")
    print(f"запрещённые фонемы: {', '.join(mm['banned'])}")
    print(f"блок заданий: {mm['tasks_mm']} мм из {mm['tasks_budget_mm']} мм")
    if m["warnings"]:
        print("предупреждения:")
        for w in m["warnings"]:
            print(f"  · {w}")
    else:
        print("предупреждений нет")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
