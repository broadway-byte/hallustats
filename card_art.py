"""
Hallu card maker: period-correct fronts and backs.

The image model supplies everything physical (portrait art, cardstock, wear).
Code supplies every word and number, then "prints" them into the stock so
type picks up the paper grain, ink spread and stains instead of floating on top.

Period rules live in config.py (BACK_STYLES, FULL_CAREER_STATS_FROM, etc.).
"""

import hashlib
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

from config import (
    BACK_PHOTO_YEARS, BACK_STYLES, BW_BACK_PHOTO_YEARS, CARTOON_YEARS, ERA_STYLES,
    FRONT_BRAND_BANNER, FULL_CAREER_STATS_FROM,
)
from teams import TEAM_BY_NAME, team_accent_rgb

CARD_W, CARD_H = 750, 1050
STRIP_H = 130
FONT_DIR = Path("fonts")
TEMPLATE_DIR = Path("cards") / "templates"
PITCHERS = {"SP", "RP", "P"}
LIGHT = (248, 244, 234)


# ── Era / year helpers ────────────────────────────────────────────────────────

def era_for(player: dict) -> str:
    """The player's era, or the era whose years contain his first season if it is missing."""
    era = player.get("era")
    if era in ERA_STYLES:
        return era
    year = player.get("year_start") or 1925
    for name, style in ERA_STYLES.items():
        if style["years"][0] <= year <= style["years"][1]:
            return name
    return min(ERA_STYLES, key=lambda e: abs(ERA_STYLES[e]["years"][0] - year))


def card_year(player: dict) -> int:
    """Year the card was printed: the season after his last, kept inside his era.

    Dating cards after the career means a story never refers to a season the
    card could not have known about.
    """
    start = player.get("year_start") or 1925
    end = player.get("year_end") or start
    lo, hi = ERA_STYLES[era_for(player)]["years"]
    return min(max(end + 1, lo), hi)


def seed_for(player: dict, salt: str = "") -> int:
    return int(hashlib.md5((player.get("name", "") + salt).encode()).hexdigest(), 16) % (2 ** 31)


# ── Fonts ─────────────────────────────────────────────────────────────────────

def load_font(size: int, bold: bool = False, serif: bool = False):
    if serif:
        candidates = [
            FONT_DIR / ("serif_bold.ttf" if bold else "serif.ttf"),
            Path("/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf" if bold
                 else "/System/Library/Fonts/Supplemental/Times New Roman.ttf"),
            Path("/System/Library/Fonts/Supplemental/Georgia Bold.ttf" if bold
                 else "/System/Library/Fonts/Supplemental/Georgia.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf" if bold
                 else "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf"),
        ]
    else:
        candidates = [
            FONT_DIR / ("bold.ttf" if bold else "regular.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold
                 else "/System/Library/Fonts/Supplemental/Arial.ttf"),
            Path("/System/Library/Fonts/Helvetica.ttc"),
            Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold
                 else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        ]
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except Exception:
                continue
    return ImageFont.load_default()


# ── Printing: ink into paper ──────────────────────────────────────────────────

def _ink(base: Image.Image, mask: Image.Image, color: tuple, seed: int,
         spread: float = 0.6, strength: float = 0.92, offset=(0, 0)) -> Image.Image:
    """Multiply a color into base through mask, with ink spread and breakup."""
    rng = random.Random(seed)
    m = mask.filter(ImageFilter.GaussianBlur(spread)) if spread else mask
    if offset != (0, 0):
        m = ImageChops.offset(m, *offset)
    # Ink breakup: speckle the mask so solid areas look printed, not rendered
    noise = Image.effect_noise(base.size, 40 + rng.random() * 20).convert("L")
    noise = noise.point(lambda v: 255 if v > 70 else int(v * 2.5))
    m = ImageChops.multiply(m, noise)
    m = m.point(lambda v: int(v * strength))
    if _lum(color) > 160:
        # Light ink (e.g. cream lettering on a red strip): lighten instead of darken
        layer = ImageChops.blend(base, Image.new("RGB", base.size, color), 0.92)
    else:
        layer = ImageChops.multiply(base, Image.new("RGB", base.size, color))
    return Image.composite(layer, base, m)


def _lum(c):
    return 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]


def print_text(img, xy, text, font, color, seed, anchor="la", **kw):
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).text(xy, text, font=font, fill=255, anchor=anchor)
    return _ink(img, mask, color, seed, **kw)


def print_rect(img, box, color, seed, outline_only=False, width=3, **kw):
    mask = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(mask)
    if outline_only:
        d.rectangle(box, outline=255, width=width)
    else:
        d.rectangle(box, fill=255)
    return _ink(img, mask, color, seed, **kw)


def knockout_text(img, xy, text, font, seed, anchor="la"):
    """Light text inside a printed block: lift the ink back toward the stock."""
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).text(xy, text, font=font, fill=255, anchor=anchor)
    mask = mask.filter(ImageFilter.GaussianBlur(0.5))
    light = ImageChops.screen(img, Image.new("RGB", img.size, LIGHT))
    return Image.composite(light, img, mask)


def wrap_px(font, text, max_w):
    d = ImageDraw.Draw(Image.new("L", (1, 1)))
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if d.textlength(trial, font=font) <= max_w:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def text_w(font, text):
    return ImageDraw.Draw(Image.new("L", (1, 1))).textlength(text, font=font)


def fit_font(text, max_w, size, bold=True, serif=False, floor=18):
    f = load_font(size, bold, serif)
    while size > floor and text_w(f, text) > max_w:
        size -= 2
        f = load_font(size, bold, serif)
    return f


# ── Fronts ────────────────────────────────────────────────────────────────────

def front_text_mode(era: str) -> str:
    return ERA_STYLES[era].get("front_text", "strip")


def front_layout_prompt(era: str) -> str:
    mode = front_text_mode(era)
    if mode == "none":
        return "The image fills the whole card with no strip, banner or name area. "
    if mode == "brand_banner":
        return ("Leave a plain light banner across the very bottom (about 12 percent of card height), "
                "blank, with no lettering, for a printed banner to be added later. ")
    return ("Leave a plain light printed border strip at the very bottom (about 12 percent of card height), "
            "blank, with no lettering, for a caption to be added later. Give it the same age, "
            "wear and stains as the rest of the card. ")


def _strip_base(img, era, team):
    """Tint the model's blank strip to the era color while keeping its wear and stains."""
    style = ERA_STYLES[era]
    y0 = CARD_H - STRIP_H
    region = img.crop((0, y0, CARD_W, CARD_H))
    # Normalize the region's luminance so stains and creases survive the tint
    lum = ImageOps.autocontrast(region.convert("L"), cutoff=2).point(lambda v: 170 + v * 85 // 255)
    tinted = ImageChops.multiply(Image.new("RGB", region.size, style["strip_color"]), lum.convert("RGB"))
    img.paste(tinted, (0, y0))
    return img, y0


def stamp_front(img: Image.Image, player: dict) -> Image.Image:
    era = era_for(player)
    mode = front_text_mode(era)
    if mode == "none":
        return img
    style = ERA_STYLES[era]
    serif = BACK_STYLES[era].get("serif", False)
    seed = seed_for(player, "front")
    team = player.get("team", "")
    img, y0 = _strip_base(img, era, team)
    color = style["name_color"]
    accent = team_accent_rgb(team) if team in TEAM_BY_NAME else style["accent_color"]
    cx = CARD_W // 2

    if mode == "surname_city":
        # T206 caption: last name, then city
        surname = player.get("name", "").replace('"', "").split()[-1].upper()
        city = _city_of(team).upper()
        f = fit_font(f"{surname}, {city}", CARD_W - 80, 34, bold=True, serif=True)
        return print_text(img, (cx, y0 + STRIP_H // 2), f"{surname}, {city}", f, color, seed, anchor="mm")

    if mode == "brand_banner":
        f = fit_font(FRONT_BRAND_BANNER, CARD_W - 80, 44, bold=True, serif=True)
        img = print_rect(img, (0, y0, CARD_W, y0 + 6), style["accent_color"], seed)
        return print_text(img, (cx, y0 + STRIP_H // 2 + 3), FRONT_BRAND_BANNER, f, style["accent_color"], seed + 1, anchor="mm")

    # strip: name, then team and position (fronts never carried career years)
    img = print_rect(img, (0, y0, CARD_W, y0 + 5), accent if _lum(accent) < 200 else color, seed)
    name = player.get("name", "").upper()
    f1 = fit_font(name, CARD_W - 60, 34, bold=True, serif=serif)
    f2 = load_font(22, serif=serif)
    img = print_text(img, (cx, y0 + 46), name, f1, color, seed + 1, anchor="mm")
    line2 = f"{team.upper()}  ·  {player.get('position', '')}"
    misreg = (1, 0) if era in ("topps66", "topps76", "upperdeck") else (0, 0)
    strip_lum = _lum(style["strip_color"])
    line2_color = accent if abs(_lum(accent) - strip_lum) > 110 else color
    return print_text(img, (cx, y0 + 92), line2, f2, line2_color, seed + 2, anchor="mm", offset=misreg)


def _club_abbr(team_name: str) -> str:
    city = _city_of(team_name).upper()
    return {"TARPON SPRINGS": "TARPON SPGS."}.get(city, city[:12])


def _city_of(team_name: str) -> str:
    for multi in ("New London", "Little Rock", "Salt Lake", "Terre Haute", "Sioux City", "Tarpon Springs"):
        if team_name.startswith(multi + " "):
            return multi
    return team_name.split(" ", 1)[0]


# ── Season lines (stats era) ──────────────────────────────────────────────────

def season_lines(player: dict) -> list:
    """Year-by-year lines through the season before the card year.

    The best season is the player's real (generated) line; other seasons are
    built around it, seeded by name so a player's record never changes.
    """
    if player.get("seasons"):
        return _writer_seasons(player)
    rng = random.Random(seed_for(player, "seasons"))
    start = player.get("year_start") or 1925
    last = card_year(player) - 1
    end = min(player.get("year_end") or last, last)
    best = player.get("best_season_year") or end
    years = list(range(start, max(start, end) + 1))[-20:]
    club = _club_abbr(player.get("team", ""))
    pitcher = player.get("position") in PITCHERS
    out = []
    for y in years:
        is_best = (y == best)
        if pitcher:
            if player.get("earned_run_avg") is not None:
                era_best = float(player["earned_run_avg"])
                w_best, l_best = int(player.get("w") or 6), int(player.get("l") or 6)
            else:  # drafted before pitchers had their own fields
                era_best = float(player.get("avg") or 4.0)
                w_best, l_best = int(player.get("hr") or 6), int(player.get("rbi") or 6)
            g = rng.randint(18, 40)
            ip = rng.randint(60, 190)
            if is_best:
                w, l, era_v = w_best, l_best, era_best
                ip = max(ip, 150)
            else:
                w = rng.randint(0, max(1, w_best - 1))
                l = rng.randint(max(0, l_best - 3), l_best + 4)
                era_v = round(era_best + rng.uniform(0.2, 1.6), 2)
            so = int(ip * rng.uniform(0.35, 0.7))
            bb = int(ip * rng.uniform(0.3, 0.55))
            out.append(dict(year=y, club=club, g=g, ip=ip, w=w, l=l, so=so, bb=bb, era=era_v))
        else:
            avg_best = float(player.get("avg") or 0.240)
            hr_best, rbi_best = int(player.get("hr") or 2), int(player.get("rbi") or 30)
            g = rng.randint(60, 140)
            ab = int(g * rng.uniform(3.0, 3.8))
            if is_best:
                g = max(g, 120)
                ab = max(ab, int(g * 3.5))
                avg_v, hr, rbi = avg_best, hr_best, rbi_best
            else:
                avg_v = max(0.140, min(avg_best - 0.002, avg_best - rng.uniform(0.008, 0.045)))
                hr = rng.randint(0, max(0, hr_best - 1))
                rbi = int(rbi_best * rng.uniform(0.35, 0.9))
            h = round(ab * avg_v)
            d2 = int(h * rng.uniform(0.10, 0.20))
            t3 = rng.randint(0, 4)
            r = int(h * rng.uniform(0.35, 0.55))
            out.append(dict(year=y, club=club, g=g, ab=ab, r=r, h=h, d=d2, t=t3, hr=hr, rbi=rbi,
                            avg=(h / ab if ab else 0)))
    return out


def _writer_seasons(player: dict) -> list:
    """The writer's own season lines, shown through the season before the card year."""
    club = _club_abbr(player.get("team", ""))
    pitcher = player.get("position") in PITCHERS
    last = card_year(player) - 1
    out = []
    for x in sorted(player["seasons"], key=lambda x: x.get("year", 0)):
        if x.get("year", 0) > last:
            continue
        if pitcher:
            out.append(dict(year=x["year"], club=club, g=x.get("g", 0), ip=x.get("ip", 0), w=x.get("w", 0),
                            l=x.get("l", 0), so=x.get("so", 0), bb=x.get("bb", 0), era=float(x.get("era", 0))))
        else:
            ab, h = x.get("ab", 0), x.get("h", 0)
            out.append(dict(year=x["year"], club=club, g=x.get("g", 0), ab=ab, r=x.get("r", 0), h=h,
                            d=x.get("doubles", 0), t=x.get("triples", 0), hr=x.get("hr", 0),
                            rbi=x.get("rbi", 0), avg=(h / ab if ab else 0)))
    return out


def lifetime(lines: list, pitcher: bool) -> dict:
    if not lines:
        return {}
    if pitcher:
        ip = sum(x["ip"] for x in lines)
        er = sum(x["era"] * x["ip"] / 9 for x in lines)
        return dict(g=sum(x["g"] for x in lines), ip=ip, w=sum(x["w"] for x in lines),
                    l=sum(x["l"] for x in lines), so=sum(x["so"] for x in lines),
                    bb=sum(x["bb"] for x in lines), era=(er * 9 / ip if ip else 0))
    ab = sum(x["ab"] for x in lines)
    h = sum(x["h"] for x in lines)
    keys = ("g", "ab", "r", "h", "d", "t", "hr", "rbi")
    tot = {k: sum(x[k] for x in lines) for k in keys}
    tot["avg"] = h / ab if ab else 0
    return tot


def vitals(player: dict) -> str:
    rng = random.Random(seed_for(player, "vitals"))
    start = player.get("year_start") or 1925
    born = start - rng.randint(20, 24)
    months = ["Jan.", "Feb.", "Mar.", "Apr.", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]
    inches = rng.randint(67, 75)
    ht = f"{inches // 12}'{inches % 12}\""
    wt = rng.randint(158, 205)
    bats = rng.choice(["Right", "Right", "Left", "Both"])
    throws = "Left" if (player.get("position") in PITCHERS and rng.random() < 0.3) else "Right"
    return (f"Ht.: {ht}   Wt.: {wt}   Bats: {bats}   Throws: {throws}   "
            f"Born: {rng.choice(months)} {rng.randint(1, 28)}, {born}")


def _fmt_avg(v):
    return f"{v:.3f}".lstrip("0") if v < 1 else f"{v:.3f}"


# ── Back template (cardstock from the image model) ────────────────────────────

def back_template_prompt(era: str) -> str:
    b = BACK_STYLES[era]
    y0, y1 = ERA_STYLES[era]["years"]
    return (
        f"Flat, straight-on scan of the blank reverse side of a baseball card printed between {y0} and {y1}. "
        f"Only the bare {b['stock']}, completely unprinted: no text, no lettering, no borders, no graphics, "
        f"no logos. Show authentic age for the period: paper grain, slight discoloration, faint stains, "
        f"soft corner wear and a light crease or two. Even lighting, the card fills the entire frame edge to edge. "
        f"Aspect ratio roughly 3:4 (portrait card)."
    )


def load_back_template(era: str, fetch=None) -> Image.Image:
    """One generated cardstock per era, cached on disk. Falls back to a plain stock if none."""
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    path = TEMPLATE_DIR / f"back_{era}.png"
    if path.exists():
        return Image.open(path).convert("RGB").resize((CARD_W, CARD_H))
    if fetch is not None:
        img = fetch(back_template_prompt(era))
        img.save(path, "PNG")
        return img
    stock = Image.new("RGB", (CARD_W, CARD_H), BACK_STYLES[era]["stock_rgb"])
    grain = Image.effect_noise((CARD_W, CARD_H), 18).convert("RGB").point(lambda v: 200 + v // 5)
    return ImageChops.multiply(stock, grain)


def _vary_stock(template: Image.Image, seed: int) -> Image.Image:
    """Each card gets its own wear: flip or rotate the shared stock and add grain."""
    rng = random.Random(seed)
    img = template
    if rng.random() < 0.5:
        img = ImageOps.mirror(img)
    if rng.random() < 0.5:
        img = img.rotate(180)
    grain = Image.effect_noise(img.size, 14).convert("RGB").point(lambda v: 225 + v // 9)
    return ImageChops.multiply(img, grain)


def cartoon_prompt(player: dict, era: str) -> str:
    b = BACK_STYLES[era]
    return (
        f"A small single-panel cartoon, the kind printed on the back of a {card_year(player)} baseball card: "
        f"simple two-color line drawing in one ink color on {b['stock']}, a little cartoon ballplayer, "
        f"gently comic. It illustrates this: {player.get('stat_note', 'a baseball oddity')}. "
        f"No text, no lettering, no speech balloons. Square composition."
    )


# ── Backs ─────────────────────────────────────────────────────────────────────

def render_back(player: dict, template: Image.Image = None, cartoon: Image.Image = None,
                photo: Image.Image = None) -> Image.Image:
    era = era_for(player)
    b = BACK_STYLES[era]
    year = card_year(player)
    serif = b.get("serif", False)
    seed = seed_for(player, "back")
    img = _vary_stock(template or load_back_template(era), seed)
    ink, acc = b["ink"], b["accent"]
    m = 50
    w = CARD_W - 2 * m
    no = seed_for(player, "no") % b.get("series_size", 300) + 1
    s = [seed + i for i in range(200)]
    si = iter(s)

    img = print_rect(img, (24, 24, CARD_W - 24, CARD_H - 24), acc, next(si), outline_only=True, width=4)

    if b["layout"] == "ad":
        y = 250
        for i, line in enumerate(b["ad_lines"]):
            f = fit_font(line, w, 64 if i == 1 else 40, bold=True, serif=True)
            img = print_text(img, (CARD_W // 2, y), line, f, ink, next(si), anchor="mm")
            y += 90 if i == 1 else 70
        img = print_rect(img, (m + 60, y, CARD_W - m - 60, y + 3), ink, next(si))
        y += 50
        img = print_text(img, (CARD_W // 2, y), b["tagline"], load_font(24, serif=True), ink, next(si), anchor="mm")
        for j, line in enumerate(b["footer"]):
            img = print_text(img, (CARD_W // 2, CARD_H - 120 + j * 30), line, load_font(20, serif=True),
                             ink, next(si), anchor="mm")
        return img

    name = player.get("name", "").upper()
    pos = player.get("position", "")
    team = player.get("team", "")
    write_up = " ".join(x for x in ((player.get("stat_note") or "").strip(),
                                    (player.get("story") or "").strip()) if x)

    y = 56
    if b.get("numbered"):
        img = print_text(img, (m, y), f"No. {no}", load_font(24, bold=True, serif=serif), acc, next(si))
    y += 44

    # Optional back photo (1971, 1989 on)
    photo_w = 0
    if photo is not None and year in BACK_PHOTO_YEARS:
        ph = ImageOps.fit(photo, (150, 190), centering=(0.5, 0.25))
        if year in BW_BACK_PHOTO_YEARS:
            ph = ImageOps.grayscale(ph).convert("RGB")
        img.paste(ph, (CARD_W - m - 150, y))
        img = print_rect(img, (CARD_W - m - 150, y, CARD_W - m, y + 190), acc, next(si), outline_only=True, width=2)
        photo_w = 165

    # Name header
    hw = w - photo_w
    if b["layout"] == "stats":
        hf = fit_font(name, hw - 20, 40, bold=True, serif=serif)
        img = print_rect(img, (m - 10, y - 4, m - 10 + hw + 10, y + 56), acc, next(si))
        img = knockout_text(img, (m, y + 26), name, hf, next(si), anchor="lm")
    else:
        hf = fit_font(name, hw, 38, bold=True, serif=serif)
        img = print_text(img, (m, y + 26), name, hf, acc, next(si), anchor="lm")
    y += 72
    sub = load_font(22, serif=serif)
    img = print_text(img, (m, y), f"{pos}  ·  {team.upper()}", sub, ink, next(si))
    y += 34
    if b["layout"] == "stats" or era == "bowman":
        vf = fit_font(vitals(player), hw, 18, bold=False, serif=serif, floor=13)
        img = print_text(img, (m, y), vitals(player), vf, ink, next(si))
        y += 30
    y = max(y + 14, (56 + 44 + 200) if photo_w else 0)

    # Write-up, with the cartoon panel beside it when the period calls for one
    body = load_font(24 if b["layout"] == "stats" else 30, serif=serif)
    text_w_avail = w
    if cartoon is not None and CARTOON_YEARS[0] <= year <= CARTOON_YEARS[1] and b["layout"] == "stats":
        cw = 220
        cimg = ImageOps.fit(cartoon, (cw, cw)).convert("L")
        # Print the cartoon in the era ink, like a one-color plate
        mask = ImageOps.invert(ImageOps.autocontrast(cimg))
        layer = Image.new("L", img.size, 0)
        layer.paste(mask, (CARD_W - m - cw, y))
        img = _ink(img, layer, acc, next(si), spread=0.4)
        text_w_avail = w - cw - 20
    lines = wrap_px(body, write_up, text_w_avail)
    line_h = int(body.size * 1.35)
    y_text = y
    for line in lines[:10]:
        img = print_text(img, (m, y), line, body, ink, next(si))
        y += line_h
    if text_w_avail < w:
        y = max(y, y_text + 230)
    y += 16

    if b["layout"] == "bio":
        if b.get("series_line"):
            img = print_text(img, (CARD_W // 2, CARD_H - 170), b["series_line"],
                             load_font(22, serif=True), ink, next(si), anchor="mm")
        for j, line in enumerate(b["footer"]):
            f = load_font(30 if j == 0 else 20, bold=(j == 0), serif=True)
            img = print_text(img, (CARD_W // 2, CARD_H - 120 + j * 38), line, f, acc if j == 0 else ink,
                             next(si), anchor="mm")
        return img

    # Stat table
    pitcher = pos in PITCHERS
    lines_all = season_lines(player)
    tot = lifetime(lines_all, pitcher)
    full = year >= FULL_CAREER_STATS_FROM
    rows = lines_all if full else lines_all[-1:]
    title = ("MINOR LEAGUE PITCHING RECORD" if pitcher else "MINOR LEAGUE BATTING RECORD")
    if pitcher:
        cols = [("YR", 0), ("CLUB", 62), ("G", 230), ("IP", 290), ("W", 360), ("L", 410),
                ("SO", 460), ("BB", 520), ("ERA", 580)]
        def cells(r):
            return [str(r["year"])[-2:] if "year" in r else "", r.get("club", ""), r["g"], r["ip"], r["w"],
                    r["l"], r["so"], r["bb"], f"{r['era']:.2f}"]
    else:
        cols = [("YR", 0), ("CLUB", 50), ("G", 200), ("AB", 250), ("R", 312), ("H", 362), ("2B", 414),
                ("3B", 464), ("HR", 508), ("RBI", 552), ("AVG", 600)]
        def cells(r):
            return [str(r["year"])[-2:] if "year" in r else "", r.get("club", ""), r["g"], r["ab"], r["r"],
                    r["h"], r["d"], r["t"], r["hr"], r["rbi"], _fmt_avg(r["avg"])]

    foot_top = CARD_H - 70 - 34 * len(b["footer"])
    avail = foot_top - y - 40 - 34 - 34
    n = len(rows) + 1
    row_h = max(17, min(30, avail // max(n, 1)))
    if row_h * n > avail:
        rows = rows[-max(1, avail // row_h - 1):]
    tf = load_font(max(14, min(20, row_h - 6)), serif=False)
    hf2 = load_font(max(14, min(20, row_h - 6)), bold=True)

    img = print_text(img, (CARD_W // 2, y + 12), title, load_font(22, bold=True), acc, next(si), anchor="mm")
    y += 32
    img = print_rect(img, (m - 10, y, CARD_W - m + 10, y + row_h + 4), ink, next(si))
    for label, dx in cols:
        img = knockout_text(img, (m + dx, y + 3), label, hf2, next(si))
    y += row_h + 8
    for r in rows:
        for (label, dx), v in zip(cols, cells(r)):
            img = print_text(img, (m + dx, y), str(v), tf, ink, next(si))
        y += row_h
    img = print_rect(img, (m - 10, y + 2, CARD_W - m + 10, y + 4), ink, next(si))
    y += 8
    tot_cells = cells(dict(tot, year="", club="TOTALS")) if tot else []
    for (label, dx), v in zip(cols, tot_cells):
        if label == "YR":
            continue
        img = print_text(img, (m + dx, y), str(v), hf2, ink, next(si))

    for j, line in enumerate(b["footer"]):
        txt = line.format(year=year)
        img = print_text(img, (CARD_W // 2, CARD_H - 90 - (len(b["footer"]) - 1 - j) * 30), txt,
                         load_font(20, bold=(j == 0 and len(b["footer"]) > 1)), ink, next(si), anchor="mm")
    return img


# ── Image-generated backs ─────────────────────────────────────────────────────
# The whole back is drawn by the image model, from exact text supplied here,
# so it shares the fronts' printing, stock and wear. Text is kept short and
# tables are capped so the model has less to get wrong; you check every back
# before it posts.

BACK_LOOK = {
    "tobacco":   "the back of a 1909-1911 T206 tobacco card: a single advertisement in dark blue ink on thin cream "
                 "cardboard, ornate period display type, a thin decorative frame, no player information",
    "goudey":    "the back of a 1933 Goudey gum card: dark green ink on thick cream cardboard, the player's name and "
                 "a short biography set in a classic serif, a small gum advertisement at the foot",
    "bowman":    "the back of a 1948 Bowman gum card: black and red ink on thin off-white cardboard, card number, name, "
                 "short vital statistics and a biography in plain period type",
    "topps52":   "the back of a 1950s Topps card: red and black ink on gray cardboard, a name box, vital statistics, "
                 "a short biography, a one-panel cartoon, and a small statistics table",
    "topps66":   "the back of a 1960s Topps card: black and orange ink on gray cardboard, a name header, vital "
                 "statistics, a short biography, a one-panel cartoon, and a year-by-year statistics table",
    "topps76":   "the back of a 1970s Topps card: green and black ink on gray cardboard, a name header, vital "
                 "statistics, a short biography, a one-panel cartoon, and a year-by-year statistics table",
    "upperdeck": "the back of a late-1980s premium card: full color on white glossy cardboard, a small color "
                 "photograph of the player in one corner, a name banner, a short biography and a statistics table",
    "chrome":    "the back of a late-1990s chrome card: full color on bright white premium stock, a small color "
                 "photograph of the player, a name banner, a short biography and a statistics table",
}

MAX_BACK_ROWS = 8


def _table_lines(player: dict) -> list:
    pitcher = player.get("position") in PITCHERS
    rows = season_lines(player)
    full = card_year(player) >= FULL_CAREER_STATS_FROM
    rows = rows[-MAX_BACK_ROWS:] if full else rows[-1:]
    tot = lifetime(season_lines(player), pitcher)
    if pitcher:
        head = "YR  CLUB  G  IP  W  L  SO  BB  ERA"
        body = [f"{str(r['year'])[-2:]}  {r['club']}  {r['g']}  {r['ip']}  {r['w']}  {r['l']}  "
                f"{r['so']}  {r['bb']}  {r['era']:.2f}" for r in rows]
        totl = (f"TOTALS  {tot['g']}  {tot['ip']}  {tot['w']}  {tot['l']}  {tot['so']}  {tot['bb']}  "
                f"{tot['era']:.2f}") if tot else ""
        title = "MINOR LEAGUE PITCHING RECORD"
    else:
        head = "YR  CLUB  G  AB  R  H  2B  3B  HR  RBI  AVG"
        body = [f"{str(r['year'])[-2:]}  {r['club']}  {r['g']}  {r['ab']}  {r['r']}  {r['h']}  {r['d']}  "
                f"{r['t']}  {r['hr']}  {r['rbi']}  {_fmt_avg(r['avg'])}" for r in rows]
        totl = (f"TOTALS  {tot['g']}  {tot['ab']}  {tot['r']}  {tot['h']}  {tot['d']}  {tot['t']}  "
                f"{tot['hr']}  {tot['rbi']}  {_fmt_avg(tot['avg'])}") if tot else ""
        title = "MINOR LEAGUE BATTING RECORD"
    return [title, head] + body + ([totl] if totl else [])


def back_prompt(player: dict) -> str:
    """Full image prompt for a card back, with every word spelled out exactly."""
    era = era_for(player)
    b = BACK_STYLES[era]
    year = card_year(player)
    no = seed_for(player, "no") % b.get("series_size", 300) + 1
    name = player.get("name", "")
    team = player.get("team", "")
    pos = player.get("position", "")
    write_up = " ".join(x for x in ((player.get("stat_note") or "").strip(),
                                    (player.get("story") or "").strip()) if x)

    text = []
    if b["layout"] == "ad":
        text += b["ad_lines"] + [b["tagline"]] + b["footer"]
    else:
        if b.get("numbered"):
            text.append(f"No. {no}")
        text += [name.upper(), f"{pos}  ·  {team.upper()}"]
        if b["layout"] == "stats" or era == "bowman":
            text.append(vitals(player))
        if write_up:
            text.append(write_up)
        if b["layout"] == "stats":
            text += _table_lines(player)
        if b.get("series_line"):
            text.append(b["series_line"])
        text += [line.format(year=year) for line in b["footer"]]

    extras = []
    if b["layout"] == "stats" and CARTOON_YEARS[0] <= year <= CARTOON_YEARS[1]:
        extras.append(f"Include a small one-panel cartoon in the card's ink colors illustrating: "
                      f"{(player.get('stat_note') or 'a baseball oddity').rstrip('.')}. The cartoon has no words of its own.")
    if year in BACK_PHOTO_YEARS:
        tone = "black-and-white" if year in BW_BACK_PHOTO_YEARS else "color"
        t = TEAM_BY_NAME.get(team)
        kit = f" in a {t['kit']['colors'][0]} and {t['kit']['colors'][1]} uniform" if t else ""
        extras.append(f"Include a small {tone} head-and-shoulders photo of the player{kit}. "
                      f"{look_text(dict(player, pose=''))}")

    lines = "\n".join(f"- {t}" for t in text)
    return (
        f"Vintage baseball card, reverse side only, printed in {year}. It looks like {BACK_LOOK[era]}. "
        f"Flat, straight-on scan with the card filling the frame, aspect ratio roughly 3:4 (portrait). "
        f"Authentic age for a card printed in {year}: paper grain, slight ink spread, faint stains, "
        f"soft corner wear. {' '.join(extras)} "
        f"Print exactly this text, spelled exactly as written, and no other words, numbers or logos:\n"
        f"{lines}"
    )


# ── Image-generated fronts ────────────────────────────────────────────────────
# The image model draws the whole front, name plate included, from exact text.
# Older eras are illustrations that act out the story; later eras are photos
# with period name plates.

FRONT_LOOK = {
    "tobacco": (
        "a 1909-1911 T206 tobacco card: a hand-colored lithograph of the player standing full length in "
        "a posed stance on a patch of infield dirt, against a flat painted background of one deep color "
        "(brick red, olive, sky blue or mustard), inside a plain cream border. Below the picture, in the "
        "cream border, a two-line caption in small black serif capitals"
    ),
    "goudey": (
        "a 1933 Goudey gum card: a vivid painted portrait, head and shoulders, against a bold flat color "
        "background (bright red, yellow, green or orange), thick cream border, slightly stylized like "
        "commercial illustration of the period. At the bottom, a narrow cream banner with the player's "
        "name in small capitals and the gum brand in bold red capitals beneath it"
    ),
    "bowman": (
        "an early-1950s Bowman gum card: a painted oil-portrait illustration, waist up, visible brushwork and "
        "canvas texture, a plain soft pastel background, thin cream border. Across the bottom, a cream name "
        "panel with small double rule lines and a dot at each side: the name in large bold black capitals, "
        "the team in red capitals beneath it, and the position in bold black at the right end of the panel"
    ),
    "topps52": (
        "a 1952-1953 Topps card: a colorized, painted-over photograph portrait, white border. A bordered "
        "name box at the lower left holds a small round team logo, the name in bold black capitals and the "
        "team in smaller red capitals. A facsimile autograph in dark ink runs across the lower part of the picture"
    ),
    "topps66": (
        "a mid-1960s Topps card: a large headshot photograph beside a smaller full-length action photo cut "
        "out on a solid bright color panel (yellow, pink or orange). A diagonal color banner across the top "
        "left corner carries the team nickname in bold white capitals. Along the bottom, a bold color name "
        "bar: the name in large white condensed capitals, the position in black italic script, and the full "
        "team name in yellow capitals"
    ),
    "topps76": (
        "a mid-1970s Topps card: a color photograph inside a two-tone colored border, the team name in large "
        "bold colored letters across the top, a round pennant-style badge with the position in a lower "
        "corner, and the name in black capitals on a white banner along the bottom"
    ),
    "upperdeck": (
        "a late-1980s premium card: a glossy color action photograph, a bold diagonal stripe in the team "
        "colors along one edge carrying the team name, the name in white italic capitals on a dark color bar "
        "with thin pinstripe accents, the position beside it, a small round team logo badge in a corner, and a "
        "tiny silver hologram square"
    ),
    "chrome": (
        "a late-1990s chrome card: a refractor rainbow-foil border, an action photograph, the team name as a "
        "bold metallic script logo, the name in embossed silver capitals on a curved foil nameplate, and the "
        "position in a small foil shield"
    ),
}

OLD_POSITIONS = {"1B": "1st B.", "2B": "2nd B.", "3B": "3rd B.", "SS": "S. S.", "C": "Catcher",
                 "LF": "L. F.", "CF": "C. F.", "RF": "R. F.", "SP": "Pitcher", "RP": "Pitcher"}
POSITION_WORDS = {"1B": "first base", "2B": "second base", "3B": "third base", "SS": "shortstop",
                  "C": "catcher", "LF": "left field", "CF": "center field", "RF": "right field",
                  "SP": "pitcher", "RP": "pitcher"}
ILLUSTRATED_ERAS = {"tobacco", "goudey", "bowman", "topps52"}


def _plain_name(name: str) -> str:
    """Name as printed on a name plate, nickname quotes kept: LEROY "WELT" CONNATSER."""
    return " ".join(name.split())


def _signature_name(name: str) -> str:
    """How he would sign: first and last name, no nickname."""
    import re as _re
    return " ".join(_re.sub(r'"[^"]*"', "", name).split())


def _caption_name(name: str) -> str:
    """T206 captions used what the player was called: the nickname, then the surname."""
    import re as _re
    m = _re.search(r'"([^"]+)"', name)
    surname = name.replace('"', "").split()[-1]
    return f"{m.group(1)} {surname}" if m else _plain_name(name)


def front_text_lines(player: dict) -> list:
    """Every word printed on the front's name plate, exactly."""
    era = era_for(player)
    name = player.get("name", "")
    team = player.get("team", "")
    city = _city_of(team)
    nick = team[len(city):].strip() if team.startswith(city) else team
    pos = player.get("position", "")
    if era == "tobacco":
        return [f"{_caption_name(name).upper()}, {OLD_POSITIONS.get(pos, pos)}, {city.upper()}", nick.upper()]
    if era == "goudey":
        from config import FRONT_BRAND_BANNER
        return [_plain_name(name).upper(), FRONT_BRAND_BANNER]
    if era == "bowman":
        return [_plain_name(name).upper(), team.upper(), pos]
    if era == "topps52":
        return [_plain_name(name).upper(), team.upper(), f"Signature: {_signature_name(name)}"]
    if era == "topps66":
        return [nick.upper(), _plain_name(name).upper(), POSITION_WORDS.get(pos, pos), team.upper()]
    if era == "topps76":
        return [team.upper(), pos, _plain_name(name).upper()]
    return [team.upper(), _plain_name(name).upper(), pos]


def look_text(player: dict) -> str:
    """The same man in every image: fixed appearance plus the pose that acts out his story."""
    look = (player.get("look") or "").strip()
    pose = (player.get("pose") or "").strip()
    out = ""
    if look:
        out += f"The player, identical in every image of him: {look}. "
    if pose:
        out += f"Pose and expression: {pose}. "
    return out


def front_prompt(player: dict, option_idx: int, uniform: str = "") -> str:
    era = era_for(player)
    year = card_year(player)
    lines = "\n".join(f"- {t}" for t in front_text_lines(player))
    medium = ("It is an illustration, not a photograph: a character study where the pose and face tell "
              "the player's story. " if era in ILLUSTRATED_ERAS else "")
    framing = ["three-quarter view", "slight turn to the other side", "straight-on"][option_idx % 3]
    return (
        f"Vintage baseball card, front side, printed in {year}. It looks like {FRONT_LOOK[era]}. "
        f"{medium}{look_text(player)}{uniform}"
        f"Framing: {framing}. "
        f"Authentic age for a card printed in {year}: wear, soft corners, a crease or two, slight fading. "
        f"Flat straight-on scan, the card fills the frame, aspect ratio roughly 3:4 (portrait). "
        f"Print exactly this text on the card, spelled exactly as written; apart from the jersey wordmark "
        f"there are no other words or numbers:\n{lines}"
    )
