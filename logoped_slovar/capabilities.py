# -*- coding: utf-8 -*-
"""
capabilities.py — ЧТО КАКОЙ МАТЕРИАЛ УМЕЕТ. Один дом на весь генератор.

ЗАЧЕМ ЭТОТ ФАЙЛ ПОЯВИЛСЯ (2026-08-10, по разбору автора)
─────────────────────────────────────────────────────────────────────
Экран предлагал логопеду пять типов слога — ЛА · АЛ · АЛА · КЛА · АЛК — и
предлагал их всем материалам одинаково. А материалы разные: лист умеет пять,
слоговая дорожка три, звуковая дорожка два. Что происходило на несовпадении:

  • слоговая дорожка отказывалась фразой, где стояло слово «cluster_onset» —
    машинный код на экране логопеда (нарушение локального закона 3);
  • звуковая дорожка МОЛЧА подменяла выбор на прямой слог.

Оба поведения — из одного корня: правда о том, что материал умеет, лежала
внутри каждого материала, и экран узнавал её только постфактум, отказом. Здесь
она собрана в одном месте, чтобы экран мог погасить кнопку ДО нажатия.

ГРАНИЦА ФАЙЛА
─────────────────────────────────────────────────────────────────────
Здесь только запреты УСТРОЙСТВА материала (жанр) и ЯЗЫКА (оглушение) — то, что
известно заранее, без сборки. Хватит ли слов на лист — вопрос данных, а не
устройства; на него отвечает сама сборка (сервер пробует собрать и гасит
кнопку по результату).

Наружу идут КОДЫ причин, а не фразы: человеческий текст живёт в `web/human.py`
(локальный закон 3 — один дом у слова, которое видит логопед).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import content as C          # noqa: E402
import propisi as PR         # noqa: E402
import track as T            # noqa: E402


# Материалы, у которых слог вообще есть. У словосочетаний слога нет (они
# собираются из слов), у лабиринта вместо слога позиция звука — их здесь нет
# намеренно, а не по забывчивости.
SYLLABLE_MATERIALS: Dict[str, tuple] = {
    "sheet": tuple(C.SYL_TYPES),
    "track": tuple(T.TRACK_TYPES),
    "propisi": tuple(PR.PROPISI_TYPES),
}

# Коды причин. Текст — в web/human.py.
CLUSTER = "cluster"                # в стечении второй согласный
INTERVOCAL_LINE = "intervocal_line"  # гласная с обеих сторон линии
REVERSE_LINE = "reverse_line"      # линия ведёт К гласной, а не от неё
DEVOICED = "devoiced"              # звонкий в конце слова оглушается

CLUSTER_TYPES = ("cluster_onset", "cluster_coda")


def block_reason(material: str, sound: str, typ: str) -> str:
    """Код причины, по которой материал НЕ делает такой слог. Пусто = делает."""
    allowed = SYLLABLE_MATERIALS.get(material)
    if allowed is None:
        return ""
    typ = C.SYL_TYPES[0] if not typ else typ
    if typ not in allowed:
        if typ in CLUSTER_TYPES:
            return CLUSTER
        # Причины у «АЛА» и «АЛ» разные, и валить их в одну нельзя: у первого
        # гласная с обеих сторон линии, у второго линия пришлась бы ПОСЛЕ
        # гласной — а на всех найденных образцах она ведёт К ней (08-10).
        return REVERSE_LINE if typ == "reverse" else INTERVOCAL_LINE
    # Язык, а не жанр: у звонких в конце слова оглушение обязательно, и
    # обратный слог печатал бы «аж», а ребёнок читал бы [аш]. Проверяем ровно
    # тем же способом, что и сами материалы, — одной функцией движка.
    if typ == "reverse":
        probe = C.ortho(C._syllable_text(sound, C.SYL_VOWELS_TRACK[0], typ))
        if not C.syllable_keeps_sound(sound, probe):
            return DEVOICED
    return ""


def position_reason(sound: str, position: str) -> str:
    """Почему лабиринт не делает такую позицию звука. Пусто = делает.

    Та же болезнь, что и со слогами, только у лабиринта: кнопка «в конце
    слова» горела у [З], [Ж], [Щ], а лабиринт отказывался. У звонких причина
    не в картотеке, а в языке — слова, кончающегося на [З], не бывает вовсе.
    Нехватку слов ([Сь], [Щ]) отсюда не видно: это данные, их считает сборкой
    сервер.
    """
    if position != "final":
        return ""
    probe = C.ortho(C._syllable_text(sound, C.SYL_VOWELS_TRACK[0], "reverse"))
    return "" if C.syllable_keeps_sound(sound, probe) else DEVOICED


def probe_syllable(sound: str, typ: str) -> str:
    """Как выглядит такой слог у этого звука — «АЖ», «КЛА».

    Нужен, когда объясняем ОТКАЗ: лист на этом слоге может не собираться, и
    подписи кнопки нет, а сказать «АЖ читается как АШ» всё равно надо.

    У стечений слога здесь не будет, и это честно: сам согласный при стечении
    движок берёт из ОТОБРАННЫХ СЛОВ («КЛА» — из «клоун»). Слов нет — нет и
    слога; выдумывать его нельзя (иначе на экране встало бы «А»).
    """
    if typ in CLUSTER_TYPES:
        return ""
    try:
        return C.ortho(C._syllable_text(sound, C.SYL_VOWELS_TRACK[0], typ)).upper()
    except BaseException:
        return ""


def syllable_options(material: str, sound: str) -> List[Dict[str, Any]]:
    """Все типы слога для материала: [{typ, ok, reason}] в канонном порядке."""
    out: List[Dict[str, Any]] = []
    for typ in C.SYL_TYPES:
        why = block_reason(material, sound, typ)
        out.append({"typ": typ, "ok": not why, "reason": why})
    return out


def first_available(material: str, sound: str) -> str:
    """Первый тип слога, который материал на этом звуке действительно делает."""
    for opt in syllable_options(material, sound):
        if opt["ok"]:
            return str(opt["typ"])
    return ""
