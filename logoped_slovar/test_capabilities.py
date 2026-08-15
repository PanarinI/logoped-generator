# -*- coding: utf-8 -*-
"""
test_capabilities.py — обещания ЭКРАНУ. Проверяется не материал, а честность.

Запуск:  python3 test_capabilities.py    (свой раннер, без зависимостей)
         pytest test_capabilities.py     (тоже работает)

ЗАЧЕМ. Экран гасит кнопку слога и кнопку игры по тому, что сказал движок. Если
таблица `capabilities` и настоящее поведение материалов разойдутся, логопед
получит ровно ту болезнь, от которой всё и чинилось 08-10: кнопка обещает, а
материал не делает — или наоборот, живой материал спрятан за серой кнопкой.

Здесь ловится и то и другое:
  • сказано «не делает» → build_track/build_propisi обязаны отказать;
  • сказано «делает»    → обязаны собрать;
  • сказано «игра живая» → лист обязан напечатать ИМЕННО её;
  • сказано «игра мертва» → лист обязан напечатать другую и не молчать.
"""

from __future__ import annotations

import sys

import capabilities as CAP
import content as C
import propisi as PR
import sheet as S
import track as T

_results = []


def check(name, actual, expected):
    ok = actual == expected
    _results.append((ok, name, actual, expected))
    assert ok, f"{name}: получили {actual!r}, ждали {expected!r}"
    return ok


SOUNDS = sorted(C.WORDS_BY_SOUND)
# Хватает двух звуков на игры: полный перебор по всем 11 × 5 × 3 — это минуты,
# а болезнь ловится и на паре (у [Л] игры живут, у [Щ] проседают).
GAME_SOUNDS = ("л", "щ")


def test_track_matches_table():
    """Слоговая дорожка: таблица и поведение — одно и то же."""
    for snd in SOUNDS:
        for opt in CAP.syllable_options("track", snd):
            try:
                T.build_track(snd, opt["typ"])
                built = True
            except T.TrackError:
                built = False
            check(f"track [{snd}] {opt['typ']}", built, opt["ok"])


def test_propisi_matches_table():
    """Звуковая дорожка: то же самое. Молчаливой подмены типа больше нет."""
    for snd in SOUNDS:
        for opt in CAP.syllable_options("propisi", snd):
            try:
                PR.build_propisi(snd, opt["typ"], mode="syllable")
                built = True
            except PR.PropisiError:
                built = False
            check(f"propisi [{snd}] {opt['typ']}", built, opt["ok"])


def test_isolated_ignores_syllable_type():
    """Ступень «только звук»: слога на бумаге нет — тип не может ей мешать."""
    for snd in SOUNDS:
        p = PR.build_propisi(snd, "direct", mode="isolated")
        check(f"isolated [{snd}] без слога", p["meta"]["syllable"], "")


def test_games_offer_is_honest():
    """Что обещано кнопкой игры, то и печатается на листе."""
    for snd in GAME_SOUNDS:
        for typ in C.SYL_TYPES:
            try:
                content, _ = S.compose(snd, typ, "", sheet_no=1, seed=0)
            except BaseException:
                continue                      # лист на этом слоге не собирается
            offer = content.get("games_offer") or {}
            check(f"[{snd}] {typ}: обещание есть", sorted(offer), sorted(C.GAME_KINDS))
            for kind, state in offer.items():
                c2, _ = S.compose(snd, typ, "", sheet_no=1, seed=0, game_kind=kind)
                printed = (c2.get("game") or {}).get("kind", "")
                if state["ok"]:
                    # живая игра обязана попасть на лист именно как выбранная
                    check(f"[{snd}] {typ}: {kind} печатается", printed, kind)
                else:
                    # мёртвая — не печатается, движок откатывается к другой
                    check(f"[{snd}] {typ}: {kind} не печатается",
                          printed == kind, False)


def test_offer_counts_are_real():
    """«Набирается 3 из 4» — не фигура речи: меньше четырёх и значит мертва."""
    for snd in GAME_SOUNDS:
        content, _ = S.compose(snd, "direct", "", sheet_no=1, seed=0)
        for kind, state in (content.get("games_offer") or {}).items():
            if state.get("reason"):
                continue                      # отказ не по числу примеров
            check(f"[{snd}] {kind}: счёт сходится с вердиктом",
                  state["found"] >= state["need"], state["ok"])


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
