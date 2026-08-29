#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""エッジテクノロジー週次案件メール → トレンド集計JSON

入力:
  data/raw/YYYY-MM-DD_<messageId>.txt  生メール本文（gitignore）
  data/projects.jsonl                  匿名化済み正規化データ（git管理・マージ対象）
出力:
  data/projects.jsonl                  上記を更新
  docs/data/{meta,trends,summary}.json および docs/data/weeks/YYYY-MM-DD.json

LLM は一切使わない。決定論的・再現性100%。
"""
from __future__ import annotations

import argparse
import collections
import datetime as dt
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tech_dict as td  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(ROOT, "data", "raw")
PROJECTS_PATH = os.path.join(ROOT, "data", "projects.jsonl")
STATE_PATH = os.path.join(ROOT, "data", "state.json")
OUT_DIR = os.path.join(ROOT, "docs", "data")
WEEKS_DIR = os.path.join(OUT_DIR, "weeks")

FIELD_KEYS = [
    "案件", "月額単価", "契約形態", "精算時間", "作業場所", "稼働形態", "貸与PC",
    "契約開始", "稼働率", "募集人数", "商談回数", "業界", "ポジション",
    "案件内容", "必須スキル", "尚可スキル", "補足事項",
]
# ラベルと値の区切りには全角スペースが挟まる（例: "[案件]　　　："）。
# Python3 の \s は U+3000 にもマッチするので \s* で吸収できる。
_KEY_ALT = "|".join(re.escape(k) for k in FIELD_KEYS)
FIELD_RE = re.compile(
    r"\[(" + _KEY_ALT + r")\]\s*[：:]\s*(.*?)(?=\[(?:" + _KEY_ALT + r")\]\s*[：:]|\Z)",
    re.DOTALL,
)
BLOCK_SPLIT_RE = re.compile(r"={10,}")
CASE_NO_RE = re.compile(r"案件番号\s*(\d{3,8})")

TECH_PATTERNS = [(n, c, re.compile(p, re.IGNORECASE)) for n, c, p in td.TECHS]
WORKSTYLE_PATTERNS = [(n, re.compile(p, re.IGNORECASE)) for n, p in td.WORKSTYLE_RULES]
POSITION_PATTERNS = [(n, re.compile(p, re.IGNORECASE)) for n, p in td.POSITION_RULES]


# ---------------------------------------------------------------- parsing

def anon_id(case_no: str) -> str:
    """案件番号は生のまま公開しない。安定ハッシュの先頭12桁を識別子にする。"""
    return hashlib.sha1(f"edge-tech:{case_no}".encode("utf-8")).hexdigest()[:12]


def norm_ws(s: str) -> str:
    return re.sub(r"[\s　]+", " ", s).strip()


def parse_rate(raw: str):
    """月額単価を万円単位の (min, max) に。記載が無ければ (None, None)。"""
    if not raw:
        return None, None
    t = raw.replace(",", "")
    man = [int(m) for m in re.findall(r"(\d{2,4})\s*万", t)]
    if not man:
        yen = [int(m) for m in re.findall(r"(\d{6,8})\s*円", t)]
        man = [y // 10000 for y in yen]
    man = [v for v in man if 10 <= v <= 500]
    if not man:
        return None, None
    return min(man), max(man)


def parse_ratio(raw: str):
    """稼働率を (min, max) の百分率に。"""
    if not raw:
        return None, None
    nums = [int(m) for m in re.findall(r"(\d{1,3})\s*%", raw)]
    nums = [n for n in nums if 0 < n <= 100]
    if not nums:
        return None, None
    return min(nums), max(nums)


def match_first(patterns, text: str, default: str):
    for name, rx in patterns:
        if rx.search(text):
            return name
    return default


def extract_techs(text: str):
    found = []
    for name, cat, rx in TECH_PATTERNS:
        if rx.search(text):
            found.append(name)
    return sorted(set(found))


def parse_email(text: str, week: str, message_id: str):
    """1通のメール本文から案件レコードのリストを返す。"""
    records = []
    for block in BLOCK_SPLIT_RE.split(text):
        m = CASE_NO_RE.search(block)
        if not m:
            continue
        case_no = m.group(1)
        fields = {k: norm_ws(v) for k, v in FIELD_RE.findall(block)}
        if not fields.get("案件"):
            continue

        skill_text = " ".join(
            fields.get(k, "")
            for k in ("案件", "案件内容", "必須スキル", "尚可スキル", "補足事項")
        )
        # 必須と尚可を分けておく。「必須で書かれる＝持たないと土俵に乗れない」
        # 「尚可止まり＝差別化に効く」を後段で区別するため。
        techs_req = extract_techs(fields.get("必須スキル", ""))
        techs_opt = [t for t in extract_techs(fields.get("尚可スキル", ""))
                     if t not in techs_req]
        rate_min, rate_max = parse_rate(fields.get("月額単価", ""))
        ratio_min, ratio_max = parse_ratio(fields.get("稼働率", ""))

        industry = fields.get("業界", "") or "-"
        if industry in ("-", "", "要確認"):
            industry = "不明"

        pos_raw = fields.get("ポジション", "") or ""
        title = fields.get("案件", "")
        pos_src = pos_raw if pos_raw not in ("", "-") else title
        position = match_first(POSITION_PATTERNS, pos_src, "その他")

        workstyle = match_first(
            WORKSTYLE_PATTERNS, fields.get("稼働形態", ""), "不明"
        )

        records.append({
            "id": anon_id(case_no),
            "week": week,
            "message_id": message_id,
            "position": position,
            "industry": industry,
            "workstyle": workstyle,
            "rate_min": rate_min,
            "rate_max": rate_max,
            "ratio_min": ratio_min,
            "ratio_max": ratio_max,
            "start": fields.get("契約開始", "") or "",
            "contract": fields.get("契約形態", "") or "",
            "techs": extract_techs(skill_text),
            "techs_req": techs_req,
            "techs_opt": techs_opt,
        })
    return records


# ---------------------------------------------------------------- io

RAW_NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:_([A-Za-z0-9]+))?\.txt$")


def load_raw_records():
    """(レコード一覧, 処理済みソースキー集合) を返す。"""
    recs, seen, bad = [], set(), []
    if not os.path.isdir(RAW_DIR):
        return recs, seen, bad
    for fn in sorted(os.listdir(RAW_DIR)):
        m = RAW_NAME_RE.match(fn)
        if not m:
            continue
        week, mid = m.group(1), m.group(2) or m.group(1)
        with open(os.path.join(RAW_DIR, fn), encoding="utf-8") as f:
            got = parse_email(f.read(), week, mid)
        if not got:
            # Gmail の text/plain パートが空テンプレートのことがある（2025年前半に多い）。
            # 実データは text/html 側にしか無いので、取り込みを黙って通さない。
            bad.append(fn)
            continue
        seen.add(f"{week}_{mid}")
        recs.extend(got)
    return recs, seen, bad


def update_state(seen):
    """処理済みメールの記録。data/raw は git 管理外なので、
    ここを唯一の永続的な「取得済み」台帳にする（和集合でのみ更新）。"""
    state = {"processed": []}
    if os.path.exists(STATE_PATH):
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                state = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass
    merged = sorted(set(state.get("processed", [])) | set(seen))
    return {
        "source": "coordinator@edge-tech.co.jp",
        "note": "各要素は <受信日>_<threadId>。ai-jobs-update スキルが差分判定に使う。",
        "processed": merged,
    }


def load_projects():
    if not os.path.exists(PROJECTS_PATH):
        return []
    out = []
    with open(PROJECTS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def merge(existing, fresh):
    """(id, week) をキーにマージ。新しくパースした方を優先する。"""
    by_key = {(r["id"], r["week"]): r for r in existing}
    for r in fresh:
        by_key[(r["id"], r["week"])] = r
    return [by_key[k] for k in sorted(by_key, key=lambda k: (k[1], k[0]))]


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1, sort_keys=False)
        f.write("\n")


# ---------------------------------------------------------------- aggregate

RATIO_BANDS = ["〜30%", "31〜50%", "51〜80%", "81〜100%", "不明"]


def ratio_band(pct):
    if pct is None:
        return "不明"
    if pct <= 30:
        return "〜30%"
    if pct <= 50:
        return "31〜50%"
    if pct <= 80:
        return "51〜80%"
    return "81〜100%"


RATE_BINS = [(0, 49, "〜49万"), (50, 69, "50〜69万"), (70, 89, "70〜89万"),
             (90, 109, "90〜109万"), (110, 129, "110〜129万"), (130, 9999, "130万〜")]


def rate_band(man):
    for lo, hi, label in RATE_BINS:
        if lo <= man <= hi:
            return label
    return RATE_BINS[-1][2]


def counter_to_list(c: collections.Counter, limit=None):
    items = sorted(c.items(), key=lambda kv: (-kv[1], kv[0]))
    if limit:
        items = items[:limit]
    return [{"name": k, "count": v} for k, v in items]


MOMENTUM_MAX = 8   # 直近/前期の比較窓の上限（週）


def build_strategy(records, trends, first_seen, week_index):
    """「次にどの技術を取りに行くか」を決めるための指標一式。

    重みはクライアント側で変えられるよう、正規化済みの素点まで出して
    合成スコア自体は画面で計算させる。
    """
    weeks = trends["weeks"]
    win = max(2, min(MOMENTUM_MAX, len(weeks) // 2))
    cat_of = {n: c for n, c, _ in td.TECHS}

    mom = []
    for s in trends["series"]:
        c = s["counts"]
        recent, prev = sum(c[-win:]), sum(c[-2 * win:-win])
        if recent + prev < 4:
            continue
        mom.append({
            "name": s["name"], "cat": s.get("category", cat_of.get(s["name"], "その他")),
            "recent": recent, "prev": prev, "delta": recent - prev,
            # 分母が小さいときに率が跳ねないよう +2 で減衰させる
            "growth": round((recent - prev) / (prev + 2), 3),
            "total": s["total"],
        })
    if mom:
        mv = max(m["recent"] for m in mom) or 1
        mg = max((m["growth"] for m in mom), default=1) or 1
        for m in mom:
            m["nvol"] = round(m["recent"] / mv, 4)
            m["ngrowth"] = round(max(0.0, m["growth"]) / mg, 4) if mg > 0 else 0.0
    mom.sort(key=lambda m: -m["recent"])

    # 共起（同じ案件で同時に求められる技術）
    pairs = collections.Counter()
    solo = collections.Counter()
    for r in records:
        ts = sorted(set(r["techs"]))
        for a in ts:
            solo[a] += 1
            for b in ts:
                if a != b:
                    pairs[(a, b)] += 1
    keys = [m["name"] for m in sorted(mom, key=lambda m: -m["total"])[:30]]
    cooc = {}
    for k in keys:
        partners = sorted(((b, n) for (a, b), n in pairs.items() if a == k),
                          key=lambda x: (-x[1], x[0]))[:6]
        cooc[k] = [{"name": b, "n": n, "rate": round(n / solo[k], 3)}
                   for b, n in partners]

    return {
        "window": win,
        "momentum": mom,
        "cooccurrence": cooc,
        "weights": {"volume": 0.4, "growth": 0.6},
        "note": ("成長率は 直近{w}週 と その前{w}週 の比較。"
                 "分母が小さい技術で率が跳ねないよう減衰させている。").format(w=win),
    }


def build_cube(records, n_pos=7, n_ind=7):
    """業界 × ロール × 技術カテゴリ の3次元クロス集計。

    1案件が複数の技術カテゴリを持つため、カテゴリ軸では案件が重複計上される
    （「その組み合わせを求めた案件が何件あるか」を数えている）。
    """
    cat_of = {n: c for n, c, _ in td.TECHS}
    positions = [p for p, _ in collections.Counter(
        r["position"] for r in records).most_common(n_pos)]
    inds = [i for i, _ in collections.Counter(
        r["industry"] for r in records).most_common(n_ind + 1) if i != "不明"]
    inds = inds[:n_ind - 1] + ["不明"]
    cats = [c for c, _ in collections.Counter(
        cat_of.get(t, "その他") for r in records for t in r["techs"]).most_common(8)]

    pi = {v: i for i, v in enumerate(positions)}
    ii = {v: i for i, v in enumerate(inds)}
    ci = {v: i for i, v in enumerate(cats)}

    counts = collections.Counter()
    for r in records:
        if r["position"] not in pi or r["industry"] not in ii:
            continue
        for c in {cat_of.get(t, "その他") for t in r["techs"]}:
            if c in ci:
                counts[(ii[r["industry"]], pi[r["position"]], ci[c])] += 1

    cells = [{"i": i, "p": p, "c": c, "n": n}
             for (i, p, c), n in sorted(counts.items())]
    return {
        "industries": ["業界未記載" if i == "不明" else i for i in inds],
        "positions": positions,
        "categories": cats,
        "cells": cells,
        "max": max((x["n"] for x in cells), default=0),
        "note": "1案件が複数の技術カテゴリを持つため、カテゴリ軸では重複計上される。",
    }


def aggregate(records):
    weeks = sorted({r["week"] for r in records})
    week_index = {w: i for i, w in enumerate(weeks)}

    first_seen, last_seen = {}, {}
    for r in records:
        pid = r["id"]
        if pid not in first_seen or r["week"] < first_seen[pid]:
            first_seen[pid] = r["week"]
        if pid not in last_seen or r["week"] > last_seen[pid]:
            last_seen[pid] = r["week"]

    tech_meta = {n: c for n, c, _ in td.TECHS}
    tech_week = collections.defaultdict(lambda: [0] * len(weeks))
    per_week = collections.defaultdict(list)
    for r in records:
        per_week[r["week"]].append(r)
        for t in r["techs"]:
            tech_week[t][week_index[r["week"]]] += 1

    series = []
    for name, counts in tech_week.items():
        series.append({
            "name": name,
            "category": tech_meta.get(name, "その他"),
            "counts": counts,
            "total": sum(counts),
        })
    series.sort(key=lambda s: (-s["total"], s["name"]))

    # 直近4週 vs その前4週 で急上昇/急落を出す
    rising = []
    if len(weeks) >= 2:
        n = min(4, len(weeks) // 2)
        for s in series:
            recent = sum(s["counts"][-n:])
            prev = sum(s["counts"][-2 * n:-n])
            if recent + prev >= 3:
                rising.append({
                    "name": s["name"], "category": s["category"],
                    "recent": recent, "prev": prev, "delta": recent - prev,
                })
        rising.sort(key=lambda x: (-x["delta"], -x["recent"]))

    latest = weeks[-1] if weeks else None
    latest_recs = per_week.get(latest, [])
    new_ids = [r["id"] for r in latest_recs if first_seen[r["id"]] == latest]

    weekly = []
    for w in weeks:
        rs = per_week[w]
        weekly.append({
            "week": w,
            "projects": len(rs),
            "new_projects": sum(1 for r in rs if first_seen[r["id"]] == w),
        })

    def dist(key, recs):
        return counter_to_list(collections.Counter(r[key] for r in recs))

    rates = [r["rate_max"] for r in records if r["rate_max"]]
    spans = []
    for pid, fw in first_seen.items():
        span = week_index[last_seen[pid]] - week_index[fw] + 1
        if span >= 2:
            sample = next(r for r in records if r["id"] == pid)
            spans.append({
                "id": pid, "weeks": span,
                "first_week": fw, "last_week": last_seen[pid],
                "position": sample["position"], "industry": sample["industry"],
                "techs": sample["techs"][:6],
            })
    spans.sort(key=lambda x: (-x["weeks"], x["first_week"]))

    # --- 必須率: その技術が [必須スキル] に書かれた割合 ---
    tech_any, tech_req_c, tech_fresh = (collections.Counter() for _ in range(3))
    tech_projects = collections.defaultdict(set)
    for r in records:
        is_new = first_seen[r["id"]] == r["week"]
        for t in set(r["techs"]):
            tech_any[t] += 1
            tech_projects[t].add(r["id"])
            if is_new:
                tech_fresh[t] += 1
        for t in set(r.get("techs_req", [])):
            tech_req_c[t] += 1

    MIN_N = max(5, len(records) // 60)   # 母数が小さい技術は率が暴れるので除外
    must_rate = sorted(
        ({"name": t, "listings": n, "req": tech_req_c[t],
          "rate": round(tech_req_c[t] / n, 3)}
         for t, n in tech_any.items() if n >= MIN_N),
        key=lambda x: (-x["rate"], -x["listings"]))

    # --- 供給不足シグナル: 掲載継続週数と、新規案件での出現率 ---
    span = {pid: week_index[last_seen[pid]] - week_index[fw] + 1
            for pid, fw in first_seen.items()}
    supply = sorted(
        ({"name": t,
          "weeks": round(sum(span[pid] for pid in tech_projects[t])
                         / len(tech_projects[t]), 2),
          "fresh": round(tech_fresh[t] / n, 3),
          "listings": n}
         for t, n in tech_any.items() if n >= MIN_N),
        key=lambda x: (-x["weeks"], -x["listings"]))

    trends = {
        "weeks": weeks,
        "weekly": weekly,
        "series": series,
        "categories": sorted({s["category"] for s in series}),
    }
    summary = {
        "latest_week": latest,
        "latest": {
            "projects": len(latest_recs),
            "new_projects": len(new_ids),
        },
        "totals": {
            "weeks": len(weeks),
            "listings": len(records),
            "unique_projects": len(first_seen),
        },
        "distributions": {
            "position": dist("position", records),
            "industry": dist("industry", records),
            "workstyle": dist("workstyle", records),
            "position_latest": dist("position", latest_recs),
            "industry_latest": dist("industry", latest_recs),
            "ratio": [
                {"name": b, "count": n} for b, n in
                sorted(collections.Counter(
                    ratio_band(r["ratio_max"]) for r in records).items(),
                    key=lambda kv: RATIO_BANDS.index(kv[0]))
            ],
        },
        "top_techs": [
            {"name": s["name"], "category": s["category"], "count": s["total"]}
            for s in series[:20]
        ],
        "rising": rising[:10],
        "falling": sorted(rising, key=lambda x: (x["delta"], -x["prev"]))[:10],
        "longest_running": spans[:10],
        "must_rate": must_rate[:20],
        "must_rate_low": must_rate[-12:][::-1],
        "supply": supply[:15],
        "min_listings": MIN_N,
        "rate": {
            "reported": len(rates),
            "missing": len(records) - len(rates),
            "min": min(rates) if rates else None,
            "max": max(rates) if rates else None,
            "median": sorted(rates)[len(rates) // 2] if rates else None,
            "bins": [
                {"name": label,
                 "count": sum(1 for v in rates if rate_band(v) == label)}
                for _, _, label in RATE_BINS
            ],
        },
        "commentary": "",
    }
    return trends, summary, per_week, first_seen, week_index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="JSONを書かず件数サマリのみ表示")
    args = ap.parse_args()

    fresh, seen, bad = load_raw_records()
    if bad:
        print("WARNING: 案件が1件も取れなかった生メールファイル "
              f"({len(bad)}件) — text/plain が空テンプレートの可能性が高い。"
              "FULL_CONTENT の html_body から取り直すこと:", file=sys.stderr)
        for fn in bad:
            print(f"  - data/raw/{fn}", file=sys.stderr)
    existing = load_projects()
    records = merge(existing, fresh)

    if not records:
        print("no records: data/raw/ にメール本文が無く data/projects.jsonl も空です",
              file=sys.stderr)
        return 1

    trends, summary, per_week, first_seen, week_index = aggregate(records)

    print(f"raw files parsed : {len(fresh)} listings")
    print(f"merged total     : {len(records)} listings / "
          f"{summary['totals']['unique_projects']} unique projects")
    print(f"weeks            : {summary['totals']['weeks']} "
          f"({trends['weeks'][0]} .. {trends['weeks'][-1]})")
    print(f"tech tags        : {len(trends['series'])}")
    print("top10            : " + ", ".join(
        f"{t['name']}({t['count']})" for t in summary["top_techs"][:10]))

    if args.dry_run:
        return 0

    # 既存の commentary は再ビルドで消さない
    old_summary_path = os.path.join(OUT_DIR, "summary.json")
    if os.path.exists(old_summary_path):
        try:
            with open(old_summary_path, encoding="utf-8") as f:
                summary["commentary"] = json.load(f).get("commentary", "")
        except (OSError, json.JSONDecodeError):
            pass

    # message_id は Gmail のスレッド識別子。公開リポジトリに残す必要がないので落とす。
    with open(PROJECTS_PATH, "w", encoding="utf-8") as f:
        for r in records:
            row = {k: v for k, v in r.items() if k != "message_id"}
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    write_json(STATE_PATH, update_state(seen))
    write_json(os.path.join(OUT_DIR, "cube.json"), build_cube(records))
    write_json(os.path.join(OUT_DIR, "strategy.json"),
               build_strategy(records, trends, first_seen, week_index))
    write_json(os.path.join(OUT_DIR, "trends.json"), trends)
    write_json(old_summary_path, summary)
    write_json(os.path.join(OUT_DIR, "meta.json"), {
        "generated_at": dt.datetime.now(dt.timezone.utc)
            .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "weeks": summary["totals"]["weeks"],
        "listings": summary["totals"]["listings"],
        "unique_projects": summary["totals"]["unique_projects"],
        "latest_week": summary["latest_week"],
    })

    os.makedirs(WEEKS_DIR, exist_ok=True)
    for w, rs in per_week.items():
        write_json(os.path.join(WEEKS_DIR, f"{w}.json"), {
            "week": w,
            "projects": [{
                "id": r["id"],
                "position": r["position"],
                "industry": r["industry"],
                "workstyle": r["workstyle"],
                "ratio_min": r["ratio_min"],
                "ratio_max": r["ratio_max"],
                "rate_min": r["rate_min"],
                "rate_max": r["rate_max"],
                "is_new": first_seen[r["id"]] == w,
                "techs": r["techs"],
            } for r in sorted(rs, key=lambda x: x["id"])],
        })
    print(f"wrote docs/data/ ({len(per_week)} week files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
