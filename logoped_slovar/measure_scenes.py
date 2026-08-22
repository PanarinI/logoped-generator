"""Замер укладки спрайтов сцены: что реально доходит до бумаги.

Зачем. Автор решил 08-19 заказать генератору СЛОВАРЬ СПРАЙТОВ — рисовать не
сцену целиком, а её предметы по отдельности, тем же конвейером, что 979
картинок корпуса. Прежде чем платить за картинки, надо знать, какие из них
вообще выходят на лист: сцена укладывается ВОКРУГ дорожки, и если для предмета
нет свободного места, он просто не печатается («пустое место честнее обрезанного
домика», `Canvas.place`). Заказать спрайт, который не ложится ни разу, — значит
заплатить за то, чего логопед никогда не увидит.

Что делает. Подменяет `Canvas.spread` счётчиком, прогоняет все сцены на
настоящем холсте слоговой дорожки (те же ширина, высота и список занятых кругов,
что в `track._render`) и печатает по каждому спрайту: сколько раз сцена его
попросила и сколько раз он лёг.

Запуск:  python3 measure_scenes.py [--rows N] [--cols N] [--md ПУТЬ]

Замер зависит от числа кружков: чем их больше, тем меньше места остаётся сцене.
Поэтому строку замера без указания rows/cols читать нельзя — она бессмысленна.
"""

from __future__ import annotations

import argparse
import sys
from typing import Any, Callable, Dict, List, Tuple

import scenes as SC
import track as T


def measure(rows: int, cols: int) -> Tuple[List[Dict[str, Any]], Dict[str, float]]:
    """Прогнать все сцены и вернуть построчный замер + размеры холста."""
    # Холст ровно такой, каким его строит рендер дорожки: та же высота из числа
    # рядов и тот же список занятых кругов. Иначе замер мерил бы не наш лист.
    height = T._TOP + (rows - 1) * T._ROW_H + T._R + T._AMP + 8.0
    cells = rows * cols

    rowsout: List[Dict[str, Any]] = []
    real_spread = SC.Canvas.spread

    for scene_name in SC.SCENES:
        shape = T.shape_for(scene_name)
        avoid = T._occupied(rows, cols, cells, shape)

        log: List[Dict[str, Any]] = []

        def counting(self: SC.Canvas, sprite: Callable[..., None],
                     bw: float, bh: float, zone: str, n: int,
                     fallback: bool = True, **kw: Any) -> int:
            made = real_spread(self, sprite, bw, bh, zone, n,
                               fallback=fallback, **kw)
            log.append({
                "scene": scene_name,
                "sprite": getattr(sprite, "__name__", "?").removeprefix("_sp_"),
                "w": bw, "h": bh, "zone": zone,
                "asked": n, "placed": made,
            })
            return made

        SC.Canvas.spread = counting          # type: ignore[method-assign]
        try:
            SC.scene_svg(scene_name, T._W, height, avoid=avoid)
        finally:
            SC.Canvas.spread = real_spread   # type: ignore[method-assign]

        rowsout.extend(log)

    return rowsout, {"w": T._W, "h": height, "avoid": len(avoid), "cells": cells}


def report(rows_out: List[Dict[str, Any]], canvas: Dict[str, float],
           rows: int, cols: int) -> str:
    """Собрать отчёт человеческим языком: сперва приговор, потом таблица."""
    out: List[str] = []
    out.append(f"# Замер укладки спрайтов сцены — {rows}×{cols}\n")
    out.append(
        f"Холст {canvas['w']:.0f}×{canvas['h']:.0f} мм · кружков {int(canvas['cells'])} · "
        f"занятых кругов {int(canvas['avoid'])}.\n"
    )
    out.append(
        "Сцена укладывается вокруг дорожки. Спрайт, которому не хватило места, "
        "не печатается вовсе — значит и заказывать его картинкой незачем, пока "
        "не уменьшен бокс или не срезано число кружков.\n"
    )

    # Свод по спрайту: один предмет живёт в нескольких сценах и в разных боксах.
    by_sprite: Dict[str, Dict[str, Any]] = {}
    for r in rows_out:
        s = by_sprite.setdefault(r["sprite"], {"asked": 0, "placed": 0,
                                               "boxes": set(), "scenes": set()})
        s["asked"] += r["asked"]
        s["placed"] += r["placed"]
        s["boxes"].add(f"{r['w']:g}×{r['h']:g}")
        s["scenes"].add(r["scene"])

    dead = sorted(k for k, v in by_sprite.items() if v["placed"] == 0)
    weak = sorted(k for k, v in by_sprite.items()
                  if 0 < v["placed"] < v["asked"] * 0.5)

    out.append("## Приговор\n")
    out.append(f"- **Не ложатся НИ РАЗУ ({len(dead)}):** "
               + (", ".join(f"`{d}`" for d in dead) if dead else "нет") + "\n")
    out.append(f"- **Ложатся меньше половины запрошенного ({len(weak)}):** "
               + (", ".join(f"`{w}`" for w in weak) if weak else "нет") + "\n")
    out.append(f"- Всего спрайтов в замере: **{len(by_sprite)}**\n")

    out.append("\n## По спрайтам\n")
    out.append("| спрайт | боксы, мм | запрошено | легло | сцены |")
    out.append("|---|---|---:|---:|---|")
    for name in sorted(by_sprite, key=lambda k: (by_sprite[k]["placed"], k)):
        v = by_sprite[name]
        out.append(f"| `{name}` | {' · '.join(sorted(v['boxes']))} | "
                   f"{v['asked']} | {v['placed']} | {', '.join(sorted(v['scenes']))} |")

    out.append("\n## По сценам\n")
    out.append("| сцена | запрошено | легло | пусто |")
    out.append("|---|---:|---:|---|")
    scenes_agg: Dict[str, Dict[str, Any]] = {}
    for r in rows_out:
        s = scenes_agg.setdefault(r["scene"], {"asked": 0, "placed": 0, "dead": []})
        s["asked"] += r["asked"]
        s["placed"] += r["placed"]
        if r["placed"] == 0:
            s["dead"].append(r["sprite"])
    for name, v in scenes_agg.items():
        out.append(f"| {name} | {v['asked']} | {v['placed']} | "
                   f"{', '.join(sorted(set(v['dead']))) or '—'} |")

    return "\n".join(out) + "\n"


def main(argv: List[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    # Умолчание — то же, что у дорожки: 6 рядов по 5 кружков.
    ap.add_argument("--rows", type=int, default=T.ROWS_DEFAULT)
    ap.add_argument("--cols", type=int, default=T.COLS)
    ap.add_argument("--md", default="", help="куда положить отчёт (иначе на экран)")
    args = ap.parse_args(argv)

    rows_out, canvas = measure(args.rows, args.cols)
    text = report(rows_out, canvas, args.rows, args.cols)

    if args.md:
        with open(args.md, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"отчёт записан: {args.md}")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
