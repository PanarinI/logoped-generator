# -*- coding: utf-8 -*-
"""Сборка verbs_ch/verbs_ts и adjectives_ch из сверки двух разборов (2026-11-23).

    python3 research/razbor_ch_ts_2026-11-23/sobrat_glagoly_prilagatelnye.py

Глагол берётся, только если ОБА разбора дали ту же форму 3-го лица с тем же ударением
и несовершенным видом (закон 7: разошлись — молчим). Класс подлежащего — пересечение
двух разборов, и ещё снимается там, где предложение «Тут … …» вышло бы обрывом или
бессмыслицей (см. NO_SUBJECT). Транскрипции и `other_correctable` — у движка (бриф §11).

Прилагательные [ч] не размечались заново: все шесть уже лежат выверенными записями в
словарях [р], [р'], [л] — берём их оттуда. У [ц] ни одного прилагательного из таблицы
сочетаемости нет (`combinability.json`), файла нет.
"""
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SL = os.path.normpath(os.path.join(HERE, "..", "..", "logoped_slovar"))
sys.path.insert(0, SL)
import phonetics as P  # noqa: E402

NO_SUBJECT = {
    "ч": {"прячет": "без дополнения обрыв: «Тут мальчик прячет.»",
          "начинает": "без дополнения обрыв", "получает": "без дополнения обрыв",
          "качает": "без дополнения обрыв", "мочит": "без дополнения обрыв",
          "точит": "без дополнения обрыв", "пачкает": "без дополнения обрыв",
          "чинит": "без дополнения обрыв: «Дома дочь чинит.» (поймано на листе 11-23)",
          "учит": "без дополнения обрыв: «Тут мальчик учит.»",
          "мычит": "звук одного вида: класс «звери» дал бы «Тут белочка мычит»",
          "рычит": "звук не всех зверей: «Тут белочка рычит»", "урчит": "звук одного вида",
          "мурлычет": "звук одного вида (кошка)",
          "чирикает": "звук не всех птиц: «Тут чайка чирикает»"},
    "ц": {"целует": "без дополнения обрыв", "цепляется": "без «за что» обрыв",
          "цокает": "звук одного вида (лошадь)"},
}
_T = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
              ["a", "b", "v", "g", "d", "e", "yo", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p",
               "r", "s", "t", "u", "f", "kh", "ts", "ch", "sh", "shch", "", "y", "", "e", "yu", "ya"]))


def translit(w):
    return "".join(_T.get(c, c) for c in w)


def write_jsonl(name, rows):
    with io.open(os.path.join(SL, name), "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def verbs():
    mine = json.load(open(os.path.join(HERE, "razbor1_glagoly_prilagatelnye.json"), encoding="utf-8"))
    for snd, key, rf, out, pre in (("ч", "verbs_ch", "razbor2_ch.json", "verbs_ch.jsonl", "ch_v_"),
                                   ("ц", "verbs_ts", "razbor2_ts.json", "verbs_ts.jsonl", "ts_v_")):
        theirs = {v["form_3sg"]: v for v in
                  json.load(open(os.path.join(HERE, rf), encoding="utf-8"))["verbs"]}
        recs, log = [], []
        for inf, st, f3, st3, trans, subj, cat, fam, age in mine[key]:
            t = theirs.get(f3)
            if not t:
                log.append(f"{f3}: только в первом разборе — не берём")
                continue
            if t["form_3sg_stress"] != st3 or t["aspect"] != "несов" or t["word"] != inf:
                log.append(f"{f3}: разошлись ({st3} / {t['form_3sg_stress']}) — молчим")
                continue
            subj2 = [c for c in subj if c in t["subject_classes"]]
            note = ""
            if f3 in NO_SUBJECT[snd]:
                note = "подлежащее не размечено: " + NO_SUBJECT[snd][f3]
                subj2 = []
            a_inf, a3 = P.analyze(inf, st), P.analyze(f3, st3)
            assert snd in a3.transcription, f3
            recs.append({
                "id": pre + translit(inf), "word": inf, "pos": "verb",
                "transcription": a_inf.transcription, "stress_syllable": st,
                "form_3sg": f3, "form_3sg_transcription": a3.transcription,
                "form_3sg_stress": st3, "sound_in_infinitive": snd in a_inf.transcription,
                "transitive": trans, "semantic_category": cat,
                "familiarity": min(fam, t["familiarity"]), "age_min": max(age, t["age_min"]),
                "sensitive": False,
                "other_correctable": sorted(set(a3.problem_phonemes) - {snd}),
                "note": note, "aspect": "несов", "form_3sg_tense": "настоящее",
                "subject_classes": subj2,
            })
        write_jsonl(out, recs)
        used = [r["form_3sg"] for r in recs if r["subject_classes"]]
        print(out, len(recs), "в предложениях:", len(used), ", ".join(used))
        for line in log:
            print("   ", line)


def adjectives_ch():
    order = ["чёрный", "горячий", "молочный", "яблочный", "клубничный", "кирпичный"]
    got = {}
    for fn in sorted(glob.glob(os.path.join(SL, "adjectives_*.jsonl"))):
        if fn.endswith("adjectives_ch.jsonl"):
            continue
        for line in open(fn, encoding="utf-8"):
            if not line.strip():
                continue
            a = json.loads(line)
            if a["word"] in order and a["word"] not in got:
                a = dict(a)
                a["id"] = "ch_" + a["id"]
                forms = ((a["word"], a["stress_syllable"]), (a["form_f"], a["stress_syllable"]),
                         (a["form_n"], a["stress_syllable"]))
                oc = set()
                for w, s in forms:
                    oc |= set(P.analyze(w, s).problem_phonemes)
                a["other_correctable"] = sorted(oc - {"ч"})
                got[a["word"]] = a
    write_jsonl("adjectives_ch.jsonl", [got[w] for w in order])
    print("adjectives_ch.jsonl", len(order))


if __name__ == "__main__":
    verbs()
    adjectives_ch()
