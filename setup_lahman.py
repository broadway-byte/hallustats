#!/usr/bin/env python3
"""Download the Lahman People.csv and extract all real player names to lahman_names.json.

This file is used by generate_batch.py to filter out any generated player whose
stripped name matches a real major-league player. Run once before your first batch.
"""

import csv
import io
import json
import urllib.request

PEOPLE_URL = (
    "https://github.com/chadwickbureau/baseballdatabank/raw/master/core/People.csv"
)
OUTPUT = "lahman_names.json"


def main():
    print("Downloading Lahman People.csv…")
    with urllib.request.urlopen(PEOPLE_URL, timeout=60) as resp:
        content = resp.read().decode("utf-8")

    reader = csv.DictReader(io.StringIO(content))
    names = set()
    for row in reader:
        first = (row.get("nameFirst") or "").strip().lower()
        last  = (row.get("nameLast")  or "").strip().lower()
        if first and last:
            names.add(f"{first} {last}")

    with open(OUTPUT, "w") as f:
        json.dump(sorted(names), f)

    print(f"Saved {len(names):,} player names to {OUTPUT}")


if __name__ == "__main__":
    main()
