#!/usr/bin/env python3
"""r05-c build step — "the sitting".

The taxonomy below (departments, places, gates) is r04-c's, taken whole because
the round-4 verdict said it had the least residue of the three and PRODUCT-1
§7.1 says the vocabulary must stop being rewritten. What is new here is what
the round-5 brief asks for:

  1. Every company carries a self-description. 371 of 789 have one in
     descriptions.json — WHAT / FOR WHOM / WHY THEM, AI-written, 272 of them
     checked against the company's own site. The other 418 carry, instead, the
     headings their own job board files roles under. Two different voices, and
     the card says which one it is speaking in. Nothing is invented for the 13
     companies that have neither.
  2. Status is a fact with a source and no adjective. A YC batch year, a YC
     status string, and the receipt. No colour, no warning, no hype.
  3. Two orders, both from stated numbers: matching roles (PRODUCT-1's
     default) and the pair "staff YC lists" / "roles their board lists", which
     is the only hiring-intensity signal in the corpus with two named sources.

Reads design/fixture-v2/{cards,companies,descriptions,build-report,
first-seen}.json; writes an index of all 789, a first-screenful head inlined
into index.html, and one role shard per company.

Nothing here is hand-entered. Every number in the output is counted from the
fixture. The only authored content is the *mapping* from raw strings to
buckets, which is a vocabulary, not a fact.

    python3 build.py
"""

import collections
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
    ("sf", "San Francisco / Bay Area", [
        r"san francisco", r"\bsf\b", r"bay area", r"sunnyvale", r"mountain view",
        r"palo alto", r"san mateo", r"menlo park", r"redwood city", r"santa clara",
        r"san jose", r"oakland", r"berkeley", r"cupertino", r"burlingame",
        r"foster city", r"south san francisco", r"emeryville",
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
    """Y Combinator's own row, restated without an adjective.

    `status` is YC's word, printed as YC's word. Round 5 settles this: a
    company that went public is not demoted, warned about, or celebrated here.
    "Public — per Y Combinator" and "Active — per Y Combinator" are the same
    grammar, the same colour, and the same link.
    """
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


# -------------------------------------------------------------------- the sentence

def board_words(roles):
    """The headings a company's own board files its open roles under.

    This is the honest substitute for a description the build has not written:
    not the page's guess at what the company does, but the company's own filing
    cabinet, quoted. Ordered by how many roles sit under each. No heading is
    dropped for being uninformative — a board whose only word is "Engineering"
    is a thin fact, and a thin fact is still not a blank.
    """
    counts = collections.Counter()
    for role in roles:
        raw = (role.get("department") or "").strip()
        if raw:
            counts[raw] += 1
    return [[word, n] for word, n in counts.most_common(6)]


def describe(card, company, descriptions):
    """What the company IS, in whichever voice the build can honestly use.

    Three outcomes, and the card renders each one differently:

      "ours"   371 companies — WHAT / FOR WHOM / WHY THEM, written by an AI
               from the company's own site, `ck` true for the 272 that were
               then checked against that site. The page's voice.
      "theirs" 405 of the remaining 418 — the headings their own board uses.
               Their voice, quoted, never paraphrased.
      "none"   13 companies whose board files roles under no heading at all.
               A stated silence. Nothing is composed to fill it.
    """
    got = descriptions.get(card["name"])
    if got and got.get("what"):
        return {
            "v": "ours",
            "w": got["what"],
            "f": got.get("for_whom"),
            "y": got.get("why_them"),
            "ck": bool(got.get("checked")),
        }
    words = board_words(company.get("roles") or [])
    if words:
        return {"v": "theirs", "bw": words}
    return {"v": "none"}


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
        rows.append({
            "t": role.get("title"),
            "u": role.get("url"),
            "l": ", ".join((role.get("places") or role.get("locations") or [])[:3]),
            "d": field,
            "p": places,
            "w": workplace if workplace in ("remote", "hybrid", "onsite") else None,
            "v": stated,
        })
    return rows, dept_counts, place_counts, pairs


# ---------------------------------------------------------------------- the menus

PLACE_GROUPS = [
    ("The big four", {"remote", "sf", "nyc", "london"}),
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
        "voice": collections.Counter(),
        "roles": 0,
    }


def build_index(cards, full, counters, descriptions):
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

        said = describe(card, company, descriptions)
        counters["voice"][said["v"]] += 1
        if said["v"] == "ours":
            counters["voice"]["checked" if said["ck"] else "unchecked"] += 1
        record = {
            "s": slug,
            "n": card["name"],
            "r": card["roles_open"],
            "g": gate(card),
            "say": said,
            "d": dict(dept_counts),
            "p": dict(place_counts),
            "x": [[d, p, n] for (d, p), n in pairs.items()],
            "vy": sum(1 for row in rows if row["v"] == "yes"),
            "vn": sum(1 for row in rows if row["v"] == "no"),
        }
        # The staff/roles pair, kept as two separately-sourced numbers and
        # never divided into a score on the card. The ratio exists only as a
        # sort key, and the sort says so in words above the deal.
        team = record["g"].get("team")
        if team:
            record["ts"] = team
            record["hi"] = round(card["roles_open"] / team, 4)
        index.append(record)
        write_json(os.path.join(ROLES_OUT, slug + ".json"),
                   {"s": slug, "n": card["name"], "roles": rows})
    return index


def build_funnel(report):
    """The ladder from 10,125 to 789.

    corpus_size / checked / counts come from build-report.json; `read` and
    `not_qualified` are the corpus-level counts quoted in PRODUCT-1 §2, and they
    reconcile exactly with corpus_size: 10125 - 6895 - 109 - 196 = 2925.
    """
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
    }


def build_meta(sources, index, counters, menus):
    cards, full, report, first_seen, _descriptions = sources
    dept_menu, place_menu = menus
    yc_cards = [c for c in index if c["g"]["kind"] == "yc"]
    visa = counters["visa"]
    voice = counters["voice"]
    status = collections.Counter(
        c["g"]["status"] for c in yc_cards if c["g"].get("status"))
    return {
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
        "status": dict(status),
        "voice": {
            "ours": voice["ours"], "checked": voice["checked"],
            "unchecked": voice["unchecked"], "theirs": voice["theirs"],
            "none": voice["none"],
        },
        "intensity": {
            "n": sum(1 for c in index if "hi" in c),
            "small": sum(1 for c in index if c.get("ts", 99) < 10),
        },
        # the size of the view the page opens on, so the first paint can state
        # its own cut honestly before index.json has landed
        "default_cut": sum(1 for c in index if c["r"] < 100),
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
                  "funnel", "gates", "amounts", "no_amount", "first_seen", "yc",
                  "visa", "voice", "status", "intensity", "default_cut")
START_PAIRS = (("eng", "sf"), ("eng", "remote"), ("product", "nyc"))


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


def render_page(head):
    """page.html is the source; index.html is page.html with the first screenful
    inlined, so first paint costs exactly one request."""
    payload = json.dumps(head, separators=(",", ":"), ensure_ascii=False)
    with open(os.path.join(HERE, "page.html")) as fh:
        template = fh.read()
    if "__HEAD_JSON__" not in template:
        raise SystemExit("page.html has no __HEAD_JSON__ marker")
    with open(os.path.join(HERE, "index.html"), "w") as fh:
        fh.write(template.replace("__HEAD_JSON__", payload.replace("</", "<\\/")))


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
    voice = counters["voice"]
    print(f"voice: ours {voice['ours']} ({voice['checked']} checked) · "
          f"theirs {voice['theirs']} · stated silence {voice['none']}")
    print("\ntop unbucketed:")
    for title, n in counters["other_titles"].most_common(25):
        print(f"   {n:4d}  {title[:90]}")
    print(f"\nplaces in menu: {len(place_menu)}")
    for place in place_menu[:8]:
        print(f"   {place['l']:<34} {place['c']:4d} companies {place['r']:5d} roles")


def main():
    sources = read_fixture()
    cards, full, descriptions = sources[0], sources[1], sources[4]
    counters = new_counters()
    index = build_index(cards, full, counters, descriptions)
    menus = build_menus(counters)
    meta = build_meta(sources, index, counters, menus)
    head = build_head(index, meta, menus)

    write_json(os.path.join(OUT, "index.json"), {"meta": meta, "companies": index})
    write_json(os.path.join(OUT, "head.json"), head)
    render_page(head)
    report_sizes(index, head, counters, menus[1])


if __name__ == "__main__":
    main()
