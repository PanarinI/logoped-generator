"""Канал обратной связи от логопеда — приём, хранение, пересылка автору.

Зачем отдельный модуль. Инструмент вышел к живым людям 2026-08-25, и без слов
пользователя он дальше не растёт: весь нынешний лист вырос из переписки с одним
логопедом (`ГОЛОСА.md`). Канал должен существовать ДО прихода людей — мнение,
которому некуда деться, не возвращается.

Два входа, разные по цене для человека:
  · ТИХАЯ ССЫЛКА «На листе что-то не так?» — висит всегда, ничего не перекрывает,
    открывается свободным полем. Пишет тот, кто сам захотел;
  · ОДИН ВОПРОС после второго скачивания — «Вы дадите этот лист ребёнку?»
    (формулировка автора 08-24). Спрашивает про ДЕЙСТВИЕ, а не про чувство:
    канон буткемпа предупреждает, что «оцените нас» даёт эмоцию, а развёрнутая
    критика приходит примерно от 5 % отвечающих.

Куда падает. Сначала СВОЙ файл, потом — Google-форма автора. Порядок важен:
своя запись не зависит ни от сети, ни от чужого сервиса, и терять её нельзя.
Файл лежит на постоянном диске Amvera (`/data`, `persistenceMount` в
`amvera.yaml`) — он переживает пересборку образа, в отличие от всего остального.

Почему пересылку делает сервер, а не браузер. Отправка формы из страницы
уходит в `no-cors`: ответ не читается, и мы не знаем, дошло ли. Сервер видит код
ответа Google и может честно сказать в лог, что не дошло.

Персональные данные не собираются: ни имени, ни почты, ни IP. Единственное поле,
куда человек может вписать контакт, — добровольное и называется своим именем.

Переменные окружения (Amvera → «Переменные»):
    GOOGLE_FORM_URL    полный адрес .../formResponse
    GOOGLE_FORM_FIELD  имя поля для текста, вида entry.123456789
    OTZYV_PATH         куда писать (по умолчанию /data/otzyvy.jsonl)
Пока переменных нет, канал работает как есть — пишет к себе.
"""

from __future__ import annotations

import json
import os
import threading
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List

STORE = os.environ.get("OTZYV_PATH", "/data/otzyvy.jsonl")
FORM_URL = os.environ.get("GOOGLE_FORM_URL", "").strip()
FORM_FIELD = os.environ.get("GOOGLE_FORM_FIELD", "").strip()

# Запасной путь: на машине автора каталога /data нет, и падать из-за этого
# канал не должен — иначе он не проверяется дома.
FALLBACK = os.path.join(os.path.dirname(os.path.abspath(__file__)), "otzyvy.jsonl")

# Причины, которые предлагает второй экран вопроса. Список закрытый: свободный
# текст рядом остаётся, но клик по готовой причине делают все, а пишут немногие.
REASONS = {
    "words": "слова не те",
    "few": "мало материала",
    "look": "оформление",
    "task": "не то задание",
    "other": "другое",
}

MAX_TEXT = 2000          # больше человек не пишет, а защита от мусора нужна
MAX_CONTACT = 200


def _path() -> str:
    d = os.path.dirname(STORE)
    if d and os.path.isdir(d) and os.access(d, os.W_OK):
        return STORE
    return FALLBACK


def _clean(value: Any, limit: int) -> str:
    return str(value or "").strip()[:limit]


def record(data: Dict[str, Any]) -> Dict[str, Any]:
    """Собрать запись из тела запроса. Ничего не додумывает — только чистит."""
    reasons: List[str] = []
    for key in (data.get("reasons") or []):
        k = str(key)
        if k in REASONS and k not in reasons:
            reasons.append(k)

    answer = str(data.get("answer") or "")
    if answer not in ("yes", "no", ""):
        answer = ""

    return {
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        # откуда пришло: "vopros" — полоса после второго скачивания,
        # "svobodno" — тихая ссылка
        "kind": "vopros" if answer else "svobodno",
        "answer": answer,
        "reasons": reasons,
        "text": _clean(data.get("text"), MAX_TEXT),
        "contact": _clean(data.get("contact"), MAX_CONTACT),
        # что было на экране в этот момент — без этого отзыв нечитаем:
        # «мало материала» на [Щ] и на [С] — это разные новости
        "sound": _clean(data.get("sound"), 8),
        "material": _clean(data.get("material"), 20),
        "profile": _clean(data.get("profile"), 80),
        "saves": int(data.get("saves") or 0),
    }


def store(rec: Dict[str, Any]) -> bool:
    try:
        with open(_path(), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return True
    except Exception as exc:                      # noqa: BLE001
        print(f"[отзыв] не записался: {exc}", flush=True)
        return False


def _human(rec: Dict[str, Any]) -> str:
    """Одна строка для Google-формы: там поле одно, а знать надо всё."""
    parts: List[str] = []
    if rec["answer"]:
        parts.append("дам ребёнку: да" if rec["answer"] == "yes"
                     else "дам ребёнку: нет")
    if rec["reasons"]:
        parts.append("что не так: " + ", ".join(REASONS[r] for r in rec["reasons"]))
    if rec["text"]:
        parts.append(rec["text"])
    where = " · ".join(x for x in (
        f"звук {rec['sound']}" if rec["sound"] else "",
        rec["material"],
        f"не поставлены {rec['profile']}" if rec["profile"] else "",
        f"скачиваний {rec['saves']}" if rec["saves"] else "",
    ) if x)
    if where:
        parts.append("[" + where + "]")
    if rec["contact"]:
        parts.append("связь: " + rec["contact"])
    return "\n".join(parts)


def forward(rec: Dict[str, Any]) -> None:
    """Переслать в Google-форму автора. Молча: человек уже получил «спасибо»."""
    if not FORM_URL or not FORM_FIELD:
        return
    body = urllib.parse.urlencode({FORM_FIELD: _human(rec)}).encode("utf-8")
    req = urllib.request.Request(
        FORM_URL, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "User-Agent": "logozvuk-otzyv/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            if r.status >= 400:
                print(f"[отзыв] Google ответил {r.status}", flush=True)
    except Exception as exc:                      # noqa: BLE001
        print(f"[отзыв] в форму не ушло: {exc}", flush=True)


def take(data: Dict[str, Any]) -> Dict[str, Any]:
    """Принять отзыв: сначала записать себе, потом переслать в фоне."""
    rec = record(data)
    if not (rec["text"] or rec["answer"] or rec["reasons"]):
        return {"ok": False, "kind": "input", "message": "пустой отзыв"}
    saved = store(rec)
    threading.Thread(target=forward, args=(rec,), daemon=True).start()
    return {"ok": True, "saved": saved}
