"""The department and place vocabulary, taken verbatim from r04-c's build.py.

Round 5's brief: "pick ONE of round 4's three (r04-c's had the least residue)
rather than writing a fifth." This file is that pick, copied unchanged so the
diff against r04-c is empty and the residue it confesses is the same residue.
It is still a renderer's stopgap; PRODUCT-1 7.1 wants it in the world build.
"""

import re

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
