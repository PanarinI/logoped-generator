# -*- coding: utf-8 -*-
"""
scenes.py — ФОН слоговой дорожки: сюжетная сцена, которую выбирает логопед.

Откуда взялось
─────────────────────────────────────────────────────────────────────
Дословная строка запроса Ольги Субботиной (`ГОЛОСА.md`): «Алгоритм должен
уметь менять **фон**, звук, слог в зависимости от запроса». Звук и слог
генератор менял с самого начала, фон — единственный параметр запроса, к
которому не подходили ни разу. На её фото 1 тропа со слогами лежит на
ПОДВОДНОЙ сцене: это не украшение, а сюжет, в котором ребёнок идёт.

Фон — КОНТЕКСТ ГЕРОЯ (решение автора 08-10)
─────────────────────────────────────────────────────────────────────
Сначала пять сцен предлагались всем одинаково, и логопед мог поставить мотору
море — машина оказывалась под водой. Напрашивался запрет, но запрет лечит
симптом: пара «комарик + море» не становится осмысленной оттого, что комарик
не тонет. Поэтому список не режется — он СОБИРАЕТСЯ: у каждого героя свои
миры, по два, и «без фона» доступно всегда (слово автора: чистая бумага —
законный выбор, а не отсутствие фона).

Сцена УКЛАДЫВАЕТСЯ ВОКРУГ ДОРОЖКИ (переработка 08-10)
─────────────────────────────────────────────────────────────────────
⚡ Раньше сцена рисовалась вслепую: она не знала, где идёт тропа и где стоят
кружки со слогами, и половина предметов оказывалась перекрыта. Автор: «было бы
здорово, если бы фон создавался с учётом дорожки — тогда он был бы органично
интегрирован».

Теперь так и есть. `scene_svg` принимает `avoid` — круги, занятые кружками
слогов и самой тропой, — и каждая сцена не рисует по абсолютным координатам, а
ПРОСИТ место: `cv.place(ширина, высота, зона)`. Место выдаётся только если оно
свободно и от дорожки, и от уже разложенных предметов сцены; не нашлось —
предмет не печатается вовсе. Отсюда два следствия:
  • ни один предмет больше не перекрывается кружком;
  • на разных листах одна сцена ложится по-разному — дорожка каждый раз своя.

Чем фон отличается от речевого материала — и почему это важно
─────────────────────────────────────────────────────────────────────
Фильтр чистоты по профилю ребёнка сюда НЕ применяется, и это не поблажка:
ребёнок сцену не НАЗЫВАЕТ, он в ней находится. Называет он только слоги в
кружках. Ровно та же граница записана у лабиринта («ребёнок картинку не
называет, а узнаёт») и в `content['purity_scope']`.
Отсюда прямое следствие: в сцене не должно быть предмета, который просится
быть названным — крупного, одиночного, в центре. Сцена идёт по краям и фоном,
мелко и много, чтобы читаться как среда, а не как задание.

Ремесло печати (из-за чего именно такие числа)
─────────────────────────────────────────────────────────────────────
  • сцена рисуется ТОНКО (~0.95) и БЛЕДНО (opacity ~0.42): на ч/б принтере
    жирная фоновая линия спорит с кружком, и слог перестаёт читаться. Числа
    подняты 08-10 с 0.8/0.30 — по глазам автора сцены «читались непонятно с
    первого взгляда»; выше поднимать нельзя, начинает спорить с тропой;
  • узнаётся СИЛУЭТ, а не текстура: ёлка, дом, волна, камыш читаются, а
    плитка и рёбра ворот на бледной тонкой линии дают шум (проверено 08-10);
  • кружки уже залиты белым, поэтому сцена может идти насквозь — слоги
    «пробивают» её, как на образце Ольги;
  • ни одной заливки серым: серое пятно на дешёвом принтере станет грязью.
"""

from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

__all__ = ["scene_svg", "SCENES", "SCENE_LABELS", "WORLDS",
           "worlds_for", "default_scene", "fits", "path_word"]

SCENE_LABELS: Dict[str, str] = {
    "": "без фона",
    "море": "море",
    "лес": "лес",
    "небо": "небо",
    "дорога": "дорога",
    "аэродром": "аэродром",
    "город": "город",
    "двор": "двор",
    "гараж": "гараж",
    "пруд": "пруд",
    "трава": "трава",
    "камни": "камни",
    "ванная": "ванная",
    "прихожая": "прихожая",
}

# Миры героя: первый — умолчание. Почему по два, а не по три: три давали
# натянутые пары («щётка во дворе»), а материал не выигрывает от выбора между
# хорошим и притянутым.
WORLDS: Dict[str, Tuple[str, ...]] = {
    "мотор": ("дорога", "город"),
    "моторчик": ("дорога", "город"),
    # «Море» самолёту не подошло: над волнами он читается тонущим, а не летящим
    # (глаза автора 08-10). Аэродром — место, где самолёт бывает на самом деле.
    "самолёт": ("небо", "аэродром"),
    "самолётик": ("небо", "аэродром"),
    "насос": ("двор", "гараж"),
    "насосик": ("двор", "гараж"),
    "комарик": ("лес", "пруд"),
    "змея": ("трава", "камни"),
    "жук": ("трава", "лес"),
    "щётка": ("ванная", "прихожая"),
}

# КАК НАЗЫВАЕТСЯ ПУТЬ. Одно слово «тропа» стояло на всех листах, и «проведи
# щётку по тропе» звучало сюрреально (поймано автором 08-10). Слово берётся от
# сцены: в лесу тропинка, на дороге дорога, в комнате дорожка. Падежи таблицей,
# а не правилом, — их всего два и они разные («по дороге», «пройди дорогу»).
PATH_WORD: Dict[str, Dict[str, str]] = {
    "лес": {"dative": "тропинке", "accusative": "тропинку"},
    "трава": {"dative": "тропинке", "accusative": "тропинку"},
    "камни": {"dative": "тропинке", "accusative": "тропинку"},
    "пруд": {"dative": "тропинке", "accusative": "тропинку"},
    "море": {"dative": "дорожке", "accusative": "дорожку"},
    "дорога": {"dative": "дороге", "accusative": "дорогу"},
    "город": {"dative": "улице", "accusative": "улицу"},
    "аэродром": {"dative": "полосе", "accusative": "полосу"},
    "двор": {"dative": "дорожке", "accusative": "дорожку"},
}
PATH_DEFAULT: Dict[str, str] = {"dative": "дорожке", "accusative": "дорожку"}


def path_word(scene: str) -> Dict[str, str]:
    """Как назвать путь на этой сцене: {'dative': …, 'accusative': …}."""
    return PATH_WORD.get(scene or "", PATH_DEFAULT)


def worlds_for(character: str) -> Tuple[str, ...]:
    """Сцены, в которых этот герой органичен. Пустой кортеж — героя не знаем."""
    return WORLDS.get(character, ())


def default_scene(character: str) -> str:
    """Умолчание — первый мир героя; для незнакомого героя это «без фона»."""
    worlds = worlds_for(character)
    return worlds[0] if worlds else ""


def fits(character: str, scene: str) -> bool:
    """Годится ли сцена этому герою. «Без фона» годится всем всегда."""
    return not scene or scene in worlds_for(character)


# ═══════════════════════════════════════════════════════════════════════
#  ХОЛСТ: сцена укладывается ВОКРУГ дорожки
# ═══════════════════════════════════════════════════════════════════════

# Зоны листа. Сцена живёт по краям — в середине идёт дорожка со слогами.
ZONE_W = 27.0       # ширина боковой кромки, мм
ZONE_H = 28.0       # высота верхней и нижней полосы, мм


class Canvas:
    """Место для предметов сцены с оглядкой на дорожку.

    `avoid` — круги (x, y, r), занятые кружками слогов и самой тропой. Предмет
    получает координаты только там, где не заденет ни дорожку, ни уже
    разложенные предметы. Не нашлось места — предмет не печатается: пустое
    место честнее обрезанного домика.
    """

    def __init__(self, w: float, h: float,
                 avoid: Optional[Sequence[Tuple[float, float, float]]] = None):
        self.w, self.h = w, h
        self.avoid = list(avoid or [])
        self.taken: List[Tuple[float, float, float, float]] = []
        self.parts: List[str] = []

    # — проверка места —

    def _hits(self, x: float, y: float, bw: float, bh: float,
              pad: float = 1.2) -> bool:
        for cx, cy, r in self.avoid:
            if (x - pad < cx + r and x + bw + pad > cx - r
                    and y - pad < cy + r and y + bh + pad > cy - r):
                return True
        for tx, ty, tw, th in self.taken:
            if (x < tx + tw + pad and x + bw + pad > tx
                    and y < ty + th + pad and y + bh + pad > ty):
                return True
        return False

    def _range(self, bw: float, bh: float, zone: str,
               step: float) -> Tuple[List[float], List[float]]:
        w, h = self.w, self.h
        if zone == "left":
            xs = _seq(1.0, min(ZONE_W, w * 0.3) - bw, step)
            ys = _seq(2.0, h - bh - 2.0, step)
        elif zone == "right":
            xs = _seq(max(w - ZONE_W, w * 0.7), w - bw - 1.0, step)
            ys = _seq(2.0, h - bh - 2.0, step)
        elif zone == "top":
            xs = _seq(2.0, w - bw - 2.0, step)
            ys = _seq(1.0, ZONE_H - bh, step)
        elif zone == "bottom":
            xs = _seq(2.0, w - bw - 2.0, step)
            ys = _seq(h - ZONE_H, h - bh - 1.0, step)
        else:                                   # «где угодно, лишь бы влезло»
            xs = _seq(2.0, w - bw - 2.0, step)
            ys = _seq(2.0, h - bh - 2.0, step)
        return xs, ys

    def place(self, bw: float, bh: float, zone: str = "any",
              step: float = 2.5) -> Optional[Tuple[float, float]]:
        """Свободный угол под предмет bw×bh. None — места нет."""
        xs, ys = self._range(bw, bh, zone, step)
        for y in ys:
            for x in xs:
                if not self._hits(x, y, bw, bh):
                    self.taken.append((x, y, bw, bh))
                    return x, y
        return None

    def spread(self, sprite: Callable[..., None], bw: float, bh: float,
               zone: str, n: int, fallback: bool = True, **kw: Any) -> int:
        """Разложить предмет до n раз, пока есть место. Вернёт сколько вышло.

        `fallback` — если в своей зоне места не осталось, ищем в промежутках
        между рядами. Без этого сцены пустели: боковые кромки узкие, и после
        того как сцена стала обходить дорожку, дома с ёлками переставали
        помещаться вовсе (08-10).
        """
        made = 0
        for _ in range(n):
            pos = self.place(bw, bh, zone)
            if pos is None and fallback and zone != "any":
                pos = self.place(bw, bh, "any")
            if pos is None:
                break
            sprite(self, pos[0], pos[1], bw, bh, **kw)
            made += 1
        return made

    # — рисование —

    def add(self, d: str) -> None:
        self.parts.append(f'<path d="{d}"/>')

    def circle(self, cx: float, cy: float, r: float) -> None:
        self.parts.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r:.1f}"/>')

    def free_strip(self, y: float, thick: float = 2.0) -> List[Tuple[float, float]]:
        """Куски горизонтали на высоте y, свободные от дорожки.

        Поверхность (полотно дороги, кромка воды, плинтус) — это линия во всю
        ширину, и обрывать её у каждого кружка вручную нельзя. Здесь она
        нарезается автоматически: считаем, где горизонталь пересекает занятые
        круги, и печатаем только промежутки.
        """
        cuts: List[Tuple[float, float]] = []
        for cx, cy, r in self.avoid:
            dy = abs(cy - y)
            rr = r + thick
            if dy < rr:
                half = math.sqrt(rr * rr - dy * dy)
                cuts.append((cx - half, cx + half))
        cuts.sort()
        out: List[Tuple[float, float]] = []
        x = 0.0
        for a, b in cuts:
            if a > x + 3.0:
                out.append((x, a))
            x = max(x, b)
        if x < self.w - 3.0:
            out.append((x, self.w))
        return out

    def hline(self, y: float, thick: float = 2.0) -> None:
        """Горизонталь, разрезанная дорожкой."""
        for a, b in self.free_strip(y, thick):
            self.add(f"M{a:.1f} {y:.1f} L{b:.1f} {y:.1f}")

    def svg(self, stroke: float, opacity: float) -> str:
        if not self.parts:
            return ""
        return (f'<g fill="none" stroke="#000" stroke-width="{stroke}" '
                f'stroke-linecap="round" stroke-linejoin="round" '
                f'opacity="{opacity}">{"".join(self.parts)}</g>')


def _seq(a: float, b: float, step: float) -> List[float]:
    if b < a:
        return []
    n = int((b - a) / step) + 1
    return [a + i * step for i in range(n)]


# ═══════════════════════════════════════════════════════════════════════
#  ПРЕДМЕТЫ (спрайты). Каждый рисуется в своём боксе x, y, w, h
# ═══════════════════════════════════════════════════════════════════════

def _sp_tree(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    """Ёлка: три яруса и ствол."""
    cx = x + w / 2
    step = h / 4.2
    top = y
    for k in range(3):
        yy = top + k * step
        half = w * (0.30 + 0.18 * k)
        cv.add(f"M{cx:.1f} {yy:.1f} L{cx-half:.1f} {yy+step*1.25:.1f} "
               f"L{cx+half:.1f} {yy+step*1.25:.1f} z")
    cv.add(f"M{cx:.1f} {y+h-step*0.7:.1f} l 0 {step*0.7:.1f}")


def _sp_bush(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cv.add(f"M{x:.1f} {y+h:.1f} q {w*0.1:.1f} {-h:.1f} {w*0.5:.1f} {-h*0.85:.1f} "
           f"q {w*0.4:.1f} {-h*0.15:.1f} {w*0.5:.1f} {h*0.85:.1f} z")


def _sp_mushroom(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cx = x + w / 2
    cv.add(f"M{cx-w*0.14:.1f} {y+h:.1f} l 0 {-h*0.45:.1f} l {w*0.28:.1f} 0 l 0 {h*0.45:.1f}")
    cv.add(f"M{x:.1f} {y+h*0.55:.1f} a {w*0.5:.1f} {h*0.5:.1f} 0 0 1 {w:.1f} 0 z")


def _sp_cloud(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cv.add(f"M{x:.1f} {y+h:.1f} a {h*0.55:.1f} {h*0.55:.1f} 0 0 1 {h*0.5:.1f} {-h*0.6:.1f} "
           f"a {w*0.28:.1f} {h*0.75:.1f} 0 0 1 {w*0.55:.1f} {h*0.06:.1f} "
           f"a {h*0.45:.1f} {h*0.45:.1f} 0 0 1 {w*0.2:.1f} {h*0.54:.1f} z")


def _sp_bird(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cv.add(f"M{x:.1f} {y+h*0.6:.1f} q {w*0.25:.1f} {-h*0.6:.1f} {w*0.5:.1f} 0 "
           f"q {w*0.25:.1f} {-h*0.6:.1f} {w*0.5:.1f} 0")


def _sp_sun(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cx, cy, r = x + w / 2, y + h / 2, min(w, h) * 0.28
    cv.circle(cx, cy, r)
    for i in range(8):
        a = i * math.pi / 4
        cv.add(f"M{cx + (r+1.2)*math.cos(a):.1f} {cy + (r+1.2)*math.sin(a):.1f} "
               f"L{cx + (r+3.4)*math.cos(a):.1f} {cy + (r+3.4)*math.sin(a):.1f}")


def _sp_house(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    roof = h * 0.34
    cv.add(f"M{x:.1f} {y+h:.1f} l 0 {-(h-roof):.1f} l {w*0.5:.1f} {-roof:.1f} "
           f"l {w*0.5:.1f} {roof:.1f} l 0 {h-roof:.1f} z")
    cv.add(f"M{x+w*0.36:.1f} {y+h:.1f} l 0 {-h*0.34:.1f} l {w*0.28:.1f} 0 l 0 {h*0.34:.1f}")


def _sp_tower(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    """Городская башня: окна рядами."""
    cv.add(f"M{x:.1f} {y+h:.1f} l 0 {-h:.1f} l {w:.1f} 0 l 0 {h:.1f} z")
    rows = max(2, int(h // 7))
    for r in range(rows):
        yy = y + 3.0 + r * (h - 4.0) / rows
        for c in (0, 1):
            cv.add(f"M{x + w*0.22 + c*w*0.38:.1f} {yy:.1f} l {w*0.2:.1f} 0 "
                   f"l 0 {min(3.4, h/rows*0.5):.1f} l {-w*0.2:.1f} 0 z")


def _sp_lamp(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cv.add(f"M{x+w*0.5:.1f} {y+h:.1f} l 0 {-h*0.8:.1f} q 0 {-h*0.2:.1f} {w*0.4:.1f} {-h*0.2:.1f}")
    cv.circle(x + w * 0.9, y + h * 0.05, min(w, h) * 0.12)


def _sp_reed(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    """Камыш: стебель и початок."""
    cx = x + w / 2
    cv.add(f"M{cx:.1f} {y+h:.1f} L{cx:.1f} {y+h*0.22:.1f}")
    cv.add(f"M{cx-w*0.22:.1f} {y+h*0.30:.1f} a {w*0.22:.1f} {h*0.14:.1f} 0 0 1 "
           f"{w*0.44:.1f} 0 l 0 {-h*0.16:.1f} a {w*0.22:.1f} {h*0.14:.1f} 0 0 1 "
           f"{-w*0.44:.1f} 0 z")
    cv.add(f"M{cx:.1f} {y+h*0.62:.1f} q {w*0.5:.1f} {-h*0.12:.1f} {w*0.72:.1f} {-h*0.34:.1f}")


def _sp_lily(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cv.add(f"M{x:.1f} {y+h*0.75:.1f} a {w*0.5:.1f} {h*0.42:.1f} 0 1 1 {w:.1f} 0 z")
    cv.add(f"M{x+w*0.5:.1f} {y+h*0.75:.1f} l 0 {-h*0.3:.1f}")


def _sp_dragonfly(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cv.add(f"M{x:.1f} {y+h*0.5:.1f} l {w:.1f} 0")
    cv.add(f"M{x+w*0.28:.1f} {y+h*0.5:.1f} q {w*0.2:.1f} {-h*0.5:.1f} {w*0.42:.1f} {-h*0.1:.1f}")
    cv.add(f"M{x+w*0.28:.1f} {y+h*0.5:.1f} q {w*0.2:.1f} {h*0.5:.1f} {w*0.42:.1f} {h*0.1:.1f}")


def _sp_grass(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cv.add(f"M{x:.1f} {y+h:.1f} q {w*0.22:.1f} {-h*0.55:.1f} {w*0.4:.1f} {-h:.1f}")
    cv.add(f"M{x+w*0.3:.1f} {y+h:.1f} q {w*0.1:.1f} {-h*0.5:.1f} {w*0.24:.1f} {-h*0.8:.1f}")
    cv.add(f"M{x+w*0.62:.1f} {y+h:.1f} q {w*0.2:.1f} {-h*0.5:.1f} {w*0.38:.1f} {-h*0.92:.1f}")


def _sp_flower(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cx, cy = x + w / 2, y + h * 0.32
    cv.add(f"M{cx:.1f} {y+h:.1f} L{cx:.1f} {cy + h*0.16:.1f}")
    cv.circle(cx, cy, min(w, h) * 0.13)
    for i in range(6):
        a = i * math.pi / 3
        r0, r1 = min(w, h) * 0.2, min(w, h) * 0.36
        cv.add(f"M{cx + r0*math.cos(a):.1f} {cy + r0*math.sin(a):.1f} "
               f"L{cx + r1*math.cos(a):.1f} {cy + r1*math.sin(a):.1f}")


def _sp_stone(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cv.add(f"M{x:.1f} {y+h:.1f} a {w*0.5:.1f} {h*0.85:.1f} 0 0 1 {w:.1f} 0 z")
    cv.add(f"M{x+w*0.3:.1f} {y+h:.1f} q {w*0.12:.1f} {-h*0.45:.1f} {w*0.3:.1f} {-h*0.55:.1f}")


def _sp_pebbles(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    for i, (dx, dy, r) in enumerate(((0.2, 0.7, 0.16), (0.55, 0.35, 0.12),
                                     (0.8, 0.75, 0.1))):
        cv.circle(x + w * dx, y + h * dy, min(w, h) * r)


def _sp_fence(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    """Кусок забора: планки и две поперечины."""
    cv.add(f"M{x:.1f} {y+h*0.35:.1f} l {w:.1f} 0 M{x:.1f} {y+h*0.72:.1f} l {w:.1f} 0")
    step = max(4.0, w / 5)
    xx = x
    while xx <= x + w - 1:
        cv.add(f"M{xx:.1f} {y+h:.1f} l 0 {-h*0.86:.1f} l {step*0.22:.1f} {-h*0.14:.1f} "
               f"l {step*0.22:.1f} {h*0.14:.1f} l 0 {h*0.86:.1f}")
        xx += step


def _sp_swing(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cv.add(f"M{x+w*0.15:.1f} {y:.1f} l 0 {h*0.75:.1f} M{x+w*0.85:.1f} {y:.1f} l 0 {h*0.75:.1f}")
    cv.add(f"M{x:.1f} {y:.1f} l {w:.1f} 0 M{x+w*0.15:.1f} {y+h*0.75:.1f} l {w*0.7:.1f} 0")


def _sp_tyre(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cx, cy, r = x + w / 2, y + h / 2, min(w, h) / 2
    cv.circle(cx, cy, r)
    cv.circle(cx, cy, r * 0.42)


def _sp_can(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cv.add(f"M{x:.1f} {y+h:.1f} l 0 {-h*0.8:.1f} l {w:.1f} 0 l 0 {h*0.8:.1f} z")
    cv.add(f"M{x+w*0.25:.1f} {y+h*0.2:.1f} l 0 {-h*0.2:.1f} l {w*0.4:.1f} 0 l 0 {h*0.2:.1f}")


def _sp_bucket(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cv.add(f"M{x:.1f} {y+h*0.25:.1f} l {w*0.14:.1f} {h*0.75:.1f} l {w*0.72:.1f} 0 "
           f"l {w*0.14:.1f} {-h*0.75:.1f} z")
    cv.add(f"M{x:.1f} {y+h*0.25:.1f} q {w*0.5:.1f} {-h*0.45:.1f} {w:.1f} 0")


def _sp_tools(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    """Полка с инструментами: молоток, ключ, отвёртка."""
    cv.add(f"M{x:.1f} {y:.1f} l {w:.1f} 0")
    cv.add(f"M{x+w*0.18:.1f} {y:.1f} l 0 {h*0.55:.1f} "
           f"M{x+w*0.08:.1f} {y+h*0.55:.1f} l {w*0.2:.1f} 0 l 0 {h*0.16:.1f} l {-w*0.2:.1f} 0 z")
    cv.add(f"M{x+w*0.5:.1f} {y:.1f} l 0 {h*0.5:.1f}")
    cv.circle(x + w * 0.5, y + h * 0.62, min(w, h) * 0.11)
    cv.add(f"M{x+w*0.82:.1f} {y:.1f} l 0 {h*0.45:.1f} l {-w*0.05:.1f} 0 l 0 {h*0.2:.1f} "
           f"l {w*0.1:.1f} 0 l 0 {-h*0.2:.1f} z")


def _sp_bath(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    """Ванна на ножках — самый узнаваемый предмет ванной."""
    cv.add(f"M{x:.1f} {y+h*0.25:.1f} q 0 {h*0.65:.1f} {w*0.2:.1f} {h*0.65:.1f} "
           f"l {w*0.6:.1f} 0 q {w*0.2:.1f} 0 {w*0.2:.1f} {-h*0.65:.1f}")
    cv.add(f"M{x-w*0.04:.1f} {y+h*0.25:.1f} l {w*1.08:.1f} 0")
    for dx in (0.18, 0.74):
        cv.add(f"M{x+w*dx:.1f} {y+h*0.9:.1f} l {-w*0.04:.1f} {h*0.1:.1f} "
               f"M{x+w*(dx+0.08):.1f} {y+h*0.9:.1f} l {w*0.04:.1f} {h*0.1:.1f}")
    cv.add(f"M{x+w*0.06:.1f} {y+h*0.25:.1f} l 0 {-h*0.18:.1f} q 0 {-h*0.1:.1f} {w*0.14:.1f} {-h*0.1:.1f}")


def _sp_shower(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cx = x + w * 0.5
    cv.add(f"M{cx:.1f} {y:.1f} l 0 {h*0.32:.1f}")
    cv.add(f"M{cx-w*0.3:.1f} {y+h*0.32:.1f} l {w*0.6:.1f} 0 l {-w*0.12:.1f} {h*0.18:.1f} "
           f"l {-w*0.36:.1f} 0 z")
    for i, dx in enumerate((-0.18, 0.0, 0.18)):
        cv.add(f"M{cx+w*dx:.1f} {y+h*(0.62+i*0.14):.1f} "
               f"a {w*0.06:.1f} {h*0.07:.1f} 0 1 1 0.1 0 z")


def _sp_towel(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cv.add(f"M{x:.1f} {y:.1f} l {w:.1f} 0")
    cv.add(f"M{x+w*0.2:.1f} {y:.1f} l 0 {h*0.8:.1f} q {w*0.3:.1f} {h*0.2:.1f} {w*0.6:.1f} 0 "
           f"l 0 {-h*0.8:.1f}")
    cv.add(f"M{x+w*0.5:.1f} {y+h*0.2:.1f} l 0 {h*0.55:.1f}")


def _sp_door(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cv.add(f"M{x:.1f} {y+h:.1f} l 0 {-h:.1f} l {w:.1f} 0 l 0 {h:.1f}")
    cv.add(f"M{x+w*0.18:.1f} {y+h*0.12:.1f} l {w*0.64:.1f} 0 l 0 {h*0.3:.1f} l {-w*0.64:.1f} 0 z")
    cv.circle(x + w * 0.82, y + h * 0.6, min(w, h) * 0.05)


def _sp_boots(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    for dx in (0.0, 0.52):
        cv.add(f"M{x+w*dx:.1f} {y+h:.1f} l 0 {-h*0.62:.1f} q 0 {-h*0.38:.1f} {w*0.2:.1f} {-h*0.38:.1f} "
               f"q {w*0.2:.1f} 0 {w*0.2:.1f} {h*0.5:.1f} l {w*0.08:.1f} {h*0.5:.1f} z")


def _sp_hooks(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cv.add(f"M{x:.1f} {y:.1f} l {w:.1f} 0")
    for i in range(3):
        cx = x + w * (0.18 + i * 0.32)
        cv.add(f"M{cx:.1f} {y:.1f} l 0 {h*0.6:.1f} q 0 {h*0.3:.1f} {w*0.1:.1f} {h*0.3:.1f}")


def _sp_umbrella(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cx = x + w * 0.5
    cv.add(f"M{cx:.1f} {y+h*0.28:.1f} l 0 {h*0.6:.1f} q 0 {h*0.12:.1f} {-w*0.16:.1f} {h*0.12:.1f}")
    cv.add(f"M{x:.1f} {y+h*0.28:.1f} a {w*0.5:.1f} {h*0.28:.1f} 0 0 1 {w:.1f} 0 z")


def _sp_tank(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    """Диспетчерская вышка аэродрома."""
    cv.add(f"M{x+w*0.2:.1f} {y+h:.1f} l 0 {-h*0.55:.1f} M{x+w*0.8:.1f} {y+h:.1f} l 0 {-h*0.55:.1f}")
    cv.add(f"M{x:.1f} {y+h*0.45:.1f} l {w:.1f} 0 l {-w*0.16:.1f} {-h*0.22:.1f} l {-w*0.68:.1f} 0 z")
    cv.add(f"M{x+w*0.16:.1f} {y+h*0.23:.1f} l {w*0.68:.1f} 0 M{x+w*0.5:.1f} {y+h*0.23:.1f} l 0 {-h*0.2:.1f}")


def _sp_hangar(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cv.add(f"M{x:.1f} {y+h:.1f} l 0 {-h*0.5:.1f} q {w*0.5:.1f} {-h*0.55:.1f} {w:.1f} 0 "
           f"l 0 {h*0.5:.1f} z")
    cv.add(f"M{x+w*0.36:.1f} {y+h:.1f} l 0 {-h*0.32:.1f} l {w*0.28:.1f} 0 l 0 {h*0.32:.1f}")


def _sp_windsock(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cv.add(f"M{x+w*0.12:.1f} {y+h:.1f} l 0 {-h:.1f}")
    cv.add(f"M{x+w*0.12:.1f} {y:.1f} l {w*0.88:.1f} {h*0.2:.1f} l {-w*0.88:.1f} {h*0.2:.1f} z")


def _sp_wave(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    d, xx, up = [f"M{x:.1f} {y+h*0.5:.1f}"], x, True
    while xx < x + w:
        step = min(6.0, x + w - xx)
        d.append(f"q {step/2:.1f} {(-h*0.5) if up else (h*0.5):.1f} {step:.1f} 0")
        xx += step
        up = not up
    cv.add(" ".join(d))


def _sp_algae(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cx, yy, bend = x + w / 2, y + h, 3.2
    d = [f"M{cx:.1f} {yy:.1f}"]
    seg = h / 3.0
    for _ in range(3):
        d.append(f"q {bend:.1f} {-seg/2:.1f} 0 {-seg:.1f}")
        bend = -bend
    cv.add(" ".join(d))


def _sp_shell(cv: Canvas, x: float, y: float, w: float, h: float) -> None:
    cv.add(f"M{x:.1f} {y+h:.1f} a {w*0.5:.1f} {h:.1f} 0 0 1 {w:.1f} 0 z")
    for dx in (0.28, 0.5, 0.72):
        cv.add(f"M{x+w*dx:.1f} {y+h:.1f} L{x+w*0.5:.1f} {y+h*0.12:.1f}")


# ═══════════════════════════════════════════════════════════════════════
#  СЦЕНЫ. Каждая просит места у холста и раскладывается вокруг дорожки
# ═══════════════════════════════════════════════════════════════════════

def _sea(cv: Canvas) -> None:
    cv.spread(_sp_algae, 7.0, 26.0, "left", 3)
    cv.spread(_sp_algae, 7.0, 26.0, "right", 3)
    cv.spread(_sp_shell, 9.0, 6.0, "bottom", 3)
    cv.spread(_sp_wave, 34.0, 6.0, "top", 3)
    cv.spread(_sp_wave, 30.0, 6.0, "bottom", 2)
    for y in (cv.h - 5.0,):
        cv.hline(y)


def _forest(cv: Canvas) -> None:
    cv.spread(_sp_tree, 15.0, 28.0, "left", 4)
    cv.spread(_sp_tree, 15.0, 28.0, "right", 4)
    cv.spread(_sp_tree, 13.0, 22.0, "any", 3)      # в промежутках между рядами
    cv.spread(_sp_bush, 12.0, 8.0, "bottom", 4)
    cv.spread(_sp_bush, 12.0, 8.0, "any", 3)
    cv.spread(_sp_mushroom, 7.5, 7.5, "bottom", 3)
    cv.spread(_sp_mushroom, 7.5, 7.5, "any", 2)
    cv.spread(_sp_cloud, 21.0, 9.0, "top", 2)


def _sky(cv: Canvas) -> None:
    cv.spread(_sp_sun, 18.0, 18.0, "top", 1)
    cv.spread(_sp_cloud, 24.0, 10.0, "top", 2)
    cv.spread(_sp_cloud, 22.0, 9.0, "left", 2)
    cv.spread(_sp_cloud, 22.0, 9.0, "right", 2)
    cv.spread(_sp_bird, 12.0, 5.0, "right", 3)
    cv.spread(_sp_bird, 12.0, 5.0, "left", 2)
    cv.spread(_sp_cloud, 26.0, 10.0, "bottom", 2)


def _road(cv: Canvas) -> None:
    # полотно по низу: две кромки, разрезанные дорожкой, и штрихи осевой
    cv.hline(cv.h - 12.0)
    cv.hline(cv.h - 2.5)
    for a, b in cv.free_strip(cv.h - 7.0):
        x = a + 2.0
        while x < b - 6.0:
            cv.add(f"M{x:.1f} {cv.h-7.0:.1f} l 6 0")
            x += 13.0
    cv.spread(_sp_house, 14.0, 14.0, "left", 3)
    cv.spread(_sp_house, 14.0, 14.0, "right", 3)
    cv.spread(_sp_house, 13.0, 13.0, "any", 3)
    cv.spread(_sp_lamp, 10.0, 16.0, "left", 1)
    cv.spread(_sp_lamp, 10.0, 16.0, "right", 1)
    cv.spread(_sp_cloud, 22.0, 9.0, "top", 2)


def _airfield(cv: Canvas) -> None:
    cv.hline(cv.h - 13.0)
    cv.hline(cv.h - 2.5)
    for a, b in cv.free_strip(cv.h - 7.5):
        x = a + 2.0
        while x < b - 9.0:
            cv.add(f"M{x:.1f} {cv.h-7.5:.1f} l 9 0")
            x += 18.0
    for a, b in cv.free_strip(cv.h - 15.5, 1.5):
        x = a + 4.0
        while x < b - 2.0:
            cv.circle(x, cv.h - 15.5, 0.9)
            x += 11.0
    cv.spread(_sp_tank, 16.0, 26.0, "left", 1)
    cv.spread(_sp_hangar, 20.0, 14.0, "right", 1)
    cv.spread(_sp_windsock, 12.0, 12.0, "right", 1)
    cv.spread(_sp_cloud, 22.0, 9.0, "top", 2)


def _city(cv: Canvas) -> None:
    cv.spread(_sp_tower, 14.0, 30.0, "left", 3)
    cv.spread(_sp_tower, 14.0, 30.0, "right", 3)
    cv.spread(_sp_tower, 13.0, 22.0, "any", 4)
    cv.spread(_sp_lamp, 10.0, 14.0, "bottom", 2)
    cv.hline(cv.h - 4.0)
    for a, b in cv.free_strip(cv.h - 8.0):
        x = a + 3.0
        while x < b - 3.0:
            cv.add(f"M{x:.1f} {cv.h-8.0:.1f} l 0 -3.4")
            x += 7.0


def _yard(cv: Canvas) -> None:
    cv.spread(_sp_fence, 26.0, 12.0, "bottom", 5)
    cv.spread(_sp_tree, 15.0, 26.0, "left", 2)
    cv.spread(_sp_swing, 20.0, 14.0, "top", 1)
    cv.spread(_sp_bush, 12.0, 8.0, "right", 2)
    cv.spread(_sp_grass, 10.0, 6.0, "bottom", 3)


def _garage(cv: Canvas) -> None:
    cv.spread(_sp_tyre, 15.0, 15.0, "left", 2)
    cv.spread(_sp_can, 11.0, 13.0, "left", 1)
    cv.spread(_sp_tools, 20.0, 12.0, "right", 2)
    cv.spread(_sp_bucket, 13.0, 11.0, "right", 1)
    cv.spread(_sp_lamp, 10.0, 12.0, "top", 1)
    cv.hline(cv.h - 3.0)


def _pond(cv: Canvas) -> None:
    cv.spread(_sp_reed, 9.0, 24.0, "left", 4)
    cv.spread(_sp_reed, 9.0, 24.0, "right", 4)
    cv.spread(_sp_reed, 9.0, 20.0, "any", 3)
    cv.spread(_sp_lily, 11.0, 7.5, "bottom", 4)
    cv.spread(_sp_lily, 11.0, 7.5, "any", 3)
    cv.spread(_sp_dragonfly, 13.0, 6.5, "top", 2)
    cv.spread(_sp_dragonfly, 13.0, 6.5, "any", 2)
    for y in (cv.h - 5.0, cv.h - 9.5):
        cv.hline(y)


def _grass(cv: Canvas) -> None:
    # Трава должна быть ГУСТОЙ: редкие пучки читаются штрихами, а не лугом.
    # Поэтому здесь много мелких боксов, а не несколько крупных.
    cv.spread(_sp_flower, 9.0, 11.0, "bottom", 3)
    cv.spread(_sp_flower, 9.0, 11.0, "left", 2)
    cv.spread(_sp_flower, 9.0, 11.0, "right", 2)
    cv.spread(_sp_grass, 9.0, 6.5, "bottom", 16)
    cv.spread(_sp_grass, 9.0, 6.0, "left", 8)
    cv.spread(_sp_grass, 9.0, 6.0, "right", 8)
    cv.spread(_sp_grass, 9.0, 6.0, "any", 14)      # в промежутках между рядами


def _stones(cv: Canvas) -> None:
    cv.spread(_sp_stone, 17.0, 10.0, "bottom", 4)
    cv.spread(_sp_stone, 15.0, 9.0, "left", 3)
    cv.spread(_sp_stone, 15.0, 9.0, "right", 3)
    cv.spread(_sp_stone, 14.0, 8.5, "any", 4)
    cv.spread(_sp_pebbles, 11.0, 6.0, "bottom", 4)
    cv.spread(_sp_pebbles, 11.0, 6.0, "left", 3)
    cv.spread(_sp_pebbles, 11.0, 6.0, "right", 3)
    cv.spread(_sp_pebbles, 11.0, 6.0, "any", 6)
    cv.spread(_sp_grass, 9.0, 6.0, "bottom", 3)


def _bathroom(cv: Canvas) -> None:
    cv.spread(_sp_bath, 40.0, 18.0, "bottom", 1)
    cv.spread(_sp_shower, 14.0, 20.0, "top", 1)
    cv.spread(_sp_towel, 12.0, 20.0, "right", 1)
    cv.spread(_sp_pebbles, 10.0, 8.0, "left", 2)     # мыльные пузыри
    cv.hline(cv.h - 2.5)


def _hallway(cv: Canvas) -> None:
    cv.spread(_sp_door, 16.0, 34.0, "right", 1)
    cv.spread(_sp_hooks, 16.0, 10.0, "left", 1)
    cv.spread(_sp_umbrella, 13.0, 20.0, "left", 1)
    cv.spread(_sp_boots, 16.0, 9.0, "bottom", 2)
    cv.hline(cv.h - 10.0)
    cv.hline(cv.h - 8.0)


SCENES: Dict[str, Callable[[Canvas], None]] = {
    # ⚠ «море» осталось в банке, но НИ У КОГО не стоит в мирах: это та самая
    # подводная сцена с фото Ольги, и она ждёт своего героя (водного). Пока
    # героя нет — сцена не предлагается никому, и это честнее, чем приписать
    # её самолёту «под крылом».
    "море": _sea,
    "лес": _forest,
    "небо": _sky,
    "дорога": _road,
    "аэродром": _airfield,
    "город": _city,
    "двор": _yard,
    "гараж": _garage,
    "пруд": _pond,
    "трава": _grass,
    "камни": _stones,
    "ванная": _bathroom,
    "прихожая": _hallway,
}


def scene_svg(name: str, w: float, h: float,
              stroke: float = 0.95, opacity: float = 0.42,
              avoid: Optional[Sequence[Tuple[float, float, float]]] = None) -> str:
    """Слой сцены для вставки ПЕРВЫМ в <svg> дорожки (под тропу и кружки).

    `avoid` — круги, занятые кружками слогов и самой дорожкой. Без него сцена
    ляжет как раньше, вслепую; с ним — обойдёт материал стороной.

    Пустая строка — законный ответ: «без фона» это выбор логопеда, а не
    отсутствие возможности.
    """
    fn = SCENES.get(name or "")
    if not fn:
        return ""
    cv = Canvas(w, h, avoid)
    fn(cv)
    return cv.svg(stroke, opacity)
