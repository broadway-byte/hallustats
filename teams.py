"""
Canonical HalluStats team registry.

These are the only teams the generator should use. The note field is the
one-line historical hook — the generator can use it for story flavor.
years is the (first, last) season the franchise operated; the generator
only places a player on a team active during his career.
Teams marked with a region allow the critic to flag if the same region
dominates a single batch.
"""

TEAMS = [
    # ── Great Lakes / Midwest ────────────────────────────────────────────────
    {"name": "Findlay Well Shooters",      "years": (1888, 1931), "region": "midwest",    "note": "Well shooters dropped nitroglycerin down oil and gas wells to open the flow; Findlay boomed in the 1880s"},
    {"name": "Erie Shale Pickers",         "years": (1905, 1962), "region": "great_lakes","note": "Shale quarry labor on the lake bluffs"},
    {"name": "Kalamazoo Seagulls",         "years": (1923, 1971), "region": "great_lakes","note": "Seagulls followed river fishing boats inland; locals found this unsettling"},
    {"name": "Racine Marmots",             "years": (1909, 1957), "region": "great_lakes","note": "Groundhog colonies in the lakefront bluffs, a municipal nuisance"},
    {"name": "Youngstown Puddlers",        "years": (1895, 1958), "region": "great_lakes","note": "Iron puddlers stirred molten pig iron by hand at the steel mills"},
    {"name": "Zanesville Potters",         "years": (1896, 1949), "region": "midwest",    "note": "Center of American art pottery; also home of the Y-Bridge, which can be crossed without leaving the side of the river you started on"},
    {"name": "Lima Boilermakers",          "years": (1912, 1955), "region": "midwest",    "note": "Lima Locomotive Works built Shay geared logging engines and Super Power steam locomotives"},
    {"name": "Muncie Gaslights",           "years": (1889, 1912), "region": "midwest",    "note": "Indiana gas boom; flares burned day and night on the belief the gas would never run out; by 1910 it had"},
    {"name": "Gary Furnacemen",            "years": (1909, 1983), "region": "great_lakes","note": "U.S. Steel built the city around its blast furnaces in 1906 and named it for the company chairman, who lived in Manhattan"},
    {"name": "Peoria Coopers",             "years": (1887, 1919), "region": "midwest",    "note": "Barrel coopers for the Illinois River distilleries; Peoria paid more federal liquor tax than any district in the country"},
    {"name": "Decatur Starchmen",          "years": (1914, 1966), "region": "midwest",    "note": "A.E. Staley corn starch plant; the company football team later moved to Chicago and became the Bears"},
    {"name": "Oshkosh Sawdust",            "years": (1887, 1914), "region": "great_lakes","note": "Sawdust Capital of the World; 47 sawmills along the river by 1874"},
    {"name": "Waukegan Barbs",             "years": (1891, 1920), "region": "great_lakes","note": "Washburn & Moen opened a barbed wire works in 1891 and drew hundreds of workers to town"},
    {"name": "Waukegan Asbestos",          "years": (1921, 1968), "region": "great_lakes","note": "Johns Manville opened a large asbestos plant on the lakefront in the early 1920s; the product was considered a marvel"},
    {"name": "Terre Haute Wheelmen",       "years": (1893, 1937), "region": "midwest",    "note": "Named for the Terre Haute Cycling Club during the 1890s bicycle craze"},
    {"name": "Evansville River Rats",      "years": (1937, 1999), "region": "midwest",    "note": "Ohio River flood rats; originally a slur, adopted by the club as a point of pride"},

    # ── Mid-Atlantic / Northeast ─────────────────────────────────────────────
    {"name": "Baltimore Oyster Shuckers",  "years": (1887, 1934), "region": "mid_atlantic","note": "Chesapeake oyster packing houses employed over ten thousand Baltimoreans by 1869"},
    {"name": "Altoona Confectioners",      "years": (1938, 1976), "region": "mid_atlantic","note": "Boyer Brothers made Mallo Cups here; each wrapper held cardboard points that could be saved and redeemed from a prize catalogue"},
    {"name": "Troy Collars",               "years": (1888, 1929), "region": "northeast",   "note": "In 1825 a Troy housewife cut the collars off her husband's shirts so she would only have to wash those; the city built an industry on it"},
    {"name": "Schenectady Dynamos",        "years": (1899, 1974), "region": "northeast",   "note": "General Electric headquarters; the word dynamo was new and thrilling"},
    {"name": "Utica Knitters",             "years": (1902, 1959), "region": "northeast",   "note": "Knit goods center; in 1919 two thirds of working Uticans held textile jobs"},
    {"name": "Camden Riveters",            "years": (1917, 1967), "region": "mid_atlantic","note": "New York Shipbuilding Company riveted warships on the Delaware waterfront"},
    {"name": "Trenton Tileworkers",        "years": (1911, 1986), "region": "mid_atlantic","note": "The Staffordshire of America, built on pottery and tile; Trenton Makes, the World Takes"},
    {"name": "New London Whalers",         "years": (1887, 1926), "region": "northeast",   "note": "One of the three busiest whaling ports in the world; whale money built the mansions on Whale Oil Row"},
    {"name": "Lowell Bobbin Boys",         "years": (1888, 1963), "region": "northeast",   "note": "Planned textile city of the 1820s; bobbin boys swapped full bobbins for empty ones while the mill girls published a literary magazine"},
    {"name": "Haverhill Lasters",          "years": (1891, 1948), "region": "northeast",   "note": "A laster stretched leather uppers onto shoe lasts; by 1913 Haverhill made a tenth of America's shoes and called itself the Queen Slipper City"},
    {"name": "Brockton Peggers",           "years": (1898, 1990), "region": "northeast",   "note": "Pegging attached soles with wooden pegs; Brockton was America's largest shoe producer by the Civil War"},
    {"name": "Providence Platers",         "years": (1930, 2000), "region": "northeast",   "note": "Gold and silver plating for the costume jewelry trade; Providence called itself jewelry capital of the world"},
    {"name": "Scranton Breaker Boys",      "years": (1895, 1954), "region": "mid_atlantic","note": "Breaker boys sorted slate from anthracite by hand in the coal chutes"},
    {"name": "Wilkes-Barre Culm Dumpers",  "years": (1920, 1981), "region": "mid_atlantic","note": "Culm is coal waste; the culm banks around the city were visible for miles"},
    {"name": "Pottsville Anthracites",     "years": (1887, 1961), "region": "mid_atlantic","note": "Anthracite coal town; also home of Yuengling, America's oldest brewery, which got through Prohibition by making ice cream"},

    # ── Southern ─────────────────────────────────────────────────────────────
    {"name": "Birmingham Slag",            "years": (1902, 1975), "region": "south",      "note": "Crushed blast furnace slag from Birmingham paved roads and railbeds across the South"},
    {"name": "Knoxville Marbles",          "years": (1909, 1988), "region": "south",      "note": "The Marble City; Tennessee pink marble finished here went into the National Gallery of Art"},
    {"name": "Memphis Grocers",            "years": (1917, 1960), "region": "south",      "note": "Clarence Saunders opened the first self-service grocery here in 1916 and patented the idea of customers fetching their own groceries"},
    {"name": "Mobile Turpentiners",        "years": (1892, 1966), "region": "south",      "note": "Pine pitch and turpentine from the coastal forests shipped out of Mobile's docks"},
    {"name": "Macon Cherries",             "years": (1952, 2000), "region": "south",      "note": "Calls itself the Cherry Blossom Capital of the World; its Yoshino cherry trees do not produce cherries"},
    {"name": "Shreveport Roughnecks",      "years": (1908, 1994), "region": "south",      "note": "Drilling crews of the Caddo Parish oil field, which came in around 1905"},
    {"name": "Meridian Woodmen",           "years": (1912, 1952), "region": "south",      "note": "Woodmen of the World fraternal lodge combined with the timber industry"},
    {"name": "Tarpon Springs Spongers",    "years": (1905, 1947), "region": "south",      "note": "Greek divers from Kalymnos worked the Gulf sponge beds from 1905 until the 1947 red tide"},
    {"name": "Little Rock Bauxites",       "years": (1919, 1984), "region": "south",      "note": "Arkansas was the center of American aluminum ore mining"},
    {"name": "Nashville Cannonballs",      "years": (1887, 1924), "region": "south",      "note": "Western Highland Rim iron belt; Cumberland Furnace cast cannonballs for the Battle of New Orleans"},

    # ── Plains / Mountain ────────────────────────────────────────────────────
    {"name": "Topeka Grasshoppers",        "years": (1887, 1956), "region": "plains",     "note": "The locust swarms of the 1870s ate wood and wool and stopped trains on the rails; the species was last seen in 1904"},
    {"name": "Pueblo Ladlemen",            "years": (1891, 1982), "region": "mountain",   "note": "Ladlemen poured molten steel from the ladle into ingot molds at Colorado Fuel and Iron, for decades the only integrated steel mill in the West"},
    {"name": "Butte Copperheads",          "years": (1892, 1983), "region": "mountain",   "note": "Anaconda Copper's Butte operation; the richest hill on earth"},
    {"name": "Fargo Bones",                "years": (1887, 1903), "region": "plains",     "note": "Buffalo bones gathered off the plains were shipped east to be ground into fertilizer and used to whiten sugar"},
    {"name": "Duluth Dockers",             "years": (1903, 1997), "region": "great_lakes","note": "Lake Superior iron ore loaded onto Great Lakes freighters at the docks"},
    {"name": "Wichita Barnstormers",       "years": (1925, 2000), "region": "plains",     "note": "Air Capital of the World; Beech, Cessna and Stearman all started out together at one Wichita airplane company in 1925"},
    {"name": "Sioux City Meatpackers",     "years": (1888, 1999), "region": "plains",     "note": "Missouri River stockyards and meatpacking; a smaller version of Chicago"},

    # ── Pacific / Mountain West ──────────────────────────────────────────────
    {"name": "Kellogg Smelters",           "years": (1917, 1981), "region": "mountain",   "note": "Bunker Hill smelter fired up in 1917 on Coeur d'Alene silver and lead ore; the next town over was named Smelterville"},
    {"name": "Spokane Lilacs",             "years": (1890, 1973), "region": "pacific",    "note": "Called itself the Lilac City and held a lilac festival every spring from 1938"},
    {"name": "Tacoma Aromas",              "years": (1904, 1991), "region": "pacific",    "note": "The smell from the pulp mill and smelter on the tideflats was known locally as the Tacoma Aroma"},
    {"name": "Salt Lake Flats",            "years": (1915, 1979), "region": "mountain",   "note": "Salt was harvested from evaporation ponds on the lake; out on the Bonneville Salt Flats, men drove cars for land speed records starting in 1914"},
]

# Flat list of name strings — used in generator prompts
TEAM_NAMES = [t["name"] for t in TEAMS]

# Lookup by name
TEAM_BY_NAME = {t["name"]: t for t in TEAMS}

# Guard: full names and nicknames must both be unique
assert len(TEAM_BY_NAME) == len(TEAMS), "duplicate team name"
_nicks = [t["name"].split(" ", 1)[1] if t["name"].split(" ", 1)[0] not in ("New", "Little", "Salt", "Terre", "Sioux", "Tarpon") else t["name"].split(" ", 2)[2] for t in TEAMS]
assert len(set(_nicks)) == len(_nicks), "duplicate team nickname"


def teams_active(start: int, end: int) -> list:
    """Teams whose operating years overlap the given span."""
    return [t for t in TEAMS if t["years"][0] <= end and t["years"][1] >= start]


# ── Visual identity ──────────────────────────────────────────────────────────
# Fixed for a team's whole run; the era style handles the period look.
# cap: a simple symbol, never letters. chest: the only text allowed on the art.

COLOR_RGB = {
    "black": (20, 20, 20), "cream": (232, 220, 190), "slate gray": (95, 105, 115),
    "navy": (25, 35, 75), "white": (245, 245, 240), "gull gray": (150, 155, 160),
    "brown": (100, 65, 35), "tan": (195, 165, 120), "rust": (160, 70, 35),
    "glaze green": (60, 120, 90), "silver": (170, 175, 180), "flame orange": (230, 110, 30),
    "steel gray": (110, 115, 120), "red": (180, 30, 35), "whiskey brown": (140, 85, 40),
    "corn yellow": (235, 200, 70), "forest green": (35, 85, 50), "gray": (128, 128, 128),
    "ash gray": (175, 175, 170), "maroon": (110, 25, 40), "mud brown": (110, 85, 60),
    "river teal": (40, 110, 110), "pearl gray": (200, 200, 195), "chocolate brown": (80, 45, 25),
    "amber": (220, 150, 40), "heather gray": (160, 160, 160), "battleship gray": (110, 120, 125),
    "terracotta": (190, 95, 60), "crimson": (165, 20, 45), "oxblood": (95, 20, 25),
    "saddle brown": (140, 85, 45), "royal blue": (35, 70, 160), "coal black": (25, 25, 25),
    "slate": (90, 100, 110), "mustard": (210, 170, 50), "molten orange": (230, 100, 20),
    "iron gray": (90, 90, 95), "Tennessee pink": (215, 160, 155), "grocer green": (40, 120, 60),
    "pine green": (25, 80, 50), "blossom pink": (240, 170, 190), "sea blue": (40, 100, 150),
    "sand": (220, 200, 160), "bauxite red": (160, 55, 40), "gunmetal gray": (75, 80, 85),
    "scarlet": (200, 25, 30), "olive": (110, 110, 50), "wheat": (225, 200, 140),
    "charcoal": (55, 55, 60), "copper": (185, 105, 60), "bone white": (235, 228, 210),
    "lake blue": (40, 90, 140), "sky blue": (110, 170, 215), "lilac purple": (160, 120, 190),
    "desert tan": (210, 180, 130),
}

# name: (primary, secondary, cap symbol, chest wordmark, uniform detail)
KITS = {
    "Findlay Well Shooters":     ("black", "cream", "an oil derrick", "Findlay", "cream flannel with black sleeve stripes"),
    "Erie Shale Pickers":        ("slate gray", "navy", "a pickaxe", "Erie", "gray flannel with navy piping"),
    "Kalamazoo Seagulls":        ("white", "gull gray", "a seagull in flight", "Seagulls", "gray sleeve stripes"),
    "Racine Marmots":            ("brown", "tan", "a marmot's head", "Marmots", "tan socks with brown stripes"),
    "Youngstown Puddlers":       ("rust", "black", "a glowing ball of iron", "Youngstown", "rust pinstripes"),
    "Zanesville Potters":        ("glaze green", "cream", "a pottery vase", "Potters", "green piping"),
    "Lima Boilermakers":         ("black", "silver", "a locomotive drive wheel", "Lima", "a silver sleeve stripe"),
    "Muncie Gaslights":          ("navy", "flame orange", "a gas flame", "Muncie", "orange socks"),
    "Gary Furnacemen":           ("steel gray", "red", "a steel I-beam", "Gary", "red pinstripes"),
    "Peoria Coopers":            ("whiskey brown", "cream", "a barrel", "Coopers", "brown sleeve bands like barrel hoops"),
    "Decatur Starchmen":         ("white", "corn yellow", "an ear of corn", "Decatur", "an all-white uniform with yellow trim"),
    "Oshkosh Sawdust":           ("tan", "forest green", "a circular sawblade", "Oshkosh", "tan flannel with green socks"),
    "Waukegan Barbs":            ("gray", "black", "a twist of barbed wire", "Barbs", "black pinstripes"),
    "Waukegan Asbestos":         ("white", "ash gray", "a small flame inside a circle", "Asbestos", "an all-white uniform with gray trim"),
    "Terre Haute Wheelmen":      ("maroon", "cream", "a high-wheel bicycle", "Wheelmen", "a cream belt"),
    "Evansville River Rats":     ("mud brown", "river teal", "a rat", "River Rats", "brown sleeve stripes"),
    "Baltimore Oyster Shuckers": ("pearl gray", "navy", "an oyster shell", "Baltimore", "navy piping"),
    "Altoona Confectioners":     ("chocolate brown", "cream", "a wrapped piece of candy", "Altoona", "brown pinstripes"),
    "Troy Collars":              ("white", "black", "a pair of scissors", "Troy", "a tall stiff white collar on the jersey"),
    "Schenectady Dynamos":       ("navy", "amber", "a light bulb", "Dynamos", "an amber sleeve stripe"),
    "Utica Knitters":            ("heather gray", "red", "a ball of yarn with knitting needles", "Utica", "a red-trimmed knit collar"),
    "Camden Riveters":           ("battleship gray", "navy", "a rivet", "Camden", "a navy sleeve stripe"),
    "Trenton Tileworkers":       ("terracotta", "cream", "a square glazed tile", "Trenton", "checkered sleeve trim"),
    "New London Whalers":        ("navy", "white", "a harpoon", "Whalers", "navy pinstripes"),
    "Lowell Bobbin Boys":        ("crimson", "cream", "a thread bobbin", "Lowell", "crimson sleeves"),
    "Haverhill Lasters":         ("oxblood", "tan", "a wooden shoe last", "Haverhill", "tan socks"),
    "Brockton Peggers":          ("saddle brown", "cream", "a cobbler's hammer", "Brockton", "cream piping"),
    "Providence Platers":        ("silver", "royal blue", "a cut gemstone", "Providence", "silver sleeve stripes"),
    "Scranton Breaker Boys":     ("coal black", "gray", "a lump of coal", "Scranton", "gray socks"),
    "Wilkes-Barre Culm Dumpers": ("slate", "mustard", "a coal cart", "Wilkes-Barre", "mustard piping"),
    "Pottsville Anthracites":    ("black", "maroon", "a faceted lump of anthracite", "Pottsville", "maroon sleeves"),
    "Birmingham Slag":           ("iron gray", "molten orange", "a pouring ladle", "Slag", "orange sleeve stripes"),
    "Knoxville Marbles":         ("Tennessee pink", "gray", "a block of marble", "Knoxville", "pink trim"),
    "Memphis Grocers":           ("grocer green", "white", "a shopping basket", "Grocers", "green-and-white striped socks like a shop awning"),
    "Mobile Turpentiners":       ("pine green", "amber", "a pine tree", "Mobile", "amber piping"),
    "Macon Cherries":            ("blossom pink", "white", "a cartoon pair of maraschino cherries", "Macon", "pink sleeve stripes"),
    "Shreveport Roughnecks":     ("black", "red", "a pipe wrench", "Roughnecks", "red socks"),
    "Meridian Woodmen":          ("forest green", "tan", "a felling axe", "Woodmen", "a tan sleeve stripe"),
    "Tarpon Springs Spongers":   ("sea blue", "sand", "a brass diving helmet", "Spongers", "sand sleeve stripes"),
    "Little Rock Bauxites":      ("bauxite red", "white", "a chunk of red ore", "Little Rock", "red pinstripes"),
    "Nashville Cannonballs":     ("gunmetal gray", "scarlet", "a cannonball", "Nashville", "scarlet sleeves"),
    "Topeka Grasshoppers":       ("olive", "wheat", "a grasshopper", "Topeka", "olive sleeve stripes"),
    "Pueblo Ladlemen":           ("charcoal", "molten orange", "a steel ingot", "Pueblo", "charcoal pinstripes"),
    "Butte Copperheads":         ("copper", "black", "a coiled snake", "Butte", "copper sleeves"),
    "Fargo Bones":               ("bone white", "black", "a buffalo skull", "Fargo", "an all bone-white uniform"),
    "Duluth Dockers":            ("lake blue", "red", "an ore boat", "Duluth", "red sleeve stripes"),
    "Wichita Barnstormers":      ("sky blue", "red", "a biplane", "Wichita", "red sleeve stripes"),
    "Sioux City Meatpackers":    ("red", "white", "a butcher's cleaver", "Sioux City", "red pinstripes"),
    "Kellogg Smelters":          ("silver", "maroon", "a smokestack", "Kellogg", "maroon socks"),
    "Spokane Lilacs":            ("lilac purple", "white", "a lilac sprig", "Lilacs", "purple sleeve stripes"),
    "Tacoma Aromas":             ("olive", "mustard", "wavy lines rising from a stack", "Aromas", "mustard piping"),
    "Salt Lake Flats":           ("white", "desert tan", "a salt crystal", "Salt Lake", "tan sleeve stripes"),
}

assert set(KITS) == set(TEAM_BY_NAME), "every team needs exactly one kit"
for _t in TEAMS:
    _p, _s, _cap, _chest, _detail = KITS[_t["name"]]
    assert _p in COLOR_RGB and _s in COLOR_RGB, _t["name"]
    _t["kit"] = {"colors": (_p, _s), "cap": _cap, "chest": _chest, "detail": _detail}


def team_accent_rgb(team_name: str) -> tuple:
    """The darker of the team's two colors, so the card's accent line shows on a light strip."""
    p, s = TEAM_BY_NAME[team_name]["kit"]["colors"]
    lum = lambda c: 0.299 * c[0] + 0.587 * c[1] + 0.114 * c[2]
    return min(COLOR_RGB[p], COLOR_RGB[s], key=lum)
