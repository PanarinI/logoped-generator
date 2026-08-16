# -*- coding: utf-8 -*-
"""
story.py — «СОЧИНИ РАССКАЗ»: лист-сценарий ВЗРОСЛОМУ, отдельный материал.

ЧТО ЭТО И ПОЧЕМУ ИМЕННО ТАК
─────────────────────────────────────────────────────────────────────
✅ **Текст читает не ребёнок, а взрослый.** Подсчитано по изданному альбому
   Комаровой (звук Р): «Послушай» — 10 раз, «Прочитай» — 2, и оба в блоке
   обучения грамоте. Значит лист с рассказом — это СЦЕНАРИЙ ДЛЯ ВЗРОСЛОГО, и
   без инструкции взрослому он не работает (DECISIONS 2026-08-04).
🔶 **Пять форматов рассказа** — наш разбор, а не цитата: (1) вставь слово по
   картинке · (2) рассказ-задача · (3) рассказ с вопросами · (4) готовый
   рассказ, насыщенный звуком · (5) сочини свой по теме и опорным словам.
   Источник под сам этот список не найден, тир держим честным.

ПОЧЕМУ ИЗ ПЯТИ СДЕЛАН ТОЛЬКО ПЯТЫЙ (замер 2026-08-12)
─────────────────────────────────────────────────────────────────────
Формат (1) упирается в банк картинок: лабиринту нужно 216 разных предметов,
своих нарисовано 7 персонажей.
Форматы (2), (3), (4) требуют СВЯЗНОГО ТЕКСТА, а мы не умеем его проверять:
`phonetics.analyze` отказывает на словах без размеченного ударения — движок
разбирает только слова из своей картотеки, не произвольный текст (это записано
блокером ещё 08-04). Собрать «рассказ» из готовых каркасов блока [6] можно, но
выйдет «У мамы рама. Тут рак и роза.» — список, названный рассказом. Локальный
закон 2 это запрещает: материал не имеет права утверждать больше, чем мы можем
показать.
Формат (5) текста не требует вовсе — по нашему же разбору, «там нужны тема и
список опорных слов». Тема и слова у нас есть и проверяемы. Его и делаем.

ЧТО НА ЛИСТЕ
─────────────────────────────────────────────────────────────────────
Тема · опорные существительные · глаголы · инструкция взрослому. Ребёнок
сочиняет вслух, взрослый называет опорные слова и ведёт. Картинок здесь нет —
и поэтому материал не ждёт банка.

ЧЕГО ЗДЕСЬ НЕТ (называю вслух)
─────────────────────────────────────────────────────────────────────
• Готового текста рассказа — см. выше, проверить его мы не можем.
• Вопросов-подсказок «кто · что делал · чем кончилось»: приём известный, но
  источника под конкретный набор я не нашёл, а выдумывать методику нельзя
  (локальный закон 1). Место под них оставлено, строка не печатается.
• Слога: рассказ собирается из слов, ступени слога у него нет — так же
  устроены словосочетания и лабиринт.
"""

from __future__ import annotations

import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import content as C          # noqa: E402
import characters as CH      # noqa: E402
import phonetics as _P       # noqa: E402
import sheet as S            # noqa: E402

__all__ = ["build_story", "render_story", "StoryError",
           "MIN_NOUNS", "MAX_NOUNS", "MIN_VERBS", "MAX_VERBS"]

# ✅ СКОЛЬКО СЛОВ В НАБОРЕ — норма найдена, и она 3-4.
#   Глухов В.П. «Комплексный подход к формированию связной речи…», 2-е изд.,
#   М.: В. Секачёв, 2014, с. 72: «Составление рассказа по опорным словам (в
#   работе со старшими дошкольниками) рекомендуется в целом ряде исследований.
#   Детям предлагаются 3-4 слова, СВЯЗАННЫЕ ПО СМЫСЛУ, по которым они
#   составляют свои рассказы».
#   Канонные наборы у него — тройки: «мальчик — удочка — река», «ребята — лес
#   — ёжик». «Связанные по смыслу» у нас держится темой.
# ⛔ Здесь стояло 6-9 слов со ссылкой на «шкалу Ефименковой: больше слов =
#   легче». Проверка 08-12 эту шкалу опровергла: у Ефименковой 1985 слов
#   «опорные слова» нет вовсе (0 вхождений в полном тексте), а формула «по
#   опорным словам» есть в другой её книге — для ПЕРВОКЛАССНИКОВ. Атрибуция
#   пришла из анонимного студенческого файла. Ровно тот случай, о котором
#   говорит локальный закон 10: чужая уверенная фраза — не источник.
MIN_SET = 3
MAX_SET = 4

# ✅ НЕСКОЛЬКО НАБОРОВ НА ВЫБОР — А. П. Усова (цит. по Глухову, там же):
#   вначале всей группе дают одни и те же опорные слова, «затем — несколько
#   вариантов слов на выбор. В дальнейшем дети сами подбирают опорные слова».
#   Отсюда на листе не один набор, а три: логопед даёт один, или ребёнок
#   выбирает. Лист при этом остаётся набором по 3-4 слова, а не списком из 12.
N_SETS = 3

# ✅ ПЛАН ИЗ ВОПРОСОВ — Алексеева М.М., Яшина В.И. «Методика развития речи и
#   обучения родному языку дошкольников», гл. VII: «План рассказа — это 2-3
#   вопроса, определяющие его содержание и последовательность» (с. 291);
#   «Для плана целесообразно использовать 3-4 вопроса, большее их количество
#   ведёт к излишней детализации действий и описания, что может тормозить
#   самостоятельность детского замысла» (с. 341).
#   Сама тройка — Л. А. Пеньевской (цит. там же, с. 291), и у каждого вопроса
#   названа СВОЯ работа. Формулировки обобщены с её примера «Как мальчик нашёл
#   щенка» до любой темы; функции сохранены дословно.
PLAN = (
    ("Где и когда это было?", "обстоятельство места и времени"),
    ("Какой он был?", "описание"),
    ("Что было дальше?", "развитие сюжетной линии"),
)


class StoryError(Exception):
    """Отказ, который можно объяснить логопеду словами."""


def _hero(sound: str) -> str:
    """Имя канонного образа звука. Правду про него знает propisi.image_for."""
    import propisi as _PR
    return (_PR.image_for(sound).get("name") or "").strip()


def _theme_of(row: Dict[str, Any]) -> str:
    """Верхний уровень темы: «еда/рыба» → «еда»."""
    return (row.get("semantic_category") or "").split("/")[0].strip()


def themes_for(sound: str, profile: Any = (), min_familiarity: int = 1
               ) -> List[Tuple[str, int]]:
    """Темы этого звука, где ЧИСТЫХ слов хватает на лист. (тема, сколько слов).

    Считается по профилю ребёнка: тема, богатая вообще, может обеднеть, когда
    у ребёнка убраны ещё звуки. Экран обязан знать это ДО нажатия.
    """
    banned = C.banned_phonemes(sound, frozenset(profile))
    by: Dict[str, int] = defaultdict(int)
    for r in C.load_words(C._words_path(sound, None)):
        if r.get("familiarity", 3) < min_familiarity:
            continue
        if not C.is_clean(r["word"], banned, r.get("stress_syllable")):
            continue
        t = _theme_of(r)
        if t:
            by[t] += 1
    return sorted(((t, n) for t, n in by.items() if n >= MIN_SET),
                  key=lambda x: (-x[1], x[0]))


def build_story(sound: str = "р",
                profile: Any = (),
                theme: Optional[str] = None,
                seed: int = 0,
                min_familiarity: int = 1,
                child_name: str = "") -> Dict[str, Any]:
    """Лист «сочини рассказ» одного звука под профиль конкретного ребёнка."""
    if sound not in C.WORDS_BY_SOUND:
        raise StoryError(
            f"звука [{_P.sound_label(sound)}] в генераторе нет; собраны: "
            + ", ".join(_P.sound_label(s) for s in sorted(C.WORDS_BY_SOUND)))

    profile = frozenset(profile)
    banned = C.banned_phonemes(sound, profile)
    rnd = random.Random(f"story|{sound}|{sorted(profile)}|{theme}|{seed}")

    rich = themes_for(sound, profile, min_familiarity)
    if not rich:
        raise StoryError(
            f"ни одной темы, где набирается {MIN_NOUNS} чистых слов на "
            f"[{_P.sound_label(sound)}]: сочинять не из чего")
    names = [t for t, _ in rich]
    if theme and theme not in names:
        raise StoryError(
            f"темы «{theme}» на этом звуке нет; есть: " + ", ".join(names))
    if not theme:
        theme = names[seed % len(names)]

    rows = [r for r in C.load_words(C._words_path(sound, None))
            if _theme_of(r) == theme
            and r.get("familiarity", 3) >= min_familiarity
            and C.is_clean(r["word"], banned, r.get("stress_syllable"))]
    rnd.shuffle(rows)
    # Знакомое вперёд: ребёнок сочиняет вслух, и опора должна быть опорой.
    rows.sort(key=lambda r: -(r.get("familiarity") or 0))
    if len(rows) < MIN_SET:
        raise StoryError(
            f"в теме «{theme}» чистых слов {len(rows)}, на набор нужно {MIN_SET}")

    def _mark(word: str, stress: Optional[int]) -> str:
        return S.put_stress(word, stress, "non_obvious")

    # Наборы по 3-4 слова (Глухов), несколько на выбор (Усова). Слово не
    # повторяется между наборами: иначе «выбор» окажется мнимым.
    sets: List[List[str]] = []
    pos = 0
    while len(sets) < N_SETS and len(rows) - pos >= MIN_SET:
        size = MAX_SET if len(rows) - pos >= MAX_SET else MIN_SET
        sets.append([_mark(r["word"], r.get("stress_syllable"))
                     for r in rows[pos:pos + size]])
        pos += size

    warnings: List[str] = []
    if len(sets) < N_SETS:
        warnings.append(
            f"в теме «{theme}» хватило слов на {len(sets)} набор(а) вместо "
            f"{N_SETS} — выбора у ребёнка будет меньше")

    # Последняя проверка — по тому, что реально попадёт на бумагу.
    for word in [w for s_ in sets for w in s_]:
        bare = word.replace("́", "")
        dirty = C.corrigible_of(bare) & banned
        if dirty:
            raise StoryError(
                f"нарушен фильтр чистоты: «{bare}» содержит {sorted(dirty)}")

    return {
        "sets": sets,
        "plan": [q for q, _ in PLAN],
        "warnings": warnings,
        "meta": {
            "sound": sound,
            "sound_label": _P.sound_label(sound),
            "theme": theme,
            "themes": names,
            "profile": sorted(profile),
            "banned": sorted(banned),
            "child": child_name,
            "n_sets": len(sets),
            "n_words": sum(len(x) for x in sets),
            # Канонный образ звука — тот же, что у дорожек, листа и
            # словосочетаний: ребёнок встречает одно существо во всех
            # материалах. Один дом у этого знания — propisi.image_for.
            "image": CH.character_svg(_hero(sound), 26.0, 2.2) if _hero(sound) else "",
            "hero": _hero(sound),
        },
    }


def _e(s: Any) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# Инструкция ВЗРОСЛОМУ — не ребёнку: этот лист адресован ведущему, и обращаться
# он обязан к нему. Глаголы обращения к ребёнку («повтори», «назови») здесь
# были бы ложью о том, кто читает.
#
# Шаг с ОБРАЗЦОМ — не наша выдумка. Глухов: «При обучении составлению рассказа
# по данным словам БЕЗ ОПОРЫ НА КАРТИНКИ такой образец рассказа используется,
# как правило, постоянно». Картинок у нас нет, значит образец обязателен.
ADULT_STEPS = (
    "Выберите один набор и назовите слова вслух — по одному, не торопясь.",
    "Начните сами: скажите первую фразу истории с этими словами. "
    "Без картинок образец начала нужен каждый раз.",
    "Дальше ведите вопросами из плана — по одному, дожидаясь ответа.",
    "Слушайте звук. Сбился — не поправляйте посреди фразы: дайте договорить, "
    "потом повторите слово вместе, медленно.",
)


def render_story(s: Dict[str, Any]) -> str:
    """Печатный лист А4. Взрослому — крупно то, что он произносит вслух."""
    m = s["meta"]
    steps = "".join(f"<li>{_e(x)}</li>" for x in ADULT_STEPS)
    sets = "".join(
        f'<div class="set"><div class="set-no">{i + 1}</div>'
        + "".join(f'<span class="w">{_e(w)}</span>' for w in words)
        + "</div>"
        for i, words in enumerate(s["sets"]))
    # У каждого вопроса своя работа — она названа у Пеньевской, и взрослому
    # полезно её видеть: иначе план читается как три случайных вопроса.
    plan = "".join(f'<li>{_e(q)} <span class="fn">— {_e(fn)}</span></li>'
                   for q, fn in PLAN)
    child = _e(m.get("child") or "")
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Сочини рассказ — звук [{_e(m['sound_label'])}]</title>
<style>
@page {{ size: A4; margin: {S.A4['margin_top']}mm {S.A4['margin_right']}mm
         {S.A4['margin_bottom']}mm {S.A4['margin_left']}mm; }}
* {{ box-sizing: border-box; }}
html, body {{ margin:0; padding:0; background:#fff; color:#000;
  font-family:'PT Sans','Helvetica Neue',Arial,'Liberation Sans',sans-serif;
  hyphens:none; word-break:keep-all; }}
.sheet {{ width:{S.CONTENT_W}mm; }}
@media screen {{
  body {{ background:#f2f2f2; padding:10px; }}
  .sheet {{ width:{S.A4['width_mm']}mm; min-height:{S.A4['height_mm']}mm;
    padding:{S.A4['margin_top']}mm {S.A4['margin_right']}mm
            {S.A4['margin_bottom']}mm {S.A4['margin_left']}mm;
    margin:0 auto; background:#fff; border:1px solid #bbb; }}
}}
@media print {{ .sheet {{ width:auto; padding:0; border:0; margin:0; }} }}
.doc {{ display:flex; align-items:center; gap:4mm; font-size:10.5pt;
        padding-bottom:1.5mm; border-bottom:0.4pt solid #000; }}
.doc .fill {{ display:inline-block; border-bottom:0.4pt solid #000; width:46mm; }}
.badge {{ border:0.4pt solid #000; padding:0.2mm 1.8mm; font-weight:700; }}
h1 {{ font-size:14pt; margin:5mm 0 1mm; font-weight:700; }}
h1 b {{ font-size:20pt; }}
.who {{ font-size:10pt; color:#444; font-style:italic; margin:0 0 4mm; }}
.block {{ margin-top:4mm; }}
.bhead {{ display:flex; align-items:baseline; gap:2mm; margin-bottom:1.5mm; }}
.btitle {{ font-size:12pt; font-weight:700; }}
.task {{ font-size:10pt; color:#444; font-style:italic; }}
.set {{ display:flex; align-items:baseline; gap:6mm; padding:1.6mm 0;
        border-bottom:0.4pt solid #ccc; }}
.set:last-child {{ border-bottom:0; }}
.set-no {{ flex:0 0 auto; width:5mm; height:5mm; line-height:4.7mm;
           border:0.4pt solid #000; border-radius:50%; text-align:center;
           font-size:8.5pt; font-weight:700; }}
.w {{ font-size:20pt; line-height:1.3; white-space:nowrap; }}
ol {{ font-size:10.5pt; line-height:1.5; margin:0; padding-left:5mm; }}
ol.plan {{ font-size:13pt; line-height:1.45; }}
ol.plan .fn {{ font-size:9.5pt; color:#666; font-style:italic; }}
.foot {{ margin-top:6mm; border-top:0.4pt solid #000; padding-top:1.2mm;
         font-size:9.5pt; font-style:italic; color:#444; line-height:1.45; }}
.hero {{ margin-left:auto; }}
</style>
</head>
<body>
<div class="sheet">
  <div class="doc">
    <span>Ребёнок <span class="fill">{child}</span></span>
    <span class="badge">Звук [{_e(m['sound_label'])}]</span>
    <span>Дата <span class="fill" style="width:26mm"></span></span>
    <span class="hero">{m.get('image') or ''}</span>
  </div>

  <h1>Сочини рассказ: <b>{_e(m['theme'])}</b></h1>
  <p class="who">Этот лист — взрослому. Читает и ведёт он, сочиняет ребёнок.</p>

  <section class="block">
    <div class="bhead"><span class="btitle">Опорные слова</span>
      <span class="task">Три набора на выбор — берите ОДИН, не все сразу.</span></div>
    {sets}
  </section>

  <section class="block">
    <div class="bhead"><span class="btitle">План — три вопроса</span>
      <span class="task">По одному, дожидаясь ответа.</span></div>
    <ol class="plan">{plan}</ol>
  </section>

  <section class="block">
    <div class="bhead"><span class="btitle">Как вести</span></div>
    <ol>{steps}</ol>
  </section>

  <div class="foot">
    Готового текста здесь нет намеренно: рассказ сочиняет ребёнок, а лист даёт
    ему опору и держит звук. Слова отобраны так, чтобы в них не было звуков,
    которые у ребёнка сейчас не получаются. Три-четыре слова в наборе и три
    вопроса в плане — не наши числа: так их задают Глухов и Пеньевская.
    Больше вопросов, по Пеньевской, начинает мешать замыслу ребёнка.
  </div>
</div>
</body>
</html>
"""
