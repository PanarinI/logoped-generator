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
    check("Й запрещён (правило 2, канон листа)", "й" in b, True)
    check("Рь запрещён (мягкий близнец цели)", "р'" in b, True)
    check("сама цель Р не запрещена", "р" in b, False)
    check("Ш из профиля запрещён", "ш" in b, True)


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


def test_sentences_use_only_block4_nouns():
    c = build()
    allowed = set(c["vocabulary"]["block4"]) | set(c["vocabulary"]["service"])
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


def test_all_three_games_reachable():
    kinds = set()
    for seed in range(6):
        for sheet in (1, 2, 3):
            kinds.add(build(seed=seed, sheet_no=sheet, n_words=24)["game"]["kind"])
    check("доступны все три игры", kinds, set(C.GAME_KINDS))


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
    check("рама: род. ед.", C._gen_sg("рама", "f"), "рамы")
    check("рама: род. мн.", C._gen_pl("рама", "f"), "рам")
    check("комар: род. ед.", C._gen_sg("комар", "m"), "комара")
    check("комар: род. мн.", C._gen_pl("комар", "m"), "комаров")
    check("ведро: род. ед.", C._gen_sg("ведро", "n"), "ведра")
    check("ведро: род. мн. (по таблице)", C._gen_pl("ведро", "n"), "вёдер")
    check("парта: род. мн. без беглой гласной", C._gen_pl("парта", "f"), "парт")
    check("марка: род. мн. с беглой О", C._gen_pl("марка", "f"), "марок")
    check("ручка: род. мн. с беглой Е", C._gen_pl("ручка", "f"), "ручек")
    check("рот: род. ед. по таблице", C._gen_sg("рот", "m"), "рта")
    check("рынок: беглая гласная — только по таблице",
          C._gen_sg("рынок", "m"), "рынка")
    check("ветер: беглая гласная — только по таблице",
          C._gen_sg("ветер", "m"), "ветра")
    check("неизвестное на -ец правило не выдумывает",
          C._gen_sg("ранец", "m"), "ранца")
    check("ок-слово вне таблицы даёт None", C._gen_sg("горшок", "m"), "горшка")
    check("средний род вне таблицы: род. мн. = None",
          C._gen_pl("болото", "n"), None)


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
    check("словарь загружен целиком", len(rows), 162)
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


if __name__ == "__main__":
    sys.exit(main())
