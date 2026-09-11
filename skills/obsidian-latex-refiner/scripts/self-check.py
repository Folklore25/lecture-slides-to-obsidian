#!/usr/bin/env python3
"""Smoke-test the bundled math fixtures without touching any vault."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent

CASES = (
    {"name": "legacy-inline", "input": "Solve \\(x^2 = 4\\).", "expected": "Solve $x^2 = 4$."},
    {"name": "legacy-display", "input": "\\[a^2 + b^2 = c^2\\]", "expected": "$$\na^2 + b^2 = c^2\n$$"},
    {"name": "equation-label", "input": "\\begin{equation}\ny = x^2 \\label{eq:one}\n\\end{equation}", "expected": "$$\ny = x^2\n$$"},
    {"name": "align-to-aligned", "input": "\\begin{align}\na &= b \\\\\nc &= d\n\\end{align}", "expected": "$$\n\\begin{aligned}\na &= b \\\\\nc &= d\n\\end{aligned}\n$$"},
    {"name": "redundant-display-shell", "input": "$$\n$$\nE = mc^2\n$$\n$$", "expected": "$$\nE = mc^2\n$$"},
    {"name": "raw-cjk-in-math", "input": "$$能量 E$$", "expected": "$$\n\\text{能量} E\n$$"},
    {"name": "plain-text-unchanged", "input": "No math here.", "expected": "No math here."},
)


def load_normalizer():
    path = SCRIPT_DIR / "normalize-latex.py"
    spec = importlib.util.spec_from_file_location("lecture_latex_normalizer_selfcheck", path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load " + str(path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> int:
    normalizer = load_normalizer()
    failures = 0
    for case in CASES:
        actual, _ = normalizer.normalize_text(case["input"], set(normalizer.TRANSFORM_GROUPS))
        if actual == case["expected"]:
            print("ok   " + case["name"])
            continue
        failures += 1
        print("FAIL " + case["name"])
        print("  expected: " + repr(case["expected"]))
        print("  actual:   " + repr(actual))
    print(f"{len(CASES) - failures}/{len(CASES)} cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
