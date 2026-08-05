# -*- coding: utf-8 -*-
"""validate.py — независимая валидация словарной базы движком phonetics.py.

Делает три вещи:
  1) обогащает оба словаря всеми вычисляемыми полями -> *_enriched.jsonl
  2) ищет ошибки (мягкий Рь · неНЕЙТРАЛЬНОЕ в нейтральном пуле ·
     расхождение транскрипции · дубликаты · схемные расхождения)
  3) считает матрицу покрытия по Р и выживаемость по 4 профилям ребёнка

Запуск:  python3 validate.py            (пишет enriched-файлы + печатает отчёт)
         python3 validate.py --quiet    (только файлы)
"""
from __future__ import annotations

import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import phonetics as P  # noqa: E402

R_FILE = os.path.join(HERE, "words_r.jsonl")
N_FILE = os.path.join(HERE, "words_neutral.jsonl")
R_ENRICHED = os.path.join(HERE, "words_r_enriched.jsonl")
N_ENRICHED = os.path.join(HERE, "words_neutral_enriched.jsonl")

TARGET = "р"

# ── документированные пробелы движка: где ручное поле правее вычисленного ──
ENGINE_GAP_OVERRIDES = {
    # слово: (что даёт движок, что реально звучит, причина)
    "костёр": ("с", "с'", "ассимилятивное смягчение С перед мягким Т (п.2 докстринга)"),
    "светофор": ("с", "с'", "ассимилятивное смягчение С перед мягким В (п.2)"),
    "свитер": ("с", "с'", "ассимилятивное смягчение + заимствование: норма [св'и́тэр]"),
}


def load(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def norm_tr(s):
    return (s or "").strip().strip("[]").replace(" ", "")


# ═══════════════════════════════════════════════════════════════════
#  1. ОБОГАЩЕНИЕ
# ═══════════════════════════════════════════════════════════════════

def enrich(rows, out_path):
    out = []
    fails = []
    for row in rows:
        rec = dict(row)
        try:
            a = P.analyze(row["word"], row.get("stress_syllable"))
        except Exception as exc:                      # noqa: BLE001
            fails.append((row["word"], str(exc)))
            rec["engine_error"] = str(exc)
            out.append(rec)
            continue
        d = a.to_dict()
        rec["transcription_manual"] = row.get("transcription")
        rec["transcription"] = d["transcription"]     # единая конвенция = движок
        rec["transcription_display"] = d["transcription_display"]
        for k in ("phonemes", "phoneme_keys", "n_syllables", "syllables", "clusters",
                  "markova_v1", "markova_label", "beyond_base", "markova_conflict",
                  "markova_notes", "sound_occurrences", "problem_phonemes",
                  "opposition_pairs", "is_neutral", "soft_hard_twin",
                  "soft_hard_twins", "ends_closed"):
            rec[k] = d[k]
        rec["target_r_occurrences"] = [o for o in d["sound_occurrences"]
                                       if o["phoneme"] == TARGET]
        rec["other_correctable_computed"] = sorted(
            set(d["problem_phonemes"]) - {TARGET}) if TARGET in d["problem_phonemes"] \
            else sorted(d["problem_phonemes"])
        out.append(rec)
    with io.open(out_path, "w", encoding="utf-8") as f:
        for rec in out:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return out, fails


# ═══════════════════════════════════════════════════════════════════
#  2. ОШИБКИ
# ═══════════════════════════════════════════════════════════════════

def find_errors(r_rows, n_rows):
    errs = collections.defaultdict(list)

    # (г) дубликаты
    for name, rows in (("Р", r_rows), ("НЕЙТР", n_rows)):
        for field in ("id", "word"):
            c = collections.Counter(x[field] for x in rows)
            for k, v in c.items():
                if v > 1:
                    errs["дубликаты"].append(f"{name}: {field}={k!r} x{v}")
    wr = {x["word"] for x in r_rows}
    wn = {x["word"] for x in n_rows}
    for w in sorted(wr & wn):
        errs["дубликаты"].append(f"слово {w!r} есть и в Р, и в нейтральном пуле")
    ir = {x["id"] for x in r_rows}
    inn = {x["id"] for x in n_rows}
    for i in sorted(ir & inn):
        errs["дубликаты"].append(f"id {i!r} есть и в Р, и в нейтральном пуле")

    # (а) мягкий Рь / нет твёрдого Р
    for row in r_rows:
        if "engine_error" in row:
            errs["разбор"].append(f"Р: {row['word']} — {row['engine_error']}")
            continue
        keys = set(row["phoneme_keys"])
        if TARGET not in keys:
            errs["нет твёрдого Р"].append(
                f"{row['word']} {row['transcription_display']}")
        if "р'" in keys:
            errs["мягкий Рь в словаре твёрдого Р"].append(
                f"{row['word']} {row['transcription_display']}")

    # (б) корригируемая фонема в нейтральном пуле
    for row in n_rows:
        if "engine_error" in row:
            errs["разбор"].append(f"НЕЙТР: {row['word']} — {row['engine_error']}")
            continue
        if not row["is_neutral"]:
            errs["не нейтральное в нейтральном пуле"].append(
                f"{row['word']} {row['transcription_display']} -> {row['problem_phonemes']}")
        # мн.ч. отдельно
        pl = row.get("plural")
        if pl:
            try:
                pa = P.analyze(pl) if len(
                    [c for c in pl if c in P.VOWEL_LETTERS]) == 1 else None
            except Exception:                          # noqa: BLE001
                pa = None
            if pa is not None and not pa.is_neutral:
                errs["мн.ч. не нейтральное"].append(
                    f"{row['word']} -> {pl} {pa.transcription_display}"
                    f" {sorted(pa.problem_phonemes)}")

    # (в) транскрипция: ручная != движок
    for tag, rows in (("Р", r_rows), ("НЕЙТР", n_rows)):
        for row in rows:
            if "engine_error" in row:
                continue
            man = norm_tr(row.get("transcription_manual"))
            eng = row["transcription"]
            if man != eng:
                # согласные совпадают?
                cm = "".join(ch for ch in man if ch not in "аоуыэеёюяи")
                ce = "".join(ch for ch in eng if ch not in "аоуыэеёюяи")
                kind = "только гласные (конвенция)" if cm == ce else "СОГЛАСНЫЕ"
                errs[f"транскрипция [{tag}] {kind}"].append(
                    f"{row['word']}: ручная {man!r} / движок {eng!r}")

    # нотация: апостроф после непарных
    for tag, rows in (("Р", r_rows), ("НЕЙТР", n_rows)):
        for row in rows:
            man = norm_tr(row.get("transcription_manual"))
            for i, ch in enumerate(man):
                if ch in "чщжшц" and i + 1 < len(man) and man[i + 1] == "'":
                    errs["нотация: апостроф после непарного"].append(
                        f"{tag} {row['word']}: {man!r}")
                    break
            for x in (row.get("other_correctable") or []):
                if x.rstrip("'") in "чщжшц" and x.endswith("'"):
                    errs["нотация: апостроф после непарного"].append(
                        f"{tag} {row['word']}: other_correctable {x!r}")

    # other_correctable vs движок
    for tag, rows in (("Р", r_rows), ("НЕЙТР", n_rows)):
        for row in rows:
            if "engine_error" in row:
                continue
            man = set(row.get("other_correctable") or [])
            auto = set(row["other_correctable_computed"])
            if man != auto:
                gap = ENGINE_GAP_OVERRIDES.get(row["word"])
                mark = "  (пробел движка)" if gap else ""
                cls_man = {P.PHONEME_CLASS_OF.get(x) for x in man}
                cls_auto = {P.PHONEME_CLASS_OF.get(x) for x in auto}
                key = ("other_correctable: РАСХОЖДЕНИЕ КЛАССА"
                       if cls_man != cls_auto else
                       "other_correctable: только мягкость/нотация")
                errs[key].append(
                    f"{tag} {row['word']}: ручной {sorted(man)} / движок {sorted(auto)}{mark}")

    # тип Марковой
    for tag, rows in (("Р", r_rows), ("НЕЙТР", n_rows)):
        for row in rows:
            if "engine_error" in row:
                continue
            g = row.get("markova_v1_guess")
            g_beyond = (g == "beyond_base")
            if g_beyond:
                if not row["beyond_base"]:
                    errs["тип Марковой"].append(
                        f"{tag} {row['word']}: ручной beyond_base / движок "
                        f"{row['markova_v1']} (beyond={row['beyond_base']})")
            elif g != row["markova_v1"]:
                errs["тип Марковой"].append(
                    f"{tag} {row['word']}: ручной {g} / движок {row['markova_v1']}")

    # схема: сравнение наборов полей двух датасетов
    kr, kn = set(), set()
    for x in r_rows:
        kr |= set(x)
    for x in n_rows:
        kn |= set(x)
    only_r, only_n = sorted(kr - kn), sorted(kn - kr)
    if only_r:
        errs["схема: поля только в words_r"].append(", ".join(only_r))
    if only_n:
        errs["схема: поля только в words_neutral"].append(", ".join(only_n))
    # markova_v1_guess смешанного типа
    mixed = [x["word"] for x in r_rows + n_rows
             if not isinstance(x.get("markova_v1_guess"), int)]
    if mixed:
        errs["схема: markova_v1_guess не int"].append(
            f"{len(mixed)} строк: {mixed}")
    return errs


# ═══════════════════════════════════════════════════════════════════
#  3. МАТРИЦА ПОКРЫТИЯ
# ═══════════════════════════════════════════════════════════════════

POS_ROWS = [
    "начало (вне стечения)",
    "середина (вне стечения)",
    "конец (вне стечения)",
    "в стечении — начало слова",
    "в стечении — середина слова",
    "в стечении — конец слова",
]


# Структурная совместимость «позиция x тип», выведенная из правил
# _classify_markova. Нужна, чтобы отличать ДЫРУ (слов нет, а могли бы быть)
# от НЕВОЗМОЖНОЙ клетки (такого слова не бывает по определению типа).
NO_CLUSTER = {1, 2, 3, 4, 7, 14}     # тип требует 0 стечений
OPEN_END = {1, 2, 5, 8, 14}          # тип требует открытого конца слова
MONO = {3, 11, 12}                   # тип односложный


def cell_possible(row, t):
    if t == "beyond":
        return True
    is_cluster_row = row.startswith("в стечении")
    if is_cluster_row and t in NO_CLUSTER:
        return False
    if row == POS_ROWS[0]:                      # начало вне стечения
        return t != 11                          # 11 = стечение в начале слова
    if row == POS_ROWS[1]:                      # середина вне стечения
        return t not in MONO
    if row == POS_ROWS[2]:                      # конец вне стечения
        return t not in OPEN_END and t != 12     # 12 = стечение в конце
    if row == POS_ROWS[3]:                      # стечение в начале слова
        return True
    if row == POS_ROWS[4]:                      # стечение в середине слова
        return t not in MONO
    if row == POS_ROWS[5]:                      # стечение в конце слова
        return t not in OPEN_END and t != 11
    return True


def pos_bucket(occ, n_phonemes):
    if occ["in_cluster"]:
        cp = occ["cluster_position"]
        return {"initial": POS_ROWS[3], "medial": POS_ROWS[4],
                "final": POS_ROWS[5]}[cp]
    if occ["position"] == "initial":
        return POS_ROWS[0]
    if occ["position"] == "final":
        return POS_ROWS[2]
    return POS_ROWS[1]


def coverage_matrix(r_rows, only_words=None):
    """cell -> set(words). Слово попадает в каждую клетку, куда попал его Р."""
    cells = collections.defaultdict(set)
    types = set()
    for row in r_rows:
        if "engine_error" in row:
            continue
        if only_words is not None and row["word"] not in only_words:
            continue
        a = P.analyze(row["word"], row["stress_syllable"])
        clmap = {}
        for c in a.clusters:
            for k in range(c["start"], c["end"] + 1):
                clmap[k] = c
        t = "beyond" if row["beyond_base"] or row["markova_v1"] is None \
            else row["markova_v1"]
        types.add(t)
        for o in row["target_r_occurrences"]:
            cl = clmap.get(o["index"])
            occ = dict(o)
            occ["cluster_position"] = cl["position"] if cl else None
            cells[(pos_bucket(occ, len(a.phonemes)), t)].add(row["word"])
    return cells, types


# ═══════════════════════════════════════════════════════════════════
#  4. ПРОФИЛИ РЕБЁНКА
# ═══════════════════════════════════════════════════════════════════

SHIP = ["ш", "ж", "щ", "ч"]
WHIST = ["с", "с'", "з", "з'", "ц"]
BACK = ["к", "к'", "г", "г'", "х", "х'"]

PROFILES = [
    ("А. нарушен только Р", []),
    ("Б. Р + Л", ["л", "л'"]),
    ("В. Р + Л + шипящие", ["л", "л'"] + SHIP),
    ("Г. Р + Л + шипящие + свистящие (тяжёлое ОНР)", ["л", "л'"] + SHIP + WHIST),
    ("Д. Г + заднеязычные", ["л", "л'"] + SHIP + WHIST + BACK),
    ("Е. Д + йот (профиль отчёта задачи 2)",
     ["л", "л'", "й"] + SHIP + WHIST + BACK),
]


def run_profiles(r_rows):
    words = [(x["word"], x["stress_syllable"]) for x in r_rows
             if "engine_error" not in x]
    res = []
    for name, excl in PROFILES:
        sel = P.select(words, TARGET, exclude_phonemes=excl, n=10 ** 6)
        res.append((name, excl, sel))
    return res


def print_matrix(cells, order, title, total_n=None):
    print("\n" + "=" * 78 + f"\n{title}\n" + "=" * 78)
    print("позиция \\ тип".ljust(30) + "".join(str(t).rjust(7) for t in order)
          + "  ИТОГО")
    for row in POS_ROWS:
        line = row.ljust(30)
        tot = set()
        for t in order:
            s = cells.get((row, t), set())
            tot |= s
            if s:
                line += str(len(s)).rjust(7)
            else:
                line += ("·" if cell_possible(row, t) else "✗").rjust(7)
        line += str(len(tot)).rjust(7)
        print(line)
    line = "ИТОГО (уник. слов)".ljust(30)
    allw = set()
    for t in order:
        u = set()
        for row in POS_ROWS:
            u |= cells.get((row, t), set())
        allw |= u
        line += str(len(u)).rjust(7)
    line += str(len(allw)).rjust(7)
    print(line)
    print("  · = пусто (клетка возможна, слов нет)   "
          "✗ = структурно невозможна для этого типа")
    poss = [(r_, t) for r_ in POS_ROWS for t in order if cell_possible(r_, t)]
    empty = [(r_, t) for r_, t in poss if not cells.get((r_, t))]
    poor = [(r_, t, len(cells[(r_, t)])) for r_, t in poss
            if 0 < len(cells.get((r_, t), set())) < 3]
    print(f"  возможных клеток: {len(poss)} из {len(POS_ROWS) * len(order)} · "
          f"ПУСТЫХ: {len(empty)} · БЕДНЫХ (<3): {len(poor)} · "
          f"наполненных (>=3): {len(poss) - len(empty) - len(poor)}")
    return poss, empty, poor


# ═══════════════════════════════════════════════════════════════════

def main():
    quiet = "--quiet" in sys.argv
    r_raw, n_raw = load(R_FILE), load(N_FILE)
    r_rows, r_fail = enrich(r_raw, R_ENRICHED)
    n_rows, n_fail = enrich(n_raw, N_ENRICHED)
    print(f"обогащено: Р={len(r_rows)} -> {os.path.basename(R_ENRICHED)}, "
          f"НЕЙТР={len(n_rows)} -> {os.path.basename(N_ENRICHED)}")
    if r_fail or n_fail:
        print("НЕ РАЗОБРАНО:", r_fail + n_fail)
    if quiet:
        return

    errs = find_errors(r_rows, n_rows)
    print("\n" + "=" * 72 + "\nОШИБКИ\n" + "=" * 72)
    for k in sorted(errs):
        v = errs[k]
        print(f"\n[{k}] — {len(v)}")
        for line in v[:200]:
            print("   ", line)
    for k in ("мягкий Рь в словаре твёрдого Р", "нет твёрдого Р",
              "не нейтральное в нейтральном пуле", "дубликаты"):
        if k not in errs:
            print(f"\n[{k}] — 0  (чисто)")

    cells, types = coverage_matrix(r_rows)
    order = [t for t in range(1, 15) if t in types] + \
            (["beyond"] if "beyond" in types else [])
    poss, empty, poor = print_matrix(
        cells, order, "МАТРИЦА ПОКРЫТИЯ Р — вся база (уникальных слов в клетке)")
    print("\n  ПУСТЫЕ возможные клетки:")
    for row, t in empty:
        print(f"    {row} x тип {t}")
    print("\n  БЕДНЫЕ клетки (<3):")
    for row, t, k in poor:
        print(f"    {row} x тип {t}: {k} — {sorted(cells[(row, t)])}")
    need = sum(max(0, 3 - len(cells.get((r_, t), set()))) for r_, t in poss)
    print(f"\n  дефицит до 3 слов в каждой возможной клетке: +{need} слов")

    # ударность цели
    unstressed = [x["word"] for x in r_rows
                  if x.get("target_r_occurrences")
                  and not any(o["stressed"] for o in x["target_r_occurrences"])]
    print(f"\n  Р только в БЕЗУДАРНОМ слоге: {len(unstressed)} из {len(r_rows)}"
          f" ({100.0 * len(unstressed) / len(r_rows):.0f}%)")

    print("\n" + "=" * 78 + "\nВЫЖИВАЕМОСТЬ ПО ПРОФИЛЯМ\n" + "=" * 78)
    profiles = run_profiles(r_rows)
    for name, excl, sel in profiles:
        rep = sel.report
        print(f"\n{name}")
        print(f"   исключено движком: {rep['banned_phonemes']}")
        print(f"   выжило: {len(sel)} из {len(r_rows)}"
              f"  ({100.0 * len(sel) / len(r_rows):.0f}%)")
        by_t = collections.Counter(
            (a.markova_v1 if not a.beyond_base else "beyond") for a in sel)
        print("   по типам:", dict(sorted(by_t.items(), key=lambda x: str(x[0]))))
        if len(sel) <= 45:
            print("   слова:", ", ".join(a.word for a in sel))

    # матрицы по «боевым» профилям
    for name, excl, sel in profiles:
        if not name.startswith(("В.", "Г.", "Е.")):
            continue
        w = {a.word for a in sel}
        c2, _ = coverage_matrix(r_rows, only_words=w)
        print_matrix(c2, order, f"МАТРИЦА ПОКРЫТИЯ Р — профиль «{name}» "
                                f"({len(w)} слов)")


if __name__ == "__main__":
    main()
