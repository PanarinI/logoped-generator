# -*- coding: utf-8 -*-
"""
propisi.py — ПРОПИСИ: линия, которую ребёнок ведёт, произнося звук.

Это прямая просьба логопеда Ольги Субботиной (ГОЛОСА.md): на её втором фото —
подборка из 10 образцов «линия + слог». Ребёнок ведёт пальцем или карандашом
по линии, ПРОИЗНОСЯ звук на протяжении всей линии, а в конце линии стоит
гласная — так и собирается слог: Р ~~~~ А = РА.

ИСТОЧНИК КАНОНА (найден 2026-08-06, изданное пособие):
    «Нужно обвести трафарет и произнести: с-са. Вот и получился первый пузырь
    (аналогично отрабатываются слоги с-сы, с-сэ, с-со, с-су)»
        — Борисова Е.А. «Индивидуальные логопедические занятия с дошкольниками»,
          М.: ТЦ Сфера, 2008
Это доказывает главное: обводка здесь НЕ «мелкая моторика в довесок», а
НОСИТЕЛЬ речевого материала — линия и звук идут одновременно. Формат законен
не только по просьбе практика, но и по изданному пособию.

ФОРМА ЛИНИИ КОДИРУЕТ ГОЛОС, И ОНА ЖЕ РАНЖИРУЕТСЯ ПО СЛОЖНОСТИ
─────────────────────────────────────────────────────────────────────
⚠ Здесь стояла НАША гипотеза, выданная за канон («линия кодирует ВЫДОХ, а не
сложность; петли — простейшее»). Проверка 2026-08-06 её опровергла. Цепочка
подмены прослежена на три звена: в research/logoped_metodbaza:29 стоит
«Линия дорожки кодирует ВЫДОХ ✅», но цитата под этим ✅ (Спивак: «произноси
звук л длительно на одном выдохе») НИКАКОЙ ЛИНИИ не содержит; в ГОЛОСА.md:107
честно написано «НАШ разбор канона»; сюда слово «наш» уже не доехало.

Что говорит НАЙДЕННЫЙ источник — Попова Н.О., учитель-логопед, «Звуковые
дорожки для автоматизации звука Р», nsportal, 19.05.2022 (самодельное пособие
практика: доказывает бытование приёма, не канон издания):
  ✅ «Вариант 1. Самый простой (улитка). Ребенок произносит звук Р и проводит
     пальчиком по линии стараясь дойти до финиша… произносить звук не прерываясь»
  ✅ «Вариант 2. Посложней… Линия идет вверх, и ребенок старается произнести звук
     более звонко или мягко, линия-вниз голос необходимо сделать ниже»
  ✅ «Вариант 3. Самый сложный. Используются звуковые дорожки с прерывистыми
     линиями. Ребёнку необходимо коротко или длинно произносить звук»

Отсюда, с честными тирами:
  ✅ горка вверх/вниз  = высота голоса
  ✅ прерывистая линия = отрывисто, и это САМЫЙ СЛОЖНЫЙ вариант
  ✅ непрерывная линия = простейший вариант; простейшая названа УЛИТКА (спираль)
  ❓ петли — про них не сказал никто; наше «петли простейшие» снято
  ❓ «длина линии = длительность выдоха» — слово «выдох» в источнике стоит только
     в общем списке задач и ни к одной линии не привязано
  🔶 «нельзя наращивать нагрузку к низу листа» — наш довод, источника нет;
     у Поповой занятие идёт КАК РАЗ от простого к сложному

Поэтому порядок форм здесь — от простой к сложной (улитка → непрерывные →
прерывистая), а не «ровный по трудности», как было записано раньше.

ЧТО ЗДЕСЬ ГАРАНТИРОВАНО КОДОМ
─────────────────────────────────────────────────────────────────────
• Слог собирается тем же движком, что лист и дорожка (content._syllable_text
  + content.ortho), поэтому орфография верна: после Ш печатается «ши», не «шы»,
  а у мягкой цели выходит «ля», а не «л'а».
• Гласные — пятёрка с [Э]: правило 11 («слоговой блок ≤ ¼ словесного»)
  действует только на ЛИСТЕ, где есть словесный блок. Здесь его нет.
• Ни одной картинки не требуется — линия рисуется кодом. Значит формат не ждёт
  банка иллюстраций и выкладывается сразу.

ЧЕГО ЗДЕСЬ НЕТ (называю вслух)
─────────────────────────────────────────────────────────────────────
• Стечений (КРА, АРТ): в стечении есть второй согласный, и он может оказаться
  звуком, которого у ребёнка нет. Как и на дорожке, фрейм брать неоткуда.
• Сюжетных персонажей по краям линии (у Ольги на образцах лев, машина, собака).
  Механика без них работает, лист суше. Появятся с банком картинок.
"""
from __future__ import annotations

import html
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import content as C            # noqa: E402
import phonetics as _P         # noqa: E402


class PropisiError(Exception):
    """Прописи собрать нельзя — с человеческим объяснением."""


# Прописи строятся только на «чистых» слогах — тех, где кроме целевого звука
# и гласной ничего нет. Со стечением второй согласный не проверить (см. шапку).
PROPISI_TYPES = ("direct", "reverse")

ROWS_DEFAULT = 4

# ── геометрия листа (мм, А4 книжная) ────────────────────────────────
PAGE_W, PAGE_H = 210.0, 297.0
MARGIN_L, MARGIN_R = 16.0, 12.0
LINE_W = PAGE_W - MARGIN_L - MARGIN_R      # рабочая ширина
ROW_H = 34.0                                # высота одной строки-дорожки


# ── ГЕОМЕТРИЯ: единый закон для всех линий ──────────────────────────
# Любая дорожка ОБЯЗАНА начинаться ровно в точке старта и заканчиваться у
# буквы, на одной с ними высоте. Иначе ребёнок не понимает, откуда вести и
# куда приехал: на первом же листе горки, петли и зигзаг стартовали ниже
# точки, а «улитка» вышла каракулей. Всё, что рисуется ниже, держит контракт:
#     path начинается в (0, yc) и кончается в (w, yc).
def _yc(h: float) -> float:
    return h / 2


def _path_straight(w: float, h: float) -> str:
    y = _yc(h)
    return f"M 0 {y:.1f} L {w:.1f} {y:.1f}"


def _path_wave(w: float, h: float, n: int = 3) -> str:
    """Синусоида: ровное непрерывное ведение."""
    y0, amp, pts = _yc(h), h * 0.30, []
    steps = 72
    for i in range(steps + 1):
        x = w * i / steps
        pts.append(f"{x:.1f} {y0 - amp * math.sin(2 * math.pi * n * i / steps):.1f}")
    return "M " + " L ".join(pts)


def _path_arcs(w: float, h: float, n: int = 4) -> str:
    """Горки: голос идёт вверх-вниз (✅ Попова). Начало и конец — на линии."""
    y, seg = _yc(h), w / n
    top = h * 0.12
    d = [f"M 0 {y:.1f}"]
    for i in range(n):
        x0 = seg * i
        d.append(f"Q {x0 + seg / 2:.1f} {top:.1f} {x0 + seg:.1f} {y:.1f}")
    return " ".join(d)


def _path_loops(w: float, h: float, n: int = 5) -> str:
    """Петли: непрерывное ведение. ❓ Источник про них не говорит ничего —
    ни «просто», ни «сложно»; стоят среди непрерывных."""
    y, seg = _yc(h), w / n
    r = min(seg * 0.40, (y - 1.5) / 2.0)
    d = [f"M 0 {y:.1f}"]
    for i in range(n):
        x0 = seg * i
        d.append(f"C {x0 + seg * 0.12:.1f} {y - r * 2:.1f} "
                 f"{x0 + seg * 0.88:.1f} {y - r * 2:.1f} {x0 + seg:.1f} {y:.1f}")
    return " ".join(d)


def _path_spiral(w: float, h: float, turns: int = 2) -> str:
    """«Улитка» — простейший вариант (✅ Попова: «Вариант 1. Самый простой»).

    Раньше здесь была спираль, размазанная по всей строке: читалась как
    каракуля, а не как дорожка. Теперь линия честная: ровный подвод слева,
    компактный завиток посередине, ровный выход к букве.
    """
    y = _yc(h)
    r = min(h * 0.36, w * 0.08)
    cx = w * 0.5
    lead = cx - r * 1.6
    pts = [f"M 0 {y:.1f}", f"L {lead:.1f} {y:.1f}"]
    steps = 90
    for i in range(steps + 1):
        t = i / steps
        ang = math.pi * (1.0 + 2.0 * turns * t)      # старт слева от центра
        rr = r * (1.0 - 0.72 * t)
        pts.append(f"L {cx + rr * math.cos(ang):.1f} {y + rr * math.sin(ang):.1f}")
    pts.append(f"L {cx + r * 1.6:.1f} {y:.1f}")
    pts.append(f"L {w:.1f} {y:.1f}")
    return " ".join(pts)


def _path_zigzag(w: float, h: float, n: int = 6) -> str:
    """Зигзаг: резкая смена высоты голоса. Концы — на линии."""
    y, seg = _yc(h), w / n
    hi, lo = h * 0.16, h * 0.84
    d = [f"M 0 {y:.1f}"]
    for i in range(n):
        d.append(f"L {seg * (i + 0.5):.1f} {hi if i % 2 == 0 else lo:.1f}")
        d.append(f"L {seg * (i + 1):.1f} {y:.1f}")
    return " ".join(d)


# Порядок — ОТ ПРОСТОГО К СЛОЖНОМУ, по Поповой (см. шапку): улитка названа
# простейшей, прерывистая линия — самой сложной. Внутри непрерывных порядок
# наш (🔶): прямая проще волны, волна проще горок и петель.
SHAPES = (
    ("spiral",   "улитка",  _path_spiral,   "непрерывная"),
    ("straight", "прямая",  _path_straight, "непрерывная"),
    ("wave",     "волна",   _path_wave,     "непрерывная"),
    ("arcs",     "горки",   _path_arcs,     "голос вверх-вниз"),
    ("loops",    "петли",   _path_loops,    "непрерывная"),
    ("zigzag",   "зигзаг",  _path_zigzag,   "голос вверх-вниз"),
)


_NOMINATIVE: Dict[str, str] = {
    "песенка мотора": "мотор",
    "песенка моторчика": "моторчик",
    "песенка самолёта": "самолёт",
    "песенка самолётика": "самолётик",
    "песенка насоса": "насос",
    "песенка насосика": "насосик",
    "песенка змеи": "змея",
    "песенка жука": "жук",
    "песенка щётки": "щётка",
    "песенка комарика": "комарик",
    "комарик звенит": "комарик",
}


def _image_for(sound: str) -> Dict[str, str]:
    """Образ звука из gymnastics.json — тот же, что печатает лист в блоке [2].

    На образцах Ольги слева всегда стоит ПЕРСОНАЖ, издающий звук (львёнок,
    мотор, комар), и он одинаков во всех трёх строках. Берём наш канонный
    образ, чтобы дорожка и лист говорили ребёнку об одном и том же существе.
    """
    label = _P.sound_label(sound)
    try:
        import json
        data = json.loads((HERE / "gymnastics.json").read_text(encoding="utf-8"))
        items = data.get("images", {}).get(label) or []
        if not isinstance(items, list):
            items = [items]
        best = [i for i in items
                if i.get("recommended") and i.get("stage") == "автоматизация"]
        it = (best or items or [{}])[0]
        raw = (it.get("image") or "").split("/")[0].strip()
        # В источнике образ записан как «песенка мотора» (родительный падеж) —
        # ребёнку на листе нужен именительный: «мотор».
        name = _NOMINATIVE.get(raw, raw.replace("песенка ", ""))
        return {"name": name, "utterance": it.get("utterance") or "",
                "tier": it.get("tier") or ""}
    except Exception:
        return {"name": "", "utterance": "", "tier": ""}


# ТРИ ДОРОЖКИ — НАРАСТАЕТ ДЛИНА, А НЕ УЗОР
# ─────────────────────────────────────────────────────────────────────
# Решение принято 2026-08-06, и вот на чём стоит.
# Задача дорожки одна: чтобы ребёнок тянул звук ДОЛЬШЕ и не бросил на полпути.
# Отсюда:
#   • ✅ ПОВТОР одного слога тремя строками — это и есть автоматизация
#     (многократное повторение одного материала); так устроены все виденные
#     образцы практиков (ГОЛОСА.md, разбор фото 08-06).
#   • 🔶 НАРАСТАЕТ ДЛИНА пути: чем длиннее дорожка, тем дольше звучит звук.
#     Это наше решение, но оно единственное связывает линию с речевой задачей
#     напрямую. Длительность звучания — измеримая величина, узор — нет.
#   • ⛔ УЗОР УБРАН. Раньше здесь была лестница «улитка → волна → петли» с
#     объяснениями вроде «петли — не отрывая пальца». Ни одно защитить нечем:
#     единственный найденный источник — самодельное пособие практика, а таких
#     самоделок сколько логопедов, столько и вариантов. Форма линии в них —
#     оформление, а не метод. Выдавать оформление за метод — брак по закону
#     проекта №1.
# Форма одна: пологая волна. Прямая не даёт ощущения пути, петли и зигзаги
# перетягивают внимание на руку, а работать должен звук.
LADDER = (
    (0.62, "короткая", "тянем до буквы, не отрывая пальца"),
    (0.82, "средняя",  "теперь дорожка длиннее — звук тянется дольше"),
    (1.00, "длинная",  "самая длинная: тянем ровно, не торопясь"),
)


def build_propisi(sound: str = "р",
                  syl_type: str = "direct",
                  vowel: Optional[str] = None,
                  seed: int = 0) -> Dict[str, Any]:
    """Звуковая дорожка: ОДИН слог, три строки по нарастанию сложности."""
    if sound not in C.WORDS_BY_SOUND:
        raise PropisiError(
            f"звука [{_P.sound_label(sound)}] в генераторе нет; собраны: "
            + ", ".join(_P.sound_label(s) for s in sorted(C.WORDS_BY_SOUND)))
    if syl_type not in PROPISI_TYPES:
        raise PropisiError(
            "звуковая дорожка строится на прямых и обратных слогах: в стечении "
            "есть второй согласный, и его чистоту без словаря не проверить")

    # Ряд гласных берём НЕ у листа: там четвёрка потому, что действует правило 11
    # («слоговой блок ≤ ¼ словесного»), а здесь словесного блока нет вовсе.
    vowels = list(C.SYL_VOWELS_TRACK if not C.is_soft_target(sound)
                  else C.SYL_VOWELS_SOFT + ("э",))
    if vowel not in vowels:
        vowel = vowels[seed % len(vowels)]

    phon = C._syllable_text(sound, vowel, syl_type)
    syllable = C.ortho(phon)
    image = _image_for(sound)

    lines: List[Dict[str, Any]] = []
    for frac, length_label, hint in LADDER:
        lines.append({
            "length_frac": frac, "length_label": length_label,
            "hint": hint, "_fn": _path_wave,
        })

    return {
        "lines": lines,
        "meta": {
            "sound": sound,
            "sound_label": _P.sound_label(sound),
            "syl_type": syl_type,
            "type_label": C.SYL_TYPE_LABEL.get(syl_type, syl_type),
            "vowel": vowel,
            "syllable": syllable,
            "syllable_phon": phon,
            "utterance": image["utterance"],
            "image_name": image["name"],
            "image_tier": image["tier"],
            "n_rows": len(lines),
        },
    }


def _e(s: Any) -> str:
    return html.escape(str(s), quote=True)


def render_propisi(p: Dict[str, Any]) -> str:
    """Структура -> печатный HTML одного листа А4 (ч/б).

    Устройство взято с образцов Ольги (ГОЛОСА.md, разбор 08-06): слева
    ПЕРСОНАЖ, издающий звук, — один и тот же во всех трёх строках; над линией
    подпись, что тянуть; справа — то, к чему приехали (у нас гласная).
    """
    m = p["meta"]
    label, syll, vowel = m["sound_label"], m["syllable"], m["vowel"]
    utter = m["utterance"] or f"{m['sound']}-{m['sound']}-{m['sound']}"

    rows: List[str] = []
    for i, ln in enumerate(p["lines"], 1):
        full = LINE_W - 46.0
        w = full * ln["length_frac"]
        # число волн держим пропорционально длине — иначе на короткой дорожке
        # волны стали бы частыми, то есть ТРУДНЕЕ, а она должна быть легче
        d = ln["_fn"](w, ROW_H - 8.0, max(2, round(3 * ln["length_frac"])))
        rows.append(f"""
  <div class="row">
    <div class="hero">
      <div class="hero-box"><span>{_e(m['image_name'] or label)}</span></div>
    </div>
    <div class="track-wrap">
      <div class="utter">{_e(utter)}</div>
      <div class="track-row">
        <svg class="track" viewBox="0 0 {w:.1f} {ROW_H - 8.0:.1f}"
             width="{w:.1f}mm" height="{ROW_H - 8.0:.1f}mm"
             xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path d="{d}" fill="none" stroke="#000" stroke-width="0.5"
                stroke-linecap="round" stroke-linejoin="round"
                stroke-dasharray="1.6 1.4"/>
          <circle cx="1.2" cy="{(ROW_H - 8.0) / 2:.1f}" r="1.1" fill="#000"/>
        </svg>
        <div class="finish">{_e(vowel.upper())}</div>
      </div>
      <div class="hint">{i}. {_e(ln['hint'])}</div>
    </div>
  </div>""")

    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<title>Звуковая дорожка [{_e(label)}] — {_e(syll)}</title>
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
h1 {{ font-size:14pt; margin:5mm 0 1mm; font-weight:700; }}
h1 b {{ font-size:20pt; }}
.task {{ font-size:12pt; margin:0 0 6mm; }}
.row {{ display:flex; align-items:center; gap:3mm; height:{ROW_H + 6}mm; }}
.hero {{ width:24mm; flex:0 0 24mm; }}
.hero-box {{ height:22mm; border:0.4pt dashed #999; border-radius:2mm;
   display:flex; align-items:center; justify-content:center; text-align:center;
   font-size:9pt; color:#555; padding:1mm; }}
.track-wrap {{ flex:1 1 auto; }}
.utter {{ font-size:11pt; font-weight:700; letter-spacing:.04em;
   margin:0 0 0.5mm 6mm; }}
.track-row {{ display:flex; align-items:center; gap:2mm; }}
.track {{ display:block; flex:0 0 auto; }}
.hint {{ font-size:8.5pt; color:#444; margin:0.5mm 0 0 6mm; }}
.finish {{ font-size:20pt; font-weight:700; line-height:1; }}
.adult {{ margin-top:6mm; padding-top:2mm; border-top:0.4pt solid #000;
   font-size:9.5pt; line-height:1.45; }}
</style></head><body><div class="page">

<div class="doc">
  <span>Ребёнок <span class="fill"></span></span>
  <span class="badge">Звук [{_e(label)}]</span>
  <span>{_e(m['type_label'])}</span>
  <span>Дата <span class="fill" style="min-width:24mm"></span></span>
</div>

<h1>Звуковая дорожка · слог <b>{_e(syll.upper())}</b></h1>
<p class="task">Веди пальцем по дорожке и тяни звук, пока не доедешь до буквы.
   В конце скажи слог целиком: <b>{_e(syll)}</b>. Каждая следующая дорожка длиннее — звук тянется дольше.</p>
{''.join(rows)}

<div class="adult">
  <b>Взрослому.</b> Слог на всех трёх дорожках <b>один и тот же</b>, и форма
  линии тоже — меняется только <b>длина</b>: каждая следующая дорожка длиннее,
  значит звук тянется дольше. В этом весь смысл: не пройти побольше разных
  слогов, а удержать один звук на всё более длинном выдохе. Не торопите:
  доехали до буквы — произнесли слог целиком.
</div>

</div></body></html>"""


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Прописи: линия + слог")
    ap.add_argument("--sound", default="р")
    ap.add_argument("--type", dest="typ", default="direct",
                    choices=list(PROPISI_TYPES))
    ap.add_argument("--rows", type=int, default=ROWS_DEFAULT)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="propisi_demo.html")
    a = ap.parse_args()
    p = build_propisi(a.sound, a.typ, a.rows, a.seed)
    Path(a.out).write_text(render_propisi(p), encoding="utf-8")
    print(f"{a.out}: [{p['meta']['sound_label']}] "
          f"{' · '.join(l['syllable'] for l in p['lines'])}")
