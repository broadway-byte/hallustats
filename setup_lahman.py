#!/usr/bin/env python3
"""Download every real major-league player's name to lahman_names.json.

generate_batch.py uses this list to throw out any generated player whose name
matches a real big leaguer. Source: the Chadwick Baseball Bureau register
(the old Lahman People.csv link no longer exists). Only people with
major-league playing time are kept.
"""

import csv
import io
import json
import urllib.request

REGISTER_URL = "https://raw.githubusercontent.com/chadwickbureau/register/master/data/people-{}.csv"
OUTPUT = "lahman_names.json"


def main():
    names = set()
    for part in "0123456789abcdef":
        url = REGISTER_URL.format(part)
        print(f"Downloading {url}")
        with urllib.request.urlopen(url, timeout=60) as resp:
            content = resp.read().decode("utf-8")
        for row in csv.DictReader(io.StringIO(content)):
            if not (row.get("mlb_played_first") or "").strip():
                continue
            first = (row.get("name_first") or "").strip().lower()
            last = (row.get("name_last") or "").strip().lower()
            if first and last:
                names.add(f"{first} {last}")

    if len(names) < 15000:
        raise SystemExit(f"Only {len(names)} names found; the register format may have changed.")

    with open(OUTPUT, "w") as f:
        json.dump(sorted(names), f)
    print(f"Saved {len(names):,} player names to {OUTPUT}")


if __name__ == "__main__":
    main()
