# -*- coding: utf-8 -*-
"""Схема рта для занятия артикуляционной гимнастикой — рисует КОД, не генератор.

Зачем. Автор 24.11: «упри кончик языка в нижние зубы — да это нужно показывать.
Анимировать»; «давай схему рта тогда, которая будет двигаться». Картинка-образ (лошадка,
качели) говорит ребёнку, КАКОЕ упражнение; как двигать языком, у логопеда показывает
его лицо (Фомичёва 1989: упражнения «перед зеркалом педагог выполняет вместе с
ребенком»). На экране это делает схема рта. Генератор картинок положение языка не держит
(«Чашечка» — три промаха 24.11), поэтому схема нарисована вручную, в координатах:
каждая поза сверена с описанием упражнения в `gymnastics.json` (закон 1).

Вид спереди, как в зеркале: круглое лицо, губы, зубы, язык. Цвет языка — коралловый
бренда (`--g-tongue`): язык — главный на этой картинке. Звук упражнения («бл-бл»,
«ы-ы-ы», «ф-ф-ф») — подписью у рта, а не голосом: голос синтеза автор запретил.

Одна поза — одна функция ниже; `POZY` — какие есть. Как они чередуются в занятии,
решает таблица счёта (`gymnastics.json` → `schet.fazy[].pozy`, `takt`).
Проверка глазами — `python3 -I tools/rot_list.py` собирает все позы на один лист.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Tuple

SKIN, SKIN_EDGE = "#f7d6c2", "#dca88f"
LIP, LIP_EDGE = "#d8737d", "#b45863"
CAV = "#6b2a33"
TOOTH, TOOTH_LINE = "#ffffff", "#ddd2c6"
TONGUE, TONGUE_EDGE, GROOVE = "#ef8f86", "#c45f5a", "#d9786f"
UNDER, FREN = "#e7848e", "#c95f6d"
AIR = "#6f9fc6"

CX, CY = 100.0, 146.0  # центр рта


def _f(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


def cavity(hw: float, top: float, bot: float) -> str:
    """Проём рта: верх — лёгкая дуга, низ — глубже (улыбка)."""
    l, r = CX - hw, CX + hw
    return (f"M{_f(l)} {_f(CY)} C{_f(CX - hw * .55)} {_f(CY - top)} {_f(CX + hw * .55)} {_f(CY - top)} {_f(r)} {_f(CY)} "
            f"C{_f(CX + hw * .6)} {_f(CY + bot)} {_f(CX - hw * .6)} {_f(CY + bot)} {_f(l)} {_f(CY)}Z")


def _ytop(x: float, hw: float, top: float) -> float:
    t = (x - CX) / hw
    return CY - .75 * top * max(0.0, 1 - t * t)


def _ybot(x: float, hw: float, bot: float) -> float:
    t = (x - CX) / hw
    return CY + .75 * bot * max(0.0, 1 - t * t)


def _band(hw: float, f: Callable[[float], float], d: float) -> str:
    xs = [CX - hw + 2 * hw * i / 16 for i in range(17)]
    a = " ".join(f"{_f(x)} {_f(f(x))}" for x in xs)
    b = " ".join(f"{_f(x)} {_f(f(x) + d)}" for x in reversed(xs))
    return f"M{a} L{b}Z"


def teeth_upper(hw: float, top: float, h: float = 11) -> str:
    f = lambda x: _ytop(x, hw, top) - 2
    seps = "".join(f'<path d="M{_f(x)} {_f(f(x))}V{_f(f(x) + h)}" stroke="{TOOTH_LINE}" stroke-width="1.3"/>'
                   for x in (CX - 30, CX - 19, CX - 9.5, CX, CX + 9.5, CX + 19, CX + 30))
    return f'<path d="{_band(hw, f, h)}" fill="{TOOTH}"/>{seps}'


def teeth_lower(hw: float, bot: float, h: float = 9) -> str:
    f = lambda x: _ybot(x, hw, bot) - h + 2
    seps = "".join(f'<path d="M{_f(x)} {_f(f(x))}V{_f(f(x) + h)}" stroke="{TOOTH_LINE}" stroke-width="1.3"/>'
                   for x in (CX - 24, CX - 14, CX - 5, CX + 5, CX + 14, CX + 24))
    return f'<path d="{_band(hw, f, h)}" fill="{TOOTH}"/>{seps}'


def mouth(pid: str, hw: float, top: float, bot: float, inside: str = "", over: str = "",
          lip_over: bool = False) -> str:
    """Рот: губы (толстая обводка проёма), проём, что внутри (под обрезкой), что поверх губ."""
    d = cavity(hw, top, bot)
    clip = f"rc-{pid}"
    upper_lip = ""
    if lip_over:  # верхняя губа поверх языка: «пошлёпать губами»
        l, r = CX - hw, CX + hw
        upper_lip = (f'<path d="M{_f(l)} {_f(CY)} C{_f(CX - hw * .55)} {_f(CY - top)} {_f(CX + hw * .55)} '
                     f'{_f(CY - top)} {_f(r)} {_f(CY)}" fill="none" stroke="{LIP}" stroke-width="9" '
                     f'stroke-linecap="round"/>')
    return (f'<defs><clipPath id="{clip}"><path d="{d}"/></clipPath></defs>'
            f'<path d="{d}" fill="none" stroke="{LIP}" stroke-width="9" stroke-linejoin="round"/>'
            f'<path d="{d}" fill="{CAV}"/>'
            f'<g clip-path="url(#{clip})">{inside}</g>{over}{upper_lip}')


def _tongue(d: str, groove: str = "", fill: str = TONGUE) -> str:
    g = f'<path d="{groove}" stroke="{GROOVE}" stroke-width="2.4" fill="none" stroke-linecap="round"/>' if groove else ""
    return f'<path d="{d}" fill="{fill}" stroke="{TONGUE_EDGE}" stroke-width="1.6" stroke-linejoin="round"/>{g}'


def _under(cx: float, y_top: float, w: float, h: float, stem_to: float) -> str:
    """Язык поднят к нёбу: видна его нижняя сторона во всю ширину рта и тонкая уздечка.

    ⚠ 24.11: первая версия рисовала круглую «шляпку» и толстую «ножку» — автор: «круглый
    этот язык на палочке». Язык прижат к нёбу от края до края, уздечка — перепонка,
    а не палка; у «Грибка» сходство с грибом даёт ширина языка, а не леденец.
    """
    l, r = cx - w - 14, cx + w + 14
    bottom = y_top + h
    body = (f"M{_f(l)} {_f(y_top - 16)} L{_f(r)} {_f(y_top - 16)} L{_f(r)} {_f(y_top + h * .35)} "
            f"C{_f(cx + w * .7)} {_f(bottom + 2)} {_f(cx - w * .7)} {_f(bottom + 2)} {_f(l)} {_f(y_top + h * .35)}Z")
    veins = (f'<path d="M{_f(cx - 9)} {_f(bottom - 3)} Q{_f(cx - 14)} {_f(y_top + 2)} {_f(cx - 22)} {_f(y_top - 2)}" '
             f'stroke="#cf6f7c" stroke-width="1.4" fill="none" opacity=".7"/>'
             f'<path d="M{_f(cx + 9)} {_f(bottom - 3)} Q{_f(cx + 14)} {_f(y_top + 2)} {_f(cx + 22)} {_f(y_top - 2)}" '
             f'stroke="#cf6f7c" stroke-width="1.4" fill="none" opacity=".7"/>')
    fren = (f'<path d="M{_f(cx - 1.2)} {_f(bottom - 1)} L{_f(cx - 6)} {_f(stem_to)} L{_f(cx + 6)} {_f(stem_to)} '
            f'L{_f(cx + 1.2)} {_f(bottom - 1)}Z" fill="{FREN}" opacity=".55"/>'
            f'<path d="M{_f(cx)} {_f(bottom - 1)} L{_f(cx)} {_f(stem_to)}" stroke="{FREN}" stroke-width="1.6"/>')
    return fren + f'<path d="{body}" fill="{UNDER}" stroke="{TONGUE_EDGE}" stroke-width="1.4"/>' + veins


def _air(lines: List[Tuple[float, float, float, float]]) -> str:
    return "".join(f'<path d="M{_f(a)} {_f(b)} L{_f(c)} {_f(d)}" stroke="{AIR}" stroke-width="3" '
                   f'stroke-linecap="round" stroke-dasharray="5 6"/>' for a, b, c, d in lines)


def _zvuk(text: str, x: float = 146, y: float = 120) -> str:
    return (f'<text x="{_f(x)}" y="{_f(y)}" font-family="ui-rounded,system-ui,sans-serif" font-size="15" '
            f'font-weight="700" fill="{LIP_EDGE}" text-anchor="middle">{text}</text>')


# ── позы ───────────────────────────────────────────────────────────────────
# Каждая — по описанию упражнения в gymnastics.json (цитата в строке над функцией).

def p_zakryt() -> str:
    # Отдых: губы сомкнуты, лёгкая улыбка.
    return (f'<path d="M66 {_f(CY)} Q100 {_f(CY + 16)} 134 {_f(CY)}" fill="none" stroke="{LIP}" stroke-width="8" '
            f'stroke-linecap="round"/>')


def p_zaborchik() -> str:
    # «Улыбнуться, обнажив верхние и нижние зубы, которые стоят друг на друге, как заборчик».
    hw, top, bot = 44, 15, 17
    inside = (teeth_upper(hw, top, h=CY - _ytop(CX, hw, top) + 2) +
              teeth_lower(hw, bot, h=_ybot(CX, hw, bot) - CY + 2) +
              f'<path d="M{_f(CX - hw)} {_f(CY)}H{_f(CX + hw)}" stroke="{TOOTH_LINE}" stroke-width="1.6"/>')
    return mouth("zaborchik", hw, top, bot, inside)


def p_trubochka() -> str:
    # «вытянуть губы вперёд, округлив их как при звуке «О»».
    return (f'<ellipse cx="{_f(CX)}" cy="{_f(CY)}" rx="17" ry="15" fill="{CAV}" stroke="{LIP}" stroke-width="13"/>'
            f'<ellipse cx="{_f(CX)}" cy="{_f(CY)}" rx="25" ry="23" fill="none" stroke="{LIP_EDGE}" stroke-width="1.2"/>'
            + "".join(f'<path d="M{_f(CX + 21 * c)} {_f(CY + 21 * s)} L{_f(CX + 13 * c)} {_f(CY + 13 * s)}" '
                      f'stroke="{LIP_EDGE}" stroke-width="1.4" stroke-linecap="round"/>'
                      for c, s in ((.94, -.34), (-.94, -.34), (.94, .34), (-.94, .34), (0, -1), (0, 1))))


def _blin(y_end: float = 177) -> str:
    return _tongue(f"M70 {_f(CY + 3)} C68 {_f(y_end - 12)} 77 {_f(y_end)} 100 {_f(y_end)} "
                   f"C123 {_f(y_end)} 132 {_f(y_end - 12)} 130 {_f(CY + 3)}Z",
                   groove=f"M100 {_f(CY + 8)} L100 {_f(y_end - 6)}")


def p_blinchik() -> str:
    # «приоткрыть рот, положить широкий передний край языка на нижнюю губу и держать спокойно».
    hw, top, bot = 42, 17, 22
    inside = f'<rect x="0" y="{_f(CY - 3)}" width="200" height="60" fill="{TONGUE}"/>' + teeth_upper(hw, top)
    return mouth("blinchik", hw, top, bot, inside, over=_blin())


def p_dut_yazyk() -> str:
    # «Кто дальше загонит мяч?»: язык на нижней губе и длительно «ф-ф-ф» — воздух вперёд.
    return p_blinchik().replace("rc-blinchik", "rc-dut") + _air([(84, 184, 76, 196), (100, 186, 100, 198), (116, 184, 124, 196)]) + _zvuk("ф-ф-ф")


def p_pat(down: bool) -> str:
    # «положить язык на нижнюю губу и, пошлёпывая его губами, произносить пя-пя-пя».
    hw, top, bot = 40, (3 if down else 13), 12
    inside = f'<rect x="0" y="{_f(CY - 4)}" width="200" height="60" fill="{TONGUE}"/>'
    return mouth("pat" + ("d" if down else "u"), hw, top, bot, inside, over=_blin(172), lip_over=True) + _zvuk("пя")


def p_gorka() -> str:
    # «упереть кончик языка в нижние передние зубы, спинку языка выгнуть горкой».
    hw, top, bot = 42, 17, 26
    dome = _tongue(f"M58 {_f(CY + 28)} C62 {_f(CY - 26)} 138 {_f(CY - 26)} 142 {_f(CY + 28)}Z")
    shine = (f'<path d="M76 {_f(CY + 4)} Q100 {_f(CY - 15)} 124 {_f(CY + 4)}" stroke="#f8b8b0" stroke-width="3.2" '
             f'fill="none" stroke-linecap="round"/>')
    inside = dome + shine + teeth_upper(hw, top) + teeth_lower(hw, bot)
    return mouth("gorka", hw, top, bot, inside)


def _low_tongue() -> str:
    # Язык лежит внизу, кончик за нижними зубами — видна спинка.
    return _tongue(f"M54 {_f(CY + 28)} C60 {_f(CY - 9)} 140 {_f(CY - 9)} 146 {_f(CY + 28)}Z",
                   groove=f"M100 {_f(CY + 3)} L100 {_f(CY + 14)}")


def p_kacheli_niz() -> str:
    # «положить широкий язык за нижние зубы».
    hw, top, bot = 42, 18, 28
    return mouth("kniz", hw, top, bot, teeth_upper(hw, top) + _low_tongue() + teeth_lower(hw, bot))


def p_kacheli_verh() -> str:
    # «поднять за верхние зубы» — видна нижняя сторона языка и уздечка.
    hw, top, bot = 42, 18, 28
    inside = teeth_upper(hw, top) + _under(CX, CY - 9, 31, 14, CY + 22) + teeth_lower(hw, bot)
    return mouth("kverh", hw, top, bot, inside)


def p_gribok() -> str:
    # «прижав широкий язык всей плоскостью к нёбу, широко открыть рот (язык — шляпка грибка, уздечка — ножка)».
    hw, top, bot = 34, 28, 50
    inside = teeth_upper(hw, top) + _under(CX, CY - 12, 30, 17, CY + 34) + teeth_lower(hw, bot)
    return mouth("gribok", hw, top, bot, inside)


def p_garmoshka(open_: bool) -> str:
    # «приклеить язык к нёбу и, не отпуская языка, закрывать и открывать рот».
    if open_:
        return p_gribok().replace("rc-gribok", "rc-garm")
    hw, top, bot = 38, 17, 24
    inside = teeth_upper(hw, top) + _under(CX, CY - 7, 29, 12, CY + 16) + teeth_lower(hw, bot)
    return mouth("garmz", hw, top, bot, inside)


def p_loshadka(up: bool) -> str:
    # «пощёлкать кончиком языка (как лошадка цокает копытами)»: язык присосан к нёбу — щелчок — язык внизу.
    hw, top, bot = 40, 20, 32
    if up:
        inside = teeth_upper(hw, top) + _under(CX, CY - 10, 29, 14, CY + 22) + teeth_lower(hw, bot)
        return mouth("losh-u", hw, top, bot, inside)
    inside = teeth_upper(hw, top) + _low_tongue() + teeth_lower(hw, bot)
    return mouth("losh-d", hw, top, bot, inside) + _zvuk("цок")


def p_malyar(forward: bool) -> str:
    # «"погладить" кончиком языка твёрдое нёбо, делая движения языком вперёд-назад».
    hw, top, bot = 42, 20, 32
    under = _under(CX, CY - 10, 30, 15, CY + 24) if forward else _under(CX, CY - 14, 24, 9, CY + 24)
    return mouth("mal-" + ("f" if forward else "b"), hw, top, bot, teeth_upper(hw, top) + under + teeth_lower(hw, bot))


def p_zuby_verh(side: int) -> str:
    # «кончиком языка "почистить" верхние зубы с внутренней стороны, двигая языком из стороны в сторону».
    hw, top, bot = 42, 19, 30
    x = CX + 15 * side
    tongue = _tongue(f"M{_f(CX - 6 * side)} {_f(CY + 26)} C{_f(CX - 4 * side)} {_f(CY + 6)} {_f(x - 8 * side)} "
                     f"{_f(CY - 10)} {_f(x + 3 * side)} {_f(CY - 9)} C{_f(x + 9 * side)} {_f(CY - 8)} {_f(x + 8 * side)} "
                     f"{_f(CY - 1)} {_f(x + 2 * side)} {_f(CY + 4)} C{_f(CX + 6 * side)} {_f(CY + 12)} {_f(CX + 6 * side)} "
                     f"{_f(CY + 20)} {_f(CX + 4 * side)} {_f(CY + 26)}Z", fill=UNDER)
    return mouth(f"zv{side}", hw, top, bot, tongue + teeth_upper(hw, top) + teeth_lower(hw, bot))


def p_zuby_niz(side: int, y_tip: float = 0) -> str:
    # «кончиком языка "почистить" нижние зубы: сначала из стороны в сторону, потом снизу вверх».
    hw, top, bot = 42, 17, 28
    x = CX + 16 * side
    yt = CY + 2 + y_tip
    tongue = _tongue(f"M{_f(CX - 30)} {_f(CY + 32)} C{_f(CX - 26)} {_f(CY + 8)} {_f(x - 12)} {_f(yt - 4)} {_f(x)} {_f(yt - 6)} "
                     f"C{_f(x + 12)} {_f(yt - 4)} {_f(CX + 26)} {_f(CY + 8)} {_f(CX + 30)} {_f(CY + 32)}Z",
                     groove=f"M{_f(x)} {_f(yt)} L{_f(x * .6 + CX * .4)} {_f(yt + 14)}")
    return mouth(f"zn{side}{int(y_tip)}", hw, top, bot, teeth_upper(hw, top) + tongue + teeth_lower(hw, bot))


def _on_upper_lip(top_y: float, groove: bool = True) -> str:
    return _tongue(f"M71 {_f(CY + 4)} C69 {_f(top_y + 12)} 80 {_f(top_y)} 100 {_f(top_y)} "
                   f"C120 {_f(top_y)} 131 {_f(top_y + 12)} 129 {_f(CY + 4)}Z",
                   groove=f"M100 {_f(top_y + 5)} L100 {_f(CY - 1)}" if groove else "")


def p_varenye(up: bool) -> str:
    # «широким передним краем языка облизать верхнюю губу движением сверху вниз (не из стороны в сторону)».
    hw, top, bot = 40, 12, 18
    inside = f'<rect x="0" y="{_f(CY - 2)}" width="200" height="60" fill="{TONGUE}"/>'
    return mouth("var-" + ("u" if up else "d"), hw, top, bot, inside, over=_on_upper_lip(122 if up else 134))


def p_indyuk(forward: bool, zvuk: bool = False) -> str:
    # «положить язык на верхнюю губу и водить широким передним краем языка по губе вперёд-назад».
    hw, top, bot = 40, 12, 18
    inside = f'<rect x="0" y="{_f(CY - 2)}" width="200" height="60" fill="{TONGUE}"/>'
    m = mouth("ind-" + ("f" if forward else "b"), hw, top, bot, inside, over=_on_upper_lip(121 if forward else 131))
    return m + (_zvuk("бл-бл") if zvuk else "")


def _cup(y_top: float) -> str:
    """Чашечка: широкий язык поднят, края и кончик загнуты — ковшик с углублением."""
    body = (f"M72 {_f(CY + 6)} C69 {_f(y_top + 30)} 71 {_f(y_top + 9)} 85 {_f(y_top + 2)} "
            f"C93 {_f(y_top - 1)} 107 {_f(y_top - 1)} 115 {_f(y_top + 2)} "
            f"C129 {_f(y_top + 9)} 131 {_f(y_top + 30)} 128 {_f(CY + 6)}Z")
    hollow = f'<ellipse cx="100" cy="{_f(y_top + 17)}" rx="17" ry="11" fill="{GROOVE}"/>'
    rim = (f'<ellipse cx="100" cy="{_f(y_top + 17)}" rx="21.5" ry="14.5" fill="none" stroke="#f8b8b0" '
           f'stroke-width="3.2"/>')
    return _tongue(body) + hollow + rim


def _groove_tongue(top_y: float) -> str:
    """Язык на верхней губе «желобком» («Фокус»): посередине канавка, края приподняты."""
    t = _on_upper_lip(top_y, groove=False)
    ch = (f'<path d="M95 {_f(top_y + 5)} Q100 {_f(top_y + 2)} 105 {_f(top_y + 5)} L104 {_f(CY - 1)} '
          f'Q100 {_f(CY + 1)} 96 {_f(CY - 1)}Z" fill="{GROOVE}"/>')
    edges = (f'<path d="M89 {_f(top_y + 4)} Q86 {_f(top_y + 14)} 88 {_f(CY - 2)}" stroke="#f8b8b0" stroke-width="3" '
             f'fill="none" stroke-linecap="round"/>'
             f'<path d="M111 {_f(top_y + 4)} Q114 {_f(top_y + 14)} 112 {_f(CY - 2)}" stroke="#f8b8b0" stroke-width="3" '
             f'fill="none" stroke-linecap="round"/>')
    return t + ch + edges


def p_chashechka() -> str:
    # «Широкий язык поднять вверх, загнув боковые края и кончик так, чтобы получилась чашечка».
    hw, top, bot = 42, 18, 26
    inside = teeth_upper(hw, top) + f'<rect x="0" y="{_f(CY)}" width="200" height="60" fill="{TONGUE}"/>' + teeth_lower(hw, bot)
    return mouth("chash", hw, top, bot, inside, over=_cup(108))


def p_fokus(blow: bool) -> str:
    # «положить широкий передний край языка на верхнюю губу желобком и сдуть ватку, положенную на кончик носа».
    hw, top, bot = 40, 14, 20
    inside = f'<rect x="0" y="{_f(CY - 2)}" width="200" height="60" fill="{TONGUE}"/>'
    m = mouth("fok-" + ("b" if blow else "s"), hw, top, bot, inside, over=_groove_tongue(120))
    vy = 92 if blow else 104
    vatka = (f'<circle cx="100" cy="{vy}" r="7" fill="#fff" stroke="#c9c2b8" stroke-width="1.4"/>'
             f'<circle cx="96" cy="{vy - 3}" r="4" fill="#fff" stroke="#c9c2b8" stroke-width="1.2"/>')
    air = _air([(92, 119, 90, 108), (100, 117, 100, 106), (108, 119, 110, 108)]) if blow else ""
    return m + air + vatka


def p_chasiki(side: int) -> str:
    # «делать движения кончиком языка от одного угла рта к другому».
    hw, top, bot = 40, 15, 22
    s = side
    tip = CX + (hw + 5) * s
    tongue = _tongue(f"M{_f(CX - 4 * s)} {_f(CY + 7)} C{_f(CX + 14 * s)} {_f(CY - 3)} {_f(tip - 14 * s)} {_f(CY - 5)} "
                     f"{_f(tip)} {_f(CY - 1)} C{_f(tip + 5 * s)} {_f(CY + 1)} {_f(tip + 4 * s)} {_f(CY + 6)} {_f(tip - 2 * s)} "
                     f"{_f(CY + 7)} C{_f(tip - 14 * s)} {_f(CY + 10)} {_f(CX + 12 * s)} {_f(CY + 13)} {_f(CX - 4 * s)} "
                     f"{_f(CY + 12)}Z")
    inside = teeth_upper(hw, top) + teeth_lower(hw, bot)
    return mouth(f"ch{s}", hw, top, bot, inside, over=tongue)


def p_parokhod() -> str:
    # «Приоткрыть рот и длительно произносить звук ы (как гудит пароход)».
    hw, top, bot = 36, 10, 16
    inside = teeth_upper(hw, top) + _low_tongue() + teeth_lower(hw, bot)
    return mouth("parokh", hw, top, bot, inside) + _zvuk("ы-ы-ы")


def p_dut_trubochka() -> str:
    # «Вытянуть губы вперёд трубочкой и длительно дуть на ватный шарик».
    return p_trubochka() + _air([(90, 170, 84, 186), (100, 172, 100, 190), (110, 170, 116, 186)])


POZY: Dict[str, Callable[[], str]] = {
    "zakryt": p_zakryt,
    "zaborchik": p_zaborchik,
    "trubochka": p_trubochka,
    "blinchik": p_blinchik,
    "dut_yazyk": p_dut_yazyk,
    "pat_niz": lambda: p_pat(True),
    "pat_verh": lambda: p_pat(False),
    "gorka": p_gorka,
    "kacheli_niz": p_kacheli_niz,
    "kacheli_verh": p_kacheli_verh,
    "gribok": p_gribok,
    "garmoshka_otkr": lambda: p_garmoshka(True),
    "garmoshka_zakr": lambda: p_garmoshka(False),
    "loshadka_verh": lambda: p_loshadka(True),
    "loshadka_niz": lambda: p_loshadka(False),
    "malyar_vpered": lambda: p_malyar(True),
    "malyar_nazad": lambda: p_malyar(False),
    "zuby_verh_l": lambda: p_zuby_verh(-1),
    "zuby_verh_r": lambda: p_zuby_verh(1),
    "zuby_niz_l": lambda: p_zuby_niz(-1),
    "zuby_niz_r": lambda: p_zuby_niz(1),
    "zuby_niz_vniz": lambda: p_zuby_niz(0, 6),
    "zuby_niz_vverh": lambda: p_zuby_niz(0, -6),
    "varenye_verh": lambda: p_varenye(True),
    "varenye_niz": lambda: p_varenye(False),
    "indyuk_vpered": lambda: p_indyuk(True),
    "indyuk_nazad": lambda: p_indyuk(False),
    "indyuk_bl_vpered": lambda: p_indyuk(True, True),
    "indyuk_bl_nazad": lambda: p_indyuk(False, True),
    "chashechka": p_chashechka,
    "chashechka_vnutri": p_kacheli_verh,
    "fokus_chashka": lambda: p_fokus(False),
    "fokus_dut": lambda: p_fokus(True),
    "chasiki_l": lambda: p_chasiki(-1),
    "chasiki_r": lambda: p_chasiki(1),
    "parokhod": p_parokhod,
    "dut_trubochka": p_dut_trubochka,
}


# Крупно рот — от кончика носа до подбородка, как на логопедических карточках.
# ⚠ 24.11: было круглое лицо с глазами — автор: «монструозно… колобок». Глаза и голова
# отвлекают от языка; в кадре остаются нос (на него кладут ватку в «Фокусе») и рот.
VIEWBOX = "30 84 140 140"
FACE = (f'<rect x="30" y="84" width="140" height="140" rx="26" fill="{SKIN}"/>'
        '<path d="M86 96 Q100 108 114 96" fill="none" stroke="#c98a72" stroke-width="3" stroke-linecap="round"/>'
        '<path d="M92 99 Q95 101 97 99" fill="none" stroke="#c98a72" stroke-width="1.6" stroke-linecap="round"/>'
        '<path d="M103 99 Q105 101 108 99" fill="none" stroke="#c98a72" stroke-width="1.6" stroke-linecap="round"/>'
        '<path d="M78 206 Q100 216 122 206" fill="none" stroke="#e3b49c" stroke-width="2.4" stroke-linecap="round"/>')


def svg(poza: str, size: int = 200) -> str:
    """Лицо с ртом в позе — целый SVG."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VIEWBOX}" width="{size}" height="{size}" '
            f'role="img" aria-label="Схема рта">{FACE}<g class="rot">{POZY[poza]()}</g></svg>')


def all_mouths() -> Dict[str, str]:
    """Только рот каждой позы — лицо экран рисует один раз и меняет рот."""
    return {k: f() for k, f in POZY.items()}
