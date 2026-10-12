import json
import os
import re
import logging
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()
log = logging.getLogger(__name__)

NOTION_VERSION = "2022-06-28"
NOTION_BASE = "https://api.notion.com/v1"


class NotionClient:
    def __init__(self):
        self.token = os.environ["NOTION_API_KEY"]
        self.db_id = os.environ["NOTION_DATABASE_ID"]
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    def _get(self, path):
        r = requests.get(f"{NOTION_BASE}{path}", headers=self.headers, timeout=30)
        r.raise_for_status()
        return r.json()

    def _post(self, path, data):
        r = requests.post(f"{NOTION_BASE}{path}", headers=self.headers, json=data, timeout=30)
        r.raise_for_status()
        return r.json()

    def _patch(self, path, data):
        r = requests.patch(f"{NOTION_BASE}{path}", headers=self.headers, json=data, timeout=30)
        r.raise_for_status()
        return r.json()

    def _query_db(self, filter_obj=None, sorts=None):
        """Paginate through all results for a database query."""
        body = {}
        if filter_obj:
            body["filter"] = filter_obj
        if sorts:
            body["sorts"] = sorts

        results = []
        cursor = None
        while True:
            if cursor:
                body["start_cursor"] = cursor
            data = self._post(f"/databases/{self.db_id}/query", body)
            results.extend(data["results"])
            if not data.get("has_more"):
                break
            cursor = data["next_cursor"]
        return results

    # ── property parsers ──────────────────────────────────────────────────────

    @staticmethod
    def _title(props, key):
        items = props.get(key, {}).get("title", [])
        return items[0]["text"]["content"] if items else ""

    @staticmethod
    def _rich_text(props, key):
        # Join every piece: Notion splits text wherever formatting changes
        items = props.get(key, {}).get("rich_text", [])
        return "".join(i.get("plain_text") or i.get("text", {}).get("content", "") for i in items)

    @staticmethod
    def _select(props, key):
        s = props.get(key, {}).get("select")
        return s["name"] if s else ""

    @staticmethod
    def _number(props, key):
        return props.get(key, {}).get("number")

    @staticmethod
    def _checkbox(props, key):
        return props.get(key, {}).get("checkbox", False)

    @staticmethod
    def _date(props, key):
        d = props.get(key, {}).get("date")
        return d["start"] if d else None

    @staticmethod
    def _files(props, key):
        """Return list of URLs, handling both 'file' and 'external' types (audit fix #6)."""
        urls = []
        for f in props.get(key, {}).get("files", []):
            if f.get("type") == "file":
                urls.append(f["file"]["url"])
            elif f.get("type") == "external":
                urls.append(f["external"]["url"])
        return urls

    def _seasons(self, props):
        raw = self._rich_text(props, "Seasons")
        if not raw:
            return []
        try:
            return json.loads(raw)
        except ValueError:
            return []

    def _parse_player(self, page):
        p = page["properties"]
        return {
            "page_id": page["id"],
            "name": self._title(p, "Name"),
            "status": self._select(p, "Status"),
            "position": self._select(p, "Position") or self._rich_text(p, "Position"),
            "team": self._rich_text(p, "Team"),
            "years": self._rich_text(p, "Years"),
            "era": self._select(p, "Era"),
            "career_war": self._number(p, "Career WAR"),
            "best_season_year": self._number(p, "Best Season Year"),
            "avg": self._number(p, "AVG"),
            "hr": self._number(p, "HR"),
            "rbi": self._number(p, "RBI"),
            "earned_run_avg": self._number(p, "ERA"),
            "w": self._number(p, "W"),
            "l": self._number(p, "L"),
            "so": self._number(p, "SO"),
            "bb": self._number(p, "BB"),
            "stat_note": self._rich_text(p, "Stat Note"),
            "story": self._rich_text(p, "Story"),
            "card_image_urls": self._files(p, "Card Image"),
            "post_date": self._date(p, "Post Date"),
            "reject_reason": self._rich_text(p, "Reject Reason"),
            "edited": self._checkbox(p, "Edited"),
            "score": self._number(p, "Score"),
            "critic_note": self._rich_text(p, "Critic Note"),
            "card_option_urls": self._files(p, "Card Options"),
            "seasons": self._seasons(p),
        }

    # ── public query methods ──────────────────────────────────────────────────

    def get_roster(self):
        """All Approved, Posted, and Rejected players — used as few-shot examples."""
        pages = self._query_db(filter_obj={"or": [
            {"property": "Status", "select": {"equals": "Approved"}},
            {"property": "Status", "select": {"equals": "Posted"}},
            {"property": "Status", "select": {"equals": "Rejected"}},
        ]})
        return [self._parse_player(p) for p in pages]

    def get_next_approved(self):
        """Next approved player with a card image, sorted by Post Date then created time.
        Audit fixes: #3 (Card Image filter), #4 (sort order).
        """
        pages = self._query_db(
            filter_obj={"and": [
                {"property": "Status", "select": {"equals": "Approved"}},
                {"property": "Card Image", "files": {"is_not_empty": True}},
            ]},
            sorts=[
                {"property": "Post Date", "direction": "ascending"},
                {"timestamp": "created_time", "direction": "ascending"},
            ],
        )
        if not pages:
            return None
        return self._parse_player(pages[0])

    def get_approved_without_card(self):
        """Approved players that have never had card images generated.

        Skips anyone with Card Options already attached, so a player waiting for you
        to pick a front is not redrawn (and re-billed) every night.
        To redraw a player, clear their Card Options.
        """
        pages = self._query_db(filter_obj={"and": [
            {"property": "Status", "select": {"equals": "Approved"}},
            {"property": "Card Image", "files": {"is_empty": True}},
            {"property": "Card Options", "files": {"is_empty": True}},
        ]})
        return [self._parse_player(p) for p in pages]

    def get_queue_count(self):
        """Count of approved players with card images ready to post."""
        pages = self._query_db(filter_obj={"and": [
            {"property": "Status", "select": {"equals": "Approved"}},
            {"property": "Card Image", "files": {"is_not_empty": True}},
        ]})
        return len(pages)

    def get_all_existing_names(self):
        """All player names regardless of status, for duplicate prevention."""
        pages = self._query_db()
        names = set()
        for page in pages:
            items = page["properties"].get("Name", {}).get("title", [])
            if items:
                names.add(items[0]["text"]["content"].lower())
        return names

    # ── write methods ─────────────────────────────────────────────────────────

    def push_candidate(self, player: dict) -> str:
        """Create a new Notion page for a candidate player. Returns page_id."""
        def rt(val):
            return {"rich_text": [{"text": {"content": str(val or "")}}]}

        props = {
            "Name": {"title": [{"text": {"content": player["name"]}}]},
            "Status": {"select": {"name": "Pending"}},
            "Team": rt(player.get("team", "")),
            "Years": rt(player.get("years", "")),
            "Stat Note": rt(player.get("stat_note", "")),
            "Story": rt(player.get("story", "")),
            "Critic Note": rt(player.get("critic_note", "")),
        }
        # Season lines as compact JSON, split into Notion's 2,000-character text pieces
        if player.get("seasons"):
            blob = json.dumps(player["seasons"], separators=(",", ":"))
            props["Seasons"] = {"rich_text": [
                {"text": {"content": blob[i:i + 1900]}} for i in range(0, len(blob), 1900)
            ]}
        # Optional select fields — omit rather than create bad options
        if player.get("position"):
            props["Position"] = {"select": {"name": player["position"]}}
        if player.get("era"):
            props["Era"] = {"select": {"name": player["era"]}}

        # Numeric fields — omit if None
        for key, notion_key in [
            ("career_war", "Career WAR"),
            ("best_season_year", "Best Season Year"),
            ("avg", "AVG"),
            ("hr", "HR"),
            ("rbi", "RBI"),
            ("earned_run_avg", "ERA"),
            ("w", "W"),
            ("l", "L"),
            ("so", "SO"),
            ("bb", "BB"),
            ("score", "Score"),
        ]:
            if player.get(key) is not None:
                props[notion_key] = {"number": player[key]}

        result = self._post("/pages", {
            "parent": {"database_id": self.db_id},
            "properties": props,
        })
        return result["id"]

    def mark_posting(self, page_id: str):
        """Set status to Posting before tweeting — prevents double-post on crash (audit fix #5)."""
        self._patch(f"/pages/{page_id}", {
            "properties": {"Status": {"select": {"name": "Posting"}}}
        })

    def mark_posted(self, page_id: str):
        """Set status to Posted and record today's date after a successful tweet."""
        self._patch(f"/pages/{page_id}", {
            "properties": {
                "Status": {"select": {"name": "Posted"}},
                "Post Date": {"date": {"start": datetime.now().strftime("%Y-%m-%d")}},
            }
        })

    def mark_failed(self, page_id: str):
        """Revert Posting → Approved so the player stays in the queue."""
        self._patch(f"/pages/{page_id}", {
            "properties": {"Status": {"select": {"name": "Approved"}}}
        })

    def attach_card_options(self, page_id: str, urls: list, back_url: str = None):
        """Write front options (and the back, last) into the Card Options field."""
        files = [
            {"type": "external", "name": f"Option {i + 1}", "external": {"url": url}}
            for i, url in enumerate(urls)
        ]
        if back_url:
            files.append({"type": "external", "name": "Back", "external": {"url": back_url}})
        self._patch(f"/pages/{page_id}", {
            "properties": {"Card Options": {"files": files}}
        })
