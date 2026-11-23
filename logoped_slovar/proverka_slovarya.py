# -*- coding: utf-8 -*-
"""Сверка словаря движком — бриф §8, одна команда на любой звук.

    python3 logoped_slovar/proverka_slovarya.py ч words_ch.jsonl
    python3 logoped_slovar/proverka_slovarya.py ц words_ts.jsonl

Что печатает:
  1. расхождения РУЧНОЙ транскрипции с движком (после снятия редукции, которую рука
     по брифу не пишет) и расхождения набора корригируемых звуков;
  2. слова, где движок НЕ нашёл целевой звук (ворота 1 брифа);
  3. мёртвые слова — те, что лист этого звука не пустит никогда, при пустом профиле
     (`content.banned_phonemes`): им не место в картотеке;
  4. сколько слов отвечает каждому типу слога (`content.occurrence_kind`) — это и есть
     ступени, которые логопед увидит кнопками; канон блока [4] — 12 слов (стечения — 7).

Ничего не пишет на диск: это проверка, а не сборка.
"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import content as C  # noqa: E402
import phonetics as P  # noqa: E402

# Редукция: рука её не пишет (бриф §3), движок пишет. Сравниваем без гласных.
_VOW = set("аоуыэиеёюя")


def consonant_skeleton(tr: str) -> str:
    return "".join(ch for ch in tr if ch not in _VOW)


def main(sound: str, path: str) -> int:
    if not os.path.isabs(path):
        path = os.path.join(HERE, path)
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    banned0 = C.banned_phonemes(sound, ())
    print(f"[{sound}] {os.path.basename(path)}: {len(rows)} слов; "
          f"на листе всегда запрещены: {' '.join(sorted(banned0))}")

    tr_diff, oc_diff, no_target, dead = [], [], [], []
    kinds = collections.Counter()
    kind_words = collections.defaultdict(list)
    no_kind = []
    for r in rows:
        a = P.analyze(r["word"], r["stress_syllable"])
        if consonant_skeleton(a.transcription) != consonant_skeleton(r["transcription"]):
            tr_diff.append((r["word"], r["transcription"], a.transcription))
        eng = set(a.problem_phonemes) - {sound}
        hand = set(r["other_correctable"])
        if eng != hand:
            oc_diff.append((r["word"], sorted(hand - eng), sorted(eng - hand)))
        occ = [o for o in a.sound_occurrences if o["phoneme"] == sound]
        if not occ:
            no_target.append(r["word"])
        if not C.is_clean(r["word"], banned0, r["stress_syllable"]):
            bad = sorted(set(a.problem_phonemes) & banned0)
            dead.append((r["word"], bad))
        ks = set()
        for o in occ:
            ks |= C.occurrence_kind(o)
        if not ks:
            no_kind.append(r["word"])
        for k in ks:
            kinds[k] += 1
            kind_words[k].append(r["word"])

    print(f"\n1а. Транскрипция расходится с движком (согласные): {len(tr_diff)}")
    for w, h, e in tr_diff:
        print(f"   {w:14s} рука [{h}]  движок [{e}]")
    print(f"\n1б. Набор корригируемых расходится: {len(oc_diff)}  (лишнее у руки / у движка)")
    for w, h, e in oc_diff:
        print(f"   {w:14s} {h} / {e}")
    print(f"\n2. Движок не видит [{sound}]: {len(no_target)}  {', '.join(no_target)}")
    print(f"\n3. Мёртвые на листе [{sound}] при пустом профиле: {len(dead)}")
    for w, bad in dead:
        print(f"   {w:14s} {bad}")
    print(f"\n4. Слов на тип слога (канон блока [4]: {C.CANON_MIN_WORDS}, стечения — "
          f"{C.CANON_MIN_WORDS_CLUSTER}):")
    for k in C.SYL_TYPES:
        need = C.canon_min_words(k)
        n = kinds.get(k, 0)
        mark = "✓" if n >= need else "мало"
        print(f"   {k:14s} {n:3d}  {mark}")
    print(f"   ни одному типу не отвечают: {len(no_kind)}  {', '.join(no_kind)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
