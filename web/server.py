#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Веб-интерфейс генератора логопедических листов.

Флоу (утверждён автором, DECISIONS.md): звук → слог → готовый лист.
Профиль ребёнка НЕ спрашивается на входе — он появляется ПОСЛЕ первого листа
и пересчитывает материал на глазах. Это и есть ров: показать, а не объяснить.

Только стандартная библиотека. Движок (phonetics/content/sheet/maze) тоже без
внешних зависимостей — веб не имеет права вносить первую.

Запуск:
    python3 web/server.py [--port 8760]

━━━ ЧТО ЗДЕСЬ НЕЛЬЗЯ ТРОГАТЬ (проверено разведкой 2026-08-02) ━━━
1. Канонный путь сборки — ровно тот же, что у чеклиста брака (check_sheets.py:93-98):
       content, report = sheet.compose(sound, typ, profile_СТРОКОЙ, sheet_no=…, seed=…)
       html, warns     = sheet.render_sheet_ex(content, meta, options=…)
   fit() и lint() render_sheet_ex зовёт внутри сам. Второй build_content внутри
   sheet.py — легаси-стопгап («--stopgap»), в нём нет ни орфографии слогов, ни
   сквозного словаря. Не звать никогда.
2. Профиль отдавать ТОЛЬКО строкой «л,ш». Список из JSON молча не фильтрует
   (sheet.compose разворачивает строку и не трогает список), а прямая передача
   строки в content.build_content разваливает её на буквы. Одна дверь: compose.
3. «Другой лист» — это sheet_no+1, а НЕ seed. seed слова не меняет (проверено:
   seed 0/1/7 дают тот же список), он крутит только игру и чистоговорку.
4. typ валидировать по sheet.TYPE_ALIASES ДО вызова: на неизвестном типе compose
   делает SystemExit, а он не ловится обычным except Exception.
5. Недобор материала — ТИХИЙ УСПЕХ. Тяжёлый профиль отдаёт лист из 2 слов без
   исключения. Канон блока [4] — 12-24 слова. Поэтому сервер сам смотрит на
   количество и поднимает предупреждения движка в блокирующие.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import urllib.parse
import urllib.request
import secrets
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
ENGINE = os.path.join(PROJECT, "logoped_slovar")
sys.path.insert(0, ENGINE)

import content as C          # noqa: E402
import capabilities as CAP   # noqa: E402  — что какой материал умеет
import sheet as S            # noqa: E402
import maze as M             # noqa: E402
import track as T            # noqa: E402
import propisi as PR         # noqa: E402
import scenes as SCN         # noqa: E402
import phrases as PH         # noqa: E402
import story as ST           # noqa: E402  — «сочини рассказ», лист взрослому
import rasskaz as RZ         # noqa: E402  — готовый рассказ для пересказа
import phonetics as ph       # noqa: E402
import sitepages as SITE    # noqa: E402  — страницы сайта вокруг виджета

sys.path.insert(0, HERE)
import method                # noqa: E402  — методическая цепочка для панели
import human                 # noqa: E402  — перевод машинных текстов на человеческий
import otzyv as OT           # noqa: E402  — канал обратной связи от логопеда


# ═══════════════════════════════════════════════════════════════════════
#  СЛОВАРЬ ИНТЕРФЕЙСА
# ═══════════════════════════════════════════════════════════════════════

# Подписи кнопок звука. Апостроф — наша внутренняя запись мягкости; логопед
# пишет «Рь», и на экране должно стоять именно это (закон проекта: на экране
# нет ни одного слова, которое существует только у нас в коде).
# Порядок здесь = порядок закладок на экране. Шипящие идут Ш · Щ · Ж, чтобы
# Ш и Щ стояли рядом (слово автора 08-23): они пара по месту образования и
# логопед ходит между ними чаще, чем между Ш и Ж.
SOUND_LABEL = {
    "р": "Р", "р'": "Рь", "л": "Л", "л'": "Ль",
    "с": "С", "с'": "Сь", "з": "З", "з'": "Зь",
    "ш": "Ш", "щ": "Щ", "ж": "Ж",
}

# Мягкие пары движок добавляет сам (нарушенный [л] почти всегда значит и [л']),
# поэтому логопеду показываем только твёрдые — просить отмечать «л» и «ль»
# отдельно бессмысленно, результат тот же.
# Какие звуки логопед может отметить как НЕПОСТАВЛЕННЫЕ у ребёнка.
#
# Порядок — по группам, как их называет логопед: свистящие · шипящие и аффрикаты ·
# сонорные · заднеязычные · смычные. Движок сам добавляет мягкие пары
# (`sheet._expand_profile`), поэтому Сь, Ль и прочие отдельными кнопками не стоят.
#
# 🔶 Тир списка — наш, источника под ним нет. Первые тринадцать собраны по звукам
# ПОЗДНЕГО ОНТОГЕНЕЗА: свистящие, шипящие, сонорные, заднеязычные, Й — те, что
# логопед реально ставит при дислалии.
#
# ⚠ 2026-08-24, решение автора: добавлены смычные П Б Т Д. Прежний список был
# собран под ДИСЛАЛИЮ, а наш собственный разбор реальных обращений говорит
# обратное (research/logoped_realnye_zaprosy_2026-08-02.md, дословно): «Ни одного
# случая простой дислалии. Все — сочетанные нарушения… при ОНР III и дизартрии
# нарушено полсписка». При дизартрии смычные плывут вместе со всем остальным, и
# там же записан живой запрос логопеда: «автоматизация и дифференциация к-т, г-д».
# К и Г в списке были с самого начала — П Б Т Д отсутствовали без причины.
# Это не косметика: со стечениями («тра», «дра», «бра», «пра») профиль без них
# пропускал второй согласный не проверив.
#
# Чего в списке НЕТ и почему: губные М Н В Ф — звуки самого раннего онтогенеза,
# их нарушение выводит за рамки материала (ринолалия, тяжёлая дизартрия), и
# отмечать их логопеду по нашим наблюдениям не приходилось. Появится живой
# запрос — добавим тем же движением, механика их уже понимает.
PROFILE_OPTIONS: Tuple[Tuple[str, str], ...] = (
    ("с", "С"), ("з", "З"), ("ц", "Ц"),
    ("ш", "Ш"), ("ж", "Ж"), ("щ", "Щ"), ("ч", "Ч"),
    ("л", "Л"), ("р", "Р"), ("й", "Й"),
    ("к", "К"), ("г", "Г"), ("х", "Х"),
    ("п", "П"), ("б", "Б"), ("т", "Т"), ("д", "Д"),
)

POSITION_LABEL = {
    "initial": "в начале слова",
    "medial": "в середине слова",
    "final": "в конце слова",
}

# Канон блока [4]. Для стечений минимум ниже — так в источнике: у Спивак
# (ГНОМ, 2007) на стечении стоит строка из СЕМИ слов, а не двенадцати.
# Считает движок: C.canon_min_words(тип слога).
MIN_WORDS_CANON = 12          # канон блока [4]: 12-24 слова


# ═══════════════════════════════════════════════════════════════════════
#  МОСТ К ДВИЖКУ
# ═══════════════════════════════════════════════════════════════════════

def profile_str(items: Any) -> str:
    """Профиль из JSON (список) → строка, которую движок понимает правильно."""
    if not items:
        return ""
    if isinstance(items, str):
        return items
    clean = [str(x).strip() for x in items if str(x).strip()]
    return ",".join(clean)


def expand(raw: str) -> frozenset:
    """Разворот профиля ровно так, как это делает канонный путь sheet.compose."""
    return frozenset(S._expand_profile(raw))


def pool_stats(sound: str, prof: str) -> Dict[str, Any]:
    """Числа рва — считаются по словарю публичными воротами движка.

    dict_total   — сколько слов в картотеке звука;
    base_removed — сколько убрано ДО всякого профиля: это звуки, которые с целью
                   смешиваются (для [Р] — Л, Л', Й). Убираются всегда;
    base_clean   — что остаётся как рабочий запас звука;
    profile_removed / left — что сверх этого убрал профиль ребёнка.
    """
    rows = C.load_words(C._words_path(sound, None))
    base_banned = C.banned_phonemes(sound, frozenset())
    base_clean = [r for r in rows
                  if C.is_clean(r["word"], base_banned, r.get("stress_syllable"))]

    banned = C.banned_phonemes(sound, expand(prof))
    left = [r for r in rows
            if C.is_clean(r["word"], banned, r.get("stress_syllable"))]

    return {
        "dict_total": len(rows),
        "base_clean": len(base_clean),
        "base_removed": len(rows) - len(base_clean),
        "base_banned": sorted(base_banned),
        "profile_removed": len(base_clean) - len(left),
        "left": len(left),
        "banned": sorted(banned),
    }


def words_on_sheet(content: Dict[str, Any]) -> List[str]:
    """Слова, реально попавшие в блок [4] свёрстанного листа."""
    out: List[str] = []
    for tier in content.get("words", {}).get("tiers", []) or []:
        for group in tier.get("groups", []) or []:
            out += [it["word"] for it in group.get("items", []) or []]
    return out


GAME_LABEL = {
    "one_many": "Один — много",
    "diminutive": "Назови ласково",
    "count_1_5": "Посчитай 1-5",
}


def games_state(content: Dict[str, Any], fitted: Dict[str, Any],
                want: str) -> Dict[str, Any]:
    """Состояние трёх игр блока [5] для экрана: живая · почему нет · что на листе.

    `content` — до вёрстки (там движок сказал, какие игры набрались),
    `fitted` — после: игра могла не поместиться на А4 и быть снятой. Разница
    между ними — это разница между «игры нет в словаре» и «игра не влезла»,
    и логопеду это две разные новости.
    """
    offer = content.get("games_offer") or {}
    printed = (fitted.get("game") or {}).get("kind", "")
    built = (content.get("game") or {}).get("kind", "")
    items = []
    for key in C.GAME_KINDS:
        state = offer.get(key) or {}
        ok = bool(state.get("ok"))
        items.append({
            "key": key,
            "label": GAME_LABEL.get(key, key),
            "ready": ok,
            "why": "" if ok else human.why_game(int(state.get("found", 0)),
                                                int(state.get("need", 4)),
                                                str(state.get("reason", ""))),
        })
    return {
        "items": items,
        "printed": printed,
        # Игра собралась, но на бумагу не попала — это про место, не про слова.
        "dropped": human.GAME_DROPPED if (built and not printed) else "",
        # Логопед просил одну, движок отдал другую — молчать об этом нельзя.
        "fallback": bool(want and printed and want != printed),
    }


def build_sheet(sound: str, typ: str, prof: str,
                sheet_no: int = 1, seed: int = 0,
                audience: str = "home", game: str = "",
                colour: bool = False) -> Dict[str, Any]:
    """Канонный путь сборки листа. Возвращает готовый ответ для браузера.

    ВАЖНО про порядок. `render_sheet_ex` внутри себя зовёт `fit()`, а `fit`
    работает на ГЛУБОКОЙ КОПИИ и именно из копии выбрасывает слова, чтобы лист
    влез в А4 (sheet.py:447). Если считать слова по исходному `content`, число
    получится ДОвёрсточным: ров обещал бы 16 слов там, где на бумаге 14.
    Поэтому ужимаем сами, один раз, и дальше всё — и счёт, и канон-линтер, и
    рендер — идёт по ОДНОМУ И ТОМУ ЖЕ свёрстанному листу.
    """
    content, report = S.compose(sound, typ, prof, sheet_no=sheet_no, seed=seed,
                                game_kind=game)
    meta = {
        "sound": sound,
        "sheet_no": sheet_no,
        "child_name": "",     # имя ребёнка в интерфейсе не спрашиваем —
        "week_from": "",      # на бумаге остаётся пустая строка под руку
        "week_to": "",
        # Вместо «Лист № N» в шапке стоит СТУПЕНЬ. Номер обещал автопрогрессию
        # («лист №N сам знает свою ступень»), которой в движке нет: лестницу
        # задаёт логопед. Ступень — правда, номер был обещанием механизма.
        "step_label": C.SYL_TYPE_LABEL.get(
            S.TYPE_ALIASES.get(typ, typ), ""),
    }

    # Ужимаем ПО СВОЕМУ адресату: у листа логопеда нет шапки, подвала и
    # подсказок, и резать его по домашней мерке — значит отнимать место,
    # которого он не занимает (поймано 08-12: 18 листов из 23 резались зря).
    fitted, fit_warns = S.fit(S.for_audience(content, audience),
                              S.CONTENT_H, audience)
    html, _ = S.render_sheet_ex(
        fitted, meta,
        options={"stress": "non_obvious", "show_warnings": False,
                 "no_fit": True, "audience": audience,
                 "sound": sound, "colour": colour},
    )

    words = words_on_sheet(fitted)

    # Браком лист называет НЕ регулярка по тексту предупреждений, а сам
    # канон-линтер проекта. Раньше здесь стоял поиск подстроки «правило 11» —
    # и он ловил её в СПРАВОЧНОМ тексте движка, объявляя браком чистый лист
    # ([Ш] + обратные слоги: 15 слов, линтер молчит, а печать блокировалась).
    blocking = list(S.lint(fitted, meta))
    notes = list(fitted.get("notes") or []) + list(fit_warns)
    min_words = C.canon_min_words(S.TYPE_ALIASES.get(typ, typ))
    if len(words) < min_words and not blocking:
        blocking = [f"слов на листе {len(words)} — меньше канонического "
                    f"минимума {min_words} (блок [4])"]

    stats = pool_stats(sound, prof)
    stats["on_sheet"] = len(words)

    rows = fitted.get("syllables", {}).get("rows", []) or []
    syllable = (rows[0].get("units") or [""])[0] if rows else ""

    return {
        "ok": True,
        "html": html,
        "stats": stats,
        # Какие игры живут на СЛОВАХ ЭТОГО листа. Раньше экран считал живыми
        # все три всегда, и на листе, где выбранная игра не набирает четырёх
        # примеров, логопед жал кнопку, а печаталась прежняя игра — молча.
        "games": games_state(content, fitted, game),
        # Наружу идут ТОЛЬКО человеческие тексты. Машинные — в raw, для нас.
        "warnings": human.split(blocking, notes),
        "syllable": syllable,
        "words": words,
        "sheet_no": sheet_no,
        "purity_scope": report.get("purity_scope", ""),
    }


def build_maze(sound: str, position: str, prof: str,
               seed: int = 0, service_cell: str = "question",
               colour: bool = False) -> Dict[str, Any]:
    m = M.build_maze(sound=sound, position=position, profile=prof,
                     seed=seed, service_cell=service_cell)
    html = M.render_maze(m, {"no_warnbox": True, "colour": colour})
    return {
        "ok": True,
        "html": html,
        "warnings": human.split([], list(m.get("warnings", []))),
        "stats": maze_stats(m, sound),
    }


def maze_stats(m: Dict[str, Any], sound: str) -> Dict[str, Any]:
    """Числа ДОРОЖКИ, а не листа.

    Раньше сюда уходил `pool_stats` по всему словарю звука — числа не имели к
    дорожке отношения и не менялись при смене позиции, хотя слова в клетках
    менялись целиком. Здесь только то, что относится к этой дорожке.
    """
    rep = m.get("selection_report", {}) or {}
    rejected = rep.get("rejected", {}) or {}
    mm = m.get("meta", {}) or {}
    return {
        "kind": "maze",
        "dict_total": len(C.load_words(C._words_path(sound, None))),
        "position_label": mm.get("position_label", ""),
        "fit_position": int(mm.get("n_candidates", rep.get("found", 0)) or 0),
        "rejected_position": int(rejected.get("позиция", 0) or 0),
        "rejected_purity": int(rejected.get("чистота", 0) or 0),
        "pictures": int(mm.get("n_pictures", 0) or 0),
        "cells": len(m.get("cells", []) or []),
    }


def syllable_buttons() -> Dict[str, List[Dict[str, str]]]:
    """Подписи кнопок — НАСТОЯЩИЕ слоги из движка, а не придуманные.

    Закон автора: «показывать вещь, а не изобретать для неё имя». Поэтому на
    кнопке стоит ровно тот слог, который окажется на листе. Считается один раз
    при старте, на пустом профиле.
    """
    out: Dict[str, List[Dict[str, Any]]] = {}
    for snd in C.WORDS_BY_SOUND:
        items: List[Dict[str, Any]] = []
        for typ in C.SYL_TYPES:
            row: List[str] = []
            n_words = 0
            try:
                content, _ = S.compose(snd, typ, "", sheet_no=1, seed=0)
                rows = content.get("syllables", {}).get("rows", []) or []
                units = (rows[0].get("units") or []) if rows else []
                row = [u.upper() for u in units]
                syl = units[0] if units else ""
                n_words = len((content.get("vocabulary") or {}).get("block4", []))
            except BaseException:
                syl = ""
            label = syl.upper() if syl else "—"
            # Для объяснения берём настоящий слог, даже если лист на нём не
            # собрался: «АЖ читается как АШ» понятнее, чем «такой слог».
            said = label if label != "—" else CAP.probe_syllable(snd, typ)
            # Лист: сначала запрет устройства или языка (его можно объяснить
            # словами), и только если такого запрета нет — «слов не набралось».
            sheet_reason = CAP.block_reason("sheet", snd, typ)
            if not sheet_reason and not syl:
                sheet_reason = "no_words"
            mats: Dict[str, Dict[str, Any]] = {}
            for mat in ("sheet", "track", "propisi"):
                reason = (sheet_reason if mat == "sheet"
                          else CAP.block_reason(mat, snd, typ))
                mats[mat] = {"ok": not reason,
                             "why": human.why_syllable(reason, said, mat)}
            items.append({
                "typ": typ,
                # На погашенной кнопке стоит сам слог, а не прочерк: «АЖ» с
                # объяснением понятнее, чем немое «—». Прочерк остаётся там,
                # где слога и правда нет (у стечений он берётся из слов).
                "syllable": label if label != "—" else (said or "—"),
                # ВЕСЬ ряд слогов этого типа. На кнопке стояла одна «ЛА», и она
                # читалась как обещание листа только на А — хотя гласная тут
                # пример, а на бумаге будет ЛА · ЛО · ЛУ · ЛЫ (автор 08-11).
                "row": row,
                # Слов на таком листе. Меньше 12 — канон блока [4] не выполнен,
                # и кнопка обязана это сказать заранее, а не после сборки.
                "words": n_words,
                "thin": bool(row) and 0 < n_words < C.canon_min_words(typ),
                "need": C.canon_min_words(typ),
                "label": C.SYL_TYPE_LABEL.get(typ, typ),
                "available": bool(syl) and not sheet_reason,
                # Что на этом слоге умеет КАЖДЫЙ материал. До 08-10 экран знал
                # только про лист, а дорожки узнавали о несовпадении отказом
                # уже после нажатия — машинным «cluster_onset» или молчаливой
                # подменой слога на прямой.
                "materials": mats,
            })
        out[snd] = items
    return out


def scene_buttons() -> Dict[str, List[Dict[str, Any]]]:
    """Фоны слоговой дорожки — по звуку, через его героя.

    Логопед видит не общий список, а миры ЭТОГО героя плюс «без фона»: комарику
    предлагаются лес и пруд, мотору — дорога и город. Список не режется
    запретом, он собирается из подходящего (решение автора 08-10).
    """
    out: Dict[str, List[Dict[str, Any]]] = {}
    for snd in C.WORDS_BY_SOUND:
        hero = (PR.image_for(snd).get("name") or "").strip()
        items = [{"key": "", "label": SCN.SCENE_LABELS[""], "hero": hero}]
        for key in SCN.worlds_for(hero):
            items.append({"key": key,
                          "label": SCN.SCENE_LABELS.get(key, key),
                          "hero": hero})
        out[snd] = items
    return out


def position_buttons() -> Dict[str, List[Dict[str, Any]]]:
    """Позиции звука для лабиринта — по каждому звуку своя правда.

    Язык (оглушение) знает `capabilities`, картотеку — только сборка, поэтому
    здесь пробуем собрать. Все 33 лабиринта считаются за полсекунды, один раз
    при старте — как и подписи слогов.
    """
    out: Dict[str, List[Dict[str, Any]]] = {}
    for snd in C.WORDS_BY_SOUND:
        items: List[Dict[str, Any]] = []
        for pos, label in POSITION_LABEL.items():
            reason = CAP.position_reason(snd, pos)
            if not reason:
                try:
                    M.build_maze(sound=snd, position=pos, profile="")
                except BaseException:
                    reason = "no_words"
            items.append({"key": pos, "label": label,
                          "ok": not reason,
                          "why": human.why_position(reason, pos)})
        out[snd] = items
    return out


# ═══════════════════════════════════════════════════════════════════════
#  HTTP
# ═══════════════════════════════════════════════════════════════════════

# Сервис превращения HTML в PDF. Свой, автора: тот же, что обслуживает его
# расширение save-chatgpt-as-pdf. Адрес — окружением, чтобы не вшивать в код
# чужой хост и чтобы его можно было заменить, не трогая программу.
GOTENBERG = os.environ.get(
    "GOTENBERG_URL", "https://export-gpt.duckdns.org/forms/chromium/convert/html")


# Соответствие адреса и папки на диске — то же, каким сервер отдаёт картинки
# по сети (`_hero`, `_bank`). Один факт, один дом.
# ⚠ 08-26: у сцены появились цветной и ч/б банки. Старый плоский путь оставлен:
# нет папок — сервер отдаёт как раньше, и откат ничего не стоит.
_PICT_DIRS = {"geroi/colour": "geroi", "geroi/bw": "geroi_bw", "fony": "fony",
              "fony/colour": "fony/colour", "fony/bw": "fony/bw",
              "dorozhka/colour": "dorozhka/colour", "dorozhka/bw": "dorozhka/bw",
              # Метки старта и финиша слоговой дорожки (08-26).
              "metki/colour": "metki/colour", "metki/bw": "metki/bw"}


def _embed_pictures(html: str) -> str:
    """Вшить картинки в сам HTML перед отправкой на печать.

    Gotenberg живёт на ДРУГОМ хосте и наших относительных адресов («/geroi/…»,
    «/fony/…») не видит: он честно идёт по ним к себе и получает ничего. В PDF
    на месте героя выходил битый значок — поймано автором 08-24 на листе [Ль].
    Ровно та же беда была у снимков листов и лечилась так же: не адресом, а
    содержимым. Файл читается с диска, а не выкачивается по сети у самого себя.
    """
    root = os.path.abspath(os.path.join(HERE, "..", "pictures"))

    def sub(m):
        attr, url = m.group(1), m.group(2)
        # Имя в адресе URL-кодировано («самолёт.png» → «%D1%81…»), а на диске
        # оно кириллицей. Без раскодирования файл не находится и картинка молча
        # остаётся адресом — то есть битой на чужом хосте.
        rel = urllib.parse.unquote(url.strip("/"))
        folder, name = ("", "")
        # ⚠ 08-26, поймал автор: спрайты фона в скачанном PDF выходили битыми
        # значками, а герой вставал. Ключи перебирались В ПОРЯДКЕ ЗАПИСИ, и
        # «/fony/colour/tree.png» цеплялся за короткий ключ «fony» раньше
        # длинного «fony/colour». Имя тогда получалось «colour/tree.png», то
        # есть с подкаталогом, — и защита от выхода за папку честно отказывала.
        # Картинка молча оставалась адресом. Берём САМЫЙ ДЛИННЫЙ подходящий
        # ключ: порядок словаря не должен решать, что вшивается.
        for key in sorted(_PICT_DIRS, key=len, reverse=True):
            if rel.startswith(key + "/"):
                folder, name = _PICT_DIRS[key], rel[len(key) + 1:]
                break
        if not folder:
            return m.group(0)
        path = os.path.abspath(os.path.join(root, folder, name))
        if os.path.dirname(path) != os.path.join(root, folder) or not os.path.isfile(path):
            return m.group(0)
        with open(path, "rb") as fh:
            data = base64.b64encode(fh.read()).decode()
        return attr + '="data:image/png;base64,' + data + '"'

    return re.sub(r'\b(src|href|xlink:href)="(/(?:geroi|fony|dorozhka|metki)/[^"]+)"',
                  sub, html)


def to_pdf(html: str) -> bytes:
    """Лист → PDF. Multipart руками: ставить зависимость ради одной формы незачем."""
    html = _embed_pictures(html)
    boundary = "----logozvuk-" + hashlib.sha1(html[:200].encode()).hexdigest()[:16]
    parts: List[bytes] = []

    def field(name: str, value: str) -> None:
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"'
                     f'\r\n\r\n{value}\r\n'.encode("utf-8"))

    parts.append(
        f'--{boundary}\r\nContent-Disposition: form-data; name="files"; '
        f'filename="index.html"\r\nContent-Type: text/html\r\n\r\n'.encode("utf-8")
        + html.encode("utf-8") + b"\r\n")
    # A4 в дюймах. Поля нулевые: они уже заданы внутри листа через @page, и
    # вторые поля поверх первых сдвинули бы всю вёрстку.
    #
    # ⚠ 08-26. Размер был ВШИТ книжным, и это молча пережило появление
    # альбомного листа: полосы звуковой дорожки не влезали в портретную бумагу
    # по ширине и переносились на ВТОРУЮ страницу — все шесть пробных PDF вышли
    # двухстраничными. На экране лист выглядел правильно, потому что там
    # ориентацию задаёт `@page`, а Gotenberg про `@page` не спрашивает: бумагу
    # ему называют цифрами. Поэтому ориентацию читаем из самого листа — один
    # факт, один дом: объявил `@page ... landscape`, значит бумага альбомная.
    _land = bool(re.search(r"@page[^{]*\{[^}]*landscape", html))
    _pw, _ph = ("11.69", "8.27") if _land else ("8.27", "11.69")
    for k, v in (("paperWidth", _pw), ("paperHeight", _ph),
                 ("marginTop", "0"), ("marginBottom", "0"),
                 ("marginLeft", "0"), ("marginRight", "0"),
                 ("printBackground", "true")):
        field(k, v)
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(parts)

    req = urllib.request.Request(
        GOTENBERG, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read()


# ═══════════════════════════════════════════════════════════════════════
#  ВЫДАЧА ГОТОВОГО ФАЙЛА
# ═══════════════════════════════════════════════════════════════════════
#
# Файл кладётся сюда и забирается ОДНИМ переходом по настоящему адресу.
#
# Почему не отдавать его прямо в ответ на запрос — так и было до 08-25.
# Страница получала PDF, делала из него ссылку в памяти (`blob:`) и щёлкала по
# ней с пометкой «скачать». На компьютере работает, на айфоне нет: Safari
# пометку `download` у ссылок `blob:` не выполняет, а просто ПЕРЕХОДИТ по ней —
# и телефон показывает лист смотрелкой вместо того, чтобы сохранить. Экран с
# листом при этом умирает, правки логопеда вместе с ним. Поймано автором 08-25,
# в логе видно как есть: `POST /api/pdf 200`, а следом полная перезагрузка
# приложения. Та же беда ждала и Word — он уходил той же дорогой.
#
# Лечится не в браузере, а заголовком: файл, отданный с `Content-Disposition:
# attachment`, скачивают ВСЕ, включая айфон, и со страницы при этом не уводят.
# Но заголовок живёт на настоящем адресе, а на `blob:` его повесить некуда —
# значит готовый файл должен полежать у нас, пока за ним не придут.
#
# Одноразово и ненадолго: ключ случайный, забрали — забыли, через пять минут
# пропадает сам. Держим в памяти, а не на диске: файл живёт секунды, и класть
# чужой лист на постоянное хранилище незачем.

_STASH: Dict[str, Tuple[float, str, str, bytes]] = {}
_STASH_TTL = 300            # пять минут — с запасом на медленный телефон
_STASH_MAX = 40             # больше одновременных выдач у нас не бывает
_STASH_LOCK = threading.Lock()


def stash(data: bytes, name: str, ctype: str) -> str:
    """Придержать готовый файл, вернуть ключ для адреса `/file/<ключ>`."""
    now = time.time()
    token = secrets.token_urlsafe(12)
    with _STASH_LOCK:
        for k in [k for k, v in _STASH.items() if v[0] < now]:
            _STASH.pop(k, None)
        while len(_STASH) >= _STASH_MAX:
            _STASH.pop(min(_STASH, key=lambda k: _STASH[k][0]), None)
        _STASH[token] = (now + _STASH_TTL, name, ctype, data)
    return token


def unstash(token: str) -> Tuple[str, str, bytes] | None:
    with _STASH_LOCK:
        item = _STASH.pop(token, None)
    if not item or item[0] < time.time():
        return None
    return item[1], item[2], item[3]


def file_name(raw: str, ext: str) -> str:
    """Имя файла для человека. Расширение ставим мы, а не тот, кто попросил."""
    name = re.sub(r"[\\/\r\n\"\x00-\x1f]", "", str(raw or ""))[:80].strip()
    name = name.rsplit(".", 1)[0].strip() or "list"
    return name + "." + ext


CONFIG_CACHE: Dict[str, Any] = {}


_VERSION_CACHE: Dict[str, Any] = {"stamp": None, "v": ""}


def app_version() -> str:
    """Короткий хэш кода экрана: index.html + app.js + app.css.

    Пересчитывается, только когда у файлов сменилось время правки, — чтобы
    каждое нажатие логопеда не читало три файла с диска.
    """
    paths = [os.path.join(HERE, n) for n in ("index.html", "app.js", "app.css")]
    try:
        stamp = tuple(os.path.getmtime(p) for p in paths)
    except OSError:
        return ""
    if _VERSION_CACHE["stamp"] != stamp:
        h = hashlib.md5()
        for p in paths:
            with open(p, "rb") as fh:
                h.update(fh.read())
        _VERSION_CACHE["stamp"] = stamp
        _VERSION_CACHE["v"] = h.hexdigest()[:12]
    return str(_VERSION_CACHE["v"])


def config() -> Dict[str, Any]:
    if not CONFIG_CACHE:
        CONFIG_CACHE.update({
            "sounds": [
                {"key": s, "label": SOUND_LABEL.get(s, s.upper()),
                 "stats": pool_stats(s, "")}
                for s in C.WORDS_BY_SOUND
            ],
            "syllables": syllable_buttons(),
            "profile_options": [{"key": k, "label": v} for k, v in PROFILE_OPTIONS],
            "positions": [{"key": k, "label": v} for k, v in POSITION_LABEL.items()],
            # Позиции звука — свои у каждого звука. Кнопка «в конце слова»
            # горела у [З], [Ж], [Щ], а лабиринт на ней отказывался: у звонких
            # такого слова нет в языке, у [Сь] и [Щ] не хватает картинок.
            "positions_by_sound": position_buttons(),
            # Фоны слоговой дорожки — строка запроса Ольги «менять фон».
            # Список НЕ общий: фон это контекст героя, и у каждого героя свои
            # миры (08-10). Общий список остаётся для совместимости ответа,
            # экран берёт `scenes_by_sound`.
            "scenes": [{"key": k, "label": v} for k, v in SCN.SCENE_LABELS.items()],
            "scenes_by_sound": scene_buttons(),
            # Игры блока [5] — все три канонные (ТЗ, ЯРУС А). Здесь только
            # ключ и подпись: живая игра или нет — свойство КОНКРЕТНОГО листа
            # (слова у каждого свои), и это приходит вместе с листом. Раньше
            # тут стояло ready:True на все три навсегда, и кнопки врали.
            "games": [{"key": k, "label": GAME_LABEL[k]} for k in C.GAME_KINDS],
        })
    return CONFIG_CACHE


def unsupported(material: str, sound: str, typ: str) -> Dict[str, Any]:
    """«Этот материал на таком слоге не делается» — с причиной и выходом.

    Пустой словарь = материал слог умеет. Раньше этой развилки не было вовсе:
    слоговая дорожка падала машинной фразой, звуковая молча меняла слог. Теперь
    ответ один на оба и всегда несёт список слогов, которые материал умеет, —
    логопеду есть куда нажать, а не только что прочитать.
    """
    reason = CAP.block_reason(material, sound, typ)
    if not reason:
        return {}
    items = config()["syllables"].get(sound, [])
    label = next((i["syllable"] for i in items if i["typ"] == typ), "")
    if label in ("", "—"):
        # Лист на этом слоге не собрался, подписи кнопки нет — но объяснять
        # отказ безымянным «таким слогом» нельзя, показываем сам слог.
        label = CAP.probe_syllable(sound, typ)
    options = [{"typ": i["typ"], "syllable": i["syllable"], "label": i["label"]}
               for i in items
               if ((i.get("materials") or {}).get(material) or {}).get("ok")]
    return {
        "ok": False,
        "kind": "unsupported",
        "material": material,
        "message": human.why_syllable(reason, label, material),
        "options": options,
    }


def as_int(value: Any, default: int, low: int = 0) -> int:
    """Число из тела запроса. Мусор — не 500, а разумный дефолт."""
    try:
        return max(low, int(value))
    except (TypeError, ValueError):
        return default


def validate(sound: str, typ: str = "", position: str = "") -> str:
    """Пусто = всё в порядке, иначе — текст ошибки для логопеда."""
    if sound not in C.WORDS_BY_SOUND:
        return (f"звука [{sound}] в генераторе нет; собраны словари: "
                f"{', '.join(sorted(C.WORDS_BY_SOUND))}")
    if typ and typ not in S.TYPE_ALIASES:
        return f"неизвестный тип слога: {typ}"
    if position and position not in M.POSITIONS:
        return f"неизвестная позиция звука: {position}"
    return ""


class Handler(BaseHTTPRequestHandler):
    server_version = "logoped-generator"

    # — служебное —

    # Кто именно приходил — видно только по User-Agent, и без него лог
    # бесполезен ровно там, где он нужнее всего. Поймано 08-25: Телеграм не
    # строил превью ссылки, и по логам нельзя было понять, доходил ли его бот
    # до нас вообще. Заодно теперь видно поисковых роботов — а их приход и есть
    # первый признак, что сайт взяли в индекс.
    #
    # Пишем ТОЛЬКО имя робота, а не весь User-Agent: у браузера в нём версия
    # системы и сборки, и складывать это в вечный лог незачем — обычные заходы
    # остаются просто «браузер».
    BOT_MARKS = ("telegrambot", "twitterbot", "googlebot", "yandexbot",
                 "bingbot", "applebot", "facebookexternalhit", "whatsapp",
                 "slackbot", "discordbot", "vkshare", "mail.ru_bot",
                 "ahrefsbot", "semrushbot", "curl", "python-urllib")

    def log_message(self, fmt: str, *args: Any) -> None:
        ua = (self.headers.get("User-Agent") or "").strip()
        low = ua.lower()
        who = next((m for m in self.BOT_MARKS if m in low), "")
        if who:
            mark = f"  [{who}]"
        elif not ua:
            mark = "  [без UA]"
        elif not self.headers.get("Accept-Language"):
            # Незнакомый робот. Браузер всегда говорит, на каком языке хочет
            # страницу; тот, кто молчит, — программа. Показываем его имя целиком:
            # иначе в логе видно, что кто-то обошёл весь сайт, и не видно кто
            # (08-25: два таких обхода подряд, и опознать было нечем).
            mark = "  [%s]" % ua[:70]
        else:
            mark = ""
        sys.stderr.write("  %s%s\n" % (fmt % args, mark))

    # Кэш разведён по смыслу ответа, а не задан одной строкой на всё.
    # Раньше «no-store» стоял и на api, и на статике, и на героях — и при каждом
    # открытии страницы заново ехали 95 КБ кода плюс цветной герой 73-229 КБ.
    # На сайте виджет открывают со страницы, а скорость получения пользы канон
    # считает прямым фактором ранжирования.
    #   ответы движка   — no-store: лист собирается заново, кэшировать нечего;
    #   код и разметка  — no-cache: спрашивать сервер каждый раз, но по ETag
    #                     получать 304 без тела (после выката приедет новое);
    #   картинки банка  — сутки: имя файла = имя картинки, содержимое за ним
    #                     не меняется, а перерисовку переживёт одна ночь.
    CACHE_LIVE = "no-store"
    CACHE_CODE = "no-cache"
    CACHE_PICT = "public, max-age=86400"

    def _send(self, code: int, body: bytes, ctype: str,
              cache: str = CACHE_LIVE, etag: str = "") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        if etag:
            self.send_header("ETag", etag)
        self.end_headers()
        # На HEAD тело не отправляется — так велит HTTP. Заголовки при этом те
        # же, что у GET, поэтому один код обслуживает оба метода.
        if self.command != "HEAD":
            self.wfile.write(body)

    def _cached(self, body: bytes, ctype: str, cache: str) -> None:
        """Отдать файл с ETag; если у браузера уже такой — ответить 304 без тела."""
        etag = '"%s"' % hashlib.md5(body).hexdigest()[:16]
        if self.headers.get("If-None-Match") == etag:
            self.send_response(304)
            self.send_header("Cache-Control", cache)
            self.send_header("ETag", etag)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self._send(200, body, ctype, cache, etag)

    def _json(self, payload: Dict[str, Any], code: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def _redirect(self, location: str) -> None:
        """Один 301, а не цепочка.

        Цепочка редиректов — чужая набитая шишка: http://www.site → https://www.site
        → https://site это два перехода там, где хватает одного. Поэтому всякий
        неканонический адрес отправляется СРАЗУ на конечный.
        """
        self.send_response(301)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.send_header("Cache-Control", self.CACHE_LIVE)
        self.end_headers()

    def _give_file(self, token: str) -> None:
        """Отдать придержанный файл как ВЛОЖЕНИЕ и забыть его."""
        got = unstash(token)
        if not got:
            # Промахнуться тут можно только одним способом — вернуться на
            # старую ссылку через час. Говорим человеческим языком и не пугаем:
            # лист никуда не делся, он на экране.
            self._send(410, ("<!doctype html><meta charset=utf-8>"
                             "<title>Ссылка устарела</title>"
                             "<p style='font:16px/1.5 system-ui;padding:2rem'>"
                             "Эта ссылка на файл уже сработала или устарела.<br>"
                             "Вернитесь на страницу и нажмите «Скачать» ещё раз — "
                             "лист никуда не делся.").encode("utf-8"),
                       "text/html; charset=utf-8")
            return
        name, ctype, data = got
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        # Имя у нас кириллицей («занятие-Р.pdf»), а в заголовке разрешён только
        # ASCII. Поэтому имя идёт дважды: голым запасным вариантом и по RFC 5987
        # — второй понимают все нынешние браузеры, включая мобильный Safari.
        stem, _, ext = name.rpartition(".")
        ascii_name = re.sub(r"[^A-Za-z0-9._-]", "", stem).strip("-._")
        ascii_name = (ascii_name or "list") + "." + ext
        self.send_header(
            "Content-Disposition",
            "attachment; filename=\"%s\"; filename*=UTF-8''%s"
            % (ascii_name, urllib.parse.quote(name)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def _static(self, name: str) -> None:
        path = os.path.join(HERE, name)
        if not os.path.isfile(path) or os.path.dirname(path) != HERE:
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
            ".svg": "image/svg+xml; charset=utf-8",
        }.get(os.path.splitext(name)[1], "application/octet-stream")
        with open(path, "rb") as fh:
            data = fh.read()
        # В экран виджета счётчик вставляется на лету: файл лежит в репозитории,
        # а номер счётчика — учётная запись автора и живёт в окружении.
        # `in_frame_guard=True` обязателен: виджет открывается ещё и в рамке
        # страницы сайта, и без оговорки один заход считался бы дважды.
        if name == "index.html":
            code = SITE.analytics(in_frame_guard=True)
            if code:
                data = data.replace(b"</head>", code.encode("utf-8") + b"</head>", 1)
        self._cached(data, ctype, self.CACHE_CODE)

    # Герои отдаются ФАЙЛОМ, а не встраиваются в лист base64. Причина в весе:
    # ч/б герой весит 2-3 КБ и встраивается даром, а цветной 73-229 КБ —
    # сглаживание краёв делает «плоский цвет» многоцветным. Файлом цвет
    # не стоит почти ничего: браузер берёт его один раз и держит сутки (CACHE_PICT).
    _GEROI = {"colour": "geroi", "bw": "geroi_bw"}

    def _hero(self, kind: str, name: str) -> None:
        folder = self._GEROI.get(kind)
        # имя приходит из адреса — пускаем только то, что реально лежит в банке
        root = os.path.abspath(os.path.join(HERE, "..", "pictures", folder or ""))
        path = os.path.abspath(os.path.join(root, name))
        if not folder or os.path.dirname(path) != root or not os.path.isfile(path):
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        with open(path, "rb") as fh:
            self._cached(fh.read(), "image/png", self.CACHE_PICT)

    def _img(self, name: str) -> None:
        """Картинка страницы сайта. Кэш длинный: снимок листа не меняется."""
        root = os.path.join(HERE, "img")
        path = os.path.abspath(os.path.join(root, name))
        if os.path.dirname(path) != root or not os.path.isfile(path):
            self._not_found()
            return
        ctype = {".png": "image/png", ".jpg": "image/jpeg",
                 ".svg": "image/svg+xml"}.get(os.path.splitext(name)[1], "")
        if not ctype:
            self._not_found()
            return
        with open(path, "rb") as fh:
            self._cached(fh.read(), ctype, self.CACHE_PICT)

    def _bank(self, folder: str, name: str) -> None:
        """Картинка из банка `pictures/<folder>/`. Кэш длинный, как у героев."""
        root = os.path.abspath(os.path.join(HERE, "..", "pictures", *folder.split("/")))
        path = os.path.abspath(os.path.join(root, name))
        if os.path.dirname(path) != root or not os.path.isfile(path):
            self._not_found()
            return
        with open(path, "rb") as fh:
            self._cached(fh.read(), "image/png", self.CACHE_PICT)

    def _body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    # — маршруты —

    def _canonical_host(self) -> str | None:
        """Единственный адрес, по которому сайт живёт. Всё прочее — 301 сюда.

        Домена у проекта два: `logozvuk.com` — сайт, `logozvuk.ru` — защитная
        покупка. Два домена с одним содержимым это дублирование, и оно бьёт по
        выдаче; поэтому второй не показывает копию сайта, а отдаёт 301. Тем же
        кодом снимается и `www`. Локально (SITE_URL не задан) проверка молчит —
        иначе разработка ушла бы в вечный редирект.
        """
        if SITE.SITE_URL.startswith("http://localhost"):
            return None
        return urllib.parse.urlsplit(SITE.SITE_URL).netloc or None

    def do_GET(self) -> None:            # noqa: N802
        split = urllib.parse.urlsplit(self.path)
        path, query = split.path, split.query

        # 1. чужой хост (logozvuk.ru, www) — сразу на канонический, одним прыжком
        canon = self._canonical_host()
        if canon:
            host = (self.headers.get("Host") or "").split(":")[0]
            if host and host != canon:
                tail = f"?{query}" if query else ""
                self._redirect(f"{SITE.SITE_URL}{path}{tail}")
                return

        # 2. статика и ответы движка
        if path in ("/app.css", "/app.js", "/site.css"):
            self._static(path.lstrip("/"))
            return
        # Браузеры и превью-боты просят /favicon.ico независимо от того, что
        # объявлено в разметке. Отдаём один и тот же SVG на оба адреса, чтобы
        # 404 не сыпался на каждой странице.
        if path in ("/favicon.ico", "/favicon.svg"):
            self._static("favicon.svg")
            return
        # Готовый лист — забирается одним переходом по одноразовому ключу.
        # Почему так, а не ответом на сам запрос — см. `stash`.
        if path.startswith("/file/"):
            self._give_file(path[len("/file/"):])
            return
        # Иллюстрации страниц сайта — снимки НАСТОЯЩИХ листов, снятые с движка
        # (см. tools/snimki_listov.py). Канон требует минимум три иллюстрации на
        # страницу и называет картинку фундаментом статьи, а не украшением.
        if path.startswith("/img/"):
            self._img(urllib.parse.unquote(path[len("/img/"):]))
            return
        # Банк спрайтов сцены: предметы фона отдаются файлом, как и герои.
        # Встраивать их в лист нельзя — сцена «трава» кладёт 53 предмета.
        if path.startswith("/fony/"):
            _rest = urllib.parse.unquote(path[len("/fony/"):])
            _kind = "fony"
            for _sub in ("colour/", "bw/"):
                if _rest.startswith(_sub):
                    _kind, _rest = "fony/" + _sub[:-1], _rest[len(_sub):]
                    break
            self._bank(_kind, _rest)
            return
        # Банк ЗВУКОВОЙ ДОРОЖКИ (08-26): виды героев, цели и листы-спирали.
        # Две папки, `colour` и `bw`, и вторая СНЯТА с первой — не рисовалась
        # отдельно (закон дома: рисуем цветное, ч/б снимаем технически).
        if path.startswith("/metki/"):
            parts = path.split("/")          # ['', 'metki', <colour|bw>, <file>]
            if len(parts) == 4 and parts[2] in ("colour", "bw"):
                self._bank("metki/" + parts[2], urllib.parse.unquote(parts[3]))
                return
        if path.startswith("/dorozhka/"):
            parts = path.split("/")          # ['', 'dorozhka', <colour|bw>, <file>]
            if len(parts) == 4 and parts[2] in ("colour", "bw"):
                self._bank("dorozhka/" + parts[2],
                           urllib.parse.unquote(parts[3]))
            else:
                self._not_found()
            return
        if path.startswith("/geroi/"):
            parts = path.split("/")          # ['', 'geroi', <kind>, <file>]
            if len(parts) == 4:
                self._hero(parts[2], urllib.parse.unquote(parts[3]))
            else:
                self._not_found()
            return
        if path == "/api/version":
            # ВЕРСИЯ КОДА, ОТДАННОГО БРАУЗЕРУ. Заведена 08-26, вопрос автора:
            # «человек, открывший вчера, работает со вчерашним кодом — можно
            # сделать так, чтобы что он ни нажал, обновляло до текущей?».
            # Можно: экран спрашивает эту ручку при каждом действии, и если
            # версия сменилась — перезагружается сам.
            # Считаем ПО СОДЕРЖИМОМУ трёх файлов экрана, а не по времени сборки:
            # на Amvera образ пересобирается и от коммита, который экрана не
            # касался, — версия не должна дёргаться зря.
            self._json({"v": app_version()})
            return
        if path == "/api/config":
            self._json(config())
            return
        if path == "/api/method":
            # Счётчики тиров сняты 2026-08-10: логопеду нужна пометка у
            # конкретной строки, а не арифметика по всей справке.
            self._json(method.as_json())
            return

        # 3. виджет живёт в КАТАЛОГЕ /app/, а не на поддомене: каталог переливает
        #    больше веса. Корень принадлежит сайту.
        if path in ("/app", "/app/"):
            self._static("index.html")
            return

        # 4. служебные файлы поиска
        if path == "/robots.txt":
            self._send(200, SITE.robots_txt(), "text/plain; charset=utf-8",
                       self.CACHE_CODE)
            return
        if path == "/sitemap.xml":
            self._send(200, SITE.sitemap_xml(), "application/xml; charset=utf-8",
                       self.CACHE_CODE)
            return

        # 5. страницы сайта
        slug = path.strip("/")
        page = SITE.BY_SLUG.get(slug)

        if slug == "":
            # Пока главная — черновик, корень отдаёт виджет, как и до сайта:
            # прод не должен сломаться из-за того, что текст ещё не написан.
            home = SITE.BY_SLUG.get("")
            if home and not home.get("draft"):
                self._send(200, SITE.render(home), "text/html; charset=utf-8",
                           self.CACHE_CODE)
            else:
                self._static("index.html")
            return

        if page and not page.get("draft"):
            # Форма адреса ровно одна — со слешем на конце. Второй вид отдаёт
            # один 301, чтобы сайт не ссылался сам на свой дубль.
            if not path.endswith("/"):
                # Относительный Location законен и работает и локально, и на
                # проде: канонический хост уже обеспечен шагом 1 выше.
                tail = f"?{query}" if query else ""
                self._redirect(f"/{slug}/{tail}")
                return
            self._send(200, SITE.render(page), "text/html; charset=utf-8",
                       self.CACHE_CODE)
            return

        # Черновик снаружи неотличим от несуществующей страницы — это и нужно:
        # полупустая страница, попавшая в индекс, тратит бюджет обхода.
        self._not_found()

    def _not_found(self) -> None:
        self._send(404, SITE.render_404(), "text/html; charset=utf-8", "no-store")

    def do_HEAD(self) -> None:           # noqa: N802
        """То же, что GET, но без тела.

        Раньше отвечали 501. Этим методом стучатся превью-боты мессенджеров и
        мониторинги доступности, а ссылку логопеды получат в Telegram — карточка
        ссылки не должна ломаться на ровном месте (08-12, живой замер на Railway).
        """
        self.do_GET()

    def do_POST(self) -> None:           # noqa: N802
        path = self.path.split("?")[0]
        try:
            data = self._body()
        except Exception:
            self._json({"ok": False, "kind": "input",
                        "message": "не разобрал запрос"}, 400)
            return
        # тело может быть чем угодно — списком, числом, null; дальше по коду
        # всюду .get(), поэтому приводим здесь, а не ловим AttributeError в 500
        if not isinstance(data, dict):
            self._json({"ok": False, "kind": "input",
                        "message": "ожидался объект с настройками"}, 400)
            return

        try:
            if path == "/api/otzyv":
                # Отзыв принимается раньше всех прочих веток намеренно: он ничего
                # не считает и не зависит от движка. Если лист не собрался — тем
                # более важно, чтобы человеку было куда об этом сказать.
                self._json(OT.take(data))

            elif path == "/api/sheet":
                sound = str(data.get("sound", "р"))
                typ = str(data.get("typ", "direct"))
                err = validate(sound, typ=typ)
                if err:
                    self._json({"ok": False, "kind": "input", "message": err}, 400)
                    return
                aud = str(data.get("audience", "home"))
                if aud not in ("home", "lesson"):
                    aud = "home"
                self._json(build_sheet(
                    sound, typ, profile_str(data.get("profile")),
                    sheet_no=as_int(data.get("sheet_no"), 1, low=1),
                    seed=as_int(data.get("seed"), 0),
                    audience=aud,
                    game=str(data.get("game") or ""),
                    colour=bool(data.get("colour")),
                ))

            elif path == "/api/pdf":
                # НАСТОЯЩИЙ PDF, а не окно печати.
                #
                # Браузер не даёт выбрать «Сохранить как PDF» программно — это
                # защита от подмены, одинаковая везде. Ставить headless Chrome в
                # наш образ дорого (+300 МБ и другой тариф), писать свой
                # отрисовщик — значит завести ВТОРУЮ вёрстку листа, вечно
                # расходящуюся с первой.
                #
                # Выход нашёл автор 08-24: у него уже работает свой Gotenberg —
                # тот, что обслуживает расширение save-chatgpt-as-pdf. Это
                # Chromium под капотом, то есть лист печатается ровно тем же
                # движком, что и в браузере, и вёрстка одна на всё.
                #
                # HTML приходит ОТ КЛИЕНТА, из документа рамки, — значит в PDF
                # уходят и правки логопеда. Пересобирать лист на сервере нельзя:
                # правок он не знает.
                html = str(data.get("html") or "")
                if not html.strip():
                    self._json({"ok": False, "kind": "input",
                                "message": "нечего сохранять"}, 400)
                    return
                try:
                    pdf = to_pdf(html)
                except Exception as exc:
                    self._json({"ok": False, "kind": "network",
                                "message": human.pdf_failed(str(exc))}, 200)
                    return
                # Готовый PDF не отдаём в ответ, а придерживаем и возвращаем
                # адрес: скачать его должен ПЕРЕХОД по настоящей ссылке, иначе
                # айфон открывает лист вместо того, чтобы сохранить (см. `stash`).
                name = file_name(data.get("name"), "pdf")
                self._json({"ok": True,
                            "url": "/file/" + stash(pdf, name, "application/pdf"),
                            "name": name})
                return

            elif path == "/api/word":
                # Word собирает САМА страница — она умеет переложить сетку листа
                # в таблицы, а сервер про экранную вёрстку ничего не знает.
                # Сюда готовый документ приходит только затем, чтобы уехать
                # обратно вложением: путь скачивания в инструменте один на все
                # форматы. Иначе айфон был бы починен для PDF и сломан для Word.
                html = str(data.get("html") or "")
                if not html.strip():
                    self._json({"ok": False, "kind": "input",
                                "message": "нечего сохранять"}, 400)
                    return
                # Метка порядка байт: без неё Word открывает кириллицу кракозябрами.
                body = ("\ufeff" + html).encode("utf-8")
                name = file_name(data.get("name"), "doc")
                self._json({"ok": True,
                            "url": "/file/" + stash(
                                body, name, "application/msword"),
                            "name": name})
                return

            elif path == "/api/track_types":
                # Какие типы слога дорожка умеет ДЛЯ ЭТОГО РЕБЁНКА.
                #
                # Зачем отдельная ручка. `/api/config` считается один раз при
                # загрузке и на ПУСТОМ профиле: до 08-23 это было безвредно —
                # пределы дорожки были чисто жанровыми. Со стечениями предел
                # стал ДАННЫМИ: законна ли рамка, решает профиль ребёнка. Кнопки
                # при этом продолжали гореть все пять, что бы логопед ни отметил
                # («выбрал кучу звуков, а где звук в слоге везде есть» — автор).
                # Это прямое нарушение закона 12: пределы объявляются ЗАРАНЕЕ.
                # Конфиг целиком пересчитывать на каждый чип нельзя — он собирает
                # пробные листы по всем звукам; здесь считается только дорожка.
                sound = str(data.get("sound", "р"))
                if sound not in C.WORDS_BY_SOUND:
                    self._json({"ok": False, "kind": "input",
                                "message": f"звука [{sound}] в генераторе нет"}, 400)
                    return
                prof = S._expand_profile(",".join(data.get("profile") or []))
                types: Dict[str, Any] = {}
                for typ in C.SYL_TYPES:
                    reason = CAP.block_reason("track", sound, typ)
                    if not reason and typ in ("cluster_onset", "cluster_coda"):
                        if not C.cluster_frames_for(sound, typ, prof):
                            reason = "no_clean_cluster"
                    types[typ] = {"ok": not reason,
                                  "why": human.why_syllable(
                                      reason, CAP.probe_syllable(sound, typ), "track")}
                self._json({"ok": True, "types": types})

            elif path == "/api/track":
                sound = str(data.get("sound", "р"))
                typ = str(data.get("typ", "direct"))
                if sound not in C.WORDS_BY_SOUND:
                    self._json({"ok": False, "kind": "input",
                                "message": f"звука [{sound}] в генераторе нет"}, 400)
                    return
                bad = unsupported("track", sound, typ)
                if bad:
                    self._json(bad, 200)
                    return
                scene = data.get("scene")
                if scene is not None:
                    scene = str(scene)
                    if scene and scene not in SCN.SCENES:
                        scene = None
                # Профиль ребёнка доведён до дорожки 08-23: без него стечения
                # были запрещены наглухо («второй согласный не проверить»), а с
                # ним проверять есть по чему — тем же способом, что на листе.
                prof = S._expand_profile(",".join(data.get("profile") or []))
                try:
                    t = T.build_track(sound, typ,
                                      seed=as_int(data.get("seed"), 0),
                                      scene=scene, profile=prof)
                except T.TrackError as exc:
                    self._json({"ok": False, "kind": "engine",
                                "message": str(exc)}, 200)
                    return
                self._json({
                    "ok": True,
                    "html": T.render_track(t, colour=bool(data.get("colour"))),
                    "warnings": {"blocking": [], "notes": []},
                    "stats": {"kind": "track",
                              "scene": t["meta"].get("scene", ""),
                              "cells": t["meta"]["n_cells"],
                              "vowels": t["meta"]["vowels"],
                              "type_label": t["meta"]["type_label"]},
                })

            elif path == "/api/phrases":
                # Словосочетания «прил. + сущ.» — ✅ Спивак, «Повтори
                # словосочетания». Отдельный лист, а не блок листа: замер
                # 08-09 показал, что на А4 автоматизации места нет (см.
                # phrases.py). Профиль здесь работает на ОБЕ части пары.
                sound = str(data.get("sound", "р"))
                if sound not in C.WORDS_BY_SOUND:
                    self._json({"ok": False, "kind": "input",
                                "message": f"звука [{C.ph.sound_label(sound)}] "
                                           f"в генераторе нет"}, 400)
                    return
                prof = S._expand_profile(",".join(data.get("profile") or []))
                try:
                    ph_sheet = PH.build_phrases_sheet(
                        sound=sound, profile=prof,
                        n=min(PH.MAX_PHRASES,
                              as_int(data.get("n"), PH.MAX_PHRASES,
                                     low=PH.MIN_PHRASES)),
                        seed=as_int(data.get("seed"), 0))
                except PH.PhrasesError as exc:
                    self._json({"ok": False, "kind": "input",
                                "message": str(exc)}, 400)
                    return
                self._json({
                    "ok": True,
                    "html": PH.render_phrases(ph_sheet),
                    "warnings": human.split([], ph_sheet["warnings"]),
                    "stats": {"kind": "phrases",
                              "n": ph_sheet["meta"]["n"],
                              "items": [i["text"] for i in ph_sheet["items"]]},
                })

            elif path == "/api/rasskaz":
                # Готовый рассказ для пересказа — то, о чём дословно просила
                # логопед («генерация рассказов»). Текст из текстотеки, каждый
                # проверен валидатором норм; для профиля ребёнка отдаются
                # только чистые — иначе кнопка обещала бы то, чего нет.
                sound = str(data.get("sound", "р"))
                if sound not in C.WORDS_BY_SOUND:
                    self._json({"ok": False, "kind": "input",
                                "message": f"звука [{C.ph.sound_label(sound)}] "
                                           f"в генераторе нет"}, 400)
                    return
                prof = S._expand_profile(",".join(data.get("profile") or []))
                try:
                    rz = RZ.build_rasskaz(sound=sound, profile=prof,
                                          text_id=(str(data.get("text")) if data.get("text") else None))
                except RZ.RasskazError as exc:
                    self._json({"ok": False, "kind": "engine",
                                "message": str(exc)}, 200)
                    return
                self._json({
                    "ok": True,
                    "html": RZ.render_rasskaz(rz),
                    "warnings": [],
                    "stats": {"kind": "rasskaz",
                              "text": rz["text"]["id"],
                              "title": rz["text"]["title"],
                              "options": rz["options"],
                              "sentences": rz["stat"]["sentences"],
                              "words": rz["stat"]["words"],
                              "share": rz["stat"]["share_target"]},
                })

            elif path == "/api/story":
                # «Сочини рассказ» — лист-СЦЕНАРИЙ взрослому: тема, опорные
                # слова, глаголы. Готового текста здесь нет намеренно: движок
                # умеет проверять чистоту только своих слов, а не связного
                # текста (блокер записан 08-04). Слога у материала нет — он
                # собирается из слов, как словосочетания и лабиринт.
                sound = str(data.get("sound", "р"))
                if sound not in C.WORDS_BY_SOUND:
                    self._json({"ok": False, "kind": "input",
                                "message": f"звука [{C.ph.sound_label(sound)}] "
                                           f"в генераторе нет"}, 400)
                    return
                prof = S._expand_profile(",".join(data.get("profile") or []))
                try:
                    st = ST.build_story(
                        sound=sound, profile=prof,
                        theme=(str(data.get("theme")) if data.get("theme") else None),
                        seed=as_int(data.get("seed"), 0))
                except ST.StoryError as exc:
                    self._json({"ok": False, "kind": "engine",
                                "message": str(exc)}, 200)
                    return
                self._json({
                    "ok": True,
                    "html": ST.render_story(st),
                    "warnings": human.split([], st["warnings"]),
                    "stats": {"kind": "story",
                              "theme": st["meta"]["theme"],
                              "themes": st["meta"]["themes"],
                              "n_sets": st["meta"]["n_sets"],
                              "n_words": st["meta"]["n_words"],
                              "items": [w for g in st["sets"] for w in g]},
                })

            elif path == "/api/propisi":
                sound = str(data.get("sound", "р"))
                typ = str(data.get("typ", "direct"))
                if sound not in C.WORDS_BY_SOUND:
                    self._json({"ok": False, "kind": "input",
                                "message": f"звука [{C.ph.sound_label(sound)}] "
                                           f"в генераторе нет"}, 400)
                    return
                notes: List[str] = []
                mode = str(data.get("mode") or "syllable")
                if mode not in PR.MODES:
                    mode = "syllable"
                # Раньше несовместимый тип слога здесь МОЛЧА подменялся на
                # прямой: логопед выбирал АЛА, получал ЛА и узнавал об этом
                # мелкой строкой под листом. Подмена снята 08-10 — материал не
                # решает за логопеда, а показывает, что умеет. На ступени
                # «только звук» слога нет вовсе, и запрет там ни при чём.
                if mode != "isolated":
                    bad = unsupported("propisi", sound, typ)
                    if bad:
                        self._json(bad, 200)
                        return
                if mode == "isolated":
                    # ⚠ Строка «Ребёнок тянет один звук, гласной в конце нет.
                    # Тип слога здесь ни на что не влияет» СНЯТА 08-25 по слову
                    # автора: на самом листе уже написано, что делать, а объяснять
                    # рядом с материалом устройство интерфейса — лишнее.
                    # Слога на этой ступени нет вовсе — движку всё равно нужен
                    # какой-то тип, берём прямой. Это не подмена выбора:
                    # на бумаге типа слога не видно.
                    if typ not in PR.PROPISI_TYPES:
                        typ = "direct"
                # Конструктор дорожек (08-26): сколько их на листе, решает
                # логопед. Одна переключает СЕМЬЮ листа на спираль — см.
                # `propisi.build_propisi`.
                p = PR.build_propisi(sound, typ,
                                     vowel=data.get("vowel") or None,
                                     seed=as_int(data.get("seed"), 0),
                                     mode=mode,
                                     # Профиль ребёнка нужен стечениям: он и
                                     # решает, законна ли рамка (08-26).
                                     profile=profile_str(data.get("profile")),
                                     rows=as_int(data.get("rows"), 3, low=1),
                                     # ⚠ 08-26: `line` с экрана больше не
                                     # приходит — ручка формы линии снята
                                     # вместе с пунктиром. Движок берёт
                                     # умолчание «плавная».
                                     frame_pick=str(data.get("frame") or ""),
                                     colour=bool(data.get("colour")))
                self._json({
                    "ok": True,
                    "html": PR.render_propisi(p, colour=bool(data.get("colour"))),
                    "syllable": p["meta"]["syllable"],
                    "warnings": {"blocking": [], "notes": notes},
                    "stats": {"kind": "propisi",
                              "mode": p["meta"]["mode"],
                              "vowel": p["meta"]["vowel"],
                              "vowels": p["meta"].get("vowels") or [],
                              "rows": p["meta"]["n_rows"],
                              "family": p["meta"].get("family", "strips"),
                              "n_dorozhek": p["meta"].get("rows", 3),
                              "line": p["meta"].get("line", "wave"),
                              "frame": p["meta"].get("frame", ""),
                              "frames": p["meta"].get("frames", []),
                              "type_label": p["meta"]["type_label"],
                              "syllable": p["meta"]["syllable"],
                              "image_name": p["meta"]["image_name"],
                              "tasks": [l["task_label"] for l in p["lines"]]},
                })

            elif path == "/api/maze":
                sound = str(data.get("sound", "р"))
                position = str(data.get("position", "initial"))
                err = validate(sound, position=position)
                if err:
                    self._json({"ok": False, "kind": "input", "message": err}, 400)
                    return
                self._json(build_maze(
                    sound, position, profile_str(data.get("profile")),
                    seed=as_int(data.get("seed"), 0),
                    colour=bool(data.get("colour")),
                ))
            else:
                self._send(404, b"not found", "text/plain; charset=utf-8")

        # Движок сам себе противоречит — логопеду это показывать нельзя.
        except (C.PurityViolation, C.CrosscutViolation) as e:
            traceback.print_exc()
            self._json({"ok": False, "kind": "internal",
                        "message": "внутренняя ошибка генератора, лист не выдан",
                        "detail": str(e)}, 500)

        # Всё остальное из движка написано по-русски и с подсказкой,
        # чем расширить — показываем логопеду ДОСЛОВНО.
        except (C.ContentError, M.MazeError, T.TrackError) as e:
            thing = "дорожка" if path.endswith("track") else (
                "лабиринт" if path.endswith("maze") else "лист")
            self._json({"ok": False, "kind": "engine",
                        "message": human.error_message(str(e), thing),
                        "raw": str(e)}, 200)

        except SystemExit as e:
            self._json({"ok": False, "kind": "input",
                        "message": f"генератор отказался от таких настроек: {e}"}, 400)

        except Exception as e:
            traceback.print_exc()
            self._json({"ok": False, "kind": "internal",
                        "message": f"{type(e).__name__}: {e}"}, 500)


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="веб-интерфейс генератора листов")
    # На хостинге порт и адрес приходят из окружения: HF Space ждёт 7860 и
    # 0.0.0.0, локально остаётся 8760 на localhost — снаружи не видно.
    ap.add_argument("--port", type=int,
                    default=int(os.environ.get("PORT", 8760)))
    ap.add_argument("--host",
                    default=os.environ.get("HOST", "127.0.0.1"))
    args = ap.parse_args(argv)

    config()   # прогреть кэши и подписи кнопок до первого запроса
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Генератор логопедических листов: http://{args.host}:{args.port}")
    print(f"  звуки: {', '.join(sorted(C.WORDS_BY_SOUND))} · движок: {ENGINE}")
    print("  Ctrl+C — остановить")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\nостановлен")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
