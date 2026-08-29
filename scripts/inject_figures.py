#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""design_figures.py の出力を design/*.dc.html に流し込む。

各アートボードには
    const D = /*FIGURES*/ {...} /*/FIGURES*/;
というブロックがあり、その中身を実データで置き換える。
数値を手で書き写さないための仕組み（書き写しはデータとの食い違いを生む）。
"""
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = ["design/Main.dc.html", "design/Weekly.dc.html", "design/Mobile.dc.html"]
BLOCK = re.compile(r"(/\*FIGURES\*/)(.*?)(/\*/FIGURES\*/)", re.DOTALL)


def main():
    out = subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", "design_figures.py")],
        capture_output=True, text=True, check=True)
    figures = json.loads(out.stdout)
    payload = json.dumps(figures, ensure_ascii=False, separators=(",", ":"))
    if "</script" in payload:
        raise SystemExit("figures にスクリプト終了タグが含まれる。中断する。")

    touched = 0
    for rel in TARGETS:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        src = io.open(path, encoding="utf-8").read()
        if not BLOCK.search(src):
            print(f"skip (マーカーなし): {rel}", file=sys.stderr)
            continue
        io.open(path, "w", encoding="utf-8").write(
            BLOCK.sub(lambda m: m.group(1) + payload + m.group(3), src, count=1))
        touched += 1
        print(f"updated {rel}")
    print(f"{touched} files / {len(payload)} bytes / "
          f"{figures['totals']['weeks']}週 {figures['totals']['listings']}件")


if __name__ == "__main__":
    main()
