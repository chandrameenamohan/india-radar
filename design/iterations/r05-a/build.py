#!/usr/bin/env python3
"""r05-a build step.

Reads design/fixture-v2/{cards,companies,descriptions,build-report,first-seen}
.json and writes the three things the one screen needs before it can exist:

  1. locations and department, normalised (1,672 raw place strings -> ~60
     places; 2,300 raw department strings -> 11 fields).
  2. the corpus, sharded, so a card can paint in under 1.5s: a ~460KB index of
     all 789 companies, a first-screenful head that is inlined into the HTML,
     and one small role file per company for expand-in-place.
  3. the fold, pre-rendered as HTML by this file, so the first cards are in the
     document before a line of JavaScript runs. qa/crosscheck.mjs asserts the
     Python-rendered card and the JS-rendered card carry the same text.

Nothing here is hand-entered. Every number in the output is counted from the
fixture. The only authored content is the *mapping* from raw strings to
buckets, which is a vocabulary, not a fact — and the six gate captions, which
are sentences about what a credential proves.

    python3 build.py
"""

import collections
import html
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.normpath(os.path.join(HERE, "..", "..", "fixture-v2"))
OUT = os.path.join(HERE, "data")
ROLES_OUT = os.path.join(OUT, "roles")

# --------------------------------------------------------------------- departments

# 11 fields. Ordered: the first pattern that matches a department string wins,
# so the specific exclusions sit above the general rules.
DEPTS = [
    ("design", "Design", [
        r"\bdesign\b", r"\bux\b", r"\bui\b", r"\bbrand studio\b", r"\bcreative\b",
        r"\bart\b",
    ]),
    ("research", "Research & AI", [
        r"\bresearch\b", r"\br ?& ?d\b", r"\bscience\b", r"\bapplied ai\b",
        r"\bai (trainer|tutor|lab)", r"\bmachine learning\b", r"\bml\b",
    ]),
    ("product", "Product", [
        r"\bproduct\b", r"\bepd\b", r"\bpgm\b", r"\bprogram management\b",
    ]),
    ("eng", "Engineering", [
        r"\bengineer", r"\bengineering\b", r"\btechnolog", r"\btech\b", r"\bsoftware\b",
        r"\bplatform\b", r"\binfrastructure\b", r"\bdev ?ops\b", r"\bsre\b", r"\bdata\b",
        r"\bhardware\b", r"\brobotic", r"\bautonom", r"\bpropulsion\b", r"\bphotonic",
        r"\bmanufactur", r"\bsilicon\b", r"\bfirmware\b", r"\bqa\b", r"\bquality\b",
        r"\barchitect", r"\bit\b", r"\binformation technology\b", r"\bsecurity\b",
        r"\bcyber", r"\bvehicle\b", r"\bself.driving\b", r"\bavionic", r"\bflight\b",
        r"\bmission\b", r"\bsystems\b", r"\blaunch\b", r"\bbuilder\b", r"\bdefen[sc]e\b",
        r"\bone platform\b", r"\bengine\b", r"\bstage\b", r"\bdeployment\b",
        r"\bapplied\b",
    ]),
    ("sales", "Sales & Partnerships", [
        r"\bsales\b", r"\bselling\b", r"\baccount (executive|management|manager)\b",
        r"\brevenue\b", r"\bcommercial\b", r"\bbusiness development\b", r"\bpartnership",
        r"\bchannel\b", r"\bgo.?to.?market\b", r"\bgtm\b", r"\bterritory\b", r"\bfield\b",
        r"\bsolutions?\b", r"\bpresales\b", r"\bstrategic markets\b", r"\bbrokerage\b",
        r"\bexpansion\b", r"\bmerchant\b", r"\bgrowth\b", r"\bdemand\b",
    ]),
    ("marketing", "Marketing", [
        r"\bmarketing\b", r"\bcommunicat", r"\bcontent\b", r"\bpublic relations\b",
        r"\bpr\b", r"\bdemand gen", r"\bevents?\b", r"\bcommunity\b", r"\bsocial\b",
    ]),
    ("cs", "Customer & Support", [
        r"\bcustomer\b", r"\bsupport\b", r"\bsuccess\b", r"\bclient\b", r"\bservices?\b",
        r"\bmember\b", r"\bpatient\b", r"\bcare\b", r"\bclinical\b", r"\bexperience\b",
        r"\bdelivery\b", r"\bengagement\b", r"\buser\b", r"\bprofessional services\b",
        r"\btrust ?& ?safety\b", r"\bsafeguards\b", r"\bmoderat",
    ]),
    ("finance", "Finance", [
        r"\bfinanc", r"\baccounting\b", r"\btreasury\b", r"\bfp ?& ?a\b", r"\baudit\b",
        r"\btax\b", r"\bstrategy\b", r"\bcorporate development\b", r"\binvestment",
        r"\bunderwrit",
    ]),
    ("legal", "Legal & Compliance", [
        r"\blegal\b", r"\bcompliance\b", r"\bcounsel\b", r"\bregulatory\b", r"\brisk\b",
        r"\bpolicy\b", r"\bgovernance\b", r"\bfin ?crime\b", r"\baml\b", r"\bfraud\b",
    ]),
    ("people", "People & Recruiting", [
        r"\bpeople\b", r"\bhuman resources\b", r"\bhr\b", r"\brecruit", r"\btalent\b",
        r"\bworkplace\b", r"\bculture\b", r"\bl ?& ?d\b", r"\blearning\b", r"\bhiring\b",
    ]),
    ("ops", "Operations & Admin", [
        r"\boperations?\b", r"\bops\b", r"\bg ?& ?a\b", r"\badmin", r"\bgeneral\b",
        r"\bsupply\b", r"\blogistic", r"\bfulfil", r"\bprocurement\b", r"\bsourcing\b",
        r"\bfacilit", r"\bcorporate\b", r"\bbusiness\b", r"\bhq\b",
        r"\bstrategy and operations\b", r"\bscaling\b", r"\bexecutive\b",
    ]),
]
DEPT_RX = [(key, re.compile("|".join(pats), re.I)) for key, _, pats in DEPTS]
DEPT_LABEL = {key: label for key, label, _ in DEPTS}
DEPT_LABEL["other"] = "Something else"
DEPT_ORDER = [key for key, _, _ in DEPTS] + ["other"]

# Titles are a better signal than a board's private department vocabulary
# ("토스코어", "One Platform", "Scaling"). Used only when the department string
# matches nothing above.
TITLE_PATTERNS = [
    ("eng", (
        r"\b(engineer|engineering|developer|swe|sre|devops|architect|scientist, data"
        r"|data scientist|analytics engineer|technician|technical lead|infrastructure"
        r"|security|qa|quality|firmware|hardware|robotics|machinist|mechanic|welder"
        r"|integration|test)\b"
    )),
    ("research", r"\b(research|researcher|scientist)\b"),
    ("design", r"\b(designer|design|ux|ui)\b"),
    ("product",
     r"\b(product manager|product lead|product owner|technical program manager|tpm)\b"),
    ("sales", (
        r"\b(account executive|sales|business development|partnerships?"
        r"|solutions consultant|solutions architect|account manager|revenue|bdr|sdr"
        r"|territory)\b"
    )),
    ("marketing",
     r"\b(marketing|content|communications|brand|seo|social media|events?)\b"),
    ("cs", (
        r"\b(customer|support|success|clinical|nurse|therapist|care|onboarding"
        r"|implementation|technical account)\b"
    )),
    ("finance", (
        r"\b(finance|financial|accountant|accounting|controller|fp&a|treasury|tax"
        r"|audit)\b"
    )),
    ("legal", r"\b(counsel|legal|compliance|paralegal|regulatory|risk|policy|fraud)\b"),
    ("people", r"\b(recruiter|recruiting|people|talent|hr business partner|workplace)\b"),
    ("ops", (
        r"\b(operations|operator|ops|coordinator|program manager|chief of staff"
        r"|executive assistant|supply|logistics|warehouse|driver)\b"
    )),
]
TITLE_RX = [(key, re.compile(pat, re.I)) for key, pat in TITLE_PATTERNS]


def dept_bucket(dept, title):
    """One of the 11 fields, or 'other' when neither the board nor the title says."""
    text = (dept or "").strip()
    if text:
        for key, rx in DEPT_RX:
            if rx.search(text):
                return key
    text = (title or "").strip()
    for key, rx in TITLE_RX:
        if rx.search(text):
            return key
    return "other"


# ------------------------------------------------------------------------- places

# One canonical place per cluster. Patterns are matched against the raw place
# string after it is split on " or " / "/" / ";" / " and ".
PLACES = [
    ("remote", "Remote", [
        r"^remote", r"\bremote\b", r"\banywhere\b", r"\bdistributed\b",
        r"\bwork from home\b",
    ]),
    # San Francisco proper and the rest of the Bay Area are separate buckets,
    # because "I mean the city" and "I will commute down the peninsula" are
    # different answers. `sfbay` is derived from the two in place_buckets, so
    # the union is a counted bucket and never a sum of two overlapping ones.
    ("sf", "San Francisco proper", [
        r"san francisco", r"\bsf\b", r"south san francisco",
    ]),
    ("bayarea", "The Bay Area outside San Francisco", [
        r"bay area", r"sunnyvale", r"mountain view",
        r"palo alto", r"san mateo", r"menlo park", r"redwood city", r"santa clara",
        r"san jose", r"oakland", r"berkeley", r"cupertino", r"burlingame",
        r"foster city", r"emeryville",
    ]),
    ("nyc", "New York", [
        r"new york", r"\bnyc\b", r"brooklyn", r"manhattan", r"long island city",
    ]),
    ("london", "London", [r"\blondon\b"]),
    ("seattle", "Seattle", [
        r"seattle", r"bellevue", r"redmond", r"kirkland", r"everett",
    ]),
    ("la", "Los Angeles", [
        r"los angeles", r"\bl\.a\.\b", r"santa monica", r"el segundo", r"culver city",
        r"pasadena", r"long beach", r"hawthorne", r"burbank", r"venice, ca",
        r"playa vista", r"irvine", r"torrance",
    ]),
    ("boston", "Boston", [
        r"boston", r"cambridge", r"somerville", r"waltham", r"burlington, ma",
    ]),
    ("austin", "Austin", [r"austin"]),
    ("chicago", "Chicago", [r"chicago", r"evanston"]),
    ("denver", "Denver", [r"denver", r"boulder"]),
    ("dc", "Washington DC", [
        r"washington", r"\bd\.?c\.?\b", r"arlington", r"mclean", r"reston", r"bethesda",
        r"alexandria, va",
    ]),
    ("atlanta", "Atlanta", [r"atlanta"]),
    ("dallas", "Dallas / Houston", [
        r"dallas", r"houston", r"plano", r"fort worth", r"irving, tx", r"san antonio",
    ]),
    ("miami", "Miami", [r"miami", r"fort lauderdale", r"tampa", r"orlando"]),
    ("raleigh", "Raleigh / Durham", [
        r"raleigh", r"durham", r"\bcary\b", r"research triangle", r"chapel hill",
        r"charlotte",
    ]),
    ("slc", "Salt Lake City", [r"salt lake", r"lehi", r"provo", r"draper, ut"]),
    ("phoenix", "Phoenix", [r"phoenix", r"tempe", r"scottsdale", r"chandler, az"]),
    ("sandiego", "San Diego", [r"san diego", r"carlsbad"]),
    ("philly", "Philadelphia", [r"philadelphia", r"pittsburgh", r"conshohocken"]),
    ("midwest", "Detroit / Minneapolis / Ohio", [
        r"detroit", r"ann arbor", r"minneapolis", r"st\.? paul", r"columbus",
        r"cleveland", r"cincinnati", r"indianapolis", r"madison, wi", r"milwaukee",
        r"kansas city", r"st\.? louis",
    ]),
    ("nashville", "Nashville / Denver South", [
        r"nashville", r"memphis", r"louisville", r"birmingham, al",
    ]),
    ("portland", "Portland", [r"portland"]),
    ("toronto", "Toronto", [r"toronto", r"waterloo", r"ottawa"]),
    ("vancouver", "Vancouver", [r"vancouver"]),
    ("montreal", "Montreal", [r"montr"]),
    ("dublin", "Dublin", [r"dublin"]),
    ("berlin", "Berlin", [r"berlin"]),
    ("munich", "Munich", [r"munich", r"münchen"]),
    ("paris", "Paris", [r"paris"]),
    ("amsterdam", "Amsterdam", [r"amsterdam", r"utrecht", r"rotterdam"]),
    ("barcelona", "Barcelona", [r"barcelona"]),
    ("madrid", "Madrid", [r"madrid"]),
    ("lisbon", "Lisbon", [r"lisbon", r"lisboa", r"porto"]),
    ("zurich", "Zurich", [r"zurich", r"zürich", r"geneva"]),
    ("stockholm", "Stockholm / Nordics", [
        r"stockholm", r"copenhagen", r"oslo", r"helsinki", r"espoo", r"gothenburg",
        r"malm", r"aarhus",
    ]),
    ("warsaw", "Warsaw / Kraków", [r"warsaw", r"krak", r"wroc", r"gda", r"pozna"]),
    ("milan", "Milan / Rome", [r"milan", r"milano", r"\brome\b", r"roma\b", r"turin"]),
    ("vienna", "Vienna / Zurich-adjacent", [
        r"vienna", r"wien\b", r"prague", r"praha", r"budapest", r"bratislava",
    ]),
    ("bucharest", "Bucharest / Sofia", [
        r"bucharest", r"sofia", r"cluj", r"belgrade", r"zagreb", r"timi",
    ]),
    ("telaviv", "Tel Aviv", [r"tel aviv", r"herzliya", r"\bisrael\b"]),
    ("dubai", "Dubai", [r"dubai", r"abu dhabi"]),
    ("bengaluru", "Bengaluru", [r"bengaluru", r"bangalore"]),
    ("indiaother", "Mumbai / Delhi / Hyderabad", [
        r"mumbai", r"\bdelhi\b", r"gurugram", r"gurgaon", r"noida", r"hyderabad",
        r"pune", r"chennai",
    ]),
    ("singapore", "Singapore", [r"singapore"]),
    ("tokyo", "Tokyo", [r"tokyo", r"\bjapan\b"]),
    ("seoul", "Seoul", [r"seoul", r"\bkorea\b", r"서울"]),
    ("hongkong", "Hong Kong", [
        r"hong kong", r"shenzhen", r"shanghai", r"beijing", r"taipei",
    ]),
    ("sydney", "Sydney / Melbourne", [
        r"sydney", r"melbourne", r"brisbane", r"auckland", r"wellington",
    ]),
    ("saopaulo", "São Paulo", [
        r"paulo", r"\bbrazil\b", r"brasil", r"rio de janeiro", r"belo horizonte",
    ]),
    ("mexico", "Mexico City", [r"mexico", r"méxico", r"cdmx", r"guadalajara"]),
    ("bogota", "Bogotá / Buenos Aires", [
        r"bogot", r"buenos aires", r"santiago", r"lima", r"medell",
    ]),
    ("lagos", "Lagos / Nairobi", [
        r"lagos", r"nairobi", r"\bafrica\b", r"cape town", r"johannesburg",
    ]),
]
PLACE_RX = [(key, re.compile("|".join(pats), re.I)) for key, _, pats in PLACES]
PLACE_LABEL = {key: label for key, label, _ in PLACES}
# The union bucket. It is added to a role's set whenever either half matched, so
# it is counted once per role and never the sum of two overlapping counts.
PLACE_LABEL["sfbay"] = "San Francisco and the wider Bay Area"

# Country-level strings resolve to their own bucket, never to a city inside
# them: "United States" is not San Francisco, and pretending otherwise would be
# the exact move the doctrine forbids.
COUNTRY_PATTERNS = [
    ("us_any", "United States — city not stated",
     r"^(united states|usa|u\.s\.a?\.?|us|north america|remote - us|us remote)$"),
    ("uk_any", "United Kingdom — city not stated",
     r"^(united kingdom|uk|england|great britain|scotland|wales|ireland)$"),
    ("in_any", "India — city not stated", r"^(india)$"),
    ("ca_any", "Canada — city not stated", r"^(canada)$"),
    ("de_any", "Germany — city not stated",
     r"^(germany|deutschland|austria|switzerland)$"),
    ("es_any", "Spain / Portugal — city not stated", r"^(spain|portugal|espa|italy)$"),
    ("eu_any", "Europe — city not stated",
     r"^(europe|emea|eu|france|netherlands|poland|romania|bulgaria|croatia|hungary"
     r"|belgium|sweden|norway|denmark|finland|greece|czech republic|serbia|estonia"
     r"|lithuania|latvia|slovakia|slovenia|ukraine|turkey|cyprus|malta|luxembourg)$"),
    ("latam_any", "Latin America — city not stated",
     r"^(brazil|brasil|argentina|colombia|chile|peru|mexico|uruguay|latam"
     r"|latin america|costa rica)$"),
    ("apac_any", "Asia-Pacific — city not stated",
     r"^(australia|new zealand|japan|korea|south korea|china|taiwan|thailand|vietnam"
     r"|philippines|indonesia|malaysia|apac|asia)$"),
    ("unstated", "Their board did not say where",
     r"^(blank|n/?a|unknown|tbd|-{1,3}|other)$"),
]
COUNTRY_RX = [(key, re.compile(pat, re.I)) for key, _, pat in COUNTRY_PATTERNS]
PLACE_LABEL.update({key: label for key, label, _ in COUNTRY_PATTERNS})
PLACE_LABEL["elsewhere"] = "Somewhere not in this list"
PLACE_LABEL["unstated"] = "Their board did not say where"

SPLIT = re.compile(
    r"\s+or\s+|\s*/\s*|\s*;\s*|\s*\|\s*|\s+and\s+|\s*,\s*(?=(?:remote|hybrid)\b)",
    re.I,
)


def _one_place(part):
    """A single raw place fragment -> a canonical key, or None if nothing matches."""
    for key, rx in COUNTRY_RX:
        if rx.match(part):
            return key
    for key, rx in PLACE_RX:
        if rx.search(part):
            return key
    return None


def place_buckets(raw_places):
    """A role's raw place strings -> the set of canonical place keys it covers."""
    out = set()
    for raw in raw_places or []:
        text = (raw or "").strip()
        if not text:
            continue
        matched_any = False
        for part in (p.strip() for p in SPLIT.split(text)):
            if not part:
                continue
            key = _one_place(part)
            if key:
                out.add(key)
                matched_any = True
        if not matched_any:
            out.add("elsewhere")
    if "sf" in out or "bayarea" in out:
        out.add("sfbay")
    return out or {"unstated"}


# --------------------------------------------------------------------------- gate

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug",
          "Sep", "Oct", "Nov", "Dec"]


def money(amount, currency):
    if amount is None:
        return None
    symbol = {"USD": "$", "EUR": "€", "GBP": "£"}.get(currency or "USD", "")
    return symbol + f"{int(amount):,}"


def pretty_date(value):
    if not value:
        return None
    try:
        year, month, day = value.split("-")
        return f"{MONTHS[int(month) - 1]} {int(day)}, {year}"
    except (ValueError, IndexError):
        return value


def _gate_yc(card, url):
    yc = card["yc"]
    return {
        "who": "Y Combinator",
        "line": f"Y Combinator backed them, {yc['batch']}",
        "url": url,
        "kind": "yc",
        "batch": yc["batch"],
        "status": yc["status"],
        "team": yc.get("team_size"),
        "top": bool(yc.get("top_company")),
    }


def _gate_sec(card, url):
    amount = money(card["amount"], card["currency"])
    date = pretty_date(card["date"])
    if amount and date:
        line = f"They filed a Form D with the SEC for {amount} on {date}"
    elif date:
        line = f"They filed a Form D with the SEC on {date}"
    else:
        line = "They filed a Form D with the SEC"
    return {"who": "SEC EDGAR", "line": line, "url": url, "kind": "sec",
            "amount": amount, "date": date}


def _gate_press(card, url, who):
    amount = money(card["amount"], card["currency"])
    date = pretty_date(card["date"])
    line = f"{who} reported a round"
    if amount:
        line += f" of {amount}"
    if date:
        line += f" on {date}"
    return {"who": who, "line": line, "url": url, "kind": "tc",
            "amount": amount, "date": date}


def _gate_listed(url, who, line):
    kind = {"Forbes": "forbes", "CB Insights": "cbi"}.get(who, "other")
    return {"who": who, "line": line, "url": url, "kind": kind}


HOST_GATES = {
    "sec.gov": _gate_sec,
    "techcrunch.com": lambda card, url: _gate_press(card, url, "TechCrunch"),
    "finsmes.com": lambda card, url: _gate_press(card, url, "FinSMEs"),
    "forbes.com": lambda card, url: _gate_listed(
        url, "Forbes", "A Forbes editor put them on a list"),
    "cbinsights.com": lambda card, url: _gate_listed(
        url, "CB Insights", "CB Insights tracks them at a $1B+ valuation"),
}


def gate(card):
    """The one line on the card that says who vouched, and the receipt behind it.

    Every branch returns a link; there is no branch without one.
    """
    url = card["source_url"]
    host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
    if card.get("yc"):
        return _gate_yc(card, url)
    build = HOST_GATES.get(host)
    if build:
        return build(card, url)
    return _gate_listed(url, host, f"Listed by {host}")


# ------------------------------------------------------------------ the caption
# The sentence after the receipt that says what the credential proves and what
# it does not. It is written here, once, and shipped on the record — so the
# Python fold and the JavaScript render the same string by construction rather
# than by two authors agreeing.

def _yc_caption(g, roles):
    if g["status"] == "Active":
        if g.get("team"):
            return (f" — still independent; YC lists {g['team']:,} people, "
                    f"their own board lists {roles:,} roles.")
        return f" — still independent, and their own board lists {roles:,} roles."
    # A status is a fact with a source and it is printed as one. Round 4 read
    # this as a warning and the founder reads a young public company as the
    # opposite; neither reading belongs on the card, so neither is written here.
    return f" — and YC’s own status field for them reads {g['status']}."


def _cbi_caption(roles, dept_counts, place_counts):
    """291 cards carry CB Insights, so the second half of the sentence is a fact
    that differs between them rather than the same clause 291 times."""
    head = (" — a tracker’s call on size, not a funding fact. "
            "$1B means the launch already happened; ")
    top = dept_counts.most_common(1)
    places = len([k for k in place_counts if k not in ("elsewhere", "unstated", "sfbay")])
    if top and roles and top[0][1] * 100 >= roles * 55:
        key, n = top[0]
        return head + (f"{n:,} of their {roles:,} open roles are in "
                       f"{DEPT_LABEL[key].lower()}, which is what I would go on.")
    if places >= 8:
        return head + (f"they are hiring in {places:,} places tonight, and a company "
                       "opening that many doors is the part I can count.")
    return head + f"the {roles:,} roles on their own board tonight are what I would go on."


CAPTIONS = {
    "sec": " — a filing signed by their own counsel, not a press release.",
    "forbes": " — an editor’s call. No funding number behind it, and I will not "
              "invent one.",
    "tc": " — a reporter’s account of a round, dated.",
}


def gate_caption(g, roles, dept_counts, place_counts):
    if g["kind"] == "yc":
        return _yc_caption(g, roles)
    if g["kind"] == "cbi":
        return _cbi_caption(roles, dept_counts, place_counts)
    return CAPTIONS.get(g["kind"], "")


# ------------------------------------------------------------------ descriptions
# 371 of the 789 companies carry three one-line fields. They are this page's own
# summary of a company's own site — the page's voice, not a board's — so the
# provenance is on the record and the standing disclosure is in the lede.

PROVENANCE = {
    "checked": "in my words, checked against their own site",
    "unchecked": "in my words, not yet checked against their site",
    "board": "in my words, read off their own job board",
}


def describe(name, descriptions):
    """{what, for_whom, why_them, provenance} for a company, or None."""
    row = descriptions.get(name)
    if not row:
        return None
    if row.get("source") == "board":
        prov = "board"
    elif row.get("checked"):
        prov = "checked"
    else:
        prov = "unchecked"
    return {"w": row["what"], "f": row["for_whom"], "y": row["why_them"], "p": prov}


# ------------------------------------------------------------------- role folding

def fold_roles(roles, counters):
    """Roles -> compact rows for the shard, plus this company's histograms."""
    rows = []
    dept_counts = collections.Counter()
    place_counts = collections.Counter()
    pairs = collections.Counter()   # (field, place) -> n, for the yield line
    for role in roles:
        field = dept_bucket(
            role.get("dept_norm") or role.get("department"), role.get("title"))
        places = sorted(place_buckets(role.get("places") or role.get("locations")))
        if field == "other":
            unbucketed = (role.get("dept_norm") or "") + " || " + (role.get("title") or "")
            counters["other_titles"][unbucketed] += 1
        dept_counts[field] += 1
        for place in places:
            place_counts[place] += 1
            pairs[(field, place)] += 1

        answers = (role.get("visa") or "unknown",
                   role.get("hire_from_abroad") or "unknown")
        stated = "yes" if "yes" in answers else ("no" if "no" in answers else None)
        counters["visa"][stated or "unknown"] += 1

        workplace = role.get("workplace")
        # The board's own department word, printed beside the role as the board
        # wrote it. My eleven fields are a renderer's grouping; this is theirs.
        theirs = (role.get("department") or "").strip()
        rows.append({
            "t": role.get("title"),
            "u": role.get("url"),
            "l": ", ".join((role.get("places") or role.get("locations") or [])[:3]),
            "d": field,
            "p": places,
            "w": workplace if workplace in ("remote", "hybrid", "onsite") else None,
            "v": stated,
            "b": theirs or None,
        })
    return rows, dept_counts, place_counts, pairs


# ---------------------------------------------------------------------- the menus

PLACE_GROUPS = [
    ("The big four", {"remote", "sfbay", "nyc", "london"}),
    ("…and the Bay Area split in two, if you mean the city", {"sf", "bayarea"}),
    ("United States", {
        "seattle", "la", "boston", "austin", "chicago", "denver", "dc", "atlanta",
        "dallas", "miami", "raleigh", "slc", "phoenix", "sandiego", "philly",
        "midwest", "nashville", "portland", "us_any",
    }),
    ("Europe", {
        "dublin", "berlin", "munich", "paris", "amsterdam", "barcelona", "madrid",
        "lisbon", "zurich", "stockholm", "warsaw", "milan", "vienna", "bucharest",
        "uk_any", "de_any", "es_any", "eu_any",
    }),
    ("Asia-Pacific & Middle East", {
        "bengaluru", "indiaother", "singapore", "tokyo", "seoul", "hongkong",
        "sydney", "dubai", "telaviv", "in_any", "apac_any",
    }),
    ("The Americas & Africa", {
        "toronto", "vancouver", "montreal", "saopaulo", "mexico", "bogota", "lagos",
        "ca_any", "latam_any",
    }),
    ("Stated, but not as a place", {"elsewhere", "unstated"}),
]
GROUP_NAMES = [name for name, _ in PLACE_GROUPS]
GROUP_OF = {key: name for name, keys in PLACE_GROUPS for key in keys}


def build_menus(counters):
    """The two controls.

    Only places with enough companies behind them are worth a reader's click;
    everything else stays reachable through "anywhere", so nothing is cut from
    the corpus, only from the menu.
    """
    dept_co, dept_roles = counters["dept_co"], counters["dept_roles"]
    place_co, place_roles = counters["place_co"], counters["place_roles"]
    dept_menu = [
        {"k": key, "l": DEPT_LABEL[key], "c": dept_co[key], "r": dept_roles[key]}
        for key in DEPT_ORDER if dept_co[key]
    ]
    place_menu = [
        {"k": key, "l": PLACE_LABEL.get(key, key), "c": place_co[key],
         "r": place_roles[key], "g": GROUP_OF.get(key, "Elsewhere")}
        for key, _ in place_co.most_common() if place_co[key] >= 8
    ]
    place_menu.sort(key=lambda p: (
        GROUP_NAMES.index(p["g"]) if p["g"] in GROUP_NAMES else 9, -p["c"]))
    return dept_menu, place_menu


# ---------------------------------------------------------------------------- run

def read_fixture():
    def load(name):
        with open(os.path.join(FIX, name)) as fh:
            return json.load(fh)
    return (load("cards.json"), load("companies.json"),
            load("build-report.json"), load("first-seen.json"),
            load("descriptions.json"))


def write_json(path, payload):
    with open(path, "w") as fh:
        json.dump(payload, fh, separators=(",", ":"), ensure_ascii=False)


def new_counters():
    return {
        "dept_co": collections.Counter(),
        "dept_roles": collections.Counter(),
        "place_co": collections.Counter(),
        "place_roles": collections.Counter(),
        "other_titles": collections.Counter(),
        "visa": collections.Counter(),
        "desc": collections.Counter(),
        "roles": 0,
    }


def build_index(cards, full, descriptions, counters):
    """One record per company for the fold, plus one role file per company."""
    by_slug = {c["slug"]: c for c in full["companies"]}
    index = []
    for card in sorted(cards, key=lambda c: (-c["roles_open"], c["name"].lower())):
        slug = card["slug"]
        company = by_slug.get(slug) or {}
        rows, dept_counts, place_counts, pairs = fold_roles(
            company.get("roles") or [], counters)
        counters["roles"] += len(rows)
        for field, n in dept_counts.items():
            counters["dept_co"][field] += 1
            counters["dept_roles"][field] += n
        for place, n in place_counts.items():
            counters["place_co"][place] += 1
            counters["place_roles"][place] += n

        g = gate(card)
        g["cap"] = gate_caption(g, card["roles_open"], dept_counts, place_counts)
        desc = describe(card["name"], descriptions)
        counters["desc"][desc["p"] if desc else "absent"] += 1
        record = {
            "s": slug,
            "n": card["name"],
            "r": card["roles_open"],
            "g": g,
            "d": dict(dept_counts),
            "p": dict(place_counts),
            "x": [[d, p, n] for (d, p), n in pairs.items()],
            "vy": sum(1 for row in rows if row["v"] == "yes"),
            "vn": sum(1 for row in rows if row["v"] == "no"),
        }
        if desc:
            record["w"] = desc
        index.append(record)
        write_json(os.path.join(ROLES_OUT, slug + ".json"),
                   {"s": slug, "n": card["name"], "roles": rows})
    return index


# Four of the eleven funnel numbers are not in build-report.json. They are the
# corpus-level counts quoted in PRODUCT-1 §2, and the panel marks them as
# quoted rather than counted — a's graft 8, and the honest thing to do when two
# provenances sit in one ladder. They reconcile exactly with corpus_size:
# 10125 - 6895 - 109 - 196 = 2925.
QUOTED = ("read", "not_qualified", "not_software", "ambiguous")


def build_funnel(report):
    """The ladder from 10,125 to 789."""
    counts = report["counts"]
    return {
        "read": 10125,
        "not_qualified": 6895,
        "not_software": 109,
        "ambiguous": 196,
        "qualified": report["corpus_size"],
        "no_board": counts["slug-unresolved"],
        "boards_read": report["checked"],
        "unchecked": counts["slug-unresolved"],
        "nothing_open": counts["no-located-roles"],
        "wrong_board": counts["another-companys-board"],
        "empty": counts["empty-board-unverified"],
        "listed": counts["listed"],
        "quoted": list(QUOTED),
    }


def build_meta(sources, index, counters, menus):
    cards, full, report, first_seen = sources[:4]
    dept_menu, place_menu = menus
    yc_cards = [c for c in index if c["g"]["kind"] == "yc"]
    visa = counters["visa"]
    desc = counters["desc"]
    return {
        "desc": {"checked": desc["checked"], "unchecked": desc["unchecked"],
                 "board": desc["board"], "absent": desc["absent"],
                 "written": len(index) - desc["absent"]},
        "residue": {"roles": counters["dept_roles"]["other"],
                    "companies": counters["dept_co"]["other"],
                    "places": counters["place_roles"]["elsewhere"],
                    "place_companies": counters["place_co"]["elsewhere"]},
        "snapshot": full["snapshot"],
        "companies": len(index),
        "roles": counters["roles"],
        "roles_open_sum": sum(c["roles_open"] for c in cards),
        "giants": sum(1 for c in cards if c["roles_open"] >= 100),
        "funnel": build_funnel(report),
        "gates": dict(collections.Counter(c["g"]["who"] for c in index)),
        "yc": {
            "n": len(yc_cards),
            "active": sum(1 for c in yc_cards if c["g"]["status"] == "Active"),
            "not_active": sum(1 for c in yc_cards if c["g"]["status"] != "Active"),
            "top": sum(1 for c in yc_cards if c["g"]["top"]),
        },
        "amounts": sum(1 for c in cards if c["amount"] is not None),
        "no_amount": sum(1 for c in cards if c["amount"] is None),
        "visa": {"yes": visa["yes"], "no": visa["no"], "unknown": visa["unknown"]},
        "first_seen": {"dated": len(first_seen["dates"]),
                       "observed": len(first_seen["observed"])},
        "depts": dept_menu,
        "places": place_menu,
        "dept_labels": DEPT_LABEL,
        "place_labels": PLACE_LABEL,
    }


HEAD_META_KEYS = ("snapshot", "companies", "roles", "roles_open_sum", "giants",
                  "funnel", "gates", "no_amount", "first_seen", "yc", "visa",
                  "desc", "residue")
START_PAIRS = (("eng", "sfbay"), ("eng", "remote"), ("sales", "nyc"))


def build_head(index, meta, menus):
    """The first screenful.

    It must be able to state the true unfiltered counts and name the set-aside
    giants before index.json lands, or the first second of the page tells the
    reader something that is not so.
    """
    dept_menu, place_menu = menus
    starts = []
    for field, place in START_PAIRS:
        matched = sum(
            1 for c in index
            if c["r"] < 100 and any(x[0] == field and x[1] == place for x in c["x"])
        )
        starts.append([field, place, matched])
    return {
        "meta": {key: meta[key] for key in HEAD_META_KEYS},
        "depts": dept_menu,
        "places": place_menu,
        "dept_labels": DEPT_LABEL,
        "place_labels": PLACE_LABEL,
        "giants_list": [[c["n"], c["r"], c["s"]] for c in index if c["r"] >= 100],
        "starts": starts,
        "companies": [c for c in index if c["r"] < 100][:14],
    }


# ------------------------------------------------------------- the fold, as HTML
# b's fastest paint came from having the cards in the document before any script
# ran. These functions are the Python half of that; page.html's makeCard is the
# JavaScript half, and qa/crosscheck.mjs asserts the two produce the same text
# for the same company. Every string either renderer prints comes off the
# record, so the only thing that can drift is structure — which is what the
# cross-check reads.

# "somewhere not in this list", "their board did not say where" and the Bay Area
# union are true counts that stay on the record; none of them may take a slot on
# the card from a place a reader could travel to.
VAGUE = ("elsewhere", "unstated", "other")


def top_pairs(obj, limit, hi=()):
    """The n most-populated buckets, vague ones last, highlights pulled forward."""
    keys = sorted(obj, key=lambda k: (1 if k in VAGUE else 0, -obj[k], k))
    top = [(k, obj[k]) for k in keys[:limit]]
    for key in hi:
        if key in obj and key not in dict(top):
            top = [(key, obj[key])] + top[:limit - 1]
    return top, max(0, len(keys) - limit)


def esc(text):
    return html.escape(str(text), quote=True)


def _facts_line(label, obj, labels, limit, hi=()):
    top, rest = top_pairs(obj, limit, hi)
    if not top:
        return ""
    out = [f'<span class="lbl">{esc(label)}</span>']
    for i, (key, count) in enumerate(top):
        cls = ' class="hit"' if key in hi else ""
        sep = " · " if i else ""
        out.append(f'<span{cls}>{esc(sep + labels[key])} '
                   f'<b>{count:,}</b></span>')
    if rest:
        out.append(f'<span> · and <b>{rest:,}</b> more</span>')
    return '<div class="row">' + "".join(out) + "</div>"


def _wline(key, value, cls=""):
    """One keyed row of the description slot. The value is a bare text node
    beside its key — an anonymous grid item — so the sentence and the dated
    provenance under it stay inside one scope."""
    cls = (" " + cls) if cls else ""
    return f'<div class="wl{cls}"><span class="wk">{esc(key)}</span>{esc(value)}</div>'


def _says_html(c, meta):
    """WHAT / FOR WHOM / WHY THEM, or the honest absence of them, in one slot
    that keeps the same anatomy either way."""
    desc = c.get("w")
    if not desc:
        return ('<div class="says none">' +
                _wline("not yet read",
                       "Not written up yet — below is only what "
                       f'{c["g"]["who"]} and their own board state.') +
                '<div class="prov">the backfill job is scripts/describe.py</div>'
                "</div>")
    prov = PROVENANCE[desc["p"]] + " · " + pretty_date(meta["snapshot"])
    return (
        '<div class="says">'
        + _wline("what", desc["w"], "what")
        + _wline("for whom", desc["f"])
        + _wline("why them", desc["y"])
        + f'<div class="prov">{esc(prov)}</div>'
        + "</div>")


def _chips_html(g):
    out = ""
    if g["kind"] == "yc" and g.get("status") and g["status"] != "Active":
        # The fact and its source, and nothing either way about what it means.
        out += (f'<a class="slot ink" href="{esc(g["url"])}" target="_blank" '
                f'rel="noopener noreferrer">{esc(g["status"])}, per YC ↗</a>')
    if g["kind"] == "yc" and g.get("top"):
        out += (f'<a class="slot ink" href="{esc(g["url"])}" target="_blank" '
                'rel="noopener noreferrer">on YC’s own Top Company list ↗</a>')
    return out


def card_html(c, meta):
    """One collapsed card in the unnarrowed default state."""
    g = c["g"]
    facts = _facts_line("fields", c["d"], meta["dept_labels"], 4)
    places = {k: v for k, v in c["p"].items() if k != "sfbay"}
    facts += _facts_line("places", places, meta["place_labels"], 3)
    if c["vy"] or c["vn"]:
        bits = []
        if c["vy"]:
            bits.append(f'<b>{c["vy"]:,}</b> ' +
                        ("role says" if c["vy"] == 1 else "roles say") +
                        " they will hire from abroad")
        if c["vn"]:
            bits.append(f'<b>{c["vn"]:,}</b> ' +
                        ("says" if c["vn"] == 1 else "say") + " they will not")
        facts += ('<div class="row"><span class="lbl">visa</span><span>' +
                  " · ".join(bits) + "</span></div>")
    label = f'{c["r"]:,} ' + ("role" if c["r"] == 1 else "roles")
    unit = "role" if c["r"] == 1 else "roles"
    return (
        f'<div class="card" id="c-{esc(c["s"])}">'
        '<div class="cbody">'
        f'<div class="chead"><h2 class="cname">{esc(c["n"])}</h2>{_chips_html(g)}</div>'
        f'{_says_html(c, meta)}'
        f'<div class="gate"><a class="rcpt" href="{esc(g["url"])}" target="_blank" '
        f'rel="noopener noreferrer">{esc(g["line"])}<span class="arw">↗</span></a>'
        f'<span class="aside">{esc(g["cap"])}</span></div>'
        f'<div class="facts">{facts}</div>'
        "</div>"
        '<div class="cside">'
        f'<div class="copen"><b>{c["r"]:,}</b> {unit} open</div>'
        '<div class="act">'
        '<button class="keep">♢ keep</button>'
        f'<button class="open" data-slug="{esc(c["s"])}">{label}  →</button>'
        "</div></div></div>")


# The page's own stopwatch, stamped by the browser after the first card has
# actually been laid out — so every measurement of this page reads the page's
# own number instead of a poller's.
STAMP = ('<script>requestAnimationFrame(function(){requestAnimationFrame('
         'function(){window.__firstCardPainted=performance.now()})})</script>')


def render_fold(head, meta):
    cards = [card_html(c, meta) for c in head["companies"]]
    if not cards:
        return ""
    return cards[0] + STAMP + "".join(cards[1:])


def render_page(head, meta):
    """page.html is the source; index.html is page.html with the first screenful
    inlined — as JSON for the script and as HTML for the eye — so first paint
    costs exactly one request and does not wait for a script to run."""
    payload = json.dumps(head, separators=(",", ":"), ensure_ascii=False)
    with open(os.path.join(HERE, "page.html")) as fh:
        template = fh.read()
    for marker in ("__HEAD_JSON__", "__FOLD_HTML__", "__SNAPDATE__"):
        if marker not in template:
            raise SystemExit(f"page.html has no {marker} marker")
    out = template.replace("__FOLD_HTML__", render_fold(head, meta))
    out = out.replace("__SNAPDATE__", pretty_date(meta["snapshot"]))
    out = out.replace("__HEAD_JSON__", payload.replace("</", "<\\/"))
    with open(os.path.join(HERE, "index.html"), "w") as fh:
        fh.write(out)


def kb(path):
    return os.path.getsize(path) / 1024.0


def report_sizes(index, head, counters, place_menu):
    shards = os.listdir(ROLES_OUT)
    shard_kb = sum(kb(os.path.join(ROLES_OUT, name)) for name in shards)
    other = counters["dept_roles"]["other"]
    visa = counters["visa"]
    print(f"index.html  {kb(os.path.join(HERE, 'index.html')):6.1f} KB")
    print(f"index.json  {kb(os.path.join(OUT, 'index.json')):6.1f} KB   "
          f"{len(index)} companies")
    print(f"head.json   {kb(os.path.join(OUT, 'head.json')):6.1f} KB   "
          f"{len(head['companies'])} companies")
    print(f"roles/      {shard_kb:6.1f} KB   {len(shards)} files")
    print(f"roles total {counters['roles']}   dept 'other' {other} "
          f"({100.0 * other / counters['roles']:.1f}%)")
    print(f"visa yes {visa['yes']} no {visa['no']} unknown {visa['unknown']}")
    d = counters["desc"]
    print(f"described  {d['checked'] + d['unchecked'] + d['board']} "
          f"(checked {d['checked']}, unchecked {d['unchecked']}, "
          f"off their board {d['board']})   not written up {d['absent']}")
    print("\ntop unbucketed:")
    for title, n in counters["other_titles"].most_common(25):
        print(f"   {n:4d}  {title[:90]}")
    print(f"\nplaces in menu: {len(place_menu)}")
    for place in place_menu[:8]:
        print(f"   {place['l']:<34} {place['c']:4d} companies {place['r']:5d} roles")


def main():
    os.makedirs(ROLES_OUT, exist_ok=True)
    sources = read_fixture()
    cards, full, descriptions = sources[0], sources[1], sources[4]
    counters = new_counters()
    index = build_index(cards, full, descriptions, counters)
    menus = build_menus(counters)
    meta = build_meta(sources, index, counters, menus)
    head = build_head(index, meta, menus)

    write_json(os.path.join(OUT, "index.json"), {"meta": meta, "companies": index})
    write_json(os.path.join(OUT, "head.json"), head)
    render_page(head, meta)
    report_sizes(index, head, counters, menus[1])


if __name__ == "__main__":
    main()
