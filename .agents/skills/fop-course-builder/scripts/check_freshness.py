#!/usr/bin/env python3
"""Перевіряє дати актуальності current_rules і lesson.md."""

from __future__ import annotations

import argparse
import re
from datetime import date, datetime, timedelta
from pathlib import Path


DATE_FIELDS = {
    "last_verified": [
        r"(?mi)^last_verified:\s*(\d{4}-\d{2}-\d{2})\s*$",
        r"(?mi)^Дата (?:останньої )?перевірки актуальності:\s*\*{0,2}(\d{4}-\d{2}-\d{2})",
    ],
    "next_review": [
        r"(?mi)^next_review:\s*(\d{4}-\d{2}-\d{2})\s*$",
        r"(?mi)^Наступна перевірка:\s*\*{0,2}(\d{4}-\d{2}-\d{2})",
    ],
}
STATUS_RE = re.compile(r"(?mi)^status:\s*([a-z_]+)\s*$")
BLOCKING_STATUSES = {"changed", "repealed", "stale", "needs_review"}


def field(text: str, name: str) -> date | None:
    for pattern in DATE_FIELDS[name]:
        match = re.search(pattern, text)
        if match:
            return datetime.strptime(match.group(1), "%Y-%m-%d").date()
    return None


def candidates(root: Path) -> list[tuple[Path, int]]:
    found: list[tuple[Path, int]] = []
    rules = root / "current_rules"
    if rules.exists():
        found.extend((p, 30) for p in rules.rglob("*.md") if p.name.lower() != "readme.md")
    curriculum = root / "curriculum"
    if curriculum.exists():
        found.extend((p, 365) for p in curriculum.rglob("lesson.md"))
    return sorted(found)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--as-of", type=lambda value: datetime.strptime(value, "%Y-%m-%d").date(), default=date.today())
    args = parser.parse_args()

    errors: list[str] = []
    checked = candidates(args.project)
    for path, max_age in checked:
        text = path.read_text(encoding="utf-8")
        last = field(text, "last_verified")
        next_date = field(text, "next_review")
        status_match = STATUS_RE.search(text)
        status = status_match.group(1) if status_match else None
        rel = path.relative_to(args.project)

        if last is None:
            errors.append(f"{rel}: немає last_verified")
            continue
        if last > args.as_of:
            errors.append(f"{rel}: last_verified у майбутньому ({last})")
        deadline = next_date or last + timedelta(days=max_age)
        if deadline < args.as_of:
            errors.append(f"{rel}: прострочено перевірку ({deadline})")
        if status in BLOCKING_STATUSES:
            errors.append(f"{rel}: блокуючий status={status}")

    if errors:
        print("FAIL")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"OK: перевірено файлів {len(checked)}; дата контролю {args.as_of}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
