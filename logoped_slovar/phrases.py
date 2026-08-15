# -*- coding: utf-8 -*-
"""
phrases.py — СЛОВОСОЧЕТАНИЯ «прилагательное + существительное», отдельный лист.

ИСТОЧНИК КАНОНА (разобран лично 2026-08-09, пособие открыто и посчитано):
    Спивак Е.Н., «Речевой материал для автоматизации и дифференциации звуков
    у детей 5-7 лет» (ГНОМ), раздел Ш · Ж · Ч · Щ. Пункт озаглавлен дословно
    «Повтори словосочетания.» и стоит во ВСЕХ 10 разделах пособия — в каждом
    из четырёх разделов автоматизации и в каждом из шести разделов
    дифференциации. Это не приём одного звука, а постоянная ступень.

Замер по четырём разделам автоматизации (45 пар):
  • 44 из 45 — «прилагательное + существительное» (одно исключение —
    предложная конструкция). Форма задана источником, а не нами;
  • объём 9-12 пар;
  • место в последовательности — после слов, перед предложениями;
  • целевой звук в ОБОИХ словах лишь у 17 из 45 (38 %). Канон не требует
    звука в обеих частях. У нас он выходит в обеих сам собой: и словарь
    существительных, и словарь прилагательных собраны по целевому звуку, —
    то есть мы строже источника, и это следствие устройства словарей.
⛔ Речевой материал пособия НЕ переносится (АП ГНОМ). Перенесён метод: тип
   задания, его место, объём и правило звука.

ПОЧЕМУ ОТДЕЛЬНЫЙ ЛИСТ, А НЕ БЛОК ЛИСТА АВТОМАТИЗАЦИИ
─────────────────────────────────────────────────────────────────────
Сначала сделали блоком [5б]. Замер 2026-08-09 показал, что места нет:
лист А4 = 273 мм, а материал даёт 305-363 мм ещё ДО нового блока, и лестница
сокращений режет его в любом случае. Если оставить словосочетания и резать
ядро, слова доходят до минимума 12, объём словесного материала падает — и
ломается КАНОННОЕ правило 11 (слоговой блок ≤ ¼ словесного). Если оставить и
не резать ядро — блок не доходит до бумаги ни на одном из 21 листа.
Решение автора 2026-08-09: печатать отдельным материалом, как слоговую и
звуковую дорожки. У Спивак это тоже отдельная страница.

Отсюда — пул существительных: ВЕСЬ словарь звука, а не блок [4] листа.
Правило 13 («сквозной словарь») живёт внутри ОДНОГО листа: оно требует, чтобы
слова блоков [5][6][7] пришли из блока [4] того же листа. Здесь лист
самостоятельный, своего блока [4] у него нет — так же устроен лабиринт.

НА ЧЁМ СТОИТ МАТЕРИАЛ (закон №7: спроси, есть ли признак ДАННЫМИ)
─────────────────────────────────────────────────────────────────────
  • род существительного → форма прилагательного — ЕСТЬ данными (`gender`
    у существительного, `form_f`/`form_n` у прилагательного). Это
    единственное здесь правило, и оно механическое;
  • сочетаемость прил. ↔ сущ. — признака в данных НЕТ. Правило по паре
    категорий печатает «кирпичная рука» и «плюшевое шило». Поэтому таблица
    `combinability.json`, выверенная руками в шесть проходов глазами;
  • класс подлежащего для причастий и признаков внешности — ЕСТЬ данными
    (`SUBJECT_CLASS`, размечен 08-08 ради глаголов): без него печаталось
    «летящая щука» и «седой поросёнок».

    python3 phrases.py --sound р --profile л,ш --out phrases_r.html
"""

from __future__ import annotations

import html
import os
import random
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import characters as CH      # noqa: E402
import content as C          # noqa: E402
import phonetics as _P       # noqa: E402
import sheet as S            # noqa: E402  — ударение ставится тем же правилом,
#                              что на листе слов: один продукт, один язык бумаги


def _stress_index(sound: str) -> Dict[str, int]:
    """Слово → номер ударного слога. Из тех же картотек, что и материал.

    Прилагательные лежат отдельным файлом и склоняются по родам, поэтому в
    указатель идут все три формы: «сладкий · сладкая · сладкое». Номер слога у
    них совпадает — окончание ударение не двигает.
    """
    out: Dict[str, int] = {}
    for row in C.load_words(C._words_path(sound, None)):
        st = row.get("stress_syllable")
        if st:
            out[row["word"].lower()] = int(st)
    name = C.ADJECTIVES_BY_SOUND.get(sound, "")
    path = os.path.join(HERE, name) if name else ""
    if path and os.path.isfile(path):
        import json
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                st = row.get("stress_syllable")
                if not st:
                    continue
                for key in ("word", "form_f", "form_n"):
                    if row.get(key):
                        out[str(row[key]).lower()] = int(st)
    return out

__all__ = ["build_phrases_sheet", "render_phrases", "PhrasesError",
           "MIN_PHRASES", "MAX_PHRASES"]

MIN_PHRASES = 4
MAX_PHRASES = 12          # верх канона по замеру Спивак (9-12 пар)

PAGE_W, PAGE_H = 210, 297
MARGIN_L, MARGIN_R = 18, 15


class PhrasesError(Exception):
    pass


def build_phrases_sheet(sound: str = "р",
                        profile: Any = (),
                        n: int = MAX_PHRASES,
                        seed: int = 0,
                        min_familiarity: int = 1,
                        child_name: str = "") -> Dict[str, Any]:
    """Лист словосочетаний одного звука под профиль конкретного ребёнка."""
    if sound not in C.WORDS_BY_SOUND:
        raise PhrasesError(
            f"звука [{_P.sound_label(sound)}] в генераторе нет; собраны: "
            + ", ".join(_P.sound_label(s) for s in sorted(C.WORDS_BY_SOUND)))
    if not (MIN_PHRASES <= n <= MAX_PHRASES):
        raise PhrasesError(
            f"словосочетаний на листе {MIN_PHRASES}-{MAX_PHRASES} "
            f"(замер по Спивак: 9-12 пар)")

    profile = frozenset(profile)
    banned = C.banned_phonemes(sound, profile)
    rnd = random.Random(f"phrases|{sound}|{sorted(profile)}|{seed}")
    warnings: List[str] = []

    rows = C.load_words(C._words_path(sound, None))
    pool = [r for r in rows
            if r.get("familiarity", 3) >= min_familiarity
            and C.is_clean(r["word"], banned, r.get("stress_syllable"))]
    if not pool:
        raise PhrasesError(
            f"для профиля {sorted(profile) or '—'} чистых существительных на "
            f"[{_P.sound_label(sound)}] нет вовсе — словосочетания не из чего строить")

    built = C.build_phrases(pool, sound, banned, rnd, n, warnings)
    if not built:
        raise PhrasesError(
            "словосочетаний не набралось: " + (warnings[-1] if warnings else "—"))

    # Последняя проверка — по тому, что реально попадёт на бумагу. Здесь нет
    # verify_purity() листа, значит фильтр обязан отработать явно и упасть.
    for it in built["items"]:
        for tok in C._tokens(it["text"]):
            dirty = C.corrigible_of(tok) & banned
            if dirty:
                raise PhrasesError(
                    f"нарушен фильтр чистоты: «{it['text']}» — {tok!r} "
                    f"содержит {sorted(dirty)}")

    # УДАРЕНИЕ. На листе слов оно стоит (политика «non_obvious»), а здесь его
    # не было — один продукт говорил на бумаге двумя разными языками. Читает
    # вслух ВЗРОСЛЫЙ, и «пастила» без знака читается как «пастИла» с той же
    # вероятностью, что и на листе слов. Ставим по той же политике: только там,
    # где ударение не читается само. Добавлено 08-10 по вопросу автора.
    stress_by_word = _stress_index(sound)
    for it in built["items"]:
        it["text"] = " ".join(
            S.put_stress(tok, stress_by_word.get(tok.lower()), "non_obvious")
            for tok in it["text"].split())

    return {
        "items": built["items"],
        "warnings": warnings,
        "meta": {
            "sound": sound,
            "sound_label": _P.sound_label(sound),
            "profile": sorted(profile),
            "banned": sorted(banned),
            "child": child_name,
            "n": len(built["items"]),
            "instruction": built["instruction"],
            "image": PR_image(sound),
            "source": "Спивак Е.Н., ГНОМ — «Повтори словосочетания»",
        },
    }


def PR_image(sound: str) -> str:
    """Канонный образ звука — тот же, что у дорожек и в блоке [2] листа.

    Ребёнок встречает одно существо во всех материалах: это связность, а не
    украшение. Называть его не просят — рисунок стоит в ШАПКЕ, рядом со
    звуком, а не в поле задания. Речевой материал листа — только пары слов."""
    import propisi as _PR
    return (_PR.image_for(sound).get("name") or "").strip()


def _e(s: Any) -> str:
    return html.escape(str(s), quote=True)


def render_phrases(p: Dict[str, Any]) -> str:
    """Структура -> печатный HTML одного листа А4 (ч/б).

    Две колонки — как сетка пар в источнике. Прочерков нет намеренно: ребёнок
    здесь ПОВТОРЯЕТ, а не дописывает; строка с прочерком обещала бы письменное
    задание, которого источник не даёт."""
    m = p["meta"]
    label = m["sound_label"]
    cells = "".join(f'<div class="pair">{_e(it["text"])}</div>'
                    for it in p["items"])
    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<title>Словосочетания [{_e(label)}]</title>
<style>
@page {{ size: A4; margin: 12mm {MARGIN_R}mm 12mm {MARGIN_L}mm; }}
* {{ box-sizing: border-box; }}
html, body {{ margin:0; padding:0; background:#fff; color:#000;
   font-family:'PT Sans','Helvetica Neue',Arial,sans-serif; }}
body {{ background:#f2f2f2; padding:10px; }}
.page {{ width:{PAGE_W}mm; min-height:{PAGE_H}mm; margin:0 auto; background:#fff;
   border:1px solid #bbb; padding:12mm {MARGIN_R}mm 12mm {MARGIN_L}mm; }}
@media print {{ body{{background:#fff;padding:0}}
   .page{{width:auto;border:0;margin:0;padding:0;min-height:0}} }}
.doc {{ display:flex; gap:6mm; align-items:baseline; flex-wrap:wrap;
   font-size:10.5pt; padding-bottom:1.5mm; border-bottom:0.4pt solid #000; }}
.badge {{ border:0.8pt solid #000; padding:0.4mm 1.6mm; font-weight:700; }}
.fill {{ display:inline-block; min-width:34mm; border-bottom:0.4pt solid #000; }}
.head {{ display:flex; align-items:center; gap:5mm; margin:5mm 0 1mm; }}
h1 {{ font-size:14pt; margin:0; font-weight:700; }}
h1 b {{ font-size:20pt; }}
.task {{ font-size:12pt; margin:0 0 10mm; }}
/* Кегль и воздух — вёрстка, а не доза. Доза канонная (9-12 пар, замер по
   Спивак) и от размера шрифта не зависит; крупный шрифт лишь занимает лист
   честно, вместо половины страницы белого поля. 24 pt здесь уместен: на
   листе автоматизации речевой материал идёт 16-18 pt, а тут строк вчетверо
   меньше и читает их ребёнок 5-7 лет. */
.grid {{ display:grid; grid-template-columns:repeat(2, 1fr); gap:14mm 10mm; }}
.pair {{ font-size:24pt; line-height:1.2; }}
.adult {{ margin-top:14mm; padding-top:2mm; border-top:0.4pt solid #000;
   font-size:9.5pt; line-height:1.45; }}
.note {{ margin-top:4mm; font-size:8.5pt; color:#666; }}
</style></head><body><div class="page">

<div class="doc">
  <span>Ребёнок <span class="fill">{_e(m['child'])}</span></span>
  <span class="badge">Звук [{_e(label)}]</span>
  <span>Дата <span class="fill" style="min-width:24mm"></span></span>
</div>

<div class="head">
  {CH.character_svg(m.get("image", ""), 24.0, 2.4) or ""}
  <h1>Словосочетания · звук <b>[{_e(label)}]</b></h1>
</div>
<p class="task">{_e(m['instruction'])}</p>

<div class="grid">{cells}</div>

<div class="adult">
  <b>Взрослому.</b> Это ступень между словом и фразой: ребёнок уже держит звук
  в отдельном слове, а здесь удерживает его в двух словах подряд. Читайте
  вслух и просите повторить — писать здесь нечего. Если слово не даётся,
  вернитесь к нему в списке слов и повторите медленнее вместе.
</div>
<div class="note">Тип задания и его объём — Спивак Е.Н. (ГНОМ), «Повтори
  словосочетания». Речевой материал собственный.</div>

</div></body></html>"""


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Словосочетания «прил. + сущ.»")
    ap.add_argument("--sound", default="р")
    ap.add_argument("--profile", default="", help="нарушенные звуки: «л,ш,ж»")
    ap.add_argument("--n", type=int, default=MAX_PHRASES)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--child", default="")
    ap.add_argument("--out", default="phrases_demo.html")
    a = ap.parse_args()
    import sheet as S
    prof = S._expand_profile(a.profile)
    p = build_phrases_sheet(a.sound, prof, a.n, a.seed, child_name=a.child)
    Path(a.out).write_text(render_phrases(p), encoding="utf-8")
    print(f"{a.out}: [{p['meta']['sound_label']}] {p['meta']['n']} словосочетаний"
          + (f" · профиль {p['meta']['profile']}" if p['meta']['profile'] else ""))
    for w in p["warnings"]:
        print("  ⚠", w)
