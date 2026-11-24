# -*- coding: utf-8 -*-
"""Виджет «Артикуляционная гимнастика» — первая страница-кластер (2026-11-23).

Зачем свой виджет, а не главный генератор в рамке. Канон Site Builders 2.0: кластер —
«примерно одна функция, названная разными словами», и при смене кластера меняется сам
виджет (`app-studio/knowledge-base/site-builders-2/01-vstrecha-01.md` §7); у страницы
кластера свой виджет первым экраном (`03-vstrecha-03.md` §6.1). Встроен прямо в
страницу, а не рамкой: содержимое iframe поисковик не индексирует.

ВИД — `dizajn/KONCEPCIYA.md`. Стол — страница, где взрослый выбирает: картотека из восьми
карточек, лицом образ, оборотом «как делать» (Фомичёва: «картинка-образ дается ребенку…, а
подробная запись — для родителей»). Занятие — экран-подсказка в деревянной раме: что делать,
сколько и счёт. ⚠ 24.11 (поздно) экран перестал называться зеркалом. Автор: «странно, что в
зеркало мы видим индюка», «если он смотрит в зеркало, какая разница, что на экране?». Зеркало
настоящее и стоит рядом: в него ребёнок проверяет себя, а экран говорит, что делать и сколько.

ЯЗЫК — для не-специалиста (автор 24.11: «мне должно быть понятно не специалисту»; «держим,
повторяем — не понял»; «2 из 5 — чего?»). На карточке вместо «держим/повторяем» — сколько
простыми словами (`schet.korotko`); в счёте всегда названа единица («3 из 10 щелчков»).

ЗАНЯТИЕ идёт как у Фомичёвой: рассказать → показать → выполнить. На экране: ввод в задание
(картинка, название, что делать, сколько; голос читает) → «приготовились: три, два, один» →
счёт до числа из таблицы и стоп → отдых → следующее. Сначала медленно, потом быстрее (Буденная:
темп сначала медленный); «Только начинаем» — держим до 5 и считаем медленнее (Фомичёва: от 5 к
10). Голос — встроенный в браузер (бесплатно, качество зависит от устройства); записанный голос —
по слову автора. Картинки не дёргаются: движение образа автор не понял («дрыгается весь индюк»);
осталось одно движение, которое показывает язык, — лицо «Часиков» отражается на каждый счёт.

ЛИСТ ДОМОЙ — сначала на экране (автор: «мы должны это видеть, перед тем как печатать или
сохранять в PDF или Word»): лист в рамке, текст правится прямо на нём, настройки — картинки
ч/б или цвет, таблица на неделю. Скачивание — те же ручки, что у главного генератора:
`/api/pdf` (служба печати автора; картинки вшиваются в лист, иначе служба их не видит) и
`/api/word`. HTML берётся из рамки — с правками.

СЧЁТ — таблицей у каждого упражнения (`gymnastics.json` → `schet`, формат — `schet_format`):
дозировки разные, по названию не угадать (закон 7). Данные — только `gymnastics.json`;
упражнения постановки (`excluded_from_sheet`) сюда не попадают. Ч и Ц: источник называет
комплексы по группе — «для свистящих звуков с, з, ц», «для шипящих звуков ш, ж, ч, щ».
Практика — `research/site/gimnastika_praktika_2026-11-24.md`.
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
            # Нет таблицы счёта — нет и занятия для этого упражнения: счёт не
            # придумывается из названия (закон 7).
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


CSS = r"""
.gim{--g-paper:#f7f5f1;--g-card:#fff;--g-ink:#16191d;--g-muted:#565d66;--g-line:#e6e2da;--g-edge:#d5d0c6;
  --g-brand:#2f6b4f;--g-brand-edge:#1f4e39;--g-tongue:#e8806e;--g-tongue-edge:#c9624f;--g-bead:#d9604c;
  --g-stage:#f3f7f7;--g-frame:#dcc49c;--g-frame-edge:#c3a676;--g-shelf:#e6d3b0;--g-chip:#f1ede4;
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
.gim-gap{margin-top:var(--s4)}
.gim-toggle{display:flex;gap:8px;align-items:flex-start;width:100%;padding:8px 10px;border:1px solid var(--g-edge);
  border-radius:12px;background:#fff;font:inherit;font-size:.9rem;cursor:pointer;color:var(--g-ink);text-align:left;
  box-shadow:0 2px 0 var(--g-edge)}
.gim-toggle .box{flex:none;width:18px;height:18px;margin-top:1px;border-radius:5px;border:2px solid var(--g-edge);background:#fff}
.gim-toggle[aria-pressed="true"]{border-color:var(--g-brand)}
.gim-toggle[aria-pressed="true"] .box{background:var(--g-brand);border-color:var(--g-brand);box-shadow:inset 0 0 0 3px #fff}
.gim-toggle small{display:block;color:var(--g-muted);font-size:.76rem;line-height:1.35;margin-top:2px}
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
.gim-go{background:var(--g-tongue);border-color:var(--g-tongue);color:var(--g-ink);font-weight:600;
  box-shadow:0 3px 0 var(--g-tongue-edge)}
.gim-go:active{box-shadow:0 1px 0 var(--g-tongue-edge)}
.gim-go svg{width:14px;height:14px;fill:currentColor;vertical-align:-1px;margin-right:4px}
.gim-sm{font-size:.9rem;padding:8px 14px}
@media (max-width:760px){
  .gim{padding:var(--s3) var(--s3) var(--s4)}
  .gim-desk{grid-template-columns:minmax(0,1fr)}
  .gim-sounds{grid-template-columns:repeat(7,1fr)}
  .gim-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
  .gim-card{height:12.6rem}
  /* На телефоне картотека длинная — полочка с кнопками едет вместе с экраном. */
  .gim-shelf-row{position:sticky;bottom:0;z-index:5;margin:var(--s3) calc(-1 * var(--s3)) 0;
    padding:10px var(--s3) calc(10px + env(safe-area-inset-bottom));background:var(--g-paper);
    border-top:1px solid var(--g-line);box-shadow:0 -6px 14px rgba(22,25,29,.06)}
  .gim-hint{display:none}
  .gim-shelf-row .gim-btn{flex:1 1 auto}
}
/* ── занятие на экране ──────────────────────────────────────────────── */
.gim-run{position:fixed;inset:0;z-index:1000;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:12px;padding:2.5vh 2vw;background:var(--g-paper)}
.gim-run[hidden],.gim-sheet[hidden]{display:none}
.gim-run:focus{outline:none}
.gim-frame{width:min(96vw,1100px);height:min(78vh,760px);padding:clamp(10px,1.6vw,22px);border-radius:30px;
  background:var(--g-frame);box-shadow:inset 0 0 0 2px var(--g-frame-edge),0 14px 34px rgba(60,40,10,.12)}
.gim-stage{position:relative;width:100%;height:100%;border-radius:20px;background:var(--g-stage);overflow:hidden;
  display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:2vh 3vw}
.gim-s-step{margin:0;font-size:clamp(.9rem,1.9vh,1.05rem);color:var(--g-muted)}
.gim-s-pics{display:flex;justify-content:center;align-items:center;gap:3vw;margin:1vh 0}
.gim-s-pics:empty{display:none}
.gim-s-pics img{width:min(26vh,230px);height:min(26vh,230px);max-width:40vw;object-fit:contain;mix-blend-mode:multiply;
  transition:transform .3s ease}
.gim-s-name{margin:0;font-family:var(--g-round);font-weight:700;font-size:clamp(1.7rem,4.8vh,2.9rem);line-height:1.1}
.gim-s-line{margin:.6vh 0 0;font-size:clamp(1.05rem,2.7vh,1.45rem);max-width:44rem}
.gim-s-plan{margin:.8vh 0 0;padding:4px 12px;border-radius:10px;background:#fff;font-size:clamp(.95rem,2.2vh,1.2rem);
  color:var(--g-muted)}
.gim-s-name:empty,.gim-s-plan:empty,.gim-s-line:empty,.gim-s-label:empty,.gim-s-unit:empty,.gim-s-big:empty{display:none}
.gim-s-label{margin:1.4vh 0 0;font-family:var(--g-round);font-weight:700;font-size:clamp(1.2rem,3.4vh,1.9rem);
  color:#1f4a5a}
.gim-s-big{margin:.4vh 0 0;font-family:var(--g-round);font-weight:800;font-size:clamp(3rem,11vh,6.5rem);line-height:1;
  color:var(--g-ink);font-variant-numeric:tabular-nums}
.gim-s-big.beat{animation:gim-beat .35s ease-out}
@keyframes gim-beat{0%{transform:scale(1.18)}100%{transform:scale(1)}}
.gim-s-unit{margin:.6vh 0 0;font-size:clamp(1rem,2.6vh,1.35rem);color:var(--g-muted)}
.gim-beads{display:flex;flex-wrap:wrap;justify-content:center;gap:clamp(5px,.9vh,10px);margin:1.4vh 0 0;max-width:90%}
.gim-beads:empty{display:none}
.gim-bead{width:clamp(12px,2.2vh,22px);height:clamp(12px,2.2vh,22px);border-radius:50%;background:#fff;
  box-shadow:inset 0 0 0 2px rgba(31,74,90,.18)}
.gim-bead.f{background:var(--g-bead);box-shadow:none}
.gim-bar{width:min(60%,420px);height:10px;border-radius:6px;background:#fff;margin:1.2vh auto 0;overflow:hidden;
  box-shadow:inset 0 0 0 1px rgba(31,74,90,.15)}
.gim-bar[hidden]{display:none}
.gim-bar i{display:block;height:100%;width:0;background:var(--g-bead);border-radius:6px}
.gim-run .gim-shelf{display:flex;flex-wrap:wrap;justify-content:center;align-items:center;gap:10px;
  width:min(96vw,1100px);padding:8px 12px;border-radius:14px;background:var(--g-shelf);
  box-shadow:inset 0 -3px 0 var(--g-frame-edge)}
.gim-voice[aria-pressed="false"]{color:var(--g-muted)}
.gim-run .gim-keys{margin:0 0 0 8px;font-size:.82rem;color:#6b5634}
@media (hover:none){.gim-run .gim-keys{display:none}}
@media (prefers-reduced-motion:reduce){
  .gim-card-in,.gim-s-pics img{transition:none}
  .gim-s-big.beat{animation:none}
}
html.gim-lock,html.gim-lock body{overflow:hidden}
/* ── лист домой: сначала на экране ─────────────────────────────────── */
.gim-sheet{position:fixed;inset:0;z-index:1000;display:flex;flex-direction:column;background:#e9e6df}
.gim-sheet-bar{display:flex;flex-wrap:wrap;align-items:center;gap:8px 12px;padding:10px 16px;background:var(--g-paper);
  border-bottom:1px solid var(--g-line)}
.gim-sheet-bar h2{margin:0 auto 0 4px;font-size:1.05rem;font-weight:600}
.gim-opts{display:flex;flex-wrap:wrap;align-items:center;gap:6px 14px;padding:8px 16px;background:var(--g-paper);
  border-bottom:1px solid var(--g-line);font-size:.88rem;color:var(--g-muted)}
.gim-seg{display:inline-flex;border:1px solid var(--g-edge);border-radius:999px;overflow:hidden;background:#fff}
.gim-seg button{font:inherit;font-size:.86rem;padding:5px 12px;border:0;background:none;cursor:pointer;color:var(--g-ink)}
.gim-seg button[aria-pressed="true"]{background:var(--g-brand);color:#fff}
.gim-chk{display:inline-flex;align-items:center;gap:6px;cursor:pointer;color:var(--g-ink)}
.gim-err{margin:0;padding:6px 16px;background:#fdf5ea;color:#8a5a00;font-size:.88rem}
.gim-sheet iframe{flex:1;width:100%;border:0;background:#e9e6df}
@media (max-width:760px){.gim-sheet-bar h2{flex-basis:100%;margin:0}}
"""

JS = r"""
(function () {
  var D = JSON.parse(document.getElementById('gim-data').textContent);
  var root = document.getElementById('gim');
  var $ = function (id) { return document.getElementById(id); };
  // Фомичёва 1989: «Не следует предлагать детям более двух-трех упражнений».
  var MAX = 3;
  var S = { i: 0, sel: [], flip: {}, start: false };
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
  // «Только начинаем»: держим до 5, а не до 10 (Фомичёва: «от 1 до 5 с постепенным увеличением до 10»).
  function holdN(n) { return S.start ? Math.min(5, n) : n; }
  function plan(c) {
    var f = c.fazy.filter(function (x) { return x.vid !== 'povtor'; })[0] || {};
    return (c.korotko || '').replace('{do}', holdN(f['do'] || 10)).replace('{derzhat}', holdN(f.derzhat || 3));
  }

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
      '<button type="button" class="gim-flip" data-f="' + j + '" title="Как делать — оборот карточки" aria-label="Как делать: ' +
      esc(c.name) + '"' + (fl ? ' tabindex="-1"' : '') + '>?</button></div>' +
      '<div class="gim-face gim-back"' + (fl ? '' : ' aria-hidden="true"') + '><div class="gim-back-text">' +
      '<p class="gim-bname">' + esc(c.name) + '</p>' +
      (c.child ? '<p class="gim-child">' + esc(c.child) + '</p>' : '') +
      '<p>' + esc(c.how) + '</p>' +
      '<p><b>Сколько:</b> ' + esc(plan(c)) + (c.props ? '. <b>Понадобится:</b> ' + esc(c.props) : '') + '</p>' +
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
    $('gim-start-tog').setAttribute('aria-pressed', S.start ? 'true' : 'false');
  }

  root.querySelectorAll('.gim-sounds button').forEach(function (b, k) {
    b.addEventListener('click', function () { S.i = k; reset(); render(); });
  });
  $('gim-start-tog').addEventListener('click', function () { S.start = !S.start; render(); });
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

  // ── голос: встроенный в браузер ─────────────────────────────────────
  // Бесплатно и без записи; звучит голосом устройства. Нет синтеза речи — нет и
  // кнопки (закон 14). Записанный голос — по слову автора.
  var V = { ok: !!(window.speechSynthesis && window.SpeechSynthesisUtterance), on: true, voice: null };
  function pickVoice() {
    try {
      var vs = window.speechSynthesis.getVoices().filter(function (v) { return /^ru/i.test(v.lang); });
      V.voice = vs.filter(function (v) { return /milena|милена|google|yuri|katya|irina/i.test(v.name); })[0] || vs[0] || null;
    } catch (e) { V.voice = null; }
  }
  if (V.ok) { pickVoice(); window.speechSynthesis.onvoiceschanged = pickVoice; }
  function hush() { try { if (V.ok) window.speechSynthesis.cancel(); } catch (e) {} }
  function say(t, rate) {
    if (!V.ok || !V.on || !t) return;
    try {
      hush();
      var u = new SpeechSynthesisUtterance(t);
      u.lang = 'ru-RU'; if (V.voice) u.voice = V.voice; u.rate = rate || 1;
      window.speechSynthesis.speak(u);
    } catch (e) { /* молчим */ }
  }

  // ── занятие: рассказать → приготовиться → считать → отдыхать ─────────
  var WORD = ['', 'раз', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять', 'десять',
    'одиннадцать', 'двенадцать', 'тринадцать', 'четырнадцать', 'пятнадцать', 'шестнадцать', 'семнадцать',
    'восемнадцать', 'девятнадцать', 'двадцать'];
  // Сначала медленно, потом быстрее (Буденная: темп сначала медленный). Первая треть
  // повторов — в полтора раза медленнее; «Только начинаем» — всё медленнее.
  function steps(c) {
    var out = [], slow = S.start ? 1.3 : 1;
    c.fazy.forEach(function (f) {
      if (f.vid === 'derzhim') {
        var n = holdN(f['do']);
        for (var k = 1; k <= n; k++) out.push({ kind: 'hold', n: k, of: n, dur: slow, label: f.slovo || 'Держим' });
      } else if (f.vid === 'povtor') {
        var arr = Array.isArray(f.temp), base = arr ? f.temp[0] : f.temp, long = base >= 3;
        var t0 = arr ? f.temp[0] : f.temp * 1.5, t1 = arr ? f.temp[1] : f.temp, third = Math.ceil(f.raz / 3);
        for (var r = 1; r <= f.raz; r++) {
          var dur, tempo = '';
          if (long) dur = f.temp;
          else if (arr) { dur = t0 + (t1 - t0) * (f.raz > 1 ? (r - 1) / (f.raz - 1) : 0); tempo = r <= third ? 'медленно' : 'быстрее'; }
          else { dur = r <= third ? t0 : t1; tempo = r <= third ? 'медленно' : 'быстрее'; }
          out.push({ kind: 'rep', n: r, of: f.raz, dur: dur * slow, label: f.slovo || 'Повторяем', ed: f.ed || 'раз',
                     tempo: tempo, long: long, p: r % 2, mir: !!f.zerkalo });
        }
      } else if (f.vid === 'polozheniya') {
        var h = holdN(f.derzhat);
        for (var kr = 0; kr < f.krugov; kr++) {
          f.pozicii.forEach(function (pz, pi) {
            for (var q = 1; q <= h; q++) out.push({ kind: 'pos', n: q, of: h, dur: slow, label: pz,
              turn: kr * f.pozicii.length + pi + 1, turns: f.krugov * f.pozicii.length, first: q === 1 });
          });
        }
      }
    });
    return out;
  }
  var R = { list: [], k: -1, st: [], j: 0, t: null, due: 0, left: 0, fn: null, paused: false, mode: '', lock: null };
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
    $('gim-s-step').textContent = o.step || '';
    if (o.pics !== undefined) $('gim-s-pics').innerHTML = o.pics;
    $('gim-s-name').textContent = o.name || '';
    $('gim-s-line').textContent = o.line || '';
    $('gim-s-plan').textContent = o.plan || '';
    $('gim-s-label').textContent = o.label || '';
    $('gim-s-big').textContent = o.big || '';
    $('gim-s-unit').textContent = o.unit || '';
    $('gim-beads').innerHTML = o.beads || '';
    $('gim-bar').hidden = true;
  }
  function pulse() { var b = $('gim-s-big'); b.classList.remove('beat'); void b.offsetWidth; b.classList.add('beat'); }
  function welcome() {
    R.mode = 'welcome';
    $('gim-next').textContent = 'Дальше →'; $('gim-pause').hidden = false;
    screen({ step: 'Начинаем гимнастику', pics: '', name: 'Садимся ровно',
             line: 'Рядом поставьте зеркало: на экране — что делать и сколько, в зеркале ребёнок видит, получается ли.',
             plan: 'Упражнений: ' + R.list.length + ' · сначала медленно' });
    say('Начинаем гимнастику. Садимся ровно.');
    later(5, function () { intro(0); });
  }
  // Ввод в задание: картинка, что делать и сколько — голос читает.
  function intro(k) {
    R.k = k; R.mode = 'intro'; var c = R.list[k];
    $('gim-next').textContent = 'Дальше →';
    screen({ step: 'Упражнение ' + (k + 1) + ' из ' + R.list.length, pics: pics(c), name: c.name,
             line: c.child ? c.child.charAt(0).toUpperCase() + c.child.slice(1) : '', plan: 'Сколько: ' + plan(c) });
    say(c.name + '. ' + (c.child || '') + '.');
    later(Math.max(5, Math.min(9, 2 + (c.name.length + (c.child || '').length) / 14)), function () { ready(3); });
  }
  function ready(n) {
    R.mode = 'ready'; var c = R.list[R.k];
    screen({ step: 'Упражнение ' + (R.k + 1) + ' из ' + R.list.length + ' · ' + c.name, label: 'Приготовились',
             big: String(n) });
    say(n === 3 ? 'Приготовились. Три' : n === 2 ? 'два' : 'один');  // в отсчёте «один», не «раз»
    pulse();
    later(1, function () { if (n > 1) ready(n - 1); else count(); });
  }
  function count() { var c = R.list[R.k]; R.st = steps(c); R.j = 0; R.mode = 'count'; beat(); }
  function beat() {
    var s = R.st[R.j];
    if (!s) { rest(); return; }
    var c = R.list[R.k], unit = '', beads = '', b;
    if (s.kind === 'hold') unit = 'держим, пока считаем до ' + s.of;
    else if (s.kind === 'pos') unit = 'считаем до ' + s.of + ' · смена ' + s.turn + ' из ' + s.turns;
    else unit = 'из ' + s.of + ' ' + s.ed + (s.long ? ' · каждый ' + Math.round(s.dur) + ' секунд' : '') +
      (s.tempo ? ' · ' + s.tempo : '');
    if (!s.long) for (b = 1; b <= s.of; b++) beads += '<span class="gim-bead' + (b <= s.n ? ' f' : '') + '"></span>';
    screen({ step: 'Упражнение ' + (R.k + 1) + ' из ' + R.list.length + ' · ' + c.name, label: s.label,
             big: String(s.n), unit: unit, beads: beads });
    pulse();
    if (s.long) {  // «5 секунд» — полоса времени, чтобы было видно, сколько ещё
      var bar = $('gim-bar'), fill = bar.firstChild; bar.hidden = false;
      fill.style.transition = 'none'; fill.style.width = '0';
      void fill.offsetWidth; fill.style.transition = 'width ' + s.dur + 's linear'; fill.style.width = '100%';
    }
    // Единственное движение картинки — лицо «Часиков»: на каждый счёт язык у другого уголка рта.
    var li = run.querySelector('.gim-litso');
    if (li) li.style.transform = s.mir && s.p ? 'scaleX(-1)' : '';
    var word = WORD[s.n] || String(s.n);
    say(s.kind === 'pos' && s.first ? s.label + '. ' + word : word, s.dur < 0.9 ? 1.4 : 1);
    R.j += 1;
    later(s.dur, beat);
  }
  function rest() {
    var last = R.k + 1 >= R.list.length;
    if (last) {
      R.mode = 'end'; clear();
      screen({ step: 'Гимнастика окончена', pics: '', name: 'Готово', line: 'Можно начать ещё раз или закрыть занятие.' });
      $('gim-next').textContent = 'Ещё раз';
      $('gim-pause').hidden = true;  // ставить на паузу нечего (закон 14)
      say('Гимнастика окончена.');
      return;
    }
    R.mode = 'rest'; var nx = R.list[R.k + 1];
    screen({ step: 'Упражнение ' + (R.k + 1) + ' из ' + R.list.length + ' — готово', pics: '', name: 'Отдыхаем',
             line: 'Дальше — «' + nx.name + '»' });
    say('Отдыхаем.');
    later(3, function () { intro(R.k + 1); });
  }
  function openRun() {
    R.list = S.sel.map(at).filter(function (c) { return c.fazy && c.fazy.length; });
    if (!R.list.length) return;
    R.paused = false; $('gim-pause').textContent = 'Пауза';
    $('gim-voice').hidden = !V.ok;
    run.hidden = false; document.documentElement.classList.add('gim-lock');
    // Экран не гаснет, пока идёт занятие (планшет на столе). Не разрешили — не беда.
    try {
      if (navigator.wakeLock) navigator.wakeLock.request('screen')
        .then(function (l) { R.lock = l; }, function () { R.lock = null; });
    } catch (e) { /* молчим */ }
    welcome(); run.focus();
  }
  function stopRun() {
    clear(); hush(); run.hidden = true; document.documentElement.classList.remove('gim-lock');
    try { if (R.lock) R.lock.release(); } catch (e) {} R.lock = null;
    $('gim-start').focus();
  }
  function pause() {
    if (R.mode === 'end') return;
    if (!R.paused) {
      R.left = Math.max(0, R.due - Date.now()); clear(); hush(); R.paused = true;
      $('gim-pause').textContent = 'Продолжить';
      var fill = $('gim-bar').firstChild;
      if (fill) { fill.style.width = getComputedStyle(fill).width; fill.style.transition = 'none'; }
    } else {
      R.paused = false; $('gim-pause').textContent = 'Пауза';
      later(R.left / 1000, R.fn);
    }
  }
  function next() {
    R.paused = false; $('gim-pause').textContent = 'Пауза'; hush();
    if (R.mode === 'end') { welcome(); return; }
    if (R.mode === 'welcome') { intro(0); return; }
    if (R.mode === 'intro' || R.mode === 'ready') { clear(); count(); return; }
    if (R.k + 1 < R.list.length) intro(R.k + 1); else { R.k = R.list.length - 1; rest(); }
  }
  $('gim-start').addEventListener('click', openRun);
  // После щелчка фокус возвращается на экран занятия: иначе пробел нажимал бы ту
  // же кнопку ещё раз, а не ставил паузу.
  $('gim-pause').addEventListener('click', function () { pause(); run.focus(); });
  $('gim-next').addEventListener('click', function () { next(); run.focus(); });
  $('gim-stop').addEventListener('click', stopRun);
  $('gim-voice').addEventListener('click', function () {
    V.on = !V.on; if (!V.on) hush();
    this.setAttribute('aria-pressed', V.on ? 'true' : 'false');
    this.textContent = V.on ? 'Голос: вкл' : 'Голос: выкл';
    run.focus();
  });
  document.addEventListener('keydown', function (ev) {
    if (run.hidden) return;
    if (ev.key === 'Escape') { ev.preventDefault(); stopRun(); }
    else if (ev.key === 'ArrowRight') { ev.preventDefault(); next(); }
    else if ((ev.key === ' ' || ev.key === 'Spacebar') && ev.target === run) { ev.preventDefault(); pause(); }
  });

  // ── лист домой: на экране, с правкой, потом печать / PDF / Word ──────
  var L = { colour: false, table: true };
  var sheet = $('gim-sheet'), frame = $('gim-sheet-frame');
  function sheetDoc() {
    var s = cur(), list = S.sel.map(at), days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    var ex = list.map(function (c, k) {
      var bw = c.obraz_bw || c.obraz || c.litso, col = c.obraz || c.litso;
      var img = bw ? '<img src="' + esc(L.colour ? col : bw) + '" data-bw="' + esc(bw) + '" data-col="' + esc(col) +
        '" alt="">' : '';
      return '<div class="ex">' + img + '<div><b>' + (k + 1) + '. ' + esc(c.name) + '</b> — ' + esc(c.child) +
        '<br>' + esc(c.how) + '<br><i>Сколько: ' + esc(plan(c)) + '.</i>' +
        (c.props ? ' Понадобится: ' + esc(c.props) + '.' : '') + '</div></div>';
    }).join('');
    var head = '<tr><th>Упражнение</th>' + days.map(function (d) { return '<th>' + d + '<br>у · в</th>'; }).join('') + '</tr>';
    var rows = list.map(function (c) {
      return '<tr><td class="n">' + esc(c.name) + '</td>' + days.map(function () { return '<td>☐ ☐</td>'; }).join('') + '</tr>';
    }).join('');
    return '<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">' +
      '<title>Артикуляционная гимнастика на звук [' + esc(s.key) + ']</title><style>' +
      '@page{size:A4;margin:14mm}html{background:#e9e6df}' +
      'body{margin:16px auto;width:182mm;min-height:269mm;box-sizing:border-box;background:#fff;padding:14mm;' +
      'box-shadow:0 2px 12px rgba(0,0,0,.1);font:12pt/1.45 Arial,Helvetica,sans-serif;color:#000}' +
      '@media print{html{background:#fff}body{margin:0;width:auto;min-height:0;padding:0;box-shadow:none}}' +
      'h1{font-size:17pt;margin:0 0 4pt}.sub{margin:0 0 10pt;color:#333}' +
      '.rule{margin:0 0 12pt;padding:8pt 10pt;border:1px solid #999;border-radius:6pt}' +
      '.ex{display:flex;gap:10pt;margin:0 0 10pt;page-break-inside:avoid}' +
      '.ex img{width:24mm;height:24mm;object-fit:contain;flex:none}.ex b{font-size:13pt}' +
      'table{border-collapse:collapse;width:100%;margin-top:6pt}' +
      'th,td{border:1px solid #000;padding:4pt;font-size:10pt;text-align:center}td.n{text-align:left;width:34%}' +
      '.foot{margin-top:12pt;font-size:9pt;color:#555}body.no-table .tbl{display:none}' +
      '@media screen{html.fit body{zoom:var(--z)}}' +
      '[contenteditable]:focus{outline:none}' +
      '</style></head><body contenteditable="true" spellcheck="false" class="' + (L.table ? '' : 'no-table') + '">' +
      '<h1>Артикуляционная гимнастика на звук [' + esc(s.key) + ']</h1>' +
      '<p class="sub">Имя: ____________________ &nbsp; Неделя: с ______ по ______</p>' +
      '<div class="rule">Каждый день по 2–5 минут, два раза — утром и вечером. Ребёнок сидит перед зеркалом. ' +
      'Сначала всё делаем медленно. Не говорите ребёнку, что он делает неверно: так он может отказаться ' +
      'заниматься.</div>' + ex +
      '<div class="tbl"><p><b>Отмечайте, когда сделали:</b> у — утро, в — вечер.</p><table>' + head + rows + '</table></div>' +
      '<p class="foot">По Фомичёвой М. Ф. (1989) и картотекам логопедов · logozvuk.com</p></body></html>';
  }
  function syncOpts() {
    $('gim-o-bw').setAttribute('aria-pressed', L.colour ? 'false' : 'true');
    $('gim-o-col').setAttribute('aria-pressed', L.colour ? 'true' : 'false');
    $('gim-o-tbl').checked = L.table;
  }
  function openSheet() {
    L.colour = false; L.table = true; syncOpts(); $('gim-err').textContent = '';
    // Курсор в листе — клавиши ловит сам лист, наверх они не всплывают: Esc
    // слушаем и там (поймано 24.11 — лист не закрывался после щелчка по нему).
    frame.onload = function () {
      try {
        var d = frame.contentDocument;
        d.addEventListener('keydown', function (ev) { if (ev.key === 'Escape') closeSheet(); });
        // Телефон: А4 шире экрана — на экране лист уменьшается целиком. Только экран:
        // в печать, PDF и Word масштаб не уходит (`docClone` его снимает).
        var w = frame.clientWidth, bw = d.body.offsetWidth + 32;
        if (bw > w) { d.documentElement.style.setProperty('--z', (w / bw).toFixed(3)); d.documentElement.classList.add('fit'); }
      } catch (e) { /* молчим */ }
    };
    frame.srcdoc = sheetDoc();
    sheet.hidden = false; document.documentElement.classList.add('gim-lock');
    $('gim-sheet-back').focus();
  }
  function closeSheet() {
    sheet.hidden = true; document.documentElement.classList.remove('gim-lock'); $('gim-print-btn').focus();
  }
  // Настройки меняют лист БЕЗ пересборки — правки в тексте не теряются.
  function applyOpts() {
    var d = frame.contentDocument; syncOpts();
    if (!d || !d.body) return;
    d.body.classList.toggle('no-table', !L.table);
    d.querySelectorAll('img[data-bw]').forEach(function (im) { im.src = L.colour ? im.dataset.col : im.dataset.bw; });
  }
  function goal(fmt) {
    try {
      if (window.ym && window.METRIKA_ID) {
        var p = {}; p['[' + cur().key + ']'] = fmt;
        window.ym(window.METRIKA_ID, 'reachGoal', 'list', { 'лист получен': { 'гимнастика': p } });
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
    return c;
  }
  function fileName() { return 'Гимнастика на звук ' + cur().key; }
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
        'PDF сейчас не собрать. Лист на месте — сохраните его в Word или распечатайте.');
      if (ok) goal('PDF');
    } catch (e) {
      $('gim-err').textContent = 'Не дозвонились до службы печати. Лист на месте — сохраните его в Word или распечатайте.';
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
  $('gim-print-btn').addEventListener('click', openSheet);
  $('gim-sheet-back').addEventListener('click', closeSheet);
  $('gim-o-bw').addEventListener('click', function () { L.colour = false; applyOpts(); });
  $('gim-o-col').addEventListener('click', function () { L.colour = true; applyOpts(); });
  $('gim-o-tbl').addEventListener('change', function () { L.table = this.checked; applyOpts(); });
  document.addEventListener('keydown', function (ev) { if (!sheet.hidden && ev.key === 'Escape') closeSheet(); });

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
        '   <p class="gim-label gim-gap">Ребёнок</p>\n'
        '   <button type="button" class="gim-toggle" id="gim-start-tog" aria-pressed="false" '
        'title="Фомичёва: позу держат под счёт взрослого сначала до 5, постепенно до 10; сначала всё медленно">'
        '<span class="box"></span><span>Только начинаем<small>держим до 5, а не до 10, и считаем медленнее'
        '</small></span></button>\n'
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
        '  <button type="button" class="gim-btn" id="gim-print-btn" title="Лист для родителя: сначала на экране, '
        'потом печать, PDF или Word">Лист домой</button>\n'
        f'  <button type="button" class="gim-btn gim-go" id="gim-start" title="Экран ведёт занятие: что делать, '
        f'сколько и счёт до конца">{play}Начать занятие</button>\n'
        ' </div>\n'
        '</div>\n'
        '<div class="gim-run" id="gim-run" role="dialog" aria-modal="true" aria-label="Занятие" tabindex="-1" hidden>\n'
        ' <div class="gim-frame"><div class="gim-stage">\n'
        '  <p class="gim-s-step" id="gim-s-step"></p>\n'
        '  <div class="gim-s-pics" id="gim-s-pics"></div>\n'
        '  <p class="gim-s-name" id="gim-s-name"></p>\n'
        '  <p class="gim-s-line" id="gim-s-line"></p>\n'
        '  <p class="gim-s-plan" id="gim-s-plan"></p>\n'
        '  <p class="gim-s-label" id="gim-s-label"></p>\n'
        '  <p class="gim-s-big" id="gim-s-big" aria-live="off"></p>\n'
        '  <p class="gim-s-unit" id="gim-s-unit"></p>\n'
        '  <div class="gim-beads" id="gim-beads" aria-hidden="true"></div>\n'
        '  <div class="gim-bar" id="gim-bar" hidden><i></i></div>\n'
        ' </div></div>\n'
        ' <div class="gim-shelf">\n'
        '  <button type="button" class="gim-btn gim-sm gim-voice" id="gim-voice" aria-pressed="true" '
        'title="Голос читает задание и считает. Это голос вашего устройства">Голос: вкл</button>\n'
        '  <button type="button" class="gim-btn" id="gim-pause">Пауза</button>\n'
        '  <button type="button" class="gim-btn gim-go" id="gim-next">Дальше →</button>\n'
        '  <button type="button" class="gim-btn" id="gim-stop">Закончить</button>\n'
        '  <p class="gim-keys">Пробел — пауза · → — дальше · Esc — закончить</p>\n'
        ' </div>\n'
        '</div>\n'
        '<div class="gim-sheet" id="gim-sheet" role="dialog" aria-modal="true" aria-label="Лист домой" hidden>\n'
        ' <div class="gim-sheet-bar">\n'
        '  <button type="button" class="gim-btn gim-sm" id="gim-sheet-back">← К упражнениям</button>\n'
        '  <h2>Лист домой — так он будет выглядеть</h2>\n'
        '  <button type="button" class="gim-btn gim-sm" id="gim-print">Печать</button>\n'
        '  <button type="button" class="gim-btn gim-sm" id="gim-word">Скачать Word</button>\n'
        '  <button type="button" class="gim-btn gim-sm gim-go" id="gim-pdf">Скачать PDF</button>\n'
        ' </div>\n'
        ' <div class="gim-opts">\n'
        '  <span>Картинки:</span><span class="gim-seg"><button type="button" id="gim-o-bw" aria-pressed="true">'
        'чёрно-белые</button><button type="button" id="gim-o-col" aria-pressed="false">цветные</button></span>\n'
        '  <label class="gim-chk"><input type="checkbox" id="gim-o-tbl" checked> таблица отметок на неделю</label>\n'
        '  <span>Текст листа можно поправить прямо на нём — так он и сохранится.</span>\n'
        ' </div>\n'
        ' <p class="gim-err" id="gim-err" role="status"></p>\n'
        ' <iframe id="gim-sheet-frame" title="Лист домой"></iframe>\n'
        '</div>\n'
        f'<script type="application/json" id="gim-data">{blob}</script>\n'
        "</div>\n"
        f"<script>{JS}</script>"
    )
