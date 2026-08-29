#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""デザインのアートボードに載せる数値を、ビルド済みJSONから取り出す。

数値を手で書き写すとデータとずれる。inject_figures.py がこの出力を
design/*.dc.html の FIGURES ブロックへ流し込む。
"""
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "docs", "data")


def load(name):
    with open(os.path.join(D, name), encoding="utf-8") as f:
        return json.load(f)


def main():
    summary, trends = load("summary.json"), load("trends.json")
    strat, cube = load("strategy.json"), load("cube.json")
    week = load(os.path.join("weeks", f"{summary['latest_week']}.json"))

    w = {"volume": 0.4, "growth": 0.6}
    ranked = sorted(
        strat["momentum"],
        key=lambda m: -(w["volume"] * m["nvol"] + w["growth"] * m["ngrowth"]))
    for m in ranked:
        m["score"] = round(w["volume"] * m["nvol"] + w["growth"] * m["ngrowth"], 3)
        m["growth_pct"] = f"{round(m['growth'] * 100):+d}%"

    ps = week["projects"]
    cnt = lambda key: collections.Counter(p[key] for p in ps).most_common()

    out = {
        "totals": summary["totals"],
        "tech_count": len(trends["series"]),
        "range": [trends["weeks"][0], trends["weeks"][-1]],
        "window": strat["window"],
        "weights": w,
        "rank": [{k: m[k] for k in
                  ("name", "cat", "score", "recent", "prev", "growth_pct")}
                 for m in ranked[:10]],
        # 2軸マップは延べ出現数の多い順に上位を拾う（スコア順だと右下が空く）
        "scatter": [{k: m[k] for k in ("name", "cat", "recent", "delta", "total")}
                    for m in sorted(strat["momentum"],
                                    key=lambda m: -m["total"])[:18]],
        "cooc": [{"name": m["name"],
                  "with": [f"{x['name']} ({x['n']})"
                           for x in strat["cooccurrence"].get(m["name"], [])[:5]]}
                 for m in ranked[:5] if m["name"] in strat["cooccurrence"]],
        "must": summary["must_rate"][:6],
        "opt": summary["must_rate_low"][:6],
        "supply": summary["supply"][:6],
        "rate": {k: v for k, v in summary["rate"].items() if k != "bins"},
        "cube": {"positions": cube["positions"][:6],
                 "industries": cube["industries"][:6],
                 "categories": cube["categories"][:6],
                 "max": cube["max"],
                 "cells": [c for c in cube["cells"]
                           if c["p"] < 6 and c["i"] < 6 and c["c"] < 6]},
        "latest_week": summary["latest_week"],
        "latest": summary["latest"],
        "latest_tech": collections.Counter(
            t for p in ps for t in p["techs"]).most_common(12),
        "latest_pos": cnt("position"),
        "latest_ind": cnt("industry"),
        "latest_ws": cnt("workstyle"),
        "latest_ratio": collections.Counter(
            "不明" if p["ratio_max"] is None else
            ("〜30%" if p["ratio_max"] <= 30 else
             "31〜50%" if p["ratio_max"] <= 50 else
             "51〜80%" if p["ratio_max"] <= 80 else "81〜100%")
            for p in ps).most_common(),
        "latest_cards": [
            {"pos": p["position"], "ind": p["industry"], "ws": p["workstyle"],
             "ratio": p["ratio_max"], "new": p["is_new"], "techs": p["techs"][:5]}
            for p in sorted(ps, key=lambda x: -len(x["techs"]))[:6]],
        "weekly": [[x["week"], x["projects"], x["new_projects"]]
                   for x in trends["weekly"]],
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
