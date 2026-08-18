# -*- coding: utf-8 -*-
"""
test_maze.py — проверки генератора страницы-лабиринта 3×3.

Запуск:  python3 test_maze.py         (свой раннер, без зависимостей)
         pytest test_maze.py          (тоже работает)

Проверяется не «красиво ли», а обещания модуля:
чистота по звукам · позиция звука · гамильтонов маршрут · 9 клеток ·
разнообразие набора · детерминированность по seed · недобор не молчит ·
сторожа ПАДАЮТ на подложенном браке (иначе они декорация).
"""

from __future__ import annotations

import re
import sys

import phonetics as ph
import content as C
import maze as M

_results = []


def check(name, actual, expected):
    ok = actual == expected
    _results.append((ok, name, actual, expected))
    assert ok, f"{name}: получили {actual!r}, ждали {expected!r}"
    return ok


def truthy(name, actual):
    return check(name, bool(actual), True)


PROFILE = {"ш", "ж"}
HEAVY = {"ш", "ж", "с", "з", "ц", "щ", "ч"}


def build(**kw):
    kw.setdefault("profile", PROFILE)
    return M.build_maze(**kw)


def pictures(m):
    return [c for c in m["cells"] if c["kind"] == "picture"]


# ═══════════════════════════════════════════════════════════════════════
#  A. СЕТКА И МАРШРУТ
# ═══════════════════════════════════════════════════════════════════════

def test_nine_cells_exactly():
    m = build()
    check("клеток ровно 9", len(m["cells"]), 9)
    check("координаты покрывают всю сетку 3×3",
          sorted((c["row"], c["col"]) for c in m["cells"]),
          [(r, c) for r in range(3) for c in range(3)])
    check("номера по маршруту 1..9",
          sorted(c["order"] for c in m["cells"]), list(range(1, 10)))


def test_all_routes_are_hamiltonian():
    for name, path in M.ROUTES.items():
        M.verify_route(path)                 # бросит на любом нарушении
        check(f"маршрут {name}: 9 клеток", len(set(path)), 9)
    check("маршрутов в наборе", len(M.ROUTES) >= 5, True)


def test_verify_route_falls_on_broken_path():
    broken = [(0, 0), (0, 1), (0, 2), (2, 2), (1, 2), (1, 1), (1, 0), (2, 0), (2, 1)]
    try:
        M.verify_route(broken)
        check("сторож маршрута упал на диагональном шаге", "не упал", "RouteViolation")
    except M.RouteViolation:
        check("сторож маршрута упал на диагональном шаге", "RouteViolation", "RouteViolation")
    try:
        M.verify_route([(0, 0), (0, 1)])
        check("сторож маршрута упал на короткому пути", "не упал", "RouteViolation")
    except M.RouteViolation:
        check("сторож маршрута упал на короткому пути", "RouteViolation", "RouteViolation")


def test_star_marks_start_and_start_is_a_picture():
    m = build()
    start = min(m["cells"], key=lambda c: c["order"])
    check("старт — первая клетка маршрута", start["order"], 1)
    check("старт совпадает с началом пути",
          [start["row"], start["col"]], m["route"]["start"])
    check("на старте картинка, а не «?» (фишку ставить некуда)",
          start["kind"], "picture")


def test_directions_match_path():
    m = build()
    path = [tuple(p) for p in m["route"]["path"]]
    dirs = m["route"]["directions"]
    check("направлений на одно меньше клеток", len(dirs), len(path) - 1)
    for i, d in enumerate(dirs):
        check(f"направление шага {i} выведено из пути",
              M._direction(path[i], path[i + 1]), d)


# ═══════════════════════════════════════════════════════════════════════
#  B. ЧИСТОТА (главное обещание проекта)
# ═══════════════════════════════════════════════════════════════════════

def test_all_words_clean_for_profile():
    for profile in (set(), PROFILE, HEAVY):
        for position in ("initial", "medial", "final"):
            m = M.build_maze(position=position, profile=profile, seed=3)
            banned = frozenset(m["meta"]["banned"])
            for c in pictures(m):
                dirty = C.corrigible_of(c["word"], c["stress_syllable"]) & banned
                check(f"«{c['word']}» чисто при профиле {sorted(profile)}/{position}",
                      sorted(dirty), [])


def test_banned_always_holds_l_and_soft_twin():
    m = build()
    b = set(m["meta"]["banned"])
    check("Л запрещён при цели Р", "л" in b, True)
    check("Рь запрещён (мягкий близнец цели)", "р'" in b, True)
    check("сама цель Р не запрещена", "р" in b, False)
    check("Ш из профиля запрещён", "ш" in b, True)


def test_purity_guard_falls_on_planted_dirt():
    m = build()
    m["cells"][0].update(kind="picture", word="лужа", stress_syllable=1,
                         transcription="[лужа]", order=m["cells"][0]["order"])
    try:
        M.verify_purity(m)
        check("сторож чистоты упал на подложенном «лужа»", "не упал", "PurityViolation")
    except M.PurityViolation:
        check("сторож чистоты упал на подложенном «лужа»",
              "PurityViolation", "PurityViolation")


def test_purity_guard_falls_on_wrong_position():
    """«корова» чиста по профилю, но [р] у неё в СЕРЕДИНЕ — на листе initial
    это брак, и сторож обязан его поймать."""
    m = M.build_maze(position="initial", profile=PROFILE, seed=0)
    m["cells"][0].update(kind="picture", word="корова", stress_syllable=2,
                         transcription="[карова]")
    try:
        M.verify_purity(m)
        check("сторож поймал слово с неверной позицией звука",
              "не упал", "PurityViolation")
    except M.PurityViolation:
        check("сторож поймал слово с неверной позицией звука",
              "PurityViolation", "PurityViolation")


def test_target_sound_in_requested_position():
    for position in ("initial", "medial", "final"):
        m = M.build_maze(position=position, profile=PROFILE, seed=1)
        for c in pictures(m):
            a = ph.analyze(c["word"], c["stress_syllable"])
            hit = any(o["phoneme"] == "р" and o["position"] == position
                      for o in a.sound_occurrences)
            check(f"«{c['word']}»: [р] в позиции {position}", hit, True)


def test_derived_forms_in_games_are_clean():
    m = M.build_maze(position="medial", profile=HEAVY, seed=5)
    banned = frozenset(m["meta"]["banned"])
    for g in m["tasks"]["games"]:
        for it in g.get("items", []):
            if isinstance(it, dict) and it.get("answer"):
                for tok in str(it["answer"]).replace("—", " ").split():
                    check(f"форма «{tok}» игры «{g['title']}» чиста",
                          sorted(C.corrigible_of(tok) & banned), [])


def test_route_directions_are_clean_words():
    """Слово «влево» несёт [л] — для цели [р] это грязь. Маршрут обязан
    выбираться так, чтобы режим «С направлением» проговаривался чисто."""
    m = build()
    banned = frozenset(m["meta"]["banned"])
    check("маршрут выбран с чистыми направлениями",
          m["route"]["speak_directions"], True)
    for d in m["route"]["directions_ru"]:
        check(f"направление «{d}» чисто", C.is_clean(d, banned), True)


def test_dirty_route_switches_mode_two_to_gesture():
    m = M.build_maze(position="initial", profile=PROFILE, seed=0,
                     route="snake_rows")               # в нём есть ход «влево»
    check("ручной грязный маршрут помечен", m["route"]["speak_directions"], False)
    check("предупреждение о грязных направлениях есть",
          any("показ рукой" in w for w in m["warnings"]), True)
    m2 = [x for x in m["tasks"]["modes"] if x["n"] == 2][0]
    check("режим 2 переведён на показ рукой", "ПОКАЗЫВАЕТ" in m2["text"], True)


# ═══════════════════════════════════════════════════════════════════════
#  C. СЛУЖЕБНАЯ КЛЕТКА
# ═══════════════════════════════════════════════════════════════════════

def test_service_question():
    m = build(service_cell="question")
    svc = [c for c in m["cells"] if c["kind"] == "question"]
    check("служебная клетка ровно одна", len(svc), 1)
    check("картинок 8", len(pictures(m)), 8)
    check("подпись зовёт придумать слово", "придумай" in svc[0]["caption"], True)


def test_service_scheme():
    m = build(service_cell="scheme")
    svc = [c for c in m["cells"] if c["kind"] == "scheme"]
    check("схема ровно одна", len(svc), 1)
    check("картинок 8", len(pictures(m)), 8)
    html = M.render_maze(m)
    check("в схеме помечена буква цели", ">Р<" in html, True)


def test_service_none_gives_nine_pictures():
    m = build(service_cell="none", position="medial")
    check("без служебной клетки картинок 9", len(pictures(m)), 9)


def test_bad_service_kind_raises():
    try:
        build(service_cell="звёздочка")
        check("неизвестная служебная клетка отвергнута", "не упало", "MazeError")
    except M.MazeError:
        check("неизвестная служебная клетка отвергнута", "MazeError", "MazeError")


# ═══════════════════════════════════════════════════════════════════════
#  D. РАЗНООБРАЗИЕ НАБОРА
# ═══════════════════════════════════════════════════════════════════════

def test_no_nine_animals_in_a_row():
    for position in ("initial", "medial", "final"):
        for seed in (0, 1, 2):
            m = M.build_maze(position=position, profile=PROFILE, seed=seed)
            cats = {}
            for c in pictures(m):
                cats[c["category"]] = cats.get(c["category"], 0) + 1
            worst = max(cats.values())
            relaxed = any("разнообразие: порог" in w for w in m["warnings"])
            check(f"{position}/{seed}: не более {M.MAX_PER_CATEGORY} слов одной "
                  f"категории (или порог ослаблен вслух)",
                  worst <= M.MAX_PER_CATEGORY or relaxed, True)


def test_vowel_spread():
    m = M.build_maze(position="initial", profile=PROFILE, seed=0)
    vowels = {c["vowel"] for c in pictures(m)}
    check("гласных у целевого звука больше одной", len(vowels) >= 2, True)


def test_no_duplicate_words():
    for seed in range(4):
        m = M.build_maze(position="medial", profile=PROFILE, seed=seed)
        words = [c["word"] for c in pictures(m)]
        check(f"seed={seed}: слова не повторяются", len(set(words)), len(words))


def test_ambiguous_pictures_are_out_by_default():
    m = M.build_maze(position="medial", profile=PROFILE, seed=0)
    check("слов с неоднозначной картинкой нет",
          [c["word"] for c in pictures(m) if c["ambiguous"]], [])


# ═══════════════════════════════════════════════════════════════════════
#  E. ЗАДАНИЯ ВЗРОСЛОМУ
# ═══════════════════════════════════════════════════════════════════════

def test_four_modes_always():
    m = build()
    check("режимов ходьбы ровно 4", len(m["tasks"]["modes"]), 4)
    check("названия режимов — канон",
          [x["title"] for x in m["tasks"]["modes"]], list(M.MODES))


def test_mode_one_carries_the_rule_of_the_wrong_word():
    m = build()
    t = m["tasks"]["modes"][0]["text"]
    check("режим 1 несёт правило «пока не будет названо верно»",
          "пока слово не будет названо верно" in t, True)


def test_mode_three_is_every_second_picture():
    m = build()
    order = [c["speak"] for c in sorted(m["cells"], key=lambda c: c["order"])]
    t = m["tasks"]["modes"][2]["text"]
    for w in order[::2]:
        check(f"«через одну» содержит {w}", w in t, True)


def test_mode_four_is_reversed():
    m = build()
    order = [c["speak"] for c in sorted(m["cells"], key=lambda c: c["order"])]
    t = m["tasks"]["modes"][3]["text"]
    chain = [x.strip(" .") for x in t.split(": ", 1)[1].split(" · ")]
    check("режим 4 — весь набор задом наперёд", chain, order[::-1])


def test_games_count_and_syllables_from_engine():
    m = build()
    check("надстроечных игр 2-3", 2 <= len(m["tasks"]["games"]) <= 3, True)
    stress = {c["word"]: c["stress_syllable"] for c in pictures(m)}
    claps = [g for g in m["tasks"]["games"] if g["kind"] == "claps"]
    if claps:
        for it in claps[0]["items"]:
            check(f"хлопков у «{it['word']}» = слогов движка",
                  it["n"], ph.analyze(it["word"], stress[it["word"]]).n_syllables)


def test_claps_always_buildable():
    g = M._game_claps(pictures(build()))
    check("«Хлопушки» строятся всегда", bool(g), True)


def test_missing_game_switches_to_one_word_answer_for_r():
    """Для цели [р] рамка «не стало» несёт запрещённый [л] — игра обязана
    перейти на однословный ответ, а не притвориться чистой."""
    banned = C.banned_phonemes("р", PROFILE)
    g = M._game_missing(pictures(build()), banned)
    check("ответ переведён на одно слово", "ОДНИМ СЛОВОМ" in g["text"], True)
    check("причина названа вслух", any("рамка" in n for n in g["_notes"]), True)


def test_games_only_use_words_from_this_page():
    m = M.build_maze(position="medial", profile=PROFILE, seed=2)
    on_page = {c["word"] for c in pictures(m)}
    for g in m["tasks"]["games"]:
        for it in g.get("items", []):
            if isinstance(it, dict) and "prompt" in it:
                check(f"«{it['prompt']}» из набора страницы",
                      it["prompt"] in on_page, True)
            elif isinstance(it, str):
                check(f"«{it}» из набора страницы", it in on_page, True)


def test_count_game_skips_fleeting_vowel_words():
    """«рынок» → род. мн. правилом не берётся (беглая гласная). Игра обязана
    его пропустить, а не напечатать «пять рыноков»."""
    m = M.build_maze(position="initial", profile=PROFILE, seed=0)
    for g in m["tasks"]["games"]:
        if g["kind"] == "count_1_5":
            check("«рыноков» на листе нет", "рыноков" in g["text"], False)
            check("«ковёров» на листе нет", "ковёров" in g["text"], False)


# ═══════════════════════════════════════════════════════════════════════
#  F. ДЕТЕРМИНИРОВАННОСТЬ И НЕДОБОР
# ═══════════════════════════════════════════════════════════════════════

def test_same_seed_same_maze():
    a = M.build_maze(position="medial", profile=PROFILE, seed=7)
    b = M.build_maze(position="medial", profile=PROFILE, seed=7)
    check("слова совпадают",
          [c["speak"] for c in a["cells"]], [c["speak"] for c in b["cells"]])
    check("маршрут совпадает", a["route"]["name"], b["route"]["name"])
    check("игры совпадают",
          [g["title"] for g in a["tasks"]["games"]],
          [g["title"] for g in b["tasks"]["games"]])
    check("HTML совпадает байт в байт", M.render_maze(a), M.render_maze(b))


def test_different_seed_different_maze():
    seen = {tuple(c["speak"] for c in sorted(M.build_maze(
        position="medial", profile=PROFILE, seed=s)["cells"],
        key=lambda c: c["order"])) for s in range(5)}
    check("разные seed дают разные наборы", len(seen) >= 2, True)


def test_shortfall_raises_with_actionable_hint():
    """Профиль, выкашивающий почти всё: лабиринт не собрать — и модуль обязан
    сказать, чем расширять, а не молча выдать пустые клетки."""
    killer = {"с", "з", "т", "д", "к", "г", "ш", "ж", "ц", "ч", "щ", "б", "п", "в", "ф"}
    try:
        M.build_maze(position="final", profile=killer, seed=0)
        check("невозможный лабиринт отвергнут", "не упало", "MazeError")
    except M.MazeError as exc:
        check("невозможный лабиринт отвергнут", "MazeError", "MazeError")
        check("в сообщении есть, чем расширять", "чем расширить" in str(exc), True)


def test_warnings_are_human_readable():
    m = M.build_maze(position="initial", profile=PROFILE, seed=0,
                     route="snake_rows")
    truthy("предупреждения — непустые строки",
           all(isinstance(w, str) and len(w) > 10 for w in m["warnings"]))


def test_cell_smaller_than_canon_raises():
    try:
        build(cell_mm=40)
        check("клетка меньше 55 мм отвергнута", "не упало", "MazeError")
    except M.MazeError:
        check("клетка меньше 55 мм отвергнута", "MazeError", "MazeError")


def test_bad_position_raises():
    try:
        build(position="везде")
        check("неизвестная позиция отвергнута", "не упало", "MazeError")
    except M.MazeError:
        check("неизвестная позиция отвергнута", "MazeError", "MazeError")


# ═══════════════════════════════════════════════════════════════════════
#  G. ПЕЧАТЬ
# ═══════════════════════════════════════════════════════════════════════

def test_html_has_nine_cells_and_eight_arrows():
    html = M.render_maze(build())
    check("клеток в HTML 9", html.count('class="cell"'), 9)
    check("стрелок 8", html.count("<line "), 8)
    check("наконечников 8 + звезда", html.count("<polygon "), 9)


def test_html_geometry_is_a4_and_cells_are_canon():
    m = build()
    html = M.render_maze(m)
    check("страница A4", "size: A4" in html, True)
    check("клетка 55 мм", "width: 55mm" in html, True)
    check("сетка влезает в полосу набора",
          3 * m["meta"]["cell_mm"] + 2 * M.GAP_MM <= 180.0, True)


def test_word_caption_is_under_every_picture():
    m = build()
    html = M.render_maze(m)
    for c in pictures(m):
        check(f"подпись «{c['word']}» на листе",
              c["caption"].replace("́", "") in html.replace("́", ""), True)


def test_render_image_is_the_single_swap_point():
    # Слово, которого в банке картинок заведомо нет → плейсхолдер
    frag = M.render_image("зззз")
    check("плейсхолдер — самодостаточный svg", frag.startswith("<svg"), True)
    check("в нём есть слово", ">зззз<" in frag, True)
    check("и честная пометка «картинка»", "[картинка]" in frag, True)
    check("рамка пунктирная (сигнал «не готово»)", "stroke-dasharray" in frag, True)
    check("viewBox один на все клетки",
          f'viewBox="0 0 {M.PIC_VB_W:g} {M.PIC_VB_H:g}"' in frag, True)


def test_real_picture_replaces_placeholder():
    """Есть картинка в банке — клетка показывает её, а не рамку со словом."""
    if not M.has_picture("рак"):
        check("банк картинок пуст — проверка пропущена", True, True)
        return
    frag = M.render_image("рак")
    # Формат не важен: чужой банк лежит в jpeg, свои картинки — png (08-18).
    check("картинка встроена в svg",
          ("data:image/jpeg;base64," in frag or "data:image/png;base64," in frag), True)
    check("плейсхолдера больше нет", "[картинка]" in frag, False)
    check("страница самодостаточна (нет ссылок наружу)",
          "http" in frag.split("base64,")[0], False)
    check("слово осталось для чтения с экрана", 'aria-label="рак"' in frag, True)
    check("viewBox тот же", f'viewBox="0 0 {M.PIC_VB_W:g} {M.PIC_VB_H:g}"' in frag, True)


def test_warnings_hidden_from_paper():
    m = M.build_maze(position="initial", profile=PROFILE, seed=0,
                     route="snake_rows")
    html = M.render_maze(m)
    check("предупреждения есть на экране", "warnbox" in html, True)
    check("и скрыты при печати", "screen-only" in html, True)


def test_no_fills_except_marks():
    """Ч/б печать: заливок нет, кроме чёрных пометок (стрелка, звезда) и белой
    подложки под звездой."""
    html = M.render_maze(build())
    fills = set(re.findall(r'fill="([^"]+)"', html))
    check("заливки только чёрная/белая/none", fills - {"#000", "#fff", "none", "#555"}, set())


def test_tasks_fit_the_page_model():
    for position in ("initial", "medial", "final"):
        m = M.build_maze(position=position, profile=PROFILE, seed=0)
        check(f"{position}: блок заданий влезает в бюджет",
              m["meta"]["tasks_mm"] <= m["meta"]["tasks_budget_mm"], True)


def test_preview_covers_all_blocks():
    txt = M.render_preview(build())
    for token in ("ДОРОЖКА", "СЕТКА", "ПО МАРШРУТУ", "НАПРАВЛЕНИЯ", "ЗАДАНИЯ ВЗРОСЛОМУ"):
        check(f"в предпросмотре есть «{token}»", token in txt, True)


def test_cli_writes_file(tmp="/tmp/_maze_cli_test.html"):
    rc = M.main(["--sound", "р", "--position", "initial", "--profile", "ш,ж",
                 "--out", tmp])
    check("CLI вернул 0", rc, 0)
    with open(tmp, encoding="utf-8") as f:
        html = f.read()
    check("CLI написал лист", html.count('class="cell"'), 9)


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
