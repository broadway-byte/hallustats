#!/usr/bin/env python3
"""Post the next approved player to X (@HalluStats).

Usage:
  python bot.py              # post and mark as Posted in Notion
  python bot.py --dry-run    # print post text and char count, do not post
  python bot.py --check-queue # print queue depth and exit
"""

import argparse
import logging
import os
import sys
import tempfile
from pathlib import Path

import requests
import tweepy
from dotenv import load_dotenv

from config import LOW_QUEUE_THRESHOLD, MAX_POST_CHARS, POST_TEMPLATE
from notion_client import NotionClient

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


# ── Post text ────────────────────────────────────────────────────────────────

def format_post(player: dict) -> str:
    avg_raw = player.get("avg") or 0
    avg_str = f".{int(avg_raw * 1000):03d}" if avg_raw < 1 else f"{avg_raw:.2f}"
    return POST_TEMPLATE.format(
        name=player["name"],
        position=player["position"],
        team=player["team"],
        years=player.get("years", ""),
        war=player.get("career_war", "—"),
        season=player.get("best_season_year", ""),
        avg=avg_str,
        hr=player.get("hr", 0),
        rbi=player.get("rbi", 0),
        stat_note=player.get("stat_note", ""),
        story=player.get("story", ""),
    )


# ── X / Twitter client ───────────────────────────────────────────────────────

def get_v2_client() -> tweepy.Client:
    return tweepy.Client(
        consumer_key=os.environ["TWITTER_API_KEY"],
        consumer_secret=os.environ["TWITTER_API_SECRET"],
        access_token=os.environ["TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
    )


def upload_media(image_path: str) -> str | None:
    """Upload image and return media_id string.
    Tries v2 endpoint first (requires TWITTER_OAUTH2_TOKEN with media.write scope),
    then falls back to v1.1 (deprecated but may still work).
    """
    oauth2_token = os.getenv("TWITTER_OAUTH2_TOKEN", "").strip()
    if oauth2_token:
        try:
            return _upload_v2(image_path, oauth2_token)
        except Exception as e:
            log.warning(f"v2 upload failed ({e}) — trying v1.1 fallback")

    try:
        return _upload_v1(image_path)
    except Exception as e:
        log.error(f"v1.1 upload also failed: {e}")
        return None


def _upload_v2(image_path: str, token: str) -> str:
    """POST to /2/media/upload with an OAuth 2.0 user context token."""
    url = "https://api.x.com/2/media/upload"
    with open(image_path, "rb") as f:
        r = requests.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            files={"media": (Path(image_path).name, f, "image/png")},
            timeout=120,
        )
    r.raise_for_status()
    return str(r.json()["data"]["id"])


def _upload_v1(image_path: str) -> str:
    """Upload via the v1.1 endpoint using OAuth 1.0a credentials."""
    auth = tweepy.OAuth1UserHandler(
        os.environ["TWITTER_API_KEY"],
        os.environ["TWITTER_API_SECRET"],
        os.environ["TWITTER_ACCESS_TOKEN"],
        os.environ["TWITTER_ACCESS_TOKEN_SECRET"],
    )
    api = tweepy.API(auth)
    media = api.media_upload(filename=image_path)
    return str(media.media_id)


# ── Card image download ───────────────────────────────────────────────────────

def download_card(url: str) -> str:
    """Download card image to a temp file; return path."""
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    suffix = ".png" if "png" in url.lower() else ".jpg"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(r.content)
    tmp.close()
    return tmp.name


# ── Queue check ───────────────────────────────────────────────────────────────

def check_and_warn_queue(notion: NotionClient):
    count = notion.get_queue_count()
    log.info(f"Queue depth: {count} approved players with cards")
    if count < LOW_QUEUE_THRESHOLD:
        msg = f"HalluStats queue low: {count} players remaining (threshold {LOW_QUEUE_THRESHOLD})"
        log.warning(msg)
        # GitHub Actions surfaces this as a workflow warning annotation
        print(f"::warning::{msg}")
    return count


# ── Main post flow ────────────────────────────────────────────────────────────

def post_player(player: dict, dry_run: bool, notion: NotionClient) -> bool:
    post_text = format_post(player)
    char_count = len(post_text)
    card_urls = player.get("card_image_urls", [])

    log.info(f"Player:     {player['name']}")
    log.info(f"Characters: {char_count} / {MAX_POST_CHARS}")
    log.info(f"Post text:\n{post_text}")
    if card_urls:
        log.info(f"Card image: {card_urls[0]}")
    else:
        log.warning("No card image attached — will post text only")

    # Audit fix #1: hard stop if post exceeds 280 chars
    if char_count > MAX_POST_CHARS:
        log.error(
            f"Post is {char_count} chars — exceeds {MAX_POST_CHARS}. "
            "Trim stat_note or story in Notion before posting."
        )
        return False

    if dry_run:
        log.info("Dry run — not posting.")
        return True

    page_id   = player["page_id"]
    tmp_image = None

    try:
        # Audit fix #5: mark Posting *before* the API call so a mid-run crash
        # leaves the player in Posting (not Approved), preventing a double-post.
        notion.mark_posting(page_id)

        media_id = None
        if card_urls:
            tmp_image = download_card(card_urls[0])
            media_id = upload_media(tmp_image)
            if not media_id:
                log.warning("Media upload failed — posting text only")

        client = get_v2_client()
        if media_id:
            resp = client.create_tweet(text=post_text, media_ids=[media_id])
        else:
            resp = client.create_tweet(text=post_text)

        tweet_id = resp.data["id"]
        log.info(f"Posted: https://x.com/HalluStats/status/{tweet_id}")
        notion.mark_posted(page_id)
        return True

    except Exception as e:
        log.error(f"Post failed: {e}")
        # Audit fix #5: revert to Approved so it stays in the queue
        try:
            notion.mark_failed(page_id)
        except Exception as revert_err:
            log.error(f"Could not revert status: {revert_err}")
        return False

    finally:
        if tmp_image:
            try:
                os.unlink(tmp_image)
            except OSError:
                pass


def main():
    parser = argparse.ArgumentParser(description="Post next HalluStats player to X")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview post without publishing")
    parser.add_argument("--check-queue", action="store_true",
                        help="Print queue depth and exit")
    args = parser.parse_args()

    notion = NotionClient()

    if args.check_queue:
        check_and_warn_queue(notion)
        return

    player = notion.get_next_approved()
    if not player:
        log.error("No approved players with card images ready to post")
        sys.exit(1)

    success = post_player(player, dry_run=args.dry_run, notion=notion)

    if not args.dry_run and success:
        check_and_warn_queue(notion)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
