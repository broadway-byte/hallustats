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
    format_post,
    MIN_SCORE_TO_NOTION,
    PITCHER_POSITIONS,
    MAX_STORY_CHARS,
    MAX_STAT_NOTE_CHARS,
)
from notion_client import COPY_APPROVED_STATUSES, NotionClient
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
    approved = [p for p in roster if p["status"] in COPY_APPROVED_STATUSES]
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
- best_season_year is the player's best season. Fill the best-season fields for his position only:
  batters (1B 2B 3B SS C LF CF RF): avg 0.158–0.291, hr that season (0–22), rbi that season
  pitchers (SP RP): earned_run_avg 3.20–6.80, w and l (SP 5–18 wins, RP 1–9), so (strikeouts), bb (walks)
  Leave the other position's fields out.
- seasons: one line for EVERY season from year_start to year_end, all with this one team.
  batters: year, g, ab, r, h, doubles, triples, hr, rbi (h/ab is the average)
  pitchers: year, g, ip, w, l, so, bb, era
  The best season's line must match the best-season fields exactly (for batters, h/ab rounds to avg).
  Seasons should look like a real minor-league career: partial first and last years, an off year, an injury year if the story mentions one.
- Every number in stat_note and story must agree with the season lines.

Rules for the card artist (not part of the post, no length pressure beyond the limits below):
- look (max 200 characters): the player's fixed appearance, so every image shows the same man.
  Age, build, face, hair, facial hair, complexion, and one distinguishing feature. Period-plausible.
- pose (max 150 characters): body language and expression for the card portrait that quietly acts out
  the story (example: "standing rigidly upright, chin lifted, holding a glove he clearly dislikes touching").

Rules for copy (posts are capped at 280 characters; any entry over is thrown away):
- stat_note + story TOGETHER must be 140 characters or fewer. Count them.
- Example at the right length (126 characters total):
  stat_note: "Grounded into 34 double plays in 1936." (38)
  story: "The Waukegan News-Sun called his swing purposeful. He was traded in May for a used tarp." (88)
- stat_note: max {MAX_STAT_NOTE_CHARS} characters, one specific deadpan career fact
- story: max {MAX_STORY_CHARS} characters, the deadpan closing line, built on one concrete detail
- Avoid the "nobody noticed him" shape and do not repeat a joke shape within the batch

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
                        "earned_run_avg":   {"type": "number"},
                        "w":                {"type": "integer"},
                        "l":                {"type": "integer"},
                        "so":               {"type": "integer"},
                        "bb":               {"type": "integer"},
                        "seasons": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "year": {"type": "integer"}, "g": {"type": "integer"},
                                    "ab": {"type": "integer"}, "r": {"type": "integer"},
                                    "h": {"type": "integer"}, "doubles": {"type": "integer"},
                                    "triples": {"type": "integer"}, "hr": {"type": "integer"},
                                    "rbi": {"type": "integer"},
                                    "ip": {"type": "integer"}, "w": {"type": "integer"},
                                    "l": {"type": "integer"}, "so": {"type": "integer"},
                                    "bb": {"type": "integer"}, "era": {"type": "number"},
                                },
                                "required": ["year", "g"],
                            },
                        },
                        "look":             {"type": "string"},
                        "pose":             {"type": "string"},
                        "stat_note":        {"type": "string"},
                        "story":            {"type": "string"},
                    },
                    "required": [
                        "name", "position", "team", "year_start", "year_end",
                        "era", "career_war", "best_season_year",
                        "seasons", "look", "pose", "stat_note", "story",
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
        max_tokens=20000,
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
6. Concrete detail — the story turns on one checkable detail (date, count, named object or place). Vague stories score 5 or lower.
7. Freshness — the "nobody noticed him / never interviewed / no public statements" shape scores 4 or lower. Two drafts with the same joke shape: score the weaker one 4 or lower.
8. The story must add something; if it restates the stat_note, score 5 or lower.

Be strict. A 9–10 should be rare. Most drafts land 5–7.

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


# ── Season lines ──────────────────────────────────────────────────────────────

def repair_seasons(p: dict) -> bool:
    """Check the writer's season lines; make the best season match the headline stats.

    Returns False if the lines are unusable (missing, or no best season).
    The headline (avg/hr/rbi) is what the post shows, so it wins any disagreement.
    """
    seasons = p.get("seasons") or []
    lo, hi = p.get("year_start"), p.get("year_end")
    seasons = [x for x in seasons if isinstance(x, dict) and isinstance(x.get("year"), int)
               and lo <= x["year"] <= hi]
    seen = set()
    seasons = [x for x in sorted(seasons, key=lambda x: x["year"])
               if not (x["year"] in seen or seen.add(x["year"]))]
    best = next((x for x in seasons if x["year"] == p.get("best_season_year")), None)
    if not seasons or best is None:
        return False
    if p.get("position") in PITCHER_POSITIONS:
        if p.get("earned_run_avg") is None or p.get("w") is None or p.get("l") is None:
            return False
        best["era"], best["w"], best["l"] = round(float(p["earned_run_avg"]), 2), int(p["w"]), int(p["l"])
        if p.get("so") is not None:
            best["so"] = int(p["so"])
        if p.get("bb") is not None:
            best["bb"] = int(p["bb"])
        for k in ("avg", "hr", "rbi"):
            p.pop(k, None)
        for x in seasons:
            for k in ("ip", "w", "l", "so", "bb"):
                x[k] = max(0, int(x.get(k) or 0))
            x["era"] = round(float(x.get("era") or 0), 2)
    else:
        if p.get("avg") is None or p.get("hr") is None or p.get("rbi") is None:
            return False
        for k in ("earned_run_avg", "w", "l", "so", "bb"):
            p.pop(k, None)
        for x in seasons:
            for k in ("ab", "r", "h", "doubles", "triples", "hr", "rbi"):
                x[k] = max(0, int(x.get(k) or 0))
            x["h"] = min(x["h"], x["ab"])
        if best["ab"] <= 0:
            best["ab"] = 400
        best["h"] = round(float(p["avg"]) * best["ab"])
        best["hr"], best["rbi"] = int(p["hr"]), int(p["rbi"])
    p["seasons"] = seasons
    return True


# ── Tightening pass ───────────────────────────────────────────────────────────

SHORTEN_TOOL = {
    "name": "submit_shortened",
    "description": "Submit the shortened copy for each player.",
    "input_schema": {
        "type": "object",
        "properties": {
            "players": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id":        {"type": "integer"},
                        "stat_note": {"type": "string"},
                        "story":     {"type": "string"},
                    },
                    "required": ["id", "stat_note", "story"],
                },
            }
        },
        "required": ["players"],
    },
}


def copy_budget(p: dict) -> int:
    """Characters left for stat_note + story once the rest of the post is laid out."""
    return MAX_POST_CHARS - len(format_post(dict(p, stat_note="", story="")))


def shorten_drafts(client: anthropic.Anthropic, drafts: list) -> None:
    """Send over-length drafts back to the writer with an exact budget; edits in place."""
    if not drafts:
        return
    lines = ""
    for i, p in enumerate(drafts):
        budget = copy_budget(p)
        now = len(p["stat_note"]) + len(p["story"])
        lines += (f"id {i} | {p['name']} | currently {now} chars, must be {budget} or fewer "
                  f"(stat_note at most {min(MAX_STAT_NOTE_CHARS, budget // 3)}) | "
                  f"stat_note: {p['stat_note']!r} | story: {p['story']!r}\n")
    response = client.messages.create(
        model=CLAUDE_DRAFT_MODEL,
        max_tokens=6000,
        system=VOICE_RULES,
        tools=[SHORTEN_TOOL],
        tool_choice={"type": "tool", "name": "submit_shortened"},
        messages=[{"role": "user", "content": f"""These entries are too long for a 280-character post.
Rewrite each stat_note and story so their combined length is at or under the budget shown.
Count characters, spaces included. Return every id.
Keep the same joke, the same concrete detail and every number exactly as it is. Cut words, not facts.
The story must still end flat.

{lines}"""}],
    )
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_shortened":
            for x in block.input["players"]:
                i = x.get("id")
                if isinstance(i, int) and 0 <= i < len(drafts):
                    drafts[i]["stat_note"] = x["stat_note"].strip()
                    drafts[i]["story"] = x["story"].strip()
            return
    log.warning("Shortening pass returned nothing")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    notion = NotionClient()
    lahman_names = load_lahman_names()

    log.info("Fetching roster from Notion...")
    roster = notion.get_roster()
    existing_names = notion.get_all_existing_names()
    log.info(f"{len(roster)} roster players, {len(existing_names)} existing names")

    approved = [p for p in roster if p["status"] in COPY_APPROVED_STATUSES]
    slots = assign_slots(BATCH_CANDIDATES)
    system, user = build_prompts(roster, existing_names, slots)

    all_drafts = generate_drafts(client, system, user)
    log.info(f"Received {len(all_drafts)} drafts")

    # Safety checks (audit fixes #7, #8)
    valid = []
    over, too_long = [], []
    skipped = {"malformed": 0, "too_long": 0, "bad_seasons": 0, "name_in_notion": 0, "real_player": 0}
    for p in all_drafts:
        if not repair_seasons(p):
            log.warning(f"Skipping '{p['name']}': season lines or best-season stats missing")
            skipped["bad_seasons"] += 1
            continue

        try:
            post_text = format_post(p)
        except (KeyError, TypeError) as e:
            log.warning(f"Skipping malformed draft '{p.get('name', '?')}': {e}")
            skipped["malformed"] += 1
            continue

        if len(post_text) > MAX_POST_CHARS:
            over.append(len(post_text) - MAX_POST_CHARS)
            too_long.append(p)
            continue

        if p["name"].lower() in existing_names:
            log.warning(f"Skipping '{p['name']}': name already in Notion")
            skipped["name_in_notion"] += 1
            continue

        if name_matches_real_player(p["name"], lahman_names):
            log.warning(f"Skipping '{p['name']}': matches real player in Lahman DB")
            skipped["real_player"] += 1
            continue

        valid.append(p)

    # Second chance for over-length drafts: one tightening call, then re-measure
    if too_long:
        log.info(f"Tightening {len(too_long)} over-length drafts...")
        for attempt in range(2):
            still = [p for p in too_long if len(format_post(p)) > MAX_POST_CHARS]
            if not still:
                break
            try:
                shorten_drafts(client, still)
            except Exception as e:
                print(f"::warning::Shortening pass {attempt + 1} failed: {str(e)[:300]}")
        for p in too_long:
            n = len(format_post(p))
            if n > MAX_POST_CHARS:
                log.warning(f"Skipping '{p['name']}': still too long after tightening ({n} chars)")
                skipped["too_long"] += 1
            elif p["name"].lower() in existing_names or name_matches_real_player(p["name"], lahman_names):
                skipped["name_in_notion"] += 1
            else:
                valid.append(p)
    if over:
        print(f"::notice::{len(over)} drafts were over 280 on the first pass, "
              f"by {min(over)}-{max(over)} chars (median {sorted(over)[len(over) // 2]})")

    log.info(f"{len(valid)} valid drafts after safety checks")

    scored = run_critic(client, valid, approved)
    scored.sort(key=lambda p: p.get("score", 0), reverse=True)
    top = [p for p in scored if p.get("score", 0) >= MIN_SCORE_TO_NOTION][:TOP_N_TO_NOTION]

    log.info(f"Pushing top {len(top)} to Notion...")
    pushed, push_errors = 0, []
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
                "avg":              p.get("avg"),
                "hr":               p.get("hr"),
                "rbi":              p.get("rbi"),
                "earned_run_avg":   p.get("earned_run_avg"),
                "w":                p.get("w"),
                "l":                p.get("l"),
                "so":               p.get("so"),
                "bb":               p.get("bb"),
                "stat_note":        p["stat_note"],
                "story":            p["story"],
                "seasons":          p["seasons"],
                "look":             p.get("look", ""),
                "pose":             p.get("pose", ""),
                "score":            p.get("score"),
                "critic_note":      p.get("critic_note", ""),
            })
            log.info(f"  ✓ {p['name']}  score={p.get('score', '?')}  {page_id[:8]}…")
            pushed += 1
        except Exception as e:
            log.error(f"  ✗ {p['name']}: {e}")
            push_errors.append(f"{p['name']}: {str(e)[:150]}")

    # One-line summary, shown on the workflow run page
    print(f"::notice::drafts={len(all_drafts)} skipped={skipped} valid={len(valid)} "
          f"scored={len(scored)} pushed={pushed}")
    for err in push_errors[:3]:
        print(f"::warning::Notion push failed: {err}")

    log.info("Batch complete.")


if __name__ == "__main__":
    main()
