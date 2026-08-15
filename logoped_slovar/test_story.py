# -*- coding: utf-8 -*-
"""
test_story.py — прогон материала «Сочини рассказ».

Проверяется не намерение кода, а то, что попадёт на бумагу: слова, которые
логопед прочитает вслух. Главное здесь — ЧИСТОТА: лист обещает, что в опорных
словах нет звуков, которые у ребёнка сейчас не получаются, и это обещание
обязано держаться на каждом звуке и на каждом профиле.

    python3 test_story.py
"""

from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import content as C          # noqa: E402
import story as ST           # noqa: E402

ok = fail = 0


def check(cond: bool, what: str, detail: str = "") -> None:
    global ok, fail
    if cond:
        ok += 1
    else:
        fail += 1
        print(f"  ❌ {what}" + (f" — {detail}" if detail else ""))


def bare(word: str) -> str:
    """Слово без знака ударения — в таком виде его знает фонетика."""
    return word.replace("́", "")


PROFILES = ((), ("ш", "ж"), ("л", "л'"), ("с", "з", "ш", "ж"))

print("Прогон материала «Сочини рассказ»")
print("─" * 60)

for sound in sorted(C.WORDS_BY_SOUND):
    for profile in PROFILES:
        tag = f"[{sound}] профиль {','.join(profile) or '—'}"
        try:
            s = ST.build_story(sound, profile=profile)
        except ST.StoryError as exc:
            # Отказ законен: на узком профиле тема может обеднеть. Но он обязан
            # быть ЧЕЛОВЕЧЕСКИМ — логопед читает его как есть (локальный закон 3).
            msg = str(exc)
            check(msg and msg[0].islower() or msg[0].isupper(),
                  f"{tag}: отказ пустой")
            check("Traceback" not in msg and "Error" not in msg,
                  f"{tag}: отказ машинный", msg[:60])
            continue

        banned = C.banned_phonemes(sound, frozenset(profile))
        printed = s["nouns"] + s["verbs"]

        check(len(s["nouns"]) >= ST.MIN_NOUNS,
              f"{tag}: опорных слов {len(s['nouns'])}, канон дома {ST.MIN_NOUNS}")
        check(len(s["nouns"]) <= ST.MAX_NOUNS,
              f"{tag}: опорных слов больше {ST.MAX_NOUNS}")
        check(len(set(printed)) == len(printed),
              f"{tag}: слово повторяется на листе")

        # ГЛАВНОЕ: ни одного запрещённого звука в том, что читают вслух.
        for w in printed:
            dirty = C.corrigible_of(bare(w)) & banned
            check(not dirty, f"{tag}: «{bare(w)}» несёт {sorted(dirty)}")

        # Целевой звук обязан быть в каждом опорном слове — иначе это опора
        # не на звук, а просто слово по теме.
        for w in s["nouns"]:
            check(sound in C.corrigible_of(bare(w)),
                  f"{tag}: в опорном слове «{bare(w)}» нет целевого звука")

        # Тема, которую напечатали, обязана быть в списке предложенных: экран
        # рисует кнопки по этому списку, и кнопка не должна вести в никуда.
        check(s["meta"]["theme"] in s["meta"]["themes"],
              f"{tag}: напечатана тема вне списка")

        # Тот же вход — тот же лист. Иначе логопед не может вернуться к тому,
        # что уже распечатал.
        again = ST.build_story(sound, profile=profile)
        check(again["nouns"] == s["nouns"] and again["verbs"] == s["verbs"],
              f"{tag}: два одинаковых запроса дали разные листы")

# Отказ на несуществующей теме — словами, а не исключением движка.
try:
    ST.build_story("р", theme="колбаса-и-звёзды")
    check(False, "несуществующая тема принята молча")
except ST.StoryError as exc:
    check("есть:" in str(exc), "отказ по теме не перечисляет доступные темы")

# Каждая предложенная тема обязана собираться — кнопок-обманок быть не должно.
for sound in sorted(C.WORDS_BY_SOUND):
    themes = [t for t, _ in ST.themes_for(sound)]
    for t in themes:
        try:
            ST.build_story(sound, theme=t)
        except ST.StoryError as exc:
            check(False, f"[{sound}] тема «{t}» предложена, но не собирается",
                  str(exc)[:60])

print("─" * 60)
print(f"проверок: {ok + fail}   прошло: {ok}   упало: {fail}")
print("ВСЁ ЗЕЛЁНОЕ" if not fail else "ЕСТЬ ПАДЕНИЯ")
raise SystemExit(1 if fail else 0)
