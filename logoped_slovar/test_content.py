# -*- coding: utf-8 -*-
"""
test_content.py — проверки генератора наполнения листа.

Запуск:  python3 test_content.py         (свой раннер, без зависимостей)
         pytest test_content.py          (тоже работает)

Главное, что здесь проверяется, — не «красиво ли», а четыре обещания:
чистота по звукам · сквозной словарь · связка «слог — слово» ·
детерминированность. Плюс: сторожа (verify_*) обязаны ПАДАТЬ на подложенном
браке, иначе они декорация.
"""

from __future__ import annotations


import json
import sys

import phonetics as ph
import content as C

_results = []


def check(name, actual, expected):
    ok = actual == expected
    _results.append((ok, name, actual, expected))
    assert ok, f"{name}: получили {actual!r}, ждали {expected!r}"
    return ok


def truthy(name, actual):
    return check(name, bool(actual), True)


PROFILE = {"л", "ш", "ж"}
HEAVY = {"л", "ш", "ж", "с", "з", "ц", "щ", "ч"}


def build(**kw):
    kw.setdefault("profile", PROFILE)
    return C.build_content(**kw)


# ═══════════════════════════════════════════════════════════════════════
#  A. ФИЛЬТР ЧИСТОТЫ (правила 1-3)
# ═══════════════════════════════════════════════════════════════════════

def test_banned_includes_mixed_and_twin():
    b = C.banned_phonemes("р", {"ш"})
    check("Л запрещён при цели Р (оппозиция)", "л" in b, True)
    check("Ль запрещён", "л'" in b, True)
    check("Рь запрещён (мягкий близнец цели)", "р'" in b, True)
    check("сама цель Р не запрещена", "р" in b, False)
    check("Ш из профиля запрещён", "ш" in b, True)
    # Решение 2026-08-08: безусловно убираем только то, что стоит в
    # оппозиционных парах движка. [й] там не стоит ни в одной — значит он
    # убирается ПРОФИЛЕМ, как решит логопед про конкретного ребёнка.
    check("Й сам по себе НЕ запрещён", "й" in b, False)
    check("Й запрещается, если логопед отметил его в профиле",
          "й" in C.banned_phonemes("р", {"й"}), True)


def test_profile_expands_to_soft_twin():
    b = C.banned_phonemes("р", {"с"})
    check("профиль С тянет за собой Сь", "с'" in b, True)


def test_no_banned_phoneme_in_material():
    for syl_type in C.SYL_TYPES:
        c = build(syl_type=syl_type)
        banned = set(c["meta"]["banned"])
        for block, text in C._material_texts(c):
            for tok in C._tokens(text):
                dirty = C.corrigible_of(tok) & banned
                check(f"{syl_type}/{block}: {tok} чист", sorted(dirty), [])


def test_filter_is_by_sound_not_letter():
    # «мороз» = [марос] содержит С — при профиле со свистящими слово обязано выпасть
    c = build(profile={"л", "ш", "ж", "с", "з"}, syl_type="intervocal")
    check("мороз не попал (в нём звучит С)", "мороз" in c["words"]["all"], False)
    c2 = build(profile={"л", "ш", "ж"}, syl_type="intervocal", n_words=24)
    check("при чистом по С профиле мороз доступен",
          "мороз" in c2["words"]["all"], True)


def test_soft_r_words_excluded():
    for syl_type in C.SYL_TYPES:
        c = build(syl_type=syl_type)
        for w in c["words"]["all"]:
            keys = ph.analyze(w, next(it["stress_syllable"] for g in c["words"]["groups"]
                                      for it in g["items"] if it["word"] == w)).phoneme_keys
            check(f"{w}: нет мягкого Рь", "р'" in keys, False)


def test_verify_purity_actually_raises():
    c = build()
    c["words"]["groups"][0]["items"].append({
        "word": "лошадка", "stress_syllable": 2, "transcription": "лашатка",
        "markova_v1": 5, "familiarity": 3, "gender": "f", "plural": "лошадки",
        "semantic_category": "животные/домашние", "tier": "а",
        "initial": False, "stressed": True, "_occ": None,
    })
    try:
        C.verify_purity(c)
    except C.PurityViolation as exc:
        check("verify_purity падает на подложенном грязном слове",
              "лошадка" in str(exc), True)
    else:
        check("verify_purity падает на подложенном грязном слове", False, True)


# ═══════════════════════════════════════════════════════════════════════
#  B. СКВОЗНОЙ СЛОВАРЬ (правило 13)
# ═══════════════════════════════════════════════════════════════════════

def test_crosscut_holds():
    for syl_type in C.SYL_TYPES:
        c = build(syl_type=syl_type)
        C.verify_crosscut(c)          # не должно бросить
        check(f"{syl_type}: сквозной словарь держится", True, True)


def test_sentences_use_only_declared_sources():
    """Каждое слово предложения пришло из места, которое можно назвать.

    С 2026-08-08 источников четыре, а не три: к блоку [4] и служебным
    добавились ГЛАГОЛЫ листа. Они объявляются в vocabulary["verbs"] и проходят
    тот же фильтр чистоты — «слушает» на лист [С] не пускается, в нём [ш].
    """
    c = build()
    allowed = (set(c["vocabulary"]["block4"]) | set(c["vocabulary"]["service"])
               | set(c["vocabulary"]["verbs"]))
    for s in c["sentences"]["items"]:
        for tok in C._tokens(s["text"]):
            check(f"предложение: {tok} из блока [4] или служебное",
                  tok in allowed, True)


def test_verify_crosscut_actually_raises():
    c = build()
    c["sentences"]["items"].append(
        {"text": "Тут кастрюля.", "n_words": 2, "scale": "Три слова"})
    try:
        C.verify_crosscut(c)
    except C.CrosscutViolation as exc:
        check("verify_crosscut падает на чужом слове", "кастрюл" in str(exc), True)
    else:
        check("verify_crosscut падает на чужом слове", False, True)


def test_derived_form_must_point_to_block4():
    c = build()
    c["vocabulary"]["derived"]["табуретки"] = "табуретка"
    try:
        C.verify_crosscut(c)
    except C.CrosscutViolation as exc:
        check("производная форма без леммы в блоке [4] падает",
              "табуретк" in str(exc), True)
    else:
        check("производная форма без леммы в блоке [4] падает", False, True)


def test_game_answers_are_derived_of_block4():
    for seed in range(3):
        c = build(seed=seed)
        block4 = set(c["vocabulary"]["block4"])
        for it in c["game"]["items"]:
            check(f"игра seed={seed}: {it['prompt']} из блока [4]",
                  it["prompt"] in block4, True)


def test_service_words_have_no_target_sound():
    pool = C._service_pool("р", C.banned_phonemes("р", PROFILE))
    for w in pool:
        check(f"служебное {w}: без целевого Р",
              "р" in ph.analyze(w, pool[w]).phoneme_keys, False)


# ═══════════════════════════════════════════════════════════════════════
#  C. БЛОК [3] — СЛОГИ
# ═══════════════════════════════════════════════════════════════════════

def test_syllables_one_type_and_count():
    for syl_type in C.SYL_TYPES:
        c = build(syl_type=syl_type)
        s = c["syllables"]
        check(f"{syl_type}: тип один", s["type"], syl_type)
        truthy(f"{syl_type}: 16-25 слогов", 16 <= s["n_units"] <= 25)
        truthy(f"{syl_type}: 4-6 рядов", 4 <= s["n_rows"] <= 6)


def test_every_row_has_bond_to_block4():
    for syl_type in C.SYL_TYPES:
        c = build(syl_type=syl_type)
        block4 = set(c["words"]["all"])
        for row in c["syllables"]["rows"]:
            truthy(f"{syl_type}: ряд имеет связку", row["bond"])
            check(f"{syl_type}: слово связки из блока [4]",
                  row["bond"]["word"] in block4, True)


def test_bond_matches_by_sound_not_by_letters():
    """«борода» = [барада] на слог «оро» не годится, хотя буквы совпадают."""
    for syl_type in C.SYL_TYPES:
        c = build(syl_type=syl_type)
        by_word = {it["word"]: it for g in c["words"]["groups"] for it in g["items"]}
        for row in c["syllables"]["rows"]:
            b = row["bond"]
            tr = by_word[b["word"]]["transcription"]
            check(f"{syl_type}: связка «{b['syllable']} — {b['word']}» звучит",
                  b["syllable"] in tr, True)


def test_no_i_vowel_in_syllables():
    for syl_type in C.SYL_TYPES:
        c = build(syl_type=syl_type)
        for row in c["syllables"]["rows"]:
            for u in row["units"]:
                check(f"{syl_type}: в слоге {u} нет И", "и" in u, False)


def test_syllable_shapes():
    c = build(syl_type="direct")
    check("прямой слог начинается с Р", c["syllables"]["rows"][0]["units"][0][0], "р")
    c = build(syl_type="reverse")
    check("обратный слог кончается на Р", c["syllables"]["rows"][0]["units"][0][-1], "р")
    c = build(syl_type="intervocal")
    check("интервокальный слог из 3 букв",
          len(c["syllables"]["rows"][0]["units"][0]), 3)
    c = build(syl_type="cluster_onset")
    truthy("слог со стечением в начале длиннее 2",
           len(c["syllables"]["rows"][0]["units"][0]) >= 3)


# ═══════════════════════════════════════════════════════════════════════
#  D. БЛОК [4] — СЛОВА
# ═══════════════════════════════════════════════════════════════════════

def test_words_count_and_groups():
    for syl_type in C.SYL_TYPES:
        c = build(syl_type=syl_type)
        w = c["words"]
        truthy(f"{syl_type}: 12-24 слова", 12 <= w["n"] <= 24)
        check(f"{syl_type}: слов столько же, сколько в all", w["n"], len(w["all"]))
        for g in w["groups"]:
            truthy(f"{syl_type}: гласная колонки из АОУЫ", g["vowel"] in C.VOWELS)
            check(f"{syl_type}: заголовок колонки — слог",
                  g["header"].endswith(":"), True)
            check(f"{syl_type}: колонка непуста", len(g["items"]) > 0, True)


def test_group_header_is_the_syllable():
    c = build(syl_type="direct")
    headers = {g["header"] for g in c["words"]["groups"]}
    truthy("прямой лист: колонка «Ра:» есть", "Ра:" in headers)
    c = build(syl_type="reverse")
    headers = {g["header"] for g in c["words"]["groups"]}
    truthy("обратный лист: колонка «Ар:» есть", "Ар:" in headers)


def test_two_tiers_present():
    c = build(syl_type="direct", n_words=20)
    tier_a = sum(len(g["tier_a"]) for g in c["words"]["groups"])
    tier_b = sum(len(g["tier_b"]) for g in c["words"]["groups"])
    truthy("ярус а) непуст", tier_a > 0)
    truthy("ярус б) непуст", tier_b > 0)


def test_no_duplicate_words():
    for syl_type in C.SYL_TYPES:
        c = build(syl_type=syl_type)
        all_w = c["words"]["all"]
        check(f"{syl_type}: слова не повторяются", len(all_w), len(set(all_w)))


def test_sheet_no_shifts_selection():
    a1 = build(sheet_no=1)["words"]["all"]
    a2 = build(sheet_no=2)["words"]["all"]
    check("лист №2 отличается от листа №1", a1 == a2, False)


# ═══════════════════════════════════════════════════════════════════════
#  E. БЛОК [5] — ИГРА
# ═══════════════════════════════════════════════════════════════════════

def test_game_has_sample_with_completed_first_item():
    for seed in range(3):
        c = build(seed=seed)
        g = c["game"]
        check(f"seed={seed}: строка «Образец:» есть",
              g["sample"].startswith("Образец:"), True)
        first = g["items"][0]
        check(f"seed={seed}: образец содержит первый элемент",
              first["prompt"] in g["sample"], True)
        check(f"seed={seed}: образец выполнен",
              first["answer"] in g["sample"], True)


def test_games_reachable():
    """Игры, которые СЕЙЧАС имеют право строиться, — строятся.

    «Посчитай 1-5» выбывала 2026-08-08: её формы порождало правило, и оно
    врало. 2026-08-10 таблица форм выверена (590 ед. ч. / 595 мн. ч.), и игра
    вернулась — теперь строятся ВСЕ три канонные игры ТЗ, как и написано в
    оставленной здесь же инструкции «когда таблица появится, вернуть».
    """
    kinds = set()
    for seed in range(6):
        for sheet in (1, 2, 3):
            kinds.add(build(seed=seed, sheet_no=sheet, n_words=24)["game"]["kind"])
    check("строятся все три канонные игры", kinds, set(C.GAME_KINDS))


def test_one_many_skips_uncountable():
    for seed in range(6):
        c = build(seed=seed, syl_type="cluster_onset", n_words=24)
        if c["game"]["kind"] != "one_many":
            continue
        for it in c["game"]["items"]:
            check(f"«{it['prompt']}» исчисляемо", it["prompt"] == it["answer"], False)


def test_diminutive_never_uses_blocked_word():
    for seed in range(6):
        for sheet in (1, 2, 3):
            c = build(seed=seed, sheet_no=sheet, n_words=24)
            if c["game"]["kind"] != "diminutive":
                continue
            for it in c["game"]["items"]:
                check(f"деминутив не берёт запрещённое «{it['prompt']}»",
                      it["prompt"] in C.DIMINUTIVE_BLOCKED, False)


def test_count_game_forms():
    """Падежная форма берётся ТОЛЬКО из выверенной таблицы.

    Тест переписан 2026-08-08. Раньше он закреплял работу правила-генератора —
    и вместе с ней брак: «два угола · пять уголов · лобов · козёлов · левов ·
    пёсов · заяцов · лужайок · пять редьк», а после расширения стоп-листа
    вылезли осётр, улей, репей, ёж, ёрш. Русское словоизменение не ловится
    хвостом слова, поэтому правило выключено (C.ALLOW_RULE_CASES = False).
    """
    check("правило падежей выключено", C.ALLOW_RULE_CASES, False)

    # что в таблице — то и печатается
    check("рот: род. ед. по таблице", C._gen_sg("рот", "m"), "рта")
    check("рот: род. мн. по таблице", C._gen_pl("рот", "m"), "ртов")
    check("ведро: род. мн. по таблице", C._gen_pl("ведро", "n"), "вёдер")
    check("лоб: род. ед. по таблице", C._gen_sg("лоб", "m"), "лба")
    check("стул: род. мн. по таблице", C._gen_pl("стул", "m"), "стульев")

    # 2026-08-10: таблица выросла с 23 слов до 590/595 — двумя независимыми
    # разборами со сверкой (99,7 % совпадения, ноль расхождений с формами,
    # выверенными руками 08-08). Прежние «слова вне таблицы» в неё вошли,
    # поэтому проверка молчания идёт на словах, которых в словарях нет вовсе.
    # Смысл теста не изменился: движок НЕ ВЫВОДИТ форму, он её ЗНАЕТ или молчит.
    for word, gender in (("трамплин", "m"), ("философия", "f"),
                         ("пингвин", "m"), ("велосипед", "m")):
        check(f"{word}: род. ед. не выдумывается", C._gen_sg(word, gender), None)
        check(f"{word}: род. мн. не выдумывается", C._gen_pl(word, gender), None)


def test_count_game_never_prints_wrong_form():
    """Ни одно слово всех словарей не даёт формы мимо выверенной таблицы."""
    import json as _json, glob as _glob, os as _os
    here = _os.path.dirname(_os.path.abspath(__file__))
    leaked = []
    for path in _glob.glob(_os.path.join(here, "words_*.jsonl")):
        if "neutral" in path or "enriched" in path:
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                d = _json.loads(line)
                w, g = d["word"], d.get("gender")
                if not g:
                    continue
                if C._gen_sg(w, g) and w not in C.GEN_SG_OVERRIDES:
                    leaked.append(w)
                if C._gen_pl(w, g) and w not in C.GEN_PL_OVERRIDES:
                    leaked.append(w)
    check(f"форм мимо таблицы нет (утекло: {leaked[:5]})", len(leaked), 0)


def test_diminutive_table_is_sane():
    for word, form in C.DIMINUTIVE.items():
        check(f"деминутив {word} не равен слову", word == form, False)
        ph.analyze(form, 1)          # разбирается движком
    overlap = set(C.DIMINUTIVE) & set(C.DIMINUTIVE_BLOCKED)
    check("слово не может быть одновременно в таблице и в блок-листе",
          sorted(overlap), [])


def test_game_instruction_is_one_imperative_phrase():
    for seed in range(3):
        g = build(seed=seed)["game"]
        check(f"seed={seed}: инструкция — одна фраза",
              g["instruction"].count(".") <= 1, True)
        truthy(f"seed={seed}: канонический глагол",
               g["instruction"].split()[0].rstrip(",.").capitalize() in C.CHILD_VERBS)


# ═══════════════════════════════════════════════════════════════════════
#  F. БЛОК [6] — ПРЕДЛОЖЕНИЯ
# ═══════════════════════════════════════════════════════════════════════

def test_sentences_count_and_scale():
    c = build()
    items = c["sentences"]["items"]
    truthy("6-10 предложений", 6 <= len(items) <= 10)
    lengths = [it["n_words"] for it in items]
    check("шкала длины не убывает", lengths, sorted(lengths))
    for it in items:
        check(f"«{it['text']}»: слов = заявленному",
              len(it["text"].split()), it["n_words"])


def test_sentence_scale_labels():
    c = build()
    labels = {it["n_words"]: it["scale"] for it in c["sentences"]["items"]}
    for n, label in labels.items():
        check(f"подпись шкалы для {n}", label,
              {3: "Три слова", 4: "Четыре слова", 5: "Пять слов"}[n])


def test_sentences_are_capitalised_and_closed():
    c = build()
    for it in c["sentences"]["items"]:
        check(f"«{it['text']}» с большой буквы", it["text"][0].isupper(), True)
        check(f"«{it['text']}» с точкой", it["text"].endswith("."), True)


def test_body_parts_not_in_sentences():
    # семантические ворота каркаса: «Дома одна рука» — брак
    for seed in range(4):
        c = build(seed=seed, syl_type="direct", n_words=20)
        text = " ".join(it["text"] for it in c["sentences"]["items"])
        for bad in ("рука", "рот", "борода"):
            check(f"seed={seed}: «{bad}» не в предложениях", bad in C._tokens(text), False)


# ═══════════════════════════════════════════════════════════════════════
#  G. БЛОК [7] — ЧИСТОГОВОРКА
# ═══════════════════════════════════════════════════════════════════════

def test_chistogovorka_rhymes():
    c = build(syl_type="direct")
    ch = c["chistogovorka"]
    truthy("чистоговорка построена", ch)
    syl = ch["syllable"]
    check("зачин — тройной слог", ch["text"].lower().startswith(f"{syl}-{syl}-{syl}"), True)
    a = ph.analyze(ch["rhyme_word"], ch["rhyme_stress"])
    check("рифма: слово кончается целевым слогом",
          a.transcription.endswith(syl), True)
    check("рифма: последний слог ударный", a.syllables[-1]["stressed"], True)


def test_chistogovorka_is_on_the_same_step():
    for syl_type in C.SYL_TYPES:
        c = build(syl_type=syl_type)
        ch = c["chistogovorka"]
        if not ch:
            continue
        units = {u for row in c["syllables"]["rows"] for u in row["units"]}
        check(f"{syl_type}: слог чистоговорки — со ступени листа",
              ch["syllable"] in units, True)
        a = ph.analyze(ch["rhyme_word"], ch["rhyme_stress"])
        check(f"{syl_type}: рифма кончается этим слогом",
              a.transcription.endswith(ch["syllable"]), True)


def test_chistogovorka_word_from_block4():
    c = build(syl_type="direct")
    ch = c["chistogovorka"]
    vocab = set(c["vocabulary"]["block4"]) | set(c["vocabulary"]["derived"])
    check("слово рифмы из сквозного словаря", ch["rhyme_word"] in vocab, True)


# ═══════════════════════════════════════════════════════════════════════
#  H. ДЕТЕРМИНИРОВАННОСТЬ И НЕДОБОР
# ═══════════════════════════════════════════════════════════════════════

def _dump(c):
    return json.dumps(c, ensure_ascii=False, sort_keys=True, default=str)


def test_deterministic():
    for syl_type in C.SYL_TYPES:
        a = build(syl_type=syl_type, seed=7, sheet_no=2)
        b = build(syl_type=syl_type, seed=7, sheet_no=2)
        check(f"{syl_type}: один seed — один результат", _dump(a), _dump(b))


def test_seed_changes_result():
    a = build(seed=0, n_words=24)
    b = build(seed=1, n_words=24)
    check("разные seed — разный лист", _dump(a) == _dump(b), False)


def test_shortfall_is_reported():
    c = build(profile=HEAVY, syl_type="cluster_coda", n_words=24)
    truthy("недобор не молчит", c["warnings"])
    joined = " ".join(c["warnings"])
    truthy("сообщение про «нашлось N слов из M»", "нашлось" in joined)


def test_shortfall_message_shape():
    msg = C._shortfall_message(8, 12, {"структура": 3, "частотность": 5, "чистота": 9},
                               4, 3)
    truthy("формат: нашлось X из Y", msg.startswith("нашлось 8 слов из 12"))
    truthy("подсказка про Маркову", "тип Марковой до 6" in msg)
    truthy("подсказка про familiarity", "familiarity=3" in msg)
    truthy("чистоту снимать нельзя", "НЕЛЬЗЯ" in msg)


def test_game_degrades_loudly_not_silently():
    """Крайний профиль: игру собрать не из чего. Блок пуст, но молчания нет."""
    extreme = {"л", "ш", "ж", "щ", "ч", "с", "з", "ц", "к", "г", "х"}
    c = C.build_content(syl_type="cluster_coda", profile=extreme, n_words=12)
    check("игра не построена", c["game"], None)
    truthy("сказано, что блок [5] пуст",
           any("блок [5] пуст" in w for w in c["warnings"]))
    C.verify_purity(c)                 # проверки переживают пустой блок
    C.verify_crosscut(c)
    truthy("предпросмотр не падает", "[5]" in C.render_preview(c))


def test_heavy_profile_still_clean_or_honest():
    c = build(profile=HEAVY, syl_type="direct", n_words=12)
    banned = set(c["meta"]["banned"])
    for _block, text in C._material_texts(c):
        for tok in C._tokens(text):
            check(f"тяжёлый профиль: {tok} чист",
                  sorted(C.corrigible_of(tok) & banned), [])


# ═══════════════════════════════════════════════════════════════════════
#  I. ИНВАРИАНТЫ ДВИЖКА, НА КОТОРЫХ СТОИТ МОДУЛЬ
# ═══════════════════════════════════════════════════════════════════════

def test_purity_is_stress_independent():
    """Обоснование: производные формы (мн. ч., деминутив, падежи) идут без
    ударения. Это законно только если набор корригируемых фонем от ударения
    не зависит. Проверяем на всём корпусе."""
    rows = C.load_words(str(C.HERE / "words_r.jsonl"))
    bad = []
    for r in rows:
        n = ph.analyze(r["word"], r["stress_syllable"]).n_syllables
        sets = {ph.analyze(r["word"], s).problem_phonemes for s in range(1, n + 1)}
        if len(sets) != 1:
            bad.append(r["word"])
    check("корригируемые фонемы не зависят от ударения", bad, [])


def test_dictionary_rows_are_analyzable():
    rows = C.load_words(str(C.HERE / "words_r.jsonl"))
    # Число растёт по мере пополнения картотеки — важно не оно, а то, что
    # каждая строка разбирается движком. Жёсткая цифра здесь только ловила бы
    # руку на случайной потере строк, поэтому держим нижнюю границу.
    check("словарь [Р] не усох", len(rows) >= 162, True)
    for r in rows:
        ph.analyze(r["word"], r["stress_syllable"])


# ═══════════════════════════════════════════════════════════════════════
#  J. КОНТРАКТ API
# ═══════════════════════════════════════════════════════════════════════

def test_unknown_sound_fails_loudly():
    # Звук, словаря которого нет. Тест переезжал дважды: «ш» → «л», оба раза
    # потому, что словарь появлялся. Теперь взят [ч] — аффриката, намеренно
    # оставленная вне формата листа (её нельзя тянуть в блоке [2], и порядок
    # слогов у неё перевёрнут). Если словарь [ч] однажды появится, значит
    # построен отдельный лист для аффрикат — тогда взять звук, которого нет.
    assert "ч" not in C.WORDS_BY_SOUND, "тест устарел: словарь [ч] появился, возьмите другой звук"
    try:
        C.build_content(sound="ч", profile={"р"})
    except C.ContentError as exc:
        truthy("нет словаря — говорим прямо", "словаря нет" in str(exc))
    else:
        check("нет словаря — говорим прямо", False, True)


def test_bad_syl_type_fails():
    try:
        C.build_content(syl_type="какой-то")
    except C.ContentError as exc:
        truthy("неизвестный тип слога отвергнут", "syl_type" in str(exc))
    else:
        check("неизвестный тип слога отвергнут", False, True)


def test_canonical_ranges_enforced():
    for kw, why in (({"n_words": 30}, "слов"), ({"n_sentences": 20}, "предложений")):
        try:
            C.build_content(profile=PROFILE, **kw)
        except C.ContentError:
            check(f"вне канона ({why}) — отказ", True, True)
        else:
            check(f"вне канона ({why}) — отказ", False, True)


def test_all_blocks_present():
    c = build()
    for key in ("header", "artic", "isolated", "syllables", "words", "game",
                "sentences", "chistogovorka", "footer", "warnings", "meta",
                "vocabulary", "purity_scope"):
        truthy(f"блок {key} присутствует", key in c)
    check("блок [8] графики в v1 нет", "graphics" in c, False)


def test_one_game_image_and_canon_verbs():
    c = build()
    check("изолированный звук — ровно одна строка",
          c["isolated"]["line"].count("\n"), 0)
    # Канон ТЗ: «Р — мотора». Источник (Спивак 2007) даёт «песенку мотора».
    truthy("игровой образ — мотор (канон для Р)", "мотор" in c["isolated"]["image"])
    check("образ взят со стадии АВТОМАТИЗАЦИИ, не постановки",
          c["isolated"].get("stage"), "автоматизация")
    truthy("образ отслежен до источника", bool(c["isolated"].get("source")))
    truthy("«заведи мотор» (постановка у Фомичёвой) на лист не попал",
           "заведи" not in c["isolated"]["line"].lower())
    truthy("нет дятла/барабанщика на листе автоматизации",
           "барабанщик" not in C._tokens(c["isolated"]["line"] + " "
                                         + " ".join(c["artic"]["items"])))
    truthy("блок [1] отслежен до источника (gymnastics.json)",
           bool(c["artic"].get("source")))
    check("блок [1] — ровно 4 названия", len(c["artic"]["items"]), 4)
    for path in (c["syllables"]["instruction"], c["words"]["instruction"],
                 c["sentences"]["instruction"], c["artic"]["instruction"]):
        truthy(f"инструкция «{path}» начинается каноническим глаголом",
               path.split()[0].rstrip(",.") in C.CHILD_VERBS)
    truthy("двойной глагол «Повтори, прочитай»",
           c["words"]["instruction"].startswith("Повтори, прочитай"))


def test_footer_has_no_invented_norms():
    c = build()
    text = " ".join(c["footer"])
    truthy("подвал ≤ 3 строк", len(c["footer"]) <= 3)
    for fake in ("60 раз", "21 день", "100 раз"):
        check(f"нет выдуманной нормы «{fake}»", fake in text, False)
    truthy("есть разрешение поделить на приёмы", "2-3 приёма" in text)


def test_render_preview_runs():
    txt = C.render_preview(build())
    truthy("предпросмотр содержит все номера блоков",
           all(m in txt for m in ("[0]", "[1]", "[2]", "[3]", "[4]",
                                  "[5]", "[6]", "[7]", "[9]")))
    check("блока [8] в предпросмотре нет", "[8]" in txt, False)


def main() -> int:
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = []
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            failures.append((t.__name__, str(exc)))
        except Exception as exc:                     # noqa: BLE001
            failures.append((t.__name__, f"{type(exc).__name__}: {exc}"))
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




def test_rhyme_swap_keeps_word_count():
    """Подмена ради чистоговорки МЕНЯЕТ слово, а не добавляет.

    Иначе сдвинулось бы правило 11 (слоговой блок ≤ ¼ словесного) и лист мог
    бы перестать влезать в А4. Проверяем на звуках, где подмена реально
    случается (замер 08-08: 4 листа из 19).
    """
    for sound, typ in (("с", "direct"), ("з", "direct"), ("ш", "direct"),
                       ("л'", "direct")):
        c = C.build_content(sound=sound, syl_type=typ, profile=frozenset(),
                            sheet_no=1, n_words=16)
        n = sum(len(g["items"]) for g in (c.get("words") or {}).get("groups", []))
        check(f"[{sound}/{typ}] слов ровно столько, сколько просили", n, 16)


def test_chistogovorka_coverage_not_worse():
    """Сколько листов несут чистоговорку. Ниже этой планки — регресс.

    11 из 19 было до 08-08 · 16 стало после пополнения словаря, ударений
    мн. ч. и подмены ради рифмы.
    """
    built = 0
    for sound in sorted(C.WORDS_BY_SOUND):
        for typ in ("direct", "reverse"):
            try:
                c = C.build_content(sound=sound, syl_type=typ,
                                    profile=frozenset(), sheet_no=1)
            except Exception:
                continue
            if (c.get("chistogovorka") or {}).get("text"):
                built += 1
    check(f"чистоговорка строится не меньше чем на 16 листах (сейчас {built})",
          built >= 16, True)


def test_animacy_is_not_derived_from_topic():
    """Одушевлённость — признак слова, а не его темы.

    Ловушка, на которой сломался первый заход в предложения с глаголами:
    «животные/части» это ЛАПА, «птицы/части» это ПЕРО, а «сказка» держит и
    принцессу, и ЗАМОК. Печаталось «Замок заходит» и «Лапа ловит».
    """
    rows = {r["word"]: r for r in C.load_words(C._words_path("з", ""))}
    check("«заяц» живой", rows["заяц"]["animate"], True)
    check("«замок» НЕ живой", rows["замок"]["animate"], False)
    rows_r = {r["word"]: r for r in C.load_words(C._words_path("р", ""))}
    if "рыба" in rows_r:
        check("«рыба» живая", rows_r["рыба"]["animate"], True)
    for w in ("рама", "ракета", "рынок"):
        if w in rows_r:
            check(f"«{w}» не живой", rows_r[w]["animate"], False)


def test_verb_aspect_marked_everywhere():
    """У каждого глагола проставлен вид, и у совершенного форма — будущее.

    Без этого на листе смешивались времена: «Лиса летит» и «Медвежонок убежит».
    """
    import glob as _glob, json as _json, os as _os
    here = _os.path.dirname(_os.path.abspath(__file__))
    total = unmarked = 0
    for path in _glob.glob(_os.path.join(here, "verbs_*.jsonl")):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                v = _json.loads(line)
                total += 1
                if v.get("aspect") not in ("сов", "несов"):
                    unmarked += 1
                elif v["aspect"] == "сов":
                    check(f"«{v['word']}»: форма 3 л. названа будущим",
                          v.get("form_3sg_tense"), "будущее")
    check(f"вид проставлен у всех {total} глаголов", unmarked, 0)


def test_verb_sentences_are_sane():
    """Глагол в предложении: несовершенный вид, живое подлежащее, свой класс.

    Три ловушки, каждая печаталась на пробном заходе 08-08:
    «Медвежонок убежит» (совершенный вид — будущее время),
    «Замок заходит» (неживое подлежащее),
    «Рыба бегает» (класс подлежащего не тот).
    """
    import glob as _glob, json as _json, os as _os
    here = _os.path.dirname(_os.path.abspath(__file__))
    forms = {}
    for path in _glob.glob(_os.path.join(here, "verbs_*.jsonl")):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    v = _json.loads(line)
                    forms[v["form_3sg"]] = v
    for sound in ("р", "л", "с", "ж", "щ"):
        c = C.build_content(sound=sound, syl_type="direct",
                            profile=frozenset(), sheet_no=1)
        block4 = {w: True for w in c["vocabulary"]["block4"]}
        rows = {it["word"]: it for g in c["words"]["groups"] for it in g["items"]}
        for verb in c["vocabulary"]["verbs"]:
            v = forms.get(verb)
            truthy(f"[{sound}] глагол «{verb}» есть в картотеке", v)
            if not v:
                continue
            check(f"[{sound}] «{verb}» несовершенного вида", v["aspect"], "несов")
            truthy(f"[{sound}] «{verb}» имеет класс подлежащего", v["subject_classes"])
        for s in c["sentences"]["items"]:
            toks = C._tokens(s["text"])
            used = [t for t in toks if t in forms]
            if not used:
                continue
            subj = [t for t in toks if t in block4]
            truthy(f"[{sound}] «{s['text']}» имеет подлежащее из блока [4]", subj)
            for w in subj:
                row = rows.get(w)
                if row:
                    cls = C.subject_class({"semantic_category": row.get("semantic_category")})
                    truthy(f"[{sound}] подлежащее «{w}» живое", cls)
                    check(f"[{sound}] «{w}» подходит глаголу «{used[0]}»",
                          cls in forms[used[0]]["subject_classes"], True)


def test_phrases_material_is_agreed_and_clean():
    """Словосочетания — ОТДЕЛЬНЫЙ материал (`phrases.py`), ✅ Спивак.

    Проверяем ровно то, на чём материал стоит:
      • прилагательное согласовано по роду ФОРМОЙ ИЗ СЛОВАРЯ, не по хвосту;
      • обе части чисты по профилю ребёнка;
      • сочетаемость взята из таблицы, а не из правила по категории;
      • причастию и признаку внешности досталось СВОЁ подлежащее.
    """
    import phrases as F
    table = C.load_combinability()
    for sound in ("р", "с", "ш", "щ", "л"):
        p = F.build_phrases_sheet(sound=sound, n=12)
        check(f"[{sound}] словосочетаний на листе", p["meta"]["n"], 12)
        rows = {r["word"]: r for r in C.load_words(C._words_path(sound, None))}
        for it in p["items"]:
            noun = rows[it["noun"]]
            adj = next(a for a in C.load_adjectives(sound)
                       if a["word"] == it["adj_lemma"])
            check(f"[{sound}] «{it['text']}»: форма по роду из словаря",
                  it["adj"], C._agreed_form(adj, noun["gender"]))
            truthy(f"[{sound}] «{it['text']}»: класс сочетаемости разрешён",
                   it["noun_class"]
                   in table["adjective_classes"][it["comb_class"]]["fits"])
            truthy(f"[{sound}] «{it['text']}»: не тавтология",
                   not C._same_root(it["adj"], it["noun"]))
            allowed = (table["adjective_classes"][it["comb_class"]]
                       .get("subject_classes", {}).get(it["adj_lemma"]))
            if allowed:
                truthy(f"[{sound}] «{it['text']}»: подлежащее своего класса",
                       C.subject_class(noun) in allowed)


def test_phrases_respect_profile():
    """Профиль ребёнка режет ОБЕ части словосочетания, а не только слово."""
    import phrases as F
    profile = {"л", "ш", "ж"}
    p = F.build_phrases_sheet(sound="р", profile=profile, n=8)
    banned = C.banned_phonemes("р", profile)
    for it in p["items"]:
        for tok in C._tokens(it["text"]):
            check(f"«{it['text']}»: {tok} чист по профилю",
                  sorted(C.corrigible_of(tok) & banned), [])


def test_phrases_are_not_on_the_automation_sheet():
    """Лист автоматизации словосочетаний НЕ несёт: А4 переполнен, решение
    автора 08-09 — отдельный материал. Если блок вернётся на лист молча,
    сломается канонное правило 11 (замер в DECISIONS)."""
    c = C.build_content()
    check("на листе автоматизации блока словосочетаний нет",
          "phrases" in c, False)


def test_combinability_table_is_whole():
    """Таблица покрывает КАЖДОЕ прилагательное словаря — либо классом, либо
    строкой «не размечено». Без этого блок молча теряет слова, а мы думаем,
    что их нет. Ловушка поймана 08-08: правка по строке не применилась, и
    «сырой» оказался разом и в классе, и в неразмеченных."""
    import glob as _glob, json as _json, os as _os
    here = _os.path.dirname(_os.path.abspath(__file__))
    table = C.load_combinability()
    classed = {}
    dupes = []
    for cls, spec in table["adjective_classes"].items():
        for w in spec["words"]:
            if w in classed:
                dupes.append(w)
            classed[w] = cls
    unmarked = set(table["unmarked"]["words"])
    check("ни одно прилагательное не лежит в двух классах", dupes, [])
    check("класс и «не размечено» не пересекаются",
          sorted(set(classed) & unmarked), [])
    words = set()
    for path in _glob.glob(_os.path.join(here, "adjectives_*.jsonl")):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    words.add(_json.loads(line)["word"])
    check("каждое прилагательное словаря есть в таблице",
          sorted(words - set(classed) - unmarked), [])
    check("в таблице нет призраков (слов, которых нет в словаре)",
          sorted((set(classed) | unmarked) - words), [])
    # у каждого класса fits — непустой список известных классов существительных
    known = ({"живое", "предмет", "одежда", "игрушка", "растение", "тело",
              "часть-вещи", "плод", "еда", "блюдо", "напиток", "вода",
              "природа", "постройка", "вещество"})
    for cls, spec in table["adjective_classes"].items():
        truthy(f"класс «{cls}»: fits непуст", bool(spec["fits"]))
        check(f"класс «{cls}»: fits знает только известные классы",
              sorted(set(spec["fits"]) - known), [])


def test_noun_class_uses_animacy_not_topic():
    """Класс существительного считается по одушевлённости, а НЕ по полю
    записи: в блок [4] запись приходит урезанной. На этом 08-08 молча
    выпадало всё живое — щенок, щука, рак."""
    c = C.build_content(sound="щ", syl_type="direct")
    rows = {it["word"]: it for g in c["words"]["groups"] for it in g["items"]}
    for w in ("щенок", "щука"):
        if w in rows:
            truthy(f"«{w}» в урезанной записи всё равно живой",
                   "animate" not in rows[w])
            check(f"«{w}» — класс «живое»", C.noun_class(rows[w]), "живое")




def test_characters_are_drawn_not_written():
    """Персонаж звука на дорожках — РИСУНОК, а не слово.

    Поймано автором 08-09: обе дорожки печатали «мотор» текстом, и на детской
    половине листа не стояло ничего — ребёнок 5-7 лет не читает. Проверяем,
    что у каждого звука есть свой рисунок и что он попадает в печать."""
    import characters as CH
    import propisi as PR
    import track as TR
    for sound in C.WORDS_BY_SOUND:
        name = PR._image_for(sound).get("name") or ""
        truthy(f"[{sound}] у образа «{name}» есть рисунок", CH.has_character(name))
        svg = CH.character_svg(name, 30.0)
        # 08-21: герой стал ЦВЕТНЫМ по решению автора — прежнее «контур без
        # заливки» отменено (разведка поля: контурного персонажа в русской
        # традиции нет ни разу). Осталось то, что не менялось: рисунок есть,
        # он вписан в лист картинкой, и внутри него НЕТ текста — ребёнок
        # 5-7 лет не читает, надпись перетянула бы внимание.
        truthy(f"[{sound}] рисунок есть и вписан в лист",
               bool(svg) and ('<image' in svg or 'fill="none"' in svg))
        truthy(f"[{sound}] внутри рисунка нет текста",
               bool(svg) and "<text" not in svg)
        # умолчание — ч/б: лист печатают на обычном принтере, а цветная
        # заливка на нём садится ровным серым и глушит линии (замер 08-18)
        truthy(f"[{sound}] по умолчанию берётся ч/б, не цветной",
               bool(svg) and len(svg) < len(CH.character_svg(name, 30.0, colour=True) or "x" * 10**9))
    html = PR.render_propisi(PR.build_propisi("р", "direct"))
    truthy("звуковая дорожка печатает рисунок, а не слово «мотор»",
           "<svg class=\"chr\"" in html)
    html_t = TR.render_track(TR.build_track("р", "direct"))
    truthy("слоговая дорожка печатает рисунок", "<svg class=\"chr\"" in html_t)


def test_scene_sprite_raster_with_vector_fallback():
    """Спрайт сцены приходит картинкой, а нет картинки — рисуется вектором.

    Записано 08-22, когда сцена научилась класть растр. Проверяем ровно то, что
    может тихо сломаться: (1) при пустом банке сцена НЕ пустеет, а возвращается
    к вектору — иначе не доехавший в образ банк оставил бы логопеду голый лист;
    (2) при живом банке растр реально попадает в лист; (3) картинка отдаётся
    адресом, а не встраивается — «трава» кладёт полсотни предметов, и встраивание
    раздуло бы один лист на мегабайт.
    """
    import os
    import scenes as SC
    import track as TR

    h = TR._TOP + 5 * TR._ROW_H + TR._R + TR._AMP + 8.0
    avoid = TR._occupied(6, 5, 30, TR.shape_for("лес"))

    real_have = SC.have_sprite
    try:
        SC.have_sprite = lambda name: False          # банк «не доехал»
        empty = SC.scene_svg("лес", TR._W, h, avoid=avoid)
    finally:
        SC.have_sprite = real_have
    check("без банка сцена не пустеет", "<path" in empty, True)
    check("без банка растра нет", "<image" in empty, False)

    live = SC.scene_svg("лес", TR._W, h, avoid=avoid)
    if any(SC.have_sprite(n) for n in ("tree", "bush", "cloud", "mushroom")):
        check("с банком растр попадает в лист", "<image" in live, True)
        check("картинка отдаётся адресом, а не base64",
              "data:image" in live, False)
        check("бок о бок с вектором", "<path" in live, True)


def test_scene_is_chosen_and_never_absurd():
    """Фон — строка запроса Ольги «менять фон».

    С 08-10 фон это КОНТЕКСТ ГЕРОЯ, а не общий список: у каждого героя два своих
    мира, и чужой мир движок не принимает. Проверяем: умолчание — первый мир
    героя, свой мир принимается, «без фона» законно, чужой и несуществующий —
    отказ вслух.
    """
    import scenes as SC
    import track as TR
    for sound, expect in (("р", "дорога"), ("л", "небо"), ("ш", "трава")):
        t = TR.build_track(sound, "direct")
        check(f"[{sound}] фон по умолчанию", t["meta"]["scene"], expect)
    t = TR.build_track("р", "direct", scene="город")
    check("логопед переопределяет умолчание", t["meta"]["scene"], "город")
    t0 = TR.build_track("р", "direct", scene="")
    check("«без фона» — законный выбор, а не сбой", t0["meta"]["scene"], "")
    try:
        TR.build_track("р", "direct", scene="марс")
        check("несуществующий фон отвергнут вслух", False, True)
    except TR.TrackError:
        check("несуществующий фон отвергнут вслух", True, True)
    try:
        # «море» существует, но это мир самолёта: мотор под водой — та самая
        # нелепица, ради которой миры и заведены.
        TR.build_track("р", "direct", scene="море")
        check("чужой мир отвергнут вслух", False, True)
    except TR.TrackError:
        check("чужой мир отвергнут вслух", True, True)
    # Сцена не должна перекрывать слоги: внутри SVG МАРШРУТА она обязана идти
    # первым слоем. Считаем позиции только внутри маршрута — иначе первым
    # <circle> в документе оказывается глаз змеи в рисунке персонажа.
    html = TR.render_track(TR.build_track("ш", "direct"))
    route = html[html.find('class="route"'):]
    # Ищем слой сцены по его подписи, а не по конкретной прозрачности: она
    # менялась (0.30 → 0.42 в 08-10, чтобы сцены читались) и будет меняться.
    i_scene, i_circle = route.find('opacity="0.'), route.find('fill="#fff"')
    truthy("сцена нарисована ДО кружков (иначе закроет слоги)",
           0 <= i_scene < i_circle)




def test_counting_game_is_alive_and_tabled():
    """«Посчитай 1-5» — третья канонная игра (ТЗ, ЯРУС А).

    До 2026-08-10 она не собиралась НИ НА ОДНОМ листе: формы родительного
    падежа были выверены у 23 слов из 1760, а правило падежей выключено
    08-08 как врущее («пять стулов», «два угола»). Игра числилась
    существующей, не существуя. Тест держит два условия: она собирается,
    и каждая форма приходит ИЗ ТАБЛИЦЫ, а не из правила.
    """
    built = 0
    checked = 0
    for sound in C.WORDS_BY_SOUND:
        for typ in ("direct", "reverse", "intervocal"):
            try:
                c = C.build_content(sound=sound, syl_type=typ,
                                    game_kind="count_1_5")
            except C.ContentError:
                continue
            g = c.get("game") or {}
            if g.get("kind") != "count_1_5":
                continue
            built += 1
            for row in g["items"]:
                w = row["prompt"]
                checked += 1
                truthy(f"«{w}»: форма ед. ч. взята из таблицы",
                       w in C.GEN_SG_OVERRIDES)
                truthy(f"«{w}»: форма мн. ч. взята из таблицы",
                       w in C.GEN_PL_OVERRIDES)
    truthy(f"игра собирается больше чем на половине листов ({built})", built >= 15)
    truthy(f"проверено форм: {checked}", checked > 50)
    # ловушки, на которых правило врало
    for w, sg, pl in (("стул", "стула", "стульев"), ("угол", "угла", "углов"),
                      ("ёж", "ежа", "ежей"), ("поросёнок", "поросёнка", "поросят"),
                      ("барашек", "барашка", "барашков")):
        check(f"«{w}» ед. ч.", C.GEN_SG_OVERRIDES.get(w), sg)
        check(f"«{w}» мн. ч.", C.GEN_PL_OVERRIDES.get(w), pl)
    # «сук» намеренно исключён: «два сука» на листе, читаемом вслух
    check("«сук» в таблицу не включён", "сук" in C.GEN_PL_OVERRIDES, False)


if __name__ == "__main__":
    sys.exit(main())
