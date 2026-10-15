#!/usr/bin/env python3
"""
forensic.py — investigate a (possibly dead) box.

This is tool #4 of the four. You run it when something has gone wrong and you
need to know what actually happened. It is designed for the "pulled the plug"
scenario: the machine is stopped or suspect, and you want a single, read-only
sweep that captures the evidence before you touch anything.

It runs every probe in checks/ and writes a structured report plus raw artifacts
to an output directory. It never modifies the box and never copies secret values
(it records where secrets live, so you can rotate them all).

Usage:
    python forensic.py                      # writes ./forensics-<timestamp>/
    python forensic.py --out /evidence/run1
    python forensic.py --json               # also print a JSON summary
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from checks import ALL_CHECKS  # noqa: E402


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_all(out_dir: str) -> List[Dict[str, Any]]:
    os.makedirs(out_dir, exist_ok=True)
    results: List[Dict[str, Any]] = []
    for check in ALL_CHECKS:
        name = getattr(check, "__name__", "unknown").split(".")[-1]
        try:
            result = check.run(out_dir)
        except Exception as exc:  # a probe must never take down the sweep
            result = {"name": name, "ok": False, "summary": f"probe error: {exc}",
                      "findings": [], "artifacts": []}
        results.append(result)
    return results


def write_report(out_dir: str, results: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    lines.append("MUSE GUARD FORENSICS REPORT")
    lines.append("=" * 60)
    lines.append(f"generated: {_now()}")
    lines.append(f"host: {os.uname().nodename if hasattr(os, 'uname') else 'unknown'}")
    lines.append("")

    # Summary table
    lines.append("SUMMARY")
    lines.append("-" * 60)
    for r in results:
        status = "OK  " if r.get("ok") else "FLAG"
        lines.append(f"[{status}] {r['name']:<12} {r.get('summary', '')}")
    lines.append("")

    # Details
    for r in results:
        lines.append("=" * 60)
        lines.append(f"CHECK: {r['name']}  ({'OK' if r.get('ok') else 'FLAGGED'})")
        lines.append(f"summary: {r.get('summary', '')}")
        findings = r.get("findings", [])
        if findings:
            lines.append("findings:")
            for f in findings:
                lines.append(f"  - {f}")
        else:
            lines.append("findings: (none)")
        artifacts = r.get("artifacts", [])
        if artifacts:
            lines.append("artifacts:")
            for a in artifacts:
                lines.append(f"  - {a}")
        lines.append("")

    report_path = os.path.join(out_dir, "REPORT.txt")
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return report_path


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Muse Guard forensics sweep")
    parser.add_argument("--out", default=None, help="output directory")
    parser.add_argument("--json", action="store_true", help="also print JSON summary")
    args = parser.parse_args(argv)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = args.out or os.path.join(os.getcwd(), f"forensics-{stamp}")

    print(f"Muse Guard forensics — sweeping into {out_dir}")
    results = run_all(out_dir)
    report_path = write_report(out_dir, results)

    flagged = [r for r in results if not r.get("ok")]
    print()
    for r in results:
        mark = "OK  " if r.get("ok") else "FLAG"
        print(f"  [{mark}] {r['name']:<12} {r.get('summary', '')}")
    print()
    print(f"report: {report_path}")

    if args.json:
        print(json.dumps({"out_dir": out_dir, "results": results}, indent=2))

    # Exit non-zero if anything was flagged, so a script can react.
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
