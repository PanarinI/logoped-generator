# -*- coding: utf-8 -*-
"""Виджет «Артикуляционная гимнастика» — первая страница-кластер (2026-11-23).

Зачем свой виджет, а не главный генератор в рамке. Канон Site Builders 2.0: кластер —
«примерно одна функция, названная разными словами», и при смене кластера меняется сам
виджет (`app-studio/knowledge-base/site-builders-2/01-vstrecha-01.md` §7); у страницы
кластера свой виджет первым экраном (`03-vstrecha-03.md` §6.1). Встроен прямо в
страницу, а не рамкой: содержимое iframe поисковик не индексирует.

Устройство — с 24.11 (вечер), по образцу Brain Breaks в funclass. Первая версия
выкладывала комплекс карточками в столбик, и автор сказал: «пока не выглядит как
виджет… огромный, промотка». Теперь один экран: слева звук и список упражнений,
справа ДОСКА с одним упражнением занятия, внизу «▶ Начать на экране» (главное
действие) и «Лист домой». Почему главное — экран: замеры спроса
(`research/site/scenarii_klasterov_2026-11-24.md` §2) показывают, что ищут не список
(он есть в любой картотеке), а как провести занятие: картинки, игру на экране, сюжет.

В занятии до трёх упражнений. Фомичёва 1989: «не более двух-трёх», и «новым может
быть только одно». Поэтому «другое упражнение» меняет ОДНО — следующим по очереди, а
не кубиком. Так же крутит разминку главный генератор (`gymnastics.json` →
`rotation_note`), и нажатиями проходится весь список. Очередь — набор недели
(`sheet_4`), потом запас (`alternates`); упражнения с реквизитом стоят в конце.
Деления «основные / запас» на экране нет: его придумали мы под четыре клетки листа, а
у Фомичёвой комплекс один (ответ автору 24.11). Лист домой печатает то, что на доске.

Данные — только `logoped_slovar/gymnastics.json` (разбор Фомичёвой 1989 и картотек
практиков, с тирами). Упражнения постановки (`excluded_from_sheet`: Барабанщики,
Моторчик…) сюда не попадают — на автоматизации их не делают.

Ч и Ц. Своих комплексов в файле нет, но источник называет комплексы по ГРУППЕ:
«для свистящих звуков с, з, ц» и «для шипящих звуков ш, ж, ч, щ» (`derivation_note`
у [З] и [Ж]). Поэтому [Ц] берёт комплекс [С], [Ч] — комплекс [Ш], с тем же тиром
«книга», что у [З] и [Ж]. Появятся в файле свои — возьмутся они.

Картинки собирает `tools/gim_kartinki.py`: образ есть у каждого упражнения, лицо — там,
где рисунок совпал с источником. Счёт на экране задаёт только темп «под счёт», раз в
секунду. Сколько делать, говорит дозировка источника над ним; своей «нормы» счётчик не
придумывает (закон 2). Про зеркало прежняя пометка «в источниках этого нет» была
неверна. У Фомичёвой: «Сначала упражнения выполняются в медленном темпе перед
зеркалом», потом зеркало убирают; дома с четырёх лет — тоже перед зеркалом. Это
строки 314 и 1333 копии `research/afrikaty_ch_ts_2026-11-23_syrye/fomicheva_1989.txt`.
На экран и в лист это пока не вынесено: ждёт слова автора.
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
            "obraz": pic(eid, "obraz"),
            "obraz_bw": pic(eid, "obraz-bw"),
            "litso": pic(eid, "litso"),
        }

    def queue(c: Dict[str, Any]) -> List[str]:
        # Очередь «другого упражнения» и порядок списка: набор недели, потом запас;
        # с реквизитом — в конце, как в разминке главного генератора (rotation_note).
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
.gim{padding:var(--s4)}
.gim-in{max-width:56rem;margin:0 auto}
.gim-grid{display:grid;grid-template-columns:15.5rem minmax(0,1fr);gap:var(--s3);align-items:start}
.gim-label{margin:0 0 6px;font-size:.85rem;color:var(--ink-soft)}
.gim-sounds{display:grid;grid-template-columns:repeat(5,1fr);gap:5px}
.gim-sounds button{min-width:0;padding:7px 0;border:1px solid var(--line);border-radius:8px;background:#fff;
  font:inherit;font-size:1.02rem;cursor:pointer;color:var(--ink)}
.gim-sounds button[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:#fff}
.gim-note{margin:8px 0 0;font-size:.82rem;line-height:1.4;color:var(--ink-soft)}
.gim-note:empty,.gim-warn:empty{display:none}
.gim-all{display:block;width:100%;margin:var(--s3) 0 0;padding:8px 10px;border:1px solid var(--line);
  border-radius:8px;background:#fff;font:inherit;font-size:.92rem;cursor:pointer;color:var(--ink);text-align:left}
.gim-list{list-style:none;margin:6px 0 0;padding:0}
.gim-list li{margin:0;border-top:1px solid var(--line)}
.gim-list label{display:flex;gap:8px;align-items:baseline;padding:6px 2px;font-size:.92rem;line-height:1.35;cursor:pointer}
.gim-list small{color:var(--ink-soft)}
.gim-warn{margin:6px 0 0;font-size:.82rem;line-height:1.4;color:#8a5a00}
.gim-board{background:#fff;border:1px solid var(--line);border-radius:12px;padding:var(--s3) var(--s4)}
.gim-top{display:flex;justify-content:space-between;align-items:center;gap:8px;font-size:.85rem;color:var(--ink-soft)}
.gim-other{border:1px solid var(--line);border-radius:20px;background:#fff;font:inherit;font-size:.85rem;
  padding:3px 12px;cursor:pointer;color:var(--ink);white-space:nowrap}
.gim-pics{display:flex;justify-content:center;gap:12px;margin:var(--s2) 0}
.gim-pics img{width:120px;height:120px;object-fit:contain}
.gim-board p{margin:4px 0 0;font-size:.95rem;line-height:1.45}
.gim-board .gim-name{margin:0;font-size:1.3rem;line-height:1.3;font-weight:600}
.gim-child{font-style:italic}
.gim-board .gim-small{font-size:.82rem;color:var(--ink-soft)}
.gim-nav{display:flex;justify-content:space-between;align-items:center;margin-top:var(--s3)}
.gim-nav[hidden]{display:none}
.gim-nav>button{width:44px;height:36px;border:1px solid var(--line);border-radius:8px;background:#fff;
  font:inherit;font-size:1.25rem;line-height:1;cursor:pointer;color:var(--ink)}
.gim-dots{display:flex;gap:2px}
.gim-dots button{position:relative;width:26px;height:26px;padding:0;border:0;background:none;cursor:pointer}
.gim-dots button::after{content:"";position:absolute;left:8px;top:8px;width:10px;height:10px;border-radius:50%;
  background:var(--line)}
.gim-dots button[aria-current="true"]::after{background:var(--ink)}
.gim-actions{display:flex;flex-wrap:wrap;align-items:center;gap:var(--s2);margin-top:var(--s3)}
.gim-hint{margin:0 auto 0 0;font-size:.85rem;color:var(--ink-soft)}
.gim-actions button,.gim-run-btns button{font:inherit;font-size:1rem;padding:10px 18px;border-radius:10px;
  border:1px solid var(--line);background:#fff;cursor:pointer;color:var(--ink)}
.gim-actions .gim-primary,.gim-run-btns .gim-primary{background:var(--accent);border-color:var(--accent);color:#fff}
@media (max-width:720px){
  .gim{padding:var(--s3) var(--s3) var(--s4)}
  .gim-grid{grid-template-columns:minmax(0,1fr)}
  .gim-sounds{grid-template-columns:repeat(7,1fr)}
  .gim-pics img{width:96px;height:96px}
  .gim-hint{flex-basis:100%}
  .gim-actions button{flex:1 1 auto}
}
.gim-run{position:fixed;inset:0;z-index:1000;display:flex;flex-direction:column;align-items:center;
  justify-content:center;padding:4vh 16px;overflow:auto;background:#fff;text-align:center}
.gim-run[hidden]{display:none}
.gim-run:focus{outline:none}
.gim-run .gim-step{margin:0;font-size:.95rem;color:var(--ink-soft)}
.gim-run .gim-pics img{width:min(32vh,260px);height:min(32vh,260px);max-width:44vw}
.gim-run .gim-run-name{margin:var(--s2) 0 0;font-size:clamp(1.6rem,4.5vh,2.4rem);line-height:1.2;font-weight:600}
.gim-run p{margin:var(--s2) 0 0;max-width:40rem;font-size:clamp(1.05rem,2.6vh,1.35rem);line-height:1.4}
.gim-count{margin:var(--s3) 0;font-size:clamp(3.5rem,14vh,7rem);font-weight:700;line-height:1;color:var(--accent);
  font-variant-numeric:tabular-nums}
.gim-run-btns{display:flex;justify-content:center;flex-wrap:wrap;gap:var(--s2)}
.gim-run .gim-keys{font-size:.82rem;color:var(--ink-soft)}
@media (hover:none){.gim-run .gim-keys{display:none}}
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
  var root = document.getElementById('gim');
  var $ = function (id) { return document.getElementById(id); };
  // Фомичёва 1989: «Не следует предлагать детям более двух-трех упражнений».
  var MAX = 3;
  var S = { i: 0, ses: [], k: 0, open: false };
  var esc = function (t) {
    return String(t || '').replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  };
  var cur = function () { return D.sounds[S.i]; };
  var at = function (j) { return cur().ex[j]; };

  function warn(t) { $('gim-warn').textContent = t || ''; }
  function reset() {
    S.ses = []; S.k = 0; warn('');
    for (var j = 0; j < cur().ex.length && j < MAX; j++) S.ses.push(j);
  }

  // Образ — что напоминает упражнение; лицо — как делать. Лицо есть не у всех:
  // только там, где рисунок совпал с описанием источника (tools/gim_kartinki.py).
  function picsHtml(c, eager) {
    var lz = eager ? '' : ' loading="lazy"', out = '';
    if (c.obraz) out += '<img src="' + esc(c.obraz) + '" alt="' + esc(c.name) + '"' + lz + '>';
    if (c.litso) out += '<img src="' + esc(c.litso) + '" alt="Как делать: ' + esc(c.name) + '"' + lz + '>';
    return out ? '<div class="gim-pics">' + out + '</div>' : '';
  }
  function posText(k, n, c) { return 'Упражнение ' + (k + 1) + ' из ' + n + (c.kind ? ' · ' + c.kind : ''); }

  function render() {
    var s = cur(), n = S.ses.length, c = at(S.ses[S.k]);
    root.querySelectorAll('.gim-sounds button').forEach(function (b, k) {
      b.setAttribute('aria-pressed', k === S.i ? 'true' : 'false');
    });
    $('gim-note').textContent = s.note || '';
    $('gim-pos').textContent = posText(S.k, n, c);
    $('gim-pics').innerHTML = picsHtml(c);
    $('gim-name').textContent = c.name;
    $('gim-child').textContent = c.child || '';
    $('gim-how').textContent = c.how || '';
    $('gim-dose').innerHTML = '<b>Сколько:</b> ' + esc(c.dose) +
      (c.props ? '. <b>Понадобится:</b> ' + esc(c.props) : '');
    $('gim-why').textContent = c.why ? 'Зачем: ' + c.why : '';
    $('gim-src').textContent = 'Источник: ' + c.src;
    $('gim-src').title = c.src_full;
    $('gim-dots').innerHTML = S.ses.map(function (_, k) {
      return '<button type="button" data-k="' + k + '" aria-label="Упражнение ' + (k + 1) + '"' +
        (k === S.k ? ' aria-current="true"' : '') + '></button>';
    }).join('');
    $('gim-nav').hidden = n < 2;
    // Закон 14: заменить не на что — кнопки нет.
    $('gim-other').hidden = s.ex.length <= n;
    $('gim-all').setAttribute('aria-expanded', S.open ? 'true' : 'false');
    $('gim-all').textContent = 'Все упражнения (' + s.ex.length + ') ' + (S.open ? '▴' : '▾');
    $('gim-list').hidden = !S.open;
    $('gim-list').innerHTML = !S.open ? '' : s.ex.map(function (e, j) {
      return '<li><label><input type="checkbox" data-j="' + j + '"' +
        (S.ses.indexOf(j) >= 0 ? ' checked' : '') + '><span>' + esc(e.name) +
        (e.props ? ' <small>· ' + esc(e.props) + '</small>' : '') + '</span></label></li>';
    }).join('');
  }

  root.querySelectorAll('.gim-sounds button').forEach(function (b, k) {
    b.addEventListener('click', function () { S.i = k; reset(); render(); });
  });
  $('gim-prev').addEventListener('click', function () {
    S.k = (S.k + S.ses.length - 1) % S.ses.length; render();
  });
  $('gim-fwd').addEventListener('click', function () { S.k = (S.k + 1) % S.ses.length; render(); });
  $('gim-dots').addEventListener('click', function (ev) {
    var b = ev.target.closest('button');
    if (b) { S.k = +b.dataset.k; render(); }
  });
  // «Другое упражнение» — следующее по очереди, которого нет в занятии: нажатиями
  // проходится весь список, а не кубик (см. шапку модуля).
  $('gim-other').addEventListener('click', function () {
    var n = cur().ex.length, j = S.ses[S.k];
    for (var step = 1; step < n; step++) {
      var c = (j + step) % n;
      if (S.ses.indexOf(c) < 0) { S.ses[S.k] = c; break; }
    }
    warn(''); render();
  });
  $('gim-all').addEventListener('click', function () { S.open = !S.open; render(); });
  $('gim-list').addEventListener('change', function (ev) {
    var t = ev.target;
    if (!t.dataset || t.dataset.j === undefined) return;
    var j = +t.dataset.j, pos = S.ses.indexOf(j);
    if (t.checked && pos < 0) {
      if (S.ses.length >= MAX) {
        t.checked = false;
        warn('В занятии не больше трёх: у Фомичёвой «не более двух-трёх упражнений» за раз. ' +
             'Снимите галочку с другого.');
        return;
      }
      S.ses.push(j); S.k = S.ses.length - 1;
    } else if (!t.checked && pos >= 0) {
      if (S.ses.length <= 1) { t.checked = true; warn('Одно упражнение в занятии остаётся всегда.'); return; }
      S.ses.splice(pos, 1);
      if (S.k >= S.ses.length) S.k = S.ses.length - 1;
    }
    warn(''); render();
  });

  // ── занятие на экране ─────────────────────────────────────────────────
  var R = { k: 0, n: 0, timer: null };
  var run = $('gim-run');
  function tick() { R.n += 1; $('gim-count').textContent = R.n; }
  function showRun() {
    var c = at(S.ses[R.k]);
    $('gim-step').textContent = posText(R.k, S.ses.length, c);
    $('gim-run-pics').innerHTML = picsHtml(c, true);
    $('gim-run-name').textContent = c.name;
    $('gim-run-child').textContent = c.child || '';
    $('gim-run-dose').textContent = 'Сколько: ' + c.dose + (c.props ? '. Понадобится: ' + c.props : '');
    R.n = 0; $('gim-count').textContent = '0';
    clearInterval(R.timer); R.timer = setInterval(tick, 1000);
    $('gim-pause').textContent = 'Пауза';
    $('gim-next').textContent = R.k + 1 < S.ses.length ? 'Дальше →' : 'Готово';
  }
  function openRun() {
    R.k = 0; run.hidden = false;
    document.documentElement.classList.add('gim-lock');
    showRun(); run.focus();
  }
  function stopRun() {
    clearInterval(R.timer); R.timer = null;
    run.hidden = true;
    document.documentElement.classList.remove('gim-lock');
    $('gim-start').focus();
  }
  function pause() {
    if (R.timer) { clearInterval(R.timer); R.timer = null; $('gim-pause').textContent = 'Продолжить'; }
    else { R.timer = setInterval(tick, 1000); $('gim-pause').textContent = 'Пауза'; }
  }
  function next() { if (R.k + 1 < S.ses.length) { R.k += 1; showRun(); } else { stopRun(); } }
  $('gim-start').addEventListener('click', openRun);
  // После щелчка фокус возвращается на панель: иначе пробел нажимал бы ту же
  // кнопку ещё раз, а не ставил паузу.
  $('gim-pause').addEventListener('click', function () { pause(); run.focus(); });
  $('gim-next').addEventListener('click', function () { next(); if (!run.hidden) run.focus(); });
  $('gim-stop').addEventListener('click', stopRun);
  document.addEventListener('keydown', function (ev) {
    if (run.hidden) return;
    if (ev.key === 'Escape') { ev.preventDefault(); stopRun(); }
    else if (ev.key === 'ArrowRight') { ev.preventDefault(); next(); }
    else if ((ev.key === ' ' || ev.key === 'Spacebar') && ev.target === run) { ev.preventDefault(); pause(); }
  });

  // ── лист домой на неделю: то, что на доске ────────────────────────────
  $('gim-print-btn').addEventListener('click', function () {
    var s = cur(), list = S.ses.map(at), days = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
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
    return (
        f"<style>{CSS}</style>\n"
        '<div class="widget-box gim" id="gim">\n'
        '<div class="gim-in">\n'
        ' <div class="gim-grid">\n'
        '  <div class="gim-side">\n'
        '   <p class="gim-label">Звук</p>\n'
        f'   <div class="gim-sounds" role="group" aria-label="Звук">{buttons}</div>\n'
        '   <p class="gim-note" id="gim-note"></p>\n'
        '   <button type="button" class="gim-all" id="gim-all" aria-expanded="false" '
        'aria-controls="gim-list" title="Все упражнения для этого звука: отметьте, какие делать '
        'сегодня, — до трёх"></button>\n'
        '   <ul class="gim-list" id="gim-list" hidden></ul>\n'
        '   <p class="gim-warn" id="gim-warn" role="status"></p>\n'
        '  </div>\n'
        '  <div class="gim-board">\n'
        '   <div class="gim-top"><span id="gim-pos" aria-live="polite"></span>'
        '<button type="button" class="gim-other" id="gim-other" title="Заменить это упражнение '
        'следующим из списка. За один раз новое — одно (Фомичёва, 1989)">↻ другое упражнение</button></div>\n'
        '   <div id="gim-pics"></div>\n'
        '   <p class="gim-name" id="gim-name"></p>\n'
        '   <p class="gim-child" id="gim-child"></p>\n'
        '   <p id="gim-how"></p>\n'
        '   <p id="gim-dose"></p>\n'
        '   <p class="gim-small" id="gim-why"></p>\n'
        '   <p class="gim-small" id="gim-src"></p>\n'
        '   <div class="gim-nav" id="gim-nav">'
        '<button type="button" id="gim-prev" aria-label="Предыдущее упражнение">‹</button>'
        '<div class="gim-dots" id="gim-dots"></div>'
        '<button type="button" id="gim-fwd" aria-label="Следующее упражнение">›</button></div>\n'
        '  </div>\n'
        ' </div>\n'
        ' <div class="gim-actions">\n'
        '  <p class="gim-hint">За один раз — 2–3 упражнения, новое из них одно (Фомичёва, 1989).</p>\n'
        '  <button type="button" id="gim-print-btn" title="Печать для родителя: упражнения с доски, '
        'правила и таблица отметок на неделю">Лист домой</button>\n'
        '  <button type="button" class="gim-primary" id="gim-start" title="Упражнения по одному, '
        'крупно, со счётом — показать ребёнку на экране">▶ Начать на экране</button>\n'
        ' </div>\n'
        '</div>\n'
        '<div class="gim-run" id="gim-run" role="dialog" aria-modal="true" '
        'aria-label="Занятие на экране" tabindex="-1" hidden>\n'
        '  <p class="gim-step" id="gim-step"></p>\n'
        '  <div id="gim-run-pics"></div>\n'
        '  <p class="gim-run-name" id="gim-run-name"></p>\n'
        '  <p class="gim-child" id="gim-run-child"></p>\n'
        '  <p id="gim-run-dose"></p>\n'
        '  <div class="gim-count" id="gim-count">0</div>\n'
        '  <div class="gim-run-btns">\n'
        '    <button type="button" id="gim-pause">Пауза</button>\n'
        '    <button type="button" class="gim-primary" id="gim-next">Дальше →</button>\n'
        '    <button type="button" id="gim-stop">Закончить</button>\n'
        '  </div>\n'
        '  <p class="gim-keys">Пробел — пауза · → — дальше · Esc — закончить</p>\n'
        '</div>\n'
        f'<script type="application/json" id="gim-data">{blob}</script>\n'
        "</div>\n"
        '<div id="gim-print"></div>\n'
        f"<script>{JS}</script>"
    )
