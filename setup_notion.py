#!/usr/bin/env python3
"""Add new Notion database properties required by the relaunch.

Run this once after setting up your .env file. It is safe to run repeatedly —
Notion ignores add-property requests for properties that already exist.
"""

import os
import sys
import requests
from dotenv import load_dotenv

load_dotenv()

NOTION_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1"


def main():
    db_id = os.environ["NOTION_DATABASE_ID"]
    token = os.environ["NOTION_API_KEY"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    # Verify the database is accessible first
    r = requests.get(f"{NOTION_BASE}/databases/{db_id}", headers=headers, timeout=15)
    if not r.ok:
        print(f"::error::Error reaching database: {r.status_code} {r.text[:300]}")
        sys.exit(1)

    existing = set(r.json().get("properties", {}).keys())
    print(f"Existing properties: {sorted(existing)}")

    new_props = {
        # New fields for the relaunch
        "Reject Reason": {"rich_text": {}},
        "Edited":        {"checkbox": {}},
        "Score":         {"number": {"format": "number"}},
        "Critic Note":   {"rich_text": {}},
        "Card Options":  {"files": {}},
        "Card Image":    {"files": {}},
        "Post Date":     {"date": {}},
        "Seasons":       {"rich_text": {}},
        "ERA":           {"number": {"format": "number"}},
        "W":             {"number": {"format": "number"}},
        "L":             {"number": {"format": "number"}},
        "SO":            {"number": {"format": "number"}},
        "BB":            {"number": {"format": "number"}},
        # Core fields — add if missing
        "Team":              {"rich_text": {}},
        "Years":             {"rich_text": {}},
        "Stat Note":         {"rich_text": {}},
        "Story":             {"rich_text": {}},
        "Career WAR":        {"number": {"format": "number"}},
        "Best Season Year":  {"number": {"format": "number"}},
        "AVG":               {"number": {"format": "number"}},
        "HR":                {"number": {"format": "number"}},
        "RBI":               {"number": {"format": "number"}},
        "Era": {"select": {"options": [
            {"name": "tobacco",   "color": "brown"},
            {"name": "goudey",    "color": "green"},
            {"name": "bowman",    "color": "gray"},
            {"name": "topps52",   "color": "red"},
            {"name": "topps66",   "color": "orange"},
            {"name": "topps76",   "color": "yellow"},
            {"name": "upperdeck", "color": "blue"},
            {"name": "chrome",    "color": "purple"},
        ]}},
        "Position": {"select": {"options": [
            {"name": pos, "color": "default"}
            for pos in ["1B", "2B", "3B", "SS", "C", "LF", "CF", "RF", "SP", "RP"]
        ]}},
        "Status": {"select": {"options": [
            {"name": "Pending",  "color": "yellow"},
            {"name": "Approved", "color": "green"},
            {"name": "Rejected", "color": "red"},
            {"name": "Posting",  "color": "blue"},
            {"name": "Posted",   "color": "gray"},
        ]}},
    }

    to_add = {k: v for k, v in new_props.items() if k not in existing}
    if not to_add:
        print("All required properties already exist — nothing to add.")
        return

    print(f"Adding: {sorted(to_add.keys())}")
    r = requests.patch(
        f"{NOTION_BASE}/databases/{db_id}",
        headers=headers,
        json={"properties": to_add},
        timeout=15,
    )
    if r.ok:
        print("Done — database properties updated.")
    else:
        print(f"::error::Error: {r.status_code} {r.text[:300]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
