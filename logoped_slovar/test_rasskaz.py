# -*- coding: utf-8 -*-
"""
test_rasskaz.py — прогон материала «Рассказ» (пересказ готового текста).

Проверяется ТЕКСТОТЕКА, а не намерение кода: каждый текст, который может уйти
на бумагу, обязан держать нормы и чистоту. Главное обещание листа — «в словах
нет звуков, которые у ребёнка не получаются», и оно проверяется на всех
профилях, а не только на пустом.

    python3 test_rasskaz.py
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import content as C          # noqa: E402
import rasskaz as R          # noqa: E402

ok = fail = 0


def check(cond: bool, what: str, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
    else:
        fail += 1
        print(f"  ❌ {what}" + (f" — {detail}" if detail else ""))


PROFILES = ((), ("ш", "ж"), ("л", "л'"), ("с", "з", "ш", "ж"))

print("Прогон материала «Рассказ»")
print("─" * 60)

texts = R.load_texts()
check(bool(texts), "текстотека пуста")

ids = [t["id"] for t in texts]
check(len(set(ids)) == len(ids), "повторяющийся id текста")

for t in texts:
    tag = f"[{t['sound']}] «{t['title']}»"
    check(t["sound"] in C.WORDS_BY_SOUND, f"{tag}: звука нет в генераторе")

    # НОРМЫ И ЧИСТОТА на пустом профиле — текст в текстотеке обязан быть годным
    # хотя бы для ребёнка без других нарушений. Иначе он не нужен вовсе.
    base = C.banned_phonemes(t["sound"], frozenset())
    st = R.check_text(t, t["sound"], base)
    check(not st["errors"], f"{tag}: не проходит нормы", "; ".join(st["errors"]))

    # Композиция: зачин и концовка обязательны (✅ Глухов). Проверяем то, что
    # проверяемо кодом: текст не обрывается и не начинается с середины —
    # первое и последнее предложения существуют и не пусты.
    sents = R._sentences(t["text"])
    check(len(sents) >= 3, f"{tag}: предложений меньше трёх — нет композиции")
    check(bool(sents and sents[0].strip()), f"{tag}: нет зачина")
    check(bool(sents and sents[-1].strip()), f"{tag}: нет концовки")

    # Вопросы обязаны быть про ЭТОТ текст: пустых и дублей быть не должно.
    qs = t.get("questions", [])
    check(all(q.strip().endswith("?") for q in qs),
          f"{tag}: вопрос без знака вопроса")
    check(len(set(qs)) == len(qs), f"{tag}: вопрос повторяется")

# Сборка листа на всех звуках и профилях: либо лист, либо ЧЕЛОВЕЧЕСКИЙ отказ.
for sound in sorted(C.WORDS_BY_SOUND):
    for profile in PROFILES:
        tag = f"[{sound}] профиль {','.join(profile) or '—'}"
        try:
            r = R.build_rasskaz(sound, profile=profile)
        except R.RasskazError as exc:
            msg = str(exc)
            check("Traceback" not in msg and "Error" not in msg,
                  f"{tag}: отказ машинный", msg[:70])
            continue

        banned = C.banned_phonemes(sound, frozenset(profile))
        # ГЛАВНОЕ: на бумаге нет ни одного запрещённого звука.
        for w in R._tokens(r["text"]["text"]) + R._tokens(r["text"]["title"]):
            bad = R._keys(w) & banned
            check(not bad, f"{tag}: «{w}» несёт {sorted(bad)}")

        # Текст, который напечатали, обязан быть в списке предложенных —
        # экран рисует кнопки по нему, и кнопка не должна вести в никуда.
        check(r["text"]["id"] in [o["id"] for o in r["options"]],
              f"{tag}: напечатан текст вне списка")

        # Ударение не выдумывается: печатная версия отличается от исходной
        # только знаками ударения, слова те же.
        check(r["printed_text"].replace("́", "") == r["text"]["text"],
              f"{tag}: печатный текст разошёлся с исходным")

        # Тот же вход — тот же лист.
        again = R.build_rasskaz(sound, profile=profile)
        check(again["text"]["id"] == r["text"]["id"],
              f"{tag}: два одинаковых запроса дали разные тексты")

# Отказ на несуществующем тексте — словами.
try:
    R.build_rasskaz("р", text_id="нет-такого")
    check(False, "несуществующий текст принят молча")
except R.RasskazError as exc:
    check("есть:" in str(exc), "отказ по тексту не перечисляет доступные")

print("─" * 60)
print(f"проверок: {ok + fail}   прошло: {ok}   упало: {fail}")
print("ВСЁ ЗЕЛЁНОЕ" if not fail else "ЕСТЬ ПАДЕНИЯ")
raise SystemExit(1 if fail else 0)
