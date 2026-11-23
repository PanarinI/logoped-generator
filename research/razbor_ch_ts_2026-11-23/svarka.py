# -*- coding: utf-8 -*-
"""Сверка двух независимых разборов словарей [ч] и [ц] (2026-11-23).

Разбор 1 — Клод: `logoped_slovar/words_ch.jsonl`, `words_ts.jsonl` (из gen_words_*.py),
`razbor1_formy.json`, `razbor1_glagoly_prilagatelnye.json`.
Разбор 2 — отдельный составитель вслепую, по одному списку слов: `razbor2_ch.json`, `razbor2_ts.json`.

Печатает расхождения по полям. Правило проекта (CLAUDE.md, закон 7): при расхождении
в ФОРМЕ — молчать, а не выбирать убедительное. Решения по каждому расхождению —
в `words_ch_report.md` / `words_ts_report.md`.

    python3 research/razbor_ch_ts_2026-11-23/svarka.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
SL = os.path.join(HERE, "..", "..", "logoped_slovar")


def load_jsonl(name):
    return {r["word"]: r for r in (json.loads(l) for l in open(os.path.join(SL, name), encoding="utf-8") if l.strip())}


def main():
    f1 = json.load(open(os.path.join(HERE, "razbor1_formy.json"), encoding="utf-8"))
    for sound, wfile, r2file in (("ч", "words_ch.jsonl", "razbor2_ch.json"),
                                 ("ц", "words_ts.jsonl", "razbor2_ts.json")):
        mine = load_jsonl(wfile)
        theirs = {r["word"]: r for r in json.load(open(os.path.join(HERE, r2file), encoding="utf-8"))["part_a"]}
        print(f"\n══════ [{sound}] — {len(mine)} слов у разбора 1, {len(theirs)} у разбора 2 ══════")
        missing = sorted(set(mine) - set(theirs))
        if missing:
            print("  разбор 2 не разметил:", ", ".join(missing))
        rej = [(w, r["verdict"]) for w, r in theirs.items() if r.get("verdict") != "ok"]
        print(f"\n  ОТБРАКОВАНО разбором 2: {len(rej)}")
        for w, v in rej:
            print(f"    {w}: {v}")
        objective = []
        subjective = []
        for w, m in mine.items():
            t = theirs.get(w)
            if not t:
                continue
            pairs = [("stress", m["stress_syllable"], t.get("stress")),
                     ("gender", m["gender"], t.get("gender")),
                     ("plural", m["plural"], t.get("plural"))]
            for fld, a, b in pairs:
                if a != b:
                    objective.append((w, fld, a, b))
            pl_st = f1["plural_stress"].get(m["plural"]) if m["plural"] else None
            if m["plural"] and t.get("plural") == m["plural"] and pl_st != t.get("plural_stress"):
                objective.append((w, "plural_stress", pl_st, t.get("plural_stress")))
            cnt1 = w not in f1["countable_false"]
            if cnt1 != bool(t.get("countable")):
                objective.append((w, "countable", cnt1, t.get("countable")))
            if sound == "ч":
                d1 = f1["diminutive_ch"].get(w, "-")
                d2 = t.get("diminutive") or "-"
                if d1 != d2:
                    objective.append((w, "diminutive", d1, d2))
            else:
                g1 = f1["gen_ts"].get(w, ("-", "-"))
                g2 = (t.get("gen_sg") or "-", t.get("gen_pl") or "-")
                if tuple(g1) != g2:
                    objective.append((w, "gen_sg/gen_pl", "/".join(g1), "/".join(g2)))
            for fld, a, b in (("familiarity", m["familiarity"], t.get("familiarity")),
                              ("age_min", m["age_min"], t.get("age_min")),
                              ("ambiguous", m["ambiguous"], t.get("ambiguous")),
                              ("category", m["semantic_category"], t.get("category"))):
                if a != b:
                    subjective.append((w, fld, a, b))
        print(f"\n  ФОРМА расходится (молчать): {len(objective)}")
        for row in objective:
            print("    %-12s %-14s разбор1=%-22s разбор2=%s" % row)
        print(f"\n  ОЦЕНКА расходится (берём осторожное): {len(subjective)}")
        for row in subjective:
            print("    %-12s %-12s разбор1=%-18s разбор2=%s" % row)


if __name__ == "__main__":
    main()
