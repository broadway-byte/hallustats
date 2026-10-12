import os

CLAUDE_DRAFT_MODEL = os.getenv("CLAUDE_DRAFT_MODEL") or "claude-sonnet-4-6"   # empty secret falls back
CLAUDE_CRITIC_MODEL = os.getenv("CLAUDE_CRITIC_MODEL") or "claude-opus-4-8"
OPENAI_IMAGE_MODEL = "gpt-image-2"

# Era definitions. Weight = slots per 25-candidate batch (must sum to 25).
# front_text: "surname_city" = T206 caption (COBB, DETROIT); "brand_banner" = Goudey gum banner;
# "strip" = name with team and position; "none" = no lettering (1948 Bowman fronts carried no name). All lettering is stamped in code, never drawn by the model.
ERA_STYLES = {
    "tobacco": {
        "years": (1887, 1915),
        "weight": 3,
        "front_text": "surname_city",
        "description": (
            "T206 tobacco card, early 1900s. Color lithograph portrait on a painted background. "
            "Sepia and earth tones. Flat painted sky or studio backdrop. Subtle age wear and crease marks. "
            "No decorative borders. The look of a card printed by American Tobacco Company circa 1909."
        ),
        "strip_color": (240, 228, 210),
        "name_color": (18, 14, 10),
        "accent_color": (90, 60, 30),
    },
    "goudey": {
        "years": (1932, 1941),
        "weight": 4,
        "front_text": "brand_banner",
        "description": (
            "Goudey Big League Gum card, 1933–1941. Painterly close-up portrait against a bold single-color "
            "background (bright red, yellow, green, or orange). The illustration style is vivid and slightly "
            "stylized, like the real Goudey cards."
        ),
        "strip_color": (215, 195, 155),
        "name_color": (10, 10, 10),
        "accent_color": (180, 30, 20),
    },
    "bowman": {
        "years": (1948, 1955),
        "weight": 2,
        "front_text": "none",
        "description": (
            "Bowman Gum card, 1948–1955. Black-and-white or early color photograph, slightly grainy. "
            "Thin paper stock, faintly yellowed. Very minimal design — almost no border decoration. "
            "The look of early postwar baseball cards."
        ),
        "strip_color": (205, 198, 182),
        "name_color": (15, 15, 15),
        "accent_color": (60, 60, 60),
    },
    "topps52": {
        "years": (1952, 1960),
        "weight": 5,
        "front_text": "strip",
        "description": (
            "Classic Topps card, 1952–1960. Painted portrait or early color photography. "
            "The definitive golden-age baseball card look."
        ),
        "strip_color": (220, 200, 165),
        "name_color": (12, 12, 12),
        "accent_color": (160, 40, 30),
    },
    "topps66": {
        "years": (1961, 1969),
        "weight": 5,
        "front_text": "strip",
        "description": (
            "Topps card, 1961–1969. Full-bleed color photography. Portrait shot plus a small action inset "
            "in a color panel beside it. "
            "The look of the 1966 Topps set — bright, graphic, slightly worn."
        ),
        "strip_color": (210, 60, 30),
        "name_color": (245, 240, 230),
        "accent_color": (220, 170, 20),
    },
    "topps76": {
        "years": (1970, 1979),
        "weight": 2,
        "front_text": "strip",
        "description": (
            "Topps card, 1970–1979. Clean action photography, simple solid-color border. "
            "No frills — the workhorse card of the decade."
        ),
        "strip_color": (220, 200, 165),
        "name_color": (12, 12, 12),
        "accent_color": (30, 80, 160),
    },
    "upperdeck": {
        "years": (1984, 1993),
        "weight": 3,
        "front_text": "strip",
        "description": (
            "Junk wax era card, 1984–1993. Glossy action photography, bold graphic border in team colors. "
            "Donruss, Score, Fleer, or early Upper Deck style. "
            "The card looks expensive but was printed by the millions."
        ),
        "strip_color": (30, 50, 120),
        "name_color": (240, 235, 220),
        "accent_color": (200, 30, 30),
    },
    "chrome": {
        "years": (1993, 2000),
        "weight": 1,
        "front_text": "strip",
        "description": (
            "Topps Chrome or Bowman Chrome card, 1993–2000. Foil and refractor sheen on premium card stock. "
            "High-gloss action photography, holographic border, color team logo. "
            "The card catches the light."
        ),
        "strip_color": (180, 190, 210),
        "name_color": (10, 10, 30),
        "accent_color": (150, 170, 200),
    },
}

# How the chest wordmark is lettered in each era. Keeps uniforms period-correct.
WORDMARK_STYLES = {
    "tobacco":   "small plain block capitals sewn across a wool flannel button-front jersey",
    "goudey":    "arched felt block capitals or early chain-stitched script on flannel",
    "bowman":    "flowing script lettering on flannel",
    "topps52":   "flowing script lettering with an underline tail, on flannel",
    "topps66":   "script or block lettering on a flannel jersey",
    "topps76":   "block or script lettering on a double-knit pullover jersey",
    "upperdeck": "outlined block or script lettering on a double-knit jersey",
    "chrome":    "modern script lettering with a drop shadow",
}

# ── Hallu: the one fictional card maker across every era ─────────────────────
# Product changes with the period (tobacco, then gum, then cards alone); the maker never does.
# Backs: cardstock comes from the image model (one template per era); all printing is done in code.
#   layout "ad"    = tobacco advertising back, no player info (T206 backs carried none)
#   layout "bio"   = name, number, write-up, no stats (1933 Goudey, 1948 Bowman)
#   layout "stats" = vitals, write-up, stat table (Topps-style, 1952 on)
BACK_STYLES = {
    "tobacco": {
        "stock": "thin cream cardboard", "stock_rgb": (226, 216, 196), "ink": (40, 60, 120), "accent": (40, 60, 120),
        "layout": "ad", "serif": True,
        "ad_lines": ["SMOKE", "HALLU", "CIGARETTES"],
        "tagline": "BASE BALL SERIES  ·  150 SUBJECTS",
        "footer": ["FACTORY No. 30, DIST. OF OHIO"],
        "numbered": False,
    },
    "goudey": {
        "stock": "thick cream cardboard", "stock_rgb": (234, 224, 198), "ink": (35, 85, 45), "accent": (35, 85, 45),
        "layout": "bio", "serif": True,
        "series_line": "This is one of a series of 240 Baseball Stars",
        "footer": ["HALLU CHEWING GUM", "HALLU GUM COMPANY"],
        "numbered": True, "series_size": 240,
    },
    "bowman": {
        "stock": "thin off-white cardboard", "stock_rgb": (236, 232, 218), "ink": (20, 20, 20), "accent": (150, 30, 30),
        "layout": "bio", "serif": True,
        "series_line": "",
        "footer": ["HALLU GUM, INC."],
        "numbered": True, "series_size": 48,
    },
    "topps52": {
        "stock": "gray cardboard", "stock_rgb": (186, 180, 168), "ink": (20, 20, 20), "accent": (170, 30, 30),
        "layout": "stats", "serif": False,
        "footer": ["HALLU BASEBALL", "© H.G.I.   PRTD. IN U.S.A."],
        "numbered": True, "series_size": 407,
    },
    "topps66": {
        "stock": "gray cardboard", "stock_rgb": (196, 186, 166), "ink": (20, 20, 20), "accent": (200, 90, 20),
        "layout": "stats", "serif": False,
        "footer": ["© H.G.I.   PRTD. IN U.S.A."],
        "numbered": True, "series_size": 598,
    },
    "topps76": {
        "stock": "gray cardboard", "stock_rgb": (200, 190, 170), "ink": (25, 70, 40), "accent": (25, 70, 40),
        "layout": "stats", "serif": False,
        "footer": ["© HALLU GUM, INC.   PRTD. IN U.S.A."],
        "numbered": True, "series_size": 660,
    },
    "upperdeck": {
        "stock": "white glossy cardboard", "stock_rgb": (244, 244, 240), "ink": (20, 30, 70), "accent": (190, 30, 30),
        "layout": "stats", "serif": False,
        "footer": ["© {year} THE HALLU CARD CO.   PRINTED IN U.S.A."],
        "numbered": True, "series_size": 792,
    },
    "chrome": {
        "stock": "bright white premium cardboard", "stock_rgb": (240, 242, 246), "ink": (15, 15, 25), "accent": (90, 110, 150),
        "layout": "stats", "serif": False,
        "footer": ["© {year} THE HALLU CARD CO.   PRINTED IN U.S.A."],
        "numbered": True, "series_size": 495,
    },
}

# Period rules for card backs (by the card's print year)
FULL_CAREER_STATS_FROM = 1957          # before this: last season + lifetime only
CARTOON_YEARS = (1953, 1982)           # one-panel trivia cartoons on backs
BACK_PHOTO_YEARS = {1971} | set(range(1989, 2001))   # 1971 experiment; photos return 1989 on
BW_BACK_PHOTO_YEARS = {1971}
FRONT_BRAND_BANNER = "HALLU CHEWING GUM"   # Goudey-era fronts carried the gum banner, not the name

POSITIONS = ["1B", "2B", "3B", "SS", "C", "LF", "CF", "RF", "SP", "RP"]

COMEDIC_ANGLES = [
    "stat_oddity",       # a genuinely strange career stat or record
    "managerial_error",  # a mistake by or involving this player that cost games
    "injury",            # an injury with suspicious or comic circumstances
    "off_field_job",     # a real or rumored second job or side business during the career
    "specific_object",   # one named object (a glove, a hat, a car, a dog) that shaped the career
    "ballpark_incident", # one dated event at a specific ballpark, train or hotel
]

VOICE_RULES = """You write biographical entries for fictional minor-league and journeyman major-league baseball players from 1887 to 2000. These players did not exist.

Voice rules:
- Deadpan throughout. No winking, no "as if," no "somehow." The entry reads like a dry archive record.
- Humor comes from specificity, not from announcing something is funny. A batting average of .203 over nine seasons is funnier than "batted very poorly."
- The final sentence lands flat. It does not escalate, it does not resolve, it simply stops. The last line is often the funniest because it refuses to comment on itself.
- Player names are period-plausible: common first names of the era with either an unusual surname or a nickname in quotes that fits a specific physical trait or incident. Nicknames are never ironic — they describe exactly what they describe.
- Stats are internally consistent. Career WAR between -5.0 and +2.5. Batting averages between .158 and .291. HR totals between 0 and 22 for a career. Keep the numbers real-feeling.
- Teams are fictional but regionally plausible: cities that had minor-league or independent teams in the era. Team nicknames reflect local industry, fauna, or a specific incident.
- No modern slang. No anachronisms. No self-aware language.

Approved roster examples (match this quality and voice):
"Bones" Hildebrand — Played eight seasons with a career WAR of -1.3. Led the Eastern Shore League in passed balls three consecutive years. Retired to manage a laundry in Hagerstown.
Chester "Frosty" Pruett — 2B, .218 lifetime, renowned for his ability to ground out to second base in situations requiring a fly ball. The record stood for eleven years.
"Cramps" Doolan — Threw left-handed exclusively until 1914, when a winter incident required him to switch. The nature of the incident was not recorded.
Roscoe "Blimp" Creel — Caught for six teams in nine years. His throw to second base was described by the Akron Beacon as "a committed gesture."
Elwood "Rattles" Coombs — Career WAR of -2.1. His lifetime batting average improved .006 points following a beaning in 1931. He never mentioned this.

Story strength:
- Every story is built on one concrete, checkable detail: a date, a count, a named object, a named place, a quoted newspaper phrase. That detail is the joke.
- The story adds something new. It never restates the stat_note.
- Do not use the "nobody noticed him" shape: never interviewed, made no public statements, never discussed, without being noted, broadly accepted. It is overused.
- No two players in a batch share the same joke shape.
- Every number in the stat_note and story must agree with the player's season lines.

Do not write things like:
- "Despite this, he..." (telegraphs the joke)
- "Remarkably..." or "Incredibly..." (announcing the joke)
- "...for reasons that remain unclear" (winking)
- Any sentence that explains why something is funny"""

POST_TEMPLATE = """{name}
{position}, {team} · {years}

Career WAR: {war}
{season}: {line}

{stat_note}

{story}"""

PITCHER_POSITIONS = {"SP", "RP", "P"}


def best_season_line(p: dict) -> str:
    """The best-season stat line: ERA, W-L, K, BB for pitchers; AVG, HR, RBI for batters."""
    if p.get("position") in PITCHER_POSITIONS:
        era = p.get("earned_run_avg")
        if era is None:                    # players drafted before pitchers had their own fields
            era, w, l, so, bb = p.get("avg") or 0, p.get("hr") or 0, p.get("rbi") or 0, None, None
        else:
            w, l, so, bb = p.get("w") or 0, p.get("l") or 0, p.get("so"), p.get("bb")
        line = f"{float(era):.2f} ERA / {w}-{l}"
        if so is not None:
            line += f" / {so} K"
        if bb is not None:
            line += f" / {bb} BB"
        return line
    avg = p.get("avg") or 0
    avg_str = f".{int(round(avg * 1000)):03d}" if avg < 1 else f"{avg:.3f}"
    return f"{avg_str} / {p.get('hr', 0)} HR / {p.get('rbi', 0)} RBI"


def format_post(p: dict) -> str:
    years = p.get("years") or f"{p.get('year_start', '')}–{p.get('year_end', '')}"
    return POST_TEMPLATE.format(
        name=p["name"], position=p["position"], team=p["team"], years=years,
        war=p.get("career_war", "—"), season=p.get("best_season_year", ""),
        line=best_season_line(p), stat_note=p.get("stat_note", ""), story=p.get("story", ""),
    )

MAX_POST_CHARS = 280
MAX_STORY_CHARS = 95
MAX_STAT_NOTE_CHARS = 50
CARDS_DIR = "cards"
LAHMAN_NAMES_FILE = "lahman_names.json"
BATCH_CANDIDATES = 25
TOP_N_TO_NOTION = 8
MIN_SCORE_TO_NOTION = 7   # drafts the critic scores below this never reach Notion
LOW_QUEUE_THRESHOLD = 7
