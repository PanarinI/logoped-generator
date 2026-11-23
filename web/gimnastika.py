# -*- coding: utf-8 -*-
"""Виджет «Артикуляционная гимнастика» — первая страница-кластер (2026-11-23).

Зачем свой виджет, а не главный генератор в рамке. Канон Site Builders 2.0: кластер —
«примерно одна функция, названная разными словами», и при смене кластера меняется сам
виджет (`app-studio/knowledge-base/site-builders-2/01-vstrecha-01.md` §7); у страницы
кластера свой виджет первым экраном (`03-vstrecha-03.md` §6.1). Встроен прямо в
страницу, а не рамкой: содержимое iframe поисковик не индексирует, а здесь текст
комплексов и есть польза.

Данные — только `logoped_slovar/gymnastics.json` (разбор Фомичёвой 1989 и картотек
практиков, с тирами). Набор недели (`sheet_4`) и запас (`alternates`) — те же, что в
разминке листа «Занятие»; упражнения постановки (`excluded_from_sheet`: Барабанщики,
Моторчик…) сюда не попадают — на автоматизации их не делают.

Ч и Ц. Своих комплексов в файле нет, но источник называет комплексы по ГРУППЕ:
«для свистящих звуков с, з, ц» и «для шипящих звуков ш, ж, ч, щ» (`derivation_note`
у [З] и [Ж]). Поэтому [Ц] берёт комплекс [С], [Ч] — комплекс [Ш], с тем же тиром
«книга», что у [З] и [Ж]. Появятся в файле свои — возьмутся они.

Картинок упражнений пока нет — второй шаг (слово автора 23.11).
Счёт в «Начать» — только темп «под счёт», раз в секунду. Сколько делать, говорит
дозировка источника над ним; своей «нормы» счётчик не придумывает (закон 2: материал
не утверждает больше, чем мы можем показать). «У зеркала» не пишем: в источниках
проекта этого нет.
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

    def card(eid: str) -> Dict[str, str]:
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
        }

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
        sounds.append({
            "key": s,
            "note": note,
            "week": [card(i) for i in c["sheet_4"] if i in ex],
            "more": [card(i) for i in c.get("alternates", []) if i in ex],
        })
    return {"sounds": sounds}


CSS = r"""
.gim{padding:var(--s4) var(--s4) var(--s5)}
.gim-in{max-width:52rem;margin:0 auto}
.gim-title{font-size:1.05rem;margin:0 0 var(--s2);color:var(--ink-soft);font-weight:600}
.gim-sounds{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 var(--s2)}
.gim-sounds button{min-width:2.9rem;padding:6px 10px;border:1px solid var(--line);border-radius:8px;
  background:#fff;font:inherit;font-size:1.05rem;cursor:pointer;color:var(--ink)}
.gim-sounds button[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
.gim-note{margin:0 0 var(--s3);font-size:.9rem;color:var(--ink-soft);min-height:1.4em}
.gim-list{list-style:none;margin:0;padding:0;display:grid;gap:var(--s3);
  grid-template-columns:repeat(auto-fill,minmax(15.5rem,1fr))}
.gim-card{background:#fff;border:1px solid var(--line);border-radius:10px;padding:var(--s3);
  display:flex;flex-direction:column;gap:6px}
.gim-card.off{opacity:.55}
.gim-card h3{margin:0;font-size:1.1rem;line-height:1.3}
.gim-kind{font-size:.78rem;font-weight:400;color:var(--ink-soft);border:1px solid var(--line);
  border-radius:20px;padding:0 8px;margin-left:6px;white-space:nowrap}
.gim-card p{margin:0;font-size:.93rem;line-height:1.45}
.gim-child{font-style:italic}
.gim-small{font-size:.82rem !important;color:var(--ink-soft)}
.gim-pick{font-size:.88rem;display:flex;gap:6px;align-items:center;cursor:pointer;color:var(--ink-soft)}
.gim-more-btn{margin:var(--s3) 0 0;background:none;border:0;padding:0;color:var(--accent);
  font:inherit;font-size:.95rem;cursor:pointer;text-decoration:underline}
.gim-more{margin-top:var(--s3)}
.gim-actions{display:flex;flex-wrap:wrap;gap:var(--s2);margin:var(--s4) 0 var(--s2)}
.gim-actions button,.gim-run button{font:inherit;font-size:1rem;padding:10px 18px;border-radius:10px;
  border:1px solid var(--line);background:#fff;cursor:pointer;color:var(--ink)}
.gim-actions .gim-primary,.gim-run .gim-primary{background:var(--accent);border-color:var(--accent);color:#fff}
.gim-actions button:disabled{opacity:.45;cursor:default}
.gim-hint{margin:0;font-size:.88rem;color:var(--ink-soft)}
.gim-run{max-width:36rem;margin:0 auto;text-align:center;padding:var(--s4) 0}
.gim-run h3{font-size:1.7rem;margin:var(--s2) 0}
.gim-run p{margin:var(--s2) 0}
.gim-count{font-size:5.5rem;font-weight:700;line-height:1;margin:var(--s4) 0;color:var(--accent);
  font-variant-numeric:tabular-nums}
.gim-run-btns{display:flex;justify-content:center;flex-wrap:wrap;gap:var(--s2)}
#gim-print{display:none}
@media print{
  body>*{display:none !important}
  body>#gim-print{display:block !important;font:12pt/1.4 Arial,sans-serif;color:#000}
  #gim-print h1{font-size:16pt;margin:0 0 6pt}
  #gim-print .rule{margin:0 0 10pt}
  #gim-print .ex{margin:0 0 8pt;page-break-inside:avoid}
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
  var root = document.getElementById('gim');
  var $ = function (id) { return document.getElementById(id); };
  var S = { i: 0, more: false, picked: {} };
  var esc = function (t) {
    return String(t || '').replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  };
  var cur = function () { return D.sounds[S.i]; };
  var all = function () { return cur().week.concat(cur().more); };

  function resetPicks() {
    S.picked = {};
    // Фомичёва: за один раз 2–3 упражнения — по умолчанию в занятие идут три.
    cur().week.forEach(function (c, k) { if (k < 3) S.picked[c.name] = true; });
  }

  function cardHtml(c) {
    var on = !!S.picked[c.name];
    return '<li class="gim-card' + (on ? '' : ' off') + '">' +
      '<label class="gim-pick"><input type="checkbox" data-n="' + esc(c.name) + '"' +
      (on ? ' checked' : '') + '> в занятие</label>' +
      '<h3>' + esc(c.name) + (c.kind ? '<span class="gim-kind">' + esc(c.kind) + '</span>' : '') + '</h3>' +
      (c.child ? '<p class="gim-child">' + esc(c.child) + '</p>' : '') +
      '<p>' + esc(c.how) + '</p>' +
      '<p><b>Сколько:</b> ' + esc(c.dose) + '</p>' +
      (c.props ? '<p><b>Понадобится:</b> ' + esc(c.props) + '</p>' : '') +
      (c.why ? '<p class="gim-small">Зачем: ' + esc(c.why) + '</p>' : '') +
      '<p class="gim-small" title="' + esc(c.src_full) + '">Источник: ' + esc(c.src) + '</p>' +
      '</li>';
  }

  function render() {
    var s = cur();
    root.querySelectorAll('.gim-sounds button').forEach(function (b, k) {
      b.setAttribute('aria-pressed', k === S.i ? 'true' : 'false');
    });
    $('gim-note').textContent = s.note || '';
    $('gim-week').innerHTML = s.week.map(cardHtml).join('');
    $('gim-more').innerHTML = s.more.map(cardHtml).join('');
    $('gim-more').hidden = !S.more;
    $('gim-more-btn').textContent = S.more ? 'Скрыть запас' : 'Ещё упражнения (' + s.more.length + ')';
    $('gim-more-btn').hidden = !s.more.length;
    var n = all().filter(function (c) { return S.picked[c.name]; }).length;
    $('gim-start').disabled = !n;
    $('gim-start').textContent = n ? '▶ Начать: ' + n + ' ' + plural(n) : 'Отметьте упражнения';
  }

  function plural(n) {
    var a = n % 10, b = n % 100;
    if (a === 1 && b !== 11) return 'упражнение';
    if (a >= 2 && a <= 4 && (b < 12 || b > 14)) return 'упражнения';
    return 'упражнений';
  }

  root.addEventListener('change', function (ev) {
    var t = ev.target;
    if (t && t.dataset && t.dataset.n) { S.picked[t.dataset.n] = t.checked; render(); }
  });

  // ── занятие по счёту ──────────────────────────────────────────────────
  var R = { list: [], k: 0, n: 0, timer: null };
  function tick() { R.n += 1; $('gim-count').textContent = R.n; }
  function showRun() {
    var c = R.list[R.k];
    $('gim-step').textContent = 'Упражнение ' + (R.k + 1) + ' из ' + R.list.length;
    $('gim-run-name').textContent = c.name;
    $('gim-run-child').textContent = c.child || '';
    $('gim-run-dose').textContent = 'Сколько: ' + c.dose;
    R.n = 0; $('gim-count').textContent = '0';
    clearInterval(R.timer); R.timer = setInterval(tick, 1000);
    $('gim-pause').textContent = 'Пауза';
    $('gim-next').textContent = R.k + 1 < R.list.length ? 'Дальше →' : 'Готово';
  }
  // Кнопка «Начать» стоит внизу длинного списка: без прокрутки панель занятия
  // открывалась бы над краем экрана, и человек видел бы низ страницы (поймано 23.11).
  function toTop() { root.scrollIntoView({ block: 'start' }); }
  function stopRun() {
    clearInterval(R.timer); R.timer = null;
    $('gim-run').hidden = true; $('gim-main').hidden = false; toTop();
  }
  $('gim-start').addEventListener('click', function () {
    R.list = all().filter(function (c) { return S.picked[c.name]; });
    if (!R.list.length) return;
    R.k = 0; $('gim-main').hidden = true; $('gim-run').hidden = false; showRun(); toTop();
  });
  $('gim-pause').addEventListener('click', function () {
    if (R.timer) { clearInterval(R.timer); R.timer = null; this.textContent = 'Продолжить'; }
    else { R.timer = setInterval(tick, 1000); this.textContent = 'Пауза'; }
  });
  $('gim-next').addEventListener('click', function () {
    if (R.k + 1 < R.list.length) { R.k += 1; showRun(); } else { stopRun(); }
  });
  $('gim-stop').addEventListener('click', stopRun);

  // ── лист домой на неделю ──────────────────────────────────────────────
  $('gim-print-btn').addEventListener('click', function () {
    var s = cur(), days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    var head = '<tr><th>Упражнение</th>' + days.map(function (d) {
      return '<th>' + d + '<br>у · в</th>'; }).join('') + '</tr>';
    var rows = s.week.map(function (c) {
      return '<tr><td class="n">' + esc(c.name) + '</td>' +
        days.map(function () { return '<td>☐ ☐</td>'; }).join('') + '</tr>';
    }).join('');
    var ex = s.week.map(function (c, k) {
      return '<div class="ex"><b>' + (k + 1) + '. ' + esc(c.name) + '</b> — ' + esc(c.child) +
        '<br>' + esc(c.how) + ' <i>Сколько: ' + esc(c.dose) + '.</i>' +
        (c.props ? ' Понадобится: ' + esc(c.props) + '.' : '') + '</div>';
    }).join('');
    var box = $('gim-print');
    if (box.parentNode !== document.body) document.body.appendChild(box);
    box.innerHTML =
      '<h1>Артикуляционная гимнастика на звук [' + esc(s.key) + '] — на неделю</h1>' +
      '<p class="rule">Каждый день по 2–5 минут, два раза — утром и вечером. За один раз — 2–3 ' +
      'упражнения, новое из них одно. Ребёнок сидит. Не говорите ему, что он делает неверно: ' +
      'так он может отказаться заниматься. Отмечайте в таблице: у — утро, в — вечер.</p>' + ex +
      '<table>' + head + rows + '</table>' +
      '<p class="foot">По Фомичёвой М. Ф. (1989) и картотекам логопедов · logozvuk.com</p>';
    try {
      if (window.ym && window.METRIKA_ID) {
        var p = {}; p['[' + s.key + ']'] = 'печать';
        window.ym(window.METRIKA_ID, 'reachGoal', 'list', { 'лист получен': { 'гимнастика': p } });
      }
    } catch (e) { /* молчим */ }
    window.print();
  });

  root.querySelectorAll('.gim-sounds button').forEach(function (b, k) {
    b.addEventListener('click', function () { S.i = k; S.more = false; resetPicks(); render(); });
  });
  $('gim-more-btn').addEventListener('click', function () { S.more = !S.more; render(); });

  resetPicks(); render();
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
    return (
        f"<style>{CSS}</style>\n"
        '<div class="widget-box gim" id="gim">\n'
        '<div class="gim-in" id="gim-main">\n'
        '  <p class="gim-title">Выберите звук — комплекс на неделю</p>\n'
        f'  <div class="gim-sounds" role="group" aria-label="Звук">{buttons}</div>\n'
        '  <p class="gim-note" id="gim-note"></p>\n'
        '  <ol class="gim-list" id="gim-week"></ol>\n'
        '  <button type="button" class="gim-more-btn" id="gim-more-btn"></button>\n'
        '  <ol class="gim-list gim-more" id="gim-more" hidden></ol>\n'
        '  <div class="gim-actions">\n'
        '    <button type="button" class="gim-primary" id="gim-start"></button>\n'
        '    <button type="button" id="gim-print-btn">Лист домой на неделю</button>\n'
        '  </div>\n'
        '  <p class="gim-hint">За один раз — 2–3 упражнения, новое одно (Фомичёва, 1989). '
        'Отметьте, какие делаете сегодня; счёт идёт раз в секунду.</p>\n'
        '</div>\n'
        '<div class="gim-run" id="gim-run" hidden>\n'
        '  <p class="gim-small" id="gim-step"></p>\n'
        '  <h3 id="gim-run-name"></h3>\n'
        '  <p class="gim-child" id="gim-run-child"></p>\n'
        '  <p id="gim-run-dose"></p>\n'
        '  <div class="gim-count" id="gim-count" aria-live="polite">0</div>\n'
        '  <div class="gim-run-btns">\n'
        '    <button type="button" id="gim-pause">Пауза</button>\n'
        '    <button type="button" class="gim-primary" id="gim-next">Дальше →</button>\n'
        '    <button type="button" id="gim-stop">Закончить</button>\n'
        '  </div>\n'
        '</div>\n'
        f'<script type="application/json" id="gim-data">{blob}</script>\n'
        "</div>\n"
        '<div id="gim-print"></div>\n'
        f"<script>{JS}</script>"
    )
