# -*- coding: utf-8 -*-
"""
sheet.py — ВЁРСТКА домашнего логопедического листа автоматизации (А4, ч/б).

Модуль отвечает ТОЛЬКО за печатную форму. Содержание (какие слова, слоги,
предложения) приходит извне — dict `content`. Внутри есть черновой сборщик
`build_content()` (стопгап до модуля контента), чтобы CLI работал уже сейчас.

    render_sheet(content, meta) -> str            # HTML одного листа А4
    render_sheet_ex(content, meta) -> (str, list) # то же + предупреждения

meta = {child_name, sound, sheet_no, week_from, week_to}

───────────────────────────────────────────────────────────────────────────
СКЕЛЕТ (порядок жёсткий, канон ТЗ 2026-08-01)
───────────────────────────────────────────────────────────────────────────
    [0] шапка-документ (без номера)   [4] слова колонками, два яруса
    [1] артикуляционная гимнастика    [5] игра + «Образец: …»
    [2] изолированный звук (1 строка) [6] предложения со шкалой длины
    [3] слоги одного типа + связка    [7] чистоговорка
    [8] графика — в v1 ОТСУТСТВУЕТ (осознанный вычет)
    [9] подвал взрослому (без номера, отделён линией)

───────────────────────────────────────────────────────────────────────────
СХЕМА `content` (все ключи необязательны — блок без данных не печатается)
───────────────────────────────────────────────────────────────────────────
{
  "articulation": {"items": ["Заборчик", "Маляр", ...],       # [1] 4 названия
                   "instruction": "...", "adult": "..."},
  "isolated":     {"instruction": "Заведи мотор:",            # [2] РОВНО одна строка
                   "text": "р-р-р-р-р-р"},
  "syllables":    {"type_label": "прямой открытый слог",      # [3] один тип
                   "instruction": "...",
                   "rows": [{"units": ["ра","ра","ра","ра"],
                             "word": {"word": "рама", "stress_syllable": 1}}],
                   "adult": "..."},
  "words":        {"instruction": "...",                      # [4] 12-24 слова
                   "tiers": [{"label": "а) короткие",
                              "groups": [{"header": "Ра:",
                                          "items": [{"word": "рама",
                                                     "stress_syllable": 1}]}]}]},
  "game":         {"title": "Один — много", "instruction": "...",   # [5]
                   "example": "рама — рамы", "items": ["роза", ...]},
  "sentences":    {"instruction": "...",                      # [6] 6-10 шт
                   "items": [{"text": "Рама и роза.", "n_words": 3}]},
  "chant":        {"instruction": "...",                      # [7]
                   "text": "ра-ра-ра — вот гора"},
  "footer":       ["строка", "строка", "строка"],             # [9] не более 3
  "notes":        ["сообщения сборщика содержания (недобор и т.п.)"],
}
Слово допускается и строкой ("рама") — тогда ударение просто не ставится.

───────────────────────────────────────────────────────────────────────────
ЧТО МОДУЛЬ ГАРАНТИРУЕТ ПЕЧАТЬЮ
───────────────────────────────────────────────────────────────────────────
• @page A4, поля 12/12/12/18 мм — левое шире под дырокол.
• Чистый ч/б: ни одной заливки, только контуры и волосяные линии (0.4 pt).
• Речевой материал ≥ 18 pt, текст ребёнку ≥ 16 pt, взрослому — мелкий курсив.
• hyphens:none + word-break:keep-all + nowrap на каждом слове — переносов нет.
• Обязательная «ё»: модуль ничего не заменяет на «е».
• Ударение — по полю stress_syllable, политика по умолчанию «неочевидные»
  (см. put_stress).
• Предупреждения печатаются на ЭКРАНЕ и скрыты при печати — бумага ребёнку
  остаётся чистой.

───────────────────────────────────────────────────────────────────────────
ОДИН ЛИСТ: модель влезания
───────────────────────────────────────────────────────────────────────────
Кегль НИКОГДА не уменьшается ниже минимума канона. Вместо этого работает
лестница сокращений (`fit`) — СНАЧАЛА объём внутри канонных вилок, ПОТОМ
целые блоки (порядок наш; ТЗ вилки задаёт, лестницу — нет):
    0) предложения до канонного минимума (6)
    1) слова до канонного минимума (12)
    2) слоговые строки до 16 слоговых единиц
    3) снять блок [6] предложения — потеря ступени, громкое предупреждение
    4) снять блок [5] игра
    5) сдаться и сказать об этом прямо
Каждое сокращение попадает в warnings. Высоты считаются в мм теми же
метриками, что заданы в CSS (METRICS); модель откалибрована по реальному
рендеру Chrome — расхождение по блокам ≤ 1,3 мм (`python3 fit_check.py`).

───────────────────────────────────────────────────────────────────────────
ГРАНИЦА ОТВЕТСТВЕННОСТИ
───────────────────────────────────────────────────────────────────────────
Фонемная чистота — забота сборщика содержания (phonetics.select). Здесь она
только ПРОВЕРЯЕТСЯ как линтер канона (`lint`): сквозной словарь, «Образец»,
глагол инструкции, выдуманные нормы, объёмы, вес слогового блока. Линтер
говорит предупреждениями и никогда не правит содержание молча.
Чистота требуется от речевого материала РЕБЁНКА (блоки 2,3,4,5,6,7);
подвал и пометки взрослому — обычный русский язык.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import os
import re
import sys
import unicodedata
from typing import Any, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "render_sheet", "render_sheet_ex", "fit", "lint", "put_stress",
    "estimate_heights", "compose", "from_content", "build_content",
    "A4", "METRICS", "CONTENT_H",
]

HERE = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════════════
#  1. ГЕОМЕТРИЯ И ТИПОГРАФИКА  (значения дублируются в CSS — держать в паре)
# ═══════════════════════════════════════════════════════════════════════

PT_MM = 0.352778                      # 1 типографский пункт в мм
CHAR_W = 0.50                         # средняя ширина кириллического знака в долях кегля

A4 = {
    "width_mm": 210.0,
    "height_mm": 297.0,
    "margin_top": 12.0,
    "margin_right": 12.0,
    "margin_bottom": 12.0,
    "margin_left": 18.0,              # шире — под дырокол
}
CONTENT_W = A4["width_mm"] - A4["margin_left"] - A4["margin_right"]     # 180 мм
CONTENT_H = A4["height_mm"] - A4["margin_top"] - A4["margin_bottom"]    # 273 мм

METRICS = {
    "fs_speech": 18.0,    # слоги, слова, предложения, чистоговорка — минимум канона
    "fs_body": 16.0,      # инструкции ребёнку — минимум канона
    "fs_title": 12.0,     # заголовок блока (взрослому: навигация)
    "fs_doc": 11.0,       # поля шапки-документа
    "fs_adult": 10.0,     # пометки взрослому — мелкий курсив
    "lh_speech": 1.12,
    "lh_body": 1.18,
    "lh_adult": 1.25,
    "block_gap": 1.8,     # мм между блоками
    "title_gap": 0.6,     # мм под шапкой блока
    "tick_row": 8.7,      # мм строка с клетками отметок
    "rule_gap": 1.6,      # мм на линейку + воздух
}

MAX_WORD_COLS = 4         # шире 4 колонок слова не читаются на 180 мм
MIN_WORDS = 12            # нижние границы канона — ниже сокращать нельзя
MAX_WORDS = 24
MIN_SYLLABLE_UNITS = 16
MAX_SYLLABLE_UNITS = 25
MIN_SENTENCES = 6
MAX_SENTENCES = 10

# Глаголы, которыми разрешено обращаться к ребёнку (тон канона).
CHILD_VERBS = {
    "повтори", "спой", "произнеси", "послушай", "назови", "перескажи", "отгадай",
    "прочитай",           # только как второй глагол в связке «Повтори, прочитай»
    "закончи", "договори",
}
# Служебные слова, которым разрешено быть в предложениях помимо блока [4].
FUNCTION_WORDS = {"вот", "тут", "и", "а", "да", "не", "у", "на", "в", "с",
                  "два", "три", "много"}

NUM_WORDS_LABEL = {
    2: "Два слова", 3: "Три слова", 4: "Четыре слова",
    5: "Пять слов", 6: "Шесть слов", 7: "Семь слов",
}

VOWELS = "аеёиоуыэюя"
ACUTE = "́"          # комбинирующее ударение


# ═══════════════════════════════════════════════════════════════════════
#  2. УДАРЕНИЕ
# ═══════════════════════════════════════════════════════════════════════

def put_stress(word: str, stress_syllable: Optional[int],
               policy: str = "non_obvious") -> str:
    """Ставит знак ударения над гласной stress_syllable-го слога.

    policy:
      'non_obvious' (по умолчанию) — метит только там, где ударение не читается
          само: пропускает односложные, слова с «ё» (она всегда ударна) и
          двусложные с ударением на первом слоге (самый частый случай).
      'all'  — метит везде, где слогов больше одного и нет «ё».
      'none' — не метит.
    """
    if policy == "none" or not word or not stress_syllable:
        return word
    low = word.lower()
    vpos = [i for i, ch in enumerate(low) if ch in VOWELS]
    if len(vpos) < 2 or "ё" in low:
        return word
    if policy == "non_obvious" and len(vpos) == 2 and stress_syllable == 1:
        return word
    if not (1 <= stress_syllable <= len(vpos)):
        return word
    i = vpos[stress_syllable - 1]
    return word[: i + 1] + ACUTE + word[i + 1:]


def _strip_marks(s: str) -> str:
    return unicodedata.normalize("NFC", s).replace(ACUTE, "")


# ═══════════════════════════════════════════════════════════════════════
#  3. МОДЕЛЬ ВЫСОТЫ (мм) — те же метрики, что в CSS
# ═══════════════════════════════════════════════════════════════════════

def _line(fs: float, lh: float) -> float:
    return fs * lh * PT_MM


def _speech_line() -> float:
    return _line(METRICS["fs_speech"], METRICS["lh_speech"])


def _body_line() -> float:
    return _line(METRICS["fs_body"], METRICS["lh_body"])


def _adult_line() -> float:
    return _line(METRICS["fs_adult"], METRICS["lh_adult"])


def _head_line(block: Optional[Dict[str, Any]] = None, title: str = "") -> float:
    """Шапка блока: номер + название + инструкция ребёнку на ОДНОЙ строке.
    Высоту задаёт самый крупный кегль строки — инструкция (fs_body).
    Если строка длинная — она переносится, и это учитывается."""
    b = block or {}
    width_pt = (len(title) * METRICS["fs_title"] * CHAR_W
                + len(str(b.get("type_label") or b.get("title") or ""))
                * METRICS["fs_adult"] * CHAR_W
                + len(str(b.get("instruction") or "")) * METRICS["fs_body"] * CHAR_W)
    lines = max(1, math.ceil(width_pt * PT_MM / (CONTENT_W - 8)))   # −8 мм на номер
    return lines * _body_line() + METRICS["title_gap"]


def _wrap(text: Any, fs: float, width_mm: float = CONTENT_W) -> int:
    """Сколько строк займёт текст при данном кегле и ширине."""
    if not text:
        return 0
    per = max(8, int(width_mm / (fs * CHAR_W * PT_MM)))
    return max(1, math.ceil(len(str(text)) / per))


def _word_text(item: Any) -> str:
    return item if isinstance(item, str) else str(item.get("word", ""))


def _words_flat(words: Dict[str, Any]) -> List[Any]:
    out: List[Any] = []
    for tier in words.get("tiers", []):
        for grp in tier.get("groups", []):
            out.extend(grp.get("items", []))
    return out


def _syllable_units(syl: Dict[str, Any]) -> int:
    return sum(len(r.get("units", [])) for r in syl.get("rows", []))


def _syl_row_text(r: Dict[str, Any]) -> str:
    """Как строка [3] выглядит на бумаге: единицы + связка «слог — слово»."""
    units = " ".join(str(u) for u in r.get("units", []))
    w = r.get("word")
    if not w:
        return units
    wt = _word_text(w)
    bond = r.get("bond_syllable")
    tail = f"{bond} — {wt}" if bond else wt
    return f"{units}   {tail}"


def _syl_columns(syl: Dict[str, Any]) -> int:
    """2 печатные колонки или 1 — решает самая длинная строка (перенос запрещён)."""
    longest = max((len(_syl_row_text(r)) for r in syl.get("rows", [])), default=0)
    need = longest * METRICS["fs_speech"] * CHAR_W * PT_MM
    return 2 if need <= (CONTENT_W - 9.0) / 2 else 1


def _cols_by_width(longest_chars: int, extra_chars: int = 0) -> int:
    """Сколько колонок влезает по ширине: перенос запрещён, значит колонка
    обязана вместить самое длинное слово целиком (плюс метку яруса «а) »)."""
    need_mm = ((longest_chars + extra_chars) * METRICS["fs_speech"] * CHAR_W * PT_MM
               + 2.0)
    n = MAX_WORD_COLS
    while n > 1 and (CONTENT_W - 4.0 * (n - 1)) / n < need_mm:
        n -= 1
    return n


_TIER_LETTER = re.compile(r"\s*([абв])\)")


def word_segments(words: Dict[str, Any]) -> Tuple[int, List[Dict[str, Any]], bool]:
    """Раскладка блока [4] в колонки. Возвращает (колонок, сегменты, метки?).

    ЯРУСЫ НЕ ДЕЛЯТ ЛИСТ НАДВОЕ. Канон ТЗ показывает ярусы ВНУТРИ слоговой
    колонки — «Ру: а) рука  б) ручка, рукав, рукавица», а не двумя отдельными
    сетками. Две сетки стоили лишней строки-подписи на ярус и, главное,
    заставляли каждую сетку быть высотой с самую глубокую свою колонку: 11 слов
    занимали 9 строк. Здесь ярусы сливаются по заголовку (порядок а→б внутри
    колонки сохранён и виден по метке), а слишком глубокая колонка разрезается
    на соседнюю с тем же заголовком — колонки выходят ровными.
    """
    order: List[str] = []
    merged: Dict[str, List[Dict[str, Any]]] = {}
    letters: set = set()
    for tier in words.get("tiers", []):
        m = _TIER_LETTER.match(str(tier.get("label") or ""))
        letter = m.group(1) if m else ""
        for g in tier.get("groups", []):
            h = str(g.get("header", ""))
            if h not in merged:
                merged[h] = []
                order.append(h)
            for it in g.get("items", []):
                merged[h].append({"item": it, "tier": letter})
                letters.add(letter)

    plain: List[Dict[str, Any]] = [{"header": h, "items": merged[h]}
                                   for h in order if merged[h]]
    show_marks = len(letters - {""}) > 1
    longest = max((len(_word_text(x["item"])) for s in plain for x in s["items"]),
                  default=0)
    ncol = _cols_by_width(longest, 3 if show_marks else 0)

    # разрезать самую глубокую колонку, пока есть свободные колонки
    segs = [dict(s) for s in plain]
    while len(segs) < ncol:
        i = max(range(len(segs)), key=lambda k: len(segs[k]["items"]))
        if len(segs[i]["items"]) < 4:            # мельче 4 резать бессмысленно
            break
        half = (len(segs[i]["items"]) + 1) // 2
        rest = segs[i]["items"][half:]
        segs[i] = dict(segs[i], items=segs[i]["items"][:half])
        segs.insert(i + 1, {"header": segs[i]["header"], "items": rest, "cont": True})

    # разрез повторяет заголовок в соседней колонке — за это платим ясностью,
    # поэтому берём его, только если он экономит не меньше двух строк
    if _seg_lines(segs, ncol) > _seg_lines(plain, ncol) - 2:
        segs = plain
    return (min(ncol, len(segs)) or 1), segs, show_marks


def _seg_lines(segs: List[Dict[str, Any]], ncol: int) -> int:
    n = min(ncol, len(segs)) or 1
    return sum(1 + max(len(s["items"]) for s in segs[i:i + n])
               for i in range(0, len(segs), n))


def _words_body_height(words: Dict[str, Any]) -> float:
    ncol, segs, _ = word_segments(words)
    return _seg_lines(segs, ncol) * _speech_line()


def estimate_heights(content: Dict[str, Any]) -> Dict[str, float]:
    """Оценка высоты каждого блока в мм. Ключи — как в content + '_header'/'_footer'."""
    g = METRICS["block_gap"]
    h: Dict[str, float] = {}

    # [0] шапка: строка полей + строка клеток отметок + линейка
    h["_header"] = (_line(METRICS["fs_doc"], 1.35) + METRICS["tick_row"]
                    + METRICS["rule_gap"] + g)

    art = content.get("articulation")
    if art:
        # поток с переносом: считаем реальные ширины имён + галочка + зазор
        box_mm = 4.2 + 1.6 + 7.0                              # квадрат + отступ + gap
        rows, line = 1, 0.0
        for x in art.get("items", []):
            w = len(str(x)) * METRICS["fs_body"] * CHAR_W * PT_MM + box_mm
            if line and line + w > CONTENT_W:
                rows, line = rows + 1, w
            else:
                line += w
        h["articulation"] = (_head_line(art, "Разминка") + rows * _body_line()
                             + _wrap(art.get("adult"), METRICS["fs_adult"]) * _adult_line()
                             + g)

    iso = content.get("isolated")
    if iso:
        h["isolated"] = (_speech_line() + METRICS["title_gap"] + g
                         + _wrap(iso.get("adult"), METRICS["fs_adult"]) * _adult_line())

    syl = content.get("syllables")
    if syl:
        rows = math.ceil(len(syl.get("rows", [])) / _syl_columns(syl))
        h["syllables"] = (_head_line(syl, "Слоги") + rows * _speech_line()
                          + _wrap(syl.get("adult"), METRICS["fs_adult"]) * _adult_line()
                          + g)

    words = content.get("words")
    if words and _words_flat(words):
        h["words"] = _head_line(words, "Слова") + g + _words_body_height(words)

    game = content.get("game")
    if game:
        rows = math.ceil(len(game.get("items", [])) / 3)      # 3 колонки
        h["game"] = (_head_line(game, "Игра")
                     + _wrap(game.get("example"), METRICS["fs_speech"]) * _speech_line()
                     + rows * _speech_line() + g)

    sent = content.get("sentences")
    if sent:
        tot = _head_line(sent, "Предложения") + g
        for it in sent.get("items", []):
            tot += _wrap(it.get("text"), METRICS["fs_speech"],
                         CONTENT_W - 29) * _speech_line()     # минус колонка шкалы
        h["sentences"] = tot

    chant = content.get("chant")
    if chant:
        h["chant"] = (_head_line(chant, "Чистоговорка")
                      + _wrap(chant.get("text"), METRICS["fs_speech"]) * _speech_line()
                      + 2.4 + g)                              # + рамка и поля

    foot = content.get("footer")
    if foot:
        h["_footer"] = (METRICS["rule_gap"] + 1.0
                        + sum(_wrap(x, METRICS["fs_adult"]) for x in foot[:3])
                        * _adult_line())
    return h


def total_height(content: Dict[str, Any]) -> float:
    return sum(estimate_heights(content).values())


# ═══════════════════════════════════════════════════════════════════════
#  4. ЛЕСТНИЦА СОКРАЩЕНИЙ
# ═══════════════════════════════════════════════════════════════════════

def fit(content: Dict[str, Any], budget_mm: float = CONTENT_H
        ) -> Tuple[Dict[str, Any], List[str]]:
    """Ужимает content до одного А4, НЕ трогая кегль. Возвращает (content, warnings).

    ПОРЯДОК СОКРАЩЕНИЙ — наше решение, а не буква ТЗ (ТЗ лестницы не содержит,
    он задаёт только вилки объёмов: слов 12-24 · слогов 16-25 · предложений
    6-10). Принцип: СНАЧАЛА объём внутри канонной вилки, ПОТОМ целые блоки.
    Раньше блок [6] снимался вторым — лист терял целую ступень, чтобы сохранить
    24 слова; это противоречит сути ТЗ (у Комаровой слова 25 % и фразы 16 %
    стоят ОБА, а раздувается только самое дешёвое — и канон запрещает именно
    это). Целые блоки снимаются последними и всегда громко.
    """
    c = json.loads(json.dumps(content, ensure_ascii=False))   # глубокая копия
    warns: List[str] = []
    if total_height(c) <= budget_mm:
        return c, warns

    # 0) предложения — до канонного минимума 6
    sent = c.get("sentences") or {}
    while len(sent.get("items", [])) > MIN_SENTENCES:
        sent["items"].pop()
        if total_height(c) <= budget_mm:
            warns.append(f"не влезало: предложений оставлено {len(sent['items'])} "
                         f"(канон 6-10)")
            return c, warns

    # 1) слова — до канонного минимума 12
    words = c.get("words") or {}
    n0 = len(_words_flat(words))
    for tier in reversed(words.get("tiers", [])):
        for grp in reversed(tier.get("groups", [])):
            while grp.get("items") and len(_words_flat(words)) > MIN_WORDS:
                grp["items"].pop()
                if total_height(c) <= budget_mm:
                    _drop_empty(words)
                    warns.append(f"не влезало: слов оставлено "
                                 f"{len(_words_flat(words))} из {n0} (канон 12-24)")
                    return c, warns
    _drop_empty(words)

    # 2) слоговые строки — не ниже 16 единиц
    syl = c.get("syllables") or {}
    while len(syl.get("rows", [])) > 1 and _syllable_units(syl) > MIN_SYLLABLE_UNITS:
        syl["rows"].pop()
        if total_height(c) <= budget_mm:
            warns.append(f"не влезало: слоговых строк оставлено "
                         f"{len(syl['rows'])} ({_syllable_units(syl)} единиц)")
            return c, warns

    # 3) снять блок [6] предложения — это уже потеря ступени, а не объёма
    if c.get("sentences"):
        c.pop("sentences")
        warns.append("НЕ ВЛЕЗАЛО: снят блок [6] предложения — лист потерял ступень "
                     "«слово → фраза». Уберите материал на входе "
                     "(меньше слоговых строк или короче подвал).")
        if total_height(c) <= budget_mm:
            return c, warns

    # 4) снять блок [5] игра
    if c.get("game"):
        c.pop("game")
        warns.append("НЕ ВЛЕЗАЛО: снят блок [5] игра")
        if total_height(c) <= budget_mm:
            return c, warns

    # 5) сдаться честно
    warns.append(f"НЕ ВЛЕЗАЕТ: не хватает {total_height(c) - budget_mm:.0f} мм даже "
                 f"после всех сокращений. Кегль не уменьшаю (канон: ≥16/18 pt) — "
                 f"уберите материал на входе.")
    return c, warns


def _drop_empty(words: Dict[str, Any]) -> None:
    for tier in words.get("tiers", []):
        tier["groups"] = [x for x in tier.get("groups", []) if x.get("items")]
    words["tiers"] = [t for t in words.get("tiers", []) if t.get("groups")]


# ═══════════════════════════════════════════════════════════════════════
#  5. ЛИНТЕР КАНОНА (говорит, но не правит)
# ═══════════════════════════════════════════════════════════════════════

_FAKE_NORM = re.compile(r"\d+\s*(раз|раза|день|дня|дней|недел)", re.I)
_TOKEN = re.compile(r"[а-яёА-ЯЁ]+")


def _material_mm(content: Dict[str, Any]) -> Tuple[float, float]:
    """(слоговой материал, словесный материал) в мм — БЕЗ шапок и пометок."""
    syl = content.get("syllables") or {}
    syl_mm = (math.ceil(len(syl.get("rows", [])) / _syl_columns(syl)) * _speech_line()
              if syl.get("rows") else 0.0)

    words = content.get("words") or {}
    word_mm = _words_body_height(words) if _words_flat(words) else 0.0

    game = content.get("game") or {}
    if game:
        word_mm += _wrap(game.get("example"), METRICS["fs_speech"]) * _speech_line()
        word_mm += math.ceil(len(game.get("items", [])) / 3) * _speech_line()

    for it in (content.get("sentences") or {}).get("items", []):
        word_mm += _wrap(it.get("text"), METRICS["fs_speech"],
                         CONTENT_W - 29) * _speech_line()

    chant = content.get("chant") or {}
    if chant.get("text"):
        word_mm += _wrap(chant["text"], METRICS["fs_speech"]) * _speech_line()
    return syl_mm, word_mm


def _first_verb_ok(instruction: str) -> bool:
    m = _TOKEN.search(instruction or "")
    return bool(m) and m.group(0).lower() in CHILD_VERBS


def _in_sweep_vocab(token: str, base: List[str]) -> bool:
    """Мягкая проверка сквозного словаря: словоформа считается своей, если делит
    с каким-то словом блока [4] почти весь корень (допуск на окончание)."""
    t = _strip_marks(token.lower())
    if t in FUNCTION_WORDS:
        return True
    for w in base:
        w = _strip_marks(w.lower())
        common = 0
        for a, b in zip(t, w):
            if a != b:
                break
            common += 1
        if common >= max(3, len(w) - 2):
            return True
    return False


def lint(content: Dict[str, Any], meta: Dict[str, Any]) -> List[str]:
    """Проверки канона, которые видны из готового содержания листа."""
    out: List[str] = []
    words = content.get("words") or {}
    base = [_word_text(i) for i in _words_flat(words)]

    if base and not (MIN_WORDS <= len(base) <= MAX_WORDS):
        out.append(f"канон [4]: слов {len(base)}, норма {MIN_WORDS}-{MAX_WORDS}")

    syl = content.get("syllables") or {}
    if syl:
        u = _syllable_units(syl)
        if not (MIN_SYLLABLE_UNITS <= u <= MAX_SYLLABLE_UNITS):
            out.append(f"канон [3]: слоговых единиц {u}, норма "
                       f"{MIN_SYLLABLE_UNITS}-{MAX_SYLLABLE_UNITS}")
        if not (4 <= len(syl.get("rows", [])) <= 6):
            out.append(f"канон [3]: строк {len(syl.get('rows', []))}, норма 4-6")
        if any(not r.get("word") for r in syl.get("rows", [])):
            out.append("канон правило 7: слоговая строка без связки со словом")

    sent = content.get("sentences") or {}
    if sent and not (MIN_SENTENCES <= len(sent.get("items", [])) <= MAX_SENTENCES):
        out.append(f"канон [6]: предложений {len(sent.get('items', []))}, "
                   f"норма {MIN_SENTENCES}-{MAX_SENTENCES}")

    # правило 11 — вес слогового блока.
    # Меряем МАТЕРИАЛ, а не блоки целиком: заголовок, инструкция и пометка
    # взрослому есть у КАЖДОГО блока и к «объёму слогового материала» отношения
    # не имеют. Сравнение блоков целиком штрафовало слоговой блок за его же
    # мебель и валило совершенно нормальные листы со стечениями.
    syl_mm, word_mm = _material_mm(content)
    if syl_mm and word_mm and syl_mm > 0.25 * word_mm:
        out.append(f"канон правило 11: слоговой материал {syl_mm:.0f} мм > ¼ "
                   f"словесного ({word_mm:.0f} мм) — сократите слоги")

    # правило 2 — изолированный звук ровно одной строкой
    iso = content.get("isolated") or {}
    if iso and ("\n" in str(iso.get("text", ""))
                or _wrap(f"{iso.get('instruction','')} {iso.get('text','')}",
                         METRICS["fs_speech"]) > 1):
        out.append("канон [2]: изолированный звук должен быть РОВНО одной строкой")

    # правило 14 — «Образец: …»
    game = content.get("game") or {}
    if game and not game.get("example"):
        out.append("канон правило 14: у игры [5] нет строки «Образец: …»")

    # правила 15/16 — инструкция ребёнку
    for key in ("articulation", "syllables", "words", "game", "sentences", "chant"):
        ins = (content.get(key) or {}).get("instruction")
        if ins and not _first_verb_ok(ins):
            out.append(f"канон правило 15/16: инструкция блока «{key}» не начинается "
                       f"глаголом канона — «{ins}»")

    # правило 13 — сквозной словарь.
    # Если содержание пришло с объявленным словарём (content.py), проверяем
    # СТРОГО: каждая словоформа обязана быть в block4 ∪ derived ∪ service ∪
    # syllables. Без словаря остаётся мягкая проверка по общему корню.
    voc = content.get("vocabulary") or {}
    if voc:
        allowed = {_strip_marks(str(x).lower())
                   for x in (list(voc.get("block4", []))
                             + list(voc.get("derived", {}).keys())
                             + list(voc.get("service", []))
                             + list(voc.get("syllables", [])))}
        ok = lambda t: _strip_marks(t.lower()) in allowed        # noqa: E731
    elif base:
        ok = lambda t: _in_sweep_vocab(t, base)                  # noqa: E731
    else:
        ok = None
    if ok:
        stray: List[str] = []
        for it in sent.get("items", []):
            stray += [t for t in _TOKEN.findall(it.get("text", "")) if not ok(t)]
        pool = list(game.get("items", []))
        if game.get("example"):
            pool.append(game["example"])
        for it in pool:
            stray += [t for t in _TOKEN.findall(str(it)) if not ok(t)]
        chant_text = (content.get("chant") or {}).get("text", "")
        if voc:                       # строгий режим проверяет и слоговый зачин
            stray += [t for t in _TOKEN.findall(chant_text) if not ok(t)]
        else:
            stray += [t for t in _TOKEN.findall(chant_text.split("—")[-1]) if not ok(t)]
        if stray:
            out.append("канон правило 13 (сквозной словарь): вне блока [4] — "
                       + ", ".join(sorted(set(stray))[:8]))

    # правило 24 — выдуманные нормы
    for m in sorted(set(_FAKE_NORM.findall(json.dumps(content, ensure_ascii=False)))):
        out.append(f"канон правило 24: похоже на выдуманную норму («…{m}»)")

    if not meta.get("sound"):
        out.append("шапка: не указан целевой звук")
    return out


# ═══════════════════════════════════════════════════════════════════════
#  6. CSS
# ═══════════════════════════════════════════════════════════════════════

def _css(options: Dict[str, Any]) -> str:
    m = METRICS
    words_font = ("'PT Mono','DejaVu Sans Mono','Courier New',monospace"
                  if options.get("words_mono") else "inherit")
    return f"""
@page {{ size: A4; margin: {A4['margin_top']}mm {A4['margin_right']}mm {A4['margin_bottom']}mm {A4['margin_left']}mm; }}

:root {{
  --fs-speech: {m['fs_speech']}pt;
  --fs-body:   {m['fs_body']}pt;
  --fs-title:  {m['fs_title']}pt;
  --fs-doc:    {m['fs_doc']}pt;
  --fs-adult:  {m['fs_adult']}pt;
  --hair: 0.4pt solid #000;
  --gap: {m['block_gap']}mm;
}}

* {{ box-sizing: border-box; }}

html, body {{
  margin: 0; padding: 0;
  background: #fff; color: #000;
  font-family: 'PT Sans','Helvetica Neue',Arial,'Liberation Sans',sans-serif;
  font-size: var(--fs-body);
  line-height: {m['lh_body']};
  /* канон печати: переносов нет ни при каких обстоятельствах */
  hyphens: none; -webkit-hyphens: none; -moz-hyphens: none;
  word-break: keep-all;
  overflow-wrap: normal;
  text-rendering: geometricPrecision;
}}

.sheet {{ width: {CONTENT_W}mm; }}

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
  border: 1px solid #999; background: #fff;
  font-size: 10pt; line-height: 1.4; color: #333;
}}
.warnbox ul {{ margin: 4px 0 0; padding-left: 18px; }}

/* ── [0] шапка-документ ────────────────────────────────────────────── */
.doc {{ font-size: var(--fs-doc); line-height: 1.35; }}
.doc-row {{ display: flex; flex-wrap: nowrap; align-items: center; gap: 4mm; }}
.f {{ white-space: nowrap; }}
.fill {{ display: inline-block; border-bottom: var(--hair); }}
.fill-name {{ width: 50mm; }}
.fill-no   {{ width: 11mm; }}
.fill-date {{ width: 16mm; }}
.fill-sign {{ width: 34mm; }}
.sound-badge {{ border: var(--hair); padding: 0.2mm 1.8mm; font-weight: 700; white-space: nowrap; }}

.ticks {{ display: flex; gap: 1.5mm; }}
.tick {{ text-align: center; }}
.tick i {{ display: block; width: 6.2mm; height: 6.2mm; border: var(--hair); border-radius: 0.6mm; }}
.tick s {{ display: block; font-size: 6.5pt; text-decoration: none; color: #444; line-height: 1.15; }}
.doc-line {{ border-bottom: var(--hair); margin-top: {m['rule_gap'] / 2}mm; }}

/* ── общий блок: номер + название + инструкция ребёнку в одной строке ─ */
.block {{ margin-top: var(--gap); break-inside: avoid; page-break-inside: avoid; }}
.bhead {{
  display: flex; align-items: baseline; gap: 2mm;
  margin-bottom: {m['title_gap']}mm;
}}
.bnum {{
  flex: 0 0 auto; width: 5mm; height: 5mm; line-height: 4.7mm;
  border: var(--hair); border-radius: 50%; text-align: center;
  font-size: 8.5pt; font-weight: 700;
}}
.btitle {{
  font-size: var(--fs-title); font-weight: 700;
  text-transform: uppercase; letter-spacing: 0.4pt; white-space: nowrap;
}}
.bhint {{ font-size: var(--fs-adult); font-style: italic; color: #555; white-space: nowrap; }}
.task {{ font-size: var(--fs-body); }}
.adult {{ font-size: var(--fs-adult); font-style: italic; color: #555; margin: 0; }}

/* ── [1] гимнастика: имена упражнений разной длины («Почистим верхние
      зубы» вдвое шире «Маляра»), поэтому не сетка равных колонок, а поток
      с переносом — при длинных именах строка честно становится второй ─── */
.artic {{ display: flex; flex-wrap: wrap; column-gap: 7mm; row-gap: 0; }}
.artic div {{ white-space: nowrap; }}
.box {{
  display: inline-block; width: 4.2mm; height: 4.2mm;
  border: var(--hair); margin-right: 1.6mm; vertical-align: -0.4mm;
}}

/* ── [2] изолированный звук ───────────────────────────────────────── */
.iso {{ font-size: var(--fs-speech); white-space: nowrap; }}
.iso b {{ letter-spacing: 1pt; }}

/* ── [3] слоги: 2 печатные колонки, поток сверху вниз (порядок строк
      канона сохранён: сначала вся левая колонка, потом правая) ───────── */
/* зазор между печатными колонками ШИРЕ, чем между рядом и его связкой, —
   иначе «ра ро ру ры  ра — рак | ру ры ра ро  ру — рука» читается как одна
   длинная строка и связка теряет хозяина */
.syl {{
  column-count: 2; column-gap: 9mm;
  font-size: var(--fs-speech); line-height: {m['lh_speech']};
}}
.syl-row {{ white-space: nowrap; break-inside: avoid; }}
.syl-units {{ letter-spacing: 0.6pt; }}
.syl-bond {{ margin-left: 4mm; }}
.syl-bond::before {{ content: ""; }}

/* ── [4] слова колонками по гласному ──────────────────────────────── */
.tier-label {{ font-size: var(--fs-adult); font-style: italic; color: #555; }}
.tmark {{ font-size: var(--fs-adult); color: #555; }}
.wcols {{ display: grid; gap: 0 4mm; }}
.wcol-h {{
  font-size: var(--fs-speech); line-height: {m['lh_speech']};
  font-weight: 700; border-bottom: var(--hair); white-space: nowrap;
}}
/* колонка-продолжение того же слога: заголовок повторён, но не жирный —
   глаз читает жирный как начало группы, светлый как её хвост */
.wcol-h.cont {{ font-weight: 400; color: #444; }}
.wcol-h.cont::before {{ content: "…"; margin-right: 0.6mm; }}
.w {{
  font-size: var(--fs-speech); line-height: {m['lh_speech']};
  white-space: nowrap; font-family: {words_font};
}}

/* ── [5] игра: слова образца и заданий ребёнок ПРОИЗНОСИТ, значит это
      речевой материал — кегль тот же, что у слов и предложений (18 pt),
      а не «текст ребёнку» (16 pt) ─────────────────────────────────────── */
.sample {{ font-size: var(--fs-speech); line-height: {m['lh_speech']}; }}
.game {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 0 4mm;
        font-size: var(--fs-speech); line-height: {m['lh_speech']}; }}
.game div {{ white-space: nowrap; }}
.blank {{ display: inline-block; width: 18mm; border-bottom: var(--hair); }}

/* ── [6] предложения со шкалой длины ──────────────────────────────── */
.sent {{ display: grid; grid-template-columns: 25mm 1fr; gap: 0 4mm; align-items: baseline; }}
.sent .lab {{ font-size: var(--fs-adult); font-style: italic; color: #555; white-space: nowrap; }}
.sent .txt {{ font-size: var(--fs-speech); line-height: {m['lh_speech']}; }}

/* ── [7] чистоговорка ─────────────────────────────────────────────── */
.chant {{
  font-size: var(--fs-speech); line-height: {m['lh_speech']};
  border: var(--hair); padding: 0.8mm 2.4mm; display: inline-block;
}}

/* ── [9] подвал взрослому ─────────────────────────────────────────── */
.foot {{
  margin-top: var(--gap); border-top: var(--hair); padding-top: 1.0mm;
  font-size: var(--fs-adult); font-style: italic; color: #444;
  line-height: {m['lh_adult']};
}}
"""


# ═══════════════════════════════════════════════════════════════════════
#  7. РЕНДЕР БЛОКОВ
# ═══════════════════════════════════════════════════════════════════════

def _e(s: Any) -> str:
    return html.escape(str(s), quote=False)


def _stress_lookup(content: Dict[str, Any]) -> Dict[str, int]:
    """word -> stress_syllable по блоку [4]: чтобы ударения в предложениях,
    игре и чистоговорке совпадали со словарём листа, а не жили отдельно."""
    out: Dict[str, int] = {}
    for i in _words_flat(content.get("words") or {}):
        if isinstance(i, dict) and i.get("stress_syllable"):
            out[_strip_marks(str(i["word"])).lower()] = int(i["stress_syllable"])
    return out


def _mark_text(text: str, lookup: Dict[str, int], policy: str) -> str:
    """Проставить ударения в связном тексте по словарю блока [4]."""
    if not text or not lookup:
        return text

    def sub(m: "re.Match") -> str:
        tok = m.group(0)
        st = lookup.get(_strip_marks(tok).lower())
        if not st:
            return tok
        marked = put_stress(tok.lower(), st, policy)
        return marked.capitalize() if tok[:1].isupper() else marked

    return _TOKEN.sub(sub, text)


def _head(num: Optional[str], title: str, hint: str = "", task: str = "",
          extra: str = "") -> str:
    n = f'<span class="bnum">{_e(num)}</span>' if num else ""
    h = f'<span class="bhint">{_e(hint)}</span>' if hint else ""
    t = f'<span class="task">{_e(task)}</span>' if task else ""
    return (f'<div class="bhead">{n}<span class="btitle">{_e(title)}</span>'
            f'{h}{t}{extra}</div>')


# Подпись звука для человека («р'» → «Рь») живёт в phonetics.py — там же, где
# классы мягкости. Здесь только ссылка, чтобы правило имело один дом.
from phonetics import sound_label            # noqa: E402


def _b0_header(meta: Dict[str, Any]) -> str:
    sound = sound_label(meta.get("sound", ""))
    days = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    ticks = "".join(f'<div class="tick"><i></i><s>{d}</s></div>' for d in days)
    return f"""<div class="doc">
  <div class="doc-row">
    <span class="f">Ребёнок <span class="fill fill-name">{_e(meta.get('child_name') or '')}</span></span>
    <span class="f sound-badge">Звук [{_e(sound)}]</span>
    <span class="f">{_e(meta.get('step_label') or '')}</span>
    <span class="f">Неделя с <span class="fill fill-date">{_e(meta.get('week_from') or '')}</span> по <span class="fill fill-date">{_e(meta.get('week_to') or '')}</span></span>
  </div>
  <div class="doc-row">
    <span class="f">Отметки:</span>
    <div class="ticks">{ticks}</div>
    <span class="f">Подпись взрослого <span class="fill fill-sign"></span></span>
  </div>
  <div class="doc-line"></div>
</div>"""


def _b1_articulation(b: Dict[str, Any]) -> str:
    items = "".join(f'<div><span class="box"></span>{_e(x)}</div>'
                    for x in b.get("items", []))
    adult = f'<div class="adult">{_e(b["adult"])}</div>' if b.get("adult") else ""
    return (f'<section class="block">'
            f'{_head("1", "Разминка", b.get("hint", ""), b.get("instruction", ""))}'
            f'<div class="artic">{items}</div>{adult}</section>')


def _b2_isolated(b: Dict[str, Any]) -> str:
    line = (f'<span class="iso">{_e(b.get("instruction", ""))} '
            f'<b>{_e(b.get("text", ""))}</b></span>')
    adult = f'<div class="adult">{_e(b["adult"])}</div>' if b.get("adult") else ""
    return (f'<section class="block">{_head("2", "Звук", "", "", line)}'
            f'{adult}</section>')


def _b3_syllables(b: Dict[str, Any], sp: str) -> str:
    rows = []
    for r in b.get("rows", []):
        units = " ".join(_e(u) for u in r.get("units", []))
        w = r.get("word")
        link = ""
        if w:
            wt = put_stress(_word_text(w),
                            w.get("stress_syllable") if isinstance(w, dict) else None, sp)
            bond = r.get("bond_syllable")
            head = f'{_e(bond)} — ' if bond else ""
            link = f'<span class="syl-bond">{head}{_e(wt)}</span>'
        rows.append(f'<div class="syl-row"><span class="syl-units">{units}</span>{link}</div>')
    adult = f'<div class="adult">{_e(b["adult"])}</div>' if b.get("adult") else ""
    ncol = _syl_columns(b)
    return (f'<section class="block">'
            f'{_head("3", "Слоги", b.get("type_label", ""), b.get("instruction", ""))}'
            f'<div class="syl" style="column-count:{ncol}">{"".join(rows)}</div>'
            f'{adult}</section>')


def _b4_words(b: Dict[str, Any], sp: str) -> str:
    ncol, segs, marks = word_segments(b)
    cols = []
    for s in segs:
        prev = None
        items = []
        for x in s["items"]:
            it, letter = x["item"], x.get("tier") or ""
            wt = put_stress(_word_text(it),
                            it.get("stress_syllable") if isinstance(it, dict) else None,
                            sp)
            mark = (f'<span class="tmark">{_e(letter)})</span> '
                    if marks and letter and letter != prev else "")
            prev = letter
            items.append(f'<div class="w">{mark}{_e(wt)}</div>')
        cls = "wcol-h cont" if s.get("cont") else "wcol-h"
        cols.append(f'<div><div class="{cls}">{_e(s["header"])}</div>'
                    f'{"".join(items)}</div>')
    hint = " · ".join(str(t["label"]) for t in b.get("tiers", [])
                      if t.get("label")) if marks else ""
    return (f'<section class="block">'
            f'{_head("4", "Слова", hint, b.get("instruction", ""))}'
            f'<div class="wcols" style="grid-template-columns:repeat({ncol},1fr)">'
            f'{"".join(cols)}</div></section>')


def _b5_game(b: Dict[str, Any], lk: Dict[str, int], sp: str) -> str:
    ex = (f'<div class="sample"><b>Образец:</b> {_e(_mark_text(b["example"], lk, sp))}</div>'
          if b.get("example") else "")
    items = "".join(f'<div>{_e(_mark_text(str(x), lk, sp))} <span class="blank"></span></div>'
                    for x in b.get("items", []))
    return (f'<section class="block">'
            f'{_head("5", "Игра", b.get("title", ""), b.get("instruction", ""))}'
            f'{ex}<div class="game">{items}</div></section>')


def _b6_sentences(b: Dict[str, Any], lk: Dict[str, int], sp: str) -> str:
    rows, prev = [], None
    for it in b.get("items", []):
        n = it.get("n_words")
        lab = ""
        if n and n != prev:
            lab = NUM_WORDS_LABEL.get(n, f"{n} слов")
            prev = n
        rows.append(f'<div class="lab">{_e(lab)}</div>'
                    f'<div class="txt">{_e(_mark_text(it.get("text", ""), lk, sp))}</div>')
    return (f'<section class="block">'
            f'{_head("6", "Предложения", "", b.get("instruction", ""))}'
            f'<div class="sent">{"".join(rows)}</div></section>')


def _b7_chant(b: Dict[str, Any], lk: Dict[str, int], sp: str) -> str:
    return (f'<section class="block">'
            f'{_head("7", "Чистоговорка", "", b.get("instruction", ""))}'
            f'<div class="chant">{_e(_mark_text(b.get("text", ""), lk, sp))}</div>'
            f'</section>')


def _b9_footer(lines: Sequence[str]) -> str:
    return ('<div class="foot">'
            + "".join(f"<div>{_e(x)}</div>" for x in lines[:3]) + "</div>")


# ═══════════════════════════════════════════════════════════════════════
#  8. ГЛАВНАЯ ФУНКЦИЯ
# ═══════════════════════════════════════════════════════════════════════

def render_sheet(content: Dict[str, Any], meta: Dict[str, Any], *,
                 options: Optional[Dict[str, Any]] = None,
                 warnings: Optional[List[str]] = None) -> str:
    """Содержание + шапка -> печатный HTML одного листа А4.

    options: {'stress': 'non_obvious'|'all'|'none', 'words_mono': bool,
              'no_fit': bool, 'show_warnings': bool}
    warnings: если передать список — он будет заполнен предупреждениями.
    """
    doc, warns = render_sheet_ex(content, meta, options=options)
    if warnings is not None:
        warnings.extend(warns)
    return doc


def render_sheet_ex(content: Dict[str, Any], meta: Dict[str, Any], *,
                    options: Optional[Dict[str, Any]] = None
                    ) -> Tuple[str, List[str]]:
    opt = dict(options or {})
    sp = opt.get("stress", "non_obvious")

    warns: List[str] = list(content.get("notes") or [])
    c = content
    if not opt.get("no_fit"):
        c, fit_warns = fit(content, CONTENT_H)
        warns.extend(fit_warns)
    warns.extend(lint(c, meta))

    # КУДА идёт лист. Речевое содержание для дома и для занятия одинаково —
    # различаются только две обёртки: шапка-документ [0] (неделя, клетки
    # отметок, подпись родителя) и подвал взрослому [9] (как заниматься).
    # Дома они нужны: там материал ведёт родитель-непрофессионал и тетрадь
    # служит документом обмена. На занятии логопед рядом — обе лишние.
    audience = opt.get("audience", "home")
    if audience not in ("home", "lesson"):
        raise SystemExit("audience должен быть 'home' или 'lesson'")

    parts: List[str] = []
    if audience == "home":
        parts.append(_b0_header(meta))
    if c.get("articulation"):
        parts.append(_b1_articulation(c["articulation"]))
    if c.get("isolated"):
        parts.append(_b2_isolated(c["isolated"]))
    if c.get("syllables"):
        parts.append(_b3_syllables(c["syllables"], sp))
    lk = _stress_lookup(c)
    if c.get("words"):
        parts.append(_b4_words(c["words"], sp))
    if c.get("game"):
        parts.append(_b5_game(c["game"], lk, sp))
    if c.get("sentences"):
        parts.append(_b6_sentences(c["sentences"], lk, sp))
    if c.get("chant"):
        parts.append(_b7_chant(c["chant"], lk, sp))
    if c.get("footer") and audience == "home":
        parts.append(_b9_footer(c["footer"]))

    est = total_height(c)
    warn_html = ""
    if warns and opt.get("show_warnings", True):
        li = "".join(f"<li>{_e(w)}</li>" for w in warns)
        warn_html = (f'<div class="warnbox screen-only"><b>Предупреждения '
                     f'(на печать не идут)</b><ul>{li}</ul></div>')

    return (f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Лист автоматизации [{_e(sound_label(meta.get('sound', '')))}]</title>
<!-- занято по модели: {est:.1f} мм из {CONTENT_H:.0f} мм -->
<style>{_css(opt)}</style>
</head>
<body>
{warn_html}
<div class="sheet" data-est-mm="{est:.1f}">
{chr(10).join(parts)}
</div>
</body>
</html>
""", warns)


# ═══════════════════════════════════════════════════════════════════════
#  8.5 МОСТ: content.py → схема вёрстки
# ═══════════════════════════════════════════════════════════════════════
#  content.py — методический движок (чистота, сквозной словарь, гимнастика
#  из gymnastics.json). sheet.py — печать. Схемы у них разные СОЗНАТЕЛЬНО:
#  движок мыслит фонемами, вёрстка — миллиметрами. Мост ниже — единственное
#  место, где они знают друг о друге.

def from_content(c: Dict[str, Any]) -> Dict[str, Any]:
    """Наполнение из content.build_content() -> схема render_sheet()."""
    stress = {it["word"]: it.get("stress_syllable")
              for g in (c.get("words") or {}).get("groups", [])
              for it in g.get("items", [])}

    def w(word: str) -> Dict[str, Any]:
        return {"word": word, "stress_syllable": stress.get(word)}

    out: Dict[str, Any] = {}

    art = c.get("artic") or {}
    if art.get("items"):
        out["articulation"] = {
            "items": list(art["items"]),
            "instruction": art.get("instruction", ""),
            "hint": art.get("time_note", ""),
            "adult": " · ".join(x for x in (art.get("note"), art.get("dosage"),
                                            art.get("source_ref")) if x),
        }

    iso = c.get("isolated") or {}
    if iso.get("line"):
        head, _, tail = str(iso["line"]).rpartition(":")
        out["isolated"] = ({"instruction": head + ":", "text": tail.strip().rstrip(".")}
                           if head else {"instruction": "", "text": iso["line"]})
        if iso.get("adult"):
            out["isolated"]["adult"] = iso["adult"]

    syl = c.get("syllables") or {}
    if syl.get("rows"):
        rows = []
        for r in syl["rows"]:
            bond = r.get("bond") or {}
            rows.append({
                "units": list(r.get("units", [])),
                "bond_syllable": bond.get("syllable"),
                "word": w(bond["word"]) if bond.get("word") else None,
            })
        out["syllables"] = {
            "type_label": syl.get("type_label", ""),
            "instruction": syl.get("instruction", ""),
            "rows": rows,
            "adult": "Один тип слога на лист; каждая строка кончается словом — "
                     "слог не остаётся сам по себе.",
        }

    words = c.get("words") or {}
    if words.get("groups"):
        tiers: List[Dict[str, Any]] = []
        has_b = any(g.get("tier_b") for g in words["groups"])
        # ТЗ: «ярусы а) короткие частотные / б) длинные». Движок ставит в ярус б
        # ещё и РЕДКИЕ короткие слова (familiarity < 3) — подпись это отражает,
        # иначе «б) пар» выглядит ошибкой.
        for tag, label in (("а", "а) короткие частотные"),
                           ("б", "б) длиннее или реже")):
            groups = []
            for g in words["groups"]:
                items = [w(it["word"]) for it in g.get("items", [])
                         if it.get("tier") == tag]
                if items:
                    groups.append({"header": g.get("header", ""), "items": items})
            if groups:
                tiers.append({"label": label if has_b else None, "groups": groups})
        out["words"] = {"instruction": words.get("instruction", ""), "tiers": tiers}

    game = c.get("game") or {}
    if game.get("items_to_do"):
        sample = str(game.get("sample", ""))
        out["game"] = {
            "title": game.get("title", ""),
            "instruction": game.get("instruction", ""),
            "example": sample.split(":", 1)[-1].strip().rstrip("."),
            "items": [i["prompt"] for i in game["items_to_do"]],
        }

    sent = c.get("sentences") or {}
    if sent.get("items"):
        out["sentences"] = {"instruction": sent.get("instruction", ""),
                            "items": [{"text": i["text"], "n_words": i["n_words"]}
                                      for i in sent["items"]]}

    ch = c.get("chistogovorka") or {}
    if ch.get("text"):
        out["chant"] = {"instruction": ch.get("instruction", ""), "text": ch["text"]}

    out["footer"] = list(c.get("footer") or [])
    out["notes"] = list(c.get("warnings") or [])
    if c.get("vocabulary"):
        out["vocabulary"] = c["vocabulary"]        # линтеру — для строгого правила 13
    return out


# Тип слоговой позиции: имена вёрстки ↔ имена движка. Вёрстка исторически знала
# один «cluster»; движок различает стечение перед гласной и после неё.
TYPE_ALIASES = {
    "cluster": "cluster_onset",
    "cluster_onset": "cluster_onset",
    "cluster_coda": "cluster_coda",
    "direct": "direct", "reverse": "reverse", "intervocal": "intervocal",
}


def compose(sound: str = "р", typ: str = "direct", profile: str = "",
            **kw: Any) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """ОСНОВНОЙ путь: методический движок content.py -> схема вёрстки.

    profile — строка CLI («л,ш,ж» или класс «шипящие»), разворачивается тем же
    `_expand_profile`, что и в стопгапе. Возвращает (content_для_render, report).
    """
    import content as C                                        # noqa: E402
    engine_typ = TYPE_ALIASES.get(typ)
    if engine_typ is None:
        raise SystemExit(f"--type должен быть один из {sorted(TYPE_ALIASES)}")
    prof = _expand_profile(profile) if isinstance(profile, str) else set(profile)
    c = C.build_content(sound=sound, syl_type=engine_typ, profile=prof, **kw)
    report = {
        "banned_phonemes": sorted(c.get("meta", {}).get("banned", [])),
        "engine": "content.py",
        "purity_scope": c.get("purity_scope"),
    }
    return from_content(c), report


# ═══════════════════════════════════════════════════════════════════════
#  9. ЧЕРНОВОЙ СБОРЩИК СОДЕРЖАНИЯ  (стопгап до модуля контента)
# ═══════════════════════════════════════════════════════════════════════
#  Методической амбиции здесь нет: задача — дать вёрстке настоящий,
#  фонетически чистый материал, чтобы CLI работал и лист можно было мерить.
#  Предложения строятся перечислением — это заведомо бедно и заменяется
#  модулем контента.

WORDS_R = os.path.join(HERE, "words_r.jsonl")

# Звуки, СМЕШИВАЕМЫЕ с целевым (канон, правило 2). Движок оппозиций знает
# пару р-л, но не знает й — добавляем руками.
MIXED_WITH = {
    "р": {"л", "л'", "й"},
    "р'": {"л", "л'", "й"},
    "л": {"р", "р'", "й"},
    "с": {"з", "з'", "ц", "ш", "ж", "ч", "щ"},
    "ш": {"с", "с'", "з", "з'", "ж", "щ", "ч"},
}
# ⚠ Блоки [1] и [2] НЕ придумываются здесь и не хранятся таблицей в вёрстке:
#   единственный источник — gymnastics.json (разбор Фомичёвой 1989 / Спивак 2007),
#   доступ к нему — через content.artic_block() / content.isolated_block().
#   Прежние таблицы («Заведи мотор», «Заборчик, Маляр, Грибок, Гармошка») сняты:
#   «Заведи мотор» — формулировка ПОСТАНОВКИ, а не автоматизации; набор из четырёх
#   упражнений был взят на глаз, а не из комплекса источника.
TYPE_LABEL = {
    "direct": "прямой открытый слог",
    "reverse": "обратный слог",
    "intervocal": "звук между гласными",
    "cluster": "слог со стечением",
}
FOOTER_DEFAULT = [
    "Лист рассчитан на 10-15 минут. Не обязательно всё за раз — поделите на 2-3 приёма.",
    "Сначала произносите вместе, потом ребёнок один. Читающий читает сам.",
    "Не получается — не поправляйте резко: вернитесь к строке 2 и начните заново.",
]


def _load_words(path: str = WORDS_R) -> List[Dict[str, Any]]:
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def _expand_profile(raw: str) -> set:
    """'л,ш,ж' или 'шипящие,л' -> множество фонемных ключей (+ мягкие близнецы).
    Перефильтровать безопаснее, чем недофильтровать (закон чистоты)."""
    from phonetics import ALWAYS_HARD, ALWAYS_SOFT, PHONEME_CLASSES
    out: set = set()
    for tok in (raw or "").split(","):
        tok = tok.strip().lower()
        if not tok:
            continue
        if tok in PHONEME_CLASSES:
            out |= set(PHONEME_CLASSES[tok])
            continue
        out.add(tok)
        base = tok.rstrip("'")
        if base not in ALWAYS_HARD and base not in ALWAYS_SOFT:
            out |= {base, base + "'"}
    return out


def _occ_matches(o: Dict[str, Any], typ: str) -> bool:
    if typ == "direct":
        return o["position"] == "initial" and not o["in_cluster"] and bool(o["vowel_after"])
    if typ == "reverse":
        return o["position"] == "final" and not o["in_cluster"] and bool(o["vowel_before"])
    if typ == "intervocal":
        return (o["position"] == "medial" and not o["in_cluster"]
                and bool(o["vowel_before"]) and bool(o["vowel_after"]))
    if typ == "cluster":
        return bool(o["in_cluster"] and o["vowel_after"])
    raise ValueError(f"неизвестный тип позиции: {typ}")


def _unit_of(o: Dict[str, Any], target: str) -> str:
    """Слоговая единица: заголовок колонки и единица слогового ряда."""
    if o.get("cluster") and o["vowel_after"]:
        return o["cluster"] + o["vowel_after"]
    if o["vowel_after"]:
        return target + o["vowel_after"]
    if o["vowel_before"]:
        return o["vowel_before"] + target
    return target


def _balanced(pairs, limit: int, target: str, max_cols: int = MAX_WORD_COLS):
    """Разложить по слоговым корзинам и взять по кругу — колонки выходят ровными."""
    buckets: Dict[str, List[Any]] = {}
    for p in pairs:
        buckets.setdefault(_unit_of(p[1], target), []).append(p)
    order = sorted(buckets, key=lambda u: (-len(buckets[u]), u))[:max_cols]
    out = []
    while len(out) < limit and any(buckets[u] for u in order):
        for u in order:
            if buckets[u] and len(out) < limit:
                out.append(buckets[u].pop(0))
    return out


def _to_groups(pairs, target: str) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[Dict[str, Any]]] = {}
    for a, o in pairs:
        buckets.setdefault(_unit_of(o, target), []).append(
            {"word": a.word, "stress_syllable": a.stress_syllable})
    order = sorted(buckets, key=lambda u: (-len(buckets[u]), u))
    return [{"header": u.capitalize() + ":", "items": buckets[u]} for u in order]


def build_content(sound: str = "р", typ: str = "direct", profile: str = "",
                  n_words: int = 16, n_syl_rows: int = 5,
                  words_path: str = WORDS_R) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Черновой сбор содержания из словаря. Возвращает (content, report)."""
    from phonetics import analyze, select

    if typ not in TYPE_LABEL:
        raise SystemExit(f"--type должен быть один из {sorted(TYPE_LABEL)}")

    # словарь берём по звуку из единого реестра content.WORDS_BY_SOUND
    # (раньше здесь был жёстко зашит [р] и WORDS_R — стопгап врал бы словарём
    #  при --sound с/ш).
    if words_path == WORDS_R and sound != "р":
        import content as _C                                    # noqa: E402
        if sound not in _C.WORDS_BY_SOUND:
            raise SystemExit(
                f"словаря для [{sound}] нет; есть: {', '.join(sorted(_C.WORDS_BY_SOUND))}")
        words_path = os.path.join(HERE, _C.WORDS_BY_SOUND[sound])

    recs = _load_words(words_path)
    by_word = {r["word"]: r for r in recs}
    banned = _expand_profile(profile) | MIXED_WITH.get(sound, set())
    banned.discard(sound)

    sel = select(recs, sound, exclude_phonemes=banned, n=len(recs))
    report = dict(sel.report)

    cand = []
    for a in sel:
        occ = [o for o in a.sound_occurrences
               if o["phoneme"] == sound and _occ_matches(o, typ)]
        if occ:
            cand.append((a, occ[0]))
    if not cand:
        raise SystemExit(
            f"нет ни одного чистого слова для типа «{TYPE_LABEL[typ]}» при профиле "
            f"[{', '.join(sorted(banned)) or '—'}]: словарь дал {len(sel)} чистых слов "
            f"из {len(recs)}, но ни одно не даёт нужную позицию звука.")

    # ── ярусы: а) короткие частотные   б) длиннее / со стечениями ─────
    def key(pair):
        a, _ = pair
        r = by_word.get(a.word, {})
        return (a.n_syllables, len(a.clusters), -int(r.get("familiarity", 1)),
                a.markova_v1 or 99, a.word)

    cand.sort(key=key)
    short = [p for p in cand if p[0].n_syllables <= 2 and not p[0].clusters]
    short_ids = {id(p) for p in short}
    long_ = [p for p in cand if id(p) not in short_ids]

    half = max(1, min(n_words // 2, len(short)))
    tier_a = _balanced(short, half, sound)
    used = {p[0].word for p in tier_a}
    tier_b = _balanced([p for p in long_ if p[0].word not in used],
                       n_words - len(tier_a), sound)
    if len(tier_a) + len(tier_b) < n_words:                  # добрать из короткого
        used |= {p[0].word for p in tier_b}
        extra = _balanced([p for p in short if p[0].word not in used],
                          n_words - len(tier_a) - len(tier_b), sound)
        tier_a += extra

    groups_a, groups_b = _to_groups(tier_a, sound), _to_groups(tier_b, sound)
    all_pairs = tier_a + tier_b
    flat = [p[0].word for p in all_pairs]

    # ── [3] слоги: 4-6 строк, ОДИН тип, каждая со связкой «слог — слово» ──
    units: List[str] = []
    for a, o in all_pairs:
        u = _unit_of(o, sound)
        if typ != "cluster" and len(u) > 2:
            continue
        if u not in units:
            units.append(u)
    rows = []
    for u in units[:n_syl_rows]:
        link = next((p for p in all_pairs if _unit_of(p[1], sound) == u), None)
        rows.append({
            "units": [u] * 4,
            "word": ({"word": link[0].word, "stress_syllable": link[0].stress_syllable}
                     if link else None),
        })

    # ── [5] игра «Один — много»: формы проверяем на чистоту тем же фильтром ──
    def clean(word: str) -> bool:
        try:
            a = analyze(word) if len(_vowels(word)) == 1 else analyze(word, 1)
        except ValueError:
            return False
        return bool(sound in a.phoneme_keys) and not (set(a.phoneme_keys) & banned)

    game_items: List[str] = []
    game_example = None
    for a, _o in all_pairs:
        pl = (by_word.get(a.word) or {}).get("plural")
        if not pl or not clean(pl):
            continue
        if game_example is None:
            game_example = f"{a.word} — {pl}"
        else:
            game_items.append(a.word)
        if len(game_items) >= 6:
            break

    # ── [6] предложения: перечисления из слов блока [4] + служебные скрепы ──
    sentences = []
    if len(flat) >= 4:
        p0, p1, p2, p3 = flat[0], flat[1], flat[2], flat[3]
        sentences = [
            {"text": f"Вот {p0}.", "n_words": 2},
            {"text": f"Вот {p1}.", "n_words": 2},
            {"text": f"{p0.capitalize()} и {p2}.", "n_words": 3},
            {"text": f"{p1.capitalize()} и {p3}.", "n_words": 3},
            {"text": f"{p0.capitalize()}, {p1} и {p2}.", "n_words": 4},
            {"text": f"{p1.capitalize()}, {p2}, {p3} и {p0}.", "n_words": 5},
        ]

    # ── [7] чистоговорка: рифма = слово с ударным конечным целевым слогом ──
    unit0 = units[0] if units else sound
    rhyme = next((a.word for a, _ in all_pairs
                  if a.syllables[-1]["stressed"]
                  and a.syllables[-1]["text"].endswith(unit0)), None)
    chant_word = rhyme or (flat[0] if flat else "")
    chant = {"instruction": "Повтори, прочитай:",
             "text": f"{unit0}-{unit0}-{unit0} — вот {chant_word}"}

    notes: List[str] = []
    notes.append(f"словарь: чистых слов {len(sel)} из {len(recs)}; "
                 f"позицию «{TYPE_LABEL[typ]}» дают {len(cand)}")
    if len(flat) < n_words:
        notes.append(f"НЕДОБОР (правило 4): слов найдено {len(flat)} из {n_words}. "
                     f"Смягчить фильтр нельзя — нужен более широкий словник.")
    if not rhyme:
        notes.append("чистоговорка без рифмы: в блоке [4] нет слова с ударным "
                     "конечным целевым слогом")
    if not game_example:
        notes.append("игра [5] не собрана: у слов блока [4] нет чистых форм мн. ч.")
    notes.append("СТОПГАП: предложения собраны перечислением — заменить модулем содержания")

    # [1] и [2] — из источника (gymnastics.json), а не из таблицы вёрстки
    from content import artic_block, isolated_block            # noqa: E402
    art_b, art_w = artic_block(sound)
    iso_b, iso_w = isolated_block(sound)
    notes += art_w + iso_w
    iso_head, _, iso_tail = str(iso_b.get("line", "")).rpartition(":")

    content: Dict[str, Any] = {
        "articulation": {
            "items": list(art_b.get("items") or []),
            "instruction": art_b.get("instruction", "Повтори упражнения перед зеркалом."),
            "hint": art_b.get("time_note", ""),
            "adult": " · ".join(x for x in (art_b.get("note"), art_b.get("dosage"),
                                            art_b.get("source_ref")) if x),
        },
        "isolated": {
            "instruction": (iso_head + ":") if iso_head else "",
            "text": (iso_tail.strip().rstrip(".") if iso_head
                     else str(iso_b.get("line", ""))),
            "adult": iso_b.get("adult", ""),
        },
        "syllables": {
            "type_label": TYPE_LABEL[typ],
            "instruction": "Повтори, прочитай и назови слово:",
            "rows": rows,
            "adult": "Один тип слога на лист; каждая строка кончается словом — "
                     "слог не остаётся сам по себе.",
        },
        # подпись яруса нужна только когда ярусов действительно два
        "words": {
            "instruction": "Повтори, прочитай:",
            "tiers": [
                {"label": "а) короткие" if (groups_a and groups_b) else None,
                 "groups": groups_a},
                {"label": "б) длиннее и со стечениями" if (groups_a and groups_b) else None,
                 "groups": groups_b},
            ],
        },
        "footer": FOOTER_DEFAULT,
        "notes": notes,
    }
    if game_example:
        content["game"] = {"title": "Один — много", "instruction": "Назови много:",
                           "example": game_example, "items": game_items}
    if sentences:
        content["sentences"] = {"instruction": "Повтори, прочитай:", "items": sentences}
    content["chant"] = chant
    return content, report


def _vowels(w: str) -> str:
    return "".join(ch for ch in w.lower() if ch in VOWELS)


# ═══════════════════════════════════════════════════════════════════════
#  10. CLI
# ═══════════════════════════════════════════════════════════════════════

def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(
        description="Вёрстка домашнего логопедического листа автоматизации (А4).")
    p.add_argument("--sound", default="р",
                   help="целевой звук; словари есть для р · с · ш")
    p.add_argument("--type", dest="typ", default="direct", choices=sorted(TYPE_ALIASES),
                   help="тип слоговой позиции")
    p.add_argument("--profile", default="",
                   help="нарушенные звуки ребёнка через запятую («л,ш,ж» "
                        "или класс: «шипящие,свистящие»)")
    p.add_argument("--content", help="готовый JSON с содержанием (вместо сборщика)")
    p.add_argument("--out", default="sheet.html")
    p.add_argument("--child", default="", help="имя ребёнка в шапку")
    p.add_argument("--sheet-no", default="", help="номер листа")
    p.add_argument("--week-from", default="")
    p.add_argument("--week-to", default="")
    p.add_argument("--words", type=int, default=16, help="слов в блок [4]")
    p.add_argument("--syl-rows", type=int, default=5, help="слоговых строк в блок [3]")
    p.add_argument("--stress", default="non_obvious",
                   choices=["non_obvious", "all", "none"])
    p.add_argument("--mono", action="store_true", help="слова моноширинным шрифтом")
    p.add_argument("--no-fit", action="store_true",
                   help="не сокращать (для отладки переполнения)")
    p.add_argument("--dump-content", help="сохранить собранный content в JSON")
    p.add_argument("--seed", type=int, default=0, help="зерно перестановок движка")
    p.add_argument("--sentences", type=int, default=8, help="предложений в блок [6]")
    p.add_argument("--stopgap", action="store_true",
                   help="черновой сборщик вёрстки вместо движка content.py "
                        "(только для отладки печати)")
    a = p.parse_args(argv)

    sys.path.insert(0, HERE)
    if a.content:
        with open(a.content, encoding="utf-8") as f:
            content = json.load(f)
        report: Dict[str, Any] = {}
    elif a.stopgap:
        content, report = build_content(a.sound, a.typ, a.profile,
                                        n_words=a.words, n_syl_rows=a.syl_rows)
        content.setdefault("notes", []).insert(
            0, "СБОРЩИК: черновой (--stopgap). Методический движок content.py "
               "выключен — содержание не проверено на сквозной словарь.")
    else:
        content, report = compose(a.sound, a.typ, a.profile,
                                  n_words=a.words, n_sentences=a.sentences,
                                  sheet_no=int(a.sheet_no or 1), seed=a.seed,
                                  child_name=a.child)

    meta = {"child_name": a.child, "sound": a.sound, "sheet_no": a.sheet_no,
            "week_from": a.week_from, "week_to": a.week_to}
    doc, warns = render_sheet_ex(content, meta, options={
        "stress": a.stress, "words_mono": a.mono, "no_fit": a.no_fit})

    with open(a.out, "w", encoding="utf-8") as f:
        f.write(doc)
    if a.dump_content:
        with open(a.dump_content, "w", encoding="utf-8") as f:
            json.dump(content, f, ensure_ascii=False, indent=2)

    est = total_height(content if a.no_fit else fit(content)[0])
    print(f"лист: {a.out}")
    print(f"занято по модели: {est:.1f} мм из {CONTENT_H:.0f} мм "
          f"({est / CONTENT_H * 100:.0f} %)")
    if report:
        print(f"запрещённые фонемы: {', '.join(report.get('banned_phonemes', []))}")
    if warns:
        print("предупреждения:")
        for w in warns:
            print(f"  · {w}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
