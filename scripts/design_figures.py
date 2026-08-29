#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""デザインのアートボードに載せる数値を、実データから一括で算出して出力する。

手で書いた数値がデータとずれる事故を防ぐための補助スクリプト。
出力される JSON をそのまま .dc.html の renderVals() に貼る。
"""
import collections
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import tech_dict as td  # noqa: E402

CAT = {n: c for n, c, _ in td.TECHS}
WINDOW_MAX = 8  # 直近/前期の比較窓の上限（週）。実際は週数の半分で頭打ちにする。


def load():
    with open(os.path.join(ROOT, "docs/data/trends.json"), encoding="utf-8") as f:
        trends = json.load(f)
    with open(os.path.join(ROOT, "docs/data/summary.json"), encoding="utf-8") as f:
        summary = json.load(f)
    rows = []
    with open(os.path.join(ROOT, "data/projects.jsonl"), encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    return trends, summary, rows


def pick_window(trends):
    """比較窓。前期側が空にならないよう、週数の半分を超えないようにする。"""
    return max(2, min(WINDOW_MAX, len(trends["weeks"]) // 2))


def momentum(trends, window=None):
    """(技術, 直近window週の件数, その前window週の件数, 増減, 成長率) を返す。"""
    window = window or pick_window(trends)
    out = []
    for s in trends["series"]:
        c = s["counts"]
        recent = sum(c[-window:])
        prev = sum(c[-2 * window:-window])
        if recent + prev < 4:
            continue
        out.append({
            "name": s["name"], "cat": s.get("category", CAT.get(s["name"], "その他")),
            "recent": recent, "prev": prev, "delta": recent - prev,
            # 分母が小さいときに成長率が跳ねないよう +2 で減衰させる
            "growth": (recent - prev) / (prev + 2),
            "total": s["total"],
        })
    return out


def priority(mom, w_vol=0.4, w_growth=0.6):
    if not mom:
        return []
    max_v = max(m["recent"] for m in mom) or 1
    max_g = max(m["growth"] for m in mom) or 1
    for m in mom:
        nv = m["recent"] / max_v
        ng = max(0.0, m["growth"]) / max_g if max_g > 0 else 0.0
        m["score"] = round(w_vol * nv + w_growth * ng, 3)
        m["growth_pct"] = f"{round(m['growth'] * 100):+d}%"
    return sorted(mom, key=lambda m: -m["score"])


def cooccurrence(rows, keys, top=5):
    pairs = collections.Counter()
    for r in rows:
        ts = sorted(set(r["techs"]))
        for a in ts:
            for b in ts:
                if a != b:
                    pairs[(a, b)] += 1
    out = []
    for k in keys:
        partners = sorted(
            ((b, n) for (a, b), n in pairs.items() if a == k),
            key=lambda x: (-x[1], x[0]))[:top]
        out.append({"name": k, "with": [f"{b} ({n})" for b, n in partners]})
    return out


def crosstab(rows, n_pos=6, n_ind=6):
    pos = [p for p, _ in collections.Counter(
        r["position"] for r in rows).most_common(n_pos)]
    inds = [i for i, _ in collections.Counter(
        r["industry"] for r in rows).most_common(n_ind + 1) if i != "不明"][:n_ind - 1]
    inds.append("不明")
    grid = [[sum(1 for r in rows if r["industry"] == i and r["position"] == p)
             for p in pos] for i in inds]
    labels = ["業界未記載" if i == "不明" else i for i in inds]
    return pos, labels, grid


def main():
    trends, summary, rows = load()
    mom = momentum(trends)
    ranked = priority(mom)
    top10 = ranked[:10]
    pos, ind_labels, grid = crosstab(rows)
    latest = summary["latest_week"]
    with open(os.path.join(ROOT, f"docs/data/weeks/{latest}.json"), encoding="utf-8") as f:
        week = json.load(f)
    wtech = collections.Counter(t for p in week["projects"] for t in p["techs"])

    out = {
        "totals": summary["totals"],
        "range": [trends["weeks"][0], trends["weeks"][-1]],
        "window": pick_window(trends),
        "rank": [{k: m[k] for k in
                  ("name", "cat", "score", "recent", "prev", "growth_pct")} for m in top10],
        "scatter": [{k: m[k] for k in ("name", "cat", "recent", "delta", "total")}
                    for m in ranked[:16]],
        "cooc": cooccurrence(rows, [m["name"] for m in top10[:5]]),
        "crosstab": {"positions": pos, "industries": ind_labels, "grid": grid,
                     "max": max(max(r) for r in grid)},
        "dist": {k: summary["distributions"][k][:8]
                 for k in ("position", "industry", "workstyle")},
        "rate": {k: v for k, v in summary["rate"].items() if k != "bins"},
        "latest_week": latest,
        "latest": summary["latest"],
        "latest_tech": wtech.most_common(12),
        "latest_pos": collections.Counter(p["position"] for p in week["projects"]).most_common(),
        "latest_ind": collections.Counter(p["industry"] for p in week["projects"]).most_common(),
        "latest_ws": collections.Counter(p["workstyle"] for p in week["projects"]).most_common(),
        "weekly": [[w["week"], w["projects"], w["new_projects"]] for w in trends["weekly"]],
    }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main()
