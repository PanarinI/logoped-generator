#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Букварикс — частотность Яндекс-Вордстата по посевам (бесплатный API, ключ `free`).

Запуск:  python3 -I tools/bukvarix.py <папка-замера>

В папке замера лежит `seeds.json`:
    [{"id": "chistogovorki", "idea": "Чистоговорки на звук", "seeds": ["чистоговорки"]}, ...]

Пишет туда же:
    raw/<id>__<n>.csv  — ответ API как есть (повторный запуск берёт его, сеть не трогает);
    summary.csv        — по строке на посев и по строке «итого» на идею;
    log.md             — что и когда снято, сколько запросов ушло в сеть.

Что меряет и чего НЕ меряет (читать до вывода):
    · регион API — «весь мир», не только РФ (Беларусь, Казахстан, диаспора внутри);
    · точная частотность — фраза в кавычках с «!»: ровно эти слова в этой форме;
    · на посев API отдаёт до 1000 связанных фраз; сумма точных по ним — ГРУБАЯ
      оценка семьи запросов: чистки по смыслу здесь нет, её делает человек;
    · только Яндекс; Google-половина РФ этим прибором не видна.
Прибор и его история — research/site/pribor_rf_2026-08-19.md.
"""
import csv
import datetime
import io
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "http://api.bukvarix.com/v1/keywords/?q={q}&api_key=free&num=1000&format=csv"
PAUSE_S = 3.0  # бережно: API бесплатный и общий


def fetch(seed: str) -> str:
    url = API.format(q=urllib.parse.quote(seed))
    with urllib.request.urlopen(url, timeout=60) as resp:
        return resp.read().decode("utf-8-sig")


def parse(text: str):
    """Ответ — CSV через «;»: фраза · слов · символов · широкая · точная."""
    rows = []
    reader = csv.reader(io.StringIO(text.lstrip("﻿")), delimiter=";")
    next(reader, None)  # шапка
    for rec in reader:
        if len(rec) < 5:
            continue
        try:
            rows.append((rec[0].strip(), int(rec[3]), int(rec[4])))
        except ValueError:
            continue
    return rows


def main() -> None:
    folder = pathlib.Path(sys.argv[1])
    ideas = json.loads((folder / "seeds.json").read_text(encoding="utf-8"))
    raw_dir = folder / "raw"
    raw_dir.mkdir(exist_ok=True)

    calls = 0
    limited = False  # API ответил 429 — до конца запуска в сеть больше не ходим
    missing = []
    lines = []
    log = [f"# Замер Букварикса — {datetime.date.today().isoformat()}", "",
           f"Запрос: `{API.format(q='<посев>')}` · пауза {PAUSE_S} с · регион «весь мир».", ""]

    for idea in ideas:
        union = {}
        for n, seed in enumerate(idea["seeds"], 1):
            path = raw_dir / f"{idea['id']}__{n}.csv"
            if path.exists():
                text = path.read_text(encoding="utf-8")
            elif limited:
                missing.append(seed)
                continue
            else:
                try:
                    text = fetch(seed)
                except urllib.error.HTTPError as err:
                    if err.code != 429:
                        raise
                    # Бесплатный ключ упёрся в предел частоты. Не долбим: остаток —
                    # следующим запуском, готовое уже лежит в raw/.
                    limited = True
                    missing.append(seed)
                    continue
                calls += 1
                path.write_text(text, encoding="utf-8")
                time.sleep(PAUSE_S)
            rows = parse(text)
            own = next(((w, e) for k, w, e in rows if k == seed), (None, None))
            total = sum(e for _, _, e in rows)
            top = sorted(rows, key=lambda r: -r[2])[:10]
            for k, w, e in rows:
                union[k] = e
            lines.append({
                "idea_id": idea["id"], "idea": idea["idea"], "seed": seed,
                "rows": len(rows), "seed_wide": own[0], "seed_exact": own[1],
                "sum_exact": total,
                "top_exact": " | ".join(f"{k} — {e}" for k, _, e in top),
            })
            log.append(f"- `{seed}` ({idea['id']}): фраз {len(rows)}, Σ точных {total}, "
                       f"сам посев {own[1]} точных / {own[0]} широкая")
        snyato = [s for s in idea["seeds"] if s not in missing]
        lines.append({
            "idea_id": idea["id"], "idea": idea["idea"],
            # «Нет данных» — не ноль: идея без снятых посевов не получает суммы.
            "seed": ("ИТОГО по идее (фразы без повторов)" if snyato
                     else "ИТОГО — не снято (429)"),
            "rows": len(union) if snyato else "", "seed_wide": "", "seed_exact": "",
            "sum_exact": sum(union.values()) if snyato else "", "top_exact": "",
        })

    with open(folder / "summary.csv", "w", encoding="utf-8", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(lines[0].keys()))
        wr.writeheader()
        wr.writerows(lines)
    log += ["", f"Запросов в сеть за этот запуск: {calls} (остальное взято из raw/)."]
    if missing:
        log += [f"⬜ Не снято (API ответил 429 — предел частоты бесплатного ключа): "
                + ", ".join(f"`{s}`" for s in missing) + ". Повторный запуск доснимет только их."]
    (folder / "log.md").write_text("\n".join(log) + "\n", encoding="utf-8")
    print(f"готово: {len(lines)} строк в summary.csv, запросов в сеть {calls}")


if __name__ == "__main__":
    main()
