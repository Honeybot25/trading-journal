#!/usr/bin/env python3
"""Env parity checker for trading repo.

Compares required keys in .env.example against locally-set keys and optional
Vercel environment keys (if `vercel` CLI is available and linked).

Usage:
  python3 scripts/env-parity-check.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / ".env.example"
LOCAL = ROOT / ".env"


def parse_env_keys(path: Path) -> set[str]:
    if not path.exists():
        return set()
    keys: set[str] = set()
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)=", line)
        if m:
            keys.add(m.group(1))
    return keys


def vercel_keys() -> set[str]:
    if shutil.which("vercel") is None:
        return set()
    try:
        out = subprocess.check_output(["vercel", "env", "ls"], cwd=ROOT, stderr=subprocess.STDOUT, text=True)
    except Exception:
        return set()

    keys: set[str] = set()
    for line in out.splitlines():
        line = line.strip()
        if not line or line.startswith(">") or line.startswith("Retrieving"):
            continue
        if line.lower().startswith("name"):
            continue
        key = line.split()[0] if line.split() else ""
        if re.match(r"^[A-Z_][A-Z0-9_]*$", key):
            keys.add(key)
    return keys


def main() -> int:
    expected = parse_env_keys(EXAMPLE)
    local = parse_env_keys(LOCAL)
    vercel = vercel_keys()

    print("# Env Parity Report")
    print(f"expected_keys={len(expected)} local_keys={len(local)} vercel_keys={len(vercel)}")

    missing_local = sorted(expected - local)
    missing_vercel = sorted(expected - vercel) if vercel else []

    if missing_local:
        print("\nMissing in .env:")
        for k in missing_local:
            print(f"- {k}")

    if vercel:
        if missing_vercel:
            print("\nMissing in Vercel env:")
            for k in missing_vercel:
                print(f"- {k}")
    else:
        print("\nVercel env check skipped (CLI unavailable, not linked, or access denied).")

    if not missing_local and (not vercel or not missing_vercel):
        print("\nPASS: env parity OK")
        return 0

    print("\nFAIL: env parity gaps detected")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
