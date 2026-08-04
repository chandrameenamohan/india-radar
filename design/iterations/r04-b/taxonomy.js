// taxonomy.js — the two normalisations PRODUCT-1 §4 says the build owes the page.
//
// fixture-v2 ships `dept_norm` (2,300 distinct strings) and canonical `places`
// (1,672 distinct strings). Neither is the ~10 departments / ~30 cities the one
// screen needs. Until the build does it, the page does it — deterministically,
// in one file, shared verbatim by the page, the worker and the seed generator so
// the three can never disagree.
//
// Rules are ordered. First match wins. Nothing is dropped: whatever no rule
// claims lands in "Other", which is a real bucket you can select, not a bin.

export const FIELDS = [
  ['engineering',  'Engineering'],
  ['product',      'Product'],
  ['design',       'Design'],
  ['data',         'Data & Research'],
  ['sales',        'Sales & GTM'],
  ['marketing',    'Marketing & Growth'],
  ['customer',     'Customer'],
  ['operations',   'Operations'],
  ['finance',      'Finance & Legal'],
  ['people',       'People'],
  ['security',     'Security & IT'],
  ['clinical',     'Clinical & Care'],
  ['other',        'Other'],
];

export const FIELD_LABEL = Object.fromEntries(FIELDS);

// Ordered. Tested against every one of the 2,300 dept_norm strings in the fixture.
const FIELD_RULES = [
  [/security|trust\s*&?\s*safety|information technology|\bit\b|infosec|privacy/i, 'security'],
  [/clinical|medical|nursing|nurse|physician|patient care|pharmac|therap|behavio(u)?ral health|veterin/i, 'clinical'],
  [/people|talent|recruit|human resources|\bhr\b|hiring|workplace experience|culture/i, 'people'],
  [/financ|account|controller|payroll|\btax\b|audit|legal|counsel|complian|\brisk\b|regulat|treasur/i, 'finance'],
  [/design|\bux\b|\bui\b|creative|brand studio|user research/i, 'design'],
  [/data|research|science|scientist|analytic|insight|statistic|bioinformat/i, 'data'],
  [/market|growth|content|communicat|\bpr\b|brand|demand gen|community|social/i, 'marketing'],
  [/customer|support|success|client service|professional services|implementation|onboarding|solutions architect|technical account|experience|\bsolutions?\b|consult|\bdelivery\b|deployment|\bservices\b/i, 'customer'],
  [/sales|gtm|go.?to.?market|revenue|account exec|account manage|business development|\bbd\b|partnership|commercial|field|enterprise|solutions engineer|pre.?sales|sdr|\bbdr\b|channel/i, 'sales'],
  [/engineer|software|technolog|\btech\b|infrastructure|platform|backend|back.?end|frontend|front.?end|full.?stack|devops|\bsre\b|reliability|mobile|android|\bios\b|hardware|firmware|electrical|mechanical|robotic|\bml\b|machine learning|applied ai|\bai\b|r&d|\brnd\b|quality|\bqa\b|test|architecture|developer|systems|network|cloud|web\b/i, 'engineering'],
  [/product manage|\bproduct\b|\bpm\b/i, 'product'],
  [/operation|\bops\b|supply|logistic|manufactur|production|facilit|program|project|strateg|business|admin|general|g&a|corporate|fulfil|warehouse|driver|field service|installation|construction|energy|policy|government|sustainab|real estate|procurement|vendor/i, 'operations'],
];

const FIELD_CACHE = new Map();

export function fieldOf(deptNorm) {
  const d = (deptNorm || '').trim();
  if (!d) return 'other';
  const hit = FIELD_CACHE.get(d);
  if (hit) return hit;
  let f = 'other';
  for (const [re, key] of FIELD_RULES) { if (re.test(d)) { f = key; break; } }
  FIELD_CACHE.set(d, f);
  return f;
}

// ── places ────────────────────────────────────────────────────────────────────
// The fixture's `places` are already canonical-ish; what is left is prefixes
// ("Hybrid - San Francisco"), suffixes ("San Francisco HQ") and a short alias
// list. "Remote" is kept as a place because it is the largest one in the corpus
// (4,659 role-locations) and a seeker choosing it is choosing something real.

const PLACE_ALIASES = {
  'nyc': 'New York', 'new york city': 'New York', 'ny': 'New York',
  'brooklyn': 'New York', 'manhattan': 'New York',
  'sf': 'San Francisco', 'san francisco bay area': 'San Francisco',
  'bay area': 'San Francisco', 'sf bay area': 'San Francisco',
  'bangalore': 'Bengaluru', 'bengaluru / bangalore': 'Bengaluru',
  'washington dc': 'Washington DC', 'washington d.c.': 'Washington DC',
  'washington, d.c.': 'Washington DC', 'washington': 'Washington DC',
  'dc': 'Washington DC',
  'sao paulo': 'São Paulo', 'são paulo': 'São Paulo',
  'bengaluru': 'Bengaluru',
  'usa': 'United States', 'us': 'United States', 'united states of america': 'United States',
  'uk': 'United Kingdom',
  'anywhere': 'Remote', 'remote (us)': 'Remote', 'fully remote': 'Remote',
  'tel aviv-yafo': 'Tel Aviv', 'tel aviv': 'Tel Aviv',
  'gurgaon': 'Gurugram', 'bombay': 'Mumbai',
  'saint louis': 'St. Louis', 'st louis': 'St. Louis',
};

const PLACE_CACHE = new Map();

export function placeOf(raw) {
  const s0 = (raw || '').trim();
  if (!s0) return null;
  const hit = PLACE_CACHE.get(s0);
  if (hit !== undefined) return hit;
  let s = s0
    .replace(/^(hybrid|remote|onsite|on-site|in.?office|flexible)\s*[-–—:|]\s*/i, '')
    .replace(/\s*[-–—]\s*(hybrid|remote|onsite|on-site|in.?office)\s*$/i, '')
    .replace(/\s*\((hybrid|remote|onsite|on-site|optional|preferred)\)\s*$/i, '')
    .replace(/\s+(hq|headquarters|office|area|metro|region)$/i, '')
    .trim();
  const key = s.toLowerCase();
  // "seoul" and "Seoul" are one place. Title-case a wholly lower-case ASCII
  // string so the two merge; anything with its own capitals or script is left
  // exactly as the board wrote it, because changing it would be translating.
  if (!PLACE_ALIASES[key] && /^[a-z][a-z .'-]*$/.test(s)) {
    s = s.replace(/(^|[ .'-])([a-z])/g, (m, a, b) => a + b.toUpperCase());
  }
  const out = PLACE_ALIASES[key] || s || null;
  PLACE_CACHE.set(s0, out);
  return out;
}

// A role can sit in several places; count it once per canonical place.
export function placesOf(role) {
  const src = (role.places && role.places.length) ? role.places : (role.locations || []);
  const out = [];
  for (const p of src) {
    const c = placeOf(p);
    if (c && !out.includes(c)) out.push(c);
  }
  return out;
}

// ── the gate line ─────────────────────────────────────────────────────────────
// One sentence per company, read off `source_url` + `qualified_by` + `amount`.
// Never composed, never inferred: the host of the URL is the gatekeeper.

export const GATES = {
  'www.ycombinator.com': 'yc',
  'www.cbinsights.com':  'cbi',
  'www.sec.gov':         'sec',
  'www.forbes.com':      'forbes',
  'techcrunch.com':      'techcrunch',
  'www.finsmes.com':     'finsmes',
};

export function gateOf(card) {
  const u = card.source_url || '';
  let host = '';
  try { host = new URL(u).host; } catch (e) { host = ''; }
  return GATES[host] || 'unknown';
}

export const GATE_NAME = {
  yc: 'Y Combinator', cbi: 'CB Insights', sec: 'SEC EDGAR',
  forbes: 'Forbes', techcrunch: 'TechCrunch', finsmes: 'FinSMEs',
  unknown: 'the build',
};

const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

export function prettyDate(iso) {
  if (!iso) return '';
  const [y, m, d] = iso.split('-').map(Number);
  if (!y || !m || !d) return iso;
  return `${MONTHS[m - 1]} ${d}, ${y}`;
}

export function money(amount, currency) {
  if (amount == null) return '';
  const sym = currency === 'USD' ? '$' : (currency ? currency + ' ' : '');
  if (amount >= 1e9) return sym + (amount / 1e9).toFixed(amount % 1e9 === 0 ? 0 : 2) + 'B';
  if (amount >= 1e6) return sym + (amount / 1e6).toFixed(amount % 1e6 === 0 ? 0 : 1) + 'M';
  return sym + amount.toLocaleString('en-US');
}

// The gate sentence, as text + the receipt it links to. Every word of it is a
// field. A company with no amount says nothing about an amount — that is the
// whole of M5 on this line.
export function gateLine(card) {
  const g = gateOf(card);
  const yc = card.yc;
  if (g === 'yc' && yc && yc.batch) return `Y Combinator, ${yc.batch}`;
  if (g === 'yc') return 'Y Combinator company';
  if (g === 'sec' && card.amount != null && card.date) {
    return `Filed a Form D for ${money(card.amount, card.currency)} on ${prettyDate(card.date)}`;
  }
  if (g === 'sec') return 'Filed a Form D with the SEC';
  if (g === 'cbi') return 'Listed by CB Insights';
  if (g === 'forbes') return 'On a Forbes list';
  if (g === 'techcrunch' && card.amount != null && card.date) {
    return `TechCrunch, ${prettyDate(card.date)}: a ${money(card.amount, card.currency)} round`;
  }
  if (g === 'techcrunch') return 'Covered by TechCrunch';
  if (g === 'finsmes' && card.amount != null && card.date) {
    return `FinSMEs, ${prettyDate(card.date)}: a ${money(card.amount, card.currency)} round`;
  }
  if (g === 'finsmes') return 'Reported by FinSMEs';
  return 'Admitted by the build';
}

export const GIANT_FLOOR = 100; // "hide the giants" — open roles >= 100
