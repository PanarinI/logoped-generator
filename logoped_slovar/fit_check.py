# -*- coding: utf-8 -*-
"""
fit_check.py — доказательство, что лист влезает в ОДИН А4.

Утверждение «один лист» существует только как строка прогона, а не как
обещание вёрстки. Проверяется двумя независимыми способами:

  1. МОДЕЛЬ  — sheet.estimate_heights() считает высоту блоков в мм.
  2. ФАКТ    — Chrome печатает HTML в PDF (@page A4) и мы считаем страницы.

Прогон: python3 fit_check.py
Требуется Google Chrome (печать в PDF); без него отработает только модель.

Что проверяется:
  · 4 типа слоговой позиции × 4 объёма словаря (12/16/20/24) = 16 листов
  · пустой профиль (максимум словаря) и тяжёлый профиль (минимум словаря)
  · заведомый перегруз — с лестницей сокращений (должен дать 1 страницу)
    и БЕЗ неё (контроль: должен дать 2 — иначе тест ничего не доказывает)
  · калибровка: модель против факта поблочно (расхождение должно быть ≤ 3 мм)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import sheet  # noqa: E402

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
]
CHROME = next((p for p in CHROME_CANDIDATES if os.path.exists(p)), None)
TMP = tempfile.mkdtemp(prefix="logoped_fit_")

MEASURE_JS = """
<script>(function(){
  var MM=96/25.4, out=[];
  function h(el){ if(!el) return 0;
    var r=el.getBoundingClientRect(), cs=getComputedStyle(el);
    return (r.height+parseFloat(cs.marginTop)+parseFloat(cs.marginBottom))/MM; }
  var names={'1':'articulation','2':'isolated','3':'syllables','4':'words',
             '5':'game','6':'sentences','7':'chant'};
  out.push(['_header', h(document.querySelector('.doc'))]);
  document.querySelectorAll('.block').forEach(function(b){
    var n=b.querySelector('.bnum');
    out.push([names[n?n.textContent.trim():'?']||'?', h(b)]); });
  out.push(['_footer', h(document.querySelector('.foot'))]);
  var p=document.createElement('pre'); p.id='MEASURE';
  p.textContent=JSON.stringify(out); document.body.appendChild(p);
})();</script>
"""


def _chrome(args, timeout=180):
    return subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-sandbox",
                           "--virtual-time-budget=3000"] + args,
                          capture_output=True, text=True, timeout=timeout)


def pdf_pages(path: str) -> int:
    data = open(path, "rb").read()
    counts = re.findall(rb"/Type\s*/Pages[^>]*?/Count\s+(\d+)", data)
    if counts:
        return max(int(x) for x in counts)
    return len(re.findall(rb"/Type\s*/Page[^s]", data))


def print_pages(name: str, doc: str) -> int:
    h = os.path.join(TMP, f"{name}.html")
    pdf = os.path.join(TMP, f"{name}.pdf")
    open(h, "w", encoding="utf-8").write(doc)
    _chrome(["--no-pdf-header-footer", f"--print-to-pdf={pdf}", "file://" + h])
    return pdf_pages(pdf)


def measure_blocks(doc: str):
    h = os.path.join(TMP, "measure.html")
    open(h, "w", encoding="utf-8").write(doc.replace("</body>", MEASURE_JS + "</body>"))
    dom = _chrome(["--dump-dom", "file://" + h]).stdout
    m = re.search(r'<pre id="MEASURE">(.*?)</pre>', dom, re.S)
    if not m:
        return {}
    import html as _h
    return dict(json.loads(_h.unescape(m.group(1))))


def main() -> int:
    meta = {"child_name": "", "sound": "р", "sheet_no": "1",
            "week_from": "", "week_to": ""}
    cases = []
    # основной путь — методический движок content.py через мост compose()
    for typ in ("direct", "reverse", "intervocal", "cluster", "cluster_coda"):
        for nw in (12, 16, 20, 24):
            try:
                c, _ = sheet.compose("р", typ, "л,ш,ж", n_words=nw)
                cases.append((f"{typ}-{nw}", c, {}))
            except SystemExit as exc:
                print(f"--  {typ}/{nw}: {exc}")
    for prof, tag in (("", "профиль-пуст"), ("шипящие,свистящие,л", "профиль-тяжёлый"),
                      ("л,ш,ж,с,з,ц", "профиль-крайний")):
        c, _ = sheet.compose("р", "direct", prof, n_words=24, n_sentences=10)
        cases.append((f"{tag}-24", c, {}))

    # черновой сборщик вёрстки — тоже должен влезать
    c, _ = sheet.build_content("р", "direct", "л,ш,ж", n_words=16, n_syl_rows=5)
    cases.append(("стопгап-16", c, {}))

    # заведомый перегруз + контроль без лестницы сокращений
    over, _ = sheet.build_content("р", "direct", "", n_words=24, n_syl_rows=6)
    over["sentences"]["items"] = (over["sentences"]["items"] * 2)[:10]
    cases.append(("перегруз", over, {}))
    cases.append(("перегруз-БЕЗ-fit", over, {"no_fit": True}))

    # Лист логопеда — ОТДЕЛЬНЫЙ лист, а не тот же самый: у него нет шапки,
    # подвала и подсказок разминки. Раз обвязка другая, доказывать «один А4»
    # для него надо своим прогоном (08-12: до этого его резали по домашней
    # мерке, и он терял материал там, где место было).
    for name, content, opt in list(cases):
        if not opt.get("no_fit"):
            cases.append((f"{name}·логопед", content, {"audience": "lesson"}))

    if not CHROME:
        print("Chrome не найден — только модель, без печати в PDF")

    bad = 0
    print(f"{'случай':26} {'модель, мм':>11} {'страниц':>8}")
    for name, content, opt in cases:
        doc, warns = sheet.render_sheet_ex(content, meta, options=opt)
        who = opt.get("audience", "home")
        shaped = sheet.for_audience(content, who)
        fitted = shaped if opt.get("no_fit") else sheet.fit(shaped, sheet.CONTENT_H, who)[0]
        est = sheet.total_height(fitted, who)
        pages = print_pages(name, doc) if CHROME else 0
        expect = 2 if name.endswith("БЕЗ-fit") else 1
        ok = (pages == expect) if CHROME else (est <= sheet.CONTENT_H or opt.get("no_fit"))
        bad += (not ok)
        print(f"{'OK ' if ok else '!! '}{name:23} {est:11.1f} {pages:8}")
        for w in warns:
            if w.startswith(("НЕ ВЛЕЗ", "не влезало")):
                print(f"      ↳ {w}")

    # калибровка модели по факту — по КАЖДОМУ адресату отдельно: у листа
    # логопеда своя обвязка, и модель должна попадать в неё, а не в домашнюю
    if CHROME:
        for who in ("home", "lesson"):
            print(f"\nкалибровка, адресат «{who}» (модель против рендера), мм:")
            c, _ = sheet.compose("р", "direct", "л,ш,ж", n_words=16)
            doc, _ = sheet.render_sheet_ex(c, meta, options={"no_fit": True,
                                                            "show_warnings": False,
                                                            "audience": who})
            fact = measure_blocks(doc)
            model = sheet.estimate_heights(sheet.for_audience(c, who), who)
            for k in ["_header", "articulation", "isolated", "syllables", "words",
                      "game", "sentences", "chant", "_footer"]:
                if k in model or k in fact:
                    d = fact.get(k, 0) - model.get(k, 0)
                    flag = "" if abs(d) <= 3 else "  ← расхождение > 3 мм"
                    bad += abs(d) > 3
                    print(f"  {k:14} модель {model.get(k, 0):6.1f}  факт "
                          f"{fact.get(k, 0):6.1f}  дельта {d:+5.1f}{flag}")

    print(f"\nитог: провалов {bad}" + ("" if bad else "  — ВСЁ ЗЕЛЁНОЕ"))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
