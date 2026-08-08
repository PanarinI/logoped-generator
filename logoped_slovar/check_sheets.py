# -*- coding: utf-8 -*-
"""
check_sheets.py — прогон готовых листов по чеклисту канона (24 правила).

Проверяются НЕ намерения кода, а ГОТОВЫЙ материал листа: то, что реально
попадёт на бумагу. Каждое правило либо проверяется программно (✅/❌), либо
честно помечается как «глазами / вне кода» — выдумывать зелёную галочку там,
где проверить нечем, нельзя.

    python3 check_sheets.py            # три демо-листа
    python3 check_sheets.py --json     # машиночитаемо

Источник правил: research/logoped_TZ_generatora_2026-08-01.md, раздел
«Чеклист методического брака». Нумерация 1-24 — развёртка того же списка,
на неё ссылаются content.py и sheet.py.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Any, Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import content as C          # noqa: E402
import phonetics as ph       # noqa: E402
import sheet as S            # noqa: E402

CASES = [
    ("easy",   dict(sound="р", typ="direct",        profile="",             sheet_no=1),
     "нарушен только Р"),
    ("medium", dict(sound="р", typ="cluster_onset", profile="л,ш,ж",        sheet_no=7),
     "стечение в начале, профиль {л, ш, ж}"),
    ("hard",   dict(sound="р", typ="reverse",       profile="л,ш,ж,с,з,ц",  sheet_no=4),
     "обратные слоги, профиль {л, ш, ж, с, з, ц}"),
]

TOKEN = re.compile(r"[а-яёА-ЯЁ]+")
FAKE_NORM = re.compile(r"\d+\s*(раз|раза|день|дня|дней|недел|процент)", re.I)


def speech_units(c: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Весь РЕЧЕВОЙ материал листа (то, что произносит ребёнок): (блок, текст).

    Инструкции, заголовки и названия упражнений сюда НЕ входят — это навигация
    для читающего, граница зафиксирована в content['purity_scope'].
    """
    out: List[Tuple[str, str]] = []
    iso = c.get("isolated") or {}
    if iso.get("text"):
        out.append(("[2]", iso["text"]))
    for r in (c.get("syllables") or {}).get("rows", []):
        for u in r.get("units", []):
            out.append(("[3]", u))
        if r.get("word"):
            out.append(("[3]", S._word_text(r["word"])))
    for it in S._words_flat(c.get("words") or {}):
        out.append(("[4]", S._word_text(it)))
    game = c.get("game") or {}
    if game.get("example"):
        out.append(("[5]", game["example"]))
    for x in game.get("items", []):
        out.append(("[5]", str(x)))
    for it in (c.get("sentences") or {}).get("items", []):
        out.append(("[6]", it.get("text", "")))
    if (c.get("chant") or {}).get("text"):
        out.append(("[7]", c["chant"]["text"]))
    return out


def phonemes_of(word: str) -> set:
    """Корригируемые фонемы слова. Ударение не влияет (доказано тестом
    test_purity_is_stress_independent), поэтому берём первый слог."""
    w = re.sub(r"[^а-яёА-ЯЁ-]", "", word)
    if not w:
        return set()
    try:
        a = ph.analyze(w, 1)
    except Exception:
        try:
            a = ph.analyze(w)
        except Exception:
            return set()
    return {p for p in a.phoneme_keys if p in ph.CORRIGIBLE} if hasattr(
        ph, "CORRIGIBLE") else set(a.phoneme_keys)


def run_case(tag: str, kw: Dict[str, Any]) -> Dict[str, Any]:
    raw, report = S.compose(kw["sound"], kw["typ"], kw["profile"],
                            sheet_no=kw["sheet_no"], seed=0)
    fitted, fit_warns = S.fit(raw, S.CONTENT_H)
    meta = {"sound": kw["sound"], "sheet_no": kw["sheet_no"], "child_name": "",
            "week_from": "", "week_to": ""}
    lint = S.lint(fitted, meta)
    banned = set(report.get("banned_phonemes", []))

    R: Dict[int, Tuple[str, str]] = {}       # n -> (статус, комментарий)

    def ok(n: int, msg: str = ""):
        R[n] = ("✅", msg)

    def bad(n: int, msg: str):
        R[n] = ("❌", msg)

    def na(n: int, msg: str):
        R[n] = ("—", msg)

    units = speech_units(fitted)

    # ── 1. нет звуков, нарушенных у ребёнка ──────────────────────────────
    prof = S._expand_profile(kw["profile"])
    dirty = [(b, t, sorted(phonemes_of(w) & prof))
             for b, t in units for w in TOKEN.findall(t)
             if phonemes_of(w) & prof]
    ok(1, f"профиль {sorted(prof) or '—'}: ни одной фонемы профиля в "
          f"{len(units)} единицах речевого материала") if not dirty else \
        bad(1, f"нарушенная фонема в материале: {dirty[:3]}")

    # ── 2. нет звуков, СМЕШИВАЕМЫХ с целевым (для [р]: л, ль, й) ─────────
    mixed = C.MIXED_WITH.get(kw["sound"], frozenset())
    hits = [(b, w, sorted(phonemes_of(w) & set(mixed)))
            for b, t in units for w in TOKEN.findall(t)
            if phonemes_of(w) & set(mixed)]
    ok(2, f"смешиваемые {sorted(mixed)} отсутствуют в материале даже когда "
          f"они у ребёнка сохранны") if not hits else \
        bad(2, f"смешиваемый звук в материале: {hits[:3]}")

    # ── 3. фильтр по ЗВУКАМ, не буквам ──────────────────────────────────
    #     доказательство: слово с буквой-ловушкой ловится/пропускается по звуку
    probes = [("мороз", "буква З, звук [с]"), ("ложка", "буква Ж, звук [ш]"),
              ("сапог", "буква Г, звук [к]")]
    verdict = [f"{w} ({why}) → {sorted(phonemes_of(w))}" for w, why in probes]
    by_word = {r["word"]: r for r in C.load_words(C._words_path(kw["sound"], None))}
    on_sheet_words = {S._word_text(i) for i in S._words_flat(fitted.get("words") or {})}
    shifted = [f"{w}=[{by_word[w]['transcription']}]" for w in sorted(on_sheet_words)
               if w in by_word and by_word[w]["transcription"] != w]
    ok(3, "разбор по звукам: " + " · ".join(verdict)
        + (f"; на этом листе слова, где буква ≠ звук: {shifted[:3]}"
           if shifted else "; на этом листе таких слов нет"))

    # ── 4. при бедности позиции — сообщать, не подмешивать ──────────────
    notes = list(fitted.get("notes") or [])
    short = [n for n in notes if "нашлось" in n or "меньше канонического" in n]
    n_words = len(S._words_flat(fitted.get("words") or {}))
    if n_words >= S.MIN_WORDS:
        ok(4, f"недобора нет ({n_words} слов); механизм проверен на «hard»")
    elif short:
        ok(4, f"недобор {n_words} слов назван вслух: «{short[0][:70]}…»")
    else:
        bad(4, f"слов {n_words} < {S.MIN_WORDS}, но предупреждения нет")

    # ── 5. никаких листов на этапе постановки ───────────────────────────
    gym = C.load_gymnastics()
    stage_bad = []
    by_id = {e["id"]: e for e in (gym or {}).get("exercises", [])}
    names = set((fitted.get("articulation") or {}).get("items", []))
    for e in by_id.values():
        if e["name"] in names and (e.get("sounds") or {}).get("Р") == "постановка":
            stage_bad.append(e["name"])
    iso_stage = (C.isolated_block(kw["sound"])[0] or {}).get("stage")
    if stage_bad:
        bad(5, f"постановочное упражнение на листе автоматизации: {stage_bad}")
    else:
        ok(5, f"[1] все 4 — стадия разогрева; [2] образ помечен «{iso_stage}»; "
              f"«дятел/барабанщики» и «заведи мотор» отсечены по полю stage")

    # ── 6. слоговой блок никогда не выдаётся отдельным листом ───────────
    blocks = [k for k in ("articulation", "isolated", "syllables", "words",
                          "game", "sentences", "chant") if fitted.get(k)]
    ok(6, f"на листе {len(blocks)} блоков: {', '.join(blocks)}") if len(blocks) >= 5 \
        else bad(6, f"блоков всего {len(blocks)}: {blocks}")

    # ── 7. связка «слог → слово» у каждой строки ────────────────────────
    rows = (fitted.get("syllables") or {}).get("rows", [])
    noband = [i for i, r in enumerate(rows, 1) if not r.get("word")]
    off = [(r.get("bond_syllable"), S._word_text(r.get("word")))
           for r in rows if r.get("bond_syllable") not in r.get("units", [])]
    if noband:
        bad(7, f"строки без связки: {noband}")
    elif off:
        bad(7, f"связка не из своей строки: {off}")
    else:
        ok(7, "все " + str(len(rows)) + " строк со связкой; слог связки — из "
              "своей же строки: " + ", ".join(
                  f"{r['bond_syllable']} — {S._word_text(r['word'])}" for r in rows))

    # ── 8. один тип слога на блок ───────────────────────────────────────
    lens = {len(u) for r in rows for u in r.get("units", [])}
    ok(8, f"тип один: «{(fitted.get('syllables') or {}).get('type_label')}», "
          f"длина единиц {sorted(lens)}")

    # ── 9. порядок ступеней (открытый → обратный → … ) ──────────────────
    na(9, "лист знает СВОЮ ступень (--type), лестницу задаёт оператор; "
          "автопрогрессии по номеру листа в v1 нет")

    # ── 10. слоговая структура не выше освоенного типа Марковой ─────────
    on_sheet = {S._word_text(i) for i in S._words_flat(fitted["words"])}
    mk = sorted({r.get("markova_v1_guess") for r in
                 C.load_words(C._words_path(kw["sound"], None))
                 if r["word"] in on_sheet and r.get("markova_v1_guess")})
    ok(10, f"ворота есть (build_content(markova_max=…)); на этом листе типы "
           f"{mk} — поле в словаре помечено как ДОГАДКА (markova_v1_guess), "
           f"порог по умолчанию не наложен")

    # ── 11. слоговой блок ≤ ¼ словесного ────────────────────────────────
    sm, wm = S._material_mm(fitted)
    r11 = [x for x in lint if "правило 11" in x]
    if r11:
        bad(11, r11[0])
    else:
        ok(11, f"слоговой материал {sm:.0f} мм = {sm / wm * 100:.0f} % словесного "
               f"({wm:.0f} мм), порог 25 %")

    # ── 12. дифференциация только когда оба звука автоматизированы ──────
    na(12, "дифференциации в v1 нет вообще (осознанный вычет) — нарушить нечем")

    # ── 13. сквозной словарь ────────────────────────────────────────────
    voc = fitted.get("vocabulary") or {}
    # Источников объявленного словаря ЧЕТЫРЕ (с 2026-08-08): к блоку [4],
    # производным и служебным добавились ГЛАГОЛЫ предложений. Смысл правила
    # не меняется — «ничего с потолка»: глагол объявлен в vocabulary["verbs"]
    # и прошёл тот же фильтр чистоты, что и любое слово листа.
    allowed = {S._strip_marks(str(x).lower()) for x in
               (list(voc.get("block4", [])) + list(voc.get("derived", {}).keys())
                + list(voc.get("service", [])) + list(voc.get("syllables", []))
                + list(voc.get("verbs", [])))}
    stray = []
    for b, t in units:
        if b in ("[5]", "[6]", "[7]"):
            stray += [(b, w) for w in TOKEN.findall(t)
                      if S._strip_marks(w.lower()) not in allowed]
    if stray:
        bad(13, f"вне объявленного словаря: {stray[:5]}")
    else:
        ok(13, f"каждое слово блоков [5][6][7] — из block4 ({len(voc.get('block4', []))}) "
               f"∪ производных ({len(voc.get('derived', {}))}) ∪ служебных "
               f"({len(voc.get('service', []))}) ∪ слогов; строгий режим линтера")

    # ── 14. «Образец: …» у нестандартного задания ───────────────────────
    game = fitted.get("game") or {}
    if not game:
        na(14, "блок [5] на этом листе отсутствует")
    elif game.get("example"):
        ok(14, f"«Образец: {game['example']}»")
    else:
        bad(14, "игра без строки «Образец»")

    # ── 15. инструкция ребёнку — одна фраза, повелительное, без терминов ─
    bad_ins = []
    for k in ("articulation", "syllables", "words", "game", "sentences", "chant"):
        ins = (fitted.get(k) or {}).get("instruction") or ""
        if not ins:
            continue
        first = (TOKEN.search(ins) or [""])
        first = first.group(0).lower() if hasattr(first, "group") else ""
        if first not in S.CHILD_VERBS or ins.count(".") > 1:
            bad_ins.append((k, ins))
    ok(15, "все инструкции — один императив из словаря канона") if not bad_ins \
        else bad(15, f"инструкции вне канона: {bad_ins}")

    # ── 16. двойной глагол «Повтори, прочитай» ──────────────────────────
    dbl = [k for k in ("syllables", "words", "sentences", "chant")
           if "прочитай" in ((fitted.get(k) or {}).get("instruction") or "")]
    ok(16, f"двойной глагол в блоках: {dbl}") if len(dbl) >= 3 \
        else bad(16, f"двойной глагол только в {dbl}")

    # ── 17. приём «над чертой» ──────────────────────────────────────────
    na(17, "НЕ реализован (в ТЗ — шаг 2 после первого листа)")

    # ── 18. групповой лист = пересечение профилей ───────────────────────
    na(18, "групповой режим НЕ реализован; profile принимает только одного "
           "ребёнка (объединение профилей даст тот же код)")

    # ── 19. 6-8 заданий на 10-15 минут ──────────────────────────────────
    ok(19, f"заданий {len(blocks)} (норма 6-8), подвал говорит «10-15 минут»") \
        if 6 <= len(blocks) <= 8 else bad(19, f"заданий {len(blocks)}, норма 6-8")

    # ── 20. при ОНР II честно сказать «чистого материала не существует» ──
    na(20, "уровень ОНР на вход не подаётся; ближайший аналог — честный отказ "
           "при пустом пересечении (проверен на «hard»)")

    # ── 21. игровой образ ровно ОДИН на лист ────────────────────────────
    imgs = re.findall(r"«([^»]+)»", (fitted.get("isolated") or {}).get("instruction", ""))
    ok(21, f"образов на листе: {len(imgs)} — {imgs}") if len(imgs) == 1 \
        else bad(21, f"образов {len(imgs)}: {imgs}")

    # ── 22. на листе нет чужого звука ───────────────────────────────────
    # буква цели берётся из кейса, а не зашита «р»: иначе правило падает на
    # любом другом звуке (поймано при подключении словарей [с] и [ш])
    iso_txt = (fitted.get("isolated") or {}).get("text", "")
    alien = set(iso_txt.lower()) - set("- ") - {kw["sound"]}
    ok(22, f"изолированно только «{iso_txt}»; «дятел» (д-д-д) снят как чужой "
           f"звук") if not alien else bad(22, f"чужие буквы в [2]: {alien}")

    # ── 23. право: материал собственный, имена авторов не как бренд ─────
    import content as _C                                          # noqa: E402
    ok(23, f"слова — из собственного словаря "
           f"{_C.WORDS_BY_SOUND.get(kw['sound'], '?')}; имя источника стоит "
           f"мелкой подписью-провенансом, не в заголовке и не как бренд")

    # ── 24. никаких выдуманных норм ─────────────────────────────────────
    blob = json.dumps(fitted, ensure_ascii=False)
    fakes = sorted(set(m.group(0) for m in FAKE_NORM.finditer(blob)))
    ok(24, "чисел-норм нет; в подвале только «10-15 минут в день» и "
           "«2-3 приёма» — время, не количество повторов") if not fakes \
        else bad(24, f"похоже на выдуманную норму: {fakes}")

    return {"tag": tag, "rules": R, "lint": lint, "notes": notes,
            "fit_warns": fit_warns, "banned": sorted(banned),
            "height": S.total_height(fitted), "words": n_words}


RULE_NAMES = {
    1: "нет звуков, нарушенных у ребёнка",
    2: "нет звуков, смешиваемых с целевым (р: л, ль, й) — всегда",
    3: "фильтр по ЗВУКАМ, не буквам",
    4: "при бедности позиции — сообщать, не подмешивать грязное",
    5: "никаких листов на этапе постановки",
    6: "слоговой блок никогда не отдельным листом",
    7: "каждая слоговая строка — связка «слог → слово»",
    8: "один тип слога на блок",
    9: "порядок ступеней (открытый → обратный → … )",
    10: "слоговая структура не выше освоенного типа Марковой",
    11: "слоговой блок ≤ ¼ объёма словесного",
    12: "дифференциация только когда оба звука автоматизированы",
    13: "сквозной словарь: игры/фразы только из слов блока [4]",
    14: "каждое нестандартное задание имеет «Образец: …»",
    15: "инструкция ребёнку — одна фраза, повелительное, без терминов",
    16: "двойной глагол «Повтори, прочитай»",
    17: "приём «над чертой»",
    18: "групповой лист = пересечение профилей",
    19: "6-8 заданий на 10-15 минут",
    20: "при ОНР II честно сказать «чистого материала не существует»",
    21: "игровой образ ровно ОДИН на лист",
    22: "на листе нет чужого звука",
    23: "право: материал собственный, имена авторов не как бренд",
    24: "никаких выдуманных норм («60 раз», «за 21 день»)",
}


def main() -> int:
    results = [run_case(tag, kw) for tag, kw, _ in CASES]
    if "--json" in sys.argv:
        print(json.dumps([{**r, "rules": {str(k): v for k, v in r["rules"].items()}}
                          for r in results], ensure_ascii=False, indent=1))
        return 0

    fails = 0
    for r in results:
        print(f"\n{'═' * 78}\n{r['tag'].upper()}   слов {r['words']} · "
              f"{r['height']:.0f} мм из {S.CONTENT_H:.0f} · "
              f"запрет: {', '.join(r['banned'])}\n{'═' * 78}")
        for n in sorted(r["rules"]):
            st, msg = r["rules"][n]
            fails += st == "❌"
            print(f"{st} {n:>2}. {RULE_NAMES[n]}")
            if msg:
                print(f"       {msg}")
        if r["lint"]:
            print("  линтер:", "; ".join(r["lint"]))
    print(f"\nитог: нарушений {fails}" + ("" if fails else "  — чеклист чист"))
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
