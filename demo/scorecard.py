#!/usr/bin/env python3
"""
Release-gate scorecard: turns Robot Framework output.xml (+ optional pytest junit xml,
+ UDS session verdict) into a one-page PNG.

usage: scorecard.py <robot output.xml> <out.png> [--pytest junit.xml] [--uds uds_session.txt]
"""

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib
import matplotlib.ticker

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from robot.api import ExecutionResult

GREEN, RED, GREY, BG, FG = "#2ea043", "#f85149", "#30363d", "#0d1117", "#e6edf3"


def robot_suites(xml_path: Path):
    result = ExecutionResult(str(xml_path))
    rows = []

    def walk(suite):
        if suite.tests:
            st = suite.statistics
            rows.append((suite.name, st.passed, st.failed, st.skipped, suite.elapsedtime / 1000))
        for s in suite.suites:
            walk(s)

    walk(result.suite)
    total = result.suite.statistics
    return rows, (total.passed, total.failed, total.skipped, result.suite.elapsedtime / 1000)


def pytest_counts(junit: Path | None):
    if not junit or not junit.exists():
        return None
    root = ET.parse(junit).getroot()
    ts = root if root.tag == "testsuite" else root.find("testsuite")
    if ts is None:
        return None
    tests = int(ts.get("tests", 0))
    failed = int(ts.get("failures", 0)) + int(ts.get("errors", 0))
    skipped = int(ts.get("skipped", 0))
    return tests - failed - skipped, failed, skipped, float(ts.get("time", 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("output_xml", type=Path)
    ap.add_argument("out_png", type=Path)
    ap.add_argument("--pytest", type=Path)
    ap.add_argument("--uds", type=Path)
    a = ap.parse_args()

    rows, (tp, tf, ts, tdur) = robot_suites(a.output_xml)
    py = pytest_counts(a.pytest)
    if py:
        rows.append(("pytest unit tests", *py))
        tp, tf, ts = tp + py[0], tf + py[1], ts + py[2]
    uds_ok = None
    if a.uds and a.uds.exists():
        uds_ok = "UDS diagnostics check: PASS" in a.uds.read_text()
        rows.append(("UDS DTC read/clear session", int(uds_ok), int(not uds_ok), 0, 0.0))
        tp, tf = tp + int(uds_ok), tf + int(not uds_ok)

    gate = "RELEASE GATE: PASS" if tf == 0 else "RELEASE GATE: BLOCKED"
    gate_color = GREEN if tf == 0 else RED

    fig = plt.figure(figsize=(12, 1.8 + 0.8 * len(rows)), facecolor=BG)
    gs = fig.add_gridspec(2, 1, height_ratios=[1.0, len(rows)], hspace=0.05)

    hdr = fig.add_subplot(gs[0])
    hdr.axis("off")
    hdr.text(0, 0.9, "Virtual HIL Framework — Stage 6 Release Gate", color=FG, fontsize=18,
             fontweight="bold", va="top")
    hdr.text(0, 0.35, f"{tp + tf + ts} checks   {tp} passed   {tf} failed   {ts} skipped   "
             f"Robot wall time {tdur:.1f}s", color=FG, fontsize=12, va="top")
    hdr.text(1.0, 0.25, gate, color="white", fontsize=15, fontweight="bold", ha="right", va="center",
             bbox={"boxstyle": "round,pad=0.5", "facecolor": gate_color, "edgecolor": "none"})

    ax = fig.add_subplot(gs[1])
    ax.set_facecolor(BG)
    names = [r[0] for r in rows]
    y = range(len(rows))[::-1]
    p = [r[1] for r in rows]
    f = [r[2] for r in rows]
    s = [r[3] for r in rows]
    ax.barh(y, p, color=GREEN, height=0.55)
    ax.barh(y, f, left=p, color=RED, height=0.55)
    ax.barh(y, s, left=[pi + fi for pi, fi in zip(p, f, strict=True)], color=GREY, height=0.55)
    for yi, r in zip(y, rows, strict=True):
        total = r[1] + r[2] + r[3]
        txt = f"{r[1]}/{total} passed" + (f"   {r[4]:.1f}s" if r[4] else "")
        ax.text(total + 0.2, yi, txt, color=FG, va="center", fontsize=11)
    ax.set_yticks(list(y))
    ax.set_yticklabels(names, color=FG, fontsize=12)
    ax.set_xlim(0, max(r[1] + r[2] + r[3] for r in rows) * 1.45)
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    ax.tick_params(axis="x", colors=FG)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_xlabel("test cases", color=FG)
    ax.grid(axis="x", color=GREY, alpha=0.4)

    a.out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(a.out_png, dpi=150, bbox_inches="tight", facecolor=BG)
    print(f"{gate}  ({tp} passed / {tf} failed / {ts} skipped) -> {a.out_png}")
    return 0 if tf == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
