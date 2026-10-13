#!/usr/bin/env python3
"""Generate three front options and one back per approved player, save them to cards/,
and attach the raw GitHub URLs to the player's Card Options field in Notion.

Workflow:
  1. Fetch players marked Copy Approved (or Redraw Cards) in Notion.
  2. For each player, call gpt-image-2 three times (portrait in the team's uniform, era card art).
  3. Print the era's front caption into the card in code (card_art.py).
  4. Generate the back as an image from exact text: period-correct layout, Hallu branding,
     stats, cartoon (1953-82) and back photo (1971, 1989 on).
  5. Save to cards/<slug>_<era>_opt<n>.png and cards/<slug>_<era>_back.png.
  5. Write the GitHub raw URLs to Notion Card Options.

After this runs, go to Notion and drag your preferred option into Card Image.
The posting bot reads Card Image, not Card Options.
"""

import base64
import io
import json
import logging
import os
import re
import time
from pathlib import Path

import anthropic
import openai
import subprocess
import requests
from dotenv import load_dotenv
from PIL import Image

from card_art import CARD_H, CARD_W, back_prompt, era_for, front_prompt
from config import CARDS_DIR, CLAUDE_DRAFT_MODEL, ERA_STYLES, OPENAI_IMAGE_MODEL, WORDMARK_STYLES
from teams import TEAM_BY_NAME
from notion_client import NotionClient

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

OPTIONS = 3            # card options per player
IMAGE_SIZE = "1024x1536"

PORTRAIT_ANGLES = [
    "three-quarter view facing slightly left",
    "three-quarter view facing slightly right",
    "direct frontal portrait",
]


def uniform_text(team: str, era: str) -> str:
    """Fixed team kit, lettered in the era's style. Empty if the team is unknown."""
    t = TEAM_BY_NAME.get(team)
    if not t:
        return ""
    k = t["kit"]
    lettering = WORDMARK_STYLES.get(era, "simple lettering")
    return (
        f"Uniform: {k['colors'][0]} and {k['colors'][1]}, with {k['detail']}. "
        f"The cap shows a simple emblem of {k['cap']}, with no letters. "
        f'The jersey chest reads "{k["chest"]}" in {lettering}; spell it exactly. '
    )


def build_image_prompt(player: dict, option_idx: int) -> str:
    return front_prompt(player, option_idx, uniform=uniform_text(player.get("team", ""), era_for(player)))


# ── Player look (for players written before the writer produced one) ─────────

LOOK_TOOL = {
    "name": "submit_look",
    "description": "Describe the player's fixed appearance and card pose.",
    "input_schema": {
        "type": "object",
        "properties": {
            "look": {"type": "string"},
            "pose": {"type": "string"},
        },
        "required": ["look", "pose"],
    },
}


def ensure_look(claude, notion, player: dict) -> None:
    """Write a Look and Pose for players that lack one, and save them to Notion."""
    if player.get("look") and player.get("pose"):
        return
    if claude is None:
        return
    msg = claude.messages.create(
        model=CLAUDE_DRAFT_MODEL,
        max_tokens=600,
        tools=[LOOK_TOOL],
        tool_choice={"type": "tool", "name": "submit_look"},
        messages=[{"role": "user", "content": f"""Describe this fictional ballplayer for a card illustrator.

{player.get('name')} | {player.get('position')}, {player.get('team')} | {player.get('years')}
Stat note: {player.get('stat_note')}
Story: {player.get('story')}

look (max 200 characters): his fixed appearance so every image shows the same man. Age, build, face,
hair, facial hair, complexion, and one distinguishing feature. Period-plausible.
pose (max 150 characters): body language and expression for the card portrait that quietly acts out
the story, deadpan, no props that contradict it."""}],
    )
    for block in msg.content:
        if block.type == "tool_use":
            player["look"] = block.input["look"].strip()
            player["pose"] = block.input["pose"].strip()
            try:
                notion.save_look(player["page_id"], player["look"], player["pose"])
            except Exception as e:
                log.warning(f"  Could not save look to Notion: {e}")


# ── Publishing ────────────────────────────────────────────────────────────────

def publish(paths: list, name: str) -> bool:
    """In GitHub Actions, commit and push this player's images right away so links work."""
    if not os.getenv("GITHUB_ACTIONS"):
        return True
    git = ["git", "-c", "user.name=HalluStats Bot", "-c", "user.email=bot@hallustats.invalid"]
    try:
        subprocess.run(git + ["add", *paths], check=True)
        subprocess.run(git + ["commit", "-q", "-m", f"Cards: {name}"], check=True)
        for _ in range(3):
            subprocess.run(git + ["pull", "-q", "--rebase"], check=False)
            if subprocess.run(git + ["push", "-q"], check=False).returncode == 0:
                return True
            time.sleep(3)
    except subprocess.CalledProcessError as e:
        log.error(f"  git failed: {e}")
    return False


def fetch_image(client: openai.OpenAI, prompt: str, size: str = None) -> Image.Image:
    response = client.images.generate(
        model=OPENAI_IMAGE_MODEL,
        prompt=prompt,
        size=size or IMAGE_SIZE,
        quality="high",
        n=1,
    )
    item = response.data[0]
    if getattr(item, "b64_json", None):          # gpt-image models return base64
        img_bytes = base64.b64decode(item.b64_json)
    elif getattr(item, "url", None):
        img_bytes = requests.get(item.url, timeout=60).content
    else:
        raise RuntimeError("Image API returned neither b64_json nor url")
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    return img if size else img.resize((CARD_W, CARD_H), Image.LANCZOS)


# ── File helpers ──────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def github_raw_url(filename: str) -> str | None:
    repo   = os.getenv("GITHUB_REPO", "").strip()
    branch = os.getenv("GITHUB_BRANCH", "main").strip()
    if not repo:
        return None
    return f"https://raw.githubusercontent.com/{repo}/{branch}/cards/{filename}"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    oai    = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    claude = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"]) if os.getenv("ANTHROPIC_API_KEY") else None
    notion = NotionClient()
    Path(CARDS_DIR).mkdir(exist_ok=True)

    players = notion.get_players_needing_cards()
    log.info(f"{len(players)} players need cards (Copy Approved or Redraw Cards)")

    for player in players:
        name = player["name"]
        era  = era_for(player)

        # Parse year_start / year_end from the Years field if not already present
        if not player.get("year_start"):
            years_str = player.get("years", "1920-1930")
            parts = re.split(r"[–\-]", years_str)
            try:
                player["year_start"] = int(parts[0].strip())
                player["year_end"]   = int(parts[-1].strip()) if len(parts) > 1 else player["year_start"] + 5
            except ValueError:
                player["year_start"] = 1920
                player["year_end"]   = 1930

        try:
            ensure_look(claude, notion, player)
        except Exception as e:
            log.warning(f"  Look not written: {e}")

        log.info(f"Generating {OPTIONS} options for {name} ({era})…")
        saved_paths = []
        raw_urls    = []

        for opt in range(OPTIONS):
            try:
                prompt   = build_image_prompt(player, opt)
                art      = fetch_image(oai, prompt)
                filename = f"{slugify(name)}_{era}_opt{opt + 1}.png"
                filepath = Path(CARDS_DIR) / filename
                art.save(filepath, "PNG")
                saved_paths.append(str(filepath))

                url = github_raw_url(filename)
                if url:
                    raw_urls.append(url)

                log.info(f"  ✓ Option {opt + 1}: {filename}")
                time.sleep(1)  # brief pause between API calls
            except Exception as e:
                log.error(f"  ✗ Option {opt + 1}: {e}")

        # One back per player, drawn by the image model from exact text
        back_url = None
        try:
            back = fetch_image(oai, back_prompt(player))
            back_name = f"{slugify(name)}_{era}_back.png"
            back.save(Path(CARDS_DIR) / back_name, "PNG")
            saved_paths.append(str(Path(CARDS_DIR) / back_name))
            log.info(f"  ✓ Back: {back_name}")
            back_url = github_raw_url(back_name)
        except Exception as e:
            log.error(f"  ✗ Back: {e}")

        # Put this player's images on GitHub before Notion points at them
        if raw_urls and not publish(saved_paths, name):
            log.error(f"  Images for {name} not pushed; leaving status unchanged")
            continue

        if raw_urls:
            try:
                notion.attach_card_options(player["page_id"], raw_urls, back_url=back_url)
                notion.set_status(player["page_id"], "Cards Ready")   # now waiting on your art review
                log.info(f"  Attached {len(raw_urls)} Card Options to Notion page")
            except Exception as e:
                log.error(f"  Failed to attach Card Options: {e}")
        elif saved_paths:
            log.info(
                f"  Cards saved locally but GITHUB_REPO not set — "
                "set it in .env and re-run after pushing to attach Notion URLs"
            )

    log.info("Card generation complete.")


if __name__ == "__main__":
    main()
