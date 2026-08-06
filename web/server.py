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
import json
import os
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
ENGINE = os.path.join(PROJECT, "logoped_slovar")
sys.path.insert(0, ENGINE)

import content as C          # noqa: E402
import sheet as S            # noqa: E402
import maze as M             # noqa: E402
import track as T            # noqa: E402
import propisi as PR         # noqa: E402
import phonetics as ph       # noqa: E402

sys.path.insert(0, HERE)
import method                # noqa: E402  — методическая цепочка для панели
import human                 # noqa: E402  — перевод машинных текстов на человеческий


# ═══════════════════════════════════════════════════════════════════════
#  СЛОВАРЬ ИНТЕРФЕЙСА
# ═══════════════════════════════════════════════════════════════════════

# Подписи кнопок звука. Апостроф — наша внутренняя запись мягкости; логопед
# пишет «Рь», и на экране должно стоять именно это (закон проекта: на экране
# нет ни одного слова, которое существует только у нас в коде).
SOUND_LABEL = {
    "р": "Р", "р'": "Рь", "л": "Л", "л'": "Ль",
    "с": "С", "с'": "Сь", "з": "З", "з'": "Зь",
    "ш": "Ш", "ж": "Ж", "щ": "Щ",
}

# Мягкие пары движок добавляет сам (нарушенный [л] почти всегда значит и [л']),
# поэтому логопеду показываем только твёрдые — просить отмечать «л» и «ль»
# отдельно бессмысленно, результат тот же.
PROFILE_OPTIONS: Tuple[Tuple[str, str], ...] = (
    ("с", "С"), ("з", "З"), ("ц", "Ц"),
    ("ш", "Ш"), ("ж", "Ж"), ("щ", "Щ"), ("ч", "Ч"),
    ("л", "Л"), ("р", "Р"), ("й", "Й"),
    ("к", "К"), ("г", "Г"), ("х", "Х"),
)

POSITION_LABEL = {
    "initial": "в начале слова",
    "medial": "в середине слова",
    "final": "в конце слова",
}

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


def build_sheet(sound: str, typ: str, prof: str,
                sheet_no: int = 1, seed: int = 0,
                audience: str = "home") -> Dict[str, Any]:
    """Канонный путь сборки листа. Возвращает готовый ответ для браузера.

    ВАЖНО про порядок. `render_sheet_ex` внутри себя зовёт `fit()`, а `fit`
    работает на ГЛУБОКОЙ КОПИИ и именно из копии выбрасывает слова, чтобы лист
    влез в А4 (sheet.py:447). Если считать слова по исходному `content`, число
    получится ДОвёрсточным: ров обещал бы 16 слов там, где на бумаге 14.
    Поэтому ужимаем сами, один раз, и дальше всё — и счёт, и канон-линтер, и
    рендер — идёт по ОДНОМУ И ТОМУ ЖЕ свёрстанному листу.
    """
    content, report = S.compose(sound, typ, prof, sheet_no=sheet_no, seed=seed)
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

    fitted, fit_warns = S.fit(content, S.CONTENT_H)
    html, _ = S.render_sheet_ex(
        fitted, meta,
        options={"stress": "non_obvious", "show_warnings": False,
                 "no_fit": True, "audience": audience},
    )

    words = words_on_sheet(fitted)

    # Браком лист называет НЕ регулярка по тексту предупреждений, а сам
    # канон-линтер проекта. Раньше здесь стоял поиск подстроки «правило 11» —
    # и он ловил её в СПРАВОЧНОМ тексте движка, объявляя браком чистый лист
    # ([Ш] + обратные слоги: 15 слов, линтер молчит, а печать блокировалась).
    blocking = list(S.lint(fitted, meta))
    notes = list(fitted.get("notes") or []) + list(fit_warns)
    if len(words) < MIN_WORDS_CANON and not blocking:
        blocking = [f"слов на листе {len(words)} — меньше канонического "
                    f"минимума {MIN_WORDS_CANON} (блок [4])"]

    stats = pool_stats(sound, prof)
    stats["on_sheet"] = len(words)

    rows = fitted.get("syllables", {}).get("rows", []) or []
    syllable = (rows[0].get("units") or [""])[0] if rows else ""

    return {
        "ok": True,
        "html": html,
        "stats": stats,
        # Наружу идут ТОЛЬКО человеческие тексты. Машинные — в raw, для нас.
        "warnings": human.split(blocking, notes),
        "syllable": syllable,
        "words": words,
        "sheet_no": sheet_no,
        "purity_scope": report.get("purity_scope", ""),
    }


def build_maze(sound: str, position: str, prof: str,
               seed: int = 0, service_cell: str = "question") -> Dict[str, Any]:
    m = M.build_maze(sound=sound, position=position, profile=prof,
                     seed=seed, service_cell=service_cell)
    html = M.render_maze(m, {"no_warnbox": True})
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
    out: Dict[str, List[Dict[str, str]]] = {}
    for snd in C.WORDS_BY_SOUND:
        items: List[Dict[str, str]] = []
        for typ in C.SYL_TYPES:
            try:
                content, _ = S.compose(snd, typ, "", sheet_no=1, seed=0)
                rows = content.get("syllables", {}).get("rows", []) or []
                syl = (rows[0].get("units") or [""])[0] if rows else ""
                items.append({
                    "typ": typ,
                    "syllable": syl.upper(),
                    "label": C.SYL_TYPE_LABEL.get(typ, typ),
                    "available": bool(syl),
                })
            except BaseException:
                items.append({"typ": typ, "syllable": "—",
                              "label": C.SYL_TYPE_LABEL.get(typ, typ),
                              "available": False})
        out[snd] = items
    return out


# ═══════════════════════════════════════════════════════════════════════
#  HTTP
# ═══════════════════════════════════════════════════════════════════════

CONFIG_CACHE: Dict[str, Any] = {}


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
        })
    return CONFIG_CACHE


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

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("  %s\n" % (fmt % args))

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, payload: Dict[str, Any], code: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def _static(self, name: str) -> None:
        path = os.path.join(HERE, name)
        if not os.path.isfile(path) or os.path.dirname(path) != HERE:
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        ctype = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "application/javascript; charset=utf-8",
        }.get(os.path.splitext(name)[1], "application/octet-stream")
        with open(path, "rb") as fh:
            self._send(200, fh.read(), ctype)

    def _body(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    # — маршруты —

    def do_GET(self) -> None:            # noqa: N802
        path = self.path.split("?")[0]
        if path == "/":
            self._static("index.html")
        elif path in ("/app.css", "/app.js"):
            self._static(path.lstrip("/"))
        elif path == "/api/config":
            self._json(config())
        elif path == "/api/method":
            payload = method.as_json()
            payload["counts"] = method.counts()
            self._json(payload)
        else:
            self._send(404, b"not found", "text/plain; charset=utf-8")

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
            if path == "/api/sheet":
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
                ))

            elif path == "/api/track":
                sound = str(data.get("sound", "р"))
                typ = str(data.get("typ", "direct"))
                if sound not in C.WORDS_BY_SOUND:
                    self._json({"ok": False, "kind": "input",
                                "message": f"звука [{sound}] в генераторе нет"}, 400)
                    return
                t = T.build_track(sound, typ,
                                  seed=as_int(data.get("seed"), 0))
                self._json({
                    "ok": True,
                    "html": T.render_track(t),
                    "warnings": {"blocking": [], "notes": []},
                    "stats": {"kind": "track",
                              "cells": t["meta"]["n_cells"],
                              "vowels": t["meta"]["vowels"],
                              "type_label": t["meta"]["type_label"]},
                })

            elif path == "/api/propisi":
                sound = str(data.get("sound", "р"))
                typ = str(data.get("typ", "direct"))
                if sound not in C.WORDS_BY_SOUND:
                    self._json({"ok": False, "kind": "input",
                                "message": f"звука [{C.ph.sound_label(sound)}] "
                                           f"в генераторе нет"}, 400)
                    return
                # Прописи строятся только на чистых слогах: в стечении второй
                # согласный, его чистоту без словаря не проверить. Тип со
                # стечением молча подменяем на прямой и говорим об этом.
                notes: List[str] = []
                if typ not in PR.PROPISI_TYPES:
                    notes.append(
                        "Для прописей взят прямой слог: в стечении есть второй "
                        "согласный, и генератор не может проверить, поставлен "
                        "ли он у ребёнка.")
                    typ = "direct"
                p = PR.build_propisi(sound, typ,
                                     vowel=data.get("vowel") or None,
                                     seed=as_int(data.get("seed"), 0))
                self._json({
                    "ok": True,
                    "html": PR.render_propisi(p),
                    "syllable": p["meta"]["syllable"],
                    "warnings": {"blocking": [], "notes": notes},
                    "stats": {"kind": "propisi",
                              "rows": p["meta"]["n_rows"],
                              "type_label": p["meta"]["type_label"],
                              "syllable": p["meta"]["syllable"],
                              "image_name": p["meta"]["image_name"],
                              "shapes": [l["shape_label"] for l in p["lines"]]},
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
