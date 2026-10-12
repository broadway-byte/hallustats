#!/usr/bin/env python3
"""Generate a batch of candidate players and push the top-scored ones to Notion as Pending.

One run: 25 drafts in a single Claude call → critic scores → top 8 go to Notion.
The approved/rejected roster from Notion is included as few-shot examples so the
model knows your taste rather than relying on abstract rules.
"""

import json
import logging
import os
import random
import re
from pathlib import Path

import anthropic
from dotenv import load_dotenv

from config import (
    BATCH_CANDIDATES,
    CLAUDE_CRITIC_MODEL,
    CLAUDE_DRAFT_MODEL,
    COMEDIC_ANGLES,
    ERA_STYLES,
    LAHMAN_NAMES_FILE,
    POSITIONS,
    TOP_N_TO_NOTION,
    VOICE_RULES,
    MAX_POST_CHARS,
    POST_TEMPLATE,
    MAX_STORY_CHARS,
    MAX_STAT_NOTE_CHARS,
)
from notion_client import NotionClient
from teams import TEAM_NAMES, TEAM_BY_NAME

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ── Lahman name check ─────────────────────────────────────────────────────────

def load_lahman_names() -> set:
    p = Path(LAHMAN_NAMES_FILE)
    if not p.exists():
        log.warning(
            "lahman_names.json not found — run setup_lahman.py to enable real-player name filtering"
        )
        return set()
    with open(p) as f:
        return set(json.load(f))


def name_matches_real_player(name: str, lahman_names: set) -> bool:
    if not lahman_names:
        return False
    # Strip nickname (quoted portion) before checking
    clean = re.sub(r"['\"].*?['\"]", "", name).strip().lower()
    parts = clean.split()
    if len(parts) >= 2:
        return f"{parts[0]} {parts[-1]}" in lahman_names
    return False


# ── Slot assignment ───────────────────────────────────────────────────────────

def assign_slots(n: int) -> list:
    """Build n slots using era weights, then shuffle for variety within the batch.

    Each era's 'weight' field controls how many of the n slots it gets.
    Weights must sum to n (BATCH_CANDIDATES). Leftover slots go to the
    highest-weight era if there's any rounding gap.
    """
    total_weight = sum(s["weight"] for s in ERA_STYLES.values())
    slots = []
    for era_name, style in ERA_STYLES.items():
        count = round(n * style["weight"] / total_weight)
        for _ in range(count):
            slots.append({
                "era": era_name,
                "year_range": f"{style['years'][0]}–{style['years'][1]}",
                "position": random.choice(POSITIONS),
                "angle": random.choice(COMEDIC_ANGLES),
            })

    # Trim or pad to exactly n
    while len(slots) > n:
        slots.pop()
    while len(slots) < n:
        heaviest = max(ERA_STYLES, key=lambda e: ERA_STYLES[e]["weight"])
        style = ERA_STYLES[heaviest]
        slots.append({
            "era": heaviest,
            "year_range": f"{style['years'][0]}–{style['years'][1]}",
            "position": random.choice(POSITIONS),
            "angle": random.choice(COMEDIC_ANGLES),
        })

    random.shuffle(slots)
    return slots


# ── Prompt construction ───────────────────────────────────────────────────────

def build_prompts(roster: list, existing_names: set, slots: list) -> tuple[str, str]:
    approved = [p for p in roster if p["status"] in ("Approved", "Posted")]
    rejected = [p for p in roster if p["status"] == "Rejected"]

    approved_block = ""
    for p in approved[:20]:
        avg_str = f".{int(p['avg'] * 1000):03d}" if p.get("avg") and p["avg"] < 1 else str(p.get("avg", ""))
        approved_block += (
            f"- {p['name']} | {p['position']}, {p['team']} · {p['years']} "
            f"| WAR {p.get('career_war', '?')} | stat: {p.get('stat_note', '')} "
            f"| story: \"{p.get('story', '')}\"\n"
        )

    rejected_block = ""
    for p in rejected[:10]:
        reason = f" ({p['reject_reason']})" if p.get("reject_reason") else ""
        rejected_block += f"- {p['name']}{reason}\n"

    name_list = ", ".join(sorted(existing_names)[:120]) or "none yet"

    slots_text = ""
    for i, s in enumerate(slots, 1):
        slots_text += (
            f"{i:>2}. Era: {s['era']} ({s['year_range']})  "
            f"Position: {s['position']}  Angle: {s['angle']}\n"
        )

    team_list = "\n".join(
        f"- {TEAM_BY_NAME[n]['name']} ({TEAM_BY_NAME[n]['years'][0]}–{TEAM_BY_NAME[n]['years'][1]}, {TEAM_BY_NAME[n]['region']}): {TEAM_BY_NAME[n]['note']}"
        for n in TEAM_NAMES
    )

    system = VOICE_RULES

    user = f"""Generate {BATCH_CANDIDATES} fictional baseball player entries. Each entry must follow its assigned slot below.

APPROVED PLAYERS — match this quality and voice exactly:
{approved_block.strip() or "No approved players yet. Establish the voice from the rules above."}

REJECTED — do not resemble these:
{rejected_block.strip() or "None."}

EXISTING NAMES — none of these may appear in any form:
{name_list}

CANONICAL TEAMS — use only teams from this list. A player's year_start and year_end must fall within the team's operating years shown in parentheses. Distributing across regions is good.
{team_list}

SLOT ASSIGNMENTS (era / position / angle are assigned; do not deviate):
{slots_text}
Rules for stats:
- career_war: -5.0 to +2.5
- avg: batting average 0.158–0.291 (pitchers: ERA 3.20–6.80, use avg field for ERA value)
- hr: 0–22 career home runs (pitchers: season wins, 5–18)
- rbi: season RBI (pitchers: season losses, 3–14)
- stat_note: max {MAX_STAT_NOTE_CHARS} characters — one specific, deadpan career fact
- story: max {MAX_STORY_CHARS} characters — the deadpan biography closing line

Use the submit_players tool to return all {BATCH_CANDIDATES} players."""

    return system, user


# ── Tool schemas ──────────────────────────────────────────────────────────────

DRAFT_TOOL = {
    "name": "submit_players",
    "description": "Submit the complete batch of drafted players.",
    "input_schema": {
        "type": "object",
        "properties": {
            "players": {
                "type": "array",
                "minItems": BATCH_CANDIDATES,
                "items": {
                    "type": "object",
                    "properties": {
                        "name":             {"type": "string"},
                        "position":         {"type": "string"},
                        "team":             {"type": "string"},
                        "year_start":       {"type": "integer"},
                        "year_end":         {"type": "integer"},
                        "era":              {"type": "string"},
                        "career_war":       {"type": "number"},
                        "best_season_year": {"type": "integer"},
                        "avg":              {"type": "number"},
                        "hr":               {"type": "integer"},
                        "rbi":              {"type": "integer"},
                        "stat_note":        {"type": "string"},
                        "story":            {"type": "string"},
                    },
                    "required": [
                        "name", "position", "team", "year_start", "year_end",
                        "era", "career_war", "best_season_year", "avg", "hr",
                        "rbi", "stat_note", "story",
                    ],
                },
            }
        },
        "required": ["players"],
    },
}

CRITIC_TOOL = {
    "name": "submit_scores",
    "description": "Submit critic scores for all player drafts.",
    "input_schema": {
        "type": "object",
        "properties": {
            "scores": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name":  {"type": "string"},
                        "score": {"type": "integer", "minimum": 1, "maximum": 10},
                        "note":  {"type": "string"},
                    },
                    "required": ["name", "score", "note"],
                },
            }
        },
        "required": ["scores"],
    },
}


# ── Generation steps ──────────────────────────────────────────────────────────

def generate_drafts(client: anthropic.Anthropic, system: str, user: str) -> list:
    log.info(f"Drafting {BATCH_CANDIDATES} players with {CLAUDE_DRAFT_MODEL}...")
    response = client.messages.create(
        model=CLAUDE_DRAFT_MODEL,
        max_tokens=8000,
        system=system,
        tools=[DRAFT_TOOL],
        tool_choice={"type": "tool", "name": "submit_players"},
        messages=[{"role": "user", "content": user}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_players":
            return block.input["players"]
    raise ValueError("Draft model did not call submit_players")


def run_critic(client: anthropic.Anthropic, players: list, approved: list) -> list:
    log.info(f"Scoring {len(players)} drafts with {CLAUDE_CRITIC_MODEL}...")

    examples = "\n".join(
        f"- {p['name']}: \"{p.get('story', '')}\"" for p in approved[:10]
    ) or "No approved players yet."

    drafts = ""
    for i, p in enumerate(players, 1):
        drafts += (
            f"{i:>2}. {p['name']} | WAR {p['career_war']} | "
            f"stat: {p['stat_note']!r} | story: {p['story']!r}\n"
        )

    response = client.messages.create(
        model=CLAUDE_CRITIC_MODEL,
        max_tokens=4000,
        tools=[CRITIC_TOOL],
        tool_choice={"type": "tool", "name": "submit_scores"},
        messages=[{"role": "user", "content": f"""Score each draft 1–10. Criteria:
1. Deadpan voice — no winking, no "despite this," no "for reasons unknown"
2. Specificity — real-feeling stats and details carry the humor, not commentary
3. Flat final line — does not escalate, does not resolve, just stops
4. Originality — name, team, angle are distinct from approved roster below
5. Post fit — stat_note + story feel like a complete, satisfying 280-character post

Approved roster (what a 9–10 looks like):
{examples}

Drafts to score:
{drafts}
One honest note per player. Mark anything that announces the joke or winks at the reader.
"""}],
    )

    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_scores":
            score_map = {s["name"]: s for s in block.input["scores"]}
            for p in players:
                s = score_map.get(p["name"], {})
                p["score"] = s.get("score", 5)
                p["critic_note"] = s.get("note", "")
            return players

    # If tool call missing, return with default scores
    log.warning("Critic did not call submit_scores — using default scores")
    for p in players:
        p.setdefault("score", 5)
        p.setdefault("critic_note", "")
    return players


# ── Post text builder (for length validation) ─────────────────────────────────

def format_post(p: dict) -> str:
    avg_raw = p.get("avg", 0) or 0
    avg_str = f".{int(avg_raw * 1000):03d}" if avg_raw < 1 else f"{avg_raw:.2f}"
    return POST_TEMPLATE.format(
        name=p["name"],
        position=p["position"],
        team=p["team"],
        years=f"{p['year_start']}–{p['year_end']}",
        war=p["career_war"],
        season=p["best_season_year"],
        avg=avg_str,
        hr=p["hr"],
        rbi=p["rbi"],
        stat_note=p["stat_note"],
        story=p["story"],
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    notion = NotionClient()
    lahman_names = load_lahman_names()

    log.info("Fetching roster from Notion...")
    roster = notion.get_roster()
    existing_names = notion.get_all_existing_names()
    log.info(f"{len(roster)} roster players, {len(existing_names)} existing names")

    approved = [p for p in roster if p["status"] in ("Approved", "Posted")]
    slots = assign_slots(BATCH_CANDIDATES)
    system, user = build_prompts(roster, existing_names, slots)

    all_drafts = generate_drafts(client, system, user)
    log.info(f"Received {len(all_drafts)} drafts")

    # Safety checks (audit fixes #7, #8)
    valid = []
    for p in all_drafts:
        try:
            post_text = format_post(p)
        except (KeyError, TypeError) as e:
            log.warning(f"Skipping malformed draft '{p.get('name', '?')}': {e}")
            continue

        if len(post_text) > MAX_POST_CHARS:
            log.warning(f"Skipping '{p['name']}': post too long ({len(post_text)} chars)")
            continue

        if p["name"].lower() in existing_names:
            log.warning(f"Skipping '{p['name']}': name already in Notion")
            continue

        if name_matches_real_player(p["name"], lahman_names):
            log.warning(f"Skipping '{p['name']}': matches real player in Lahman DB")
            continue

        valid.append(p)

    log.info(f"{len(valid)} valid drafts after safety checks")

    scored = run_critic(client, valid, approved)
    scored.sort(key=lambda p: p.get("score", 0), reverse=True)
    top = scored[:TOP_N_TO_NOTION]

    log.info(f"Pushing top {len(top)} to Notion...")
    for p in top:
        try:
            page_id = notion.push_candidate({
                "name":             p["name"],
                "position":         p["position"],
                "team":             p["team"],
                "years":            f"{p['year_start']}–{p['year_end']}",
                "era":              p["era"],
                "career_war":       p["career_war"],
                "best_season_year": p["best_season_year"],
                "avg":              p["avg"],
                "hr":               p["hr"],
                "rbi":              p["rbi"],
                "stat_note":        p["stat_note"],
                "story":            p["story"],
                "score":            p.get("score"),
                "critic_note":      p.get("critic_note", ""),
            })
            log.info(f"  ✓ {p['name']}  score={p.get('score', '?')}  {page_id[:8]}…")
        except Exception as e:
            log.error(f"  ✗ {p['name']}: {e}")

    log.info("Batch complete.")


if __name__ == "__main__":
    main()
