# -*- coding: utf-8 -*-
"""
test_phonetics.py — проверки фонетического движка на словах-ловушках.

Запуск:  python3 test_phonetics.py        (свой раннер, без зависимостей)
         pytest test_phonetics.py         (тоже работает)

Ловушки, ради которых всё затевалось: фильтр идёт ПО ЗВУКАМ, НЕ ПО БУКВАМ.
"""

from __future__ import annotations

import sys

from phonetics import analyze, select

_results = []


def check(name, actual, expected):
    ok = actual == expected
    _results.append((ok, name, actual, expected))
    assert ok, f"{name}: получили {actual!r}, ждали {expected!r}"
    return ok


def a(word, stress=None):
    return analyze(word, stress)


# ═══════════════════════════════════════════════════════════════════════
#  A. ТРАНСКРИПЦИЯ — ПО ЗВУЧАНИЮ, А НЕ ПО НАПИСАНИЮ
# ═══════════════════════════════════════════════════════════════════════

def test_transcription_traps():
    check("мороз -> транскрипция", a("мороз", 2).transcription, "марос")
    check("мороз: З НЕ звучит", "з" in a("мороз", 2).phoneme_keys, False)
    check("мороз: звучит С", "с" in a("мороз", 2).problem_phonemes, True)

    check("ложка -> транскрипция", a("ложка", 1).transcription, "лошка")
    check("ложка: Ж НЕ звучит", "ж" in a("ложка", 1).phoneme_keys, False)
    check("ложка: звучит Ш", "ш" in a("ложка", 1).problem_phonemes, True)

    check("лодка -> транскрипция", a("лодка", 1).transcription, "лотка")
    check("лодка: Д НЕ звучит", "д" in a("лодка", 1).phoneme_keys, False)

    check("юбка -> транскрипция", a("юбка", 1).transcription, "йупка")
    check("юбка: Б НЕ звучит", "б" in a("юбка", 1).phoneme_keys, False)
    check("юбка: Ю в начале даёт Й", a("юбка", 1).phoneme_keys[0], "й")

    check("морковка -> транскрипция", a("морковка", 2).transcription, "маркофка")
    check("морковка: В НЕ звучит", "в" in a("морковка", 2).phoneme_keys, False)

    check("солнце: Л непроизносимая", "л" in a("солнце", 1).phoneme_keys, False)
    check("солнце -> транскрипция", a("солнце", 1).transcription, "сонцы")

    check("лестница: Т непроизносимая", a("лестница", 1).transcription, "л'эсн'ица")

    check("маяк -> транскрипция", a("маяк", 2).transcription, "майак")
    check("ёж -> транскрипция", a("ёж", 1).transcription, "йош")
    check("ёж: Ж оглушилось в Ш", "ж" in a("ёж", 1).phoneme_keys, False)

    check("рысь -> транскрипция", a("рысь", 1).transcription, "рыс'")
    check("рысь: С мягкий, не твёрдый",
          ("с'" in a("рысь", 1).problem_phonemes, "с" in a("рысь", 1).problem_phonemes),
          (True, False))

    check("зонт -> транскрипция", a("зонт", 1).transcription, "зонт")
    check("стол -> транскрипция", a("стол", 1).transcription, "стол")
    check("матрёшка -> транскрипция", a("матрёшка", 2).transcription, "матр'ошка")
    check("матрёшка: цель — мягкий Рь, не Р",
          ("р'" in a("матрёшка", 2).problem_phonemes,
           "р" in a("матрёшка", 2).problem_phonemes),
          (True, False))
    check("черепаха -> транскрипция", a("черепаха", 3).transcription, "чир'ипаха")
    check("автобус -> транскрипция", a("автобус", 2).transcription, "афтобус")
    check("автобус: есть С (ловушка)", "с" in a("автобус", 2).problem_phonemes, True)
    check("автобус: В нет, есть Ф", "в" in a("автобус", 2).phoneme_keys, False)
    check("апельсин -> транскрипция", a("апельсин", 3).transcription, "ап'ил'с'ин")
    check("вата -> транскрипция", a("вата", 1).transcription, "вата")
    check("мак -> транскрипция", a("мак", 1).transcription, "мак")


def test_voicing_and_softening():
    check("вокзал: озвончение К->Г", a("вокзал", 2).transcription, "вагзал")
    check("сделать: озвончение С->З", a("сделать", 1).transcription, "зд'элат'")
    check("поезд: каскад оглушения ЗД->СТ", a("поезд", 1).transcription, "пойист")
    check("флаг: Г->К в конце", a("флаг", 1).transcription, "флак")
    check("мазь: Зь->Сь в конце", a("мазь", 1).transcription, "мас'")
    check("снег: Г->К в конце", a("снег", 1).transcription, "сн'эк")
    check("овца: В->Ф перед Ц", a("овца", 2).transcription, "афца")
    check("жить: И->Ы после Ж", a("жить", 1).transcription, "жыт'")
    check("цирк: И->Ы после Ц", a("цирк", 1).transcription, "цырк")
    check("ванна: удвоенная = один звук", a("ванна", 1).transcription, "вана")
    check("что: ЧТ->ШТ", a("что", 1).transcription, "што")
    check("семья: Ь + Я даёт Й", a("семья", 2).transcription, "с'им'йа")
    check("ель: Е в начале даёт Й", a("ель", 1).transcription, "йэл'")
    check("юла: безударная Ю", a("юла", 2).transcription, "йула")
    check("часы: безударная А после Ч -> И", a("часы", 2).transcription, "чисы")
    check("мышь: Ь не смягчает Ш", a("мышь", 1).transcription, "мыш")


# ═══════════════════════════════════════════════════════════════════════
#  B. СЛОГИ
# ═══════════════════════════════════════════════════════════════════════

def test_syllables():
    check("мак: 1 слог", a("мак", 1).n_syllables, 1)
    check("вата: 2 слога", a("вата", 1).n_syllables, 2)
    check("матрёшка: 3 слога", a("матрёшка", 2).n_syllables, 3)
    check("черепаха: 4 слога", a("черепаха", 3).n_syllables, 4)
    check("банка: сонорный закрывает слог",
          [s["text"] for s in a("банка", 1).syllables], ["бан", "ка"])
    check("банка: первый слог закрыт", a("банка", 1).syllables[0]["closed"], True)
    check("маяк: одиночный Й уходит к гласной",
          [s["text"] for s in a("маяк", 2).syllables], ["ма", "йак"])
    check("чайник: Й перед согласным закрывает слог",
          [s["text"] for s in a("чайник", 1).syllables], ["чай", "н'ик"])
    check("матрёшка: ударный слог 2",
          [s["index"] for s in a("матрёшка", 2).syllables if s["stressed"]], [2])
    check("мороз: слово закрыто", a("мороз", 2).ends_closed, True)
    check("вата: слово открыто", a("вата", 1).ends_closed, False)


# ═══════════════════════════════════════════════════════════════════════
#  C. СТЕЧЕНИЯ И cluster_role
# ═══════════════════════════════════════════════════════════════════════

def test_clusters():
    check("стол: стечение в начале",
          [(c["text"], c["position"]) for c in a("стол", 1).clusters], [("ст", "initial")])
    check("зонт: стечение в конце",
          [(c["text"], c["position"]) for c in a("зонт", 1).clusters], [("нт", "final")])
    check("матрёшка: два стечения",
          [c["text"] for c in a("матрёшка", 2).clusters], ["тр'", "шк"])
    check("морковка: два стечения",
          [c["text"] for c in a("морковка", 2).clusters], ["рк", "фк"])
    check("вата: стечений нет", a("вата", 1).clusters, [])

    # cluster_role: ТР -> Р вторым (только начало слога); РТ -> Р первым (только конец)
    o = a("трава", 2).occurrences_of("р")[0]
    check("трава: Р вторым в ТР", (o["cluster"], o["cluster_role"], o["cluster_side"]),
          ("тр", "second", "onset"))
    o = a("кран", 1).occurrences_of("р")[0]
    check("кран: Р вторым в КР", (o["cluster"], o["cluster_role"]), ("кр", "second"))
    o = a("торт", 1).occurrences_of("р")[0]
    check("торт: Р первым в РТ", (o["cluster"], o["cluster_role"], o["cluster_side"]),
          ("рт", "first", "coda"))
    o = a("парк", 1).occurrences_of("р")[0]
    check("парк: Р первым в РК", (o["cluster"], o["cluster_role"]), ("рк", "first"))


# ═══════════════════════════════════════════════════════════════════════
#  D. МАРКОВА V1 — НОМЕР ТИПА != ЧИСЛО СЛОГОВ
# ═══════════════════════════════════════════════════════════════════════

def test_markova_v1():
    cases = [
        ("вата", 1, 1), ("муха", 1, 1),
        ("малина", 2, 2), ("собака", 2, 2),
        ("мак", 1, 3), ("дом", 1, 3), ("ёж", 1, 3), ("рысь", 1, 3),
        ("лимон", 2, 4), ("петух", 2, 4), ("мороз", 2, 4), ("маяк", 2, 4),
        ("банка", 1, 5), ("юбка", 1, 5), ("ложка", 1, 5), ("лодка", 1, 5),
        ("компот", 2, 6), ("чайник", 1, 6),
        ("телефон", 3, 7), ("бегемот", 3, 7),
        ("комната", 1, 8), ("яблоко", 1, 8),
        ("автобус", 2, 9), ("апельсин", 3, 9),
        ("матрёшка", 2, 10), ("морковка", 2, 10),
        ("стол", 1, 11), ("флаг", 1, 11), ("шкаф", 1, 11), ("кнут", 1, 11),
        ("зонт", 1, 12), ("бант", 1, 12), ("танк", 1, 12),
        ("кнопка", 1, 13), ("гнездо", 2, 13),
        ("черепаха", 3, 14), ("пианино", 3, 14),
    ]
    for word, stress, expected in cases:
        check(f"Маркова V1: {word} -> тип {expected}",
              a(word, stress).markova_v1, expected)

    check("тип 11 (стол) сложнее типа 10 (матрёшка) при меньшем числе слогов",
          (a("стол", 1).markova_v1 > a("матрёшка", 2).markova_v1,
           a("стол", 1).n_syllables < a("матрёшка", 2).n_syllables),
          (True, True))

    check("аквариум: beyond_base",
          (a("аквариум", 2).beyond_base, a("аквариум", 2).markova_v1), (True, None))
    check("хвост: стечение с двух сторон -> 12 + флаг конфликта",
          (a("хвост", 1).markova_v1, a("хвост", 1).markova_conflict), (12, True))
    check("зонт: конфликта нет", a("зонт", 1).markova_conflict, False)


# ═══════════════════════════════════════════════════════════════════════
#  E. sound_occurrences / problem_phonemes / оппозиции
# ═══════════════════════════════════════════════════════════════════════

def test_occurrences():
    o = a("матрёшка", 2).occurrences_of("р'")[0]
    check("матрёшка: Рь ударный, гласная после — О",
          (o["vowel_after"], o["stressed"], o["syllable_idx"]), ("о", True, 2))
    check("мороз: С в конце слова", a("мороз", 2).positions_of("с"), {"final"})
    check("стол: С в начале слова и в стечении",
          (a("стол", 1).positions_of("с"),
           a("стол", 1).occurrences_of("с")[0]["in_cluster"]), ({"initial"}, True))
    check("трава: Р по слову medial, «широко» — initial",
          (a("трава", 2).occurrences_of("р")[0]["position"],
           a("трава", 2).occurrences_of("р")[0]["position_wide"]), ("medial", "initial"))
    check("морковка: проблемные фонемы", sorted(a("морковка", 2).problem_phonemes),
          ["к", "р"])
    check("апельсин: проблемные фонемы мягкие",
          sorted(a("апельсин", 3).problem_phonemes), ["л'", "с'"])
    check("класс фонемы Ш", a("ложка", 1).occurrences_of("ш")[0]["phoneme_class"],
          "шипящие")


def test_oppositions_neutral_twins():
    check("солнце: оппозиция с-ц", a("солнце", 1).opposition_pairs, ["с-ц"])
    check("сушка: оппозиция с-ш", a("сушка", 1).opposition_pairs, ["с-ш"])
    check("жизнь: оппозиция з-ж", a("жизнь", 1).opposition_pairs, ["з-ж"])
    check("лестница: оппозиция с-ц", a("лестница", 1).opposition_pairs, ["с-ц"])
    check("мороз: оппозиций нет", a("мороз", 2).opposition_pairs, [])

    check("вата: нейтральное слово", a("вата", 1).is_neutral, True)
    check("дом: нейтральное слово", a("дом", 1).is_neutral, True)
    check("мак: не нейтральное (есть К)", a("мак", 1).is_neutral, False)
    check("морковка: не нейтральное", a("морковка", 2).is_neutral, False)

    check("сосиски: твёрдый и мягкий С в одном слове",
          (a("сосиски", 2).soft_hard_twin, a("сосиски", 2).soft_hard_twins),
          (True, ["с"]))
    check("рекорд: твёрдый и мягкий Р в одном слове",
          (a("рекорд", 2).soft_hard_twin, a("рекорд", 2).soft_hard_twins),
          (True, ["р"]))
    check("мороз: близнецов нет", a("мороз", 2).soft_hard_twin, False)


# ═══════════════════════════════════════════════════════════════════════
#  F. ОТБОР (жёсткие ворота)
# ═══════════════════════════════════════════════════════════════════════

WORDS = [("рак", 1), ("рыба", 1), ("роза", 1), ("шар", 1), ("трава", 2),
         ("торт", 1), ("рука", 2), ("лапа", 1), ("матрёшка", 2),
         ("рекорд", 2), ("рыболов", 3), ("парк", 1)]


def test_select():
    r = select(WORDS, "р", position="initial", exclude_phonemes={"ш"}, markova_max=5)
    check("отбор: Р в начале, тип <= 5", [x.word for x in r],
          ["рыба", "роза", "рак", "рука"])
    check("отбор: ворота наличия отсеяли слова без Р (лапа, матрёшка)",
          r.report["rejected"]["наличие"], 2)
    check("отбор: недобор не молчит",
          (r.report["found"], r.report["shortfall"], bool(r.report["hints"])),
          (4, 6, True))

    r2 = select(WORDS, "р", n=20)
    check("чистота: рыболов выпал (Л — оппозиция р-л)", "рыболов" in [x.word for x in r2],
          False)
    check("чистота: рекорд выпал (мягкий Рь при цели Р)",
          "рекорд" in [x.word for x in r2], False)
    check("наличие: матрёшка выпала (там Рь, а не Р)",
          "матрёшка" in [x.word for x in r2], False)
    check("чистота: список запрещённых включает Л и Рь",
          {"л", "л'", "р'"} <= set(r2.report["banned_phonemes"]), True)

    r3 = select(WORDS, "р", position="final", n=3)
    check("позиция final: только шар", [x.word for x in r3], ["шар"])

    r4 = select(WORDS, "р", exclude_phonemes={"к"}, n=20)
    check("exclude_phonemes: слова с К отсеяны",
          all("к" not in x.phoneme_keys for x in r4), True)

    r5 = select(WORDS, "р'", n=20)
    check("мягкая цель Рь: отбирается матрёшка, а не твёрдые",
          [x.word for x in r5], ["матрёшка"])

    r6 = select(WORDS, "р", position="initial", position_mode="wide", n=20)
    check("position_mode='wide': Р в ТР считается начальным",
          "трава" in [x.word for x in r6], True)

    r7 = select(WORDS, "р", cluster_role="second", n=20)
    check("cluster_role=second: только ТР-подобные", [x.word for x in r7], ["трава"])

    r8 = select(WORDS, "р", syl_types={12}, n=20)
    check("syl_types={12}: односложные со стечением в конце",
          sorted(x.word for x in r8), ["парк", "торт"])


# ═══════════════════════════════════════════════════════════════════════
#  G. УДАРЕНИЕ И ОШИБКИ ВВОДА
# ═══════════════════════════════════════════════════════════════════════

def test_stress_input():
    check("односложное: ударение выводится само", a("мак").stress_syllable, 1)
    check("Ё: ударение выводится само", a("матрёшка").stress_syllable, 2)
    check("Ё в лёд", a("лёд").transcription, "л'от")

    raised = False
    try:
        a("малина")
    except ValueError:
        raised = True
    check("многосложное без ударения -> ValueError", raised, True)

    raised = False
    try:
        a("мак", 3)
    except ValueError:
        raised = True
    check("ударение вне диапазона -> ValueError", raised, True)

    raised = False
    try:
        a("cat", 1)
    except ValueError:
        raised = True
    check("латиница -> ValueError", raised, True)


# ═══════════════════════════════════════════════════════════════════════
#  РАННЕР
# ═══════════════════════════════════════════════════════════════════════

def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = []
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            failures.append((t.__name__, str(exc)))
    ok = sum(1 for r in _results if r[0])
    print(f"проверок: {len(_results)}   прошло: {ok}   упало: {len(_results) - ok}")
    for good, name, actual, expected in _results:
        if not good:
            print(f"  FAIL  {name}\n        получили {actual!r}\n        ждали    {expected!r}")
    if failures:
        print("\nупавшие тест-функции (остановились на первом FAIL):")
        for name, msg in failures:
            print(f"  {name}: {msg}")
        return 1
    print("ВСЁ ЗЕЛЁНОЕ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
