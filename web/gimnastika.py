# -*- coding: utf-8 -*-
"""Виджет «Артикуляционная гимнастика» — первая страница-кластер (2026-11-23).

Зачем свой виджет, а не главный генератор в рамке. Канон Site Builders 2.0: кластер —
«примерно одна функция, названная разными словами», и при смене кластера меняется сам
виджет (`app-studio/knowledge-base/site-builders-2/01-vstrecha-01.md` §7); у страницы
кластера свой виджет первым экраном (`03-vstrecha-03.md` §6.1). Встроен прямо в
страницу, а не рамкой: содержимое iframe поисковик не индексирует.

ЧТО ДЕЛАЕТ — то же, что весь Логозвук: собирает материал под звук и даёт его напечатать.
Звук → восемь упражнений его комплекса (все на виду) → отмечают 2–3 → два материала:
  · КАРТОЧКИ НА ЗАНЯТИЕ — одна сторона: картинка-образ и название, четыре на А4, режут по
    пунктиру. Фомичёва 1989: «картинка-образ дается ребенку…, а подробная запись — для
    родителей» — подробная запись живёт в листе домой. Оборот «как делать» был до 25.11 и снят:
    автор — логопед на занятии его не читает. ТЕМЫ меняют вид карточки — одни и те же
    упражнения в новом наряде: за такое переодевание платят (`ГОЛОСА.md`, logosha_pro: семь
    тематических картотек одной механики). Мотивы темы рисует код (линия + заливка), в ч/б
    остаётся линия.
  · ЛИСТ ДОМОЙ — для родителя: картинки, как делать, сколько, таблица отметок на неделю.
Оба сначала на экране, правка прямо на листе, потом печать или PDF (лист домой — ещё Word).

⚠ 24.11 здесь было «занятие на экране» со счётом и схемой рта. Автор: «смысл виджета, если
нет звука, я не понимаю… он реально должен сидеть перед зеркалом», «рот очень отвратительно
выглядит», голос синтеза — «невозможно допускать». На занятии образец — лицо взрослого,
контроль — зеркало, счёт — голос взрослого (Фомичёва, Буденная); экран этого не заменил.
Код занятия и рта — в истории git (коммит 21ff809).

ЯЗЫК — для не-специалиста: «сколько» простыми словами (`schet.korotko`). Карточки Word не
отдают: таблица Word не держит вырезную раскладку с мотивами — честнее не предлагать.

Данные — только `gymnastics.json`; упражнения постановки (`excluded_from_sheet`) сюда не
попадают. Ч и Ц: источник называет комплексы по группе — «для свистящих звуков с, з, ц»,
«для шипящих звуков ш, ж, ч, щ». Практика — `research/site/gimnastika_praktika_2026-11-24.md`,
вид — `dizajn/KONCEPCIYA.md`.
"""
from __future__ import annotations

import html
import json
import os
import re
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
GYM_PATH = os.path.join(HERE, "..", "logoped_slovar", "gymnastics.json")
# Сказки о Весёлом Язычке для листа домой — тексты наши (см. `_zachem` в файле).
SKAZKI_PATH = os.path.join(HERE, "..", "logoped_slovar", "gimnastika_skazki.json")

# Порядок — как в главном виджете (`C.WORDS_BY_SOUND`), Ч и Ц — в конце.
ORDER = ["Р", "Рь", "Л", "Ль", "С", "Сь", "З", "Зь", "Ш", "Ж", "Щ", "Ч", "Ц"]

# Ч и Ц — см. шапку: (чей комплекс берём, у кого в файле цитата группы).
GROUP_FROM = {"Ч": ("Ш", "Ж"), "Ц": ("С", "З")}

SOURCE_LABEL = {
    "fomicheva_1989": "Фомичёва, 1989",
    "spivak_2007_shipyashchie": "Спивак, 2007",
    "spivak_2007_sonornye": "Спивак, 2007",
}
KARTOTEKA = "картотеки логопедов"

# Темы карточек: имя для экрана и мотив лицевой стороны. Мотивы — линия + заливка,
# цвета задаёт CSS листа (в ч/б заливка белая, линия чёрная).
TEMY = [("bez", "без темы"), ("osen", "осень"), ("zima", "зима"), ("kosmos", "космос"), ("more", "море")]


def _quote(text: str) -> str:
    m = re.search(r"«([^»]+)»", text or "")
    return m.group(1) if m else ""


def data() -> Dict[str, Any]:
    """Комплексы по звукам — в том виде, в каком их показывает экран."""
    with open(GYM_PATH, encoding="utf-8") as fh:
        gym = json.load(fh)
    ex = {e["id"]: e for e in gym["exercises"]}
    refs = {s["id"]: s["ref"] for s in gym["sources"]}
    comps = gym["complexes"]

    def pic(eid: str, kind: str) -> str:
        # Картинки собирает `tools/gim_kartinki.py` в web/img. Нет файла — нет
        # картинки (закон 14). Метка времени в адресе: у /img/ длинный кэш (закон 17).
        path = os.path.join(HERE, "img", f"gim-{eid}-{kind}.png")
        if not os.path.isfile(path):
            return ""
        return f"/img/gim-{eid}-{kind}.png?v={int(os.path.getmtime(path))}"

    def card(eid: str) -> Dict[str, Any]:
        e = ex[eid]
        ids = e.get("sources", [])
        labels: List[str] = []
        for s in ids:
            lab = SOURCE_LABEL.get(s, KARTOTEKA)
            if lab not in labels:
                labels.append(lab)
        schet = e.get("schet") or {}
        return {
            "name": e["name"],
            "child": e.get("sheet_hint", ""),
            "how": e.get("description", ""),
            "why": e.get("purpose", ""),
            "dose": e.get("dosage", ""),
            "props": e.get("rekvizit") or "",
            "src": " · ".join(labels),
            "src_full": "\n".join(refs.get(s, s) for s in ids),
            "obraz": pic(eid, "obraz"),
            "obraz_bw": pic(eid, "obraz-bw"),
            "litso": pic(eid, "litso"),
            "litso_bw": pic(eid, "litso-bw"),
            "fazy": schet.get("fazy", []),
            "korotko": schet.get("korotko", ""),
        }

    def queue(c: Dict[str, Any]) -> List[str]:
        # Порядок карточек: набор недели, потом запас; с реквизитом — в конце.
        skip = set(c.get("excluded_from_sheet", []))
        ids = [i for i in c["sheet_4"] + c.get("alternates", []) if i in ex and i not in skip]
        ids = list(dict.fromkeys(ids))
        return ([i for i in ids if not ex[i].get("rekvizit")] +
                [i for i in ids if ex[i].get("rekvizit")])

    # Упражнение лежит в данных ОДИН раз, звуки ссылаются на него по id: у [С], [Сь], [З], [Зь]
    # и [Ц] комплекс один и тот же — без этого страница таскала бы его пять раз.
    cards: Dict[str, Dict[str, Any]] = {}
    sounds: List[Dict[str, Any]] = []
    for s in ORDER:
        if s in comps:
            c = comps[s]
            base = c.get("derived_from")
            note = ""
            if base and c.get("derivation_tier") == "ours":
                note = (f"Отдельного комплекса для [{s}] в источнике нет — "
                        f"взят комплекс [{base}].")
            elif base:
                q = _quote(c.get("derivation_note", ""))
                note = f"Фомичёва: «{q}»." if q else ""
        elif s in GROUP_FROM:
            base, quote_from = GROUP_FROM[s]
            c = comps[base]
            q = _quote(comps[quote_from].get("derivation_note", ""))
            note = f"Фомичёва: «{q}»." if q else ""
        else:
            continue
        ids = queue(c)
        for i in ids:
            cards.setdefault(i, card(i))
        sounds.append({"key": s, "note": note, "ids": ids})
    with open(SKAZKI_PATH, encoding="utf-8") as fh:
        skazki = json.load(fh)["temy"]
    # В данные страницы — только строки упражнений, которые на ней есть.
    for v in skazki.values():
        v["ex"] = {k: s for k, s in v["ex"].items() if k in cards}
    return {"sounds": sounds, "ex": cards, "temy": TEMY, "skazki": skazki}


CSS = r"""
.gim{--g-paper:#f7f5f1;--g-card:#fff;--g-ink:#16191d;--g-muted:#565d66;--g-line:#e6e2da;--g-edge:#d5d0c6;
  --g-brand:#2f6b4f;--g-brand-edge:#1f4e39;--g-tongue:#e8806e;--g-tongue-edge:#c9624f;--g-chip:#f1ede4;
  --g-round:ui-rounded,"SF Pro Rounded","Nunito","Segoe UI",system-ui,sans-serif;
  background:var(--g-paper);padding:var(--s4) var(--s4) var(--s5);color:var(--g-ink)}
.gim-in{max-width:60rem;margin:0 auto}
.gim-desk{display:grid;grid-template-columns:13.5rem minmax(0,1fr);gap:var(--s4);align-items:start}
.gim-label{margin:0 0 6px;font-size:.82rem;letter-spacing:.02em;color:var(--g-muted)}
.gim-sounds{display:grid;grid-template-columns:repeat(5,1fr);gap:5px}
.gim-sounds button{min-width:0;padding:7px 0 6px;border:1px solid var(--g-edge);border-radius:999px;background:#fff;
  font:inherit;font-size:1rem;cursor:pointer;color:var(--g-ink);box-shadow:0 2px 0 var(--g-edge)}
.gim-sounds button[aria-pressed="true"]{background:var(--g-brand);border-color:var(--g-brand);color:#fff;
  box-shadow:0 2px 0 var(--g-brand-edge)}
.gim-note{margin:8px 0 0;font-size:.8rem;line-height:1.4;color:var(--g-muted)}
.gim-note:empty,.gim-warn:empty,.gim-err:empty{display:none}
.gim-how{margin:var(--s4) 0 0;padding:0;list-style:none;font-size:.84rem;line-height:1.4;color:var(--g-muted)}
.gim-how li{display:flex;gap:8px;margin:0 0 6px}
.gim-how b{flex:none;width:20px;height:20px;border-radius:50%;background:var(--g-chip);color:var(--g-ink);font-size:.75rem;
  display:flex;align-items:center;justify-content:center}
.gim-head{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin:0 0 8px}
.gim-head p{margin:0;font-size:.95rem}
.gim-head b{font-weight:600}
.gim-count-sel{font-size:.82rem;color:var(--g-muted);white-space:nowrap}
.gim-grid{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.gim-card{position:relative;height:13.6rem;perspective:900px;margin:0}
.gim-card-in{position:relative;width:100%;height:100%;transition:transform .45s ease;transform-style:preserve-3d}
.gim-card.is-flip .gim-card-in{transform:rotateY(180deg)}
.gim-face{position:absolute;inset:0;backface-visibility:hidden;-webkit-backface-visibility:hidden;border-radius:14px;
  background:var(--g-card);border:1px solid var(--g-line);box-shadow:0 2px 0 var(--g-line)}
.gim-back{transform:rotateY(180deg)}
.gim-back-text{position:absolute;inset:0;padding:10px 12px 36px;overflow:auto;font-size:.82rem;line-height:1.4}
.gim-card.is-on .gim-front{border:2px solid var(--g-brand);box-shadow:0 3px 0 var(--g-brand-edge)}
.gim-pick{display:flex;flex-direction:column;align-items:center;width:100%;height:100%;padding:12px 8px 10px;border:0;
  background:none;font:inherit;color:inherit;cursor:pointer;border-radius:14px;text-align:center}
.gim-pick img{width:6rem;height:6rem;object-fit:contain;margin:2px 0}
.gim-pick .noimg{width:6rem;height:6rem}
.gim-cname{font-family:var(--g-round);font-weight:600;font-size:.98rem;line-height:1.2}
.gim-dose{margin-top:5px;padding:2px 8px;border-radius:8px;background:var(--g-chip);font-size:.72rem;line-height:1.3;
  color:var(--g-muted)}
.gim-num{position:absolute;top:-8px;left:-8px;width:28px;height:28px;border-radius:50%;background:var(--g-brand);
  color:#fff;font-family:var(--g-round);font-weight:700;display:flex;align-items:center;justify-content:center;
  box-shadow:0 2px 0 var(--g-brand-edge);z-index:3;pointer-events:none}
.is-flip .gim-num{display:none}
.gim-flip{position:absolute;right:6px;top:6px;width:26px;height:26px;border-radius:50%;border:1px solid var(--g-edge);
  background:#fff;font:inherit;font-size:.85rem;line-height:1;cursor:pointer;color:var(--g-muted);z-index:2}
.gim-back .gim-flip{top:auto;bottom:6px}
.gim-back p{margin:0 0 6px}
.gim-bname{font-family:var(--g-round);font-weight:600;font-size:.95rem}
.gim-child{font-style:italic}
.gim-small{color:var(--g-muted);font-size:.76rem}
.gim-warn{margin:8px 0 0;font-size:.82rem;line-height:1.4;color:#8a5a00}
.gim-shelf-row{display:flex;flex-wrap:wrap;align-items:center;gap:var(--s2);margin-top:var(--s4);padding-top:var(--s3);
  border-top:1px solid var(--g-line)}
.gim-hint{margin:0 auto 0 0;font-size:.85rem;color:var(--g-muted)}
.gim-btn{font:inherit;font-size:1rem;padding:11px 20px;border-radius:999px;border:1px solid var(--g-edge);background:#fff;
  cursor:pointer;color:var(--g-ink);box-shadow:0 3px 0 var(--g-edge);transition:transform .06s,box-shadow .06s}
.gim-btn:active{transform:translateY(2px);box-shadow:0 1px 0 var(--g-edge)}
.gim-btn[disabled]{opacity:.6;cursor:default}
.gim-btn[hidden]{display:none}
.gim-go{background:var(--g-tongue);border-color:var(--g-tongue);color:var(--g-ink);font-weight:600;
  box-shadow:0 3px 0 var(--g-tongue-edge)}
.gim-go:active{box-shadow:0 1px 0 var(--g-tongue-edge)}
.gim-sm{font-size:.9rem;padding:8px 14px}
.gim-seg{display:inline-flex;flex-wrap:wrap;border:1px solid var(--g-edge);border-radius:18px;overflow:hidden;background:#fff}
.gim-seg button{font:inherit;font-size:.86rem;padding:5px 12px;border:0;background:none;cursor:pointer;color:var(--g-ink)}
.gim-seg button[aria-pressed="true"]{background:var(--g-brand);color:#fff}
@media (max-width:760px){
  .gim{padding:var(--s3) var(--s3) var(--s4)}
  .gim-desk{grid-template-columns:minmax(0,1fr)}
  .gim-sounds{grid-template-columns:repeat(7,1fr)}
  .gim-how{display:none}
  .gim-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .gim-card{height:12.6rem}
  /* На телефоне картотека длинная — полочка с кнопками едет вместе с экраном. */
  .gim-shelf-row{position:sticky;bottom:0;z-index:5;margin:var(--s3) calc(-1 * var(--s3)) 0;
    padding:10px var(--s3) calc(10px + env(safe-area-inset-bottom));background:var(--g-paper);
    border-top:1px solid var(--g-line);box-shadow:0 -6px 14px rgba(22,25,29,.06)}
  .gim-hint{display:none}
  .gim-shelf-row .gim-btn{flex:1 1 auto}
}
html.gim-lock,html.gim-lock body{overflow:hidden}
/* ── материал на экране: лист домой или карточки ───────────────────── */
.gim-sheet{position:fixed;inset:0;z-index:1000;display:flex;flex-direction:column;background:#e9e6df}
.gim-sheet[hidden]{display:none}
.gim-sheet-bar{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;padding:10px 16px;background:var(--g-paper);
  border-bottom:1px solid var(--g-line)}
.gim-sheet-bar h2{margin:0 auto 0 4px;font-size:1.05rem;font-weight:600}
.gim-opts{display:flex;flex-wrap:wrap;align-items:center;gap:8px 16px;padding:8px 16px;background:var(--g-paper);
  border-bottom:1px solid var(--g-line);font-size:.88rem;color:var(--g-muted)}
.gim-opt{display:inline-flex;flex-wrap:wrap;align-items:center;gap:6px}
.gim-opt[hidden]{display:none}
.gim-chk{display:inline-flex;align-items:center;gap:6px;cursor:pointer;color:var(--g-ink)}
.gim-err{margin:0;padding:6px 16px;background:#fdf5ea;color:#8a5a00;font-size:.88rem}
.gim-sheet iframe{flex:1;width:100%;border:0;background:#e9e6df}
@media (max-width:760px){.gim-sheet-bar h2{flex-basis:100%;margin:0}}
/* ── колесо: ребёнок крутит, колесо выбирает упражнение ───────────────── */
.gim-wheel{position:fixed;inset:0;z-index:1000;display:flex;flex-direction:column;background:var(--g-paper);color:var(--g-ink)}
.gim-wheel[hidden]{display:none}
.gim-wh-main{flex:1;display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr);gap:24px;align-items:center;
  padding:16px 24px;overflow:auto;max-width:70rem;width:100%;margin:0 auto;box-sizing:border-box}
.gim-wh-stage{position:relative;width:min(72vh,100%,560px);aspect-ratio:1;margin:0 auto}
.gim-wh-disc{position:absolute;inset:0;transition:transform 4.2s cubic-bezier(.15,.7,.2,1)}
.gim-wh-disc svg{width:100%;height:100%;display:block}
.gim-wh-pin{position:absolute;left:50%;top:-6px;width:34px;height:40px;transform:translateX(-50%);z-index:2;
  filter:drop-shadow(0 2px 0 var(--g-tongue-edge))}
.gim-wh-hub{position:absolute;left:50%;top:50%;width:27%;aspect-ratio:1;transform:translate(-50%,-50%);border-radius:50%;
  border:0;background:var(--g-tongue);color:var(--g-ink);font:700 clamp(1rem,2.6vw,1.45rem)/1.1 var(--g-round);cursor:pointer;
  box-shadow:0 4px 0 var(--g-tongue-edge),0 0 0 6px #fff;z-index:2}
.gim-wh-hub:active{transform:translate(-50%,calc(-50% + 3px));box-shadow:0 1px 0 var(--g-tongue-edge),0 0 0 6px #fff}
.gim-wh-hub[disabled]{cursor:default}
.gim-wh-res{text-align:center;min-height:16rem;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:8px}
.gim-wh-res img{width:min(15rem,60vw);height:min(15rem,60vw);object-fit:contain;mix-blend-mode:multiply}
.gim-wh-name{font:700 2rem/1.15 var(--g-round);margin:0}
.gim-wh-child{margin:0;font-size:1.1rem}
.gim-wh-dose{margin:0;padding:4px 12px;border-radius:10px;background:var(--g-chip);color:var(--g-muted);font-size:.95rem}
.gim-wh-hint{margin:0;font-size:1.05rem;color:var(--g-muted);max-width:22rem}
.gim-wh-left{font-size:.88rem;color:var(--g-muted);margin:6px 0 0}
@media (max-width:760px){.gim-wh-main{grid-template-columns:minmax(0,1fr);padding:12px 16px;gap:12px}
  .gim-wh-stage{width:min(86vw,46vh)}.gim-wh-res{min-height:0}.gim-wh-res img{width:8rem;height:8rem}
  .gim-wh-name{font-size:1.5rem}}
@media (prefers-reduced-motion:reduce){.gim-wh-disc{transition-duration:.6s}}
"""

# Мотивы тем — SVG в координатах 0..100 (угол карточки). Класс .f — заливка цветом темы,
# .s — линия. Одна и та же линия печатается в ч/б.
MOTIF = {
    "osen": ('<g class="m m-osen"><path class="f a1" d="M18 8C30 14 33 30 20 44C7 30 8 14 18 8Z"/>'
             '<path class="s" d="M19 11L20 46"/>'
             '<path class="f a2" d="M46 6C55 13 56 26 45 36C35 26 36 13 46 6Z" transform="rotate(28 46 22)"/>'
             '<path class="s" d="M46 9L45 38" transform="rotate(28 46 22)"/>'
             '<path class="f a3" d="M10 50C20 55 22 67 12 77C2 67 2 56 10 50Z" transform="rotate(-24 12 64)"/></g>'),
    "zima": ('<g class="m m-zima">' + "".join(
        f'<g transform="translate({x} {y}) scale({k})">'
        + "".join(f'<g transform="rotate({a})"><path class="s" d="M0 -14V14"/><path class="s" d="M0 -9L-4 -13M0 -9L4 -13"/>'
                  f'<path class="s" d="M0 9L-4 13M0 9L4 13"/></g>' for a in (0, 60, 120))
        + '</g>' for x, y, k in ((20, 20, 1.1), (50, 12, .7), (14, 52, .65))) + '</g>'),
    "kosmos": ('<g class="m m-kosmos"><circle class="f a1" cx="26" cy="26" r="12"/>'
               '<ellipse class="s" cx="26" cy="26" rx="21" ry="6" transform="rotate(-18 26 26)"/>'
               + "".join(f'<path class="f a2" d="M{x} {y - 7}L{x + 2.1} {y - 2.2}L{x + 7} {y - 2.2}L{x + 3} {y + 1}'
                         f'L{x + 4.4} {y + 6}L{x} {y + 3}L{x - 4.4} {y + 6}L{x - 3} {y + 1}L{x - 7} {y - 2.2}'
                         f'L{x - 2.1} {y - 2.2}Z"/>' for x, y in ((58, 12), (12, 58), (50, 44))) + '</g>'),
    "more": ('<g class="m m-more"><path class="f a1" d="M8 30C14 20 34 20 40 30C34 40 14 40 8 30Z"/>'
             '<path class="f a3" d="M40 30L52 22L50 30L52 38Z"/><circle class="s" cx="16" cy="28" r="1.6"/>'
             '<circle class="s" cx="30" cy="12" r="3"/><circle class="s" cx="40" cy="6" r="2"/>'
             '<circle class="s" cx="14" cy="54" r="2.6"/></g>'),
}

JS = r"""
(function () {
  var D = JSON.parse(document.getElementById('gim-data').textContent);
  var MOTIF = JSON.parse(document.getElementById('gim-motif').textContent);
  D.sounds.forEach(function (s) { s.ex = s.ids.map(function (id) { return D.ex[id]; }); });
  var root = document.getElementById('gim');
  var $ = function (id) { return document.getElementById(id); };
  // Фомичёва 1989: «Не следует предлагать детям более двух-трех упражнений».
  var MAX = 3;
  var S = { i: 0, sel: [], flip: {} };
  var esc = function (t) {
    return String(t || '').replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  };
  var cur = function () { return D.sounds[S.i]; };
  var at = function (j) { return cur().ex[j]; };
  function warn(t) { $('gim-warn').textContent = t || ''; }
  function reset() {
    S.sel = []; S.flip = {}; warn('');
    for (var j = 0; j < cur().ex.length && S.sel.length < MAX; j++) S.sel.push(j);
  }
  function plan(c) {
    var f = c.fazy.filter(function (x) { return x.vid !== 'povtor'; })[0] || {};
    return (c.korotko || '').replace('{do}', f['do'] || 10).replace('{derzhat}', f.derzhat || 3);
  }
  // Первая БУКВА заглавная, даже если строка начинается с кавычки («покрась» → «Покрась»).
  function cap(t) { return String(t || '').replace(/[a-zа-яё]/i, function (ch) { return ch.toUpperCase(); }); }
  var holds = function (c) { return c.fazy.some(function (f) { return f.vid === 'derzhim' && f['do'] >= 10; }); };
  // Фомичёва: удерживание «под счет взрослого от 1 до 5 с постепенным увеличением его до 10».
  var HOLD_TIP = 'Трудно держать до 10 — начните с 5 и постепенно доводите до 10 (Фомичёва).';

  // ── стол: картотека ──────────────────────────────────────────────────
  function cardHtml(c, j) {
    var n = S.sel.indexOf(j), on = n >= 0, fl = !!S.flip[j];
    var img = c.obraz || c.litso;
    return '<li class="gim-card' + (on ? ' is-on' : '') + (fl ? ' is-flip' : '') + '">' +
      (on ? '<span class="gim-num" aria-hidden="true">' + (n + 1) + '</span>' : '') +
      '<div class="gim-card-in">' +
      '<div class="gim-face gim-front"' + (fl ? ' aria-hidden="true"' : '') + '>' +
      '<button type="button" class="gim-pick" data-j="' + j + '" aria-pressed="' + on + '"' + (fl ? ' tabindex="-1"' : '') +
      ' title="' + (on ? 'Убрать из занятия' : 'Взять в занятие') + '">' +
      (img ? '<img src="' + esc(img) + '" alt="" loading="lazy">' : '<span class="noimg"></span>') +
      '<span class="gim-cname">' + esc(c.name) + '</span>' +
      '<span class="gim-dose">' + esc(plan(c)) + (c.props ? ' · нужна ' + esc(c.props) : '') + '</span>' +
      '</button>' +
      '<button type="button" class="gim-flip" data-f="' + j + '" title="Как делать и сколько раз" aria-label="Как делать: ' +
      esc(c.name) + '"' + (fl ? ' tabindex="-1"' : '') + '>?</button></div>' +
      '<div class="gim-face gim-back"' + (fl ? '' : ' aria-hidden="true"') + '><div class="gim-back-text">' +
      '<p class="gim-bname">' + esc(c.name) + '</p>' +
      (c.child ? '<p class="gim-child">' + esc(c.child) + '</p>' : '') +
      '<p>' + esc(c.how) + '</p>' +
      '<p><b>Сколько:</b> ' + esc(plan(c)) + (c.props ? '. <b>Понадобится:</b> ' + esc(c.props) : '') + '</p>' +
      (holds(c) ? '<p class="gim-small">' + HOLD_TIP + '</p>' : '') +
      (c.why ? '<p class="gim-small">Зачем: ' + esc(c.why) + '</p>' : '') +
      '<p class="gim-small" title="' + esc(c.src_full) + '">Источник: ' + esc(c.src) + '</p></div>' +
      '<button type="button" class="gim-flip" data-f="' + j + '" title="Назад к картинке" aria-label="Назад к картинке"' +
      (fl ? '' : ' tabindex="-1"') + '>↩</button></div>' +
      '</div></li>';
  }
  function render() {
    var s = cur();
    root.querySelectorAll('.gim-sounds button').forEach(function (b, k) {
      b.setAttribute('aria-pressed', k === S.i ? 'true' : 'false');
    });
    $('gim-note').textContent = s.note || '';
    $('gim-for').textContent = '[' + s.key + ']';
    $('gim-nsel').textContent = 'отмечено ' + S.sel.length + ' из ' + s.ex.length;
    $('gim-grid').innerHTML = s.ex.map(cardHtml).join('');
  }

  root.querySelectorAll('.gim-sounds button').forEach(function (b, k) {
    b.addEventListener('click', function () { S.i = k; reset(); render(); });
  });
  $('gim-grid').addEventListener('click', function (ev) {
    var f = ev.target.closest('[data-f]');
    if (f) {
      var jf = +f.dataset.f; S.flip[jf] = !S.flip[jf]; render();
      var back = $('gim-grid').children[jf].querySelector(S.flip[jf] ? '.gim-back .gim-flip' : '.gim-flip');
      if (back) back.focus();
      return;
    }
    var b = ev.target.closest('.gim-pick');
    if (!b) return;
    var j = +b.dataset.j, k = S.sel.indexOf(j);
    if (k >= 0) {
      if (S.sel.length <= 1) { warn('Одно упражнение остаётся отмеченным всегда.'); return; }
      S.sel.splice(k, 1);
    } else {
      if (S.sel.length >= MAX) {
        warn('Не больше трёх за раз: у Фомичёвой «не более двух-трёх упражнений». ' +
             'Сначала уберите одно — щелчком по нему.');
        return;
      }
      S.sel.push(j);
    }
    warn(''); render();
    var again = $('gim-grid').querySelector('.gim-pick[data-j="' + j + '"]');
    if (again) again.focus();
  });

  // ── материал на экране: лист домой или карточки на занятие ───────────
  // Сначала видно, что выйдет; правка — прямо на листе; настройки меняют лист без
  // пересборки, чтобы правки не терялись. Потом печать или PDF (лист — ещё Word).
  var L = { kind: 'list', colour: false, table: true, tema: 'bez', all: false };
  var sheet = $('gim-sheet'), frame = $('gim-sheet-frame');
  var PAGE_CSS = '@page{size:A4;margin:14mm}html{background:#e9e6df}' +
    'body{margin:16px auto;width:182mm;min-height:269mm;box-sizing:border-box;background:#fff;padding:14mm;' +
    'box-shadow:0 2px 12px rgba(0,0,0,.1);font:12pt/1.45 Arial,Helvetica,sans-serif;color:#000;' +
    '-webkit-print-color-adjust:exact;print-color-adjust:exact}' +
    '@media print{html{background:#fff}body{margin:0;width:auto;min-height:0;padding:0;box-shadow:none}}' +
    '@media screen{html.fit body{zoom:var(--z)}}[contenteditable]:focus{outline:none}';
  function pics(c) {
    var bw = c.obraz_bw || c.litso_bw || c.obraz || c.litso, col = c.obraz || c.litso;
    return { bw: bw, col: col };
  }
  function imgTag(c, cls) {
    var p = pics(c);
    return p.bw ? '<img class="' + cls + '" src="' + esc(L.colour ? p.col : p.bw) + '" data-bw="' + esc(p.bw) +
      '" data-col="' + esc(p.col) + '" alt="">' : '';
  }
  function listDoc() {
    var s = cur(), list = S.sel.map(at), days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    var ex = list.map(function (c, n) {
      return '<div class="ex">' + imgTag(c, '') + '<div><b>' + (n + 1) + '. ' + esc(c.name) + '</b> — ' + esc(c.child) +
        '<br>' + esc(c.how) + '<br><i>Сколько: ' + esc(plan(c)) + '.</i>' +
        (c.props ? ' Понадобится: ' + esc(c.props) + '.' : '') + '</div></div>';
    }).join('');
    var head = '<tr><th>Упражнение</th>' + days.map(function (d) { return '<th>' + d + '<br>у · в</th>'; }).join('') + '</tr>';
    var rows = list.map(function (c) {
      return '<tr><td class="n">' + esc(c.name) + '</td>' + days.map(function () { return '<td>☐ ☐</td>'; }).join('') + '</tr>';
    }).join('');
    // Сказки всех тем лежат в листе сразу, видна одна (класс темы на body): смена темы не
    // пересобирает лист, правки в тексте не теряются. В файл уходит только видимая (`docClone`).
    var tales = Object.keys(D.skazki).map(function (k) {
      var T = D.skazki[k], ids = list.map(function (c) { return s.ids[s.ex.indexOf(c)]; });
      return '<div class="tale s-' + k + '"><svg class="tmot" viewBox="0 0 80 80" aria-hidden="true">' + MOTIF[k] + '</svg>' +
        '<h2>Сказка «' + esc(T.title) + '»</h2>' +
        '<p class="tl-how">Читайте вслух. Где стрелка — остановитесь и сделайте упражнение вместе с ребёнком.</p>' +
        '<p>' + esc(T.intro) + '</p>' +
        list.map(function (c, n) {
          return '<p>' + esc(T.ex[ids[n]] || '') + '<br><b class="do">→ «' + esc(c.name) + '»: ' + esc(plan(c)) + '.</b></p>';
        }).join('') +
        '<p>' + esc(T.outro) + '</p></div>';
    }).join('');
    return '<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">' +
      '<title>Артикуляционная гимнастика на звук [' + esc(s.key) + ']</title><style>' + PAGE_CSS +
      'h1{font-size:17pt;margin:0 0 4pt}.sub{margin:0 0 10pt;color:#333}' +
      '.rule{margin:0 0 12pt;padding:8pt 10pt;border:1px solid #999;border-radius:6pt}' +
      '.ex{display:flex;gap:10pt;margin:0 0 10pt;page-break-inside:avoid}' +
      '.ex img{width:24mm;height:24mm;object-fit:contain;flex:none}.ex b{font-size:13pt}' +
      'table{border-collapse:collapse;width:100%;margin-top:6pt}' +
      'th,td{border:1px solid #000;padding:4pt;font-size:10pt;text-align:center}td.n{text-align:left;width:34%}' +
      '.foot{margin-top:12pt;font-size:9pt;color:#555}body.no-table .tbl{display:none}' +
      '.tale{display:none;position:relative;margin:0 0 12pt;padding:9pt 12pt 6pt;border:1.6pt solid var(--acc);border-radius:8pt;' +
      'background:var(--tint);page-break-inside:avoid}.tale h2{font-size:13.5pt;margin:0 0 2pt;padding-right:16mm}' +
      '.tale p{margin:0 0 5pt}.tale p.tl-how{font-size:9.5pt;color:#444;padding-right:16mm}.do{font-weight:700}' +
      '.tmot{position:absolute;right:3mm;top:2.5mm;width:14mm;height:14mm}.tmot .m{display:inline}' +
      '.tmot .f{stroke:var(--acc);stroke-width:2;stroke-linejoin:round}.tmot .a1{fill:var(--c1)}.tmot .a2{fill:var(--c2)}' +
      '.tmot .a3{fill:var(--c3)}.tmot .s{fill:none;stroke:var(--acc);stroke-width:2.2;stroke-linecap:round}' +
      'body.t-osen .s-osen,body.t-zima .s-zima,body.t-kosmos .s-kosmos,body.t-more .s-more{display:block}' +
      'body{--acc:#000;--tint:#fff;--c1:#fff;--c2:#fff;--c3:#fff}' +
      // Со сказкой лист должен остаться одной страницей: текст и картинки чуть мельче.
      '.tbl{page-break-inside:avoid}body:not(.t-bez){font-size:11pt;line-height:1.36}' +
      'body:not(.t-bez) .rule{margin-bottom:8pt;padding:6pt 9pt}body:not(.t-bez) .tale{margin-bottom:8pt}' +
      'body:not(.t-bez) .ex{margin-bottom:6pt}body:not(.t-bez) .ex img{width:19mm;height:19mm}' +
      'body:not(.t-bez) .ex b{font-size:12pt}body:not(.t-bez) th,body:not(.t-bez) td{padding:2.5pt 4pt}' +
      'body.col.t-osen{--acc:#e08a3c;--tint:#fff8ef;--c1:#f2b35c;--c2:#e5733b;--c3:#d9a441}' +
      'body.col.t-zima{--acc:#5b9bd5;--tint:#f3f8fd}' +
      'body.col.t-kosmos{--acc:#7466cf;--tint:#f6f4ff;--c1:#b9aef2;--c2:#f2c14e;--c3:#f2c14e}' +
      'body.col.t-more{--acc:#2f8fbf;--tint:#eff8fb;--c1:#7cc6e0;--c2:#7cc6e0;--c3:#f08a5d}' +
      '</style></head><body contenteditable="true" spellcheck="false" class="t-' + L.tema + (L.colour ? ' col' : '') +
      (L.table ? '' : ' no-table') + '">' +
      '<h1>Артикуляционная гимнастика на звук [' + esc(s.key) + ']</h1>' +
      '<p class="sub">Имя: ____________________ &nbsp; Неделя: с ______ по ______</p>' +
      '<div class="rule">Каждый день по 2–5 минут, два раза — утром и вечером. Ребёнок сидит перед зеркалом. ' +
      'Сначала всё делаем медленно. Не говорите ребёнку, что он делает неверно: так он может отказаться ' +
      'заниматься.</div>' + tales + ex +
      '<div class="tbl"><p><b>Отмечайте, когда сделали:</b> у — утро, в — вечер.</p><table>' + head + rows + '</table></div>' +
      '<p class="foot">По Фомичёвой М. Ф. (1989) и картотекам логопедов · logozvuk.com</p></body></html>';
  }
  // Карточки: одна сторона — картинка-образ и название, четыре на листе А4, режут по пунктиру.
  // Оборота нет (слово автора 25.11: логопед на занятии оборот не читает, родителю «как
  // делать» даёт лист домой). Карточку показывают ребёнку, ребёнок может тянуть её сам.
  function cardsDoc() {
    var s = cur(), list = L.all ? s.ex : S.sel.map(at);
    var motifs = Object.keys(MOTIF).map(function (k) { return MOTIF[k]; }).join('');
    var corner = function (pos) {
      return '<svg class="mot ' + pos + '" viewBox="0 0 80 80" aria-hidden="true">' + motifs + '</svg>';
    };
    var card = function (c) {
      return '<div class="cell"><div class="front">' + corner('tl') + corner('br') +
        '<div class="pic">' + imgTag(c, '') + '</div><div class="nm' + (c.name.length > 12 ? ' long' : '') + '">' + esc(c.name) + '</div></div></div>';
    };
    var pages = [];
    for (var i = 0; i < list.length; i += 4) pages.push('<div class="pg">' + list.slice(i, i + 4).map(card).join('') + '</div>');
    var T = '.front{--acc:#c9c2b6;--tint:#fff;--c1:#fff;--c2:#fff;--c3:#fff}' +
      'body.t-osen .front{--acc:#e08a3c;--tint:#fff8ef;--c1:#f2b35c;--c2:#e5733b;--c3:#d9a441}' +
      'body.t-zima .front{--acc:#5b9bd5;--tint:#f3f8fd;--c1:#fff;--c2:#fff;--c3:#fff}' +
      'body.t-kosmos .front{--acc:#7466cf;--tint:#f6f4ff;--c1:#b9aef2;--c2:#f2c14e;--c3:#f2c14e}' +
      'body.t-more .front{--acc:#2f8fbf;--tint:#eff8fb;--c1:#7cc6e0;--c2:#7cc6e0;--c3:#f08a5d}' +
      'body.bw .front{--acc:#000;--tint:#fff;--c1:#fff;--c2:#fff;--c3:#fff}' +
      '.m{display:none}body.t-osen .m-osen,body.t-zima .m-zima,body.t-kosmos .m-kosmos,body.t-more .m-more{display:inline}' +
      '.mot .f{stroke:var(--acc);stroke-width:2;stroke-linejoin:round}.mot .a1{fill:var(--c1)}.mot .a2{fill:var(--c2)}' +
      '.mot .a3{fill:var(--c3)}.mot .s{fill:none;stroke:var(--acc);stroke-width:2.2;stroke-linecap:round}' +
      'body.t-zima .mot .s{stroke-width:2.6}';
    // Экран: лист той же ширины, что в печати (182 мм поля), иначе две карточки не встают в ряд.
    return '<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">' +
      '<title>Карточки артикуляционной гимнастики — звук [' + esc(s.key) + ']</title><style>' + PAGE_CSS +
      '@media screen{body{width:210mm}}' +
      'h1{font-size:15pt;margin:0 0 2pt}.how{margin:0 0 5mm;font-size:9.5pt;color:#444}' +
      '.pg{display:grid;grid-template-columns:89mm 89mm;grid-auto-rows:121mm;gap:4mm}' +
      '.pg+.pg{break-before:page;page-break-before:always}@media screen{.pg+.pg{margin-top:4mm}}' +
      '.cell{border:1px dashed #9a958d;box-sizing:border-box;padding:3mm;display:flex;break-inside:avoid}' +
      '.front{position:relative;flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;' +
      'border:2.4pt solid var(--acc);border-radius:6mm;background:var(--tint);overflow:hidden;padding:9mm 6mm 17mm}' +
      '.pic img{width:60mm;height:60mm;object-fit:contain;mix-blend-mode:multiply;filter:brightness(1.06)}.nm{margin-top:4mm;' +
      'font:700 24pt/1.1 ui-rounded,"Nunito","Arial Rounded MT Bold",Arial,sans-serif;text-align:center}.nm.long{font-size:19pt}' +
      '.mot{position:absolute;width:20mm;height:20mm}.mot.tl{left:2mm;top:2mm}' +
      '.mot.br{right:2mm;bottom:2mm;transform:rotate(180deg)}' + T +
      '</style></head><body contenteditable="true" spellcheck="false" class="t-' + L.tema + (L.colour ? '' : ' bw') + '">' +
      '<h1>Карточки артикуляционной гимнастики — звук [' + esc(s.key) + ']</h1>' +
      '<p class="how">Вырежьте по пунктиру. Карточку показывают ребёнку — или он тянет её сам. Как делать и сколько раз — ' +
      'в «Листе домой» и на logozvuk.com.</p>' +
      pages.join('') + '</body></html>';
  }
  function syncOpts() {
    $('gim-o-bw').setAttribute('aria-pressed', L.colour ? 'false' : 'true');
    $('gim-o-col').setAttribute('aria-pressed', L.colour ? 'true' : 'false');
    $('gim-o-tbl').checked = L.table;
    root.querySelectorAll('[data-tema]').forEach(function (b) {
      b.setAttribute('aria-pressed', b.dataset.tema === L.tema ? 'true' : 'false');
    });
    $('gim-o-sel').setAttribute('aria-pressed', L.all ? 'false' : 'true');
    $('gim-o-all').setAttribute('aria-pressed', L.all ? 'true' : 'false');
    var cards = L.kind === 'cards';
    $('gim-opt-tbl').hidden = cards; $('gim-opt-how').hidden = !cards;
    // У листа тема — это сказка о Весёлом Язычке; у карточек — рамка и рисунки в углах.
    $('gim-tema-lab').textContent = cards ? 'Тема:' : 'Сказка:';
    root.querySelector('[data-tema="bez"]').textContent = cards ? 'без темы' : 'без сказки';
    $('gim-word').hidden = cards;  // карточки в Word не раскладываются — кнопки нет (закон 14)
    $('gim-sheet-title').textContent = cards ? 'Карточки на занятие — так они будут выглядеть' :
      'Лист домой — так он будет выглядеть';
    $('gim-o-sel').textContent = 'отмеченные (' + S.sel.length + ')';
    $('gim-o-all').textContent = 'все (' + cur().ex.length + ')';
  }
  function load() {
    // Курсор в листе — клавиши ловит сам лист, наверх они не всплывают: Esc слушаем и там.
    frame.onload = function () {
      try {
        var d = frame.contentDocument;
        d.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') closeSheet(); });
        // Телефон: А4 шире экрана — на экране лист уменьшается целиком. Только экран:
        // в печать и PDF масштаб не уходит (`docClone` его снимает).
        var w = frame.clientWidth, bw = d.body.offsetWidth + 32;
        if (bw > w) { d.documentElement.style.setProperty('--z', (w / bw).toFixed(3)); d.documentElement.classList.add('fit'); }
      } catch (e) { /* молчим */ }
    };
    frame.srcdoc = L.kind === 'cards' ? cardsDoc() : listDoc();
  }
  function openSheet(kind) {
    L.kind = kind; L.colour = kind === 'cards'; L.table = true; L.all = false;
    syncOpts(); $('gim-err').textContent = '';
    load();
    sheet.hidden = false; document.documentElement.classList.add('gim-lock');
    $('gim-sheet-back').focus();
  }
  function closeSheet() {
    sheet.hidden = true; document.documentElement.classList.remove('gim-lock');
    $(L.kind === 'cards' ? 'gim-cards-btn' : 'gim-list-btn').focus();
  }
  // Цвет, таблица и тема меняют лист БЕЗ пересборки — правки в тексте не теряются.
  function applyOpts() {
    var d = frame.contentDocument; syncOpts();
    if (!d || !d.body) return;
    d.body.classList.toggle('no-table', !L.table);
    d.body.classList.toggle('bw', !L.colour); d.body.classList.toggle('col', !!L.colour);
    ['bez', 'osen', 'zima', 'kosmos', 'more'].forEach(function (t) { d.body.classList.toggle('t-' + t, t === L.tema); });
    d.querySelectorAll('img[data-bw]').forEach(function (im) { im.src = L.colour ? im.dataset.col : im.dataset.bw; });
  }
  function goal(fmt) {
    try {
      if (window.ym && window.METRIKA_ID) {
        var p = {}; p['[' + cur().key + ']'] = fmt;
        var o = {}; o[L.kind === 'cards' ? 'гимнастика · карточки' : 'гимнастика'] = p;
        window.ym(window.METRIKA_ID, 'reachGoal', 'list', { 'лист получен': o });
      }
    } catch (e) { /* молчим */ }
  }
  function docClone() {
    var d = frame.contentDocument; if (!d) return null;
    var c = d.documentElement.cloneNode(true);
    c.classList.remove('fit'); c.style.removeProperty('--z');
    if (!c.getAttribute('class')) c.removeAttribute('class');
    if (!c.getAttribute('style')) c.removeAttribute('style');
    var b = c.querySelector('body'); if (b) { b.removeAttribute('contenteditable'); b.removeAttribute('spellcheck'); }
    c.querySelectorAll('.tale:not(.s-' + L.tema + ')').forEach(function (x) { x.parentNode.removeChild(x); });
    // Word не читает классы темы — видимой сказке стиль пишем прямо в элемент.
    var tv = c.querySelector('.tale');
    if (tv && b) {
      var cs = frame.contentWindow.getComputedStyle(frame.contentDocument.querySelector('.tale.s-' + L.tema));
      tv.setAttribute('style', 'display:block;border:1.6pt solid ' + cs.borderTopColor + ';background:' + cs.backgroundColor +
        ';padding:9pt 12pt 6pt;margin:0 0 12pt');
    }
    return c;
  }
  function fileName() { return (L.kind === 'cards' ? 'Карточки гимнастики на звук ' : 'Гимнастика на звук ') + cur().key; }
  // Файл забираем переходом по ссылке с сервера, как у главного генератора: айфон
  // иначе открывает лист смотрелкой вместо того, чтобы сохранить.
  function take(url) {
    var a = document.createElement('a'); a.href = url; document.body.appendChild(a); a.click(); document.body.removeChild(a);
  }
  function busy(btn, on) {
    if (on) { btn.dataset.was = btn.textContent; btn.textContent = 'Собираем…'; btn.disabled = true; }
    else { btn.textContent = btn.dataset.was || btn.textContent; btn.disabled = false; }
  }
  async function post(url, payload, msg) {
    var r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    var j = null; try { j = await r.json(); } catch (e) { j = null; }
    if (!j || !j.ok || !j.url) { $('gim-err').textContent = (j && j.message) || msg; return false; }
    take(j.url); return true;
  }
  // PDF собирает служба печати на другом хосте: наших адресов она не видит,
  // поэтому картинки вшиваются в сам лист.
  function asData(src) {
    return fetch(src).then(function (r) { return r.blob(); }).then(function (bl) {
      return new Promise(function (ok) { var fr = new FileReader(); fr.onload = function () { ok(fr.result); }; fr.readAsDataURL(bl); });
    });
  }
  $('gim-pdf').addEventListener('click', async function () {
    var btn = this, c = docClone(); if (!c) return; $('gim-err').textContent = ''; busy(btn, true);
    try {
      var imgs = Array.prototype.slice.call(c.querySelectorAll('img'));
      for (var i = 0; i < imgs.length; i++) imgs[i].setAttribute('src', await asData(imgs[i].getAttribute('src')));
      var ok = await post('/api/pdf', { html: '<!DOCTYPE html>' + c.outerHTML, name: fileName() },
        'PDF сейчас не собрать. Лист на месте — распечатайте его.');
      if (ok) goal('PDF');
    } catch (e) {
      $('gim-err').textContent = 'Не дозвонились до службы печати. Лист на месте — распечатайте его.';
    } finally { busy(btn, false); }
  });
  // Word открывает картинки по полному адресу сайта.
  $('gim-word').addEventListener('click', async function () {
    var btn = this, c = docClone(); if (!c) return; $('gim-err').textContent = ''; busy(btn, true);
    try {
      c.querySelectorAll('img').forEach(function (im) { im.setAttribute('src', new URL(im.getAttribute('src'), location.href).href); });
      var html = '<html xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:w="urn:schemas-microsoft-com:office:word" ' +
        'xmlns="http://www.w3.org/TR/REC-html40">' + c.innerHTML + '</html>';
      var ok = await post('/api/word', { html: html, name: fileName() },
        'Word сейчас не собрать. Лист на месте — сохраните его в PDF или распечатайте.');
      if (ok) goal('Word');
    } catch (e) {
      $('gim-err').textContent = 'Не дозвонились до сервера. Лист на месте — распечатайте его.';
    } finally { busy(btn, false); }
  });
  $('gim-print').addEventListener('click', function () {
    var w = frame.contentWindow; if (!w) return;
    var imgs = frame.contentDocument.querySelectorAll('img'), left = imgs.length;
    var go = function () { goal('печать'); w.focus(); w.print(); };
    if (!left) { go(); return; }
    imgs.forEach(function (im) {
      if (im.complete) { if (--left === 0) go(); }
      else { im.onload = im.onerror = function () { if (--left === 0) go(); }; }
    });
  });
  $('gim-list-btn').addEventListener('click', function () { openSheet('list'); });
  $('gim-cards-btn').addEventListener('click', function () { openSheet('cards'); });
  $('gim-sheet-back').addEventListener('click', closeSheet);
  $('gim-o-bw').addEventListener('click', function () { L.colour = false; applyOpts(); });
  $('gim-o-col').addEventListener('click', function () { L.colour = true; applyOpts(); });
  $('gim-o-tbl').addEventListener('change', function () { L.table = this.checked; applyOpts(); });
  root.querySelectorAll('[data-tema]').forEach(function (b) {
    b.addEventListener('click', function () { L.tema = b.dataset.tema; applyOpts(); });
  });
  // «Все карточки» меняет состав листа — лист собирается заново.
  $('gim-o-sel').addEventListener('click', function () { if (L.all) { L.all = false; syncOpts(); load(); } });
  $('gim-o-all').addEventListener('click', function () { if (!L.all) { L.all = true; syncOpts(); load(); } });
  document.addEventListener('keydown', function (ev) { if (!sheet.hidden && ev.key === 'Escape') closeSheet(); });

  // ── колесо ───────────────────────────────────────────────────────────
  // Ребёнок крутит — колесо выбирает, какое упражнение делать сейчас (как случайные карты
  // Wordwall; «дать ребёнку самому выбрать» — из методичек). Сделали — сектор гаснет,
  // следующий раз колесо его не выберет. Звук — только щелчки колеса, как у настоящего.
  var W = { all: false, list: [], done: {}, rot: 0, busy: false, cur: -1 };
  var wheel = $('gim-wheel'), disc = $('gim-wh-disc');
  var PAL = ['#f6d9a8', '#cfe6d6', '#f8cfc6', '#d7e3f4', '#efe0b0', '#e3d6f0', '#cde8ea', '#f5dcc0'];
  function wList() { return W.all ? cur().ex.slice() : S.sel.map(at); }
  function wDraw() {
    var n = W.list.length, a = 360 / n, R = 100, out = '';
    var pt = function (deg, r) { var t = (deg - 90) * Math.PI / 180; return [R + r * Math.cos(t), R + r * Math.sin(t)]; };
    W.list.forEach(function (c, i) {
      var p1 = pt(i * a, 98), p2 = pt((i + 1) * a, 98), big = a > 180 ? 1 : 0, done = !!W.done[i];
      out += '<path d="M100 100L' + p1[0].toFixed(2) + ' ' + p1[1].toFixed(2) + 'A98 98 0 ' + big + ' 1 ' +
        p2[0].toFixed(2) + ' ' + p2[1].toFixed(2) + 'Z" fill="' + (done ? '#ebe8e2' : PAL[i % PAL.length]) +
        '" stroke="#fff" stroke-width="1.6"/>';
      var m = pt((i + 0.5) * a, n > 4 ? 66 : 60), sz = n > 6 ? 30 : n > 4 ? 36 : 46, img = c.obraz || c.litso;
      if (img) out += '<image href="' + esc(img) + '" x="' + (m[0] - sz / 2).toFixed(2) + '" y="' + (m[1] - sz / 2).toFixed(2) +
        '" width="' + sz + '" height="' + sz + '" transform="rotate(' + ((i + 0.5) * a).toFixed(2) + ' ' + m[0].toFixed(2) + ' ' +
        m[1].toFixed(2) + ')" opacity="' + (done ? .3 : 1) + '" style="mix-blend-mode:multiply"/>';
    });
    disc.innerHTML = '<svg viewBox="0 0 200 200" aria-hidden="true"><circle cx="100" cy="100" r="99.5" fill="#fff"/>' + out + '</svg>';
  }
  function wLeft() { return W.list.filter(function (c, i) { return !W.done[i]; }).length; }
  function wRes() {
    var box = $('gim-wh-res'), c = W.list[W.cur], left = wLeft();
    $('gim-wh-done').hidden = !(W.cur >= 0 && !W.done[W.cur]);
    $('gim-wh-again').hidden = left > 0;
    $('gim-wh-hub').disabled = W.busy || left === 0;
    if (W.cur < 0) {
      box.innerHTML = left ? '<p class="gim-wh-hint">Нажми «Крути!» — колесо выберет упражнение.</p>' :
        '<p class="gim-wh-name">Все упражнения сделаны!</p><p class="gim-wh-hint">Молодец.</p>';
      return;
    }
    var img = c.obraz || c.litso;
    box.innerHTML = (img ? '<img src="' + esc(img) + '" alt="">' : '') + '<p class="gim-wh-name">' + esc(c.name) + '</p>' +
      (c.child ? '<p class="gim-wh-child">' + esc(cap(c.child)) + '</p>' : '') +
      '<p class="gim-wh-dose">' + esc(plan(c)) + (c.props ? ' · нужна ' + esc(c.props) : '') + '</p>' +
      '<p class="gim-wh-left">' + (W.done[W.cur] ? 'Сделали. ' : '') + 'Осталось: ' + left + ' из ' + W.list.length + '</p>';
  }
  function wSync() {
    $('gim-wh-sel').setAttribute('aria-pressed', W.all ? 'false' : 'true');
    $('gim-wh-all').setAttribute('aria-pressed', W.all ? 'true' : 'false');
    $('gim-wh-sel').textContent = 'отмеченные (' + S.sel.length + ')';
    $('gim-wh-all').textContent = 'все (' + cur().ex.length + ')';
  }
  function wReset() {
    W.list = wList(); W.done = {}; W.cur = -1; W.rot = 0;
    disc.style.transition = 'none'; disc.style.transform = 'rotate(0deg)'; void disc.offsetWidth; disc.style.transition = '';
    wSync(); wDraw(); wRes();
  }
  // Щелчок колеса — короткий тон; AudioContext закрывается сразу после остановки.
  function wTicks(ac) {
    var a = 360 / W.list.length, last = null;
    (function frame() {
      if (!W.busy) return;
      var m = getComputedStyle(disc).transform, deg = 0;
      if (m && m !== 'none') { var v = m.split('(')[1].split(','); deg = Math.atan2(+v[1], +v[0]) * 180 / Math.PI; }
      var k = Math.floor(((deg % 360) + 360) % 360 / a);
      if (last !== null && k !== last && ac) {
        try {
          var o = ac.createOscillator(), g = ac.createGain(), t0 = ac.currentTime;
          o.frequency.value = 1700; g.gain.setValueAtTime(0.06, t0); g.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.03);
          o.connect(g); g.connect(ac.destination); o.start(t0); o.stop(t0 + 0.035);
        } catch (e) { /* молчим */ }
      }
      last = k; requestAnimationFrame(frame);
    })();
  }
  function wSpin() {
    if (W.busy) return;
    var free = []; W.list.forEach(function (c, i) { if (!W.done[i]) free.push(i); });
    if (!free.length) return;
    var i = free[Math.floor(Math.random() * free.length)], a = 360 / W.list.length;
    var jitter = (Math.random() - 0.5) * a * 0.6, target = -((i + 0.5) * a) + jitter;
    var delta = ((target - W.rot) % 360 + 360) % 360;
    W.rot += 360 * 5 + delta; W.busy = true; W.cur = -1; wRes();
    $('gim-wh-res').innerHTML = '<p class="gim-wh-hint">Крутится…</p>';
    var ac = null; try { ac = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { ac = null; }
    disc.style.transform = 'rotate(' + W.rot + 'deg)';
    wTicks(ac);
    var end = function () {
      disc.removeEventListener('transitionend', end); clearTimeout(tm);
      if (!W.busy) return;
      W.busy = false; W.cur = i; wRes();
      if (ac) { try { ac.close(); } catch (e) { /* молчим */ } }
      try { if (window.ym && window.METRIKA_ID) window.ym(window.METRIKA_ID, 'reachGoal', 'koleso', { 'звук': cur().key }); }
      catch (e) { /* молчим */ }
    };
    var tm = setTimeout(end, 4600);
    disc.addEventListener('transitionend', end);
  }
  function openWheel() {
    W.all = false; wReset();
    wheel.hidden = false; document.documentElement.classList.add('gim-lock'); $('gim-wh-hub').focus();
  }
  function closeWheel() {
    W.busy = false; wheel.hidden = true; document.documentElement.classList.remove('gim-lock'); $('gim-wheel-btn').focus();
  }
  $('gim-wheel-btn').addEventListener('click', openWheel);
  $('gim-wh-back').addEventListener('click', closeWheel);
  $('gim-wh-hub').addEventListener('click', wSpin);
  $('gim-wh-done').addEventListener('click', function () { if (W.cur >= 0) { W.done[W.cur] = true; if (!wLeft()) W.cur = -1; wDraw(); wRes(); $(wLeft() ? 'gim-wh-hub' : 'gim-wh-again').focus(); } });
  $('gim-wh-again').addEventListener('click', function () { wReset(); $('gim-wh-hub').focus(); });
  $('gim-wh-sel').addEventListener('click', function () { if (W.all && !W.busy) { W.all = false; wReset(); } });
  $('gim-wh-all').addEventListener('click', function () { if (!W.all && !W.busy) { W.all = true; wReset(); } });
  document.addEventListener('keydown', function (ev) { if (!wheel.hidden && ev.key === 'Escape') closeWheel(); });

  reset(); render();
})();
"""


def widget_html() -> str:
    """Виджет целиком: разметка, стиль, данные и код — одной вставкой в страницу."""
    d = data()
    e = html.escape
    buttons = "".join(
        f'<button type="button" aria-pressed="false">{e(s["key"])}</button>'
        for s in d["sounds"])
    temy = "".join(f'<button type="button" data-tema="{k}" aria-pressed="{"true" if k == "bez" else "false"}">'
                   f'{e(v)}</button>' for k, v in TEMY)
    # «</» внутри <script> обрывает тег даже в строке (урок 08-25, `analytics`).
    blob = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
    motif = json.dumps(MOTIF, ensure_ascii=False).replace("</", "<\\/")
    return (
        f"<style>{CSS}</style>\n"
        '<div class="widget-box gim" id="gim">\n'
        '<div class="gim-in">\n'
        ' <div class="gim-desk">\n'
        '  <aside class="gim-side">\n'
        '   <p class="gim-label">Звук</p>\n'
        f'   <div class="gim-sounds" role="group" aria-label="Звук">{buttons}</div>\n'
        '   <p class="gim-note" id="gim-note"></p>\n'
        '   <ol class="gim-how">\n'
        '    <li><b>1</b><span>Выберите звук.</span></li>\n'
        '    <li><b>2</b><span>Отметьте 2–3 упражнения — номер покажет порядок.</span></li>\n'
        '    <li><b>3</b><span>«Карточки на занятие» и «Колесо» — для ребёнка. «Лист домой» — родителю, '
        'можно со сказкой.</span></li>\n'
        '   </ol>\n'
        '  </aside>\n'
        '  <section class="gim-cards" aria-label="Упражнения">\n'
        '   <div class="gim-head"><p>Упражнения для звука <b id="gim-for"></b> — отметьте 2–3</p>'
        '<span class="gim-count-sel" id="gim-nsel"></span></div>\n'
        '   <ul class="gim-grid" id="gim-grid"></ul>\n'
        '   <p class="gim-warn" id="gim-warn" role="status"></p>\n'
        '  </section>\n'
        ' </div>\n'
        ' <div class="gim-shelf-row">\n'
        '  <p class="gim-hint">За один раз — 2–3 упражнения, новое из них одно (Фомичёва, 1989).</p>\n'
        '  <button type="button" class="gim-btn" id="gim-list-btn" title="Лист для родителя: сначала на экране, '
        'потом печать, PDF или Word">Лист домой</button>\n'
        '  <button type="button" class="gim-btn gim-go" id="gim-cards-btn" title="Карточки с картинками — показывать '
        'ребёнку, четыре на листе. Сначала на экране, потом печать или PDF">Карточки на занятие</button>\n'
        '  <button type="button" class="gim-btn" id="gim-wheel-btn" title="Колесо на экране: ребёнок крутит — '
        'колесо выбирает упражнение">Колесо</button>\n'
        ' </div>\n'
        '</div>\n'
        '<div class="gim-sheet" id="gim-sheet" role="dialog" aria-modal="true" aria-labelledby="gim-sheet-title" hidden>\n'
        ' <div class="gim-sheet-bar">\n'
        '  <button type="button" class="gim-btn gim-sm" id="gim-sheet-back">← К упражнениям</button>\n'
        '  <h2 id="gim-sheet-title"></h2>\n'
        '  <button type="button" class="gim-btn gim-sm" id="gim-print">Печать</button>\n'
        '  <button type="button" class="gim-btn gim-sm" id="gim-word">Скачать Word</button>\n'
        '  <button type="button" class="gim-btn gim-sm gim-go" id="gim-pdf">Скачать PDF</button>\n'
        ' </div>\n'
        ' <div class="gim-opts">\n'
        '  <span class="gim-opt" id="gim-opt-how"><span>Карточки:</span><span class="gim-seg">'
        '<button type="button" id="gim-o-sel" aria-pressed="true"></button>'
        '<button type="button" id="gim-o-all" aria-pressed="false"></button></span></span>\n'
        f'  <span class="gim-opt" id="gim-opt-tema"><span id="gim-tema-lab">Тема:</span><span class="gim-seg">{temy}</span></span>\n'
        '  <span class="gim-opt"><span>Картинки:</span><span class="gim-seg"><button type="button" id="gim-o-bw" '
        'aria-pressed="true">чёрно-белые</button><button type="button" id="gim-o-col" aria-pressed="false">цветные'
        '</button></span></span>\n'
        '  <label class="gim-opt gim-chk" id="gim-opt-tbl"><input type="checkbox" id="gim-o-tbl" checked> '
        'таблица отметок на неделю</label>\n'
        '  <span>Текст можно поправить прямо на листе — так он и сохранится.</span>\n'
        ' </div>\n'
        ' <p class="gim-err" id="gim-err" role="status"></p>\n'
        ' <iframe id="gim-sheet-frame" title="Материал на экране"></iframe>\n'
        '</div>\n'
        '<div class="gim-wheel" id="gim-wheel" role="dialog" aria-modal="true" aria-labelledby="gim-wh-title" hidden>\n'
        ' <div class="gim-sheet-bar">\n'
        '  <button type="button" class="gim-btn gim-sm" id="gim-wh-back">← К упражнениям</button>\n'
        '  <h2 id="gim-wh-title">Колесо — крутит ребёнок</h2>\n'
        '  <span class="gim-opt"><span class="gim-seg"><button type="button" id="gim-wh-sel" aria-pressed="true"></button>'
        '<button type="button" id="gim-wh-all" aria-pressed="false"></button></span></span>\n'
        ' </div>\n'
        ' <div class="gim-wh-main">\n'
        '  <div class="gim-wh-stage">\n'
        '   <svg class="gim-wh-pin" viewBox="0 0 34 40" aria-hidden="true"><path d="M3 3H31L17 37Z" fill="#e8806e" '
        'stroke="#fff" stroke-width="3" stroke-linejoin="round"/></svg>\n'
        '   <div class="gim-wh-disc" id="gim-wh-disc"></div>\n'
        '   <button type="button" class="gim-wh-hub" id="gim-wh-hub">Крути!</button>\n'
        '  </div>\n'
        '  <div>\n'
        '   <div class="gim-wh-res" id="gim-wh-res" role="status"></div>\n'
        '   <p style="text-align:center;margin:12px 0 0"><button type="button" class="gim-btn gim-go" id="gim-wh-done" hidden>'
        'Сделали ✓</button> <button type="button" class="gim-btn" id="gim-wh-again" hidden>Крутить заново</button></p>\n'
        '  </div>\n'
        ' </div>\n'
        '</div>\n'
        f'<script type="application/json" id="gim-data">{blob}</script>\n'
        f'<script type="application/json" id="gim-motif">{motif}</script>\n'
        "</div>\n"
        f"<script>{JS}</script>"
    )
