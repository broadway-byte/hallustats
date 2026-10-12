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

import openai
import requests
from dotenv import load_dotenv
from PIL import Image

from card_art import CARD_H, CARD_W, back_prompt, era_for, front_layout_prompt, stamp_front
from config import CARDS_DIR, ERA_STYLES, OPENAI_IMAGE_MODEL, WORDMARK_STYLES
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
    era = era_for(player)
    style = ERA_STYLES[era]
    year = player.get("year_start", 1925)
    team = player.get("team", "Unknown")
    position = player.get("position", "OF")
    angle = PORTRAIT_ANGLES[option_idx % len(PORTRAIT_ANGLES)]
    uniform = uniform_text(team, era)
    layout_rule = front_layout_prompt(era)
    text_rule = (
        "Apart from the jersey wordmark, do not write any text anywhere on the card. "
        if uniform else "Do not write any text anywhere on the card. "
    )

    return (
        f"Vintage baseball card art. {style['description']} "
        f"The player is a {position} for the {team}, active circa {year}. "
        f"{uniform}"
        f"Pose: {angle}. "
        f"{layout_rule}"
        f"{text_rule}"
        f"The card should show authentic aging: wear, minor creases, and slight fading "
        f"consistent with a card printed in {year}. "
        f"Aspect ratio roughly 3:4 (portrait card)."
    )


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

        log.info(f"Generating {OPTIONS} options for {name} ({era})…")
        saved_paths = []
        raw_urls    = []

        for opt in range(OPTIONS):
            try:
                prompt   = build_image_prompt(player, opt)
                art      = fetch_image(oai, prompt)
                art      = stamp_front(art, player)
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
            log.info(f"  ✓ Back: {back_name}")
            back_url = github_raw_url(back_name)
        except Exception as e:
            log.error(f"  ✗ Back: {e}")

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
