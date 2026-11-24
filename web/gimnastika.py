# -*- coding: utf-8 -*-
"""Виджет «Артикуляционная гимнастика» — первая страница-кластер (2026-11-23).

Зачем свой виджет, а не главный генератор в рамке. Канон Site Builders 2.0: кластер —
«примерно одна функция, названная разными словами», и при смене кластера меняется сам
виджет (`app-studio/knowledge-base/site-builders-2/01-vstrecha-01.md` §7); у страницы
кластера свой виджет первым экраном (`03-vstrecha-03.md` §6.1). Встроен прямо в
страницу, а не рамкой: содержимое iframe поисковик не индексирует.

ВИД — концепция «Стол и зеркало» (`dizajn/KONCEPCIYA.md`, 24.11). Два места — два закона,
как «Стол и доска» у funclass:
  · СТОЛ — страница, где взрослый выбирает: бумага, на ней картотека — восемь карточек
    упражнений. Лицом карточка показывает картинку-образ ребёнку, оборотом — «как делать»
    взрослому. У Фомичёвой так и разделено: «картинка-образ дается ребенку…, а подробная
    запись — для родителей».
  · ЗЕРКАЛО — экран на занятии. В практике ребёнок смотрит на лицо взрослого и на себя в
    зеркало; экран встаёт рядом и делает то, что взрослый делает вслух: показывает образ и
    считает. Поэтому занятие нарисовано зеркалом в деревянной раме, кнопки взрослого лежат
    под ним на полочке.
Цвет держит смысл, один цвет — один смысл: зелёный бренда — «выбрано»; коралловый, цвет
язычка, — «сейчас» и «нажми»; стекло — только зеркало. Голубая метка — «держим»,
песочная — «повторяем»; значок на метке, чтобы смысл не держался на одном цвете.

ЧТО ДЕЛАЕТ. Звук → восемь упражнений его комплекса, все на виду (слово автора 24.11: «не
нужно выпадающего списка, нужно, чтобы все 8 мы видели») → щелчком отмечают 2–3, номер
показывает порядок → «Начать у зеркала» или «Лист домой». За один раз не больше трёх:
Фомичёва 1989, «не более двух-трёх упражнений», и «новым может быть только одно».
Порядок карточек: набор недели (`sheet_4`), потом запас (`alternates`); с реквизитом — в
конце. Деления «основные / запас» на экране нет: его придумали мы под четыре клетки листа.

СЧЁТ — таблицей у каждого упражнения (`gymnastics.json` → `schet`, формат — `schet_format`).
Автор 24.11: «держать под счёт от 1 до 10, а почему дальше пошло? 13, 14». В практике
взрослый считает вслух, и у счёта есть конец: держим — до 5, постепенно до 10 (Фомичёва);
повторяем — на каждый счёт одно движение, сначала медленно; качели — каждое положение под
счёт. Картинка-образ двигается в такт: у Фомичёвой она «служит образцом для подражания
предмету или его движениям». Голоса пока нет — он ждёт записи и слова автора; кнопку
голоса не показываем, пока его нет (закон 14).

Данные — только `logoped_slovar/gymnastics.json` (разбор Фомичёвой 1989 и картотек
практиков, с тирами). Упражнения постановки (`excluded_from_sheet`) сюда не попадают.
Ч и Ц: своих комплексов в файле нет, источник называет комплексы по ГРУППЕ — «для свистящих
звуков с, з, ц» и «для шипящих звуков ш, ж, ч, щ»; [Ц] берёт комплекс [С], [Ч] — [Ш].

Зеркало у Фомичёвой: «Сначала упражнения выполняются в медленном темпе перед зеркалом»,
дома с четырёх лет — тоже перед зеркалом (строки 314 и 1333 копии
`research/afrikaty_ch_ts_2026-11-23_syrye/fomicheva_1989.txt`). Отсюда строка в правилах
листа домой и первая заставка занятия. Практика по экрану, счёту и звуку —
`research/site/gimnastika_praktika_2026-11-24.md`.
"""
from __future__ import annotations

import html
import json
import os
import re
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
GYM_PATH = os.path.join(HERE, "..", "logoped_slovar", "gymnastics.json")

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

# Закон 3: на экране нет слова, которое живёт только в коде.
KIND = {"static": "держим", "dynamic": "повторяем"}


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
        # картинки (закон 14). Метка времени в адресе: у /img/ длинный кэш, и без
        # неё перерисованный образ сутки показывал бы старый (закон 17).
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
        return {
            "name": e["name"],
            "kind": KIND.get(e.get("type", ""), ""),
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
            # Нет таблицы счёта — нет и занятия на экране для этого упражнения:
            # счёт не придумывается из названия (закон 7).
            "fazy": (e.get("schet") or {}).get("fazy", []),
        }

    def queue(c: Dict[str, Any]) -> List[str]:
        # Порядок карточек: набор недели, потом запас; с реквизитом — в конце.
        skip = set(c.get("excluded_from_sheet", []))
        ids = [i for i in c["sheet_4"] + c.get("alternates", []) if i in ex and i not in skip]
        ids = list(dict.fromkeys(ids))
        return ([i for i in ids if not ex[i].get("rekvizit")] +
                [i for i in ids if ex[i].get("rekvizit")])

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
        sounds.append({"key": s, "note": note, "ex": [card(i) for i in queue(c)]})
    return {"sounds": sounds}


# Иконки меток: смысл держится не только на цвете.
ICON_HOLD = ('<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="4" y="3" width="2.6" height="10" rx="1.2"/>'
             '<rect x="9.4" y="3" width="2.6" height="10" rx="1.2"/></svg>')
ICON_MOVE = ('<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M1.5 8l3.2-3.2v2.1h6.6V4.8L14.5 8l-3.2 3.2V9.1H4.7v2.1z"/>'
             '</svg>')

CSS = r"""
.gim{--g-paper:#f7f5f1;--g-card:#fff;--g-ink:#16191d;--g-muted:#565d66;--g-line:#e6e2da;--g-edge:#d5d0c6;
  --g-brand:#2f6b4f;--g-brand-edge:#1f4e39;--g-tongue:#e8806e;--g-tongue-edge:#c9624f;--g-bead:#d9604c;
  --g-glass:#eef5f6;--g-frame:#dcc49c;--g-frame-edge:#c3a676;--g-shelf:#e6d3b0;
  --g-hold:#dbeaf0;--g-hold-ink:#1f4a5a;--g-move:#f7e6c4;--g-move-ink:#6b4a12;
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
.gim-note:empty,.gim-warn:empty{display:none}
.gim-gap{margin-top:var(--s4)}
.gim-toggle{display:flex;gap:8px;align-items:center;width:100%;padding:8px 10px;border:1px solid var(--g-edge);
  border-radius:12px;background:#fff;font:inherit;font-size:.9rem;cursor:pointer;color:var(--g-ink);text-align:left;
  box-shadow:0 2px 0 var(--g-edge)}
.gim-toggle .box{flex:none;width:18px;height:18px;border-radius:5px;border:2px solid var(--g-edge);background:#fff}
.gim-toggle[aria-pressed="true"]{border-color:var(--g-brand)}
.gim-toggle[aria-pressed="true"] .box{background:var(--g-brand);border-color:var(--g-brand);
  box-shadow:inset 0 0 0 3px #fff}
.gim-toggle small{display:block;color:var(--g-muted);font-size:.76rem}
.gim-head{display:flex;justify-content:space-between;align-items:baseline;gap:8px;margin:0 0 8px}
.gim-head p{margin:0;font-size:.95rem}
.gim-head b{font-weight:600}
.gim-count-sel{font-size:.82rem;color:var(--g-muted);white-space:nowrap}
.gim-grid{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}
.gim-card{position:relative;height:13.2rem;perspective:900px;margin:0}
.gim-card-in{position:relative;width:100%;height:100%;transition:transform .45s ease;transform-style:preserve-3d}
.gim-card.is-flip .gim-card-in{transform:rotateY(180deg)}
.gim-face{position:absolute;inset:0;backface-visibility:hidden;-webkit-backface-visibility:hidden;border-radius:14px;
  background:var(--g-card);border:1px solid var(--g-line);box-shadow:0 2px 0 var(--g-line)}
.gim-back{transform:rotateY(180deg)}
.gim-back-text{position:absolute;inset:0;padding:10px 12px 36px;overflow:auto;font-size:.82rem;line-height:1.4}
.gim-card.is-on .gim-front{border:2px solid var(--g-brand);box-shadow:0 3px 0 var(--g-brand-edge)}
.gim-pick{display:flex;flex-direction:column;align-items:center;width:100%;height:100%;padding:8px 8px 10px;border:0;
  background:none;font:inherit;color:inherit;cursor:pointer;border-radius:14px;text-align:center}
.gim-tab{align-self:flex-start;display:inline-flex;align-items:center;gap:4px;padding:2px 8px 2px 6px;border-radius:999px;
  font-size:.72rem;line-height:1.5}
.gim-tab svg{width:12px;height:12px;fill:currentColor}
.is-hold .gim-tab{background:var(--g-hold);color:var(--g-hold-ink)}
.is-move .gim-tab{background:var(--g-move);color:var(--g-move-ink)}
.gim-pick img{width:6.2rem;height:6.2rem;object-fit:contain;margin:4px 0 2px}
.gim-pick .noimg{width:6.2rem;height:6.2rem}
.gim-cname{font-family:var(--g-round);font-weight:600;font-size:.98rem;line-height:1.2}
.gim-cprops{font-size:.72rem;color:var(--g-muted);margin-top:2px}
.gim-num{position:absolute;top:-8px;left:-8px;width:28px;height:28px;border-radius:50%;background:var(--g-brand);
  color:#fff;font-family:var(--g-round);font-weight:700;display:flex;align-items:center;justify-content:center;
  box-shadow:0 2px 0 var(--g-brand-edge);z-index:3;pointer-events:none}
.is-on .gim-tab{margin-left:16px}
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
.gim-go{background:var(--g-tongue);border-color:var(--g-tongue);color:var(--g-ink);font-weight:600;
  box-shadow:0 3px 0 var(--g-tongue-edge)}
.gim-go:active{box-shadow:0 1px 0 var(--g-tongue-edge)}
.gim-go svg{width:14px;height:14px;fill:currentColor;vertical-align:-1px;margin-right:4px}
@media (max-width:760px){
  .gim{padding:var(--s3) var(--s3) var(--s4)}
  .gim-desk{grid-template-columns:minmax(0,1fr)}
  .gim-sounds{grid-template-columns:repeat(7,1fr)}
  .gim-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .gim-card{height:11.8rem}
  /* На телефоне картотека длинная — полочка с кнопками едет вместе с экраном,
     чтобы «Начать у зеркала» не уходило за край. */
  .gim-shelf-row{position:sticky;bottom:0;z-index:5;margin:var(--s3) calc(-1 * var(--s3)) 0;
    padding:10px var(--s3) calc(10px + env(safe-area-inset-bottom));background:var(--g-paper);
    border-top:1px solid var(--g-line);box-shadow:0 -6px 14px rgba(22,25,29,.06)}
  .gim-hint{display:none}
  .gim-shelf-row .gim-btn{flex:1 1 auto}
}
/* ── зеркало: занятие на экране ─────────────────────────────────────── */
.gim-mirror{position:fixed;inset:0;z-index:1000;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:12px;padding:2.5vh 2vw;background:var(--g-paper)}
.gim-mirror[hidden]{display:none}
.gim-mirror:focus{outline:none}
.gim-frame{width:min(96vw,1100px);height:min(78vh,760px);padding:clamp(10px,1.6vw,22px);border-radius:30px;
  background:var(--g-frame);box-shadow:inset 0 0 0 2px var(--g-frame-edge),0 14px 34px rgba(60,40,10,.12)}
.gim-glass{position:relative;width:100%;height:100%;border-radius:20px;background:var(--g-glass);overflow:hidden;
  display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:2vh 3vw;
  box-shadow:inset 0 0 0 1px rgba(31,74,90,.08)}
.gim-glass::before{content:"";position:absolute;top:-30%;left:-6%;width:34%;height:160%;pointer-events:none;
  background:linear-gradient(100deg,rgba(255,255,255,0),rgba(255,255,255,.6) 50%,rgba(255,255,255,0));transform:rotate(16deg)}
.gim-glass>*{position:relative}
.gim-m-step{margin:0;font-size:clamp(.9rem,1.9vh,1.05rem);color:var(--g-muted)}
.gim-m-pics{display:flex;justify-content:center;align-items:center;gap:3vw;margin:1.2vh 0}
.gim-m-pics img{width:min(30vh,250px);height:min(30vh,250px);max-width:40vw;object-fit:contain;
  transition:transform .35s ease;mix-blend-mode:multiply}
.gim-m-name{margin:0;font-family:var(--g-round);font-weight:700;font-size:clamp(1.7rem,5vh,3rem);line-height:1.1}
.gim-m-child{margin:.6vh 0 0;font-size:clamp(1rem,2.6vh,1.4rem);color:var(--g-muted);font-style:italic;max-width:40rem}
.gim-beads{display:flex;flex-wrap:wrap;justify-content:center;gap:clamp(5px,.9vh,10px);margin:2vh 0 .8vh;max-width:90%}
.gim-bead{width:clamp(14px,2.6vh,26px);height:clamp(14px,2.6vh,26px);border-radius:50%;background:#fff;
  box-shadow:inset 0 0 0 2px rgba(31,74,90,.18);transition:background .2s,transform .2s}
.gim-bead.f{background:var(--g-bead);box-shadow:none}
.gim-bead.now{transform:scale(1.25)}
.gim-m-num{margin:0;font-family:var(--g-round);font-weight:700;font-size:clamp(2.6rem,9vh,5.5rem);line-height:1;
  color:var(--g-ink);font-variant-numeric:tabular-nums}
.gim-m-num small{font-size:.38em;font-weight:600;color:var(--g-muted)}
.gim-m-word{margin:.6vh 0 0;font-family:var(--g-round);font-size:clamp(1.1rem,3vh,1.6rem);font-weight:600;
  color:var(--g-hold-ink)}
.gim-m-pics img.shake{animation:gim-shake .16s linear infinite}
@keyframes gim-shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-4%)}75%{transform:translateX(4%)}}
.gim-mirror .gim-shelf{display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:10px;
  width:min(96vw,1100px);padding:8px 12px;border-radius:14px;background:var(--g-shelf);
  box-shadow:inset 0 -3px 0 var(--g-frame-edge)}
.gim-mirror .gim-keys{margin:0 0 0 8px;font-size:.82rem;color:#6b5634}
@media (hover:none){.gim-mirror .gim-keys{display:none}}
@media (prefers-reduced-motion:reduce){
  .gim-card-in,.gim-m-pics img,.gim-bead{transition:none}
  .gim-m-pics img.shake{animation:none}
}
html.gim-lock,html.gim-lock body{overflow:hidden}
#gim-print{display:none}
@media print{
  body>*{display:none !important}
  body>#gim-print{display:block !important;font:12pt/1.4 Arial,sans-serif;color:#000}
  #gim-print h1{font-size:16pt;margin:0 0 6pt}
  #gim-print .rule{margin:0 0 10pt}
  #gim-print .ex{margin:0 0 8pt;page-break-inside:avoid;overflow:hidden}
  #gim-print .ex .pic{float:left;width:20mm;height:20mm;object-fit:contain;margin:0 4mm 2mm 0}
  #gim-print .ex b{font-size:12.5pt}
  #gim-print table{border-collapse:collapse;width:100%;margin-top:10pt}
  #gim-print th,#gim-print td{border:1px solid #000;padding:3pt 4pt;font-size:10pt;text-align:center}
  #gim-print td.n{text-align:left;width:32%}
  #gim-print .foot{margin-top:12pt;font-size:9pt;color:#444}
}
"""

JS = r"""
(function () {
  var D = JSON.parse(document.getElementById('gim-data').textContent);
  var ICON = JSON.parse(document.getElementById('gim-icons').textContent);
  var root = document.getElementById('gim');
  var $ = function (id) { return document.getElementById(id); };
  // Фомичёва 1989: «Не следует предлагать детям более двух-трех упражнений».
  var MAX = 3;
  var S = { i: 0, sel: [], flip: {}, five: false };
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

  // ── стол: картотека ──────────────────────────────────────────────────
  function cardHtml(c, j) {
    var n = S.sel.indexOf(j), on = n >= 0, fl = !!S.flip[j];
    var hold = c.kind === 'держим';
    var img = c.obraz || c.litso;
    return '<li class="gim-card ' + (hold ? 'is-hold' : 'is-move') + (on ? ' is-on' : '') + (fl ? ' is-flip' : '') + '">' +
      (on ? '<span class="gim-num" aria-hidden="true">' + (n + 1) + '</span>' : '') +
      '<div class="gim-card-in">' +
      '<div class="gim-face gim-front"' + (fl ? ' aria-hidden="true"' : '') + '>' +
      '<button type="button" class="gim-pick" data-j="' + j + '" aria-pressed="' + on + '"' + (fl ? ' tabindex="-1"' : '') +
      ' title="' + (on ? 'Убрать из занятия' : 'Взять в занятие') + '">' +
      '<span class="gim-tab">' + (hold ? ICON.hold : ICON.move) + esc(c.kind) + '</span>' +
      (img ? '<img src="' + esc(img) + '" alt="" loading="lazy">' : '<span class="noimg"></span>') +
      '<span class="gim-cname">' + esc(c.name) + '</span>' +
      (c.props ? '<span class="gim-cprops">понадобится: ' + esc(c.props) + '</span>' : '') +
      '</button>' +
      '<button type="button" class="gim-flip" data-f="' + j + '" title="Как делать — оборот карточки" aria-label="Как делать: ' +
      esc(c.name) + '"' + (fl ? ' tabindex="-1"' : '') + '>?</button></div>' +
      '<div class="gim-face gim-back"' + (fl ? '' : ' aria-hidden="true"') + '><div class="gim-back-text">' +
      '<p class="gim-bname">' + esc(c.name) + '</p>' +
      (c.child ? '<p class="gim-child">' + esc(c.child) + '</p>' : '') +
      '<p>' + esc(c.how) + '</p>' +
      '<p><b>Сколько:</b> ' + esc(c.dose) + (c.props ? '. <b>Понадобится:</b> ' + esc(c.props) : '') + '</p>' +
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
    $('gim-nsel').textContent = 'в занятии ' + S.sel.length + ' из ' + s.ex.length;
    $('gim-grid').innerHTML = s.ex.map(cardHtml).join('');
    $('gim-five').setAttribute('aria-pressed', S.five ? 'true' : 'false');
  }

  root.querySelectorAll('.gim-sounds button').forEach(function (b, k) {
    b.addEventListener('click', function () { S.i = k; reset(); render(); });
  });
  $('gim-five').addEventListener('click', function () { S.five = !S.five; render(); });
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
      if (S.sel.length <= 1) { warn('Одно упражнение в занятии остаётся всегда.'); return; }
      S.sel.splice(k, 1);
    } else {
      if (S.sel.length >= MAX) {
        warn('В занятии не больше трёх: у Фомичёвой «не более двух-трёх упражнений» за раз. ' +
             'Сначала уберите одно — щелчком по нему.');
        return;
      }
      S.sel.push(j);
    }
    warn(''); render();
    var again = $('gim-grid').querySelector('.gim-pick[data-j="' + j + '"]');
    if (again) again.focus();
  });

  // ── зеркало: занятие по таблице счёта ────────────────────────────────
  var WORD = ['', 'раз', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять', 'десять'];
  var DV = {
    x: function (p) { return 'translateX(' + (p ? 9 : -9) + '%)'; },
    y: function (p) { return 'translateY(' + (p ? 8 : -8) + '%)'; },
    hop: function (p) { return p ? 'translateY(-12%)' : 'translateY(0)'; },
    swing: function (p) { return 'rotate(' + (p ? -11 : 11) + 'deg)'; },
    tick: function (p) { return 'rotate(' + (p ? 13 : -13) + 'deg)'; },
    squeeze: function (p) { return p ? 'scale(1,.78)' : 'scale(1,1)'; },
    up: function (p) { return p ? 'translateY(-16%)' : 'translateY(0)'; },
    push: function (p) { return p ? 'scale(1.1)' : 'scale(1)'; }
  };
  // Фазы упражнения → шаги по одному счёту. Длительность шага — секунды.
  function steps(c) {
    var out = [];
    c.fazy.forEach(function (f) {
      if (f.vid === 'derzhim') {
        var n = S.five ? Math.min(5, f['do']) : f['do'];
        for (var k = 1; k <= n; k++) out.push({ n: k, of: n, dur: 1, word: f.slovo || 'держим' });
      } else if (f.vid === 'povtor') {
        var t0 = Array.isArray(f.temp) ? f.temp[0] : f.temp, t1 = Array.isArray(f.temp) ? f.temp[1] : f.temp;
        for (var r = 1; r <= f.raz; r++) {
          var dur = f.raz > 1 ? t0 + (t1 - t0) * (r - 1) / (f.raz - 1) : t0;
          out.push({ n: r, of: f.raz, dur: dur, word: f.slovo || 'повторяем', dv: f.dvizh, p: r % 2, mir: !!f.zerkalo });
        }
      } else if (f.vid === 'polozheniya') {
        var h = S.five ? Math.min(5, f.derzhat) : f.derzhat;
        for (var kr = 0; kr < f.krugov; kr++) {
          f.pozicii.forEach(function (pz, pi) {
            for (var q = 1; q <= h; q++) out.push({ n: q, of: h, dur: 1, word: pz, dv: f.dvizh, p: pi,
              turn: kr * f.pozicii.length + pi + 1, turns: f.krugov * f.pozicii.length });
          });
        }
      }
    });
    return out;
  }
  var R = { list: [], k: -1, st: [], j: 0, t: null, due: 0, left: 0, paused: false, mode: '' , lock: null };
  var run = $('gim-run');
  function clear() { clearTimeout(R.t); R.t = null; }
  function later(sec, fn) { clear(); R.due = Date.now() + sec * 1000; R.fn = fn; R.t = setTimeout(fn, sec * 1000); }
  function pics(c) {
    var o = '';
    if (c.obraz) o += '<img class="gim-obraz" src="' + esc(c.obraz) + '" alt="' + esc(c.name) + '">';
    if (c.litso) o += '<img class="gim-litso" src="' + esc(c.litso) + '" alt="Как делать: ' + esc(c.name) + '">';
    return o;
  }
  function screen(o) {
    $('gim-m-step').textContent = o.step || '';
    $('gim-m-pics').innerHTML = o.pics || '';
    $('gim-m-name').textContent = o.name || '';
    $('gim-m-child').textContent = o.child || '';
    $('gim-beads').innerHTML = '';
    $('gim-m-num').innerHTML = o.num || '';
    $('gim-m-word').textContent = o.word || '';
  }
  function intro() {
    R.mode = 'intro';
    $('gim-next').textContent = 'Дальше →';
    $('gim-pause').hidden = false;
    screen({ step: 'Начинаем', name: 'Садимся ровно', child: 'Зеркало — рядом: ребёнок видит себя, взрослый — ребёнка',
             word: 'Сначала медленно' });
    later(3, function () { startEx(0); });
  }
  function startEx(k) {
    R.k = k; var c = R.list[k];
    R.st = steps(c); R.j = 0; R.mode = 'ex';
    screen({ step: 'Упражнение ' + (k + 1) + ' из ' + R.list.length + ' · ' + c.kind, pics: pics(c), name: c.name,
             child: c.child });
    $('gim-next').textContent = k + 1 < R.list.length ? 'Дальше →' : 'Готово';
    beat();
  }
  function beat() {
    var s = R.st[R.j];
    if (!s) { rest(); return; }
    var c = R.list[R.k];
    var beads = '';
    for (var b = 1; b <= s.of; b++) beads += '<span class="gim-bead' + (b <= s.n ? ' f' : '') + (b === s.n ? ' now' : '') + '"></span>';
    $('gim-beads').innerHTML = beads;
    $('gim-m-num').innerHTML = s.n + ' <small>из ' + s.of + '</small>';
    $('gim-m-word').textContent = s.word + (s.turns ? ' · ' + s.turn + ' из ' + s.turns : '');
    // Двигается образ; нет образа — лицо («Накажем язычок»). Лицо «Часиков» на
    // каждый счёт отражается: язык уходит к другому уголку рта.
    var ob = run.querySelector('.gim-obraz') || run.querySelector('.gim-litso');
    var li = run.querySelector('.gim-litso');
    if (ob) {
      ob.classList.toggle('shake', s.dv === 'shake');
      ob.style.transform = s.dv && DV[s.dv] ? DV[s.dv](s.p) : '';
    }
    if (li && li !== ob) li.style.transform = s.mir && s.p ? 'scaleX(-1)' : '';
    R.j += 1;
    later(s.dur, beat);
  }
  function rest() {
    var last = R.k + 1 >= R.list.length;
    R.mode = last ? 'end' : 'rest';
    if (last) {
      screen({ step: 'Гимнастика окончена', name: 'Готово', child: 'Можно начать ещё раз или закрыть зеркало',
               word: '' });
      $('gim-next').textContent = 'Ещё раз';
      $('gim-pause').hidden = true;  // ставить на паузу нечего (закон 14)
      clear();
      return;
    }
    var nx = R.list[R.k + 1];
    screen({ step: 'Упражнение ' + (R.k + 1) + ' из ' + R.list.length + ' — готово', name: 'Отдыхаем',
             child: 'Дальше — «' + nx.name + '»', word: '' });
    later(3, function () { startEx(R.k + 1); });
  }
  function openRun() {
    R.list = S.sel.map(at).filter(function (c) { return c.fazy && c.fazy.length; });
    if (!R.list.length) return;
    R.paused = false; $('gim-pause').textContent = 'Пауза';
    run.hidden = false; document.documentElement.classList.add('gim-lock');
    // Экран не гаснет, пока идёт занятие (планшет на столе). Не разрешили — не беда.
    try {
      if (navigator.wakeLock) navigator.wakeLock.request('screen')
        .then(function (l) { R.lock = l; }, function () { R.lock = null; });
    } catch (e) { /* молчим */ }
    intro(); run.focus();
  }
  function stopRun() {
    clear(); run.hidden = true; document.documentElement.classList.remove('gim-lock');
    try { if (R.lock) R.lock.release(); } catch (e) {} R.lock = null;
    $('gim-start').focus();
  }
  function pause() {
    if (R.mode === 'end') return;
    if (!R.paused) { R.left = Math.max(0, R.due - Date.now()); clear(); R.paused = true; $('gim-pause').textContent = 'Продолжить'; }
    else { R.paused = false; $('gim-pause').textContent = 'Пауза'; later(R.left / 1000, R.fn); }
  }
  function next() {
    R.paused = false; $('gim-pause').textContent = 'Пауза';
    if (R.mode === 'end') { intro(); return; }
    if (R.mode === 'intro') { startEx(0); return; }
    if (R.k + 1 < R.list.length) startEx(R.k + 1); else { R.k = R.list.length - 1; R.j = R.st.length; rest(); }
  }
  $('gim-start').addEventListener('click', openRun);
  // После щелчка фокус возвращается на зеркало: иначе пробел нажимал бы ту же
  // кнопку ещё раз, а не ставил паузу.
  $('gim-pause').addEventListener('click', function () { pause(); run.focus(); });
  $('gim-next').addEventListener('click', function () { next(); run.focus(); });
  $('gim-stop').addEventListener('click', stopRun);
  document.addEventListener('keydown', function (ev) {
    if (run.hidden) return;
    if (ev.key === 'Escape') { ev.preventDefault(); stopRun(); }
    else if (ev.key === 'ArrowRight') { ev.preventDefault(); next(); }
    else if ((ev.key === ' ' || ev.key === 'Spacebar') && ev.target === run) { ev.preventDefault(); pause(); }
  });

  // ── лист домой на неделю: то, что отмечено ───────────────────────────
  $('gim-print-btn').addEventListener('click', function () {
    var s = cur(), list = S.sel.map(at), days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    var head = '<tr><th>Упражнение</th>' + days.map(function (d) {
      return '<th>' + d + '<br>у · в</th>'; }).join('') + '</tr>';
    var rows = list.map(function (c) {
      return '<tr><td class="n">' + esc(c.name) + '</td>' +
        days.map(function () { return '<td>☐ ☐</td>'; }).join('') + '</tr>';
    }).join('');
    var ex = list.map(function (c, k) {
      // На печать — ч/б образ (закон 13: ч/б снят с цветного; тонер логопеда свой).
      var img = c.obraz_bw ? '<img src="' + esc(c.obraz_bw) + '" alt="" class="pic">' : '';
      return '<div class="ex">' + img + '<b>' + (k + 1) + '. ' + esc(c.name) + '</b> — ' + esc(c.child) +
        '<br>' + esc(c.how) + ' <i>Сколько: ' + esc(c.dose) + '.</i>' +
        (c.props ? ' Понадобится: ' + esc(c.props) + '.' : '') + '</div>';
    }).join('');
    var box = $('gim-print');
    if (box.parentNode !== document.body) document.body.appendChild(box);
    box.innerHTML =
      '<h1>Артикуляционная гимнастика на звук [' + esc(s.key) + '] — на неделю</h1>' +
      '<p class="rule">Каждый день по 2–5 минут, два раза — утром и вечером. За один раз — 2–3 ' +
      'упражнения, новое из них одно. Ребёнок сидит перед зеркалом, сначала всё делаем медленно. ' +
      'Не говорите ему, что он делает неверно: так он может отказаться заниматься. ' +
      'Отмечайте в таблице: у — утро, в — вечер.</p>' + ex +
      '<table>' + head + rows + '</table>' +
      '<p class="foot">По Фомичёвой М. Ф. (1989) и картотекам логопедов · logozvuk.com</p>';
    try {
      if (window.ym && window.METRIKA_ID) {
        var p = {}; p['[' + s.key + ']'] = 'печать';
        window.ym(window.METRIKA_ID, 'reachGoal', 'list', { 'лист получен': { 'гимнастика': p } });
      }
    } catch (e) { /* молчим */ }
    // Печать — только когда загрузились картинки листа: иначе на бумаге пустые места.
    var imgs = box.querySelectorAll('img'), left = imgs.length;
    var go = function () { window.print(); };
    if (!left) { go(); return; }
    imgs.forEach(function (im) {
      if (im.complete) { if (--left === 0) go(); }
      else { im.onload = im.onerror = function () { if (--left === 0) go(); }; }
    });
  });

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
    # «</» внутри <script> обрывает тег даже в строке (урок 08-25, `analytics`).
    blob = json.dumps(d, ensure_ascii=False).replace("</", "<\\/")
    icons = json.dumps({"hold": ICON_HOLD, "move": ICON_MOVE}).replace("</", "<\\/")
    play = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5v11l9-5.5z"/></svg>'
    return (
        f"<style>{CSS}</style>\n"
        '<div class="widget-box gim" id="gim">\n'
        '<div class="gim-in">\n'
        ' <div class="gim-desk">\n'
        '  <aside class="gim-side">\n'
        '   <p class="gim-label">Звук</p>\n'
        f'   <div class="gim-sounds" role="group" aria-label="Звук">{buttons}</div>\n'
        '   <p class="gim-note" id="gim-note"></p>\n'
        '   <p class="gim-label gim-gap">Занятие</p>\n'
        '   <button type="button" class="gim-toggle" id="gim-five" aria-pressed="false" '
        'title="Фомичёва: позу держат под счёт взрослого сначала до 5, постепенно до 10">'
        '<span class="box"></span><span>Держим до 5<small>для начала, потом до 10</small></span></button>\n'
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
        '  <button type="button" class="gim-btn" id="gim-print-btn" title="Печать для родителя: отмеченные '
        'упражнения, правила и таблица отметок на неделю">Лист домой</button>\n'
        f'  <button type="button" class="gim-btn gim-go" id="gim-start" title="Экран как зеркало: картинка '
        f'показывает движение, счёт идёт до конца и останавливается">{play}Начать у зеркала</button>\n'
        ' </div>\n'
        '</div>\n'
        '<div class="gim-mirror" id="gim-run" role="dialog" aria-modal="true" aria-label="Занятие у зеркала" '
        'tabindex="-1" hidden>\n'
        ' <div class="gim-frame"><div class="gim-glass">\n'
        '  <p class="gim-m-step" id="gim-m-step"></p>\n'
        '  <div class="gim-m-pics" id="gim-m-pics"></div>\n'
        '  <p class="gim-m-name" id="gim-m-name"></p>\n'
        '  <p class="gim-m-child" id="gim-m-child"></p>\n'
        '  <div class="gim-beads" id="gim-beads" aria-hidden="true"></div>\n'
        '  <p class="gim-m-num" id="gim-m-num" aria-live="off"></p>\n'
        '  <p class="gim-m-word" id="gim-m-word"></p>\n'
        ' </div></div>\n'
        ' <div class="gim-shelf">\n'
        '  <button type="button" class="gim-btn" id="gim-pause">Пауза</button>\n'
        '  <button type="button" class="gim-btn gim-go" id="gim-next">Дальше →</button>\n'
        '  <button type="button" class="gim-btn" id="gim-stop">Закончить</button>\n'
        '  <p class="gim-keys">Пробел — пауза · → — дальше · Esc — закончить</p>\n'
        ' </div>\n'
        '</div>\n'
        f'<script type="application/json" id="gim-data">{blob}</script>\n'
        f'<script type="application/json" id="gim-icons">{icons}</script>\n'
        "</div>\n"
        '<div id="gim-print"></div>\n'
        f"<script>{JS}</script>"
    )
