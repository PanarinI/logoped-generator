# -*- coding: utf-8 -*-
"""
rasskaz.py — РАССКАЗ НА АВТОМАТИЗАЦИЮ: готовый текст для пересказа + лист взрослому.

Это ровно то, о чём просила логопед (ГОЛОСА.md, дословно): «генерация рассказов
для автоматизации звуков». В отличие от story.py («сочини сам»), здесь текст
ЕСТЬ, и его читает взрослый, а ребёнок слушает, отвечает и пересказывает.

ТЗ — research/logoped_rasskaz_TZ_2026-08-17.md (13 агентов, каждый вывод прошёл
проверку на опровержение). Здесь — только то, что выстояло.

МЕСТО В ЛЕСТНИЦЕ
─────────────────────────────────────────────────────────────────────
✅ Пятая ступень автоматизации: слоги → слова → предложения → чистоговорки и
   стихи → короткие, затем длинные рассказы → разговорная речь
   (Филичева, Чевелева, Чиркина «Основы логопедии», 1989, с. 68-69).
✅ Читает ВЗРОСЛЫЙ, ребёнок слушает и пересказывает (Фомичёва 1989, с. 40;
   Спивак 2007 — все инструкции «Послушай… Перескажи»). Чтение самим
   ребёнком — опция, не ступень: у Жихаревой «Прослушать текст ИЛИ прочитать
   вслух»; у Нищевой «с детьми, умеющими читать, тексты МОЖНО и читать».
✅ Текст с завышенной плотностью звука — материал ступени автоматизации, а
   не финального общения: «частотность этого звука в специальных текстах
   превышает нормальное их распределение в естественной речи»
   (Волкова, Шаховская «Логопедия», 1998).

ПОЧЕМУ ЭТО СТАЛО ВОЗМОЖНО (08-17)
─────────────────────────────────────────────────────────────────────
Блокер 08-04 звучал «движок не разбирает произвольный текст». Точнее так:
он не знает УДАРЕНИЯ незнакомого слова, а СОГЛАСНЫЙ состав от ударения не
зависит (content._analyze, инвариант test_purity_is_stress_independent).
Значит чистоту любого текста считать можно уже сейчас — `content.corrigible_of`
берёт и предлоги, и незнакомые слова. Ударение для печати ставится из
картотеки там, где слово в ней есть; остальным — по политике «non_obvious»
только если размечено. Тексты пишет рука ПОД ЭТОТ ВАЛИДАТОР — не наоборот.

НОРМЫ — ЗАМЕРЫ ПО ИЗДАННЫМ ТЕКСТАМ, НЕ НОРМА ИЗДАНИЯ
─────────────────────────────────────────────────────────────────────
Опубликованной нормы длины и насыщенности нет ни в одном проверенном издании.
Числа ниже — замеры по текстам Нищевой (2002, вып. 5 2018) и Жихаревой-Норкиной
(вып. 6, 7), так и подаются: 🔶 замер, не ✅ цитата.
  • 3-5 предложений, 22-32 слова (уровень 1); 5-7 и до 45 (уровень 2);
    потолок ~60 слов на один звук;
  • среднее предложение 5-7 слов, самое длинное ≤ 12 (в изданных бывает 11);
  • слов с целевым звуком 40-70 % от всех, цель ~половина;
  • зачин — основа — концовка обязательны: без зачина или концовки текст —
    брак (✅ Глухов: «нарушение структурно-смысловой целостности»);
  • одна сюжетная линия, прямое время (✅ Филичева/Чиркина 2008: «простая и
    понятная фабула, чётко выраженная логическая последовательность»).
ЛОВУШКИ, НАЙДЕННЫЕ ВАЛИДАТОРОМ ПРИ ПИСЬМЕ ТЕКСТОВ (08-17)
─────────────────────────────────────────────────────────────────────
Их стоит знать заранее — иначе каждый новый текст переписывается по четыре раза.
• ВОПРОСИТЕЛЬНЫЕ СЛОВА. «Что», «почему», «чем», «чей» несут [ч] и [ш] — на
  листах [с] [с'] [з] [з'] [ж] [щ] они ЗАПРЕЩЕНЫ. Чистые всегда: кто · где ·
  куда · кого · кому · когда · какой · откуда. «Сколько» несёт [с].
• ВОЗВРАТНЫЕ ГЛАГОЛЫ. «-тся/-ться» звучит как [ца]: «тащится» = [ташыца], то
  есть [ц] — брак на листах [с] [з] [ж] [щ].
• ОГЛУШЕНИЕ. «Творожком» звучит [твapoшкaм] — [ш] на листе [ж]. «Вышел»,
  «ушла», «вместе», «вкусно», «ест», «из», «с»/«со» — постоянные нарушители.
• ПЕРЕБОР ТОЖЕ БРАК. Плотность выше 75 % валидатор не пропускает: текст из
  одних целевых слов перестаёт быть рассказом.

⛔ Правило Фомичёвой «желательно, чтобы в каждом слове был звук» (1989, с. 39)
   ОПУБЛИКОВАНО, но про ступень ПРЕДЛОЖЕНИЙ, не рассказа. 100 % в рассказе не
   требуем: даже в изданных предложениях так выходит в 7-12 % случаев.

ЧТО СНЯТО ПРОВЕРКОЙ — В ДВИЖОК НЕ БРАТЬ (ТЗ, часть 4, 17 правил), главное:
  «все три позиции звука в одном тексте» · «пересказ всегда последним» ·
  «ровно один вопрос на предложение» · «банк слов обязателен» · «первый
  императив речевой, последний ручной» · универсальная таблица смешиваемых пар
  с «ноль слов».
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import content as C          # noqa: E402
import characters as CH      # noqa: E402
import phonetics as _P       # noqa: E402
import sheet as S            # noqa: E402

__all__ = ["load_texts", "check_text", "build_rasskaz", "render_rasskaz",
           "RasskazError", "NORMS"]

TEXTS_PATH = HERE / "rasskazy.jsonl"

# 🔶 Замеры (см. шапку). Держим как единственный дом чисел.
NORMS: Dict[str, Any] = {
    "sentences": (3, 7),          # уровень 1: 3-5, уровень 2: 5-7
    "words": (18, 60),            # 22-32 типично, потолок ~60
    "sentence_max_words": 12,     # в изданных бывает 11
    "share_target": (0.40, 0.75), # доля слов с целевым звуком
    "min_target_per_sentence": 1, # предложение без звука — брак
    "questions": (3, 6),          # практика 3-8, издания не нормируют
}

_TOKEN = re.compile(r"[а-яё]+(?:-[а-яё]+)*", re.I)
_SENT = re.compile(r"[^.!?…]+[.!?…]+")


class RasskazError(Exception):
    """Отказ, который можно объяснить логопеду словами."""


# ── текстотека ─────────────────────────────────────────────────────────

def load_texts(path: Path = TEXTS_PATH) -> List[Dict[str, Any]]:
    """Все тексты. Одна строка JSONL = один рассказ со всей обвязкой."""
    out: List[Dict[str, Any]] = []
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(json.loads(line))
    return out


def texts_for(sound: str, profile: Any = ()) -> List[Dict[str, Any]]:
    """Тексты этого звука, ЧИСТЫЕ для этого профиля. Экран показывает только их."""
    banned = C.banned_phonemes(sound, frozenset(profile))
    return [t for t in load_texts()
            if t["sound"] == sound and not check_text(t, sound, banned)["errors"]]


# ── валидатор ──────────────────────────────────────────────────────────

def _tokens(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN.findall(text)]


def _sentences(text: str) -> List[str]:
    return [s.strip() for s in _SENT.findall(text) if s.strip()]


def _keys(word: str) -> frozenset:
    """Корригируемые фонемы слова. Ударение не нужно: согласный состав от него
    не зависит (content._analyze). Дефисные и бесгласные токены тоже берёт."""
    return C.corrigible_of(word.replace("-", ""))


def _has_target(word: str, sound: str) -> bool:
    return sound in _keys(word)


def check_text(t: Dict[str, Any], sound: str, banned: frozenset
               ) -> Dict[str, Any]:
    """Прогон одного текста по нормам. Возвращает замеры и список нарушений.

    Проверяется то, что ПОПАДЁТ НА БУМАГУ: сам текст, заголовок, вопросы.
    Нарушение чистоты — брак; нарушение нормы длины — брак; остальное — замер.
    """
    errors: List[str] = []
    text = t["text"]
    sents = _sentences(text)
    words = _tokens(text)
    n_s, n_w = len(sents), len(words)

    lo, hi = NORMS["sentences"]
    if not (lo <= n_s <= hi):
        errors.append(f"предложений {n_s}, норма {lo}-{hi}")
    lo, hi = NORMS["words"]
    if not (lo <= n_w <= hi):
        errors.append(f"слов {n_w}, норма {lo}-{hi}")

    longest = max((len(_tokens(s)) for s in sents), default=0)
    if longest > NORMS["sentence_max_words"]:
        errors.append(f"самое длинное предложение {longest} слов, "
                      f"потолок {NORMS['sentence_max_words']}")

    with_target = [w for w in words if _has_target(w, sound)]
    share = len(with_target) / n_w if n_w else 0.0
    lo, hi = NORMS["share_target"]
    if not (lo <= share <= hi):
        errors.append(f"слов со звуком {share:.0%}, норма {lo:.0%}-{hi:.0%}")

    for i, s_ in enumerate(sents, 1):
        k = sum(1 for w in _tokens(s_) if _has_target(w, sound))
        if k < NORMS["min_target_per_sentence"]:
            errors.append(f"предложение {i} без целевого звука: «{s_}»")

    # ЧИСТОТА — главное. Всё, что читают вслух: текст, заголовок, вопросы.
    dirty: List[str] = []
    for w in words + _tokens(t.get("title", "")) + \
            [w for q in t.get("questions", []) for w in _tokens(q)]:
        bad = _keys(w) & banned
        if bad:
            dirty.append(f"«{w}» {sorted(bad)}")
    if dirty:
        errors.append("запрещённые звуки: " + ", ".join(sorted(set(dirty))))

    # Обвязка листа
    q = t.get("questions", [])
    lo, hi = NORMS["questions"]
    if not (lo <= len(q) <= hi):
        errors.append(f"вопросов {len(q)}, норма {lo}-{hi}")
    if not t.get("title"):
        errors.append("нет заголовка")

    return {
        "sentences": n_s, "words": n_w, "longest": longest,
        "share_target": round(share, 2), "target_words": len(with_target),
        "errors": errors,
    }


# ── сборка листа ───────────────────────────────────────────────────────

def _stress_index(sound: str) -> Dict[str, Optional[int]]:
    """Ударение из картотеки для слов, что в ней есть — как в phrases.py."""
    idx: Dict[str, Optional[int]] = {}
    for r in C.load_words(C._words_path(sound, None)):
        idx[r["word"].lower()] = r.get("stress_syllable")
    return idx


def _mark_text(text: str, stress_by_word: Dict[str, Optional[int]]) -> str:
    """Ударение по политике листа: только там, где оно не читается само И
    известно из картотеки. Незнакомые слова остаются как есть — врать
    ударением нельзя."""
    def repl(m: re.Match) -> str:
        w = m.group(0)
        st = stress_by_word.get(w.lower())
        if st is None:
            return w
        marked = S.put_stress(w.lower(), st, "non_obvious")
        # вернуть заглавную, если была
        return (marked[0].upper() + marked[1:]) if w[0].isupper() else marked
    return _TOKEN.sub(repl, text)


def build_rasskaz(sound: str = "р", profile: Any = (),
                  text_id: Optional[str] = None,
                  child_name: str = "") -> Dict[str, Any]:
    """Лист «Рассказ» одного звука под профиль ребёнка."""
    if sound not in C.WORDS_BY_SOUND:
        raise RasskazError(
            f"звука [{_P.sound_label(sound)}] в генераторе нет; собраны: "
            + ", ".join(_P.sound_label(s) for s in sorted(C.WORDS_BY_SOUND)))
    profile = frozenset(profile)
    banned = C.banned_phonemes(sound, profile)

    all_for_sound = [t for t in load_texts() if t["sound"] == sound]
    if not all_for_sound:
        raise RasskazError(
            f"текстов на [{_P.sound_label(sound)}] в текстотеке ещё нет")
    clean = [t for t in all_for_sound if not check_text(t, sound, banned)["errors"]]
    if not clean:
        raise RasskazError(
            f"на [{_P.sound_label(sound)}] есть {len(all_for_sound)} текст(а), но "
            f"для профиля {sorted(profile) or '—'} ни один не чист: в каждом есть "
            f"звук, который у ребёнка не поставлен")

    t = next((x for x in clean if x["id"] == text_id), clean[0]) if text_id else clean[0]
    if text_id and t["id"] != text_id:
        raise RasskazError(f"текста «{text_id}» для этого профиля нет; "
                           f"есть: " + ", ".join(x["id"] for x in clean))

    stat = check_text(t, sound, banned)
    idx = _stress_index(sound)
    import propisi as _PR
    hero = (_PR.image_for(sound).get("name") or "").strip()
    return {
        "text": t,
        "printed_text": _mark_text(t["text"], idx),
        "printed_title": _mark_text(t["title"], idx),
        "stat": stat,
        "options": [{"id": x["id"], "title": x["title"]} for x in clean],
        "meta": {
            "sound": sound, "sound_label": _P.sound_label(sound),
            "profile": sorted(profile), "banned": sorted(banned),
            "child": child_name, "hero": hero,
            "image": CH.character_svg(hero, 26.0, 2.2) if hero else "",
        },
    }


# ── печать ─────────────────────────────────────────────────────────────

def _e(s: Any) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# Порядок работы — Жихарева-Норкина (4 шага) + Нищева (установка) + Лунева
# («полным предложением», «следи за произношением»). Все — взрослому.
STEPS = (
    "Прочитайте рассказ ребёнку вслух — чётко, не торопясь, выделяя звук.",
    "Задайте вопросы. Просите отвечать полным предложением и следить за звуком.",
    "Прочитайте ещё раз.",
    "Попросите пересказать. Сбился на звуке — дайте договорить, потом "
    "повторите слово вместе.",
)


def render_rasskaz(r: Dict[str, Any]) -> str:
    m, t = r["meta"], r["text"]
    child = _e(m.get("child") or "")
    qs = "".join(f"<li>{_e(q)}</li>" for q in t.get("questions", []))
    extra = "".join(f"<li>{_e(q)}</li>" for q in t.get("extra_questions", []))
    extra_block = (f'<section class="block"><div class="bhead">'
                   f'<span class="btitle">Ещё поговорите</span>'
                   f'<span class="task">Ответа в рассказе нет — это про жизнь ребёнка.</span>'
                   f'</div><ol class="q">{extra}</ol></section>' if extra else "")
    steps = "".join(f"<li>{_e(x)}</li>" for x in STEPS)
    # Абзацы: каждое предложение с новой строки — взрослому легче вести
    # пальцем и останавливаться на вопросах.
    body = "".join(f"<p>{_e(s_)}</p>" for s_ in _sentences(r["printed_text"]))
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Рассказ — звук [{_e(m['sound_label'])}]</title>
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
.hero {{ margin-left:auto; }}
.setup {{ margin:4mm 0 3mm; font-size:10pt; color:#444; font-style:italic; }}
h1 {{ font-size:20pt; margin:2mm 0 3mm; font-weight:700; }}
.story p {{ font-size:15pt; line-height:1.55; margin:0 0 1.2mm; }}
.block {{ margin-top:5mm; }}
.bhead {{ display:flex; align-items:baseline; gap:2mm; margin-bottom:1.5mm; }}
.btitle {{ font-size:12pt; font-weight:700; }}
.task {{ font-size:10pt; color:#444; font-style:italic; }}
ol.q {{ font-size:13pt; line-height:1.5; margin:0; padding-left:5mm; }}
ol.steps {{ font-size:10.5pt; line-height:1.5; margin:0; padding-left:5mm; }}
.foot {{ margin-top:5mm; border-top:0.4pt solid #000; padding-top:1.2mm;
         font-size:9.5pt; font-style:italic; color:#444; line-height:1.45; }}
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

  <p class="setup">Взрослому. Речь ребёнка — чёткая, неторопливая, с выделенным
  звуком [{_e(m['sound_label'])}]. Читаете вы; ребёнок слушает, отвечает, пересказывает.</p>

  <h1>{_e(r['printed_title'])}</h1>
  <div class="story">{body}</div>

  <section class="block">
    <div class="bhead"><span class="btitle">Вопросы</span>
      <span class="task">Отвечать полным предложением, следить за звуком.</span></div>
    <ol class="q">{qs}</ol>
  </section>

  {extra_block}

  <section class="block">
    <div class="bhead"><span class="btitle">Как вести</span></div>
    <ol class="steps">{steps}</ol>
  </section>

  <div class="foot">
    Звук в этом рассказе встречается чаще, чем в обычной речи, — так и задумано:
    это материал для закрепления, а не образец разговора. Слова подобраны так,
    чтобы в них не было звуков, которые у ребёнка сейчас не получаются.
  </div>
</div>
</body>
</html>
"""
