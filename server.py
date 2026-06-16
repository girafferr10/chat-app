import asyncio
import hashlib
import json
import os
import secrets
import re
import random
import string
import uuid
import aiohttp
from aiohttp import web
import time as _time
from datetime import datetime, timedelta

from games import tictactoe, snake, memory, blackjack, blackjack_multi, minesweeper, solitaire, checkers, hangman, war, crazy_eights, twenty_fortyeight, genetic_cars, garlic_phone

try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    HAS_ASYNCPG = False

connected = {}       # ws -> {"username": str, "ws": ws}
banned_users = set() # set of banned usernames
admin_ws = None      # owner websocket connection
msg_reactions = {}   # msg_id -> {emoji: set(usernames)}
staff_connected = {} # staff ws -> {"username": str, "admin_key": str}
admin_connections = {}  # ws -> {"name": str, "key": str}
dm_store = {}        # (sorted_user_a, sorted_user_b) -> [{"sender":..., "recipient":..., "text":..., "ts":...}]

bj_rooms = {}
gc_store = {}
gc_counter = 0
garlic_rooms = {}

admin_accounts = {}  # key -> {"name": str, "created": str}
suggestions = []     # [{"id": int, "from": str, "text": str, "timestamp": str, "read": bool}]
suggestion_counter = [0]
owner_mailbox = []   # [{"id": int, "type": str, "text": str, "timestamp": str, "read": bool}]
owner_mailbox_counter = 0

LOG_FILE = "chat_logs.json"
chat_logs = []
log_id_counter = 0

try:
    from zoneinfo import ZoneInfo
    MTN_TZ = ZoneInfo("America/Denver")
except ImportError:
    import pytz
    MTN_TZ = pytz.timezone("America/Denver")


def mtn_now():
    return datetime.now(MTN_TZ)


def load_logs():
    global chat_logs, log_id_counter
    try:
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                chat_logs = json.load(f)
                for entry in chat_logs:
                    if "id" not in entry:
                        log_id_counter += 1
                        entry["id"] = log_id_counter
                if chat_logs:
                    log_id_counter = max(e.get("id", 0) for e in chat_logs)
    except Exception:
        chat_logs = []


def save_logs():
    try:
        with open(LOG_FILE, "w") as f:
            json.dump(chat_logs, f)
    except Exception as e:
        print(f"[LOG] Error saving logs: {e}")


def add_log(log_type, **kwargs):
    global log_id_counter
    log_id_counter += 1
    entry = {
        "id": log_id_counter,
        "type": log_type,
        "timestamp": mtn_now().strftime("%Y-%m-%d %H:%M:%S MT"),
        **kwargs
    }
    chat_logs.append(entry)
    save_logs()


def delete_log(log_id):
    global chat_logs
    chat_logs = [e for e in chat_logs if e.get("id") != log_id]
    save_logs()


def dm_key(a, b):
    return tuple(sorted([a, b]))

_raw_secret = os.environ.get("SESSION_SECRET", secrets.token_urlsafe(16))
OWNER_TOKEN = hashlib.sha256(_raw_secret.encode()).hexdigest()[:24]

db_pool = None
CURRENT_VERSION = "2.7"
CHANGELOG_NOTES = (
    "<b>What's new in v2.7</b><br><br>"
    "&#x2022; <b>Balance System</b> — Every player starts with $1,000; registered users keep it forever across sessions<br>"
    "&#x2022; <b>Shop</b> — 50+ items across 8 categories: Nameplates, Fonts, Avatar Rings, Profile FX, Themes, Titles, Chat Bubbles, Message Effects<br>"
    "&#x2022; <b>Savings Plans</b> — Create personal savings goals with deposit/withdraw and color-coded progress bars<br>"
    "&#x2022; <b>Gambling</b> — 5 casino games: Coin Flip, Dice Duel, Slot Machine, Roulette, Hi-Lo<br>"
    "&#x2022; <b>Idle Game</b> — Earn passive income, buy 11 upgrades from Intern to Space Station<br>"
    "&#x2022; <b>Browser VPN-off fix</b> — Shows a helpful overlay instead of cryptic iframe errors when VPN is off<br>"
    "&#x2022; <b>Page title auto-detection</b> — Browser tabs update their label to the loaded page title<br>"
    "&#x2022; <b>Browser keyboard shortcuts</b> — Ctrl+T (new tab), Ctrl+W (close), Ctrl+L (address bar), Ctrl+R (reload)<br>"
    "<br><b>Previously in v2.6</b><br>"
    "&#x2022; Browser UI overhaul, VPN/proxy indicator, slash command autocomplete, chat input redesign, message layout polish<br>"
    "<br><b>Previously in v2.5</b><br>"
    "&#x2022; Browser bookmarks, nav history, loading bar, home page redesign, Google\u2192DuckDuckGo redirect<br>"
    "&#x2022; Slash commands: /me /roll /flip /8ball /shrug /tableflip /rainbow /shout /trivia /poll<br>"
    "&#x2022; Formatting toolbar, typing indicator, collapsible sidebar, user search, Ctrl+K DM, username color<br>"
    "<br><b>Previously in v2.4</b><br>"
    "&#x2022; Bug fixes: owner login, DM clearing, fullscreen games, browser proxy; status selector, draft persistence<br>"
)

# ─── Economy: Shop catalog ───────────────────────────────────────────────────
SHOP_CATALOG = {
    # Nameplates
    "np_bronze":    {"name":"Bronze Nameplate",    "desc":"A warm bronze glow around your name",          "price":100,   "cat":"nameplate","rarity":"common",    "emoji":"\U0001F7EB"},
    "np_silver":    {"name":"Silver Nameplate",    "desc":"A cool silver shimmer around your name",       "price":250,   "cat":"nameplate","rarity":"uncommon",  "emoji":"\U0001F7E9"},
    "np_gold":      {"name":"Gold Nameplate",      "desc":"Shining gold highlights on your name",         "price":500,   "cat":"nameplate","rarity":"rare",      "emoji":"\U0001F7E8"},
    "np_diamond":   {"name":"Diamond Nameplate",   "desc":"Crystal-clear diamond sparkle",                "price":1000,  "cat":"nameplate","rarity":"epic",      "emoji":"\U0001F48E"},
    "np_rainbow":   {"name":"Rainbow Nameplate",   "desc":"Cycling rainbow gradient on your name",        "price":2000,  "cat":"nameplate","rarity":"legendary", "emoji":"\U0001F308"},
    "np_neon":      {"name":"Neon Nameplate",      "desc":"Electric neon glow around your name",          "price":1500,  "cat":"nameplate","rarity":"epic",      "emoji":"\U0001F4A1"},
    "np_galaxy":    {"name":"Galaxy Nameplate",    "desc":"Deep space cosmic aesthetic",                  "price":3000,  "cat":"nameplate","rarity":"legendary", "emoji":"\U0001F30C"},
    "np_fire":      {"name":"Fire Nameplate",      "desc":"Blazing flames licking your name",             "price":2500,  "cat":"nameplate","rarity":"legendary", "emoji":"\U0001F525"},
    "np_ice":       {"name":"Ice Nameplate",       "desc":"Frozen crystal icy effect",                    "price":2500,  "cat":"nameplate","rarity":"legendary", "emoji":"\u2744\uFE0F"},
    "np_holo":      {"name":"Holographic",         "desc":"Prismatic holographic shimmer",                "price":5000,  "cat":"nameplate","rarity":"mythic",    "emoji":"\u2728"},
    # Fonts
    "font_bold":    {"name":"Bold Text",           "desc":"Make your messages stand out in bold",         "price":150,   "cat":"font",     "rarity":"common",    "emoji":"\U0001F1E7"},
    "font_italic":  {"name":"Italic Text",         "desc":"Stylish slanted messages",                     "price":150,   "cat":"font",     "rarity":"common",    "emoji":"\U0001F4D4"},
    "font_mono":    {"name":"Monospace",           "desc":"Hacker-style fixed-width font",                "price":200,   "cat":"font",     "rarity":"uncommon",  "emoji":"\u2328\uFE0F"},
    "font_cursive": {"name":"Cursive",             "desc":"Elegant handwriting style font",               "price":350,   "cat":"font",     "rarity":"uncommon",  "emoji":"\u270D\uFE0F"},
    "font_pixel":   {"name":"Pixel Art",           "desc":"Retro 8-bit pixel font vibes",                 "price":500,   "cat":"font",     "rarity":"rare",      "emoji":"\U0001F47E"},
    "font_comic":   {"name":"Comic Sans",          "desc":"The legendary meme font, now as a flex",       "price":100,   "cat":"font",     "rarity":"common",    "emoji":"\U0001F602"},
    # Avatar Rings
    "ring_gold":    {"name":"Gold Ring",           "desc":"Luxurious gold ring around your avatar",       "price":300,   "cat":"ring",     "rarity":"uncommon",  "emoji":"\U0001F49B"},
    "ring_rainbow": {"name":"Rainbow Ring",        "desc":"Cycling rainbow ring around avatar",           "price":800,   "cat":"ring",     "rarity":"rare",      "emoji":"\U0001F308"},
    "ring_fire":    {"name":"Fire Ring",           "desc":"Blazing fire border around avatar",            "price":600,   "cat":"ring",     "rarity":"rare",      "emoji":"\U0001F525"},
    "ring_ice":     {"name":"Ice Ring",            "desc":"Frosty ice crystal border",                    "price":600,   "cat":"ring",     "rarity":"rare",      "emoji":"\u2744\uFE0F"},
    "ring_galaxy":  {"name":"Galaxy Ring",         "desc":"Swirling galaxy animation ring",               "price":1200,  "cat":"ring",     "rarity":"epic",      "emoji":"\U0001F30C"},
    "ring_neon":    {"name":"Neon Ring",           "desc":"Electric neon glow ring",                      "price":700,   "cat":"ring",     "rarity":"rare",      "emoji":"\U0001F4A1"},
    "ring_diamond": {"name":"Diamond Ring",        "desc":"Sparkling diamond border",                     "price":1000,  "cat":"ring",     "rarity":"epic",      "emoji":"\U0001F48E"},
    "ring_crown":   {"name":"Crown",               "desc":"A royal crown above your avatar",              "price":2000,  "cat":"ring",     "rarity":"legendary", "emoji":"\U0001F451"},
    "ring_star":    {"name":"Star Ring",           "desc":"Twinkling stars orbiting your avatar",         "price":500,   "cat":"ring",     "rarity":"uncommon",  "emoji":"\u2B50"},
    # Profile Effects
    "fx_sparkles":  {"name":"Sparkles",            "desc":"Sparkling particle effects on your profile",   "price":500,   "cat":"effect",   "rarity":"uncommon",  "emoji":"\u2728"},
    "fx_snow":      {"name":"Snowfall",            "desc":"Gentle snowflakes float around you",           "price":600,   "cat":"effect",   "rarity":"rare",      "emoji":"\u2744\uFE0F"},
    "fx_stars":     {"name":"Starfield",           "desc":"Infinite twinkling starfield background",      "price":800,   "cat":"effect",   "rarity":"rare",      "emoji":"\U0001F31F"},
    "fx_flames":    {"name":"Flames",              "desc":"Dancing fire frames your profile",             "price":700,   "cat":"effect",   "rarity":"rare",      "emoji":"\U0001F525"},
    "fx_lightning": {"name":"Lightning",           "desc":"Electric sparks crackle around you",           "price":1000,  "cat":"effect",   "rarity":"epic",      "emoji":"\u26A1"},
    "fx_bubbles":   {"name":"Bubbles",             "desc":"Floating soap bubbles drift up",               "price":600,   "cat":"effect",   "rarity":"rare",      "emoji":"\U0001FAE7"},
    "fx_matrix":    {"name":"Matrix Rain",         "desc":"Green code rains down your profile",           "price":1500,  "cat":"effect",   "rarity":"epic",      "emoji":"\U0001F4BB"},
    "fx_aurora":    {"name":"Northern Lights",     "desc":"Ethereal aurora waves shimmer",                "price":2000,  "cat":"effect",   "rarity":"legendary", "emoji":"\U0001F30C"},
    "fx_confetti":  {"name":"Confetti",            "desc":"Endless party confetti shower",                "price":400,   "cat":"effect",   "rarity":"uncommon",  "emoji":"\U0001F389"},
    "fx_hearts":    {"name":"Floating Hearts",     "desc":"Little hearts float up constantly",            "price":350,   "cat":"effect",   "rarity":"uncommon",  "emoji":"\U0001F495"},
    # Themes
    "th_cyberpunk": {"name":"Cyberpunk",           "desc":"Neon-on-dark cyber aesthetic",                 "price":500,   "cat":"theme",    "rarity":"uncommon",  "emoji":"\U0001F916"},
    "th_sakura":    {"name":"Sakura",              "desc":"Cherry blossom soft pink tones",               "price":400,   "cat":"theme",    "rarity":"uncommon",  "emoji":"\U0001F338"},
    "th_arctic":    {"name":"Arctic",              "desc":"Cool blue glacial tones",                      "price":450,   "cat":"theme",    "rarity":"uncommon",  "emoji":"\U0001F9CA"},
    "th_inferno":   {"name":"Inferno",             "desc":"Deep reds and volcanic oranges",               "price":550,   "cat":"theme",    "rarity":"rare",      "emoji":"\U0001F30B"},
    "th_emerald":   {"name":"Emerald City",        "desc":"Rich jewel-green tones",                       "price":400,   "cat":"theme",    "rarity":"uncommon",  "emoji":"\U0001F49A"},
    "th_royal":     {"name":"Royal Purple",        "desc":"Majestic purple and gold",                     "price":350,   "cat":"theme",    "rarity":"uncommon",  "emoji":"\U0001F7EA"},
    "th_bloodmoon": {"name":"Blood Moon",          "desc":"Deep crimson and black",                       "price":600,   "cat":"theme",    "rarity":"rare",      "emoji":"\U0001F311"},
    "th_golden":    {"name":"Golden Hour",         "desc":"Warm gold and amber sunset",                   "price":700,   "cat":"theme",    "rarity":"rare",      "emoji":"\u2728"},
    "th_space":     {"name":"Space Station",       "desc":"Deep navy, silver and stars",                  "price":800,   "cat":"theme",    "rarity":"rare",      "emoji":"\U0001F680"},
    "th_candy":     {"name":"Cotton Candy",        "desc":"Soft pastels and bubblegum",                   "price":300,   "cat":"theme",    "rarity":"common",    "emoji":"\U0001F36C"},
    "th_toxic":     {"name":"Toxic Waste",         "desc":"Acid green neon on black",                     "price":650,   "cat":"theme",    "rarity":"rare",      "emoji":"\u2622\uFE0F"},
    "th_vapor":     {"name":"Vaporwave",           "desc":"Retro purple and pink aesthetic",              "price":750,   "cat":"theme",    "rarity":"rare",      "emoji":"\U0001F4FA"},
    # Title Badges
    "title_fresh":  {"name":"Fresh",               "desc":"Keep it fresh vibes only",                     "price":250,   "cat":"title",    "rarity":"common",    "emoji":"\U0001F30A"},
    "title_elite":  {"name":"Elite",               "desc":"Elite status badge",                           "price":500,   "cat":"title",    "rarity":"uncommon",  "emoji":"\U0001F537"},
    "title_vip":    {"name":"VIP",                 "desc":"Very Important Person status",                 "price":800,   "cat":"title",    "rarity":"rare",      "emoji":"\u2B50"},
    "title_pro":    {"name":"Pro",                 "desc":"A certified pro badge",                        "price":600,   "cat":"title",    "rarity":"rare",      "emoji":"\u26A1"},
    "title_grind":  {"name":"Grinder",             "desc":"Always hustlin' badge",                        "price":700,   "cat":"title",    "rarity":"rare",      "emoji":"\u2699\uFE0F"},
    "title_boss":   {"name":"Boss",                "desc":"Ran that. Enough said.",                       "price":1000,  "cat":"title",    "rarity":"epic",      "emoji":"\U0001F60E"},
    "title_legend": {"name":"Legend",              "desc":"You are a legend badge",                       "price":1500,  "cat":"title",    "rarity":"epic",      "emoji":"\U0001F3C6"},
    "title_champ":  {"name":"Champion",            "desc":"Champion of champions",                        "price":2000,  "cat":"title",    "rarity":"legendary", "emoji":"\U0001F947"},
    "title_og":     {"name":"OG",                  "desc":"One of the true originals",                    "price":3000,  "cat":"title",    "rarity":"legendary", "emoji":"\U0001F4AF"},
    "title_goat":   {"name":"GOAT",                "desc":"Greatest of all time",                         "price":4000,  "cat":"title",    "rarity":"mythic",    "emoji":"\U0001F410"},
    "title_rich":   {"name":"Richie Rich",         "desc":"More money than they know what to do with",   "price":5000,  "cat":"title",    "rarity":"mythic",    "emoji":"\U0001F4B0"},
    # Chat Bubbles
    "bub_round":    {"name":"Rounded Bubbles",     "desc":"Pill-shaped message bubbles",                  "price":200,   "cat":"bubble",   "rarity":"common",    "emoji":"\U0001F4AC"},
    "bub_speech":   {"name":"Speech Bubbles",      "desc":"Classic comic speech bubbles",                 "price":350,   "cat":"bubble",   "rarity":"uncommon",  "emoji":"\U0001F5E8\uFE0F"},
    "bub_neon":     {"name":"Neon Outlines",       "desc":"Electric neon borders on messages",            "price":600,   "cat":"bubble",   "rarity":"rare",      "emoji":"\U0001F4A1"},
    "bub_shadow":   {"name":"Shadow Boxes",        "desc":"Deep drop shadow card style",                  "price":400,   "cat":"bubble",   "rarity":"uncommon",  "emoji":"\U0001F532"},
    "bub_glass":    {"name":"Glassmorphism",       "desc":"Frosted glass effect messages",                "price":700,   "cat":"bubble",   "rarity":"rare",      "emoji":"\U0001F9CA"},
    "bub_retro":    {"name":"Retro Terminal",      "desc":"Old-school green-on-black terminal look",      "price":500,   "cat":"bubble",   "rarity":"rare",      "emoji":"\U0001F4BB"},
    # Message Effects
    "msg_gradient": {"name":"Gradient Text",       "desc":"Your messages displayed in rainbow gradient",  "price":800,   "cat":"message",  "rarity":"rare",      "emoji":"\U0001F308"},
    "msg_glow":     {"name":"Glowing Text",        "desc":"Your text emits a soft colored glow",          "price":1000,  "cat":"message",  "rarity":"epic",      "emoji":"\u2728"},
    "msg_big":      {"name":"Big Text",            "desc":"Your messages appear slightly larger",         "price":200,   "cat":"message",  "rarity":"common",    "emoji":"\U0001F524"},
    "msg_shadow":   {"name":"Drop Shadow Text",    "desc":"Dramatic drop shadow on your text",            "price":500,   "cat":"message",  "rarity":"uncommon",  "emoji":"\U0001F532"},
    "msg_caps":     {"name":"ALL CAPS Mode",       "desc":"Everything you send is in bold caps",          "price":300,   "cat":"message",  "rarity":"common",    "emoji":"\U0001F50A"},
    "msg_wave":     {"name":"Wave Text",           "desc":"Your text undulates in an animated wave",      "price":1200,  "cat":"message",  "rarity":"epic",      "emoji":"\U0001F30A"},
}

# ─── Economy: Idle game upgrades ─────────────────────────────────────────────
IDLE_UPGRADES = [
    {"id":"click1",  "name":"Better Mouse",     "desc":"Each click earns +$1",          "emoji":"\U0001F5B1\uFE0F",  "base_price":50,       "type":"click","value":1},
    {"id":"click2",  "name":"Power Fingers",    "desc":"Each click earns +$5",          "emoji":"\U0001F4AA",         "base_price":300,      "type":"click","value":5},
    {"id":"click3",  "name":"Auto Tap",         "desc":"Each click earns +$25",         "emoji":"\U0001F916",         "base_price":2000,     "type":"click","value":25},
    {"id":"auto1",   "name":"Intern",           "desc":"+$0.5 per second",              "emoji":"\U0001F476",         "base_price":100,      "type":"cps",  "value":0.5},
    {"id":"auto2",   "name":"Employee",         "desc":"+$2 per second",               "emoji":"\U0001F468\u200D\U0001F4BC", "base_price":500, "type":"cps","value":2},
    {"id":"auto3",   "name":"Manager",          "desc":"+$10 per second",              "emoji":"\U0001F454",          "base_price":2500,     "type":"cps",  "value":10},
    {"id":"auto4",   "name":"Director",         "desc":"+$50 per second",              "emoji":"\U0001F3E2",          "base_price":15000,    "type":"cps",  "value":50},
    {"id":"auto5",   "name":"Corporation",      "desc":"+$200 per second",             "emoji":"\U0001F3D9\uFE0F",   "base_price":75000,    "type":"cps",  "value":200},
    {"id":"auto6",   "name":"Investment Fund",  "desc":"+$1,000 per second",           "emoji":"\U0001F4C8",          "base_price":400000,   "type":"cps",  "value":1000},
    {"id":"auto7",   "name":"Crypto Mine",      "desc":"+$5,000 per second",           "emoji":"\u26CF\uFE0F",        "base_price":2000000,  "type":"cps",  "value":5000},
    {"id":"auto8",   "name":"Space Station",    "desc":"+$25,000 per second",          "emoji":"\U0001F680",          "base_price":10000000, "type":"cps",  "value":25000},
]

def _calc_idle_stats(upgrades):
    """Return (click_value, cps) from an upgrades dict."""
    click_val = 1.0
    cps = 0.0
    for u in IDLE_UPGRADES:
        cnt = upgrades.get(u["id"], 0)
        if u["type"] == "click":
            click_val += u["value"] * cnt
        elif u["type"] == "cps":
            cps += u["value"] * cnt
    return click_val, cps


async def init_db():
    global db_pool
    if not HAS_ASYNCPG:
        return
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        return
    try:
        db_pool = await asyncpg.create_pool(db_url)
        async with db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(20) UNIQUE NOT NULL,
                    password_hash VARCHAR(64) NOT NULL DEFAULT '',
                    display_name VARCHAR(30) NOT NULL DEFAULT '',
                    bio TEXT DEFAULT '',
                    pfp_data TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            for col, defn in [
                ("password_hash", "VARCHAR(64) NOT NULL DEFAULT ''"),
                ("display_name",  "VARCHAR(30) NOT NULL DEFAULT ''"),
                ("bio",           "TEXT DEFAULT ''"),
                ("pfp_data",      "TEXT DEFAULT ''"),
            ]:
                try:
                    await conn.execute(f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {col} {defn}")
                except Exception:
                    pass
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token VARCHAR(64) PRIMARY KEY,
                    username VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS changelog_seen (
                    username VARCHAR(20) NOT NULL,
                    version VARCHAR(20) NOT NULL,
                    PRIMARY KEY (username, version)
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_economy (
                    username VARCHAR(20) PRIMARY KEY,
                    balance INTEGER NOT NULL DEFAULT 1000,
                    inventory JSONB NOT NULL DEFAULT '[]',
                    equipped JSONB NOT NULL DEFAULT '{}',
                    idle_money NUMERIC NOT NULL DEFAULT 0,
                    idle_upgrades JSONB NOT NULL DEFAULT '{}',
                    idle_last_collect TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS savings_plans (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(20) NOT NULL,
                    name VARCHAR(50) NOT NULL,
                    goal INTEGER NOT NULL DEFAULT 100,
                    saved INTEGER NOT NULL DEFAULT 0,
                    color VARCHAR(30) NOT NULL DEFAULT '#4f9cf9',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(20) NOT NULL,
                    amount INTEGER NOT NULL,
                    reason VARCHAR(200) NOT NULL DEFAULT '',
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
        print("[DB] Database initialized.")
    except Exception as e:
        print(f"[DB] Error: {e}")


async def db_register(username, password, display_name):
    if not db_pool:
        return {"error": "Database not available"}
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    try:
        async with db_pool.acquire() as conn:
            await conn.execute(
                "INSERT INTO users (username, password_hash, display_name) VALUES ($1, $2, $3)",
                username, pw_hash, display_name
            )
            token = secrets.token_hex(32)
            await conn.execute(
                "INSERT INTO sessions (token, username) VALUES ($1, $2)",
                token, username
            )
            return {"session_token": token, "username": username, "display_name": display_name,
                    "bio": "", "pfp_data": "", "show_changelog": True}
    except Exception as e:
        if "unique" in str(e).lower():
            return {"error": "Username already taken"}
        return {"error": str(e)}


async def db_login(username, password):
    if not db_pool:
        return {"error": "Database not available"}
    pw_hash = hashlib.sha256(password.encode()).hexdigest()
    async with db_pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE username=$1 AND password_hash=$2",
            username, pw_hash
        )
        if not user:
            return {"error": "Invalid username or password"}
        token = secrets.token_hex(32)
        await conn.execute("INSERT INTO sessions (token, username) VALUES ($1, $2)", token, username)
        seen = await conn.fetchrow(
            "SELECT 1 FROM changelog_seen WHERE username=$1 AND version=$2",
            username, CURRENT_VERSION
        )
        return {
            "session_token": token,
            "username": username,
            "display_name": user["display_name"],
            "bio": user["bio"] or "",
            "pfp_data": user["pfp_data"] or "",
            "show_changelog": not seen
        }


async def db_validate_session(token):
    if not db_pool or not token:
        return None
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT s.username, u.display_name, u.bio, u.pfp_data "
            "FROM sessions s JOIN users u ON s.username=u.username WHERE s.token=$1",
            token
        )
        return dict(row) if row else None


async def db_update_profile(token, display_name=None, bio=None, pfp_data=None):
    if not db_pool:
        return {"error": "Database not available"}
    user = await db_validate_session(token)
    if not user:
        return {"error": "Invalid session"}
    sets, params = [], []
    if display_name is not None:
        params.append(display_name[:30])
        sets.append(f"display_name=${len(params)}")
    if bio is not None:
        params.append(bio[:300])
        sets.append(f"bio=${len(params)}")
    if pfp_data is not None:
        params.append(pfp_data[:200000])
        sets.append(f"pfp_data=${len(params)}")
    if sets:
        params.append(user["username"])
        async with db_pool.acquire() as conn:
            await conn.execute(
                f"UPDATE users SET {', '.join(sets)} WHERE username=${len(params)}",
                *params
            )
    return {
        **user,
        **({"display_name": display_name} if display_name is not None else {}),
        **({"bio": bio} if bio is not None else {}),
        **({"pfp_data": pfp_data} if pfp_data is not None else {}),
    }


async def db_mark_changelog_seen(token, check_only=False):
    if not db_pool:
        return False
    user = await db_validate_session(token)
    if not user:
        return False
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT 1 FROM changelog_seen WHERE username=$1 AND version=$2",
            user["username"], CURRENT_VERSION
        )
        already_seen = row is not None
        if check_only:
            return not already_seen
        if not already_seen:
            await conn.execute(
                "INSERT INTO changelog_seen (username, version) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                user["username"], CURRENT_VERSION
            )
        return not already_seen

# ─── Economy DB helpers ──────────────────────────────────────────────────────
async def db_get_economy(username):
    if not db_pool:
        return {"balance":1000,"inventory":[],"equipped":{},"idle_money":0,"idle_upgrades":{},"idle_last_collect":None}
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("SELECT * FROM user_economy WHERE username=$1", username)
        if not row:
            await conn.execute("INSERT INTO user_economy (username) VALUES ($1) ON CONFLICT DO NOTHING", username)
            return {"balance":1000,"inventory":[],"equipped":{},"idle_money":0,"idle_upgrades":{},"idle_last_collect":None}
        return {
            "balance": row["balance"],
            "inventory": list(row["inventory"] or []),
            "equipped": dict(row["equipped"] or {}),
            "idle_money": float(row["idle_money"] or 0),
            "idle_upgrades": dict(row["idle_upgrades"] or {}),
            "idle_last_collect": row["idle_last_collect"],
        }

async def db_save_economy(username, data):
    if not db_pool: return
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO user_economy (username,balance,inventory,equipped,idle_money,idle_upgrades)
            VALUES ($1,$2,$3::jsonb,$4::jsonb,$5,$6::jsonb)
            ON CONFLICT (username) DO UPDATE SET
                balance=EXCLUDED.balance, inventory=EXCLUDED.inventory,
                equipped=EXCLUDED.equipped, idle_money=EXCLUDED.idle_money,
                idle_upgrades=EXCLUDED.idle_upgrades
        """, username, data["balance"],
            json.dumps(data.get("inventory",[])), json.dumps(data.get("equipped",{})),
            float(data.get("idle_money",0)), json.dumps(data.get("idle_upgrades",{})))

async def db_add_transaction(username, amount, reason):
    if not db_pool: return
    async with db_pool.acquire() as conn:
        await conn.execute("INSERT INTO transactions (username,amount,reason) VALUES ($1,$2,$3)",
                           username, int(amount), reason[:200])

async def db_get_transactions(username, limit=15):
    if not db_pool: return []
    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT amount,reason,created_at FROM transactions WHERE username=$1 ORDER BY created_at DESC LIMIT $2",
            username, limit)
        return [{"amount":r["amount"],"reason":r["reason"],"ts":r["created_at"].isoformat()} for r in rows]

async def db_get_savings(username):
    if not db_pool: return []
    async with db_pool.acquire() as conn:
        rows = await conn.fetch("SELECT id,name,goal,saved,color FROM savings_plans WHERE username=$1 ORDER BY id", username)
        return [{"id":r["id"],"name":r["name"],"goal":r["goal"],"saved":r["saved"],"color":r["color"]} for r in rows]

async def db_create_savings(username, name, goal, color):
    if not db_pool: return 0
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow(
            "INSERT INTO savings_plans (username,name,goal,color) VALUES ($1,$2,$3,$4) RETURNING id",
            username, name, goal, color)
        return row["id"]

async def db_update_savings(plan_id, username, amount, mode):
    if not db_pool: return
    async with db_pool.acquire() as conn:
        if mode == "deposit":
            await conn.execute("UPDATE savings_plans SET saved=LEAST(saved+$1,goal) WHERE id=$2 AND username=$3",
                               amount, plan_id, username)
        else:
            await conn.execute("UPDATE savings_plans SET saved=GREATEST(saved-$1,0) WHERE id=$2 AND username=$3",
                               amount, plan_id, username)

async def db_delete_savings(plan_id, username):
    if not db_pool: return
    async with db_pool.acquire() as conn:
        await conn.execute("DELETE FROM savings_plans WHERE id=$1 AND username=$2", plan_id, username)


USERNAME_RE = re.compile(r'^[a-zA-Z0-9_-]{1,20}$')
RESERVED_RE = re.compile(r'admin|mod|owner', re.IGNORECASE)


def get_admin_html(token):
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Chat Server - Owner Panel</title>
<style>
:root {
  --bg-primary: #313338;
  --bg-secondary: #2b2d31;
  --bg-tertiary: #1e1f22;
  --bg-message-hover: #2e3035;
  --text-primary: #f2f3f5;
  --text-secondary: #b5bac1;
  --text-tertiary: #949ba4;
  --text-muted: #6d6f78;
  --border: #3f4147;
  --accent: #5865f2;
  --accent-hover: #4752c4;
  --green: #23a559;
  --red: #ed4245;
  --yellow: #fee75c;
  --orange: #f0b232;
  --admin-color: #e03e3e;
  --input-bg: #383a40;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'gg sans', 'Noto Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  background: var(--bg-primary); color: var(--text-primary);
  height: 100vh; display: flex; flex-direction: column;
}
header {
  background: var(--bg-primary); border-bottom: 1px solid var(--bg-tertiary);
  padding: 12px 20px; display: flex; align-items: center;
  justify-content: space-between; gap: 8px; flex-wrap: wrap;
}
header h1 { font-size: 16px; font-weight: 600; }
.header-right { display: flex; align-items: center; gap: 12px; }
.status { font-size: 12px; color: var(--text-secondary); display: flex; align-items: center; gap: 6px; }
.status .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); }
.status.offline .dot { background: var(--red); }
.theme-btn {
  background: var(--input-bg); color: var(--text-secondary); border: none;
  padding: 6px 10px; border-radius: 4px; font-size: 12px; cursor: pointer;
}
.theme-btn:hover { background: var(--border); color: var(--text-primary); }

.container { flex: 1; display: flex; overflow: hidden; }

.sidebar {
  width: 240px; background: var(--bg-secondary);
  display: flex; flex-direction: column; flex-shrink: 0;
}
.sidebar-header {
  padding: 12px 16px; font-size: 11px; font-weight: 700; color: var(--text-tertiary);
  text-transform: uppercase; letter-spacing: 0.5px;
  display: flex; justify-content: space-between; align-items: center;
}
.sidebar-header .count {
  background: var(--bg-tertiary); color: var(--text-secondary);
  padding: 1px 6px; border-radius: 8px; font-size: 11px;
}
.user-list { flex: 1; overflow-y: auto; padding: 0 8px; }
.user-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 6px 8px; border-radius: 4px; margin-bottom: 1px;
}
.user-item:hover { background: var(--bg-message-hover); }
.user-info { display: flex; align-items: center; gap: 8px; flex: 1; min-width: 0; }
.user-avatar {
  width: 32px; height: 32px; border-radius: 50%; background: var(--accent);
  display: flex; align-items: center; justify-content: center;
  font-size: 12px; font-weight: 600; color: #fff; flex-shrink: 0;
}
.user-name {
  font-size: 14px; font-weight: 500; color: var(--text-secondary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.user-actions { display: flex; gap: 4px; visibility: hidden; }
.user-item:hover .user-actions { visibility: visible; }
.btn {
  padding: 4px 8px; border: none; border-radius: 4px;
  font-size: 11px; font-weight: 600; cursor: pointer;
  background: var(--bg-tertiary); color: var(--text-secondary);
}
.btn:hover { background: var(--border); color: var(--text-primary); }
.btn-danger { color: var(--red); }
.btn-danger:hover { background: rgba(237,66,69,0.15); color: var(--red); }
.btn-warn { color: var(--orange); }
.btn-warn:hover { background: rgba(240,178,50,0.15); color: var(--orange); }

.chat-area { flex: 1; display: flex; flex-direction: column; background: var(--bg-primary); }
.messages { flex: 1; overflow-y: auto; padding: 16px 16px; }
.msg { padding: 2px 8px; margin-bottom: 0; border-radius: 4px; line-height: 1.4; }
.msg:hover { background: var(--bg-message-hover); }
.msg-inline { padding: 4px 8px; display: flex; align-items: baseline; gap: 0; flex-wrap: wrap; }
.msg-sender { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.msg-sender.is-admin { color: var(--admin-color); }
.msg-badge { font-size: 10px; font-weight: 700; color: #fff; background: var(--admin-color);
  padding: 1px 4px; border-radius: 3px; margin-left: 4px; vertical-align: middle; }
.msg-colon { color: var(--text-tertiary); margin-right: 6px; }
.msg-time { font-size: 11px; color: var(--text-muted); margin-left: 6px; }
.msg-text { font-size: 14px; color: var(--text-secondary); word-break: break-word; }
.msg-system { text-align: center; padding: 4px 8px; margin-bottom: 2px; }
.msg-system span {
  font-size: 12px; color: var(--text-muted); background: var(--bg-secondary);
  padding: 2px 10px; border-radius: 10px;
}

.admin-input {
  padding: 12px 16px; display: flex; gap: 8px; flex-wrap: wrap;
}
.admin-input .name-input {
  width: 140px; padding: 10px 12px; border: none; border-radius: 8px;
  font-size: 14px; outline: none; background: var(--input-bg);
  color: var(--text-primary); flex-shrink: 0;
}
.admin-input .name-input:focus { outline: 2px solid var(--accent); }
.admin-input .msg-field {
  flex: 1; padding: 10px 14px; border: none; border-radius: 8px;
  font-size: 14px; outline: none; background: var(--input-bg);
  color: var(--text-primary); min-width: 200px;
}
.admin-input .msg-field:focus { outline: 2px solid var(--accent); }
.admin-input button {
  padding: 10px 20px; background: var(--accent); color: #fff;
  border: none; border-radius: 8px; font-size: 14px;
  font-weight: 500; cursor: pointer;
}
.admin-input button:hover { background: var(--accent-hover); }

.banned-section {
  border-top: 1px solid var(--bg-tertiary); padding: 10px 16px;
  max-height: 120px; overflow-y: auto;
}
.banned-header {
  font-size: 11px; font-weight: 700; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;
}
.banned-item {
  display: flex; align-items: center; justify-content: space-between; padding: 4px 0;
}
.banned-name { font-size: 13px; color: var(--text-muted); text-decoration: line-through; }
.btn-unban { color: var(--green); }
.btn-unban:hover { background: rgba(35,165,89,0.15); color: var(--green); }

.empty { display: flex; align-items: center; justify-content: center;
  height: 100%; color: var(--text-muted); font-size: 14px; }

body.theme-light {
  --bg-primary: #ffffff;
  --bg-secondary: #f2f3f5;
  --bg-tertiary: #e3e5e8;
  --bg-message-hover: #f2f3f5;
  --text-primary: #060607;
  --text-secondary: #4e5058;
  --text-tertiary: #6d6f78;
  --text-muted: #80848e;
  --border: #e3e5e8;
  --accent: #5865f2;
  --accent-hover: #4752c4;
  --input-bg: #e3e5e8;
  --admin-color: #c0392b;
}
body.theme-midnight {
  --bg-primary: #0a0a0f;
  --bg-secondary: #111118;
  --bg-tertiary: #06060a;
  --bg-message-hover: #14141c;
  --text-primary: #e0e0e8;
  --text-secondary: #9a9ab0;
  --text-tertiary: #6a6a80;
  --text-muted: #4a4a5a;
  --border: #1a1a24;
  --input-bg: #14141c;
  --admin-color: #ff5555;
}
body.theme-ocean {
  --bg-primary: #0d1b2a; --bg-secondary: #1b2838; --bg-tertiary: #0a1520;
  --bg-message-hover: #1f3044; --text-primary: #e0f0ff; --text-secondary: #8ab4d6;
  --text-tertiary: #5a8aaa; --text-muted: #3a6080; --border: #1a3050;
  --accent: #1e90ff; --accent-hover: #1570cc; --input-bg: #162636; --admin-color: #ff6b6b;
}
body.theme-forest {
  --bg-primary: #1a2618; --bg-secondary: #222e20; --bg-tertiary: #141e12;
  --bg-message-hover: #283628; --text-primary: #e0f0e0; --text-secondary: #8ab88a;
  --text-tertiary: #5a8a5a; --text-muted: #3a6a3a; --border: #2a3e2a;
  --accent: #2ecc71; --accent-hover: #27ae60; --input-bg: #1e2e1c; --admin-color: #e74c3c;
}
body.theme-sunset {
  --bg-primary: #2a1a1e; --bg-secondary: #381e24; --bg-tertiary: #1e1214;
  --bg-message-hover: #3e242a; --text-primary: #ffe8e0; --text-secondary: #d4a090;
  --text-tertiary: #a07060; --text-muted: #705040; --border: #4a2a30;
  --accent: #ff6b35; --accent-hover: #e55a2b; --input-bg: #321a20; --admin-color: #ff4444;
}
body.theme-neon {
  --bg-primary: #0a0a14; --bg-secondary: #10101e; --bg-tertiary: #06060c;
  --bg-message-hover: #161628; --text-primary: #e0e0ff; --text-secondary: #a0a0d0;
  --text-tertiary: #7070a0; --text-muted: #404070; --border: #1e1e3a;
  --accent: #ff00ff; --accent-hover: #cc00cc; --input-bg: #12121e; --admin-color: #ff3366;
}
body.theme-rose {
  --bg-primary: #201418; --bg-secondary: #2a1a20; --bg-tertiary: #180e12;
  --bg-message-hover: #301e26; --text-primary: #ffe8f0; --text-secondary: #d4a0b8;
  --text-tertiary: #a07088; --text-muted: #705060; --border: #3a1e2a;
  --accent: #e91e63; --accent-hover: #c2185b; --input-bg: #261620; --admin-color: #ff5252;
}
</style>
</head>
<body>
<header>
  <h1>Chat Server</h1>
  <div class="header-right">
    <div class="status" id="status">
      <span class="dot"></span>
      <span id="status-text">Connecting...</span>
    </div>
    <button class="theme-btn" id="themeBtn" data-testid="button-theme">Dark</button>
  </div>
</header>
<div class="container">
  <div class="sidebar">
    <div class="sidebar-header">
      Online <span class="count" id="user-count" data-testid="text-user-count">0</span>
    </div>
    <div class="user-list" id="user-list" data-testid="list-users"></div>
    <div class="banned-section" id="banned-section" style="display:none;">
      <div class="banned-header">Banned</div>
      <div id="banned-list"></div>
    </div>
  </div>
  <div class="chat-area">
    <div class="messages" id="messages" data-testid="list-messages">
      <div class="empty" id="empty-state">No messages yet</div>
    </div>
    <div class="admin-input">
      <input type="text" class="name-input" id="name-input" data-testid="input-admin-name" placeholder="Your name" value="Admin" />
      <input type="text" class="msg-field" id="msg-input" data-testid="input-message" placeholder="Type a message..." />
      <button id="send-btn" data-testid="button-send">Send</button>
    </div>
  </div>
</div>
<script>
const OWNER_TOKEN = '__TOKEN__';
history.replaceState({}, '', '/admin');
const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
const wsUrl = protocol + '//' + location.host + '/owner-ws?token=' + OWNER_TOKEN;
let ws;
const themes = ['theme-dark', 'theme-light', 'theme-midnight', 'theme-ocean', 'theme-forest', 'theme-sunset', 'theme-neon', 'theme-rose'];
const themeLabels = ['Dark', 'Light', 'Midnight', 'Ocean', 'Forest', 'Sunset', 'Neon', 'Rose'];
let themeIdx = parseInt(localStorage.getItem('admin-theme') || '0');

function applyTheme() {
  document.body.className = themes[themeIdx] || '';
  document.getElementById('themeBtn').textContent = themeLabels[themeIdx];
  localStorage.setItem('admin-theme', themeIdx);
}
applyTheme();

document.getElementById('themeBtn').addEventListener('click', function() {
  themeIdx = (themeIdx + 1) % themes.length;
  applyTheme();
});

function connectWS() {
  ws = new WebSocket(wsUrl);
  ws.onopen = () => {
    document.getElementById('status').className = 'status';
    document.getElementById('status-text').textContent = 'Server Running';
  };
  ws.onclose = () => {
    document.getElementById('status').className = 'status offline';
    document.getElementById('status-text').textContent = 'Disconnected';
    setTimeout(connectWS, 2000);
  };
  ws.onmessage = (e) => {
    const data = JSON.parse(e.data);
    switch (data.type) {
      case 'users': renderUsers(data.list); break;
      case 'chat': addMessage(data.sender, data.text, data.admin || false); break;
      case 'system': addSystemMessage(data.text); break;
      case 'banned_list': renderBanned(data.list); break;
    }
  };
}

function renderUsers(users) {
  const el = document.getElementById('user-list');
  document.getElementById('user-count').textContent = users.length;
  if (users.length === 0) {
    el.innerHTML = '<div class="empty" style="height:80px;">No users online</div>';
    return;
  }
  el.innerHTML = '';
  users.forEach(userObj => {
    const u = typeof userObj === 'string' ? userObj : userObj.name;
    const item = document.createElement('div');
    item.className = 'user-item';
    const info = document.createElement('div');
    info.className = 'user-info';
    const avatar = document.createElement('div');
    avatar.className = 'user-avatar';
    avatar.textContent = u.substring(0,2).toUpperCase();
    const name = document.createElement('div');
    name.className = 'user-name';
    name.textContent = u;
    info.appendChild(avatar);
    info.appendChild(name);
    const actions = document.createElement('div');
    actions.className = 'user-actions';
    const kickBtn = document.createElement('button');
    kickBtn.className = 'btn btn-warn';
    kickBtn.textContent = 'Kick';
    kickBtn.addEventListener('click', () => { ws.send(JSON.stringify({type:'kick',username:u})); });
    const banBtn = document.createElement('button');
    banBtn.className = 'btn btn-danger';
    banBtn.textContent = 'Ban';
    banBtn.addEventListener('click', () => { ws.send(JSON.stringify({type:'ban',username:u})); });
    actions.appendChild(kickBtn);
    actions.appendChild(banBtn);
    item.appendChild(info);
    item.appendChild(actions);
    el.appendChild(item);
  });
}

function renderBanned(list) {
  const section = document.getElementById('banned-section');
  const el = document.getElementById('banned-list');
  if (list.length === 0) { section.style.display = 'none'; return; }
  section.style.display = 'block';
  el.innerHTML = '';
  list.forEach(u => {
    const item = document.createElement('div');
    item.className = 'banned-item';
    const name = document.createElement('span');
    name.className = 'banned-name';
    name.textContent = u;
    const unbanBtn = document.createElement('button');
    unbanBtn.className = 'btn btn-unban';
    unbanBtn.textContent = 'Unban';
    unbanBtn.addEventListener('click', () => { ws.send(JSON.stringify({type:'unban',username:u})); });
    item.appendChild(name);
    item.appendChild(unbanBtn);
    el.appendChild(item);
  });
}

function addMessage(sender, text, isAdmin) {
  document.getElementById('empty-state')?.remove();
  const el = document.getElementById('messages');
  const time = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  const div = document.createElement('div');
  div.className = 'msg msg-inline';

  const senderEl = document.createElement('span');
  senderEl.className = 'msg-sender' + (isAdmin ? ' is-admin' : '');
  senderEl.textContent = sender;
  div.appendChild(senderEl);

  if (isAdmin) {
    const badge = document.createElement('span');
    badge.className = 'msg-badge';
    badge.textContent = 'ADMIN';
    div.appendChild(badge);
  }

  const colon = document.createElement('span');
  colon.className = 'msg-colon';
  colon.textContent = ': ';
  div.appendChild(colon);

  const textEl = document.createElement('span');
  textEl.className = 'msg-text';
  textEl.textContent = text;
  div.appendChild(textEl);

  const timeEl = document.createElement('span');
  timeEl.className = 'msg-time';
  timeEl.textContent = time;
  div.appendChild(timeEl);

  el.appendChild(div);
  el.scrollTop = el.scrollHeight;
}

function addSystemMessage(text) {
  document.getElementById('empty-state')?.remove();
  const el = document.getElementById('messages');
  const wrapper = document.createElement('div');
  wrapper.className = 'msg-system';
  const span = document.createElement('span');
  span.textContent = text;
  wrapper.appendChild(span);
  el.appendChild(wrapper);
  el.scrollTop = el.scrollHeight;
}

function sendMsg() {
  const nameInput = document.getElementById('name-input');
  const input = document.getElementById('msg-input');
  const text = input.value.trim();
  const name = nameInput.value.trim() || 'Admin';
  if (!text) return;
  ws.send(JSON.stringify({type: 'chat', text: text, name: name}));
  input.value = '';
  input.focus();
}

document.getElementById('send-btn').addEventListener('click', sendMsg);
document.getElementById('msg-input').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') sendMsg();
});
connectWS();
</script>
</body>
</html>""".replace('__TOKEN__', token)


def get_client_html():
    return """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Chat</title>
<style>
:root {
  --bg-primary: #313338;
  --bg-secondary: #2b2d31;
  --bg-tertiary: #1e1f22;
  --bg-message-hover: #2e3035;
  --text-primary: #f2f3f5;
  --text-secondary: #b5bac1;
  --text-tertiary: #949ba4;
  --text-muted: #6d6f78;
  --border: #3f4147;
  --accent: #5865f2;
  --accent-hover: #4752c4;
  --green: #23a559;
  --red: #ed4245;
  --orange: #f0b232;
  --admin-color: #e03e3e;
  --input-bg: #383a40;
  --dm-color: #9b59b6;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'gg sans', 'Noto Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  background: var(--bg-primary); color: var(--text-primary);
  height: 100vh; display: flex; flex-direction: column;
}

.join-screen {
  display: flex; align-items: center; justify-content: center;
  min-height: 100vh; background: var(--bg-tertiary);
}
.join-box {
  background: var(--bg-primary); border-radius: 8px;
  padding: 32px; max-width: 400px; width: 90%;
}
.join-box h2 { margin-bottom: 8px; font-size: 22px; font-weight: 700; color: var(--text-primary); }
.join-box p { color: var(--text-secondary); margin-bottom: 20px; font-size: 14px; }
.join-box label { display: block; font-size: 12px; font-weight: 700; margin-bottom: 6px;
  color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px; }
.join-box input {
  width: 100%; padding: 10px 12px; border: none; border-radius: 4px;
  font-size: 14px; margin-bottom: 16px; background: var(--bg-tertiary);
  color: var(--text-primary); outline: none;
}
.join-box input:focus { outline: 2px solid var(--accent); }
.join-box button {
  width: 100%; padding: 10px; background: var(--accent); color: #fff; border: none;
  border-radius: 4px; font-size: 14px; font-weight: 600; cursor: pointer;
}
.join-box button:hover { background: var(--accent-hover); }
.join-error { color: var(--red); font-size: 13px; margin-bottom: 10px; display: none; }
.join-tabs { display: flex; gap: 4px; margin-bottom: 18px; border-bottom: 1px solid var(--border); }
.join-tab { background: none; border: none; border-bottom: 2px solid transparent; color: var(--text-muted); font-size: 14px; font-weight: 600; padding: 8px 14px; cursor: pointer; margin-bottom: -1px; transition: color 0.15s; }
.join-tab:hover { color: var(--text-primary); background: none; }
.join-tab.active { color: var(--accent); border-bottom-color: var(--accent); background: none; }

header {
  background: var(--bg-primary); border-bottom: 1px solid var(--bg-tertiary);
  padding: 12px 20px; display: flex; align-items: center;
  justify-content: space-between; gap: 8px; flex-wrap: wrap;
}
header h1 { font-size: 16px; font-weight: 600; }
.header-right { display: flex; align-items: center; gap: 12px; }
.status { font-size: 12px; color: var(--text-secondary); display: flex; align-items: center; gap: 6px; }
.status .dot { width: 8px; height: 8px; border-radius: 50%; background: var(--green); }
.theme-btn {
  background: var(--input-bg); color: var(--text-secondary); border: none;
  padding: 6px 10px; border-radius: 4px; font-size: 12px; cursor: pointer;
}
.theme-btn:hover { background: var(--border); color: var(--text-primary); }

.container { display: flex; flex: 1; overflow: hidden; }

.sidebar {
  width: 240px; background: var(--bg-secondary);
  display: flex; flex-direction: column; flex-shrink: 0;
}
.sidebar-section {
  padding: 10px 10px 0 10px;
}
.sidebar-label {
  padding: 4px 6px; font-size: 11px; font-weight: 700;
  color: var(--text-tertiary); text-transform: uppercase; letter-spacing: 0.5px;
  display: flex; align-items: center; gap: 6px;
}
.sidebar-label .count {
  background: var(--bg-tertiary); color: var(--text-secondary);
  padding: 1px 6px; border-radius: 8px; font-size: 11px;
}
.channel-item {
  padding: 7px 10px; font-size: 14px; color: var(--text-secondary);
  border-radius: 4px; margin-bottom: 1px; display: flex; align-items: center; gap: 8px;
  cursor: pointer;
}
.channel-item:hover { background: var(--bg-message-hover); }
.channel-item.active { background: var(--bg-message-hover); color: var(--text-primary); font-weight: 600; }
.channel-icon { font-size: 16px; opacity: 0.6; }
.dm-badge {
  margin-left: auto; background: var(--red); color: #fff;
  font-size: 10px; font-weight: 700; padding: 1px 5px; border-radius: 8px;
  min-width: 16px; text-align: center;
}
.user-list-area { flex: 1; overflow-y: auto; padding: 0 10px 10px 10px; }
.user-item {
  padding: 6px 10px; font-size: 14px; color: var(--text-secondary);
  border-radius: 4px; margin-bottom: 1px; display: flex; align-items: center; gap: 8px;
  cursor: pointer; position: relative;
}
.user-item:hover { background: var(--bg-message-hover); }
.user-avatar {
  width: 28px; height: 28px; border-radius: 50%; background: var(--accent);
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 600; color: #fff; flex-shrink: 0;
  background-size: cover; background-position: center;
}
.user-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1; }
.user-actions { display: flex; gap: 4px; visibility: hidden; }
.user-item:hover .user-actions { visibility: visible; }

.chat-area { flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }

.main-panel { flex: 1; display: flex; flex-direction: column; min-width: 0; min-height: 0; }
.tab-bar {
  display: flex; align-items: center; background: var(--bg-tertiary);
  border-bottom: 1px solid var(--border); height: 36px; flex-shrink: 0;
  overflow-x: auto; overflow-y: hidden;
}
.tab-bar::-webkit-scrollbar { height: 0; }
.tab-items { display: flex; flex: 1; min-width: 0; overflow-x: auto; }
.tab-items::-webkit-scrollbar { height: 0; }
.tab-item {
  display: flex; align-items: center; gap: 6px;
  padding: 0 14px; height: 36px; font-size: 13px; font-weight: 500;
  color: var(--text-muted); cursor: pointer; white-space: nowrap;
  border-right: 1px solid var(--border); background: var(--bg-tertiary);
  flex-shrink: 0; min-width: 0; transition: color 0.12s;
  border-bottom: 2px solid transparent;
}
.tab-item:hover { background: var(--bg-secondary); color: var(--text-secondary); }
.tab-item.active { background: var(--bg-primary); color: var(--text-primary); border-bottom-color: var(--accent); }
.tab-item .tab-icon { font-size: 14px; opacity: 0.7; }
.tab-item .tab-close {
  font-size: 14px; opacity: 0; width: 18px; height: 18px;
  display: flex; align-items: center; justify-content: center;
  border-radius: 3px; color: var(--text-muted); margin-left: 2px;
  background: none; border: none; cursor: pointer; padding: 0;
}
.tab-item:hover .tab-close { visibility: visible; opacity: 1; }
.tab-item .tab-close:hover { background: var(--bg-message-hover); color: var(--text-primary); }
.new-tab-btn {
  width: 36px; height: 36px; display: flex; align-items: center; justify-content: center;
  background: none; border: none; color: var(--text-muted); font-size: 18px;
  cursor: pointer; flex-shrink: 0;
}
.new-tab-btn:hover { background: var(--bg-secondary); color: var(--text-primary); }
#tabContents { flex: 1; display: flex; flex-direction: column; min-height: 0; overflow: hidden; }
.tab-content { flex: 1; display: none; flex-direction: column; min-height: 0; overflow: hidden; }
.tab-content.active { display: flex; }

.newtab-page {
  flex: 1; display: flex; flex-direction: column; background: var(--bg-primary); overflow-y: auto;
}
.newtab-search {
  padding: 12px 16px 0; flex-shrink: 0;
}
.newtab-search input {
  width: 100%; padding: 8px 12px; border-radius: 4px; border: 1px solid var(--border);
  background: var(--input-bg); color: var(--text-primary); font-size: 13px; outline: none;
}
.newtab-search input:focus { border-color: var(--accent); }
.newtab-search input::placeholder { color: var(--text-muted); }
.newtab-list {
  flex: 1; overflow-y: auto; padding: 8px 0;
}
.newtab-item {
  display: flex; align-items: center; padding: 10px 16px; cursor: pointer;
  gap: 12px; transition: background 0.1s;
}
.newtab-item:hover { background: var(--bg-message-hover); }
.newtab-item-info { flex: 1; min-width: 0; }
.newtab-item-name { font-size: 14px; font-weight: 500; color: var(--text-primary); }
.newtab-item-desc { font-size: 12px; color: var(--text-muted); margin-top: 1px; }
.newtab-item-badge {
  font-size: 10px; padding: 2px 6px; border-radius: 3px;
  background: var(--bg-tertiary); color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.3px; font-weight: 600; flex-shrink: 0;
}
.newtab-section-label {
  font-size: 11px; font-weight: 700; color: var(--text-tertiary);
  text-transform: uppercase; letter-spacing: 0.5px;
  padding: 12px 16px 4px;
}
.newtab-empty {
  padding: 20px 16px; text-align: center; color: var(--text-muted); font-size: 13px;
}

.games-hub {
  flex: 1; display: flex; flex-direction: column; background: var(--bg-primary); overflow: hidden;
}
.games-header {
  padding: 10px 16px; border-bottom: 1px solid var(--bg-tertiary);
  font-size: 14px; font-weight: 600; display: flex; align-items: center; gap: 8px;
}
.games-header .back-btn {
  background: var(--input-bg); border: none; color: var(--text-secondary);
  padding: 4px 10px; border-radius: 4px; font-size: 12px; cursor: pointer;
}
.games-header .back-btn:hover { background: var(--border); color: var(--text-primary); }
.games-search {
  padding: 8px 16px; flex-shrink: 0;
}
.games-search input {
  width: 100%; padding: 7px 10px; border-radius: 4px; border: 1px solid var(--border);
  background: var(--input-bg); color: var(--text-primary); font-size: 13px; outline: none;
}
.games-search input:focus { border-color: var(--accent); }
.games-search input::placeholder { color: var(--text-muted); }
.games-list {
  flex: 1; overflow-y: auto; padding: 0;
}
.game-item {
  display: flex; align-items: center; padding: 10px 16px; cursor: pointer;
  gap: 12px; transition: background 0.1s;
}
.game-item:hover { background: var(--bg-message-hover); }
.game-item-info { flex: 1; min-width: 0; }
.game-item-name { font-size: 14px; font-weight: 500; color: var(--text-primary); }
.game-item-desc { font-size: 12px; color: var(--text-muted); margin-top: 1px; }
.game-item-badge {
  font-size: 10px; padding: 2px 6px; border-radius: 3px;
  background: var(--bg-tertiary); color: var(--text-secondary);
  text-transform: uppercase; letter-spacing: 0.3px; font-weight: 600; flex-shrink: 0;
}
.game-play-area {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 16px; overflow-y: auto;
}

.ttt-board {
  display: grid; grid-template-columns: repeat(3, 80px); grid-template-rows: repeat(3, 80px); gap: 4px;
}
.ttt-cell {
  width: 80px; height: 80px; background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: 4px; font-size: 32px; font-weight: 700; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  color: var(--text-primary);
}
.ttt-cell:hover { background: var(--bg-message-hover); }
.ttt-cell.x { color: var(--accent); }
.ttt-cell.o { color: var(--red); }
.game-status {
  font-size: 15px; font-weight: 600; margin-bottom: 12px; color: var(--text-primary);
  min-height: 24px;
}
.game-reset-btn {
  margin-top: 12px; padding: 8px 20px; background: var(--accent); color: #fff;
  border: none; border-radius: 6px; font-size: 13px; font-weight: 600; cursor: pointer;
}
.game-reset-btn:hover { background: var(--accent-hover); }

.snake-canvas {
  border: 2px solid var(--border); border-radius: 4px; background: var(--bg-secondary);
}
.snake-score { font-size: 14px; color: var(--text-secondary); margin-bottom: 8px; }
.snake-hint { font-size: 12px; color: var(--text-muted); margin-top: 8px; }

.memory-board {
  display: grid; grid-template-columns: repeat(4, 70px); gap: 6px;
}
.memory-card {
  width: 70px; height: 70px; background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: 6px; font-size: 24px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  color: transparent; user-select: none;
}
.memory-card:hover { background: var(--bg-message-hover); }
.memory-card.flipped, .memory-card.matched {
  color: var(--text-primary); background: var(--bg-message-hover);
  border-color: var(--accent);
}
.memory-card.matched { border-color: var(--green); cursor: default; }
.memory-stats { font-size: 13px; color: var(--text-secondary); margin-bottom: 10px; }

.channel-header {
  padding: 11px 16px; border-bottom: 1px solid var(--bg-tertiary);
  font-size: 15px; font-weight: 700; display: flex; align-items: center; gap: 6px;
  background: var(--bg-primary); flex-shrink: 0;
  box-shadow: 0 1px 4px rgba(0,0,0,0.18);
}
.channel-header .channel-hash { color: var(--text-muted); font-size: 20px; font-weight: 900; line-height: 1; margin-right: 2px; }
.channel-header .dm-label { color: var(--dm-color); }

#messages { flex: 1; overflow-y: auto; padding: 16px 16px; min-height: 0; position: relative; }
.msg { padding: var(--msg-padding, 2px 8px); border-radius: 4px; line-height: 1.4; }
.msg:hover { background: var(--bg-message-hover); }
.msg-inline { padding: 4px 8px; display: flex; align-items: baseline; gap: 0; flex-wrap: wrap; }
.msg-sender { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.msg-sender.is-admin { color: var(--admin-color); }
.msg-badge { font-size: 10px; font-weight: 700; color: #fff; background: var(--admin-color);
  padding: 1px 4px; border-radius: 3px; margin-left: 4px; vertical-align: middle; }
.msg-badge.dm-badge-inline { background: var(--dm-color); }
.msg-colon { color: var(--text-tertiary); margin-right: 6px; }
.msg-time { font-size: 11px; color: var(--text-muted); margin-left: 6px; }
.msg-text { font-size: 14px; color: var(--text-secondary); word-break: break-word; }
.msg-text a { color: var(--accent); text-decoration: none; }
.msg-text a:hover { text-decoration: underline; }
.msg-text .inline-img {
  display: block; max-width: 400px; max-height: 300px;
  border-radius: 8px; margin-top: 4px; cursor: pointer;
}
.msg-text .inline-img:hover { opacity: 0.9; }
.msg-system { text-align: center; padding: 4px 8px; margin-bottom: 2px; }
.msg-system span { font-size: 12px; color: var(--text-muted); background: var(--bg-secondary);
  padding: 2px 10px; border-radius: 10px; }
.msg-error { padding: 4px 8px; color: var(--red); font-size: 13px; font-weight: 500; }

.emoji-picker-btn {
  background: none; color: var(--text-muted); border: none;
  padding: 7px 9px; border-radius: 6px; font-size: 18px; cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: color 0.12s;
}
.emoji-picker-btn:hover { background: none; color: var(--accent); }
.emoji-picker-container {
  position: relative;
}
.emoji-panel {
  position: absolute; bottom: 100%; right: 0; margin-bottom: 8px;
  background: var(--bg-secondary); border: 1px solid var(--border);
  border-radius: 8px; padding: 8px; width: 320px;
  box-shadow: 0 4px 16px rgba(0,0,0,0.3); display: none; z-index: 100;
}
.emoji-panel.open { display: block; }
.emoji-panel-header {
  display: flex; gap: 4px; margin-bottom: 6px; flex-wrap: wrap;
}
.emoji-cat-btn {
  background: none; border: none; color: var(--text-muted);
  font-size: 16px; cursor: pointer; padding: 4px 6px; border-radius: 4px;
  width: auto;
}
.emoji-cat-btn:hover { background: var(--bg-message-hover); }
.emoji-cat-btn.active { background: var(--bg-tertiary); color: var(--text-primary); }
.emoji-search {
  width: 100%; padding: 6px 8px; border: none; border-radius: 4px;
  font-size: 13px; background: var(--bg-tertiary); color: var(--text-primary);
  outline: none; margin-bottom: 6px;
}
.emoji-search:focus { outline: 1px solid var(--accent); }
.emoji-grid {
  display: grid; grid-template-columns: repeat(8, 1fr); gap: 2px;
  max-height: 200px; overflow-y: auto;
}
.emoji-grid::-webkit-scrollbar { width: 6px; }
.emoji-grid::-webkit-scrollbar-thumb { background: var(--bg-tertiary); border-radius: 3px; }
.emoji-item {
  font-size: 20px; padding: 4px; text-align: center; cursor: pointer;
  border-radius: 4px; border: none; background: none; width: auto;
}
.emoji-item:hover { background: var(--bg-message-hover); }

.input-bar {
  padding: 4px 16px 14px; display: flex; flex-direction: column; gap: 4px; flex-shrink: 0;
  position: relative;
}
@keyframes spin { to { transform: rotate(360deg); } }
@keyframes pulse-dot { 0%,100%{opacity:1;transform:scale(1);} 50%{opacity:0.5;transform:scale(1.35);} }
#chatStatusDot { animation: pulse-dot 2s ease-in-out infinite; }
@keyframes typing-bounce { 0%,60%,100%{transform:translateY(0);opacity:0.6;} 30%{transform:translateY(-5px);opacity:1;} }
.typing-dot { display:inline-block;width:5px;height:5px;border-radius:50%;background:var(--text-muted);margin:0 1.5px;animation:typing-bounce 1.1s ease-in-out infinite; }
.typing-dot:nth-child(2){animation-delay:.18s;} .typing-dot:nth-child(3){animation-delay:.36s;}
@keyframes msg-fadein { from{opacity:0;transform:translateY(6px);} to{opacity:1;transform:translateY(0);} }
.msg-animate { animation: msg-fadein 0.22s ease; }
.rainbow-text { background:linear-gradient(90deg,#ff0000,#ff7700,#ffee00,#00c800,#0000ff,#8b00ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;font-weight:700; }
.me-action { color:var(--accent);font-style:italic;opacity:0.9; }
.fmt-toolbar { display:flex;align-items:center;gap:2px;padding:0 6px;flex-shrink:0; }
.fmt-btn { padding:3px 7px;background:none;color:var(--text-muted);border:1px solid transparent;border-radius:5px;cursor:pointer;font-size:12px;font-weight:700;line-height:1.4;transition:all 0.1s; }
.fmt-btn:hover { background:var(--bg-tertiary);color:var(--text-primary);border-color:var(--border); }
@keyframes party-hue { 0%{filter:hue-rotate(0deg);} 100%{filter:hue-rotate(360deg);} }
.party-mode { animation:party-hue 1.5s linear infinite; }
.poll-widget { background:var(--bg-tertiary);border:1px solid var(--border);border-radius:8px;padding:10px 14px;margin-top:4px;max-width:340px; }
.poll-option { display:flex;align-items:center;gap:8px;padding:6px 0;cursor:pointer; }
.poll-bar { height:6px;background:var(--accent);border-radius:3px;transition:width 0.4s; }
.slow-badge { display:none;background:var(--orange);color:#fff;border-radius:4px;padding:2px 7px;font-size:11px;font-weight:700;margin-left:8px; }
.slash-dropdown { display:none;position:absolute;bottom:100%;left:16px;right:16px;background:var(--bg-secondary);border:1px solid var(--border);border-radius:10px;overflow:hidden;box-shadow:0 -6px 28px rgba(0,0,0,0.38);z-index:220;margin-bottom:4px; }
.slash-dropdown.open { display:block; }
.slash-cmd-header { padding:5px 12px;font-size:10px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.08em;background:var(--bg-tertiary);border-bottom:1px solid var(--border); }
.slash-cmd-item { display:flex;align-items:center;gap:10px;padding:9px 14px;cursor:pointer;transition:background 0.1s;border-bottom:1px solid rgba(0,0,0,0.06); }
.slash-cmd-item:last-child { border-bottom:none; }
.slash-cmd-item:hover,.slash-cmd-item.selected { background:var(--bg-tertiary); }
.slash-cmd-name { font-size:13px;font-weight:700;color:var(--accent);min-width:110px;font-family:monospace; }
.slash-cmd-desc { font-size:12px;color:var(--text-muted);flex:1; }
.sidebar-collapsed { display:none!important; }
.hide-timestamps .msg-time { display:none!important; }
.hide-avatars .user-avatar { display:none!important; }
.msg-sender { color: var(--username-color-custom, var(--text-primary)); }
.msg-sender.is-admin { color: var(--admin-color)!important; }
.date-divider { display:flex;align-items:center;gap:10px;padding:10px 0 6px;color:var(--text-muted);font-size:11px;font-weight:600;letter-spacing:0.05em;text-transform:uppercase;user-select:none; }
.date-divider::before,.date-divider::after { content:'';flex:1;height:1px;background:var(--border); }
.unread-divider { display:flex;align-items:center;gap:10px;padding:6px 0;color:var(--red,#f04747);font-size:11px;font-weight:700;letter-spacing:0.04em;user-select:none; }
.unread-divider::before,.unread-divider::after { content:'';flex:1;height:1px;background:var(--red,#f04747);opacity:0.4; }
.char-counter { font-size:11px;color:var(--text-muted);padding:0 4px;align-self:center;flex-shrink:0; }
.char-counter.warn { color:var(--orange,#f0b232); }
.char-counter.over { color:var(--red,#f04747); }
.msg-search-bar { display:none;padding:6px 16px;background:var(--bg-secondary);border-bottom:1px solid var(--border);flex-shrink:0; }
.msg-search-bar.open { display:flex;align-items:center;gap:8px; }
.msg-search-bar input { flex:1;padding:5px 10px;border:1px solid var(--border);border-radius:6px;background:var(--input-bg);color:var(--text-primary);font-size:13px;outline:none; }
.msg-search-bar input:focus { border-color:var(--accent); }
.msg-search-bar .srch-count { font-size:12px;color:var(--text-muted);white-space:nowrap; }
.msg-highlight { background:rgba(255,200,0,0.25);border-radius:2px; }
.msg-highlight.current { background:rgba(255,150,0,0.45); }
.msg-badge.owner-badge { background:var(--accent); }
.msg-badge.staff-badge { background:var(--orange,#f0b232); }
.draft-indicator { font-size:10px;color:var(--orange,#f0b232);margin-left:4px; }
.sidebar-collapse-btn { background:none;border:none;color:var(--text-muted);cursor:pointer;padding:4px 6px;border-radius:4px;font-size:14px;flex-shrink:0;line-height:1; }
.sidebar-collapse-btn:hover { background:var(--bg-tertiary);color:var(--text-primary); }
.mute-btn { background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:13px;padding:2px 4px;border-radius:3px;line-height:1;flex-shrink:0; }
.mute-btn:hover { color:var(--text-primary); }
.mute-btn.muted { color:var(--orange,#f0b232); }
.ch-preview { font-size:11px;color:var(--text-muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:140px; }
.broadcast-btn { width:100%;padding:8px 12px;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;text-align:center;margin-top:8px; }
.broadcast-btn:hover { opacity:0.85; }
.input-bar-row {
  display: flex; gap: 0; align-items: center;
  background: var(--input-bg); border-radius: 12px;
  border: 1.5px solid transparent; transition: border-color 0.18s;
  padding: 2px 6px 2px 2px;
}
.input-bar-row:focus-within { border-color: rgba(88,101,242,0.5); }
.input-bar input#msgInput {
  flex: 1; padding: 9px 8px; border: none; border-radius: 0;
  font-size: 14px; outline: none; background: transparent;
  color: var(--text-primary);
}
.input-bar input#nameInput {
  padding: 9px 8px; border: none; border-radius: 0;
  font-size: 14px; outline: none; background: transparent;
  color: var(--text-primary); width: 120px; flex: unset;
}
.input-bar input#msgInput:focus, .input-bar input#nameInput:focus { outline: none; }
#sendBtn {
  background: var(--accent); color: #fff; border: none;
  border-radius: 50%; width: 34px; height: 34px; font-size: 17px;
  cursor: pointer; display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; transition: background 0.15s, transform 0.12s; padding: 0;
  margin: 1px 0;
}
#sendBtn:hover { background: var(--accent-hover); transform: scale(1.1); }
#sendBtn:disabled { background: var(--bg-tertiary); color: var(--text-muted); cursor: not-allowed; transform: none; }
.attach-btn {
  background: none; color: var(--text-muted); border: none;
  padding: 8px 9px; font-size: 18px; cursor: pointer;
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  border-radius: 6px; transition: color 0.12s;
}
.attach-btn:hover { background: none; color: var(--accent); }
.image-preview-bar {
  display: flex; gap: 8px; flex-wrap: wrap; padding: 6px 0 2px;
}
.image-preview-item {
  position: relative; width: 72px; height: 72px; border-radius: 6px;
  overflow: hidden; border: 2px solid var(--accent); flex-shrink: 0;
}
.image-preview-item img { width: 100%; height: 100%; object-fit: cover; }
.image-preview-item .remove-img {
  position: absolute; top: 2px; right: 2px; width: 18px; height: 18px;
  background: rgba(0,0,0,0.7); color: #fff; border: none; border-radius: 50%;
  font-size: 12px; cursor: pointer; display: flex; align-items: center; justify-content: center;
  line-height: 1;
}
.drop-overlay {
  position: absolute; inset: 0; background: rgba(88,101,242,0.15);
  border: 2px dashed var(--accent); border-radius: 4px; z-index: 10;
  display: flex; align-items: center; justify-content: center;
  font-size: 15px; font-weight: 600; color: var(--accent); pointer-events: none;
  opacity: 0; transition: opacity 0.15s;
}
.drop-overlay.visible { opacity: 1; }
.msg-img-attachment {
  display: block; max-width: 360px; max-height: 260px; border-radius: 8px;
  margin-top: 6px; cursor: pointer; border: 1px solid var(--border);
}
.msg-img-attachment:hover { opacity: 0.88; }
.msg-grouped { padding-left: 52px; }
.msg-avatar-col {
  width: 40px; flex-shrink: 0; display: flex; justify-content: center; padding-top: 2px;
}
.msg-avatar {
  width: 38px; height: 38px; border-radius: 50%; background: var(--accent);
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; color: #fff; flex-shrink: 0; user-select: none;
  background-size: cover; background-position: center;
  cursor: pointer; transition: opacity 0.12s;
}
.msg-avatar:hover { opacity: 0.85; }
.msg-full {
  display: flex; align-items: flex-start; gap: 12px; padding: 6px 8px 4px;
  border-radius: 4px; position: relative;
}
.msg-full:hover { background: var(--bg-message-hover); }
.msg-grouped-row {
  padding: 1px 8px 1px 60px; border-radius: 4px; line-height: 1.5; position: relative;
}
.msg-grouped-row:hover { background: var(--bg-message-hover); }
.msg-mention { background: rgba(250,168,26,0.08) !important; border-left: 3px solid #faa81a; padding-left: 5px !important; }
.msg-mention:hover { background: rgba(250,168,26,0.14) !important; }
#msgContextMenu { display:none;position:fixed;z-index:9999;background:var(--bg-secondary);border:1px solid var(--border);border-radius:8px;padding:6px 0;min-width:160px;box-shadow:0 4px 20px rgba(0,0,0,0.4);font-size:13px; }
#msgContextMenu .ctx-item { padding:8px 16px;cursor:pointer;color:var(--text-primary);display:flex;align-items:center;gap:8px;transition:background 0.1s; }
#msgContextMenu .ctx-item:hover { background:var(--bg-tertiary); }
#msgContextMenu .ctx-item.danger { color:var(--red); }
#msgContextMenu .ctx-sep { height:1px;background:var(--border);margin:4px 0; }
.msg-content { flex: 1; min-width: 0; }
.msg-header { display: flex; align-items: baseline; gap: 8px; margin-bottom: 2px; }
.msg-name { font-size: 14px; font-weight: 600; color: var(--text-primary); }
.msg-name.is-admin { color: var(--admin-color); }
.msg-timestamp { font-size: 11px; color: var(--text-muted); }
.msg-body { font-size: 14px; color: var(--text-secondary); word-break: break-word; line-height: 1.45; }

.msg-hover-actions {
  display: none; position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
  background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 6px;
  padding: 2px 4px; gap: 2px; align-items: center; z-index: 10;
  box-shadow: 0 2px 8px rgba(0,0,0,0.25);
}
.msg-full:hover .msg-hover-actions,
.msg-grouped-row:hover .msg-hover-actions { display: flex; }
.msg-reaction-btn {
  background: none; border: none; font-size: 15px; cursor: pointer; padding: 3px 5px;
  border-radius: 4px; line-height: 1; color: var(--text-secondary);
  transition: background 0.12s, transform 0.08s;
}
.msg-reaction-btn:hover { background: var(--bg-tertiary); transform: scale(1.18); }
.msg-reactions-row {
  display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px;
}
.msg-reaction-pill {
  display: flex; align-items: center; gap: 3px; padding: 2px 7px; font-size: 12px;
  background: var(--bg-tertiary); border: 1px solid var(--border); border-radius: 20px;
  cursor: pointer; user-select: none; transition: background 0.12s;
  font-weight: 500; color: var(--text-secondary);
}
.msg-reaction-pill:hover { background: var(--bg-message-hover); }
.msg-reaction-pill.mine { border-color: var(--accent); color: var(--accent); background: rgba(var(--accent-rgb,88,101,242),0.08); }

.empty { color: var(--text-muted); text-align: center; margin-top: 60px; font-size: 14px; }

.chat-screen { display: none; height: 100vh; flex-direction: column; }

.banned-section {
  border-top: 1px solid var(--bg-tertiary); padding: 10px 16px;
  max-height: 120px; overflow-y: auto;
}
.banned-header {
  font-size: 11px; font-weight: 700; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px;
}

.dm-spy-section {
  border-top: 1px solid var(--bg-tertiary); padding: 10px;
}
.dm-spy-label {
  padding: 4px 6px; font-size: 11px; font-weight: 700;
  color: var(--dm-color); text-transform: uppercase; letter-spacing: 0.5px;
  margin-bottom: 4px;
}
.dm-spy-item {
  padding: 5px 10px; font-size: 13px; color: var(--text-secondary);
  border-radius: 4px; cursor: pointer; margin-bottom: 1px;
  display: flex; align-items: center; gap: 6px;
}
.dm-spy-item:hover { background: var(--bg-message-hover); }
.dm-spy-item.active { background: var(--bg-message-hover); color: var(--text-primary); }
.dm-spy-icon { color: var(--dm-color); font-size: 14px; }

.gc-create-btn {
  background: var(--accent); color: #fff; border: none; border-radius: 4px;
  width: 20px; height: 20px; font-size: 14px; font-weight: 700; cursor: pointer;
  display: flex; align-items: center; justify-content: center; line-height: 1;
}
.gc-create-btn:hover { opacity: 0.8; }
.gc-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.6); z-index: 1000;
  display: flex; align-items: center; justify-content: center;
}
.gc-modal {
  background: var(--bg-secondary); border-radius: 8px; padding: 20px;
  width: 320px; max-height: 80vh; overflow-y: auto; box-shadow: 0 4px 24px rgba(0,0,0,0.3);
}
.gc-modal-title { font-size: 16px; font-weight: 700; color: var(--text-primary); margin-bottom: 12px; }
.gc-modal-input {
  width: 100%; padding: 8px 10px; border-radius: 4px; border: 1px solid var(--border);
  background: var(--input-bg); color: var(--text-primary); font-size: 13px;
  outline: none; margin-bottom: 10px; box-sizing: border-box;
}
.gc-modal-input:focus { border-color: var(--accent); }
.gc-member-list { max-height: 200px; overflow-y: auto; margin-bottom: 12px; }
.gc-member-item {
  display: flex; align-items: center; gap: 8px; padding: 6px 8px;
  border-radius: 4px; cursor: pointer; font-size: 13px; color: var(--text-secondary);
}
.gc-member-item:hover { background: var(--bg-message-hover); }
.gc-member-item.selected { background: var(--accent); color: #fff; }
.gc-member-item .gc-check {
  width: 16px; height: 16px; border: 2px solid var(--border); border-radius: 3px;
  display: flex; align-items: center; justify-content: center; font-size: 11px;
  flex-shrink: 0;
}
.gc-member-item.selected .gc-check { background: #fff; border-color: #fff; color: var(--accent); }
.gc-modal-btns { display: flex; gap: 8px; justify-content: flex-end; }
.gc-modal-btns button {
  padding: 6px 16px; border-radius: 4px; border: none; font-size: 13px;
  font-weight: 600; cursor: pointer;
}
.gc-modal-btns .gc-cancel { background: var(--bg-tertiary); color: var(--text-secondary); }
.gc-modal-btns .gc-confirm { background: var(--accent); color: #fff; }
.gc-modal-btns .gc-confirm:disabled { opacity: 0.5; cursor: not-allowed; }
.gc-badge { font-size: 10px; font-weight: 600; color: var(--green); margin-left: auto; }

.settings-row {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px; gap: 8px;
}
.settings-label { font-size: 13px; color: var(--text-secondary); flex-shrink: 0; }
.settings-row input[type="text"] {
  flex: 1; padding: 6px 8px; border-radius: 4px; border: 1px solid var(--border);
  background: var(--input-bg); color: var(--text-primary); font-size: 12px; outline: none;
}
.settings-row input[type="text"]:focus { border-color: var(--accent); }
.settings-row input[type="color"] {
  width: 36px; height: 28px; border: 1px solid var(--border); border-radius: 4px;
  padding: 0; cursor: pointer; background: transparent;
}

body.theme-light {
  --bg-primary: #ffffff;
  --bg-secondary: #f2f3f5;
  --bg-tertiary: #e3e5e8;
  --bg-message-hover: #f2f3f5;
  --text-primary: #060607;
  --text-secondary: #4e5058;
  --text-tertiary: #6d6f78;
  --text-muted: #80848e;
  --border: #e3e5e8;
  --input-bg: #e3e5e8;
  --admin-color: #c0392b;
  --dm-color: #8e44ad;
}
body.theme-midnight {
  --bg-primary: #0a0a0f;
  --bg-secondary: #111118;
  --bg-tertiary: #06060a;
  --bg-message-hover: #14141c;
  --text-primary: #e0e0e8;
  --text-secondary: #9a9ab0;
  --text-tertiary: #6a6a80;
  --text-muted: #4a4a5a;
  --border: #1a1a24;
  --input-bg: #14141c;
  --admin-color: #ff5555;
  --dm-color: #bb86fc;
}
body.theme-ocean {
  --bg-primary: #0d1b2a;
  --bg-secondary: #1b2838;
  --bg-tertiary: #0a1520;
  --bg-message-hover: #1f3044;
  --text-primary: #e0f0ff;
  --text-secondary: #8ab4d6;
  --text-tertiary: #5a8aaa;
  --text-muted: #3a6080;
  --border: #1a3050;
  --accent: #1e90ff;
  --accent-hover: #1570cc;
  --input-bg: #162636;
  --admin-color: #ff6b6b;
  --dm-color: #64b5f6;
}
body.theme-forest {
  --bg-primary: #1a2618;
  --bg-secondary: #222e20;
  --bg-tertiary: #141e12;
  --bg-message-hover: #283628;
  --text-primary: #e0f0e0;
  --text-secondary: #8ab88a;
  --text-tertiary: #5a8a5a;
  --text-muted: #3a6a3a;
  --border: #2a3e2a;
  --accent: #2ecc71;
  --accent-hover: #27ae60;
  --input-bg: #1e2e1c;
  --admin-color: #e74c3c;
  --dm-color: #a0d468;
}
body.theme-sunset {
  --bg-primary: #2a1a1e;
  --bg-secondary: #381e24;
  --bg-tertiary: #1e1214;
  --bg-message-hover: #3e242a;
  --text-primary: #ffe8e0;
  --text-secondary: #d4a090;
  --text-tertiary: #a07060;
  --text-muted: #705040;
  --border: #4a2a30;
  --accent: #ff6b35;
  --accent-hover: #e55a2b;
  --input-bg: #321a20;
  --admin-color: #ff4444;
  --dm-color: #ffb380;
}
body.theme-neon {
  --bg-primary: #0a0a14;
  --bg-secondary: #10101e;
  --bg-tertiary: #06060c;
  --bg-message-hover: #161628;
  --text-primary: #e0e0ff;
  --text-secondary: #a0a0d0;
  --text-tertiary: #7070a0;
  --text-muted: #404070;
  --border: #1e1e3a;
  --accent: #ff00ff;
  --accent-hover: #cc00cc;
  --input-bg: #12121e;
  --admin-color: #ff3366;
  --dm-color: #00ffcc;
}
body.theme-rose {
  --bg-primary: #201418;
  --bg-secondary: #2a1a20;
  --bg-tertiary: #180e12;
  --bg-message-hover: #301e26;
  --text-primary: #ffe8f0;
  --text-secondary: #d4a0b8;
  --text-tertiary: #a07088;
  --text-muted: #705060;
  --border: #3a1e2a;
  --accent: #e91e63;
  --accent-hover: #c2185b;
  --input-bg: #261620;
  --admin-color: #ff5252;
  --dm-color: #f48fb1;
}

@media (max-width: 600px) {
  .sidebar { display: none; }
}
""" + tictactoe.get_css() + snake.get_css() + memory.get_css() + blackjack.get_css() + blackjack_multi.get_css() + minesweeper.get_css() + solitaire.get_css() + checkers.get_css() + hangman.get_css() + war.get_css() + crazy_eights.get_css() + twenty_fortyeight.get_css() + """
</style>
</head>
<body>
<div class="join-screen" id="joinScreen">
  <div class="join-box" id="roleBox">
    <h2 style="text-align:center;">&#x1F4AC; Chat</h2>
    <p>How would you like to join?</p>
    <div style="display:flex;gap:8px;flex-wrap:wrap;">
      <button id="guestBtn" data-testid="button-guest" style="flex:1;">Account / Guest</button>
      <button id="staffAdminBtn" data-testid="button-staff-admin" style="flex:1;background:var(--accent);">Admin</button>
      <button id="ownerBtn" data-testid="button-owner" style="flex:1;background:var(--admin-color);">Owner</button>
    </div>
  </div>
  <div class="join-box" id="guestBox" style="display:none;max-width:420px;">
    <div class="join-tabs" id="joinTabBar">
      <button class="join-tab active" id="tabLoginBtn" data-testid="tab-login">Log In</button>
      <button class="join-tab" id="tabRegisterBtn" data-testid="tab-register">Sign Up</button>
      <button class="join-tab" id="tabGuestBtn" data-testid="tab-guest">Guest</button>
    </div>
    <!-- Login Panel -->
    <div id="loginPanel">
      <div class="join-error" id="loginError"></div>
      <label for="loginUsername">Username</label>
      <input type="text" id="loginUsername" data-testid="input-login-username" placeholder="Username..." maxlength="20" autocomplete="username" />
      <label for="loginPassword">Password</label>
      <input type="password" id="loginPassword" data-testid="input-login-password" placeholder="Password..." autocomplete="current-password" />
      <button id="loginBtn" data-testid="button-login">Log In</button>
    </div>
    <!-- Register Panel -->
    <div id="registerPanel" style="display:none;">
      <div class="join-error" id="registerError"></div>
      <label for="registerUsername">Username</label>
      <input type="text" id="registerUsername" data-testid="input-register-username" placeholder="Username (letters, numbers, _-)..." maxlength="20" autocomplete="username" />
      <label for="registerDisplayName">Display Name <span style="font-weight:400;text-transform:none;">(shown in chat)</span></label>
      <input type="text" id="registerDisplayName" data-testid="input-register-displayname" placeholder="Your display name..." maxlength="30" />
      <label for="registerPassword">Password</label>
      <input type="password" id="registerPassword" data-testid="input-register-password" placeholder="At least 6 characters..." autocomplete="new-password" />
      <button id="registerBtn" data-testid="button-register">Create Account</button>
    </div>
    <!-- Guest Panel -->
    <div id="guestPanel" style="display:none;">
      <p style="color:var(--text-muted);font-size:12px;margin-bottom:12px;">Guest mode — no account needed, but your data won't be saved.</p>
      <div class="join-error" id="joinError"></div>
      <label for="usernameInput">Username</label>
      <input type="text" id="usernameInput" data-testid="input-username" placeholder="Enter username..." maxlength="20" />
      <button id="joinBtn" data-testid="button-join">Join as Guest</button>
    </div>
    <button id="backBtn1" data-testid="button-back-guest" style="margin-top:12px;background:var(--input-bg);color:var(--text-secondary);">Back</button>
  </div>
  <div class="join-box" id="staffAdminBox" style="display:none;">
    <h2>Join as Admin</h2>
    <p>Enter your admin key to continue.</p>
    <div class="join-error" id="staffAdminError"></div>
    <label for="staffAdminKeyInput">Admin Key</label>
    <input type="password" id="staffAdminKeyInput" data-testid="input-admin-key" placeholder="Paste admin key here..." />
    <button id="staffAdminLoginBtn" data-testid="button-staff-admin-login">Login</button>
    <button id="backBtn3" data-testid="button-back-staff-admin" style="margin-top:8px;background:var(--input-bg);color:var(--text-secondary);">Back</button>
  </div>
  <div class="join-box" id="adminBox" style="display:none;">
    <h2>Join as Owner</h2>
    <p>Enter the owner key to continue.</p>
    <div class="join-error" id="adminError"></div>
    <label for="adminTokenInput">Owner Key</label>
    <input type="password" id="adminTokenInput" data-testid="input-token" placeholder="Paste owner key here..." />
    <button id="adminLoginBtn" data-testid="button-admin-login">Login</button>
    <button id="backBtn2" data-testid="button-back-admin" style="margin-top:8px;background:var(--input-bg);color:var(--text-secondary);">Back</button>
  </div>
</div>

<!-- Profile Modal -->
<div id="profileModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:2000;align-items:center;justify-content:center;">
  <div style="background:var(--bg-primary);border-radius:10px;padding:28px;max-width:440px;width:90%;max-height:90vh;overflow-y:auto;position:relative;">
    <button id="profileModalClose" style="position:absolute;top:12px;right:14px;background:none;border:none;color:var(--text-muted);font-size:22px;cursor:pointer;line-height:1;">&#x2715;</button>
    <h2 style="font-size:18px;font-weight:700;margin-bottom:18px;">Your Profile</h2>
    <div style="display:flex;flex-direction:column;align-items:center;gap:10px;margin-bottom:20px;">
      <div id="profilePfpPreview" style="width:80px;height:80px;border-radius:50%;background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:32px;font-weight:700;color:#fff;overflow:hidden;border:3px solid var(--border);cursor:pointer;" title="Click to change picture">?</div>
      <input type="file" id="pfpFileInput" accept="image/*" style="display:none;" />
      <button id="changePfpBtn" style="font-size:12px;padding:5px 12px;background:var(--bg-tertiary);color:var(--text-secondary);border:1px solid var(--border);border-radius:4px;cursor:pointer;">Change Picture</button>
      <div style="font-size:12px;color:var(--text-muted);">@<span id="profileUsernameDisplay">username</span></div>
    </div>
    <div class="join-error" id="profileError" style="display:none;"></div>
    <label style="display:block;font-size:12px;font-weight:700;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">Display Name</label>
    <input type="text" id="profileDisplayName" maxlength="30" placeholder="Your display name..." style="width:100%;padding:10px 12px;border:none;border-radius:4px;font-size:14px;margin-bottom:16px;background:var(--bg-tertiary);color:var(--text-primary);outline:none;box-sizing:border-box;" />
    <label style="display:block;font-size:12px;font-weight:700;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">Status</label>
    <select id="profileStatus" style="width:100%;padding:10px 12px;border:none;border-radius:4px;font-size:14px;margin-bottom:16px;background:var(--bg-tertiary);color:var(--text-primary);outline:none;box-sizing:border-box;cursor:pointer;">
      <option value="online">🟢 Online</option>
      <option value="idle">🟡 Idle</option>
      <option value="dnd">🔴 Do Not Disturb</option>
      <option value="invisible">⚫ Invisible</option>
    </select>
    <label style="display:block;font-size:12px;font-weight:700;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.5px;margin-bottom:6px;">Bio</label>
    <textarea id="profileBio" maxlength="300" placeholder="Say something about yourself..." rows="3" style="width:100%;padding:10px 12px;border:none;border-radius:4px;font-size:14px;margin-bottom:16px;background:var(--bg-tertiary);color:var(--text-primary);outline:none;resize:none;font-family:inherit;box-sizing:border-box;"></textarea>
    <button id="saveProfileBtn" style="width:100%;padding:10px;background:var(--accent);color:#fff;border:none;border-radius:4px;font-size:14px;font-weight:600;cursor:pointer;">Save Changes</button>
    <button id="logoutBtn" style="width:100%;padding:10px;background:transparent;color:var(--red);border:1px solid var(--red);border-radius:4px;font-size:13px;font-weight:600;cursor:pointer;margin-top:8px;">Log Out</button>
  </div>
</div>

<!-- PFP Crop Modal -->
<div id="pfpCropModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.92);z-index:3500;align-items:center;justify-content:center;">
  <div style="background:var(--bg-primary);border-radius:14px;padding:24px;max-width:360px;width:95%;position:relative;">
    <h3 style="margin:0 0 14px;font-size:16px;font-weight:700;color:var(--text-primary);">Crop Profile Picture</h3>
    <div id="pfpCropArea" style="position:relative;width:240px;height:240px;margin:0 auto 10px;overflow:hidden;border-radius:50%;border:3px solid var(--accent);cursor:move;user-select:none;background:#111;touch-action:none;">
      <img id="pfpCropImg" style="position:absolute;transform-origin:0 0;pointer-events:none;max-width:none;" src="" alt="" />
    </div>
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
      <span style="font-size:13px;">🔍</span>
      <input type="range" id="pfpCropZoom" min="0.5" max="4" step="0.01" value="1" style="flex:1;accent-color:var(--accent);" />
      <span style="font-size:13px;">🔎</span>
    </div>
    <div style="font-size:11px;color:var(--text-muted);text-align:center;margin-bottom:14px;">Drag to reposition · Slider to zoom</div>
    <div style="display:flex;gap:8px;">
      <button id="pfpCropCancel" style="flex:1;padding:10px;background:var(--bg-tertiary);color:var(--text-secondary);border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;">Cancel</button>
      <button id="pfpCropApply" style="flex:2;padding:10px;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;">✓ Apply</button>
    </div>
  </div>
</div>

<!-- PFP Viewer Modal -->
<div id="pfpViewerModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.88);z-index:3100;align-items:center;justify-content:center;cursor:pointer;" onclick="this.style.display='none'">
  <div style="position:relative;max-width:90vw;max-height:90vh;" onclick="event.stopPropagation()">
    <img id="pfpViewerImg" style="max-width:90vw;max-height:80vh;border-radius:12px;object-fit:contain;display:block;" src="" alt="" />
    <div id="pfpViewerName" style="text-align:center;color:#fff;font-size:15px;font-weight:600;margin-top:10px;"></div>
    <button onclick="document.getElementById('pfpViewerModal').style.display='none'" style="position:absolute;top:-14px;right:-14px;background:rgba(0,0,0,0.6);border:none;color:#fff;font-size:20px;width:32px;height:32px;border-radius:50%;cursor:pointer;line-height:1;">&#x2715;</button>
  </div>
</div>

<!-- DM Panel (right-side overlay) -->
<div id="dmPanel" style="display:none;position:fixed;top:50px;right:0;bottom:0;width:360px;max-width:100vw;background:var(--bg-secondary);border-left:1px solid var(--border);z-index:600;flex-direction:column;box-shadow:-4px 0 20px rgba(0,0,0,0.3);">
  <div style="display:flex;align-items:center;gap:10px;padding:12px 14px;border-bottom:1px solid var(--border);flex-shrink:0;">
    <div id="dmPanelAvatar" style="width:36px;height:36px;border-radius:50%;background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;color:#fff;flex-shrink:0;background-size:cover;background-position:center;"></div>
    <div style="flex:1;min-width:0;">
      <div id="dmPanelName" style="font-size:14px;font-weight:700;color:var(--text-primary);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"></div>
      <div style="font-size:11px;color:var(--text-muted);">Direct Message</div>
    </div>
    <button onclick="closeDmPanel()" style="background:none;border:none;color:var(--text-muted);font-size:20px;cursor:pointer;padding:2px 6px;line-height:1;">&#x2715;</button>
  </div>
  <div id="dmPanelMessages" style="flex:1;overflow-y:auto;padding:12px 14px;display:flex;flex-direction:column;gap:2px;"></div>
  <div style="padding:10px 12px;border-top:1px solid var(--border);flex-shrink:0;display:flex;gap:8px;align-items:center;">
    <input type="text" id="dmPanelInput" placeholder="Message..." style="flex:1;padding:8px 12px;border:none;border-radius:6px;background:var(--bg-tertiary);color:var(--text-primary);font-size:13px;outline:none;" />
    <button id="dmPanelSendBtn" style="padding:8px 14px;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;">Send</button>
  </div>
</div>

<!-- Changelog Modal -->
<div id="changelogModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:2001;align-items:center;justify-content:center;">
  <div style="background:var(--bg-primary);border-radius:10px;padding:28px;max-width:440px;width:90%;position:relative;">
    <h2 style="font-size:18px;font-weight:700;margin-bottom:6px;">&#x1F389; What's New</h2>
    <p style="font-size:12px;color:var(--text-muted);margin-bottom:16px;">Version """ + CURRENT_VERSION + """</p>
    <div style="font-size:14px;color:var(--text-secondary);line-height:1.7;margin-bottom:20px;max-height:52vh;overflow-y:auto;padding-right:8px;scrollbar-width:thin;">""" + CHANGELOG_NOTES + """</div>
    <button id="changelogCloseBtn" style="width:100%;padding:10px;background:var(--accent);color:#fff;border:none;border-radius:4px;font-size:14px;font-weight:600;cursor:pointer;">Got it!</button>
  </div>
</div>

<div class="chat-screen" id="chatScreen">
  <header>
    <h1 data-testid="text-header">Chat</h1>
    <button id="sidebarToggleBtn" title="Toggle Sidebar" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:18px;padding:4px 8px;border-radius:4px;line-height:1;">&#x2630;</button>
    <div class="header-right">
      <div class="status" id="chatStatus"><div class="dot" id="chatStatusDot"></div><span id="chatStatusText">Connected</span></div>
      <button class="theme-btn" id="updatesBtn" data-testid="button-updates" title="What's New" style="font-size:13px;padding:4px 9px;font-weight:600;">&#x1F195;</button>
      <button class="theme-btn" id="helpBtn" title="Keyboard Shortcuts (?)" style="font-size:13px;padding:4px 8px;font-weight:600;">?</button>
      <button class="theme-btn" id="searchBtn" title="Search Messages (Ctrl+F)" style="font-size:14px;padding:4px 8px;">&#x1F50D;</button>
      <button class="theme-btn" id="profileBtn" data-testid="button-profile" title="Your Profile" style="padding:2px;width:30px;height:30px;border-radius:50%;overflow:hidden;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;">&#x1F464;</button>
      <button class="theme-btn" id="settingsBtn" data-testid="button-settings" title="Settings" style="font-size:16px;padding:4px 8px;">&#x2699;</button>
      <button class="theme-btn" id="themeBtn" data-testid="button-theme">Dark</button>
    </div>
  </header>
  <div class="container">
    <div class="sidebar">
      <div class="sidebar-section">
        <div class="sidebar-label">Channels</div>
        <div class="channel-item active" id="channelGeneral" data-testid="channel-general">
          <span class="channel-icon">#</span> General
        </div>
      </div>
      <div class="sidebar-section" id="dmChannelsSection" style="display:none;">
        <div class="sidebar-label">Direct Messages</div>
        <div id="dmChannelsList"></div>
      </div>
      <div class="sidebar-section" id="gcChannelsSection" style="display:none;">
        <div class="sidebar-label" style="display:flex;align-items:center;justify-content:space-between;">Group Chats <button class="gc-create-btn" id="gcCreateBtn" data-testid="button-gc-create" title="Create Group Chat">+</button></div>
        <div id="gcChannelsList"></div>
      </div>
      <div class="sidebar-section">
        <div class="sidebar-label" style="display:flex;align-items:center;justify-content:space-between;">
          Online <span class="count" id="userCount" data-testid="text-user-count">0</span>
          <button id="sortUsersBtn" title="Sort A-Z" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:11px;padding:2px 5px;border-radius:3px;">A-Z</button>
        </div>
        <input id="userSearchInput" type="text" placeholder="Search users..." autocomplete="off" style="width:100%;margin:3px 0 4px;padding:4px 8px;border:1px solid var(--border);border-radius:4px;background:var(--input-bg);color:var(--text-primary);font-size:12px;outline:none;box-sizing:border-box;" />
      </div>
      <div class="user-list-area" id="userList" data-testid="list-users"></div>
      <div id="dmSpySection" class="dm-spy-section" style="display:none;">
        <div class="dm-spy-label">DM Spy</div>
        <div id="dmSpyList"></div>
      </div>
      <div id="bannedSection" class="banned-section" style="display:none;">
        <div class="banned-header">Banned</div>
        <div id="bannedList"></div>
      </div>
      <div id="logsSection" class="dm-spy-section" style="display:none;">
        <div class="dm-spy-label" style="display:flex;align-items:center;justify-content:space-between;">Logs <button class="gc-create-btn" id="viewLogsBtn" data-testid="button-view-logs" title="View Logs" style="font-size:11px;width:auto;padding:0 6px;">View</button></div>
      </div>
      <div id="mailboxSection" class="dm-spy-section" style="display:none;">
        <div class="dm-spy-label" style="display:flex;align-items:center;justify-content:space-between;color:var(--orange);">Mailbox <span class="dm-badge" id="mailboxBadge" style="display:none;">0</span></div>
        <div class="dm-spy-item" id="suggestionsBtn" data-testid="button-suggestions" style="cursor:pointer;"><span class="dm-spy-icon" style="color:var(--orange);">IN</span><span>Suggestions</span></div>
        <div class="dm-spy-item" id="adminCreatorBtn" data-testid="button-admin-creator" style="cursor:pointer;display:none;"><span class="dm-spy-icon" style="color:var(--green);">+</span><span>Create Admin</span></div>
        <div class="dm-spy-item" id="manageAdminsBtn" data-testid="button-manage-admins" style="cursor:pointer;display:none;"><span class="dm-spy-icon" style="color:var(--accent);">A</span><span>Manage Admins</span></div>
        <div class="dm-spy-item" id="broadcastBtn" data-testid="button-broadcast" style="cursor:pointer;display:none;"><span class="dm-spy-icon" style="color:#e74c3c;">📢</span><span>Broadcast</span></div>
        <div class="dm-spy-item" id="slowmodeBtn" style="cursor:pointer;display:none;"><span class="dm-spy-icon" style="color:var(--orange);">⏱</span><span id="slowmodeBtnLabel">Slowmode: Off</span></div>
        <div class="dm-spy-item" id="announcementBtn" style="cursor:pointer;display:none;"><span class="dm-spy-icon" style="color:var(--accent);">📣</span><span id="announcementBtnLabel">Announce Mode: Off</span></div>
        <div class="dm-spy-item" id="motdBtn" style="cursor:pointer;display:none;"><span class="dm-spy-icon" style="color:var(--green);">📌</span><span>Set MOTD</span></div>
        <div class="dm-spy-item" id="wordFilterBtn" style="cursor:pointer;display:none;"><span class="dm-spy-icon" style="color:var(--red,#f04747);">🚫</span><span>Word Filter</span></div>
        <div class="dm-spy-item" id="bulkClearBtn" style="cursor:pointer;display:none;"><span class="dm-spy-icon" style="color:var(--red,#f04747);">🗑</span><span>Bulk Clear Chat</span></div>
        <div class="dm-spy-item" id="exportLogsBtn" style="cursor:pointer;display:none;"><span class="dm-spy-icon" style="color:var(--text-secondary);">📥</span><span>Export Logs</span></div>
      </div>
      <div id="suggestBoxSection" class="dm-spy-section" style="display:none;">
        <div class="dm-spy-label" style="color:var(--green);">Send Suggestion</div>
        <div style="padding:4px 0;">
          <input type="text" id="suggestInput" data-testid="input-suggestion" placeholder="Type a suggestion..." style="width:100%;padding:6px 8px;border-radius:4px;border:1px solid var(--border);background:var(--input-bg);color:var(--text-primary);font-size:12px;outline:none;box-sizing:border-box;" />
          <button id="suggestSendBtn" data-testid="button-send-suggestion" style="margin-top:4px;width:100%;padding:4px;background:var(--accent);color:#fff;border:none;border-radius:4px;font-size:12px;cursor:pointer;">Send</button>
        </div>
      </div>
    </div>
    <div class="main-panel">
      <div class="tab-bar">
        <div class="tab-items" id="tabItems" data-testid="tab-bar"></div>
        <button class="new-tab-btn" id="newTabBtn" data-testid="button-new-tab" title="New Tab">+</button>
      </div>
      <div id="tabContents">
        <div class="tab-content active" id="tabContent-chat" style="flex-direction:row;">
          <div class="chat-area" style="flex:1;min-width:0;">
            <div class="channel-header" id="channelHeaderBar">
              <span class="channel-hash">#</span><span id="channelName" data-testid="text-channel-name">General</span>
            </div>
            <div class="msg-search-bar" id="msgSearchBar">
              <input type="text" id="msgSearchInput" placeholder="Search messages… (Esc to close)" autocomplete="off" />
              <span class="srch-count" id="msgSearchCount"></span>
              <button onclick="closeSearch()" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:16px;padding:2px 6px;">✕</button>
            </div>
            <div style="position:relative;flex:1;display:flex;flex-direction:column;min-height:0;">
              <div id="messages" data-testid="list-messages">
                <div class="empty" id="emptyState">No messages yet</div>
              </div>
              <button id="scrollToBottomBtn" title="Jump to latest" style="display:none;position:absolute;bottom:12px;right:18px;z-index:90;background:var(--accent);color:#fff;border:none;border-radius:50%;width:36px;height:36px;font-size:18px;cursor:pointer;box-shadow:0 2px 12px rgba(0,0,0,0.4);align-items:center;justify-content:center;padding:0;line-height:1;">↓</button>
            </div>
            <div class="input-bar" id="inputBar">
              <div class="image-preview-bar" id="imagePreviewBar" style="display:none;"></div>
              <div id="replyPreviewBar" style="display:none;align-items:center;gap:8px;padding:6px 12px;background:var(--bg-tertiary);border-left:3px solid var(--accent);border-radius:4px;margin-bottom:4px;font-size:12px;color:var(--text-secondary);max-width:100%;overflow:hidden;"></div>
              <div id="mentionDropdown" style="display:none;position:absolute;bottom:100%;left:0;right:0;background:var(--bg-primary);border:1px solid var(--border);border-radius:8px;box-shadow:0 -4px 20px rgba(0,0,0,0.25);max-height:180px;overflow-y:auto;z-index:200;margin:0 16px 4px;"></div>
              <div id="slashDropdown" class="slash-dropdown"></div>
              <div class="fmt-toolbar" id="fmtToolbar">
                <button class="fmt-btn" title="Bold (Ctrl+B)" onclick="wrapSel('**','**')"><b>B</b></button>
                <button class="fmt-btn" title="Italic (Ctrl+I)" onclick="wrapSel('_','_')"><i>I</i></button>
                <button class="fmt-btn" title="Strikethrough" onclick="wrapSel('~~','~~')"><s>S</s></button>
                <button class="fmt-btn" title="Inline code" onclick="wrapSel('\`','\`')">&#x3C;/&#x3E;</button>
                <button class="fmt-btn" title="Code block" onclick="wrapSel('\`\`\`\n','\n\`\`\`')">&#x1F4CB;</button>
                <span style="flex:1;"></span>
                <span id="slowBadge" class="slow-badge" style="display:none;">&#x23F1; Slowmode ON</span>
              </div>
              <div class="input-bar-row">
                <input type="text" id="nameInput" data-testid="input-admin-name" placeholder="Your name" value="Admin" style="display:none;width:140px;flex:unset;" />
                <button class="attach-btn" id="attachBtn" data-testid="button-attach" type="button" title="Attach image">&#x1F4CE;</button>
                <input type="file" id="fileInput" accept="image/*" multiple style="display:none;" />
                <input type="text" id="msgInput" data-testid="input-message" placeholder="Type a message..." />
                <div class="emoji-picker-container">
                  <button class="emoji-picker-btn" id="emojiBtn" data-testid="button-emoji" type="button" title="Emoji picker">&#x1F600;</button>
                  <div class="emoji-panel" id="emojiPanel">
                    <input type="text" class="emoji-search" id="emojiSearch" data-testid="input-emoji-search" placeholder="Search emojis..." />
                    <div class="emoji-panel-header" id="emojiCatBar"></div>
                    <div class="emoji-grid" id="emojiGrid" data-testid="grid-emoji"></div>
                  </div>
                </div>
                <span class="char-counter" id="charCounter" style="display:none;">0</span>
                <button id="sendBtn" data-testid="button-send" title="Send (Enter)">&#x27A4;</button>
              </div>
            </div>
          </div>
          <!-- DM Profile Sidebar -->
          <div id="dmProfileSidebar" style="display:none;width:260px;min-width:240px;flex-direction:column;border-left:1px solid var(--border);background:var(--bg-secondary);overflow-y:auto;flex-shrink:0;">
            <div style="padding:14px 14px 0;display:flex;justify-content:space-between;align-items:center;">
              <span style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--text-muted);">Profile</span>
              <div style="display:flex;gap:4px;">
                <button id="dmPopOutBtn" title="Pop out DM" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:16px;padding:2px 5px;border-radius:4px;line-height:1;" title="Pop Out">&#x2197;</button>
                <button id="dmSidebarCollapseBtn" title="Hide panel" style="background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:16px;padding:2px 5px;border-radius:4px;line-height:1;">&#x2715;</button>
              </div>
            </div>
            <div style="display:flex;flex-direction:column;align-items:center;padding:16px 16px 12px;">
              <div id="dmPeerAvatarLarge" style="width:80px;height:80px;border-radius:50%;background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:700;color:#fff;background-size:cover;background-position:center;box-shadow:0 4px 16px rgba(0,0,0,0.25);flex-shrink:0;margin-bottom:10px;"></div>
              <div id="dmPeerDisplayName" style="font-size:15px;font-weight:700;color:var(--text-primary);text-align:center;"></div>
              <div id="dmPeerUsername" style="font-size:12px;color:var(--text-muted);margin-top:2px;text-align:center;"></div>
              <div id="dmPeerStatusBadge" style="display:inline-flex;align-items:center;gap:5px;margin-top:8px;padding:3px 10px;border-radius:20px;font-size:11px;font-weight:600;background:var(--bg-tertiary);color:var(--text-secondary);"></div>
            </div>
            <div style="height:1px;background:var(--border);margin:0 14px;"></div>
            <div style="padding:12px 14px;">
              <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--text-muted);margin-bottom:6px;">About Me</div>
              <div id="dmPeerBio" style="font-size:13px;color:var(--text-secondary);line-height:1.55;"></div>
            </div>
            <div style="height:1px;background:var(--border);margin:0 14px;"></div>
            <div style="padding:12px 14px;">
              <div style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:var(--text-muted);margin-bottom:6px;">Note (private)</div>
              <textarea id="dmPeerNoteArea" placeholder="Add a private note about this person..." style="width:100%;min-height:70px;padding:7px 9px;border-radius:6px;border:1px solid var(--border);background:var(--input-bg);color:var(--text-primary);font-size:12px;outline:none;resize:vertical;box-sizing:border-box;font-family:inherit;"></textarea>
            </div>
            <div style="height:1px;background:var(--border);margin:0 14px;"></div>
            <div style="padding:10px 14px;display:flex;flex-direction:column;gap:6px;">
              <button id="dmViewAttachmentsBtn" style="width:100%;padding:7px 10px;background:var(--bg-tertiary);color:var(--text-primary);border:1px solid var(--border);border-radius:6px;cursor:pointer;font-size:12px;text-align:left;display:flex;align-items:center;gap:6px;">&#x1F4CE; View Shared Images</button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
var ws = null;
var myUsername = '';
var myDisplayName = '';
var myPfpData = '';
var myBio = '';
var mySessionToken = localStorage.getItem('chat_session_token') || '';
var myIsGuest = false;
var isAdmin = false;
var isOwner = false;
var isStaffAdmin = false;
var myRole = 'guest';
var currentChannel = 'general';
var generalMessages = [];
var dmMessages = {};
var dmUnread = {};
var onlineUsers = [];
var activeDmPairs = [];
var gcList = {};
var gcMessages = {};
var gcUnread = {};
var themes = ['theme-dark', 'theme-light', 'theme-midnight', 'theme-ocean', 'theme-forest', 'theme-sunset', 'theme-neon', 'theme-rose'];
var themeLabels = ['Dark', 'Light', 'Midnight', 'Ocean', 'Forest', 'Sunset', 'Neon', 'Rose'];
var themeIdx = parseInt(localStorage.getItem('chat-theme') || '0');

function applyTheme() {
  document.body.className = themes[themeIdx] || '';
  document.getElementById('themeBtn').textContent = themeLabels[themeIdx];
  localStorage.setItem('chat-theme', themeIdx);
}
applyTheme();

document.getElementById('themeBtn').addEventListener('click', function() {
  themeIdx = (themeIdx + 1) % themes.length;
  applyTheme();
});

document.getElementById('guestBtn').addEventListener('click', function() {
  localStorage.setItem('chat-last-role', 'guest');
  document.getElementById('roleBox').style.display = 'none';
  document.getElementById('guestBox').style.display = 'block';
  document.getElementById('loginUsername').focus();
});
// Auto-highlight last used role
(function() {
  var lastRole = localStorage.getItem('chat-last-role');
  if (!lastRole) return;
  var map = {guest: 'guestBtn', owner: 'ownerBtn', staff: 'staffAdminBtn'};
  var btn = document.getElementById(map[lastRole]);
  if (btn) { btn.style.boxShadow = '0 0 0 2px var(--accent)'; btn.title = 'Last used'; }
})();

function setJoinTab(tab) {
  ['login','register','guest'].forEach(function(t) {
    document.getElementById('tab'+t.charAt(0).toUpperCase()+t.slice(1)+'Btn').classList.toggle('active', t===tab);
    document.getElementById(t+'Panel').style.display = t===tab ? 'block' : 'none';
  });
}
document.getElementById('tabLoginBtn').addEventListener('click', function() { setJoinTab('login'); });
document.getElementById('tabRegisterBtn').addEventListener('click', function() { setJoinTab('register'); });
document.getElementById('tabGuestBtn').addEventListener('click', function() { setJoinTab('guest'); });

function doLogin() {
  var un = document.getElementById('loginUsername').value.trim();
  var pw = document.getElementById('loginPassword').value;
  var err = document.getElementById('loginError');
  err.style.display='none';
  if (!un || !pw) { err.textContent='Please fill in all fields.'; err.style.display='block'; return; }
  fetch('/api/login', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:un,password:pw})})
    .then(function(r){return r.json();})
    .then(function(d){
      if (d.error) { err.textContent=d.error; err.style.display='block'; return; }
      localStorage.setItem('chat_session_token', d.session_token);
      mySessionToken = d.session_token;
      myUsername = d.username;
      myDisplayName = d.display_name || d.username;
      myPfpData = d.pfp_data || '';
      myBio = d.bio || '';
      myIsGuest = false;
      document.getElementById('joinScreen').style.display = 'none';
      document.getElementById('chatScreen').style.display = 'flex';
      connectGuest(d.username);
      document.getElementById('msgInput').focus();
    }).catch(function(){err.textContent='Connection error.'; err.style.display='block';});
}

function doRegister() {
  var un = document.getElementById('registerUsername').value.trim();
  var dn = document.getElementById('registerDisplayName').value.trim() || un;
  var pw = document.getElementById('registerPassword').value;
  var err = document.getElementById('registerError');
  err.style.display='none';
  if (!un || !pw) { err.textContent='Please fill in username and password.'; err.style.display='block'; return; }
  if (!/^[a-zA-Z0-9_-]{1,20}$/.test(un)) { err.textContent='Username: letters, numbers, _ or - only (1-20 chars).'; err.style.display='block'; return; }
  if (pw.length < 6) { err.textContent='Password must be at least 6 characters.'; err.style.display='block'; return; }
  if (RESERVED.test(un)) { err.textContent='Username cannot contain "admin", "mod", or "owner".'; err.style.display='block'; return; }
  fetch('/api/register', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:un,display_name:dn,password:pw})})
    .then(function(r){return r.json();})
    .then(function(d){
      if (d.error) { err.textContent=d.error; err.style.display='block'; return; }
      localStorage.setItem('chat_session_token', d.session_token);
      mySessionToken = d.session_token;
      myUsername = d.username;
      myDisplayName = d.display_name || d.username;
      myPfpData = '';
      myBio = '';
      myIsGuest = false;
      document.getElementById('joinScreen').style.display = 'none';
      document.getElementById('chatScreen').style.display = 'flex';
      connectGuest(d.username);
      document.getElementById('msgInput').focus();
    }).catch(function(){err.textContent='Connection error.'; err.style.display='block';});
}

document.getElementById('loginBtn').addEventListener('click', doLogin);
document.getElementById('loginPassword').addEventListener('keydown', function(e){if(e.key==='Enter')doLogin();});
document.getElementById('loginUsername').addEventListener('keydown', function(e){if(e.key==='Enter')doLogin();});
document.getElementById('registerBtn').addEventListener('click', doRegister);
document.getElementById('registerPassword').addEventListener('keydown', function(e){if(e.key==='Enter')doRegister();});

if (mySessionToken) {
  fetch('/api/profile', {headers:{'X-Session-Token':mySessionToken}})
    .then(function(r){return r.json();})
    .then(function(d){
      if (d.username) {
        myUsername = d.username;
        myDisplayName = d.display_name || d.username;
        myPfpData = d.pfp_data || '';
        myBio = d.bio || '';
        myIsGuest = false;
        document.getElementById('joinScreen').style.display = 'none';
        document.getElementById('chatScreen').style.display = 'flex';
        connectGuest(d.username);
        document.getElementById('msgInput').focus();
      }
    }).catch(function(){});
}
document.getElementById('ownerBtn').addEventListener('click', function() {
  localStorage.setItem('chat-last-role', 'owner');
  document.getElementById('roleBox').style.display = 'none';
  document.getElementById('adminBox').style.display = 'block';
  document.getElementById('adminTokenInput').focus();
});
document.getElementById('staffAdminBtn').addEventListener('click', function() {
  localStorage.setItem('chat-last-role', 'staff');
  document.getElementById('roleBox').style.display = 'none';
  document.getElementById('staffAdminBox').style.display = 'block';
  document.getElementById('staffAdminKeyInput').focus();
});
document.getElementById('backBtn1').addEventListener('click', function() {
  document.getElementById('guestBox').style.display = 'none';
  document.getElementById('roleBox').style.display = 'block';
});
document.getElementById('backBtn2').addEventListener('click', function() {
  document.getElementById('adminBox').style.display = 'none';
  document.getElementById('roleBox').style.display = 'block';
});
document.getElementById('backBtn3').addEventListener('click', function() {
  document.getElementById('staffAdminBox').style.display = 'none';
  document.getElementById('roleBox').style.display = 'block';
});

function switchChannel(channel) {
  // Save current draft before switching
  var prevInput = document.getElementById('msgInput');
  if (prevInput && currentChannel) {
    if (prevInput.value.trim()) localStorage.setItem('draft:' + currentChannel, prevInput.value);
    else localStorage.removeItem('draft:' + currentChannel);
  }
  currentChannel = channel;
  renderMessages();
  renderSidebar();
  var headerBar = document.getElementById('channelHeaderBar');
  var dmSidebar = document.getElementById('dmProfileSidebar');
  if (channel === 'general') {
    headerBar.innerHTML = '<span class="channel-icon">#</span> <span id="channelName" data-testid="text-channel-name">General</span>';
    document.getElementById('msgInput').placeholder = 'Message #General';
    document.getElementById('msgInput').disabled = false;
    if (dmSidebar) dmSidebar.style.display = 'none';
  } else if (channel.startsWith('dm:')) {
    var target = channel.substring(3);
    var uObj = getUserObj(target);
    var dname = typeof uObj === 'string' ? uObj : (uObj.display_name || uObj.name || target);
    var statusColors2 = {online:'#43b581',idle:'#faa61a',dnd:'#f04747',invisible:'#747f8d',offline:'#747f8d'};
    var uStatus = typeof uObj === 'string' ? 'online' : (uObj.status || 'online');
    var uPfp = typeof uObj === 'string' ? '' : (uObj.pfp || '');
    var avatarHtml = uPfp
      ? '<div style="width:22px;height:22px;border-radius:50%;background-image:url('+uPfp+');background-size:cover;background-position:center;flex-shrink:0;"></div>'
      : '<div style="width:22px;height:22px;border-radius:50%;background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:9px;font-weight:700;color:#fff;flex-shrink:0;">'+escapeHtml(dname.substring(0,2).toUpperCase())+'</div>';
    var dotColor = statusColors2[uStatus] || statusColors2.online;
    headerBar.innerHTML = '<div style="display:flex;align-items:center;gap:8px;flex:1;min-width:0;">'
      + '<div style="position:relative;flex-shrink:0;">'
      + avatarHtml
      + '<div style="width:8px;height:8px;border-radius:50%;background:'+dotColor+';border:2px solid var(--bg-tertiary);position:absolute;bottom:-1px;right:-1px;"></div>'
      + '</div>'
      + '<span class="channel-icon" style="color:var(--dm-color);">@</span>'
      + '<span id="channelName" data-testid="text-channel-name" class="dm-label" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">'+escapeHtml(dname)+'</span>'
      + '</div>'
      + '<button id="dmShowProfileBtn" title="Toggle profile panel" style="flex-shrink:0;background:none;border:1px solid var(--border);color:var(--text-muted);font-size:12px;padding:3px 9px;border-radius:5px;cursor:pointer;display:flex;align-items:center;gap:4px;">&#x1F464; Profile</button>';
    document.getElementById('msgInput').placeholder = 'Message @' + dname;
    document.getElementById('msgInput').disabled = false;
    if (dmUnread[target]) { dmUnread[target] = 0; renderDmChannels(); }
    if (dmSidebar) updateDmProfileSidebar(target);
    (function(t) {
      var btn = document.getElementById('dmShowProfileBtn');
      if (btn) btn.addEventListener('click', function() {
        var s = document.getElementById('dmProfileSidebar');
        if (s) {
          if (s.style.display === 'none' || !s.style.display) { updateDmProfileSidebar(t); }
          else { s.style.display = 'none'; }
        }
      });
    })(target);
  } else if (channel.startsWith('gc:')) {
    var gcId = channel.substring(3);
    var gc = gcList[gcId];
    var gcName = gc ? gc.name : 'Group';
    var gcMemberCount = gc && gc.members ? gc.members.length : 0;
    headerBar.innerHTML = '<span class="channel-icon" style="color:var(--green);">#</span> <span id="channelName" data-testid="text-channel-name">' + escapeHtml(gcName) + '</span>'
      + (gcMemberCount ? '<span style="font-size:11px;color:var(--text-muted);margin-left:8px;">'+gcMemberCount+' members</span>' : '');
    (function(gid, gname) {
      var leaveBtn = document.createElement('button');
      leaveBtn.textContent = 'Leave';
      leaveBtn.title = 'Leave this group chat';
      leaveBtn.style.cssText = 'margin-left:auto;padding:3px 10px;background:none;border:1px solid var(--red,#f04747);color:var(--red,#f04747);border-radius:5px;cursor:pointer;font-size:11px;font-weight:600;';
      leaveBtn.addEventListener('click', function() {
        if (confirm('Leave ' + gname + '?')) {
          ws.send(JSON.stringify({type:'gc_leave', gc_id:gid}));
          delete gcList[gid]; delete gcMessages[gid]; delete gcUnread[gid];
          switchChannel('general'); renderGcChannels();
          showToast('Left ' + gname, 'info');
        }
      });
      headerBar.appendChild(leaveBtn);
    })(gcId, gcName);
    document.getElementById('msgInput').placeholder = 'Message #' + gcName;
    document.getElementById('msgInput').disabled = false;
    if (gcUnread[gcId]) { gcUnread[gcId] = 0; renderGcChannels(); }
    if (dmSidebar) dmSidebar.style.display = 'none';
  } else if (channel.startsWith('spy:')) {
    var parts = channel.substring(4);
    headerBar.innerHTML = '<span class="dm-spy-icon">SPY</span> <span id="channelName" data-testid="text-channel-name" style="color:var(--dm-color);">DM Spy: ' + escapeHtml(parts) + '</span>';
    document.getElementById('msgInput').placeholder = 'Viewing DMs (read-only)';
    document.getElementById('msgInput').disabled = true;
    if (dmSidebar) dmSidebar.style.display = 'none';
  }
  // Restore draft for new channel
  var draftKey = 'draft:' + channel;
  var draft = localStorage.getItem(draftKey);
  var inp = document.getElementById('msgInput');
  if (inp) {
    if (draft && !inp.disabled) { inp.value = draft; }
    inp.focus();
    inp.setSelectionRange(inp.value.length, inp.value.length);
  }
}

function updateDmProfileSidebar(target) {
  var sidebar = document.getElementById('dmProfileSidebar');
  if (!sidebar) return;
  var uObj = getUserObj(target);
  var displayName = typeof uObj === 'string' ? uObj : (uObj.display_name || uObj.name || target);
  var pfp = typeof uObj === 'string' ? '' : (uObj.pfp || '');
  var bio = typeof uObj === 'string' ? '' : (uObj.bio || '');
  var status = typeof uObj === 'string' ? 'online' : (uObj.status || 'online');
  var statusColorMap = {online:'#43b581',idle:'#faa61a',dnd:'#f04747',invisible:'#747f8d',offline:'#747f8d'};
  var statusLabelMap = {online:'Online',idle:'Idle',dnd:'Do Not Disturb',invisible:'Invisible',offline:'Offline'};
  var avatarEl = document.getElementById('dmPeerAvatarLarge');
  if (avatarEl) {
    if (pfp) {
      avatarEl.style.backgroundImage = 'url(' + pfp + ')';
      avatarEl.style.backgroundSize = 'cover';
      avatarEl.style.backgroundPosition = 'center';
      avatarEl.textContent = '';
    } else {
      avatarEl.style.backgroundImage = '';
      avatarEl.style.backgroundSize = '';
      avatarEl.textContent = displayName.substring(0,2).toUpperCase();
    }
  }
  var dnEl = document.getElementById('dmPeerDisplayName');
  if (dnEl) dnEl.textContent = displayName;
  var unEl = document.getElementById('dmPeerUsername');
  if (unEl) unEl.textContent = '@' + target;
  var badge = document.getElementById('dmPeerStatusBadge');
  if (badge) {
    var sc = statusColorMap[status] || statusColorMap.online;
    badge.innerHTML = '<div style="width:8px;height:8px;border-radius:50%;background:'+sc+';flex-shrink:0;"></div>' + (statusLabelMap[status] || 'Online');
  }
  var bioEl = document.getElementById('dmPeerBio');
  if (bioEl) bioEl.textContent = bio || 'No bio set.';
  var noteEl = document.getElementById('dmPeerNoteArea');
  if (noteEl) {
    var noteKey = 'peer_note_' + target;
    noteEl.value = localStorage.getItem(noteKey) || '';
    noteEl.oninput = function() { localStorage.setItem(noteKey, noteEl.value); };
  }
  var popOut = document.getElementById('dmPopOutBtn');
  if (popOut) {
    popOut.onclick = function() { openDmPanel(target, getUserObj(target)); };
  }
  var collapse = document.getElementById('dmSidebarCollapseBtn');
  if (collapse) {
    collapse.onclick = function() { sidebar.style.display = 'none'; };
  }
  var attachBtn2 = document.getElementById('dmViewAttachmentsBtn');
  if (attachBtn2) {
    attachBtn2.onclick = function() { showDmSharedImages(target); };
  }
  sidebar.style.display = 'flex';
}

function showDmSharedImages(target) {
  var msgs = dmMessages[target] || [];
  var imgs = msgs.filter(function(m) { return m.text && /^data:image\//i.test(m.text); });
  if (imgs.length === 0) { showToast('No shared images in this DM yet.', 'info'); return; }
  var modal = document.createElement('div');
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.75);z-index:3000;display:flex;align-items:center;justify-content:center;';
  var box = document.createElement('div');
  box.style.cssText = 'background:var(--bg-primary);border-radius:10px;padding:18px;max-width:90vw;max-height:80vh;overflow-y:auto;display:flex;flex-direction:column;gap:10px;min-width:280px;';
  var header = document.createElement('div');
  header.style.cssText = 'display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;';
  header.innerHTML = '<span style="font-weight:700;font-size:15px;color:var(--text-primary);">Shared Images ('+imgs.length+')</span>';
  var closeBtn2 = document.createElement('button');
  closeBtn2.textContent = '×';
  closeBtn2.style.cssText = 'background:none;border:none;color:var(--text-muted);font-size:22px;cursor:pointer;';
  closeBtn2.onclick = function() { document.body.removeChild(modal); };
  header.appendChild(closeBtn2);
  box.appendChild(header);
  var grid = document.createElement('div');
  grid.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fill,minmax(100px,1fr));gap:6px;';
  imgs.forEach(function(m) {
    var img = document.createElement('img');
    img.src = m.text;
    img.style.cssText = 'width:100%;aspect-ratio:1;object-fit:cover;border-radius:6px;cursor:pointer;';
    img.onclick = function() { openLightbox(m.text); };
    grid.appendChild(img);
  });
  box.appendChild(grid);
  modal.appendChild(box);
  modal.onclick = function(e) { if (e.target === modal) document.body.removeChild(modal); };
  document.body.appendChild(modal);
}

function openLightbox(src) {
  var modal = document.createElement('div');
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.88);z-index:4000;display:flex;align-items:center;justify-content:center;cursor:zoom-out;';
  var img = document.createElement('img');
  img.src = src;
  img.style.cssText = 'max-width:90vw;max-height:90vh;border-radius:8px;box-shadow:0 8px 40px rgba(0,0,0,0.5);';
  modal.appendChild(img);
  modal.onclick = function() { document.body.removeChild(modal); };
  document.body.appendChild(modal);
}

function escapeHtml(s) {
  var d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

var IMAGE_EXTS = /\.(png|jpg|jpeg|gif|webp|svg|bmp|apng)(\?.*)?$/i;
var GIF_HOSTS = /tenor\.com|giphy\.com|gfycat\.com|imgur\.com/i;
var URL_RE = /(https?:\/\/[^\s<>"']+)/g;
var pendingImages = []; // {dataUrl, name}

function isImageUrl(url) {
  if (/^data:image\//i.test(url)) return true;
  if (IMAGE_EXTS.test(url)) return true;
  if (GIF_HOSTS.test(url) && /\.(gif|webp|mp4)(\?.*)?$/i.test(url)) return true;
  if (/media\d*\.giphy\.com/i.test(url)) return true;
  if (/i\.imgur\.com/i.test(url)) return true;
  if (/tenor\.com.*\.gif/i.test(url)) return true;
  return false;
}

var _RE_CODEBLOCK = new RegExp('\x60\x60\x60([\\s\\S]*?)\x60\x60\x60', 'g');
var _RE_CODEINLINE = new RegExp('\x60([^\x60\\n]+)\x60', 'g');
function applyMarkdown(text) {
  // Code blocks (```...```)
  text = text.replace(_RE_CODEBLOCK, function(m, code) {
    return '<code style="display:block;background:var(--bg-tertiary);padding:8px 10px;border-radius:5px;font-family:monospace;font-size:12px;white-space:pre-wrap;margin:4px 0;">' + escapeHtml(code.trim()) + '</code>';
  });
  // Inline code
  text = text.replace(_RE_CODEINLINE, function(m, code) {
    return '<code style="background:var(--bg-tertiary);padding:1px 5px;border-radius:3px;font-family:monospace;font-size:12px;">' + escapeHtml(code) + '</code>';
  });
  // Bold **text**
  text = text.replace(/\*\*([^*\\n]+)\*\*/g, '<strong>$1</strong>');
  // Italic _text_
  text = text.replace(/_([^_\\n]+)_/g, '<em>$1</em>');
  // Strikethrough ~~text~~
  text = text.replace(/~~([^~\\n]+)~~/g, '<s>$1</s>');
  // @mention highlight
  if (myUsername) {
    var safe = myUsername.replace(/[.*+?^${}()|[\\]\\\\]/g,'\\$&');
    var reMention = new RegExp('@(' + safe + ')\\b', 'gi');
    text = text.replace(reMention, '<span style="background:rgba(88,101,242,0.25);color:var(--accent);border-radius:3px;padding:0 3px;font-weight:600;">@$1</span>');
  }
  return text;
}

function renderRichText(text) {
  var container = document.createElement('span');
  container.className = 'msg-body';
  // Handle data: image URLs specially
  if (/^data:image\//i.test(text)) {
    var img = document.createElement('img');
    img.className = 'msg-img-attachment';
    img.src = text;
    img.alt = 'Image';
    img.addEventListener('click', function() { openLightbox(text); });
    container.appendChild(img);
    return container;
  }
  var parts = text.split(URL_RE);
  for (var i = 0; i < parts.length; i++) {
    var part = parts[i];
    if (!part) continue;
    if (/^https?:\/\//i.test(part)) {
      if (isImageUrl(part)) {
        var img2 = document.createElement('img');
        img2.className = 'msg-img-attachment';
        img2.src = part;
        img2.alt = 'Image';
        img2.loading = 'lazy';
        img2.addEventListener('click', function() { openLightbox(this.src); });
        img2.addEventListener('error', function() {
          var link = document.createElement('a');
          link.href = this.src; link.target = '_blank'; link.rel = 'noopener noreferrer';
          link.textContent = this.src;
          this.parentNode.replaceChild(link, this);
        });
        container.appendChild(img2);
      } else {
        var link = document.createElement('a');
        link.href = '#';
        link.rel = 'noopener noreferrer';
        link.textContent = part;
        link.style.cssText = 'color:var(--accent);text-decoration:underline;cursor:pointer;';
        (function(u) {
          link.addEventListener('click', function(e) {
            e.preventDefault();
            openBrowserTab(u);
          });
        })(part);
        container.appendChild(link);
      }
    } else {
      var span = document.createElement('span');
      span.innerHTML = applyMarkdown(escapeHtml(part));
      // Add copy buttons to block code elements
      span.querySelectorAll('code').forEach(function(codeEl) {
        if (codeEl.style.display !== 'block') return;
        var wrap = document.createElement('div');
        wrap.style.cssText = 'position:relative;margin:4px 0;';
        codeEl.style.margin = '0';
        codeEl.parentNode.insertBefore(wrap, codeEl);
        wrap.appendChild(codeEl);
        var cpBtn = document.createElement('button');
        cpBtn.textContent = '⎘';
        cpBtn.title = 'Copy code';
        cpBtn.style.cssText = 'position:absolute;top:4px;right:4px;background:var(--bg-secondary);border:1px solid var(--border);color:var(--text-muted);cursor:pointer;font-size:11px;padding:2px 5px;border-radius:3px;line-height:1;';
        cpBtn.addEventListener('click', function() {
          var txt = codeEl.textContent;
          (navigator.clipboard ? navigator.clipboard.writeText(txt) : Promise.reject()).then(function() {
            cpBtn.textContent = '✓'; setTimeout(function() { cpBtn.textContent = '⎘'; }, 1800);
          }).catch(function() {
            var t = document.createElement('textarea'); t.value = txt; document.body.appendChild(t); t.select(); document.execCommand('copy'); document.body.removeChild(t);
            cpBtn.textContent = '✓'; setTimeout(function() { cpBtn.textContent = '⎘'; }, 1800);
          });
        });
        wrap.appendChild(cpBtn);
      });
      container.appendChild(span);
    }
  }
  return container;
}

function avatarColor(name) {
  var colors = ['#5865f2','#57f287','#fee75c','#eb459e','#ed4245','#f0b232','#00b0f4','#3ba55c'];
  var h = 0;
  for (var i = 0; i < name.length; i++) h = name.charCodeAt(i) + ((h << 5) - h);
  return colors[Math.abs(h) % colors.length];
}

var msgReactions = {}; // key -> {emoji: count, ..., mine: [emoji,...]}

function getMsgKey(m) {
  if (m.msg_id) return m.msg_id;
  return (m.sender||'') + '|' + (m.time||'') + '|' + (m.text||'').substring(0,30);
}

function addReaction(msgKey, emoji) {
  if (!msgReactions[msgKey]) msgReactions[msgKey] = {counts: {}, mine: []};
  var r = msgReactions[msgKey];
  if (r.mine.indexOf(emoji) >= 0) {
    r.mine.splice(r.mine.indexOf(emoji), 1);
    r.counts[emoji] = (r.counts[emoji] || 1) - 1;
    if (r.counts[emoji] <= 0) delete r.counts[emoji];
  } else {
    r.mine.push(emoji);
    r.counts[emoji] = (r.counts[emoji] || 0) + 1;
  }
  renderMessages();
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({type: 'react', msg_id: msgKey, emoji: emoji}));
  }
}

var _replyTo = null;

function setReplyTo(m) {
  _replyTo = m;
  var bar = document.getElementById('replyPreviewBar');
  if (!bar) return;
  var sender = m.display_name || m.sender || '?';
  var preview = (m.text || '').substring(0, 80);
  bar.innerHTML = '<span style="color:var(--accent);font-weight:600;">Replying to ' + escapeHtml(sender) + '</span><span style="color:var(--text-muted);margin-left:8px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;">' + escapeHtml(preview) + '</span>';
  var closeBtn = document.createElement('button');
  closeBtn.innerHTML = '&#x2715;';
  closeBtn.style.cssText = 'background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:14px;flex-shrink:0;padding:0 4px;';
  closeBtn.onclick = function() { _replyTo = null; bar.style.display = 'none'; };
  bar.appendChild(closeBtn);
  bar.style.display = 'flex';
}

function buildReactionBar(msgKey, m) {
  var quickEmoji = ['👍','❤️','😂','😮','😢','🔥'];
  var bar = document.createElement('div');
  bar.className = 'msg-hover-actions';
  quickEmoji.forEach(function(em) {
    var btn = document.createElement('button');
    btn.className = 'msg-reaction-btn';
    btn.textContent = em;
    btn.title = 'React ' + em;
    btn.onclick = function(e) { e.stopPropagation(); addReaction(msgKey, em); };
    bar.appendChild(btn);
  });
  // Copy button
  var copyBtn = document.createElement('button');
  copyBtn.className = 'msg-reaction-btn';
  copyBtn.textContent = '📋';
  copyBtn.title = 'Copy message';
  copyBtn.onclick = function(e) {
    e.stopPropagation();
    if (m && m.text) {
      navigator.clipboard.writeText(m.text).then(function() { showToast('Message copied!', 'success'); }).catch(function() {
        var t = document.createElement('textarea');
        t.value = m.text;
        document.body.appendChild(t);
        t.select();
        document.execCommand('copy');
        document.body.removeChild(t);
        showToast('Message copied!', 'success');
      });
    }
  };
  bar.appendChild(copyBtn);
  // Reply button
  if (m) {
    var replyBtn = document.createElement('button');
    replyBtn.className = 'msg-reaction-btn';
    replyBtn.textContent = '↩';
    replyBtn.title = 'Reply';
    replyBtn.onclick = function(e) { e.stopPropagation(); setReplyTo(m); document.getElementById('msgInput').focus(); };
    bar.appendChild(replyBtn);
  }
  // More reactions "+" picker
  var moreBtn = document.createElement('button');
  moreBtn.className = 'msg-reaction-btn';
  moreBtn.textContent = '＋';
  moreBtn.title = 'More reactions';
  moreBtn.onclick = function(e) {
    e.stopPropagation();
    var allEmoji = ['👍','👎','❤️','😂','😮','😢','😡','🔥','🎉','🥳','😍','🤩','👏','🙌','💯','🤔','🤣','😎','😴','🤯','🫡','💀','🫶','⚡','🌟'];
    var existing = document.getElementById('_moreReactPicker');
    if (existing) { existing.remove(); return; }
    var picker = document.createElement('div');
    picker.id = '_moreReactPicker';
    picker.style.cssText = 'position:fixed;z-index:10000;background:var(--bg-secondary);border:1px solid var(--border);border-radius:8px;padding:8px;display:flex;flex-wrap:wrap;gap:4px;max-width:220px;box-shadow:0 4px 16px rgba(0,0,0,0.4);';
    allEmoji.forEach(function(em) {
      var eb = document.createElement('button');
      eb.style.cssText = 'background:none;border:none;font-size:18px;cursor:pointer;padding:4px 6px;border-radius:4px;transition:background 0.1s;';
      eb.textContent = em;
      eb.onmouseenter = function(){ eb.style.background='var(--bg-tertiary)'; };
      eb.onmouseleave = function(){ eb.style.background='none'; };
      eb.onclick = function(oe){ oe.stopPropagation(); addReaction(msgKey, em); picker.remove(); };
      picker.appendChild(eb);
    });
    var rect = moreBtn.getBoundingClientRect();
    picker.style.left = Math.min(rect.left, window.innerWidth - 230) + 'px';
    picker.style.top = (rect.bottom + 4) + 'px';
    document.body.appendChild(picker);
    setTimeout(function() { document.addEventListener('click', function _rp(){ picker.remove(); document.removeEventListener('click',_rp); }, {once:true}); }, 0);
  };
  bar.appendChild(moreBtn);
  return bar;
}

function buildReactionPills(msgKey) {
  var data = msgReactions[msgKey];
  if (!data || Object.keys(data.counts).length === 0) return null;
  var row = document.createElement('div');
  row.className = 'msg-reactions-row';
  Object.keys(data.counts).forEach(function(em) {
    if (data.counts[em] <= 0) return;
    var pill = document.createElement('button');
    pill.className = 'msg-reaction-pill' + (data.mine.indexOf(em) >= 0 ? ' mine' : '');
    pill.innerHTML = em + ' <span style="font-size:11px;">' + data.counts[em] + '</span>';
    pill.onclick = function(e) { e.stopPropagation(); addReaction(msgKey, em); };
    row.appendChild(pill);
  });
  return row;
}

function makeFullMessageDiv(m) {
  var displaySender = m.display_name || m.sender || '?';
  var msgKey = getMsgKey(m);
  var row = document.createElement('div');
  var _isMention = myUsername && m.text && m.text.toLowerCase().indexOf('@' + myUsername.toLowerCase()) >= 0;
  row.className = 'msg-full' + (_isMention ? ' msg-mention' : '');
  row.style.position = 'relative';
  row.addEventListener('contextmenu', function(e) { showContextMenu(e, m); });
  var avatarCol = document.createElement('div');
  avatarCol.className = 'msg-avatar-col';
  var avatar = document.createElement('div');
  avatar.className = 'msg-avatar';
  if (m.pfp) {
    avatar.style.backgroundImage = 'url(' + m.pfp + ')';
    avatar.style.backgroundSize = 'cover';
    avatar.style.backgroundPosition = 'center';
    avatar.style.cursor = 'pointer';
    avatar.title = 'View photo';
    avatar.addEventListener('click', function() { showPfpViewer(m.pfp, m.display_name || m.sender); });
  } else {
    avatar.style.background = avatarColor(displaySender);
    avatar.textContent = displaySender.substring(0, 2).toUpperCase();
  }
  avatarCol.appendChild(avatar);
  row.appendChild(avatarCol);
  var content = document.createElement('div');
  content.className = 'msg-content';
  var header = document.createElement('div');
  header.className = 'msg-header';
  var nameEl = document.createElement('span');
  nameEl.className = 'msg-name' + (m.admin ? ' is-admin' : '');
  nameEl.textContent = displaySender;
  nameEl.style.cursor = 'pointer';
  nameEl.title = 'View profile';
  nameEl.addEventListener('click', function(e) {
    e.stopPropagation();
    var userInfo = lastUserList ? lastUserList.find(function(u){ return (typeof u==='string'?u:u.name)===m.sender; }) : null;
    var bio = userInfo ? (userInfo.bio || '') : '';
    var status = userInfo ? (userInfo.status || 'online') : 'online';
    showUserCard(e, m.sender, m.display_name || m.sender, m.pfp || '', bio, status);
  });
  header.appendChild(nameEl);
  if (m.admin) {
    var badge = document.createElement('span');
    badge.className = 'msg-badge';
    badge.textContent = 'ADMIN';
    badge.style.cssText = 'font-size:10px;font-weight:700;color:#fff;background:var(--admin-color);padding:1px 4px;border-radius:3px;vertical-align:middle;';
    header.appendChild(badge);
  }
  var timeEl = document.createElement('span');
  timeEl.className = 'msg-timestamp';
  timeEl.textContent = m.time || new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
  timeEl.title = m.time || '';
  timeEl.style.cursor = 'default';
  header.appendChild(timeEl);
  content.appendChild(header);
  // Reply-to context
  if (m.reply_sender) {
    var replyCtxEl = document.createElement('div');
    replyCtxEl.style.cssText = 'border-left:3px solid var(--accent);padding:2px 8px;margin-bottom:3px;font-size:12px;color:var(--text-muted);background:var(--bg-tertiary);border-radius:0 4px 4px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%;';
    replyCtxEl.innerHTML = '<strong style="color:var(--text-secondary);">↩ ' + escapeHtml(m.reply_sender) + '</strong>: ' + escapeHtml((m.reply_text || '').substring(0, 80));
    content.appendChild(replyCtxEl);
  }
  var body = renderRichText(m.text || '');
  content.appendChild(body);
  var pills = buildReactionPills(msgKey);
  if (pills) content.appendChild(pills);
  row.appendChild(content);
  row.appendChild(buildReactionBar(msgKey, m));
  row.addEventListener('dblclick', function(e) { e.preventDefault(); addReaction(msgKey, '👍'); });
  return row;
}

function makeGroupedMessageDiv(m) {
  var msgKey = getMsgKey(m);
  var row = document.createElement('div');
  var _isMention2 = myUsername && m.text && m.text.toLowerCase().indexOf('@' + myUsername.toLowerCase()) >= 0;
  row.className = 'msg-grouped-row' + (_isMention2 ? ' msg-mention' : '');
  row.style.position = 'relative';
  row.addEventListener('contextmenu', function(e) { showContextMenu(e, m); });
  var body = renderRichText(m.text || '');
  row.appendChild(body);
  var pills = buildReactionPills(msgKey);
  if (pills) { pills.style.paddingLeft = '52px'; row.appendChild(pills); }
  row.appendChild(buildReactionBar(msgKey, m));
  row.addEventListener('dblclick', function(e) { e.preventDefault(); addReaction(msgKey, '👍'); });
  return row;
}

function renderMessages() {
  var el = document.getElementById('messages');
  if (!el) return;
  el.innerHTML = '';
  var msgs = [];
  if (currentChannel === 'general') {
    msgs = generalMessages;
  } else if (currentChannel.startsWith('dm:')) {
    var target = currentChannel.substring(3);
    msgs = dmMessages[target] || [];
  } else if (currentChannel.startsWith('gc:')) {
    var gcId = currentChannel.substring(3);
    msgs = gcMessages[gcId] || [];
  } else if (currentChannel.startsWith('spy:')) {
    var pair = currentChannel.substring(4);
    msgs = dmMessages['spy:' + pair] || [];
  }
  if (msgs.length === 0) {
    var empty = document.createElement('div');
    empty.className = 'empty'; empty.id = 'emptyState';
    empty.textContent = currentChannel === 'general' ? 'No messages yet' : 'No messages in this conversation';
    el.appendChild(empty);
    return;
  }
  var lastSender = null;
  var lastTime = 0;
  var wasAtBottom = _autoScroll || (el.scrollHeight - el.scrollTop - el.clientHeight) < 80;
  // Date divider
  var dateDivider = document.createElement('div');
  dateDivider.className = 'date-divider';
  dateDivider.textContent = 'Today';
  el.appendChild(dateDivider);
  // Track unread divider position
  var _unreadInserted = false;
  msgs.forEach(function(m, idx) {
    // Unread divider: insert before first unread message (messages after last seen)
    if (!_unreadInserted && m._unread) {
      var udiv = document.createElement('div');
      udiv.className = 'unread-divider';
      udiv.textContent = 'New Messages';
      el.appendChild(udiv);
      _unreadInserted = true;
    }
    if (m.type === 'system') {
      var wrapper = document.createElement('div');
      wrapper.className = 'msg-system';
      var s = document.createElement('span');
      s.textContent = m.text;
      wrapper.appendChild(s);
      el.appendChild(wrapper);
      lastSender = null; lastTime = 0;
    } else {
      var isGrouped = (m.sender === lastSender) && (Date.now() - lastTime < 5 * 60 * 1000);
      if (isGrouped) {
        el.appendChild(makeGroupedMessageDiv(m));
      } else {
        el.appendChild(makeFullMessageDiv(m));
        lastSender = m.sender;
        lastTime = Date.now();
      }
    }
  });
  if (wasAtBottom) el.scrollTop = el.scrollHeight;
}

function renderSidebar() {
  renderDmChannels();
  renderGcChannels();
  var generalEl = document.getElementById('channelGeneral');
  generalEl.className = 'channel-item' + (currentChannel === 'general' ? ' active' : '');
}

function updateTotalUnread() {
  var total = 0;
  Object.keys(dmUnread).forEach(function(k) { total += dmUnread[k] || 0; });
  Object.keys(gcUnread).forEach(function(k) { total += gcUnread[k] || 0; });
  var chatTab = document.querySelector('.tab-btn[data-tab-id="chat"] .tab-badge, .tab-btn .tab-badge');
  if (chatTab) { chatTab.style.display = total > 0 ? '' : 'none'; chatTab.textContent = total > 0 ? total : ''; }
  document.title = total > 0 ? '(' + total + ') Chat' : 'Chat';
}

function setConnectionStatus(state) {
  var dot = document.getElementById('chatStatusDot');
  var txt = document.getElementById('chatStatusText');
  if (!dot || !txt) return;
  if (state === 'connected') {
    dot.style.background = '';
    txt.textContent = 'Connected';
  } else if (state === 'reconnecting') {
    dot.style.background = '#f0b232';
    txt.textContent = 'Reconnecting…';
  } else {
    dot.style.background = 'var(--red,#f04747)';
    txt.textContent = 'Disconnected';
  }
}

var _dmSearchQuery = '';
function renderDmChannels() {
  var section = document.getElementById('dmChannelsSection');
  var list = document.getElementById('dmChannelsList');
  list.innerHTML = '';
  var dmKeys = Object.keys(dmMessages).filter(function(k) { return !k.startsWith('spy:'); });
  if (dmKeys.length === 0) { section.style.display = 'none'; return; }
  section.style.display = 'block';
  // Update DM section label count
  var dmLabel = section.querySelector('.sidebar-label');
  if (dmLabel) { var dmLabelText = dmLabel.childNodes[0]; if (dmLabelText && dmLabelText.nodeType===3) dmLabelText.nodeValue = 'Direct Messages (' + dmKeys.length + ') '; }
  // Search + mark-all-read header
  if (!document.getElementById('dmSearchInput')) {
    var sectionHeader = document.querySelector('#dmChannelsSection .sidebar-section-header');
    if (sectionHeader) {
      var markAllBtn = document.createElement('button');
      markAllBtn.title = 'Mark all read';
      markAllBtn.textContent = '✓';
      markAllBtn.style.cssText = 'background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:13px;padding:2px 4px;border-radius:3px;';
      markAllBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        Object.keys(dmUnread).forEach(function(k) { dmUnread[k] = 0; });
        Object.keys(gcUnread).forEach(function(k) { gcUnread[k] = 0; });
        renderDmChannels(); renderGcChannels();
        updateTotalUnread();
      });
      sectionHeader.appendChild(markAllBtn);
      var searchInput = document.createElement('input');
      searchInput.id = 'dmSearchInput';
      searchInput.type = 'text';
      searchInput.placeholder = 'Search DMs…';
      searchInput.style.cssText = 'width:100%;margin:4px 0 2px;padding:5px 8px;border:none;border-radius:5px;background:var(--input-bg);color:var(--text-primary);font-size:12px;outline:none;box-sizing:border-box;';
      searchInput.addEventListener('input', function() {
        _dmSearchQuery = this.value.toLowerCase();
        renderDmChannels();
      });
      section.insertBefore(searchInput, document.getElementById('dmChannelsList'));
    }
  }
  var filteredKeys = _dmSearchQuery ? dmKeys.filter(function(target) {
    var uObj = getUserObj(target);
    var dname = typeof uObj === 'string' ? uObj : (uObj.display_name || uObj.name || target);
    return dname.toLowerCase().indexOf(_dmSearchQuery) >= 0;
  }) : dmKeys;
  filteredKeys.forEach(function(target) {
    var uObj = getUserObj(target);
    var dname = typeof uObj === 'string' ? uObj : (uObj.display_name || uObj.name || target);
    var pfp = typeof uObj === 'string' ? '' : (uObj.pfp || '');
    var status = typeof uObj === 'string' ? 'online' : (uObj.status || 'offline');
    var statusDotColor = {online:'#43b581',idle:'#faa61a',dnd:'#f04747',invisible:'#747f8d',offline:'#747f8d'}[status] || '#43b581';
    var item = document.createElement('div');
    item.className = 'channel-item' + (currentChannel === 'dm:' + target ? ' active' : '');
    item.setAttribute('data-testid', 'dm-channel-' + target);
    item.style.cssText = 'padding:4px 8px;display:flex;align-items:center;gap:8px;border-radius:4px;cursor:pointer;';
    var avatarWrap = document.createElement('div');
    avatarWrap.style.cssText = 'position:relative;flex-shrink:0;';
    var avatarEl = document.createElement('div');
    avatarEl.style.cssText = 'width:26px;height:26px;border-radius:50%;background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;color:#fff;flex-shrink:0;background-size:cover;background-position:center;';
    if (pfp) { avatarEl.style.backgroundImage = 'url(' + pfp + ')'; }
    else { avatarEl.textContent = dname.substring(0,2).toUpperCase(); }
    var dot = document.createElement('div');
    dot.style.cssText = 'position:absolute;bottom:-1px;right:-1px;width:8px;height:8px;border-radius:50%;border:2px solid var(--bg-secondary);background:'+statusDotColor+';';
    avatarWrap.appendChild(avatarEl);
    avatarWrap.appendChild(dot);
    item.appendChild(avatarWrap);
    var nameCol = document.createElement('div');
    nameCol.style.cssText = 'flex:1;min-width:0;';
    var nameSpan = document.createElement('span');
    nameSpan.style.cssText = 'display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px;';
    nameSpan.textContent = dname;
    nameCol.appendChild(nameSpan);
    var msgs = dmMessages[target] || [];
    var lastMsg = msgs[msgs.length - 1];
    if (lastMsg && lastMsg.text) {
      var preview = document.createElement('span');
      preview.className = 'ch-preview';
      preview.textContent = (lastMsg.sender === myUsername ? 'You: ' : '') + (lastMsg.text || '').substring(0, 45);
      nameCol.appendChild(preview);
    }
    item.appendChild(nameCol);
    var muteKey = 'mute:dm:' + target;
    var isMuted = localStorage.getItem(muteKey) === '1';
    var muteBtn = document.createElement('button');
    muteBtn.className = 'mute-btn' + (isMuted ? ' muted' : '');
    muteBtn.title = isMuted ? 'Unmute' : 'Mute notifications';
    muteBtn.textContent = isMuted ? '🔕' : '🔔';
    muteBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      var m = localStorage.getItem(muteKey) === '1';
      if (m) localStorage.removeItem(muteKey); else localStorage.setItem(muteKey, '1');
      renderDmChannels();
    });
    item.appendChild(muteBtn);
    if (dmUnread[target] && dmUnread[target] > 0 && currentChannel !== 'dm:' + target) {
      var badge = document.createElement('span');
      badge.className = 'dm-badge';
      badge.textContent = dmUnread[target];
      item.appendChild(badge);
    }
    item.addEventListener('click', function() {
      openDm(target);
    });
    list.appendChild(item);
  });
}

function renderGcChannels() {
  var section = document.getElementById('gcChannelsSection');
  var list = document.getElementById('gcChannelsList');
  list.innerHTML = '';
  var gcIds = Object.keys(gcList);
  if (gcIds.length === 0) { section.style.display = 'none'; return; }
  section.style.display = 'block';
  // Update GC section label count
  var gcLabel = section.querySelector('.sidebar-label');
  if (gcLabel) { var gcLabelFirstNode = gcLabel.childNodes[0]; if (gcLabelFirstNode && gcLabelFirstNode.nodeType===3) gcLabelFirstNode.nodeValue = 'Group Chats (' + gcIds.length + ') '; }
  gcIds.forEach(function(gcId) {
    var gc = gcList[gcId];
    var item = document.createElement('div');
    item.className = 'channel-item' + (currentChannel === 'gc:' + gcId ? ' active' : '');
    item.setAttribute('data-testid', 'gc-channel-' + gcId);
    var icon = document.createElement('span');
    icon.className = 'channel-icon';
    icon.style.color = 'var(--green)';
    icon.textContent = '#';
    item.appendChild(icon);
    var nameCol = document.createElement('div');
    nameCol.style.cssText = 'flex:1;min-width:0;';
    var nameSpan = document.createElement('span');
    nameSpan.style.cssText = 'display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px;';
    nameSpan.textContent = gc.name;
    nameCol.appendChild(nameSpan);
    var gcMsgs = gcMessages[gcId] || [];
    var gcLastMsg = gcMsgs[gcMsgs.length - 1];
    if (gcLastMsg && gcLastMsg.text) {
      var gcPreview = document.createElement('span');
      gcPreview.className = 'ch-preview';
      gcPreview.textContent = (gcLastMsg.sender === myUsername ? 'You: ' : (gcLastMsg.display_name || gcLastMsg.sender || '') + ': ') + (gcLastMsg.text || '').substring(0, 40);
      nameCol.appendChild(gcPreview);
    }
    item.appendChild(nameCol);
    var gcMuteKey = 'mute:gc:' + gcId;
    var gcIsMuted = localStorage.getItem(gcMuteKey) === '1';
    var gcMuteBtn = document.createElement('button');
    gcMuteBtn.className = 'mute-btn' + (gcIsMuted ? ' muted' : '');
    gcMuteBtn.title = gcIsMuted ? 'Unmute' : 'Mute notifications';
    gcMuteBtn.textContent = gcIsMuted ? '🔕' : '🔔';
    gcMuteBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      var m = localStorage.getItem(gcMuteKey) === '1';
      if (m) localStorage.removeItem(gcMuteKey); else localStorage.setItem(gcMuteKey, '1');
      renderGcChannels();
    });
    item.appendChild(gcMuteBtn);
    if (gcUnread[gcId] && gcUnread[gcId] > 0 && currentChannel !== 'gc:' + gcId) {
      var badge = document.createElement('span');
      badge.className = 'dm-badge';
      badge.textContent = gcUnread[gcId];
      item.appendChild(badge);
    }
    item.addEventListener('click', function() {
      switchChannel('gc:' + gcId);
      gcUnread[gcId] = 0;
      ws.send(JSON.stringify({type: 'gc_open', gc_id: gcId}));
    });
    list.appendChild(item);
  });
}

function showGcCreateModal() {
  var overlay = document.createElement('div');
  overlay.className = 'gc-overlay';
  overlay.setAttribute('data-testid', 'gc-create-modal');
  var modal = document.createElement('div');
  modal.className = 'gc-modal';
  var title = document.createElement('div');
  title.className = 'gc-modal-title';
  title.textContent = 'Create Group Chat';
  modal.appendChild(title);
  var nameInput = document.createElement('input');
  nameInput.className = 'gc-modal-input';
  nameInput.placeholder = 'Group name...';
  nameInput.setAttribute('data-testid', 'input-gc-name');
  modal.appendChild(nameInput);
  var memberLabel = document.createElement('div');
  memberLabel.style.cssText = 'font-size:12px;color:var(--text-muted);margin-bottom:6px;';
  memberLabel.textContent = 'Select members (2+ required):';
  modal.appendChild(memberLabel);
  var memberList = document.createElement('div');
  memberList.className = 'gc-member-list';
  var selected = {};
  onlineUsers.forEach(function(name) {
    if (name === myUsername) return;
    var item = document.createElement('div');
    item.className = 'gc-member-item';
    item.setAttribute('data-testid', 'gc-member-' + name);
    var check = document.createElement('div');
    check.className = 'gc-check';
    item.appendChild(check);
    var nm = document.createElement('span');
    nm.textContent = name;
    item.appendChild(nm);
    item.addEventListener('click', function() {
      if (selected[name]) {
        delete selected[name];
        item.className = 'gc-member-item';
        check.textContent = '';
      } else {
        selected[name] = true;
        item.className = 'gc-member-item selected';
        check.textContent = 'X';
      }
      confirmBtn.disabled = Object.keys(selected).length < 2;
    });
    memberList.appendChild(item);
  });
  modal.appendChild(memberList);
  var btns = document.createElement('div');
  btns.className = 'gc-modal-btns';
  var cancelBtn = document.createElement('button');
  cancelBtn.className = 'gc-cancel';
  cancelBtn.textContent = 'Cancel';
  cancelBtn.setAttribute('data-testid', 'button-gc-cancel');
  cancelBtn.addEventListener('click', function() { overlay.remove(); });
  btns.appendChild(cancelBtn);
  var confirmBtn = document.createElement('button');
  confirmBtn.className = 'gc-confirm';
  confirmBtn.textContent = 'Create';
  confirmBtn.disabled = true;
  confirmBtn.setAttribute('data-testid', 'button-gc-confirm');
  confirmBtn.addEventListener('click', function() {
    var gcName = nameInput.value.trim() || 'Group';
    var members = Object.keys(selected);
    if (members.length < 2) return;
    ws.send(JSON.stringify({type: 'gc_create', name: gcName, members: members}));
    overlay.remove();
  });
  btns.appendChild(confirmBtn);
  modal.appendChild(btns);
  overlay.appendChild(modal);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  document.body.appendChild(overlay);
  nameInput.focus();
  nameInput.addEventListener('keydown', function(e) { e.stopPropagation(); });
}

function hexToRgb(hex) {
  var r = parseInt(hex.slice(1,3),16), g = parseInt(hex.slice(3,5),16), b = parseInt(hex.slice(5,7),16);
  return {r:r, g:g, b:b};
}
function blendColor(c, factor) {
  return '#' + [c.r, c.g, c.b].map(function(v) {
    return Math.round(v * factor).toString(16).padStart(2, '0');
  }).join('');
}
function applyTextColor(hex) {
  document.documentElement.style.setProperty('--text-primary', hex);
  var rgb = hexToRgb(hex);
  document.documentElement.style.setProperty('--text-secondary', blendColor(rgb, 0.72));
  document.documentElement.style.setProperty('--text-tertiary', blendColor(rgb, 0.58));
  document.documentElement.style.setProperty('--text-muted', blendColor(rgb, 0.42));
}

function loadUserSettings() {
  var bgUrl = localStorage.getItem('chat-bg-url') || '';
  var accentColor = localStorage.getItem('chat-accent-color') || '';
  var textColor = localStorage.getItem('chat-text-color') || '';
  var fontSize = localStorage.getItem('chat-font-size') || '';
  var chatDensity = localStorage.getItem('chat-density') || '';
  var bgBlur = localStorage.getItem('chat-bg-blur') || '';
  if (bgUrl) {
    document.body.style.backgroundImage = 'url(' + bgUrl + ')';
    document.body.style.backgroundSize = 'cover';
    document.body.style.backgroundPosition = 'center';
  }
  if (bgBlur) {
    document.body.style.backdropFilter = 'blur(' + bgBlur + 'px)';
  }
  if (accentColor) {
    document.documentElement.style.setProperty('--accent', accentColor);
  }
  if (textColor) {
    applyTextColor(textColor);
  }
  if (fontSize) {
    document.documentElement.style.setProperty('font-size', fontSize + 'px');
  }
  if (chatDensity === 'compact') {
    document.documentElement.style.setProperty('--msg-padding', '2px 16px');
  } else if (chatDensity === 'cozy') {
    document.documentElement.style.setProperty('--msg-padding', '8px 16px');
  }
  var ff = localStorage.getItem('chat-font-family') || '';
  if (ff) document.documentElement.style.setProperty('font-family', ff);
  var uclr = localStorage.getItem('chat-username-color') || '';
  if (uclr) document.documentElement.style.setProperty('--username-color-custom', uclr);
  if (localStorage.getItem('chat-show-timestamps') === 'off') document.body.classList.add('hide-timestamps');
  if (localStorage.getItem('chat-show-avatars') === 'off') document.body.classList.add('hide-avatars');
}

function showSettingsModal() {
  var overlay = document.createElement('div');
  overlay.className = 'gc-overlay';
  overlay.setAttribute('data-testid', 'settings-modal');
  var modal = document.createElement('div');
  modal.className = 'gc-modal';
  modal.style.maxHeight = '85vh';
  modal.style.overflowY = 'auto';
  var title = document.createElement('div');
  title.className = 'gc-modal-title';
  title.textContent = 'User Settings';
  modal.appendChild(title);

  function addRow(labelText, inputEl) {
    var row = document.createElement('div');
    row.className = 'settings-row';
    var lbl = document.createElement('span');
    lbl.className = 'settings-label';
    lbl.textContent = labelText;
    row.appendChild(lbl);
    row.appendChild(inputEl);
    modal.appendChild(row);
    return row;
  }

  var bgInput = document.createElement('input');
  bgInput.type = 'text';
  bgInput.placeholder = 'https://...';
  bgInput.value = localStorage.getItem('chat-bg-url') || '';
  bgInput.setAttribute('data-testid', 'input-settings-bg');
  bgInput.addEventListener('keydown', function(e) { e.stopPropagation(); });
  addRow('Background Image URL', bgInput);

  var blurInput = document.createElement('input');
  blurInput.type = 'range';
  blurInput.min = '0'; blurInput.max = '20'; blurInput.step = '1';
  blurInput.value = localStorage.getItem('chat-bg-blur') || '0';
  blurInput.style.cssText = 'flex:1;cursor:pointer;';
  blurInput.setAttribute('data-testid', 'input-settings-blur');
  addRow('Background Blur', blurInput);

  var accentInput = document.createElement('input');
  accentInput.type = 'color';
  accentInput.value = localStorage.getItem('chat-accent-color') || '#5865f2';
  accentInput.setAttribute('data-testid', 'input-settings-accent');
  addRow('Accent Color', accentInput);

  var textInput = document.createElement('input');
  textInput.type = 'color';
  textInput.value = localStorage.getItem('chat-text-color') || '#ffffff';
  textInput.setAttribute('data-testid', 'input-settings-text');
  addRow('Text Color', textInput);

  var fontSelect = document.createElement('select');
  fontSelect.style.cssText = 'padding:4px 8px;border-radius:4px;border:1px solid var(--border);background:var(--input-bg);color:var(--text-primary);font-size:13px;';
  fontSelect.setAttribute('data-testid', 'select-settings-font-size');
  [['Small', '13'], ['Normal', '14'], ['Large', '16'], ['Extra Large', '18']].forEach(function(opt) {
    var o = document.createElement('option');
    o.value = opt[1]; o.textContent = opt[0];
    fontSelect.appendChild(o);
  });
  fontSelect.value = localStorage.getItem('chat-font-size') || '14';
  addRow('Font Size', fontSelect);

  var densitySelect = document.createElement('select');
  densitySelect.style.cssText = 'padding:4px 8px;border-radius:4px;border:1px solid var(--border);background:var(--input-bg);color:var(--text-primary);font-size:13px;';
  densitySelect.setAttribute('data-testid', 'select-settings-density');
  [['Default', 'default'], ['Compact', 'compact'], ['Cozy', 'cozy']].forEach(function(opt) {
    var o = document.createElement('option');
    o.value = opt[1]; o.textContent = opt[0];
    densitySelect.appendChild(o);
  });
  densitySelect.value = localStorage.getItem('chat-density') || 'default';
  addRow('Chat Density', densitySelect);

  var soundCheck = document.createElement('input');
  soundCheck.type = 'checkbox';
  soundCheck.checked = localStorage.getItem('chat-sounds') !== 'off';
  soundCheck.style.cssText = 'width:18px;height:18px;cursor:pointer;';
  soundCheck.setAttribute('data-testid', 'input-settings-sounds');
  addRow('Notification Sounds', soundCheck);

  var fontFamilySelect = document.createElement('select');
  fontFamilySelect.style.cssText = 'padding:4px 8px;border-radius:4px;border:1px solid var(--border);background:var(--input-bg);color:var(--text-primary);font-size:13px;';
  fontFamilySelect.setAttribute('data-testid', 'select-settings-font-family');
  [['Default',''],['Monospace','monospace'],['Serif','serif'],['Comic Sans','Comic Sans MS, cursive']].forEach(function(opt) {
    var o = document.createElement('option');
    o.value = opt[1]; o.textContent = opt[0];
    fontFamilySelect.appendChild(o);
  });
  fontFamilySelect.value = localStorage.getItem('chat-font-family') || '';
  addRow('Font Family', fontFamilySelect);

  var usernameColorInput = document.createElement('input');
  usernameColorInput.type = 'color';
  usernameColorInput.value = localStorage.getItem('chat-username-color') || '#5865f2';
  usernameColorInput.setAttribute('data-testid', 'input-settings-username-color');
  addRow('Username Color', usernameColorInput);

  var timestampsCheck = document.createElement('input');
  timestampsCheck.type = 'checkbox';
  timestampsCheck.checked = localStorage.getItem('chat-show-timestamps') !== 'off';
  timestampsCheck.style.cssText = 'width:18px;height:18px;cursor:pointer;';
  timestampsCheck.setAttribute('data-testid', 'input-settings-timestamps');
  addRow('Show Timestamps', timestampsCheck);

  var avatarsCheck = document.createElement('input');
  avatarsCheck.type = 'checkbox';
  avatarsCheck.checked = localStorage.getItem('chat-show-avatars') !== 'off';
  avatarsCheck.style.cssText = 'width:18px;height:18px;cursor:pointer;';
  avatarsCheck.setAttribute('data-testid', 'input-settings-avatars');
  addRow('Show Avatars', avatarsCheck);

  var animCheck = document.createElement('input');
  animCheck.type = 'checkbox';
  animCheck.checked = localStorage.getItem('chat-msg-animate') !== 'off';
  animCheck.style.cssText = 'width:18px;height:18px;cursor:pointer;';
  animCheck.setAttribute('data-testid', 'input-settings-animations');
  addRow('Message Animations', animCheck);

  var btns = document.createElement('div');
  btns.className = 'gc-modal-btns';
  var resetBtn = document.createElement('button');
  resetBtn.className = 'gc-cancel';
  resetBtn.textContent = 'Reset All';
  resetBtn.setAttribute('data-testid', 'button-settings-reset');
  resetBtn.addEventListener('click', function() {
    ['chat-bg-url','chat-accent-color','chat-text-color','chat-font-size','chat-density','chat-bg-blur','chat-sounds','chat-font-family','chat-username-color','chat-show-timestamps','chat-show-avatars','chat-msg-animate'].forEach(function(k) {
      localStorage.removeItem(k);
    });
    document.body.style.backgroundImage = '';
    document.body.style.backdropFilter = '';
    document.documentElement.style.removeProperty('--accent');
    document.documentElement.style.removeProperty('--text-primary');
    document.documentElement.style.removeProperty('--text-secondary');
    document.documentElement.style.removeProperty('--text-tertiary');
    document.documentElement.style.removeProperty('--text-muted');
    document.documentElement.style.removeProperty('font-size');
    document.documentElement.style.removeProperty('--msg-padding');
    overlay.remove();
  });
  btns.appendChild(resetBtn);
  var saveBtn = document.createElement('button');
  saveBtn.className = 'gc-confirm';
  saveBtn.textContent = 'Save';
  saveBtn.setAttribute('data-testid', 'button-settings-save');
  saveBtn.addEventListener('click', function() {
    var bgUrl = bgInput.value.trim();
    var accent = accentInput.value;
    var textClr = textInput.value;
    var fSize = fontSelect.value;
    var density = densitySelect.value;
    var blur = blurInput.value;
    var sounds = soundCheck.checked;
    if (bgUrl) {
      localStorage.setItem('chat-bg-url', bgUrl);
      document.body.style.backgroundImage = 'url(' + bgUrl + ')';
      document.body.style.backgroundSize = 'cover';
      document.body.style.backgroundPosition = 'center';
    } else {
      localStorage.removeItem('chat-bg-url');
      document.body.style.backgroundImage = '';
    }
    localStorage.setItem('chat-bg-blur', blur);
    if (parseInt(blur) > 0) {
      document.body.style.backdropFilter = 'blur(' + blur + 'px)';
    } else {
      document.body.style.backdropFilter = '';
    }
    if (accent) {
      localStorage.setItem('chat-accent-color', accent);
      document.documentElement.style.setProperty('--accent', accent);
    }
    if (textClr) {
      localStorage.setItem('chat-text-color', textClr);
      applyTextColor(textClr);
    }
    localStorage.setItem('chat-font-size', fSize);
    document.documentElement.style.setProperty('font-size', fSize + 'px');
    localStorage.setItem('chat-density', density);
    if (density === 'compact') {
      document.documentElement.style.setProperty('--msg-padding', '2px 16px');
    } else if (density === 'cozy') {
      document.documentElement.style.setProperty('--msg-padding', '8px 16px');
    } else {
      document.documentElement.style.removeProperty('--msg-padding');
    }
    localStorage.setItem('chat-sounds', sounds ? 'on' : 'off');
    var ff = fontFamilySelect.value;
    if (ff) { localStorage.setItem('chat-font-family', ff); document.documentElement.style.setProperty('font-family', ff); }
    else { localStorage.removeItem('chat-font-family'); document.documentElement.style.removeProperty('font-family'); }
    var uclr = usernameColorInput.value;
    localStorage.setItem('chat-username-color', uclr);
    document.documentElement.style.setProperty('--username-color-custom', uclr);
    localStorage.setItem('chat-show-timestamps', timestampsCheck.checked ? 'on' : 'off');
    document.body.classList.toggle('hide-timestamps', !timestampsCheck.checked);
    localStorage.setItem('chat-show-avatars', avatarsCheck.checked ? 'on' : 'off');
    document.body.classList.toggle('hide-avatars', !avatarsCheck.checked);
    localStorage.setItem('chat-msg-animate', animCheck.checked ? 'on' : 'off');
    _msgAnimations = animCheck.checked;
    overlay.remove();
  });
  btns.appendChild(saveBtn);
  modal.appendChild(btns);
  overlay.appendChild(modal);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  document.body.appendChild(overlay);
}

function showLogsModal(logs, filterOpts) {
  var overlay = document.createElement('div');
  overlay.className = 'gc-overlay';
  overlay.setAttribute('data-testid', 'logs-modal');
  var modal = document.createElement('div');
  modal.className = 'gc-modal';
  modal.style.width = '600px';
  modal.style.maxHeight = '85vh';
  var title = document.createElement('div');
  title.className = 'gc-modal-title';
  title.textContent = 'Chat Logs (' + logs.length + ' entries)';
  modal.appendChild(title);

  var filterBar = document.createElement('div');
  filterBar.style.cssText = 'display:flex;gap:6px;margin-bottom:8px;flex-wrap:wrap;';
  var typeFilter = document.createElement('select');
  typeFilter.style.cssText = 'padding:4px 8px;border-radius:4px;border:1px solid var(--border);background:var(--input-bg);color:var(--text-primary);font-size:12px;';
  ['all','chat','dm','gc'].forEach(function(t) {
    var opt = document.createElement('option');
    opt.value = t; opt.textContent = t === 'all' ? 'All Types' : t.toUpperCase();
    typeFilter.appendChild(opt);
  });
  filterBar.appendChild(typeFilter);
  var senderFilter = document.createElement('input');
  senderFilter.type = 'text';
  senderFilter.placeholder = 'Filter by sender...';
  senderFilter.style.cssText = 'flex:1;padding:4px 8px;border-radius:4px;border:1px solid var(--border);background:var(--input-bg);color:var(--text-primary);font-size:12px;outline:none;min-width:100px;';
  filterBar.appendChild(senderFilter);
  var searchFilter = document.createElement('input');
  searchFilter.type = 'text';
  searchFilter.placeholder = 'Search text...';
  searchFilter.style.cssText = 'flex:1;padding:4px 8px;border-radius:4px;border:1px solid var(--border);background:var(--input-bg);color:var(--text-primary);font-size:12px;outline:none;min-width:100px;';
  filterBar.appendChild(searchFilter);
  modal.appendChild(filterBar);

  var logList = document.createElement('div');
  logList.style.cssText = 'max-height:50vh;overflow-y:auto;font-size:12px;font-family:monospace;';

  function renderLogEntries() {
    logList.innerHTML = '';
    var ft = typeFilter.value;
    var fs = senderFilter.value.toLowerCase().trim();
    var fq = searchFilter.value.toLowerCase().trim();
    var filtered = logs.filter(function(e) {
      if (ft !== 'all' && e.type !== ft) return false;
      if (fs && (e.sender || '').toLowerCase().indexOf(fs) === -1) return false;
      if (fq && (e.text || '').toLowerCase().indexOf(fq) === -1) return false;
      return true;
    });
    if (filtered.length === 0) {
      logList.textContent = 'No matching logs.';
      logList.style.color = 'var(--text-muted)';
      return;
    }
    logList.style.color = '';
    filtered.forEach(function(entry) {
      var row = document.createElement('div');
      row.style.cssText = 'padding:3px 0;border-bottom:1px solid var(--border);color:var(--text-secondary);display:flex;align-items:flex-start;gap:6px;';
      var textSpan = document.createElement('span');
      textSpan.style.flex = '1';
      var ts = entry.timestamp || '';
      var label = '[' + ts + '] ';
      if (entry.type === 'chat') {
        label += '[CHAT] ' + (entry.sender || '') + ': ' + (entry.text || '');
      } else if (entry.type === 'dm') {
        label += '[DM] ' + (entry.sender || '') + ' -> ' + (entry.recipient || '') + ': ' + (entry.text || '');
      } else if (entry.type === 'gc') {
        label += '[GC:' + (entry.gc_name || '') + '] ' + (entry.sender || '') + ': ' + (entry.text || '');
      } else {
        label += JSON.stringify(entry);
      }
      textSpan.textContent = label;
      row.appendChild(textSpan);
      if (isOwner) {
        var delBtn = document.createElement('button');
        delBtn.style.cssText = 'background:none;border:none;color:var(--red);cursor:pointer;font-size:11px;flex-shrink:0;padding:0 4px;';
        delBtn.textContent = 'X';
        delBtn.title = 'Delete this log entry';
        delBtn.addEventListener('click', function() {
          ws.send(JSON.stringify({type: 'delete_log', log_id: entry.id}));
          logs = logs.filter(function(e) { return e.id !== entry.id; });
          renderLogEntries();
          title.textContent = 'Chat Logs (' + logs.length + ' entries)';
        });
        row.appendChild(delBtn);
      }
      logList.appendChild(row);
    });
  }

  typeFilter.addEventListener('change', renderLogEntries);
  senderFilter.addEventListener('input', renderLogEntries);
  searchFilter.addEventListener('input', renderLogEntries);
  [senderFilter, searchFilter].forEach(function(el) { el.addEventListener('keydown', function(e) { e.stopPropagation(); }); });
  renderLogEntries();

  modal.appendChild(logList);
  var btns = document.createElement('div');
  btns.className = 'gc-modal-btns';
  btns.style.marginTop = '12px';
  var closeBtn = document.createElement('button');
  closeBtn.className = 'gc-confirm';
  closeBtn.textContent = 'Close';
  closeBtn.addEventListener('click', function() { overlay.remove(); });
  btns.appendChild(closeBtn);
  modal.appendChild(btns);
  overlay.appendChild(modal);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  document.body.appendChild(overlay);
}

function showSuggestionsModal(suggestions) {
  var overlay = document.createElement('div');
  overlay.className = 'gc-overlay';
  var modal = document.createElement('div');
  modal.className = 'gc-modal';
  modal.style.width = '500px';
  var title = document.createElement('div');
  title.className = 'gc-modal-title';
  title.textContent = 'Suggestions (' + suggestions.length + ')';
  modal.appendChild(title);
  var list = document.createElement('div');
  list.style.cssText = 'max-height:50vh;overflow-y:auto;';
  if (suggestions.length === 0) {
    list.textContent = 'No suggestions yet.';
    list.style.cssText += 'color:var(--text-muted);font-size:13px;padding:8px 0;';
  } else {
    suggestions.forEach(function(s) {
      var row = document.createElement('div');
      row.style.cssText = 'padding:6px 0;border-bottom:1px solid var(--border);';
      var header = document.createElement('div');
      header.style.cssText = 'font-size:11px;color:var(--text-muted);';
      header.textContent = s.from + ' - ' + (s.timestamp || '');
      row.appendChild(header);
      var body = document.createElement('div');
      body.style.cssText = 'font-size:13px;color:var(--text-secondary);margin-top:2px;';
      body.textContent = s.text;
      row.appendChild(body);
      if (isOwner) {
        var delBtn = document.createElement('button');
        delBtn.style.cssText = 'background:none;border:none;color:var(--red);cursor:pointer;font-size:11px;margin-top:2px;';
        delBtn.textContent = 'Delete';
        delBtn.addEventListener('click', function() {
          ws.send(JSON.stringify({type: 'delete_suggestion', id: s.id}));
          row.remove();
        });
        row.appendChild(delBtn);
      }
      list.appendChild(row);
    });
  }
  modal.appendChild(list);
  var btns = document.createElement('div');
  btns.className = 'gc-modal-btns';
  btns.style.marginTop = '12px';
  var closeBtn = document.createElement('button');
  closeBtn.className = 'gc-confirm';
  closeBtn.textContent = 'Close';
  closeBtn.addEventListener('click', function() { overlay.remove(); });
  btns.appendChild(closeBtn);
  modal.appendChild(btns);
  overlay.appendChild(modal);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  document.body.appendChild(overlay);
}

function showAdminCreatorModal() {
  var overlay = document.createElement('div');
  overlay.className = 'gc-overlay';
  var modal = document.createElement('div');
  modal.className = 'gc-modal';
  var title = document.createElement('div');
  title.className = 'gc-modal-title';
  title.textContent = 'Create Admin Account';
  modal.appendChild(title);
  var nameLabel = document.createElement('div');
  nameLabel.style.cssText = 'font-size:12px;color:var(--text-muted);margin-bottom:4px;';
  nameLabel.textContent = 'Admin display name (permanent):';
  modal.appendChild(nameLabel);
  var nameInput = document.createElement('input');
  nameInput.className = 'gc-modal-input';
  nameInput.placeholder = 'Admin name...';
  nameInput.addEventListener('keydown', function(e) { e.stopPropagation(); });
  modal.appendChild(nameInput);
  var resultDiv = document.createElement('div');
  resultDiv.style.cssText = 'font-size:12px;color:var(--green);display:none;padding:8px;background:var(--bg-tertiary);border-radius:4px;margin-bottom:8px;word-break:break-all;';
  modal.appendChild(resultDiv);
  var btns = document.createElement('div');
  btns.className = 'gc-modal-btns';
  var cancelBtn = document.createElement('button');
  cancelBtn.className = 'gc-cancel';
  cancelBtn.textContent = 'Close';
  cancelBtn.addEventListener('click', function() { overlay.remove(); });
  btns.appendChild(cancelBtn);
  var createBtn = document.createElement('button');
  createBtn.className = 'gc-confirm';
  createBtn.textContent = 'Create';
  createBtn.addEventListener('click', function() {
    var n = nameInput.value.trim();
    if (!n) return;
    ws.send(JSON.stringify({type: 'create_admin', name: n}));
    createBtn.disabled = true;
  });
  btns.appendChild(createBtn);
  modal.appendChild(btns);
  overlay.appendChild(modal);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  document.body.appendChild(overlay);
  window._adminCreatorResult = function(data) {
    resultDiv.style.display = 'block';
    resultDiv.textContent = 'Admin key for "' + data.name + '": ' + data.key + ' (save this!)';
    createBtn.disabled = false;
    nameInput.value = '';
  };
}

function showManageAdminsModal(admins) {
  var overlay = document.createElement('div');
  overlay.className = 'gc-overlay';
  var modal = document.createElement('div');
  modal.className = 'gc-modal';
  modal.style.width = '450px';
  var title = document.createElement('div');
  title.className = 'gc-modal-title';
  title.textContent = 'Admin Accounts (' + admins.length + ')';
  modal.appendChild(title);
  var list = document.createElement('div');
  list.style.cssText = 'max-height:50vh;overflow-y:auto;';
  if (admins.length === 0) {
    list.textContent = 'No admin accounts created.';
    list.style.cssText += 'color:var(--text-muted);font-size:13px;padding:8px 0;';
  } else {
    admins.forEach(function(a) {
      var row = document.createElement('div');
      row.style.cssText = 'padding:6px 0;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;';
      var info = document.createElement('div');
      info.style.cssText = 'font-size:13px;color:var(--text-secondary);';
      info.textContent = a.name + ' (created: ' + a.created + ')';
      row.appendChild(info);
      var delBtn = document.createElement('button');
      delBtn.style.cssText = 'background:var(--bg-tertiary);border:none;color:var(--red);cursor:pointer;font-size:11px;padding:3px 8px;border-radius:4px;';
      delBtn.textContent = 'Remove';
      delBtn.addEventListener('click', function() {
        ws.send(JSON.stringify({type: 'remove_admin', key: a.key}));
        row.remove();
      });
      row.appendChild(delBtn);
      list.appendChild(row);
    });
  }
  modal.appendChild(list);
  var btns = document.createElement('div');
  btns.className = 'gc-modal-btns';
  btns.style.marginTop = '12px';
  var closeBtn = document.createElement('button');
  closeBtn.className = 'gc-confirm';
  closeBtn.textContent = 'Close';
  closeBtn.addEventListener('click', function() { overlay.remove(); });
  btns.appendChild(closeBtn);
  modal.appendChild(btns);
  overlay.appendChild(modal);
  overlay.addEventListener('click', function(e) { if (e.target === overlay) overlay.remove(); });
  document.body.appendChild(overlay);
}

var statusColors = { online: 'var(--green)', idle: '#f0b232', dnd: 'var(--red)', invisible: 'var(--text-muted)' };
var typingUsers = {};
var typingTimers = {};

function showToast(msg, type) {
  var container = document.getElementById('toastContainer');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toastContainer';
    container.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:9999;display:flex;flex-direction:column;gap:8px;pointer-events:none;';
    document.body.appendChild(container);
  }
  var toast = document.createElement('div');
  var bg = type === 'error' ? 'var(--red,#f04747)' : type === 'success' ? 'var(--green,#43b581)' : type === 'warn' ? '#f0b232' : 'var(--bg-tertiary)';
  toast.style.cssText = 'padding:10px 16px;background:'+bg+';color:#fff;border-radius:8px;font-size:13px;font-weight:500;box-shadow:0 4px 16px rgba(0,0,0,0.35);opacity:0;transform:translateY(8px);transition:opacity 0.2s,transform 0.2s;pointer-events:auto;max-width:300px;word-break:break-word;';
  toast.textContent = msg;
  container.appendChild(toast);
  requestAnimationFrame(function() {
    toast.style.opacity = '1';
    toast.style.transform = 'translateY(0)';
  });
  setTimeout(function() {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(8px)';
    setTimeout(function() { if (toast.parentNode) toast.parentNode.removeChild(toast); }, 220);
  }, 3200);
}

var lastUserList = [];

function getUserObj(username) {
  for (var i = 0; i < lastUserList.length; i++) {
    var u = lastUserList[i];
    if ((typeof u === 'string' ? u : u.name) === username) return u;
  }
  return {name: username};
}

var _userSortAZ = false;
var _userSearchQuery = '';

function renderUsers(list) {
  lastUserList = list;
  onlineUsers = list.map(function(u) { return typeof u === 'string' ? u : u.name; });
  document.getElementById('userCount').textContent = list.length;
  var ul = document.getElementById('userList');
  ul.innerHTML = '';
  var filtered = list.filter(function(u) {
    var n = (typeof u === 'string' ? u : (u.display_name || u.name)).toLowerCase();
    return !_userSearchQuery || n.indexOf(_userSearchQuery) !== -1;
  });
  if (_userSortAZ) {
    filtered = filtered.slice().sort(function(a, b) {
      var na = (typeof a === 'string' ? a : (a.display_name || a.name)).toLowerCase();
      var nb = (typeof b === 'string' ? b : (b.display_name || b.name)).toLowerCase();
      return na < nb ? -1 : na > nb ? 1 : 0;
    });
  }
  filtered.forEach(function(user) {
    var name = typeof user === 'string' ? user : user.name;
    var displayName = typeof user === 'string' ? user : (user.display_name || user.name);
    var pfpUrl = typeof user === 'string' ? '' : (user.pfp || '');
    var status = typeof user === 'string' ? 'online' : (user.status || 'online');
    var div = document.createElement('div');
    div.className = 'user-item';
    div.setAttribute('data-testid', 'user-item-' + name);
    div.setAttribute('data-username', name);
    var avatarWrap = document.createElement('div');
    avatarWrap.style.cssText = 'position:relative;flex-shrink:0;';
    var avatar = document.createElement('div');
    avatar.className = 'user-avatar';
    if (pfpUrl) {
      avatar.style.backgroundImage = 'url(' + pfpUrl + ')';
      avatar.style.backgroundSize = 'cover';
      avatar.style.backgroundPosition = 'center';
    } else {
      avatar.textContent = displayName.substring(0,2).toUpperCase();
    }
    var statusDot = document.createElement('div');
    statusDot.style.cssText = 'position:absolute;bottom:-1px;right:-1px;width:10px;height:10px;border-radius:50%;border:2px solid var(--bg-secondary);background:' + (statusColors[status] || statusColors.online) + ';';
    avatarWrap.appendChild(avatar);
    avatarWrap.appendChild(statusDot);
    div.appendChild(avatarWrap);
    var nameEl = document.createElement('span');
    nameEl.className = 'user-name';
    var role = typeof user === 'string' ? '' : (user.role || '');
    var roleBadge = role === 'owner' ? ' 👑' : (role === 'admin' ? ' 🛡️' : '');
    nameEl.textContent = displayName + roleBadge + (name === myUsername ? ' (you)' : '');
    div.appendChild(nameEl);
    if (name !== myUsername) {
      div.style.cursor = 'pointer';
      div.title = 'Click to DM ' + name;
      div.addEventListener('click', function(e) {
        if (e.target.tagName === 'BUTTON') return;
        openDm(name);
      });
    }
    if (isOwner && name !== myUsername) {
      var actions = document.createElement('div');
      actions.className = 'user-actions';
      var kickBtn = document.createElement('button');
      kickBtn.style.cssText = 'padding:4px 8px;border:none;border-radius:4px;font-size:11px;font-weight:600;cursor:pointer;background:var(--bg-tertiary);color:var(--orange);';
      kickBtn.textContent = 'Kick';
      kickBtn.addEventListener('click', function(e) { e.stopPropagation(); ws.send(JSON.stringify({type:'kick',username:name})); });
      var banBtn = document.createElement('button');
      banBtn.style.cssText = 'padding:4px 8px;border:none;border-radius:4px;font-size:11px;font-weight:600;cursor:pointer;background:var(--bg-tertiary);color:var(--red);';
      banBtn.textContent = 'Ban';
      banBtn.addEventListener('click', function(e) { e.stopPropagation(); ws.send(JSON.stringify({type:'ban',username:name})); });
      actions.appendChild(kickBtn);
      actions.appendChild(banBtn);
      div.appendChild(actions);
    } else if (isStaffAdmin && name !== myUsername) {
      var actions = document.createElement('div');
      actions.className = 'user-actions';
      var kickBtn = document.createElement('button');
      kickBtn.style.cssText = 'padding:4px 8px;border:none;border-radius:4px;font-size:11px;font-weight:600;cursor:pointer;background:var(--bg-tertiary);color:var(--orange);';
      kickBtn.textContent = 'Kick';
      kickBtn.addEventListener('click', function(e) { e.stopPropagation(); ws.send(JSON.stringify({type:'kick',username:name})); });
      actions.appendChild(kickBtn);
      div.appendChild(actions);
    }
    ul.appendChild(div);
  });
  // Refresh DM profile sidebar if currently viewing a DM
  if (currentChannel && currentChannel.startsWith('dm:')) {
    var t = currentChannel.substring(3);
    updateDmProfileSidebar(t);
  }
}

function showTypingIndicator(username, channel) {
  if (username === myUsername) return;
  var key = channel + ':' + username;
  typingUsers[key] = true;
  if (typingTimers[key]) clearTimeout(typingTimers[key]);
  typingTimers[key] = setTimeout(function() {
    delete typingUsers[key];
    updateTypingDisplay();
  }, 3000);
  updateTypingDisplay();
}

function updateTypingDisplay() {
  var el = document.getElementById('typingIndicator');
  if (!el) return;
  var names = [];
  for (var key in typingUsers) {
    var parts = key.split(':');
    var ch = parts[0];
    var who = parts.slice(1).join(':');
    if (currentChannel === ch || (currentChannel === 'general' && ch === 'general')) names.push(who);
  }
  if (names.length === 0) {
    el.style.display = 'none'; return;
  }
  var nameText = names.length === 1 ? names[0] + ' is typing' :
                 names.length === 2 ? names[0] + ' and ' + names[1] + ' are typing' :
                 names.length + ' people are typing';
  el.style.display = 'flex'; el.style.alignItems = 'center'; el.style.gap = '5px';
  el.innerHTML = '<span style="font-size:12px;color:var(--text-muted);font-style:italic;">' + escapeHtml(nameText) + '</span>'
    + '<span class="typing-dots" style="display:inline-flex;align-items:center;margin-bottom:1px;"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></span>';
}

function openDm(target) {
  if (!dmMessages[target]) { dmMessages[target] = []; }
  switchChannel('dm:' + target);
  ws.send(JSON.stringify({type: 'dm_open', target: target}));
}

function renderBanned(list) {
  var section = document.getElementById('bannedSection');
  var el = document.getElementById('bannedList');
  if (!list || list.length === 0) { section.style.display = 'none'; return; }
  section.style.display = 'block';
  el.innerHTML = '';
  list.forEach(function(u) {
    var item = document.createElement('div');
    item.style.cssText = 'display:flex;align-items:center;justify-content:space-between;padding:4px 0;';
    var nm = document.createElement('span');
    nm.style.cssText = 'font-size:13px;color:var(--text-muted);text-decoration:line-through;';
    nm.textContent = u;
    var unbanBtn = document.createElement('button');
    unbanBtn.style.cssText = 'padding:4px 8px;border:none;border-radius:4px;font-size:11px;font-weight:600;cursor:pointer;background:var(--bg-tertiary);color:var(--green);';
    unbanBtn.textContent = 'Unban';
    unbanBtn.addEventListener('click', function() { ws.send(JSON.stringify({type:'unban',username:u})); });
    item.appendChild(nm);
    item.appendChild(unbanBtn);
    el.appendChild(item);
  });
}

function renderDmSpy(pairs) {
  activeDmPairs = pairs;
  var section = document.getElementById('dmSpySection');
  var list = document.getElementById('dmSpyList');
  list.innerHTML = '';
  if (!isAdmin || !pairs || pairs.length === 0) { section.style.display = 'none'; return; }
  section.style.display = 'block';
  pairs.forEach(function(pair) {
    var item = document.createElement('div');
    item.className = 'dm-spy-item' + (currentChannel === 'spy:' + pair ? ' active' : '');
    item.setAttribute('data-testid', 'dm-spy-' + pair);
    var icon = document.createElement('span');
    icon.className = 'dm-spy-icon';
    icon.textContent = 'SPY';
    item.appendChild(icon);
    var label = document.createElement('span');
    label.textContent = pair;
    item.appendChild(label);
    item.addEventListener('click', function() {
      if (!dmMessages['spy:' + pair]) { dmMessages['spy:' + pair] = []; }
      switchChannel('spy:' + pair);
      ws.send(JSON.stringify({type: 'dm_spy_open', pair: pair}));
    });
    list.appendChild(item);
  });
}

function playNotifSound() {
  if (localStorage.getItem('chat-sounds') === 'off') return;
  try {
    var ctx = new (window.AudioContext || window.webkitAudioContext)();
    var osc = ctx.createOscillator();
    var gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.frequency.value = 800;
    osc.type = 'sine';
    gain.gain.setValueAtTime(0.15, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.15);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.15);
  } catch(e) {}
}

function updateProfileBtn() {
  var btn = document.getElementById('profileBtn');
  if (!btn) return;
  if (myPfpData) {
    btn.style.backgroundImage = 'url(' + myPfpData + ')';
    btn.style.backgroundSize = 'cover';
    btn.style.backgroundPosition = 'center';
    btn.textContent = '';
  } else {
    btn.textContent = (myDisplayName || myUsername || '?').charAt(0).toUpperCase();
  }
}

function handleMessage(data) {
  if (data.type === 'joined') {
    myUsername = data.username || myUsername;
    myDisplayName = data.display_name || data.username || myUsername;
    myPfpData = data.pfp_data || '';
    myBio = data.bio || '';
    updateProfileBtn();
    if (!myIsGuest && mySessionToken) {
      fetch('/api/changelog-seen', {headers:{'X-Session-Token':mySessionToken}})
        .then(function(r){return r.json();})
        .then(function(d){ if (d.show) showChangelog(); })
        .catch(function(){});
    }
  } else if (data.type === 'garlic_state' || data.type === 'garlic_error' || data.type === 'garlic_draw' || data.type === 'garlic_guess' || data.type === 'garlic_reveal' || data.type === 'garlic_lobby') {
    if (typeof window._garlicMessageHandler === 'function') window._garlicMessageHandler(data);
  } else if (data.type === 'react') {
    var mid = data.msg_id;
    if (mid) {
      if (!msgReactions[mid]) msgReactions[mid] = {counts: {}, mine: []};
      var allReactors = data.reactions || {};
      var newCounts = {};
      Object.keys(allReactors).forEach(function(em) { newCounts[em] = allReactors[em].length; });
      var newMine = [];
      Object.keys(allReactors).forEach(function(em) {
        if (allReactors[em].indexOf(myUsername) >= 0 || allReactors[em].indexOf(myDisplayName) >= 0) newMine.push(em);
      });
      msgReactions[mid] = {counts: newCounts, mine: newMine};
      renderMessages();
    }
  } else if (data.type === 'chat') {
    var time = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    generalMessages.push({sender: data.sender, display_name: data.display_name || data.sender, pfp: data.pfp || '', text: data.text, admin: data.admin || false, time: time, msg_id: data.msg_id||'', reply_sender: data.reply_sender||'', reply_text: data.reply_text||''});
    if (currentChannel === 'general') { renderMessages(); if (data.sender !== myUsername && typeof window._notifyScrollBtn === 'function') window._notifyScrollBtn(); }
    if (data.sender !== myUsername) { playNotifSound(); if (typeof checkConfetti === 'function') checkConfetti(data.text); }
    else if (typeof checkConfetti === 'function') checkConfetti(data.text);
  } else if (data.type === 'system') {
    generalMessages.push({type: 'system', text: data.text});
    if (currentChannel === 'general') { renderMessages(); if (typeof window._notifyScrollBtn === 'function') window._notifyScrollBtn(); }
  } else if (data.type === 'users') {
    renderUsers(data.list);
  } else if (data.type === 'banned_list') {
    renderBanned(data.list);
  } else if (data.type === 'dm') {
    var other;
    if (isAdmin) {
      var adminName = document.getElementById('nameInput').value.trim() || 'Admin';
      if (data.sender === adminName || data.admin) {
        other = data.recipient;
      } else {
        other = data.sender;
      }
    } else if (data.admin_dm) {
      other = 'Admin';
    } else {
      other = data.sender === myUsername ? data.recipient : data.sender;
    }
    if (!dmMessages[other]) { dmMessages[other] = []; }
    var time = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    dmMessages[other].push({sender: data.sender, display_name: data.display_name || data.sender, pfp: data.pfp || '', text: data.text, admin: data.admin || false, isDm: true, time: time, msg_id: data.msg_id||'', reply_sender: data.reply_sender||'', reply_text: data.reply_text||''});
    if (data.sender !== myUsername && currentChannel !== 'dm:' + other && !dmPanelTarget) {
      var _dname = data.display_name || data.sender;
      showToast('💬 ' + escapeHtml(_dname) + ': ' + (data.text || '').substring(0,60), 'info');
    }
    if (dmPanelTarget === other) {
      renderDmPanel();
    } else if (currentChannel === 'dm:' + other) {
      renderMessages();
    } else {
      dmUnread[other] = (dmUnread[other] || 0) + 1;
      if (localStorage.getItem('mute:dm:' + other) !== '1') playNotifSound();
      renderDmChannels();
    }
  } else if (data.type === 'dm_history') {
    var target = data.target;
    var freshMsgs = (data.messages || []).map(function(m) {
      return {sender: m.sender, display_name: m.display_name || m.sender, pfp: m.pfp || '', text: m.text, admin: m.admin || false, isDm: true, time: m.time || '', msg_id: m.msg_id||'', reply_sender: m.reply_sender||'', reply_text: m.reply_text||''};
    });
    if (freshMsgs.length > 0) { dmMessages[target] = freshMsgs; }
    else if (!dmMessages[target]) { dmMessages[target] = []; }
    if (dmPanelTarget === target) {
      renderDmPanel();
    } else if (currentChannel === 'dm:' + target) {
      renderMessages();
    }
  } else if (data.type === 'dm_spy') {
    var pair = data.pair;
    dmMessages['spy:' + pair] = [];
    (data.messages || []).forEach(function(m) {
      dmMessages['spy:' + pair].push({sender: m.sender, text: m.text, admin: m.admin || false, isDm: true, time: m.time || ''});
    });
    if (currentChannel === 'spy:' + pair) renderMessages();
  } else if (data.type === 'dm_spy_update') {
    var pair = data.pair;
    var time = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    if (!dmMessages['spy:' + pair]) dmMessages['spy:' + pair] = [];
    dmMessages['spy:' + pair].push({sender: data.sender, text: data.text, admin: data.admin || false, isDm: true, time: time});
    if (currentChannel === 'spy:' + pair) renderMessages();
  } else if (data.type === 'dm_cleanup') {
    var gone = data.username;
    if (dmMessages[gone]) {
      delete dmMessages[gone];
    }
    if (dmUnread[gone]) {
      delete dmUnread[gone];
    }
    Object.keys(dmMessages).forEach(function(k) {
      if (k.startsWith('spy:') && k.indexOf(gone) !== -1) {
        delete dmMessages[k];
      }
    });
    if (currentChannel === 'dm:' + gone || (currentChannel.startsWith('spy:') && currentChannel.indexOf(gone) !== -1)) {
      switchChannel('general');
    }
    renderDmChannels();
  } else if (data.type === 'dm_pairs') {
    renderDmSpy(data.pairs);
  } else if (data.type === 'logs_data') {
    if (window._logsExportMode) {
      window._logsExportMode = false;
      var blob = new Blob([JSON.stringify(data.logs || [], null, 2)], {type: 'application/json'});
      var url = URL.createObjectURL(blob);
      var a = document.createElement('a');
      a.href = url; a.download = 'chat_logs_' + new Date().toISOString().slice(0,10) + '.json';
      document.body.appendChild(a); a.click(); document.body.removeChild(a);
      URL.revokeObjectURL(url);
      showToast('Logs exported!', 'success');
    } else {
      showLogsModal(data.logs || []);
    }
  } else if (data.type === 'suggestions_data') {
    showSuggestionsModal(data.suggestions || []);
  } else if (data.type === 'admins_data') {
    showManageAdminsModal(data.admins || []);
  } else if (data.type === 'admin_created') {
    if (window._adminCreatorResult) window._adminCreatorResult(data);
  } else if (data.type === 'suggestion_sent') {
    // silently handled
  } else if (data.type === 'new_suggestion') {
    var badge = document.getElementById('mailboxBadge');
    var c = parseInt(badge.textContent || '0') + 1;
    badge.textContent = c;
    badge.style.display = 'inline';
  } else if (data.type === 'typing') {
    showTypingIndicator(data.username, data.channel);
  } else if (data.type === 'gc_created') {
    gcList[data.gc.id] = data.gc;
    gcMessages[data.gc.id] = [];
    renderGcChannels();
    switchChannel('gc:' + data.gc.id);
  } else if (data.type === 'gc_invited') {
    gcList[data.gc.id] = data.gc;
    gcMessages[data.gc.id] = [];
    renderGcChannels();
  } else if (data.type === 'gc_message') {
    var gcId = data.gc_id;
    if (!gcMessages[gcId]) gcMessages[gcId] = [];
    var time = new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'});
    gcMessages[gcId].push({sender: data.sender, display_name: data.display_name || data.sender, pfp: data.pfp||'', text: data.text, admin: data.admin || false, time: time, msg_id: data.msg_id||'', reply_sender: data.reply_sender||'', reply_text: data.reply_text||''});
    if (currentChannel === 'gc:' + gcId) {
      renderMessages();
    } else {
      gcUnread[gcId] = (gcUnread[gcId] || 0) + 1;
      if (localStorage.getItem('mute:gc:' + gcId) !== '1') playNotifSound();
      renderGcChannels();
    }
  } else if (data.type === 'gc_history') {
    var gcId = data.gc_id;
    gcMessages[gcId] = [];
    (data.messages || []).forEach(function(m) {
      gcMessages[gcId].push({sender: m.sender, display_name: m.display_name||m.sender, pfp: m.pfp||'', text: m.text, admin: m.admin || false, time: m.time || '', msg_id: m.msg_id||'', reply_sender: m.reply_sender||'', reply_text: m.reply_text||''});
    });
    if (currentChannel === 'gc:' + gcId) renderMessages();
  } else if (data.type === 'error') {
    if (!myUsername && !isAdmin) {
      var err = document.getElementById('joinError');
      err.textContent = data.text;
      err.style.display = 'block';
    }
  } else if (data.type === 'bj_room_created' || data.type === 'bj_joined' || data.type === 'bj_state' || data.type === 'bj_error') {
    if (window._bjMultiHandler) window._bjMultiHandler(data);
  } else if (data.type === 'balance_data' || data.type === 'shop_result' || data.type === 'equip_result' ||
             data.type === 'savings_result' || data.type === 'gamble_result' ||
             data.type === 'idle_result' || data.type === 'idle_collect_result') {
    document.dispatchEvent(new CustomEvent('_balance_msg', {detail: data}));
  }
}

var adminConnected = false;
function connectOwner(token) {
  var protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  adminConnected = false;
  ws = new WebSocket(protocol + '//' + location.host + '/owner-ws?token=' + token);
  ws.onopen = function() {
    adminConnected = true;
    isAdmin = true;
    isOwner = true;
    myRole = 'owner';
    var savedOwner = JSON.parse(localStorage.getItem('owner_profile') || 'null');
    if (savedOwner) {
      myDisplayName = savedOwner.display_name || 'Owner';
      myBio = savedOwner.bio || '';
      myPfpData = savedOwner.pfp_data || '';
    } else {
      myDisplayName = 'Owner';
    }
    updateProfileBtn();
    document.getElementById('nameInput').style.display = 'block';
    document.getElementById('nameInput').value = myDisplayName;
    document.getElementById('joinScreen').style.display = 'none';
    document.getElementById('chatScreen').style.display = 'flex';
    document.getElementById('logsSection').style.display = 'block';
    document.getElementById('mailboxSection').style.display = 'block';
    document.getElementById('adminCreatorBtn').style.display = 'flex';
    document.getElementById('manageAdminsBtn').style.display = 'flex';
    document.getElementById('broadcastBtn').style.display = 'flex';
    document.getElementById('slowmodeBtn').style.display = 'flex';
    document.getElementById('announcementBtn').style.display = 'flex';
    document.getElementById('motdBtn').style.display = 'flex';
    document.getElementById('wordFilterBtn').style.display = 'flex';
    document.getElementById('bulkClearBtn').style.display = 'flex';
    document.getElementById('exportLogsBtn').style.display = 'flex';
    document.getElementById('msgInput').focus();
    setTimeout(function() { showToast('Welcome back, Owner! 👑', 'success'); }, 600);
    _ownerReconnectDelay = 2000;
    setConnectionStatus('connected');
  };
  var _ownerReconnectDelay = 2000;
  ws.onclose = function() {
    if (!adminConnected) {
      var err = document.getElementById('adminError');
      err.textContent = 'Invalid owner key or connection failed.';
      err.style.display = 'block';
      ws = null;
      return;
    }
    document.getElementById('sendBtn').disabled = true;
    document.getElementById('msgInput').disabled = true;
    setConnectionStatus('reconnecting');
    showToast('Connection lost. Reconnecting in ' + (_ownerReconnectDelay/1000) + 's…', 'error');
    setTimeout(function() {
      _ownerReconnectDelay = Math.min(_ownerReconnectDelay * 1.5, 30000);
      connectOwner(token);
    }, _ownerReconnectDelay);
  };
  ws.onerror = function() {};
  ws.onmessage = function(event) { handleMessage(JSON.parse(event.data)); };
}

function connectStaffAdmin(key) {
  var protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  var staffConnected = false;
  ws = new WebSocket(protocol + '//' + location.host + '/staff-ws?key=' + encodeURIComponent(key));
  ws.onopen = function() {
    staffConnected = true;
    isAdmin = true;
    isStaffAdmin = true;
    myRole = 'admin';
    var savedAdmin = JSON.parse(localStorage.getItem('admin_profile') || 'null');
    if (savedAdmin) {
      myDisplayName = savedAdmin.display_name || myDisplayName || 'Admin';
      myBio = savedAdmin.bio || '';
      myPfpData = savedAdmin.pfp_data || '';
      updateProfileBtn();
    }
    document.getElementById('joinScreen').style.display = 'none';
    document.getElementById('chatScreen').style.display = 'flex';
    document.getElementById('logsSection').style.display = 'block';
    document.getElementById('suggestBoxSection').style.display = 'block';
    document.getElementById('msgInput').focus();
    setTimeout(function() { showToast('Welcome, ' + (myDisplayName || 'Admin') + '! 🛡️', 'success'); }, 600);
  };
  var _staffReconnectDelay = 2000;
  ws.onclose = function() {
    if (!staffConnected) {
      var err = document.getElementById('staffAdminError');
      err.textContent = 'Invalid admin key or connection failed.';
      err.style.display = 'block';
      ws = null;
      return;
    }
    document.getElementById('sendBtn').disabled = true;
    document.getElementById('msgInput').disabled = true;
    setConnectionStatus('reconnecting');
    showToast('Connection lost. Reconnecting in ' + (_staffReconnectDelay/1000) + 's…', 'error');
    setTimeout(function() {
      _staffReconnectDelay = Math.min(_staffReconnectDelay * 1.5, 30000);
      connectStaffAdmin(key);
    }, _staffReconnectDelay);
  };
  ws.onerror = function() {};
  ws.onmessage = function(event) { handleMessage(JSON.parse(event.data)); };
}

function connectGuest(username) {
  var protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(protocol + '//' + location.host + '/ws');
  ws.onmessage = function(event) { handleMessage(JSON.parse(event.data)); };
  var _guestReconnectDelay = 2000;
  ws.onclose = function() {
    if (myUsername) {
      document.getElementById('sendBtn').disabled = true;
      document.getElementById('msgInput').disabled = true;
      setConnectionStatus('reconnecting');
      showToast('Connection lost. Reconnecting in ' + (_guestReconnectDelay/1000) + 's…', 'error');
      setTimeout(function() {
        _guestReconnectDelay = Math.min(_guestReconnectDelay * 1.5, 30000);
        connectGuest(username);
      }, _guestReconnectDelay);
    }
  };
  ws.onopen = function() {
    _guestReconnectDelay = 2000;
    setConnectionStatus('connected');
    document.getElementById('sendBtn').disabled = false;
    document.getElementById('msgInput').disabled = false;
    ws.send(JSON.stringify({ type: 'join', username: username, session_token: mySessionToken || '' }));
    document.getElementById('suggestBoxSection').style.display = 'block';
    setTimeout(function() { showToast('Welcome, ' + (username || 'Guest') + '! 👋', 'success'); }, 600);
  };
}

var RESERVED = /admin|mod|owner/i;

document.getElementById('channelGeneral').addEventListener('click', function() {
  switchChannel('general');
});

document.getElementById('gcCreateBtn').addEventListener('click', function() {
  showGcCreateModal();
});

document.getElementById('viewLogsBtn').addEventListener('click', function() {
  ws.send(JSON.stringify({type: 'get_logs'}));
});

document.getElementById('settingsBtn').addEventListener('click', function() {
  showSettingsModal();
});

document.getElementById('profileBtn').addEventListener('click', function() {
  if (!mySessionToken && !isAdmin && !isOwner) {
    showToast('You need an account to edit your profile. Log in or sign up!', 'info');
    return;
  }
  showProfileModal();
});

function showProfileModal() {
  var modal = document.getElementById('profileModal');
  modal.style.display = 'flex';
  document.getElementById('profileUsernameDisplay').textContent = myUsername;
  document.getElementById('profileDisplayName').value = myDisplayName || '';
  document.getElementById('profileBio').value = myBio || '';
  var savedStatus = localStorage.getItem('chat-my-status') || 'online';
  document.getElementById('profileStatus').value = savedStatus;
  var preview = document.getElementById('profilePfpPreview');
  if (myPfpData) {
    preview.style.backgroundImage = 'url(' + myPfpData + ')';
    preview.style.backgroundSize = 'cover';
    preview.style.backgroundPosition = 'center';
    preview.textContent = '';
  } else {
    preview.style.backgroundImage = '';
    preview.textContent = (myDisplayName || myUsername || '?').charAt(0).toUpperCase();
  }
  var errEl = document.getElementById('profileError');
  errEl.style.display = 'none';
}

document.getElementById('profileModalClose').addEventListener('click', function() {
  document.getElementById('profileModal').style.display = 'none';
});
document.getElementById('profileModal').addEventListener('click', function(e) {
  if (e.target === this) this.style.display = 'none';
});

var _profilePfpPending = null;
document.getElementById('changePfpBtn').addEventListener('click', function() {
  document.getElementById('pfpFileInput').click();
});
document.getElementById('profilePfpPreview').addEventListener('click', function() {
  document.getElementById('pfpFileInput').click();
});
document.getElementById('pfpFileInput').addEventListener('change', function(e) {
  var file = e.target.files[0];
  if (!file) return;
  if (file.size > 5 * 1024 * 1024) { alert('Image must be under 5MB.'); return; }
  var reader = new FileReader();
  reader.onload = function(ev) { openPfpCrop(ev.target.result); };
  reader.readAsDataURL(file);
  this.value = '';
});

var _pfpCrop = {x:0, y:0, scale:1, imgNatW:0, imgNatH:0, dragging:false, startMX:0, startMY:0, startX:0, startY:0};
var CROP_SIZE = 240;

function openPfpCrop(src) {
  var modal = document.getElementById('pfpCropModal');
  var img = document.getElementById('pfpCropImg');
  var zoom = document.getElementById('pfpCropZoom');
  zoom.value = 1;
  _pfpCrop = {x:0, y:0, scale:1, imgNatW:0, imgNatH:0, dragging:false, startMX:0, startMY:0, startX:0, startY:0};
  img.src = src;
  modal.style.display = 'flex';
  img.onload = function() {
    _pfpCrop.imgNatW = img.naturalWidth;
    _pfpCrop.imgNatH = img.naturalHeight;
    var fit = CROP_SIZE / Math.min(_pfpCrop.imgNatW, _pfpCrop.imgNatH);
    _pfpCrop.scale = fit;
    zoom.min = Math.min(fit, 0.5).toFixed(3);
    zoom.max = Math.max(fit * 4, 4).toFixed(3);
    zoom.value = fit;
    _pfpCrop.x = (CROP_SIZE - _pfpCrop.imgNatW * fit) / 2;
    _pfpCrop.y = (CROP_SIZE - _pfpCrop.imgNatH * fit) / 2;
    updateCropTransform();
  };
}

function updateCropTransform() {
  var img = document.getElementById('pfpCropImg');
  img.style.left = _pfpCrop.x + 'px';
  img.style.top = _pfpCrop.y + 'px';
  img.style.width = (_pfpCrop.imgNatW * _pfpCrop.scale) + 'px';
  img.style.height = (_pfpCrop.imgNatH * _pfpCrop.scale) + 'px';
}

var _cropArea = document.getElementById('pfpCropArea');
_cropArea.addEventListener('mousedown', function(e) {
  _pfpCrop.dragging = true;
  _pfpCrop.startMX = e.clientX; _pfpCrop.startMY = e.clientY;
  _pfpCrop.startX = _pfpCrop.x; _pfpCrop.startY = _pfpCrop.y;
  e.preventDefault();
});
document.addEventListener('mousemove', function(e) {
  if (!_pfpCrop.dragging) return;
  _pfpCrop.x = _pfpCrop.startX + (e.clientX - _pfpCrop.startMX);
  _pfpCrop.y = _pfpCrop.startY + (e.clientY - _pfpCrop.startMY);
  updateCropTransform();
});
document.addEventListener('mouseup', function() { _pfpCrop.dragging = false; });
_cropArea.addEventListener('touchstart', function(e) {
  var t = e.touches[0];
  _pfpCrop.dragging = true;
  _pfpCrop.startMX = t.clientX; _pfpCrop.startMY = t.clientY;
  _pfpCrop.startX = _pfpCrop.x; _pfpCrop.startY = _pfpCrop.y;
  e.preventDefault();
}, {passive:false});
document.addEventListener('touchmove', function(e) {
  if (!_pfpCrop.dragging) return;
  var t = e.touches[0];
  _pfpCrop.x = _pfpCrop.startX + (t.clientX - _pfpCrop.startMX);
  _pfpCrop.y = _pfpCrop.startY + (t.clientY - _pfpCrop.startMY);
  updateCropTransform();
}, {passive:false});
document.addEventListener('touchend', function() { _pfpCrop.dragging = false; });

document.getElementById('pfpCropZoom').addEventListener('input', function() {
  var newScale = parseFloat(this.value);
  var cx = CROP_SIZE / 2, cy = CROP_SIZE / 2;
  _pfpCrop.x = cx - (cx - _pfpCrop.x) * newScale / _pfpCrop.scale;
  _pfpCrop.y = cy - (cy - _pfpCrop.y) * newScale / _pfpCrop.scale;
  _pfpCrop.scale = newScale;
  updateCropTransform();
});

document.getElementById('pfpCropCancel').addEventListener('click', function() {
  document.getElementById('pfpCropModal').style.display = 'none';
});

document.getElementById('pfpCropApply').addEventListener('click', function() {
  var canvas = document.createElement('canvas');
  canvas.width = 200; canvas.height = 200;
  var ctx = canvas.getContext('2d');
  ctx.beginPath();
  ctx.arc(100, 100, 100, 0, Math.PI * 2);
  ctx.clip();
  var img = document.getElementById('pfpCropImg');
  var srcX = -_pfpCrop.x / _pfpCrop.scale;
  var srcY = -_pfpCrop.y / _pfpCrop.scale;
  var srcW = CROP_SIZE / _pfpCrop.scale;
  var srcH = CROP_SIZE / _pfpCrop.scale;
  ctx.drawImage(img, srcX, srcY, srcW, srcH, 0, 0, 200, 200);
  var dataUrl = canvas.toDataURL('image/jpeg', 0.88);
  document.getElementById('pfpCropModal').style.display = 'none';
  _profilePfpPending = dataUrl;
  var preview = document.getElementById('profilePfpPreview');
  preview.style.backgroundImage = 'url(' + dataUrl + ')';
  preview.style.backgroundSize = 'cover';
  preview.style.backgroundPosition = 'center';
  preview.textContent = '';
});

document.getElementById('saveProfileBtn').addEventListener('click', function() {
  var dn = document.getElementById('profileDisplayName').value.trim();
  var bio = document.getElementById('profileBio').value.trim();
  var newStatus = document.getElementById('profileStatus').value;
  if (newStatus && ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({type:'set_status', status: newStatus}));
    localStorage.setItem('chat-my-status', newStatus);
  }
  var errEl = document.getElementById('profileError');
  errEl.style.display = 'none';
  if (!dn) { errEl.textContent = 'Display name cannot be empty.'; errEl.style.display = 'block'; return; }

  if ((isAdmin || isOwner) && !mySessionToken) {
    var roleKey = isOwner ? 'owner_profile' : 'admin_profile';
    var saved = {display_name: dn, bio: bio, pfp_data: _profilePfpPending || myPfpData || ''};
    localStorage.setItem(roleKey, JSON.stringify(saved));
    myDisplayName = dn;
    myBio = bio;
    if (_profilePfpPending) { myPfpData = _profilePfpPending; _profilePfpPending = null; }
    updateProfileBtn();
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({type:'update_display_name', display_name: dn, pfp_data: myPfpData}));
    }
    document.getElementById('profileModal').style.display = 'none';
    return;
  }

  var payload = {display_name: dn, bio: bio};
  if (_profilePfpPending) payload.pfp_data = _profilePfpPending;
  fetch('/api/profile', {method:'POST',headers:{'Content-Type':'application/json','X-Session-Token':mySessionToken},body:JSON.stringify(payload)})
    .then(function(r){return r.json();})
    .then(function(d){
      if (d.error) { errEl.textContent=d.error; errEl.style.display='block'; return; }
      myDisplayName = dn;
      myBio = bio;
      if (_profilePfpPending) { myPfpData = _profilePfpPending; _profilePfpPending = null; }
      updateProfileBtn();
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({type:'update_display_name', display_name: dn, pfp_data: myPfpData}));
      }
      document.getElementById('profileModal').style.display = 'none';
    }).catch(function(){ errEl.textContent='Failed to save. Please try again.'; errEl.style.display='block'; });
});

document.getElementById('logoutBtn').addEventListener('click', function() {
  localStorage.removeItem('chat_session_token');
  mySessionToken = '';
  myUsername = '';
  myDisplayName = '';
  myPfpData = '';
  myBio = '';
  myIsGuest = false;
  if (ws) { ws.close(); ws = null; }
  document.getElementById('profileModal').style.display = 'none';
  document.getElementById('chatScreen').style.display = 'none';
  document.getElementById('joinScreen').style.display = 'flex';
  document.getElementById('roleBox').style.display = 'block';
  document.getElementById('guestBox').style.display = 'none';
});

function showChangelog() {
  document.getElementById('changelogModal').style.display = 'flex';
}
document.getElementById('updatesBtn').addEventListener('click', function() {
  document.getElementById('changelogModal').style.display = 'flex';
});
document.getElementById('helpBtn').addEventListener('click', function() {
  openShortcutsModal();
});
document.getElementById('searchBtn').addEventListener('click', function() {
  openSearch();
});
document.getElementById('changelogCloseBtn').addEventListener('click', function() {
  document.getElementById('changelogModal').style.display = 'none';
  fetch('/api/changelog-seen', {method:'POST',headers:{'X-Session-Token':mySessionToken}}).catch(function(){});
});

function showPfpViewer(url, name) {
  document.getElementById('pfpViewerImg').src = url;
  document.getElementById('pfpViewerName').textContent = name || '';
  document.getElementById('pfpViewerModal').style.display = 'flex';
}

var dmPanelTarget = null;
var dmPanelUser = null;

function openDmPanel(target, userObj) {
  dmPanelTarget = target;
  dmPanelUser = userObj || {};
  var panel = document.getElementById('dmPanel');
  var nameEl = document.getElementById('dmPanelName');
  var avatarEl = document.getElementById('dmPanelAvatar');
  var displayName = typeof userObj === 'object' && userObj ? (userObj.display_name || userObj.name || target) : target;
  var pfpUrl = typeof userObj === 'object' && userObj ? (userObj.pfp || '') : '';
  nameEl.textContent = displayName;
  if (pfpUrl) {
    avatarEl.style.backgroundImage = 'url(' + pfpUrl + ')';
    avatarEl.style.backgroundSize = 'cover';
    avatarEl.style.backgroundPosition = 'center';
    avatarEl.textContent = '';
  } else {
    avatarEl.style.backgroundImage = '';
    avatarEl.style.background = avatarColor(displayName);
    avatarEl.textContent = displayName.substring(0,2).toUpperCase();
  }
  panel.style.display = 'flex';
  if (!dmMessages[target]) dmMessages[target] = [];
  renderDmPanel();
  ws.send(JSON.stringify({type: 'dm_open', target: target}));
  var inp = document.getElementById('dmPanelInput');
  if (inp) { setTimeout(function() { inp.focus(); }, 100); }
}

function closeDmPanel() {
  document.getElementById('dmPanel').style.display = 'none';
  dmPanelTarget = null;
}

function renderDmPanel() {
  var el = document.getElementById('dmPanelMessages');
  if (!el || !dmPanelTarget) return;
  var msgs = dmMessages[dmPanelTarget] || [];
  el.innerHTML = '';
  if (msgs.length === 0) {
    var empty = document.createElement('div');
    empty.style.cssText = 'text-align:center;color:var(--text-muted);font-size:13px;padding:24px 0;';
    empty.textContent = 'No messages yet. Say hello!';
    el.appendChild(empty);
    return;
  }
  msgs.forEach(function(m) {
    var isMine = m.sender === myUsername || m.sender === myDisplayName;
    var row = document.createElement('div');
    row.style.cssText = 'display:flex;flex-direction:column;' + (isMine ? 'align-items:flex-end;' : 'align-items:flex-start;') + 'gap:2px;margin-bottom:4px;';
    var bubble = document.createElement('div');
    bubble.style.cssText = 'max-width:80%;padding:8px 12px;border-radius:' + (isMine ? '14px 14px 4px 14px' : '14px 14px 14px 4px') + ';font-size:13px;line-height:1.4;word-break:break-word;' + (isMine ? 'background:var(--accent);color:#fff;' : 'background:var(--bg-tertiary);color:var(--text-primary);');
    bubble.textContent = m.text || '';
    var meta = document.createElement('div');
    meta.style.cssText = 'font-size:11px;color:var(--text-muted);margin:0 2px;';
    meta.textContent = (m.display_name || m.sender || '') + (m.time ? '  ' + m.time : '');
    row.appendChild(bubble);
    row.appendChild(meta);
    el.appendChild(row);
  });
  el.scrollTop = el.scrollHeight;
}

// === AUTO-SCROLL TOGGLE ===
var _autoScroll = localStorage.getItem('chat-autoscroll') !== 'off';
(function() {
  var bar = document.getElementById('channelHeaderBar');
  if (!bar) return;
  var btn = document.createElement('button');
  btn.id = 'autoScrollBtn';
  btn.title = 'Toggle auto-scroll to newest messages';
  btn.style.cssText = 'margin-left:8px;padding:2px 7px;font-size:11px;border-radius:4px;border:1px solid var(--border);background:none;cursor:pointer;color:var(--text-muted);flex-shrink:0;';
  function updateBtn() {
    btn.textContent = _autoScroll ? '⬇ Auto' : '⬇ Off';
    btn.style.opacity = _autoScroll ? '1' : '0.5';
  }
  updateBtn();
  btn.addEventListener('click', function(e) {
    e.stopPropagation();
    _autoScroll = !_autoScroll;
    localStorage.setItem('chat-autoscroll', _autoScroll ? 'on' : 'off');
    updateBtn();
    showToast('Auto-scroll ' + (_autoScroll ? 'on' : 'off'), 'info');
  });
  // Attach to input row, not header bar (to avoid header rebuild on switchChannel)
  var inputRow = document.querySelector('.input-row');
  if (inputRow) inputRow.prepend(btn);
})();

// === SCROLL TO BOTTOM BUTTON ===
var _scrollUnread = 0;
(function() {
  var msgEl = document.getElementById('messages');
  var btn = document.getElementById('scrollToBottomBtn');
  if (!msgEl || !btn) return;
  btn.innerHTML = '↓';
  btn.addEventListener('click', function() {
    msgEl.scrollTop = msgEl.scrollHeight;
    _scrollUnread = 0;
    btn.innerHTML = '↓';
    btn.style.display = 'none';
  });
  msgEl.addEventListener('scroll', function() {
    var distFromBottom = msgEl.scrollHeight - msgEl.scrollTop - msgEl.clientHeight;
    if (distFromBottom < 60) {
      _scrollUnread = 0;
      btn.innerHTML = '↓';
      btn.style.display = 'none';
    } else {
      btn.style.display = 'flex';
    }
  });
  window._notifyScrollBtn = function() {
    var distFromBottom = msgEl.scrollHeight - msgEl.scrollTop - msgEl.clientHeight;
    if (distFromBottom > 60) {
      _scrollUnread++;
      btn.innerHTML = _scrollUnread > 0 ? '<span style="font-size:11px;font-weight:700;">' + (_scrollUnread > 99 ? '99+' : _scrollUnread) + '</span>' : '↓';
      btn.style.display = 'flex';
    }
  };
})();

document.getElementById('dmPanelSendBtn').addEventListener('click', function() {
  var inp = document.getElementById('dmPanelInput');
  var text = inp ? inp.value.trim() : '';
  if (!text || !dmPanelTarget || !ws || ws.readyState !== WebSocket.OPEN) return;
  ws.send(JSON.stringify({type: 'dm_message', target: dmPanelTarget, text: text}));
  inp.value = '';
  inp.focus();
});
document.getElementById('dmPanelInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') document.getElementById('dmPanelSendBtn').click();
  e.stopPropagation();
});

document.getElementById('adminCreatorBtn').addEventListener('click', function() {
  showAdminCreatorModal();
});

document.getElementById('manageAdminsBtn').addEventListener('click', function() {
  ws.send(JSON.stringify({type: 'get_admins'}));
});

document.getElementById('suggestionsBtn').addEventListener('click', function() {
  ws.send(JSON.stringify({type: 'get_suggestions'}));
});

document.getElementById('broadcastBtn').addEventListener('click', function() {
  var msg = prompt('Broadcast a system message to all users:');
  if (!msg || !msg.trim()) return;
  ws.send(JSON.stringify({type: 'owner_broadcast', text: msg.trim()}));
  showToast('Broadcast sent!', 'success');
});

(function() {
  var slowLevels = [0, 5, 10, 30, 60];
  document.getElementById('slowmodeBtn').addEventListener('click', function() {
    var cur = slowLevels.indexOf(_slowmodeDelay);
    var next = slowLevels[(cur + 1) % slowLevels.length];
    _slowmodeDelay = next;
    var lbl = next === 0 ? 'Off' : next + 's';
    document.getElementById('slowmodeBtnLabel').textContent = 'Slowmode: ' + lbl;
    showToast('Slowmode set to ' + lbl, 'info');
  });
})();

document.getElementById('announcementBtn').addEventListener('click', function() {
  _announcementMode = !_announcementMode;
  document.getElementById('announcementBtnLabel').textContent = 'Announce Mode: ' + (_announcementMode ? 'On' : 'Off');
  showToast('Announcement mode ' + (_announcementMode ? 'enabled — only staff can post.' : 'disabled.'), 'info');
});

document.getElementById('motdBtn').addEventListener('click', function() {
  var motd = prompt('Set Message of the Day (shown to all users on join):');
  if (motd === null) return;
  if (!motd.trim()) { showToast('MOTD cleared.', 'info'); ws.send(JSON.stringify({type: 'set_motd', text: ''})); return; }
  ws.send(JSON.stringify({type: 'set_motd', text: motd.trim()}));
  showToast('MOTD set!', 'success');
});

document.getElementById('wordFilterBtn').addEventListener('click', function() {
  var current = _wordFilter.join(', ');
  var input = prompt('Word filter (comma-separated words to block):', current);
  if (input === null) return;
  _wordFilter = input.split(',').map(function(w) { return w.trim().toLowerCase(); }).filter(Boolean);
  showToast('Word filter updated (' + _wordFilter.length + ' words).', 'success');
});

document.getElementById('bulkClearBtn').addEventListener('click', function() {
  if (!confirm('Clear ALL messages from the chat? This cannot be undone.')) return;
  var messDiv = document.getElementById('messages');
  if (messDiv) messDiv.innerHTML = '';
  addSystemMessage('Chat was bulk-cleared by the owner.');
  showToast('Chat cleared!', 'success');
});

document.getElementById('exportLogsBtn').addEventListener('click', function() {
  window._logsExportMode = true;
  ws.send(JSON.stringify({type: 'get_logs'}));
  showToast('Preparing log export...', 'info');
});

document.getElementById('sidebarToggleBtn').addEventListener('click', function() {
  var sidebar = document.getElementById('sidebar');
  if (!sidebar) return;
  sidebar.classList.toggle('sidebar-collapsed');
  this.title = sidebar.classList.contains('sidebar-collapsed') ? 'Show Sidebar' : 'Hide Sidebar';
});

(function() {
  var uSearch = document.getElementById('userSearchInput');
  var sortBtn = document.getElementById('sortUsersBtn');
  if (uSearch) {
    uSearch.addEventListener('input', function() {
      _userSearchQuery = this.value.toLowerCase().trim();
      if (lastUserList) renderUsers(lastUserList);
    });
    uSearch.addEventListener('keydown', function(e) { e.stopPropagation(); });
  }
  if (sortBtn) {
    sortBtn.addEventListener('click', function() {
      _userSortAZ = !_userSortAZ;
      this.style.color = _userSortAZ ? 'var(--accent)' : 'var(--text-muted)';
      if (lastUserList) renderUsers(lastUserList);
    });
  }
})();

// Konami code easter egg
(function() {
  var _konamiSeq = [];
  var _konamiCode = ['ArrowUp','ArrowUp','ArrowDown','ArrowDown','ArrowLeft','ArrowRight','ArrowLeft','ArrowRight','b','a'];
  document.addEventListener('keydown', function(e) {
    _konamiSeq.push(e.key);
    if (_konamiSeq.length > _konamiCode.length) _konamiSeq.shift();
    if (_konamiSeq.join(',') === _konamiCode.join(',')) {
      _konamiSeq = [];
      document.body.classList.add('party-mode');
      launchConfetti();
      showToast('🎉 PARTY MODE ACTIVATED! 🎉', 'success');
      setTimeout(function() { document.body.classList.remove('party-mode'); }, 10000);
    }
  });
})();

// Ctrl+K = open DM search
document.addEventListener('keydown', function(e) {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault();
    var uSearch = document.getElementById('userSearchInput');
    if (uSearch) { uSearch.focus(); uSearch.select(); }
  }
});

document.getElementById('suggestSendBtn').addEventListener('click', function() {
  var input = document.getElementById('suggestInput');
  var text = input.value.trim();
  if (!text || !ws) return;
  ws.send(JSON.stringify({type: 'send_suggestion', text: text}));
  input.value = '';
});

document.getElementById('suggestInput').addEventListener('keydown', function(e) {
  e.stopPropagation();
  if (e.key === 'Enter') document.getElementById('suggestSendBtn').click();
});

loadUserSettings();

document.getElementById('joinBtn').addEventListener('click', function() {
  var name = document.getElementById('usernameInput').value.trim();
  var err = document.getElementById('joinError');
  if (!name) { err.textContent = 'Please enter a username.'; err.style.display = 'block'; return; }
  if (!/^[a-zA-Z0-9_-]{1,20}$/.test(name)) { err.textContent = 'Letters, numbers, _ and - only (1-20 chars).'; err.style.display = 'block'; return; }
  if (RESERVED.test(name)) { err.textContent = 'Username cannot contain "admin" or "mod".'; err.style.display = 'block'; return; }
  myUsername = name;
  myIsGuest = true;
  document.getElementById('joinScreen').style.display = 'none';
  document.getElementById('chatScreen').style.display = 'flex';
  connectGuest(name);
  document.getElementById('msgInput').focus();
});

document.getElementById('usernameInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') document.getElementById('joinBtn').click();
});

document.getElementById('adminLoginBtn').addEventListener('click', function() {
  var token = document.getElementById('adminTokenInput').value.trim();
  var err = document.getElementById('adminError');
  if (!token) { err.textContent = 'Please enter the owner key.'; err.style.display = 'block'; return; }
  connectOwner(token);
});

document.getElementById('adminTokenInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') document.getElementById('adminLoginBtn').click();
});

document.getElementById('staffAdminLoginBtn').addEventListener('click', function() {
  var key = document.getElementById('staffAdminKeyInput').value.trim();
  var err = document.getElementById('staffAdminError');
  if (!key) { err.textContent = 'Please enter your admin key.'; err.style.display = 'block'; return; }
  connectStaffAdmin(key);
});

document.getElementById('staffAdminKeyInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') document.getElementById('staffAdminLoginBtn').click();
});

// ── Reply state ──────────────────────────────────────────────────────
var _replyTo = null;
function setReplyTo(m) {
  _replyTo = m;
  var bar = document.getElementById('replyPreviewBar');
  if (!m) { bar.style.display = 'none'; bar.innerHTML = ''; return; }
  bar.style.display = 'flex';
  bar.innerHTML = '<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">↩ Replying to <strong>' + escapeHtml(m.display_name || m.sender || '?') + '</strong>: ' + escapeHtml((m.text || '').substring(0, 60)) + ((m.text||'').length > 60 ? '…' : '') + '</span>';
  var cls = document.createElement('button');
  cls.textContent = '✕';
  cls.style.cssText = 'background:none;border:none;color:var(--text-muted);cursor:pointer;padding:0 2px;font-size:13px;flex-shrink:0;';
  cls.onclick = function() { setReplyTo(null); };
  bar.appendChild(cls);
}

// ── @mention autocomplete ─────────────────────────────────────────────
var _mentionQuery = null;
var _mentionSelectedIdx = -1;
function updateMentionDropdown() {
  var input = document.getElementById('msgInput');
  var val = input.value;
  var pos = input.selectionStart;
  var before = val.substring(0, pos);
  var match = before.match(/@(\w*)$/);
  var dd = document.getElementById('mentionDropdown');
  if (!match) { dd.style.display = 'none'; _mentionQuery = null; return; }
  _mentionQuery = match[1].toLowerCase();
  var onlineUsers = [];
  document.querySelectorAll('#userList .user-item').forEach(function(li) {
    var name = li.getAttribute('data-username') || li.textContent.trim().replace(/^[^\w]*/,'').split(' ')[0];
    if (name && name.toLowerCase().indexOf(_mentionQuery) === 0) onlineUsers.push(name);
  });
  if (onlineUsers.length === 0) { dd.style.display = 'none'; return; }
  dd.style.display = 'block';
  dd.innerHTML = '';
  _mentionSelectedIdx = -1;
  onlineUsers.slice(0, 8).forEach(function(name, i) {
    var item = document.createElement('div');
    item.style.cssText = 'padding:8px 14px;cursor:pointer;font-size:13px;color:var(--text-primary);display:flex;align-items:center;gap:8px;';
    item.innerHTML = '<div style="width:24px;height:24px;border-radius:50%;background:var(--accent);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:#fff;flex-shrink:0;">' + escapeHtml(name.charAt(0).toUpperCase()) + '</div>' + escapeHtml(name);
    item.addEventListener('mouseenter', function() {
      dd.querySelectorAll('div').forEach(function(d) { d.style.background = ''; });
      item.style.background = 'var(--bg-tertiary)';
      _mentionSelectedIdx = i;
    });
    item.addEventListener('click', function() {
      completeMention(name);
    });
    dd.appendChild(item);
  });
}
function completeMention(name) {
  var input = document.getElementById('msgInput');
  var val = input.value;
  var pos = input.selectionStart;
  var before = val.substring(0, pos);
  var after = val.substring(pos);
  var newBefore = before.replace(/@(\w*)$/, '@' + name + ' ');
  input.value = newBefore + after;
  input.selectionStart = input.selectionEnd = newBefore.length;
  document.getElementById('mentionDropdown').style.display = 'none';
  _mentionQuery = null;
  input.focus();
}

var _emojiShortcodes = {':thumbsup:':'👍',':thumbsdown:':'👎',':heart:':'❤️',':smile:':'😊',':grin:':'😁',':laugh:':'😂',':joy:':'😂',':lol:':'😂',':sob:':'😭',':cry:':'😢',':fire:':'🔥',':star:':'⭐',':check:':'✅',':x:':'❌',':eyes:':'👀',':wave:':'👋',':clap:':'👏',':cool:':'😎',':rocket:':'🚀',':100:':'💯',':tada:':'🎉',':poop:':'💩',':skull:':'💀',':thinking:':'🤔',':shrug:':'🤷',':ok:':'👌',':pray:':'🙏',':muscle:':'💪',':party:':'🥳',':mind_blown:':'🤯',':ghost:':'👻',':alien:':'👽',':pizza:':'🍕',':coffee:':'☕',':bruh:':'😑',':gg:':'🎮',':sus:':'👀',':based:':'👑',':nerd:':'🤓',':facepalm:':'🤦'};
function applyShortcodes(text) {
  return text.replace(/:[a-z0-9_+\-]+:/gi, function(m) { return _emojiShortcodes[m.toLowerCase()] || m; });
}

function wrapSel(before, after) { wrapSelection(document.getElementById('msgInput'), before, after); }

function openSearch() {
  var bar = document.getElementById('msgSearchBar');
  if (bar) { bar.classList.add('open'); setTimeout(function() { var i = document.getElementById('msgSearchInput'); if(i) i.focus(); }, 50); }
}
function closeSearch() {
  var bar = document.getElementById('msgSearchBar');
  if (bar) bar.classList.remove('open');
  var inp = document.getElementById('msgSearchInput');
  if (inp) inp.value = '';
  document.querySelectorAll('#messages .msg-highlight,.msg-highlight.current').forEach(function(el){ el.outerHTML = el.innerHTML; });
  var cnt = document.getElementById('msgSearchCount'); if(cnt) cnt.textContent = '';
  _srchMatches = []; _srchIdx = 0;
}
var _srchMatches = [], _srchIdx = 0;
(function() {
  var inp = document.getElementById('msgSearchInput');
  if (!inp) return;
  inp.addEventListener('input', function() {
    var q = this.value.trim().toLowerCase();
    var cnt = document.getElementById('msgSearchCount');
    _srchMatches = []; _srchIdx = 0;
    document.querySelectorAll('#messages .msg-body, #messages .msg-grouped-row .msg-body').forEach(function(el) {
      if (!el) return;
      if (q && el.textContent.toLowerCase().indexOf(q) >= 0) _srchMatches.push(el);
    });
    if (cnt) cnt.textContent = q ? (_srchMatches.length + ' result' + (_srchMatches.length===1?'':'s')) : '';
    if (_srchMatches.length > 0 && q) { _srchMatches[0].scrollIntoView({block:'center'}); }
  });
  inp.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') { closeSearch(); }
    else if (e.key === 'Enter') {
      if (_srchMatches.length === 0) return;
      _srchIdx = (_srchIdx + 1) % _srchMatches.length;
      _srchMatches[_srchIdx].scrollIntoView({block:'center'});
    }
    e.stopPropagation();
  });
})();

// Keyboard shortcuts modal
function openShortcutsModal() {
  var existing = document.getElementById('shortcutsModal');
  if (existing) { existing.remove(); return; }
  var modal = document.createElement('div');
  modal.id = 'shortcutsModal';
  modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:10000;';
  var box = document.createElement('div');
  box.style.cssText = 'background:var(--bg-secondary);border-radius:12px;padding:24px;min-width:340px;max-width:90vw;border:1px solid var(--border);';
  var codeStyle = 'background:var(--bg-tertiary);padding:2px 7px;border-radius:4px;font-size:12px;color:var(--text-secondary);';
  var shortcuts = [
    ['Ctrl+F','Search messages'],['Ctrl+B','Bold selected text'],['Ctrl+I','Italic selected text'],
    ['Enter','Send message'],['Shift+Enter','New line'],['Escape','Cancel reply / close'],
    ['Tab','Complete @mention'],['@name','Mention a user'],[':thumbsup:','Insert emoji shortcode'],['Double-click msg','Quick 👍 reaction']
  ];
  var grid = '<div style="display:grid;grid-template-columns:auto 1fr;gap:6px 16px;font-size:13px;">';
  shortcuts.forEach(function(s) { grid += '<code style="' + codeStyle + '">' + s[0] + '</code><span>' + s[1] + '</span>'; });
  grid += '</div>';
  box.innerHTML = '<div style="font-size:17px;font-weight:700;color:var(--text-primary);margin-bottom:16px;">⌨️ Keyboard Shortcuts</div>' + grid;
  var closeBtn = document.createElement('button');
  closeBtn.textContent = 'Got it';
  closeBtn.style.cssText = 'margin-top:18px;padding:8px 20px;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:13px;font-weight:600;width:100%;';
  closeBtn.addEventListener('click', function() { modal.remove(); });
  box.appendChild(closeBtn);
  modal.appendChild(box);
  modal.addEventListener('click', function(e) { if(e.target===modal) modal.remove(); });
  document.body.appendChild(modal);
}
document.addEventListener('keydown', function(e) {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
  if (e.key === '?') { openShortcutsModal(); }
});

// ── Slash command system ─────────────────────────────────────────────────────
var _sessionMsgs = 0;
var _sessionStart = Date.now();
var _slowmodeDelay = 0;
var _lastMsgTime = 0;
var _announcementMode = false;
var _wordFilter = [];
var _msgAnimations = localStorage.getItem('chat-msg-animate') !== 'off';

var _8ballAnswers = ['It is certain.','It is decidedly so.','Without a doubt.','Yes, definitely.','You may rely on it.','As I see it, yes.','Most likely.','Outlook good.','Yes.','Signs point to yes.','Reply hazy, try again.','Ask again later.','Better not tell you now.','Cannot predict now.','Concentrate and ask again.','Don\\'t count on it.','My reply is no.','My sources say no.','Outlook not so good.','Very doubtful.'];
var _triviaQs = [
  ['What is the capital of Japan?','Tokyo'],['How many sides does a hexagon have?','6'],['What is the largest planet in our solar system?','Jupiter'],
  ['What is the chemical symbol for gold?','Au'],['Who painted the Mona Lisa?','Leonardo da Vinci'],['What is the speed of light (approx, km/s)?','299,792'],
  ['How many bones are in the adult human body?','206'],['What is the smallest country in the world?','Vatican City'],
  ['What language has the most native speakers?','Mandarin Chinese'],['What is 12 × 12?','144'],
];

var _slashCmds = [
  {name:'/me',        desc:'Do an action  —  /me dances'},
  {name:'/roll',      desc:'Roll dice  —  /roll 20'},
  {name:'/flip',      desc:'Flip a coin'},
  {name:'/8ball',     desc:'Ask the magic 8-ball a question'},
  {name:'/shrug',     desc:'Append a shrug emoticon'},
  {name:'/tableflip', desc:'(╯°□°)╯ ︵ ┻━┻'},
  {name:'/unflip',    desc:'Put the table back'},
  {name:'/lenny',     desc:'Lenny face'},
  {name:'/shout',     desc:'MAKE IT LOUD  —  /shout text'},
  {name:'/rainbow',   desc:'Colorful text  —  /rainbow text'},
  {name:'/trivia',    desc:'Post a random trivia question'},
  {name:'/poll',      desc:'Create a poll  —  /poll Q | A | B'},
];
var _slashIdx = -1;
function updateSlashDropdown() {
  var inp = document.getElementById('msgInput');
  var val = inp ? inp.value : '';
  var dd = document.getElementById('slashDropdown');
  if (!dd || !inp) return;
  if (!val || !val.startsWith('/') || val.indexOf(' ') > -1) {
    dd.classList.remove('open'); _slashIdx = -1; return;
  }
  var query = val.toLowerCase();
  var matches = _slashCmds.filter(function(c){ return c.name.startsWith(query); });
  if (!matches.length) { dd.classList.remove('open'); _slashIdx = -1; return; }
  dd.innerHTML = '';
  var hdr = document.createElement('div');
  hdr.className = 'slash-cmd-header';
  hdr.textContent = 'Commands — \u2191\u2193 to navigate, Enter/Tab to pick';
  dd.appendChild(hdr);
  matches.forEach(function(c, i) {
    var item = document.createElement('div');
    item.className = 'slash-cmd-item' + (i === _slashIdx ? ' selected' : '');
    var nm = document.createElement('span');
    nm.className = 'slash-cmd-name';
    nm.textContent = c.name;
    var ds = document.createElement('span');
    ds.className = 'slash-cmd-desc';
    ds.textContent = c.desc;
    item.appendChild(nm);
    item.appendChild(ds);
    item.addEventListener('mousedown', function(ev) {
      ev.preventDefault();
      inp.value = c.name + ' ';
      inp.focus();
      dd.classList.remove('open'); _slashIdx = -1;
    });
    dd.appendChild(item);
  });
  dd.classList.add('open');
}
function processSlashCommand(rawText, inputEl) {
  var text = rawText.trim();
  var cmd = text.split(' ')[0].toLowerCase();
  var rest = text.slice(cmd.length).trim();
  if (cmd === '/shrug') { inputEl.value = (rest || '') + ' \u00AF\\_(\u30C4)_/\u00AF'; return false; }
  if (cmd === '/tableflip') { inputEl.value = '(\u256F\u00B0\u25A1\u00B0\uFF09\u256F\uFE35 \u253B\u2501\u253B'; return false; }
  if (cmd === '/unflip') { inputEl.value = '\u252C\u2500\u252C\u30CE( \u00BA _ \u00BA\u30CE)'; return false; }
  if (cmd === '/lenny') { inputEl.value = '( \u0361\u00B0 \u035C\u0296 \u0361\u00B0)'; return false; }
  if (cmd === '/shout') { if (!rest) { showToast('Usage: /shout YOUR TEXT', 'info'); return true; } inputEl.value = rest.toUpperCase(); return false; }
  if (cmd === '/rainbow') {
    if (!rest) { showToast('Usage: /rainbow your text', 'info'); return true; }
    inputEl.value = '🌈 ' + rest;
    return false;
  }
  if (cmd === '/me') {
    if (!rest) { showToast('Usage: /me does something', 'info'); return true; }
    inputEl.value = '👤 *' + rest + '*';
    return false;
  }
  if (cmd === '/roll') {
    var sides = parseInt(rest) || 6;
    if (sides < 2 || sides > 10000) sides = 6;
    var result = Math.floor(Math.random() * sides) + 1;
    inputEl.value = '🎲 Rolled a ' + sides + '-sided die: **' + result + '**!';
    return false;
  }
  if (cmd === '/flip') {
    var coin = Math.random() < 0.5 ? 'Heads' : 'Tails';
    if (coin === 'Heads') launchConfetti();
    inputEl.value = '🪙 Flipped a coin: **' + coin + '**!';
    return false;
  }
  if (cmd === '/8ball') {
    var q = rest || 'question';
    var ans = _8ballAnswers[Math.floor(Math.random() * _8ballAnswers.length)];
    inputEl.value = '🎱 *' + q + '* — ' + ans;
    return false;
  }
  if (cmd === '/trivia') {
    var t = _triviaQs[Math.floor(Math.random() * _triviaQs.length)];
    inputEl.value = '🧠 **Trivia:** ' + t[0] + ' ||Answer: ' + t[1] + '||';
    return false;
  }
  if (cmd === '/poll') {
    var parts = text.slice(5).split('|').map(function(s){return s.trim();}).filter(Boolean);
    if (parts.length < 3) { showToast('Usage: /poll Question | Option 1 | Option 2', 'info'); return true; }
    showLocalPoll(parts[0], parts.slice(1));
    inputEl.value = '';
    return true;
  }
  return false;
}

function showLocalPoll(question, options) {
  var messagesDiv = document.getElementById('messages');
  if (!messagesDiv) return;
  var empty = document.getElementById('emptyState');
  if (empty) empty.style.display = 'none';
  var row = document.createElement('div');
  row.className = 'msg-row' + (_msgAnimations ? ' msg-animate' : '');
  row.style.cssText = 'padding:6px 16px;';
  var votes = options.map(function() { return 0; });
  var voted = -1;
  function render() {
    row.innerHTML = '';
    var w = document.createElement('div');
    w.className = 'poll-widget';
    w.innerHTML = '<div style="font-weight:700;color:var(--text-primary);margin-bottom:8px;">📊 ' + escapeHtml(question) + '</div>';
    var total = votes.reduce(function(a,b){return a+b;},0);
    options.forEach(function(opt, i) {
      var pct = total > 0 ? Math.round(votes[i]/total*100) : 0;
      var ob = document.createElement('div');
      ob.className = 'poll-option';
      ob.innerHTML = '<span style="flex:1;font-size:13px;color:var(--text-primary);">' + escapeHtml(opt) + '</span><span style="font-size:12px;color:var(--text-muted);min-width:32px;text-align:right;">' + pct + '%</span>';
      var bar = document.createElement('div');
      bar.style.cssText = 'width:100%;background:var(--bg-primary);border-radius:3px;height:6px;margin-top:4px;overflow:hidden;';
      var fill = document.createElement('div');
      fill.className = 'poll-bar'; fill.style.width = pct + '%';
      bar.appendChild(fill); ob.appendChild(bar);
      if (voted === -1) {
        ob.style.cursor = 'pointer';
        ob.addEventListener('click', function() { if (voted >= 0) return; votes[i]++; voted = i; render(); });
      }
      w.appendChild(ob);
    });
    if (voted >= 0) {
      var note = document.createElement('div');
      note.style.cssText = 'font-size:11px;color:var(--text-muted);margin-top:6px;';
      note.textContent = 'Voted! (' + total + ' total)';
      w.appendChild(note);
    }
    row.appendChild(w);
  }
  render();
  messagesDiv.appendChild(row);
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

document.getElementById('sendBtn').addEventListener('click', function() {
  var input = document.getElementById('msgInput');
  var rawText = input.value.trim();
  if (_announcementMode && !isOwner && !isAdmin) { showToast('Announcement mode is on — only staff can post.', 'info'); return; }
  if (_slowmodeDelay > 0 && !isOwner && !isAdmin) {
    var elapsed = Date.now() - _lastMsgTime;
    if (elapsed < _slowmodeDelay * 1000) {
      var wait = Math.ceil((_slowmodeDelay * 1000 - elapsed) / 1000);
      showToast('Slowmode: wait ' + wait + 's before sending again.', 'info'); return;
    }
  }
  if (rawText.startsWith('/')) {
    var cmdHandled = processSlashCommand(rawText, input);
    if (cmdHandled === true) { input.focus(); return; }
    rawText = input.value.trim();
  }
  var text = applyShortcodes(rawText);
  if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
  _lastMsgTime = Date.now();
  _sessionMsgs++;
  localStorage.removeItem('draft:' + currentChannel);
  var replyCtx = _replyTo ? { reply_sender: _replyTo.display_name || _replyTo.sender, reply_text: (_replyTo.text || '').substring(0, 80) } : {};
  if (currentChannel === 'general') {
    if (isAdmin) {
      var name = document.getElementById('nameInput').value.trim() || 'Admin';
      ws.send(JSON.stringify(Object.assign({ type: 'chat', text: text, name: name }, replyCtx)));
    } else {
      ws.send(JSON.stringify(Object.assign({ type: 'chat', text: text }, replyCtx)));
    }
  } else if (currentChannel.startsWith('dm:')) {
    var target = currentChannel.substring(3);
    if (isAdmin) {
      var name = document.getElementById('nameInput').value.trim() || 'Admin';
      ws.send(JSON.stringify(Object.assign({ type: 'dm_message', target: target, text: text, name: name }, replyCtx)));
    } else {
      ws.send(JSON.stringify(Object.assign({ type: 'dm_message', target: target, text: text }, replyCtx)));
    }
  } else if (currentChannel.startsWith('gc:')) {
    var gcId = currentChannel.substring(3);
    if (isAdmin) {
      var name = document.getElementById('nameInput').value.trim() || 'Admin';
      ws.send(JSON.stringify(Object.assign({ type: 'gc_message', gc_id: gcId, text: text, name: name }, replyCtx)));
    } else {
      ws.send(JSON.stringify(Object.assign({ type: 'gc_message', gc_id: gcId, text: text }, replyCtx)));
    }
  }
  setReplyTo(null);
  input.value = '';
  input.focus();
  document.getElementById('mentionDropdown').style.display = 'none';
});

document.getElementById('msgInput').addEventListener('input', function() {
  updateSlashDropdown();
  updateMentionDropdown();
  var len = this.value.length;
  var counter = document.getElementById('charCounter');
  if (counter) {
    if (len > 100) {
      counter.style.display = '';
      counter.textContent = len + '/2000';
      counter.className = 'char-counter' + (len > 1800 ? ' over' : len > 1500 ? ' warn' : '');
    } else { counter.style.display = 'none'; }
  }
  if (currentChannel) {
    if (this.value) localStorage.setItem('draft:' + currentChannel, this.value);
    else localStorage.removeItem('draft:' + currentChannel);
  }
});
document.getElementById('msgInput').addEventListener('keydown', function(e) {
  var sdd = document.getElementById('slashDropdown');
  var sitems = sdd ? sdd.querySelectorAll('.slash-cmd-item') : [];
  if (sdd && sdd.classList.contains('open') && sitems.length > 0) {
    if (e.key === 'ArrowDown') { e.preventDefault(); _slashIdx = Math.min(_slashIdx + 1, sitems.length - 1); sitems.forEach(function(d,i){d.classList.toggle('selected', i===_slashIdx);}); return; }
    if (e.key === 'ArrowUp') { e.preventDefault(); _slashIdx = Math.max(_slashIdx - 1, 0); sitems.forEach(function(d,i){d.classList.toggle('selected', i===_slashIdx);}); return; }
    if (e.key === 'Enter' || e.key === 'Tab') {
      var sel = _slashIdx >= 0 ? sitems[_slashIdx] : sitems[0];
      if (sel) { e.preventDefault(); sel.dispatchEvent(new MouseEvent('mousedown')); return; }
    }
    if (e.key === 'Escape') { sdd.classList.remove('open'); _slashIdx = -1; return; }
  }
  var dd = document.getElementById('mentionDropdown');
  var items = dd.querySelectorAll('div');
  if (dd.style.display !== 'none' && items.length > 0) {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      _mentionSelectedIdx = Math.min(_mentionSelectedIdx + 1, items.length - 1);
      items.forEach(function(d, i) { d.style.background = i === _mentionSelectedIdx ? 'var(--bg-tertiary)' : ''; });
      return;
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      _mentionSelectedIdx = Math.max(_mentionSelectedIdx - 1, 0);
      items.forEach(function(d, i) { d.style.background = i === _mentionSelectedIdx ? 'var(--bg-tertiary)' : ''; });
      return;
    }
    if (e.key === 'Enter' || e.key === 'Tab') {
      if (_mentionSelectedIdx >= 0 && items[_mentionSelectedIdx]) {
        e.preventDefault();
        items[_mentionSelectedIdx].click();
        return;
      } else if (e.key === 'Tab') {
        e.preventDefault();
        items[0].click();
        return;
      }
    }
    if (e.key === 'Escape') { dd.style.display = 'none'; _mentionQuery = null; return; }
  }
  if (e.key === 'Enter' && !e.shiftKey) { document.getElementById('sendBtn').click(); return; }
  if (e.key === 'Escape') {
    var srchBar = document.getElementById('msgSearchBar');
    if (srchBar && srchBar.classList.contains('open')) { closeSearch(); return; }
    setReplyTo(null); return;
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 'f') { e.preventDefault(); openSearch(); return; }
  // Ctrl+B bold, Ctrl+I italic
  if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
    e.preventDefault();
    wrapSelection(this, '**', '**');
  }
  if ((e.ctrlKey || e.metaKey) && e.key === 'i') {
    e.preventDefault();
    wrapSelection(this, '_', '_');
  }
});
// Wrap selection helper
function wrapSelection(inp, before, after) {
  var start = inp.selectionStart, end = inp.selectionEnd;
  var val = inp.value;
  if (start === end) {
    inp.value = val.substring(0, start) + before + after + val.substring(end);
    inp.selectionStart = inp.selectionEnd = start + before.length;
  } else {
    inp.value = val.substring(0, start) + before + val.substring(start, end) + after + val.substring(end);
    inp.selectionStart = start + before.length;
    inp.selectionEnd = end + before.length;
  }
}
// Image paste from clipboard
document.getElementById('msgInput').addEventListener('paste', function(e) {
  var items = e.clipboardData && e.clipboardData.items;
  if (!items) return;
  for (var i = 0; i < items.length; i++) {
    if (items[i].type.indexOf('image') !== -1) {
      e.preventDefault();
      var file = items[i].getAsFile();
      if (file) handleFileSelection([file]);
      break;
    }
  }
});
// Global Escape: close emoji panel
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    var panel = document.getElementById('emojiPanel');
    if (panel && panel.classList.contains('open')) panel.classList.remove('open');
  }
});

var _e = function(cp) { return String.fromCodePoint(cp); };
var emojiCodes = {
  'Smileys': [0x1F600,0x1F603,0x1F604,0x1F601,0x1F606,0x1F605,0x1F602,0x1F923,0x1F60A,0x1F607,0x1F642,0x1F643,0x1F609,0x1F60C,0x1F60D,0x1F970,0x1F618,0x1F617,0x1F619,0x1F61A,0x1F60B,0x1F61B,0x1F61C,0x1F92A,0x1F61D,0x1F911,0x1F917,0x1F92D,0x1F92B,0x1F914,0x1F910,0x1F928,0x1F610,0x1F611,0x1F636,0x1F60F,0x1F612,0x1F644,0x1F62C,0x1F925,0x1F60E,0x1F913,0x1F615,0x1F61F,0x1F641,0x1F614,0x1F62E,0x1F62F,0x1F632,0x1F633,0x1F97A,0x1F628,0x1F630,0x1F625,0x1F622,0x1F62D,0x1F631,0x1F616,0x1F623,0x1F61E,0x1F613,0x1F629,0x1F624,0x1F620,0x1F621,0x1F92C,0x1F608,0x1F47F,0x1F480,0x1F4A9,0x1F921,0x1F47B,0x1F47D,0x1F47E,0x1F916],
  'Gestures': [0x1F44D,0x1F44E,0x1F44A,0x270A,0x1F91B,0x1F91C,0x1F44F,0x1F64C,0x1F450,0x1F932,0x1F91D,0x1F64F,0x270D,0x1F4AA,0x1F448,0x1F449,0x261D,0x1F446,0x1F447,0x270C,0x1F91E,0x1F596,0x1F918,0x1F919,0x1F590,0x270B,0x1F44B,0x1F44C,0x2764,0x1F9E1,0x1F49B,0x1F49A,0x1F499,0x1F49C,0x1F5A4,0x1F494,0x1F495,0x1F496,0x1F497,0x1F498,0x1F49D,0x1F49E,0x1F49F,0x1F48B],
  'Animals': [0x1F436,0x1F431,0x1F42D,0x1F439,0x1F430,0x1F98A,0x1F43B,0x1F43C,0x1F428,0x1F42F,0x1F981,0x1F42E,0x1F437,0x1F438,0x1F435,0x1F648,0x1F649,0x1F64A,0x1F412,0x1F414,0x1F427,0x1F426,0x1F985,0x1F986,0x1F989,0x1F987,0x1F40A,0x1F422,0x1F40D,0x1F432,0x1F409,0x1F433,0x1F42C,0x1F41F,0x1F419,0x1F41A,0x1F40C,0x1F98B,0x1F41B,0x1F41C,0x1F41D,0x1F41E,0x1F577,0x1F982],
  'Food': [0x1F34E,0x1F34F,0x1F350,0x1F34A,0x1F34B,0x1F34C,0x1F349,0x1F347,0x1F353,0x1F348,0x1F352,0x1F351,0x1F34D,0x1F965,0x1F95D,0x1F345,0x1F346,0x1F951,0x1F955,0x1F33D,0x1F336,0x1F344,0x1F35E,0x1F950,0x1F956,0x1F9C0,0x1F354,0x1F355,0x1F32D,0x1F32E,0x1F32F,0x1F959,0x1F373,0x1F958,0x1F372,0x1F35C,0x1F363,0x1F371,0x1F35F,0x1F370,0x1F382,0x1F366,0x1F367,0x1F368,0x1F369,0x1F36A,0x1F36B,0x1F36C,0x1F36D,0x2615,0x1F375,0x1F37A,0x1F37B,0x1F377,0x1F378,0x1F379],
  'Activities': [0x26BD,0x1F3C0,0x1F3C8,0x26BE,0x1F3BE,0x1F3B1,0x1F3D3,0x1F3AF,0x1F3A3,0x1F3BF,0x1F3AE,0x1F3B2,0x1F9E9,0x2660,0x2665,0x2666,0x2663,0x1F3AD,0x1F3A8,0x1F3B5,0x1F3B6,0x1F3B9,0x1F3B7,0x1F3BA,0x1F3B8],
  'Objects': [0x1F4F1,0x1F4BB,0x1F4F7,0x1F4F9,0x1F4FA,0x1F4A1,0x1F526,0x1F4B0,0x1F4B3,0x1F48E,0x1F527,0x1F528,0x2699,0x1F52B,0x1F52A,0x1F52E,0x1F52D,0x1F52C,0x1F48A,0x1F489,0x1F511,0x1F6AA,0x1F6CF],
  'Symbols': [0x2764,0x1F525,0x2B50,0x1F31F,0x26A1,0x2728,0x1F386,0x1F387,0x1F388,0x1F389,0x1F38A,0x2714,0x274C,0x2753,0x2757,0x1F4AF,0x26D4,0x1F6AB,0x1F6D1,0x267B,0x2705,0x2795,0x2796,0x1F4B2,0x1F440]
};
var emojiData = {};
var emojiNameMap = {};
(function() {
  var names = {0x1F600:'grinning',0x1F603:'smiley',0x1F604:'smile',0x1F601:'grin',0x1F606:'laughing',0x1F605:'sweat smile',0x1F602:'joy',0x1F923:'rofl',0x1F60A:'blush',0x1F607:'innocent',0x1F642:'slight smile',0x1F643:'upside down',0x1F609:'wink',0x1F60C:'relieved',0x1F60D:'heart eyes',0x1F970:'hearts',0x1F618:'kissing heart',0x1F60B:'yum',0x1F61B:'tongue',0x1F61C:'wink tongue',0x1F92A:'zany',0x1F914:'thinking',0x1F910:'zipper mouth',0x1F60F:'smirk',0x1F612:'unamused',0x1F644:'eye roll',0x1F60E:'sunglasses',0x1F913:'nerd',0x1F641:'frown',0x1F614:'pensive',0x1F622:'cry',0x1F62D:'sob',0x1F631:'scream',0x1F620:'angry',0x1F621:'rage',0x1F92C:'cursing',0x1F608:'devil',0x1F47F:'imp',0x1F480:'skull',0x1F4A9:'poop',0x1F921:'clown',0x1F47B:'ghost',0x1F47D:'alien',0x1F916:'robot',0x1F44D:'thumbs up',0x1F44E:'thumbs down',0x1F44A:'fist',0x1F44F:'clap',0x1F64C:'raised hands',0x1F64F:'pray',0x1F4AA:'muscle',0x270C:'victory hand',0x1F918:'rock',0x1F44C:'ok',0x1F44B:'wave',0x2764:'heart',0x1F525:'fire',0x2B50:'star',0x1F4AF:'100',0x1F389:'party',0x2714:'check',0x274C:'x',0x1F440:'eyes',0x1F436:'dog',0x1F431:'cat',0x1F42D:'mouse',0x1F430:'rabbit',0x1F98A:'fox',0x1F43C:'panda',0x1F981:'lion',0x1F34E:'apple',0x1F354:'burger',0x1F355:'pizza',0x1F382:'cake',0x2615:'coffee',0x1F37A:'beer',0x26BD:'soccer',0x1F3C0:'basketball',0x1F3AE:'game',0x1F3B5:'music',0x1F3A8:'art',0x1F4F1:'phone',0x1F4BB:'laptop',0x1F4A1:'bulb',0x1F511:'key',0x2728:'sparkles',0x1F388:'balloon',0x2705:'green check',0x26A1:'lightning',0x1F48E:'gem',0x1F527:'wrench',0x2699:'gear'};
  Object.keys(emojiCodes).forEach(function(cat) {
    emojiData[cat] = emojiCodes[cat].map(function(cp) { return _e(cp); });
  });
  Object.keys(names).forEach(function(cp) {
    emojiNameMap[_e(parseInt(cp))] = names[cp];
  });
})();

var currentEmojiCat = 'Smileys';

function renderEmojiPicker(filter) {
  var grid = document.getElementById('emojiGrid');
  grid.innerHTML = '';
  var cats = filter ? Object.keys(emojiData) : [currentEmojiCat];
  cats.forEach(function(cat) {
    emojiData[cat].forEach(function(em) {
      if (filter) {
        var name = emojiNameMap[em] || '';
        if (name.indexOf(filter.toLowerCase()) === -1) return;
      }
      var btn = document.createElement('button');
      btn.className = 'emoji-item';
      btn.textContent = em;
      btn.title = emojiNameMap[em] || '';
      btn.type = 'button';
      btn.addEventListener('click', function() {
        var input = document.getElementById('msgInput');
        var pos = input.selectionStart || input.value.length;
        input.value = input.value.substring(0, pos) + em + input.value.substring(pos);
        input.focus();
        input.selectionStart = input.selectionEnd = pos + em.length;
      });
      grid.appendChild(btn);
    });
  });
}

function renderEmojiCatBar() {
  var bar = document.getElementById('emojiCatBar');
  bar.innerHTML = '';
  var catIcons = {'Smileys':0x1F600,'Gestures':0x1F44D,'Animals':0x1F436,'Food':0x1F34E,'Activities':0x26BD,'Objects':0x1F4F1,'Symbols':0x2764};
  Object.keys(emojiData).forEach(function(cat) {
    var btn = document.createElement('button');
    btn.className = 'emoji-cat-btn' + (cat === currentEmojiCat ? ' active' : '');
    btn.type = 'button';
    btn.textContent = catIcons[cat] ? _e(catIcons[cat]) : cat.charAt(0);
    btn.title = cat;
    btn.addEventListener('click', function() {
      currentEmojiCat = cat;
      document.getElementById('emojiSearch').value = '';
      renderEmojiCatBar();
      renderEmojiPicker('');
    });
    bar.appendChild(btn);
  });
}

document.getElementById('emojiBtn').addEventListener('click', function(e) {
  e.stopPropagation();
  var panel = document.getElementById('emojiPanel');
  var isOpen = panel.classList.contains('open');
  if (isOpen) {
    panel.classList.remove('open');
  } else {
    renderEmojiCatBar();
    renderEmojiPicker('');
    panel.classList.add('open');
    document.getElementById('emojiSearch').focus();
  }
});

document.getElementById('emojiSearch').addEventListener('input', function() {
  var q = this.value.trim();
  renderEmojiPicker(q);
});

document.getElementById('emojiSearch').addEventListener('keydown', function(e) {
  e.stopPropagation();
});

document.addEventListener('click', function(e) {
  var panel = document.getElementById('emojiPanel');
  var btn = document.getElementById('emojiBtn');
  if (panel && btn && !panel.contains(e.target) && e.target !== btn) {
    panel.classList.remove('open');
  }
});

// Image attachment / paste / drag-and-drop support
function addImageToPending(file) {
  if (!file || !file.type.startsWith('image/')) return;
  var reader = new FileReader();
  reader.onload = function(ev) {
    pendingImages.push({dataUrl: ev.target.result, name: file.name});
    refreshImagePreview();
  };
  reader.readAsDataURL(file);
}

function refreshImagePreview() {
  var bar = document.getElementById('imagePreviewBar');
  if (!bar) return;
  if (pendingImages.length === 0) { bar.style.display = 'none'; bar.innerHTML = ''; return; }
  bar.style.display = 'flex'; bar.innerHTML = '';
  pendingImages.forEach(function(img, idx) {
    var item = document.createElement('div');
    item.className = 'image-preview-item';
    var el = document.createElement('img');
    el.src = img.dataUrl;
    item.appendChild(el);
    var rm = document.createElement('button');
    rm.className = 'remove-img';
    rm.textContent = '\u00D7';
    rm.addEventListener('click', function() {
      pendingImages.splice(idx, 1);
      refreshImagePreview();
    });
    item.appendChild(rm);
    bar.appendChild(item);
  });
}

function sendPendingImages() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  pendingImages.forEach(function(img) {
    var msgObj;
    if (currentChannel === 'general') {
      if (isAdmin) {
        var name = (document.getElementById('nameInput') || {}).value || 'Admin';
        msgObj = {type: 'chat', text: img.dataUrl, name: name};
      } else {
        msgObj = {type: 'chat', text: img.dataUrl};
      }
    } else if (currentChannel.startsWith('dm:')) {
      var target = currentChannel.substring(3);
      msgObj = {type: 'dm_message', target: target, text: img.dataUrl};
    } else if (currentChannel.startsWith('gc:')) {
      var gcId = currentChannel.substring(3);
      msgObj = {type: 'gc_message', gc_id: gcId, text: img.dataUrl};
    }
    if (msgObj) ws.send(JSON.stringify(msgObj));
  });
  pendingImages = [];
  refreshImagePreview();
}

// Attach button click -> file input
document.addEventListener('click', function(e) {
  if (e.target && e.target.id === 'attachBtn') {
    var fi = document.getElementById('fileInput');
    if (fi) fi.click();
  }
});
document.addEventListener('change', function(e) {
  if (e.target && e.target.id === 'fileInput') {
    for (var i = 0; i < e.target.files.length; i++) addImageToPending(e.target.files[i]);
    e.target.value = '';
  }
});

// Paste handler on the whole document (when in chat)
document.addEventListener('paste', function(e) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  var items = (e.clipboardData || e.originalEvent && e.originalEvent.clipboardData || {}).items;
  if (!items) return;
  for (var i = 0; i < items.length; i++) {
    if (items[i].kind === 'file' && items[i].type.startsWith('image/')) {
      var file = items[i].getAsFile();
      if (file) { addImageToPending(file); e.preventDefault(); }
    }
  }
});

// Drag-and-drop on messages area
document.addEventListener('dragover', function(e) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  var el = document.getElementById('messages');
  var overlay = document.getElementById('dropOverlay');
  if (el && el.contains(e.target) || (overlay && overlay.contains(e.target))) {
    e.preventDefault();
    if (overlay) overlay.classList.add('visible');
  }
});
document.addEventListener('dragleave', function(e) {
  var overlay = document.getElementById('dropOverlay');
  if (overlay && !document.getElementById('messages').contains(e.relatedTarget)) {
    overlay.classList.remove('visible');
  }
});
document.addEventListener('drop', function(e) {
  var overlay = document.getElementById('dropOverlay');
  if (overlay) overlay.classList.remove('visible');
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  var el = document.getElementById('messages');
  if (!el) return;
  e.preventDefault();
  var files = e.dataTransfer ? e.dataTransfer.files : [];
  for (var i = 0; i < files.length; i++) addImageToPending(files[i]);
});

// Hook send button to also send pending images
document.addEventListener('click', function(e) {
  if (e.target && e.target.id === 'sendBtn' && pendingImages.length > 0) {
    sendPendingImages();
  }
});

var tabs = [];
var activeTabId = 'chat';
var tabIdCounter = 0;

function createTabId() { return 'tab-' + (++tabIdCounter); }

function findTabByType(type) {
  for (var i = 0; i < tabs.length; i++) {
    if (tabs[i].type === type) return tabs[i];
  }
  return null;
}

function renderTabBar() {
  var bar = document.getElementById('tabItems');
  bar.innerHTML = '';
  tabs.forEach(function(tab) {
    var item = document.createElement('div');
    item.className = 'tab-item' + (tab.id === activeTabId ? ' active' : '');
    item.setAttribute('data-testid', 'tab-' + tab.id);

    var icon = document.createElement('span');
    icon.className = 'tab-icon';
    if (tab.type === 'chat') icon.textContent = '💬';
    else if (tab.type === 'games') icon.textContent = '🎮';
    else if (tab.type === 'browser') icon.textContent = '🌐';
    else if (tab.type === 'balance') icon.textContent = '💰';
    else icon.textContent = '+';
    item.appendChild(icon);

    var label = document.createElement('span');
    label.textContent = tab.label;
    item.appendChild(label);

    var closeBtn = document.createElement('button');
    closeBtn.className = 'tab-close';
    closeBtn.textContent = '\u00D7';
    closeBtn.setAttribute('data-testid', 'button-close-tab-' + tab.id);
    closeBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      closeTab(tab.id);
    });
    item.appendChild(closeBtn);

    item.addEventListener('click', function() { switchTab(tab.id); });
    bar.appendChild(item);
  });
}

function switchTab(id) {
  activeTabId = id;
  var contents = document.getElementById('tabContents').children;
  for (var i = 0; i < contents.length; i++) {
    contents[i].classList.remove('active');
  }
  var el = document.getElementById('tabContent-' + id);
  if (el) el.classList.add('active');
  renderTabBar();
}

function closeTab(id) {
  var idx = -1;
  for (var i = 0; i < tabs.length; i++) {
    if (tabs[i].id === id) { idx = i; break; }
  }
  if (idx === -1) return;
  tabs.splice(idx, 1);
  var el = document.getElementById('tabContent-' + id);
  if (el) el.remove();
  if (tabs.length === 0) {
    openNewTab();
    return;
  }
  if (activeTabId === id) {
    var newIdx = Math.min(idx, tabs.length - 1);
    switchTab(tabs[newIdx].id);
  } else {
    renderTabBar();
  }
}

var allNewTabItems = [
  { id: 'chat', type: 'chat', name: 'Chat', desc: 'Group chat and direct messages', badge: '' },
  { id: 'games', type: 'games', name: 'Games', desc: 'Browse and play mini-games', badge: '' },
  { id: 'embedded', type: 'embedded', name: 'Embedded Games', desc: '200+ popular unblocked games playable in-browser', badge: 'NEW' },
  { id: 'balance', type: 'balance', name: 'Balance', desc: 'Your wallet, shop, savings, gambling & idle game', badge: 'NEW' },
];

function openBrowserTab(url) {
  var existing = findTabByType('browser');
  if (existing) {
    switchTab(existing.id);
    var inp = document.getElementById('browser-urlinput-' + existing.id);
    var go = document.getElementById('browser-go-' + existing.id);
    if (inp) { inp.value = url; if (go) go.click(); }
    return;
  }
  var id = createTabId();
  tabs.push({ id: id, type: 'browser', label: 'Browser' });
  var content = document.createElement('div');
  content.className = 'tab-content';
  content.id = 'tabContent-' + id;
  document.getElementById('tabContents').appendChild(content);
  renderTabBar();
  switchTab(id);
  convertTabToBrowser(id);
  setTimeout(function() {
    var inp = document.getElementById('browser-urlinput-' + id);
    var go = document.getElementById('browser-go-' + id);
    if (inp) { inp.value = url; if (go) go.click(); }
  }, 150);
}

function openNewTab() {
  var existing = findTabByType('newtab');
  if (existing) { switchTab(existing.id); return; }
  var id = createTabId();
  tabs.push({ id: id, type: 'newtab', label: 'New Tab' });

  var content = document.createElement('div');
  content.className = 'tab-content';
  content.id = 'tabContent-' + id;

  var page = document.createElement('div');
  page.className = 'newtab-page';

  var searchDiv = document.createElement('div');
  searchDiv.className = 'newtab-search';
  var searchInput = document.createElement('input');
  searchInput.type = 'text';
  searchInput.placeholder = 'Search...';
  searchInput.setAttribute('data-testid', 'input-newtab-search');
  searchDiv.appendChild(searchInput);
  page.appendChild(searchDiv);

  var listDiv = document.createElement('div');
  listDiv.className = 'newtab-list';
  page.appendChild(listDiv);

  function renderList(filter) {
    listDiv.innerHTML = '';
    var q = (filter || '').toLowerCase();
    var found = false;
    allNewTabItems.forEach(function(item) {
      if (q && item.name.toLowerCase().indexOf(q) === -1 && item.desc.toLowerCase().indexOf(q) === -1) return;
      found = true;
      var row = document.createElement('div');
      row.className = 'newtab-item';
      row.setAttribute('data-testid', 'newtab-option-' + item.id);
      var info = document.createElement('div');
      info.className = 'newtab-item-info';
      var nameEl = document.createElement('div');
      nameEl.className = 'newtab-item-name';
      nameEl.textContent = item.name;
      info.appendChild(nameEl);
      var descEl = document.createElement('div');
      descEl.className = 'newtab-item-desc';
      descEl.textContent = item.desc;
      info.appendChild(descEl);
      row.appendChild(info);
      if (item.badge) {
        var badge = document.createElement('span');
        badge.className = 'newtab-item-badge';
        badge.textContent = item.badge;
        row.appendChild(badge);
      }
      row.addEventListener('click', function() {
        if (item.type === 'chat') {
          var chatTab = findTabByType('chat');
          if (chatTab) { closeTab(id); switchTab(chatTab.id); }
          else { convertTabToChat(id); }
        } else if (item.type === 'games') {
          var gamesTab = findTabByType('games');
          if (gamesTab) { closeTab(id); switchTab(gamesTab.id); }
          else { convertTabToGames(id); }
        } else if (item.type === 'embedded') {
          convertTabToEmbedded(id);
        } else if (item.type === 'balance') {
          var bTab = findTabByType('balance');
          if (bTab) { closeTab(id); switchTab(bTab.id); }
          else { convertTabToBalance(id); }
        }
      });
      listDiv.appendChild(row);
    });
    if (!found) {
      var empty = document.createElement('div');
      empty.className = 'newtab-empty';
      empty.textContent = 'No results found';
      listDiv.appendChild(empty);
    }
  }

  searchInput.addEventListener('input', function() { renderList(this.value); });
  searchInput.addEventListener('keydown', function(e) { e.stopPropagation(); });
  renderList('');

  content.appendChild(page);
  document.getElementById('tabContents').appendChild(content);
  switchTab(id);
}

function convertTabToChat(tabId) {
  for (var i = 0; i < tabs.length; i++) {
    if (tabs[i].id === tabId) {
      tabs[i].type = 'chat';
      tabs[i].label = 'Chat';
      break;
    }
  }
  var el = document.getElementById('tabContent-' + tabId);
  el.innerHTML = '';

  var chatArea = document.createElement('div');
  chatArea.className = 'chat-area';

  var channelHeader = document.createElement('div');
  channelHeader.className = 'channel-header';
  channelHeader.id = 'channelHeaderBar';
  channelHeader.innerHTML = '<span class="channel-icon">#</span> <span id="channelName" data-testid="text-channel-name">General</span>';
  chatArea.appendChild(channelHeader);

  var messagesDiv = document.createElement('div');
  messagesDiv.id = 'messages';
  messagesDiv.setAttribute('data-testid', 'list-messages');
  chatArea.appendChild(messagesDiv);

  var inputBar = document.createElement('div');
  inputBar.className = 'input-bar';
  inputBar.id = 'inputBar';

  var imgPreviewBar = document.createElement('div');
  imgPreviewBar.className = 'image-preview-bar';
  imgPreviewBar.id = 'imagePreviewBar';
  imgPreviewBar.style.display = 'none';
  inputBar.appendChild(imgPreviewBar);

  var inputRow = document.createElement('div');
  inputRow.className = 'input-bar-row';

  var nameInput = document.createElement('input');
  nameInput.type = 'text';
  nameInput.id = 'nameInput';
  nameInput.setAttribute('data-testid', 'input-admin-name');
  nameInput.placeholder = 'Your name';
  nameInput.value = 'Admin';
  nameInput.style.cssText = 'display:none;width:140px;flex:unset;';
  if (isAdmin) nameInput.style.display = 'block';
  inputRow.appendChild(nameInput);

  var attachBtn = document.createElement('button');
  attachBtn.className = 'attach-btn';
  attachBtn.id = 'attachBtn';
  attachBtn.setAttribute('data-testid', 'button-attach');
  attachBtn.type = 'button';
  attachBtn.title = 'Attach image';
  attachBtn.textContent = '\U0001F4CE';
  inputRow.appendChild(attachBtn);

  var fileInput = document.createElement('input');
  fileInput.type = 'file';
  fileInput.id = 'fileInput';
  fileInput.accept = 'image/*';
  fileInput.multiple = true;
  fileInput.style.display = 'none';
  inputRow.appendChild(fileInput);

  var msgInput = document.createElement('input');
  msgInput.type = 'text';
  msgInput.id = 'msgInput';
  msgInput.setAttribute('data-testid', 'input-message');
  msgInput.placeholder = 'Type a message...';
  msgInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter') document.getElementById('sendBtn').click();
  });
  var lastTypingSent = 0;
  msgInput.addEventListener('input', function() {
    var now = Date.now();
    if (now - lastTypingSent > 2000 && ws && ws.readyState === WebSocket.OPEN) {
      lastTypingSent = now;
      ws.send(JSON.stringify({type: 'typing', channel: currentChannel}));
    }
  });
  inputRow.appendChild(msgInput);

  var emojiContainer = document.createElement('div');
  emojiContainer.className = 'emoji-picker-container';
  var emojiBtn = document.createElement('button');
  emojiBtn.className = 'emoji-picker-btn';
  emojiBtn.id = 'emojiBtn';
  emojiBtn.setAttribute('data-testid', 'button-emoji');
  emojiBtn.type = 'button';
  emojiBtn.title = 'Emoji picker';
  emojiBtn.textContent = '\U0001F600';
  var emojiPanel = document.createElement('div');
  emojiPanel.className = 'emoji-panel';
  emojiPanel.id = 'emojiPanel';
  var emojiSearchInput = document.createElement('input');
  emojiSearchInput.type = 'text';
  emojiSearchInput.className = 'emoji-search';
  emojiSearchInput.id = 'emojiSearch';
  emojiSearchInput.setAttribute('data-testid', 'input-emoji-search');
  emojiSearchInput.placeholder = 'Search emojis...';
  emojiPanel.appendChild(emojiSearchInput);
  var catBar = document.createElement('div');
  catBar.className = 'emoji-panel-header';
  catBar.id = 'emojiCatBar';
  emojiPanel.appendChild(catBar);
  var emojiGridEl = document.createElement('div');
  emojiGridEl.className = 'emoji-grid';
  emojiGridEl.id = 'emojiGrid';
  emojiGridEl.setAttribute('data-testid', 'grid-emoji');
  emojiPanel.appendChild(emojiGridEl);
  emojiContainer.appendChild(emojiBtn);
  emojiContainer.appendChild(emojiPanel);
  inputRow.appendChild(emojiContainer);

  var sendBtn = document.createElement('button');
  sendBtn.id = 'sendBtn';
  sendBtn.setAttribute('data-testid', 'button-send');
  sendBtn.textContent = 'Send';
  sendBtn.addEventListener('click', function() {
    if (pendingImages.length > 0) sendPendingImages();
    var input = document.getElementById('msgInput');
    var text = input ? input.value.trim() : '';
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    if (currentChannel === 'general') {
      if (isAdmin) {
        var name = (document.getElementById('nameInput') || {value:'Admin'}).value.trim() || 'Admin';
        ws.send(JSON.stringify({ type: 'chat', text: text, name: name }));
      } else {
        ws.send(JSON.stringify({ type: 'chat', text: text }));
      }
    } else if (currentChannel.startsWith('dm:')) {
      var target = currentChannel.substring(3);
      if (isAdmin) {
        var name = (document.getElementById('nameInput') || {value:'Admin'}).value.trim() || 'Admin';
        ws.send(JSON.stringify({ type: 'dm_message', target: target, text: text, name: name }));
      } else {
        ws.send(JSON.stringify({ type: 'dm_message', target: target, text: text }));
      }
    } else if (currentChannel.startsWith('gc:')) {
      var gcId = currentChannel.substring(3);
      ws.send(JSON.stringify({ type: 'gc_message', gc_id: gcId, text: text }));
    }
    if (input) { input.value = ''; input.focus(); }
  });
  inputRow.appendChild(sendBtn);
  inputBar.appendChild(inputRow);
  var typingIndicator = document.createElement('div');
  typingIndicator.id = 'typingIndicator';
  typingIndicator.style.cssText = 'display:none;padding:2px 16px;font-size:12px;color:var(--text-muted);font-style:italic;';
  typingIndicator.setAttribute('data-testid', 'text-typing-indicator');
  chatArea.appendChild(typingIndicator);
  chatArea.appendChild(inputBar);
  el.appendChild(chatArea);

  bindEmojiPicker();
  renderMessages();
  switchChannel(currentChannel);
  renderTabBar();
}

function bindEmojiPicker() {
  var emojiBtn = document.getElementById('emojiBtn');
  var emojiPanel = document.getElementById('emojiPanel');
  var emojiSearch = document.getElementById('emojiSearch');
  if (!emojiBtn) return;
  emojiBtn.addEventListener('click', function(e) {
    e.stopPropagation();
    var isOpen = emojiPanel.classList.contains('open');
    if (isOpen) { emojiPanel.classList.remove('open'); }
    else { renderEmojiCatBar(); renderEmojiPicker(''); emojiPanel.classList.add('open'); emojiSearch.focus(); }
  });
  emojiSearch.addEventListener('input', function() { renderEmojiPicker(this.value.trim()); });
  emojiSearch.addEventListener('keydown', function(e) { e.stopPropagation(); });
}

function convertTabToGames(tabId) {
  for (var i = 0; i < tabs.length; i++) {
    if (tabs[i].id === tabId) {
      tabs[i].type = 'games';
      tabs[i].label = 'Games';
      break;
    }
  }
  var el = document.getElementById('tabContent-' + tabId);
  el.innerHTML = '';
  buildGamesHub(el);
  renderTabBar();
}

var embeddedGamesList = [
  // === MULTIPLAYER .io (always work in iframes) ===
  {name:'Krunker.io',url:'https://krunker.io',cat:'multiplayer',emoji:'🔫'},
  {name:'Skribbl.io',url:'https://skribbl.io',cat:'multiplayer',emoji:'🎨'},
  {name:'Slither.io',url:'https://slither.io',cat:'multiplayer',emoji:'🐍'},
  {name:'Gartic.io',url:'https://gartic.io',cat:'multiplayer',emoji:'🖌️'},
  {name:'1v1.LOL',url:'https://1v1.lol',cat:'multiplayer',emoji:'🏗️'},
  {name:'Shell Shockers',url:'https://shellshock.io',cat:'multiplayer',emoji:'🥚'},
  {name:'Zombs Royale',url:'https://zombsroyale.io',cat:'multiplayer',emoji:'💀'},
  {name:'Warbrokers.io',url:'https://warbrokers.io',cat:'multiplayer',emoji:'💂'},
  {name:'Diep.io',url:'https://diep.io',cat:'multiplayer',emoji:'💣'},
  {name:'MooMoo.io',url:'https://moomoo.io',cat:'multiplayer',emoji:'🐄'},
  {name:'Deeeep.io',url:'https://deeeep.io',cat:'multiplayer',emoji:'🐠'},
  {name:'Stabfish.io',url:'https://stabfish.io',cat:'multiplayer',emoji:'🐟'},
  {name:'Narrow One',url:'https://narrow.one',cat:'multiplayer',emoji:'🏹'},
  {name:'Smash Karts',url:'https://smashkarts.io',cat:'multiplayer',emoji:'🚗'},
  {name:'Venge.io',url:'https://venge.io',cat:'multiplayer',emoji:'🔫'},
  {name:'Ev.io',url:'https://ev.io',cat:'multiplayer',emoji:'👾'},
  {name:'Sketchful.io',url:'https://sketchful.io',cat:'multiplayer',emoji:'✏️'},
  {name:'Pokemon Showdown',url:'https://www.crazygames.com/embed/pokemon-showdown',cat:'strategy',emoji:'⚡'},
  {name:'Agar.io',url:'https://agar.io',cat:'multiplayer',emoji:'🔵'},
  {name:'Paper.io',url:'https://paper-io.com',cat:'multiplayer',emoji:'📄'},
  {name:'Splix.io',url:'https://splix.io',cat:'multiplayer',emoji:'🟩'},
  {name:'Lordz.io',url:'https://www.lordz.io',cat:'multiplayer',emoji:'⚔️'},
  {name:'Wings.io',url:'https://wings.io',cat:'multiplayer',emoji:'✈️'},
  {name:'Superhex.io',url:'https://superhex.io',cat:'multiplayer',emoji:'🔷'},
  {name:'Bruh.io',url:'https://bruh.io',cat:'multiplayer',emoji:'😐'},
  // === TYPING ===
  {name:'Monkeytype',url:'https://monkeytype.com',cat:'action',emoji:'⌨️'},
  {name:'TypeRacer',url:'https://play.typeracer.com',cat:'action',emoji:'⌨️'},
  {name:'10FastFingers',url:'https://10fastfingers.com',cat:'action',emoji:'⌨️'},
  {name:'Keybr',url:'https://www.keybr.com',cat:'action',emoji:'⌨️'},
  // === PUZZLE (GitHub Pages / indie - no X-Frame-Options) ===
  {name:'2048',url:'https://gabrielecirulli.github.io/2048/',cat:'puzzle',emoji:'🔢'},
  {name:'Jstris (Tetris)',url:'https://jstris.jezevec10.com',cat:'puzzle',emoji:'🧩'},
  {name:'Infinite Craft',url:'https://neal.fun/infinite-craft/',cat:'puzzle',emoji:'✨'},
  {name:'Password Game',url:'https://neal.fun/password-game/',cat:'puzzle',emoji:'🔐'},
  {name:'Wordle',url:'https://wordplay.com',cat:'puzzle',emoji:'📝'},
  {name:'Minesweeper Online',url:'https://minesweeper.online',cat:'puzzle',emoji:'💣'},
  {name:'Sudoku',url:'https://sudoku.com',cat:'puzzle',emoji:'🔢'},
  {name:'Connections',url:'https://connections.swellgarfo.com',cat:'puzzle',emoji:'🔗'},
  {name:'Tictactoe',url:'https://playtictactoe.org',cat:'puzzle',emoji:'❌'},
  {name:'Crossword',url:'https://www.xwords-game.com',cat:'puzzle',emoji:'📰'},
  // === IDLE / CLICKER ===
  {name:'Cookie Clicker',url:'https://orteil.dashnet.org/cookieclicker/',cat:'idle',emoji:'🍪'},
  {name:'Universal Paperclips',url:'https://www.decisionproblem.com/paperclips/index2.html',cat:'idle',emoji:'📎'},
  {name:'Candy Box 2',url:'https://candybox2.github.io',cat:'idle',emoji:'🍬'},
  {name:'A Dark Room',url:'https://adarkroom.doublespeakgames.com',cat:'idle',emoji:'🕯️'},
  // === ACTION / ADVENTURE (direct host, likely no X-Frame-Options) ===
  {name:'Minecraft Classic',url:'https://classic.minecraft.net',cat:'adventure',emoji:'⛏️'},
  {name:'Townscaper',url:'https://oskarstalberg.com/Townscaper/',cat:'adventure',emoji:'🏘️'},
  {name:'Chrome Dino',url:'https://chromedino.com',cat:'action',emoji:'🦕'},
  {name:'Line Rider',url:'https://www.linerider.com',cat:'action',emoji:'🛷'},
  {name:'Dungeon Crawler',url:'https://browserquest.mozilla.org',cat:'adventure',emoji:'⚔️'},
  // === NEAL.FUN ===
  {name:'Neal: Traffic',url:'https://neal.fun/traffic/',cat:'puzzle',emoji:'🚗'},
  {name:'Neal: Spend Gates Money',url:'https://neal.fun/spend/',cat:'idle',emoji:'💰'},
  {name:'Neal: Absurd Trolley',url:'https://neal.fun/absurd-trolley-problems/',cat:'puzzle',emoji:'🚃'},
  {name:'Neal: Universe Size',url:'https://neal.fun/universe/',cat:'adventure',emoji:'🌌'},
  {name:'Neal: Life Stats',url:'https://neal.fun/life-stats/',cat:'puzzle',emoji:'📊'},
  // === STRATEGY ===
  {name:'Lichess (Chess)',url:'https://lichess.org',cat:'strategy',emoji:'♟️'},
  {name:'GeoGuessr Free',url:'https://www.geoguessr.com/free',cat:'adventure',emoji:'🌍'},
  {name:'Sporcle',url:'https://www.sporcle.com',cat:'puzzle',emoji:'🧠'},
  // === FUN / MISC ===
  {name:'HackerTyper',url:'https://hackertyper.net',cat:'action',emoji:'💻'},
  {name:'Pointer Pointer',url:'https://pointerpointer.com',cat:'puzzle',emoji:'👆'},
  {name:'Find the Invisible Cow',url:'https://findtheinvisiblecow.com',cat:'action',emoji:'🐄'},
  {name:'Patatap',url:'https://patatap.com',cat:'action',emoji:'🎵'},
  {name:'Silk',url:'https://weavesilk.com',cat:'action',emoji:'🌸'},
  {name:'Drawasaurus',url:'https://www.drawasaurus.org',cat:'multiplayer',emoji:'🦕'},
  {name:'skribbl.io (alt)',url:'https://sketchful.io',cat:'multiplayer',emoji:'🎨'},
  // === CLASSIC GAMES (old sites, likely embeddable) ===
  {name:'Slope',url:'https://www.crazygames.com/embed/slope',cat:'action',emoji:'🎿'},
  {name:'Run 3',url:'https://www.crazygames.com/embed/run-3',cat:'action',emoji:'🏃'},
  {name:'Retro Bowl (Classic)',url:'https://www.crazygames.com/embed/retro-bowl-classic',cat:'sports',emoji:'🏈'},
  {name:'Smash Karts',url:'https://www.crazygames.com/embed/smash-karts',cat:'racing',emoji:'🚗'},
  // === MUSIC / CREATIVE ===
  {name:'Chrome Music Lab',url:'https://musiclab.chromeexperiments.com',cat:'action',emoji:'🎹'},
  {name:'AutoDraw',url:'https://www.autodraw.com',cat:'action',emoji:'✏️'},
  {name:'Make Art',url:'https://make.art',cat:'action',emoji:'🎨'},
  // === MORE MULTIPLAYER ===
  {name:'Hordes.io',url:'https://hordes.io',cat:'multiplayer',emoji:'⚔️'},
  {name:'Starblast.io',url:'https://starblast.io',cat:'multiplayer',emoji:'🚀'},
  {name:'Territorial.io',url:'https://territorial.io',cat:'strategy',emoji:'🗺️'},
  {name:'Generals.io',url:'https://generals.io',cat:'strategy',emoji:'🗺️'},
  // === IDLE ===
  {name:'Universal Paperclips',url:'https://www.decisionproblem.com/paperclips/index2.html',cat:'idle',emoji:'📎'},
  {name:'Candy Box 2',url:'https://candybox2.github.io',cat:'idle',emoji:'🍬'},
  {name:'A Dark Room',url:'https://adarkroom.doublespeakgames.com',cat:'idle',emoji:'🕯️'},
  // === ADDITIONAL NEAL.FUN ===
  {name:'Neal: Draw Logos',url:'https://neal.fun/logo-quiz/',cat:'puzzle',emoji:'🎨'},
  {name:'Neal: Artifacts',url:'https://neal.fun/internet-artifacts/',cat:'adventure',emoji:'🌐'},
  // === MORE MISC ===
  {name:'Chrome Dino',url:'https://chromedino.com',cat:'action',emoji:'🦕'},
  {name:'Townscaper',url:'https://oskarstalberg.com/Townscaper/',cat:'adventure',emoji:'🏘️'},
  {name:'Minecraft Classic',url:'https://classic.minecraft.net',cat:'adventure',emoji:'⛏️'},
];
// (old list removed)
var _REMOVE_OLD_LIST_ = (function() { var x = [
  {name:'OvO',url:'https://www.crazygames.com/embed/ovo',cat:'action',emoji:'💫'},
  {name:'Stickman Hook',url:'https://www.crazygames.com/embed/stickman-hook',cat:'action',emoji:'🪝'},
  {name:'Smash Karts',url:'https://www.crazygames.com/embed/smash-karts',cat:'multiplayer',emoji:'🚗'},
  {name:'Drift Boss',url:'https://www.crazygames.com/embed/drift-boss',cat:'racing',emoji:'🚗'},
  {name:'Paper.io 2',url:'https://www.crazygames.com/embed/paper-io-2',cat:'multiplayer',emoji:'📄'},
  {name:'Getaway Shootout',url:'https://www.crazygames.com/embed/getaway-shootout',cat:'multiplayer',emoji:'🔫'},
  {name:'Monkey Mart',url:'https://www.crazygames.com/embed/monkey-mart',cat:'idle',emoji:'🐒'},
  {name:'Eggy Car',url:'https://www.crazygames.com/embed/eggy-car',cat:'action',emoji:'🥚'},
  {name:'Idle Breakout',url:'https://www.crazygames.com/embed/idle-breakout',cat:'idle',emoji:'🎯'},
  {name:'Cookie Clicker 3',url:'https://www.crazygames.com/embed/cookie-clicker-3',cat:'idle',emoji:'🍪'},
  {name:'Blumgi Castle',url:'https://www.crazygames.com/embed/blumgi-castle',cat:'puzzle',emoji:'🏰'},
  {name:'Basket Random',url:'https://www.crazygames.com/embed/basket-random',cat:'sports',emoji:'🏀'},
  {name:'Soccer Random',url:'https://www.crazygames.com/embed/soccer-random',cat:'sports',emoji:'⚽'},
  {name:'Moto X3M',url:'https://www.crazygames.com/embed/moto-x3m',cat:'racing',emoji:'🏍️'},
  {name:'Moto X3M Pool Party',url:'https://www.crazygames.com/embed/moto-x3m-pool-party',cat:'racing',emoji:'🏍️'},
  {name:'Moto X3M Winter',url:'https://www.crazygames.com/embed/moto-x3m-winter',cat:'racing',emoji:'🏍️'},
  {name:'Moto X3M Spooky Land',url:'https://www.crazygames.com/embed/moto-x3m-spooky-land',cat:'racing',emoji:'🏍️'},
  {name:'Bob the Robber',url:'https://www.crazygames.com/embed/bob-the-robber',cat:'adventure',emoji:'🕵️'},
  {name:'Bob the Robber 2',url:'https://www.crazygames.com/embed/bob-the-robber-2',cat:'adventure',emoji:'🕵️'},
  {name:'Bob the Robber 4',url:'https://www.crazygames.com/embed/bob-the-robber-4',cat:'adventure',emoji:'🕵️'},
  {name:'Fireboy & Watergirl',url:'https://www.crazygames.com/embed/fireboy-and-watergirl',cat:'puzzle',emoji:'🔥'},
  {name:'Fireboy & Watergirl 2',url:'https://www.crazygames.com/embed/fireboy-and-watergirl-2-light-temple',cat:'puzzle',emoji:'🔥'},
  {name:'Fireboy & Watergirl 3',url:'https://www.crazygames.com/embed/fireboy-and-watergirl-3',cat:'puzzle',emoji:'🔥'},
  {name:'Fireboy & Watergirl 4',url:'https://www.crazygames.com/embed/fireboy-and-watergirl-4-crystal-temple',cat:'puzzle',emoji:'🔥'},
  {name:'Fireboy & Watergirl 5',url:'https://www.crazygames.com/embed/fireboy-and-watergirl-5-elements',cat:'puzzle',emoji:'🔥'},
  {name:'Cut the Rope',url:'https://www.crazygames.com/embed/cut-the-rope',cat:'puzzle',emoji:'✂️'},
  {name:'Cut the Rope 2',url:'https://www.crazygames.com/embed/cut-the-rope-2',cat:'puzzle',emoji:'✂️'},
  {name:'2048',url:'https://www.crazygames.com/embed/2048',cat:'puzzle',emoji:'🔢'},
  {name:'Wordle',url:'https://www.nytimes.com/games/wordle/index.html',cat:'puzzle',emoji:'📝'},
  {name:'Wordscapes',url:'https://www.crazygames.com/embed/wordscapes',cat:'puzzle',emoji:'💬'},
  {name:'TypeRacer',url:'https://play.typeracer.com',cat:'multiplayer',emoji:'⌨️'},
  {name:'Monkeytype',url:'https://monkeytype.com',cat:'action',emoji:'⌨️'},
  {name:'Shell Shockers',url:'https://shellshock.io',cat:'multiplayer',emoji:'🥚'},
  {name:'Krunker.io',url:'https://krunker.io',cat:'multiplayer',emoji:'🔫'},
  {name:'1v1.LOL',url:'https://1v1.lol',cat:'multiplayer',emoji:'🏗️'},
  {name:'Agar.io',url:'https://agar.io',cat:'multiplayer',emoji:'🔵'},
  {name:'Slither.io',url:'https://slither.io',cat:'multiplayer',emoji:'🐍'},
  {name:'Diep.io',url:'https://diep.io',cat:'multiplayer',emoji:'💣'},
  {name:'Surviv.io',url:'https://www.crazygames.com/embed/survivio',cat:'multiplayer',emoji:'🎯'},
  {name:'Hole.io',url:'https://www.crazygames.com/embed/holeio',cat:'multiplayer',emoji:'🕳️'},
  {name:'Tanki Online',url:'https://www.crazygames.com/embed/tanki-online',cat:'multiplayer',emoji:'🔫'},
  {name:'Warbrokers.io',url:'https://warbrokers.io',cat:'multiplayer',emoji:'💂'},
  {name:'Venge.io',url:'https://www.crazygames.com/embed/vengeio',cat:'multiplayer',emoji:'🔫'},
  {name:'Defly.io',url:'https://www.crazygames.com/embed/defly-io',cat:'multiplayer',emoji:'✈️'},
  {name:'Stabfish.io',url:'https://www.crazygames.com/embed/stabfish-io',cat:'multiplayer',emoji:'🐟'},
  {name:'Battleship Online',url:'https://www.crazygames.com/embed/battleship-online',cat:'multiplayer',emoji:'⚓'},
  {name:'Chess',url:'https://www.crazygames.com/embed/chess',cat:'strategy',emoji:'♟️'},
  {name:'Checkers',url:'https://www.crazygames.com/embed/checkers-classic',cat:'strategy',emoji:'⚫'},
  {name:'Mahjong Classic',url:'https://www.crazygames.com/embed/mahjong-classic',cat:'puzzle',emoji:'🀄'},
  {name:'Mahjong Dark Dimensions',url:'https://www.crazygames.com/embed/mahjong-dark-dimensions',cat:'puzzle',emoji:'🀄'},
  {name:'Solitaire Story',url:'https://www.crazygames.com/embed/solitaire-story-tripeaks',cat:'puzzle',emoji:'🃏'},
  {name:'Spider Solitaire',url:'https://www.crazygames.com/embed/spider-solitaire',cat:'puzzle',emoji:'🕷️'},
  {name:'FreeCell',url:'https://www.crazygames.com/embed/freecell',cat:'puzzle',emoji:'🃏'},
  {name:'Hearts',url:'https://www.crazygames.com/embed/hearts',cat:'puzzle',emoji:'❤️'},
  {name:'Bubble Shooter',url:'https://www.crazygames.com/embed/bubble-shooter',cat:'puzzle',emoji:'🫧'},
  {name:'Bubble Shooter Pro',url:'https://www.crazygames.com/embed/bubble-shooter-pro',cat:'puzzle',emoji:'🫧'},
  {name:'Jewel Blast',url:'https://www.crazygames.com/embed/jewel-blast',cat:'puzzle',emoji:'💎'},
  {name:'Jewels Blitz 4',url:'https://www.crazygames.com/embed/jewels-blitz-4',cat:'puzzle',emoji:'💎'},
  {name:'Jelly Truck',url:'https://www.crazygames.com/embed/jelly-truck',cat:'action',emoji:'🟩'},
  {name:'Flip the Gun',url:'https://www.crazygames.com/embed/flip-the-gun',cat:'action',emoji:'🔫'},
  {name:'Apple Shooter',url:'https://www.crazygames.com/embed/apple-shooter',cat:'action',emoji:'🍎'},
  {name:'Earn to Die',url:'https://www.crazygames.com/embed/earn-to-die',cat:'action',emoji:'🧟'},
  {name:'Earn to Die 2',url:'https://www.crazygames.com/embed/earn-to-die-2',cat:'action',emoji:'🧟'},
  {name:'Happy Wheels',url:'https://www.crazygames.com/embed/happy-wheels',cat:'action',emoji:'🚲'},
  {name:'Elastic Man',url:'https://www.crazygames.com/embed/elastic-man',cat:'action',emoji:'😮'},
  {name:'Funny Shooter 2',url:'https://www.crazygames.com/embed/funny-shooter-2',cat:'action',emoji:'🔫'},
  {name:'Pixel Shooter',url:'https://www.crazygames.com/embed/pixel-shooter',cat:'action',emoji:'👾'},
  {name:'Head Soccer',url:'https://www.crazygames.com/embed/head-soccer',cat:'sports',emoji:'⚽'},
  {name:'Head Football',url:'https://www.crazygames.com/embed/head-football',cat:'sports',emoji:'🏈'},
  {name:'Basketball Stars',url:'https://www.crazygames.com/embed/basketball-stars',cat:'sports',emoji:'🏀'},
  {name:'Penalty Kick Online',url:'https://www.crazygames.com/embed/penalty-kick-online',cat:'sports',emoji:'⚽'},
  {name:'Football Legends',url:'https://www.crazygames.com/embed/football-legends-2021',cat:'sports',emoji:'⚽'},
  {name:'Baseball Pro',url:'https://www.crazygames.com/embed/baseball-pro',cat:'sports',emoji:'⚾'},
  {name:'Tennis Masters',url:'https://www.crazygames.com/embed/tennis-masters',cat:'sports',emoji:'🎾'},
  {name:'Table Tennis World Tour',url:'https://www.crazygames.com/embed/table-tennis-world-tour',cat:'sports',emoji:'🏓'},
  {name:'Bowling King',url:'https://www.crazygames.com/embed/bowling-king',cat:'sports',emoji:'🎳'},
  {name:'Mini Golf Club',url:'https://www.crazygames.com/embed/mini-golf-club',cat:'sports',emoji:'⛳'},
  {name:'Golf Orbit',url:'https://www.crazygames.com/embed/golf-orbit',cat:'sports',emoji:'⛳'},
  {name:'Bike Mania',url:'https://www.crazygames.com/embed/bike-mania',cat:'racing',emoji:'🚲'},
  {name:'Bike Mania 4',url:'https://www.crazygames.com/embed/bike-mania-4-microgravity',cat:'racing',emoji:'🚲'},
  {name:'Extreme Car Driving',url:'https://www.crazygames.com/embed/extreme-car-driving-simulator',cat:'racing',emoji:'🏎️'},
  {name:'Road Fury',url:'https://www.crazygames.com/embed/road-fury',cat:'racing',emoji:'🚗'},
  {name:'Rocket League SideSwipe',url:'https://www.crazygames.com/embed/rocket-soccer-derby',cat:'racing',emoji:'🚀'},
  {name:'Mini Royale Nations',url:'https://www.crazygames.com/embed/mini-royale-nations',cat:'multiplayer',emoji:'🎯'},
  {name:'Zombs Royale',url:'https://zombsroyale.io',cat:'multiplayer',emoji:'💀'},
  {name:'Friday Night Funkin',url:'https://www.crazygames.com/embed/friday-night-funkin',cat:'action',emoji:'🎵'},
  {name:'Friday Night Funkin Week 7',url:'https://www.crazygames.com/embed/friday-night-funkin-week-7',cat:'action',emoji:'🎵'},
  {name:'Among Us Online',url:'https://www.crazygames.com/embed/among-us-online-edition',cat:'multiplayer',emoji:'👨‍🚀'},
  {name:'Squid Game Online',url:'https://www.crazygames.com/embed/squid-game',cat:'action',emoji:'🟥'},
  {name:'Subway Surfers',url:'https://www.crazygames.com/embed/subway-surfers',cat:'action',emoji:'🏃'},
  {name:'Temple Run 2',url:'https://www.crazygames.com/embed/temple-run-2',cat:'action',emoji:'🏃'},
  {name:'Crossy Road',url:'https://www.crazygames.com/embed/crossy-road',cat:'action',emoji:'🐔'},
  {name:'Stacky Bird',url:'https://www.crazygames.com/embed/stacky-bird',cat:'action',emoji:'🐦'},
  {name:'Flappy Bird',url:'https://www.crazygames.com/embed/flappy-bird',cat:'action',emoji:'🐦'},
  {name:'Jetpack Joyride',url:'https://www.crazygames.com/embed/jetpack-joyride',cat:'action',emoji:'🚀'},
  {name:'Bloons TD 5',url:'https://www.crazygames.com/embed/bloons-tower-defense-5',cat:'strategy',emoji:'🎈'},
  {name:'Bloons TD 6',url:'https://www.crazygames.com/embed/bloons-tower-defense-6',cat:'strategy',emoji:'🎈'},
  {name:'Kingdom Rush',url:'https://www.crazygames.com/embed/kingdom-rush',cat:'strategy',emoji:'🏰'},
  {name:'Kingdom Rush Frontiers',url:'https://www.crazygames.com/embed/kingdom-rush-frontiers',cat:'strategy',emoji:'🏰'},
  {name:'Kingdom Rush Origins',url:'https://www.crazygames.com/embed/kingdom-rush-origins',cat:'strategy',emoji:'🏰'},
  {name:'Plants vs Zombies',url:'https://www.crazygames.com/embed/plants-vs-zombies',cat:'strategy',emoji:'🌻'},
  {name:'Clash of Clans Online',url:'https://www.crazygames.com/embed/clash-of-clans',cat:'strategy',emoji:'⚔️'},
  {name:'Stick War Legacy',url:'https://www.crazygames.com/embed/stick-war-legacy',cat:'strategy',emoji:'🪖'},
  {name:'Age of War',url:'https://www.crazygames.com/embed/age-of-war',cat:'strategy',emoji:'⚔️'},
  {name:'Age of War 2',url:'https://www.crazygames.com/embed/age-of-war-2',cat:'strategy',emoji:'⚔️'},
  {name:'Diggy',url:'https://www.crazygames.com/embed/diggy',cat:'adventure',emoji:'⛏️'},
  {name:'Minesweeper',url:'https://www.crazygames.com/embed/minesweeper',cat:'puzzle',emoji:'💣'},
  {name:'Sudoku',url:'https://www.crazygames.com/embed/daily-sudoku',cat:'puzzle',emoji:'🔢'},
  {name:'Sudoku Classic',url:'https://www.crazygames.com/embed/sudoku-classic',cat:'puzzle',emoji:'🔢'},
  {name:'Crossword Puzzle',url:'https://www.crazygames.com/embed/crossword-puzzle',cat:'puzzle',emoji:'📰'},
  {name:'Word Hurdle',url:'https://www.crazygames.com/embed/word-hurdle',cat:'puzzle',emoji:'📝'},
  {name:'Letter Scramble',url:'https://www.crazygames.com/embed/letter-scramble',cat:'puzzle',emoji:'🔤'},
  {name:'Merge Fruits',url:'https://www.crazygames.com/embed/merge-fruits',cat:'puzzle',emoji:'🍉'},
  {name:'Merge Cannon',url:'https://www.crazygames.com/embed/merge-cannon',cat:'puzzle',emoji:'💣'},
  {name:'Cube Jump',url:'https://www.crazygames.com/embed/cube-jump',cat:'action',emoji:'📦'},
  {name:'Jump King',url:'https://www.crazygames.com/embed/only-up',cat:'action',emoji:'👑'},
  {name:'Only Up',url:'https://www.crazygames.com/embed/only-up-sketchbook',cat:'action',emoji:'⬆️'},
  {name:'Getting Over It',url:'https://www.crazygames.com/embed/getting-over-it',cat:'action',emoji:'⛏️'},
  {name:'Geometry Dash',url:'https://www.crazygames.com/embed/geometry-dash',cat:'action',emoji:'🔷'},
  {name:'Geometry Dash Subzero',url:'https://www.crazygames.com/embed/geometry-dash-subzero',cat:'action',emoji:'🔷'},
  {name:'Geometry Dash Meltdown',url:'https://www.crazygames.com/embed/geometry-dash-meltdown',cat:'action',emoji:'🔷'},
  {name:'Geometry Dash Breeze',url:'https://www.crazygames.com/embed/geometry-dash-breeze',cat:'action',emoji:'🔷'},
  {name:'Sonic Exe',url:'https://www.crazygames.com/embed/sonic-exe',cat:'action',emoji:'💨'},
  {name:'Sonic Classic',url:'https://www.crazygames.com/embed/sonic-classic',cat:'action',emoji:'💨'},
  {name:'Super Mario 64 Online',url:'https://www.crazygames.com/embed/super-mario-64',cat:'adventure',emoji:'🍄'},
  {name:'Super Smash Flash 2',url:'https://www.crazygames.com/embed/super-smash-flash-2',cat:'action',emoji:'👊'},
  {name:'Pokemon Showdown',url:'https://www.crazygames.com/embed/pokemon-showdown',cat:'strategy',emoji:'⚡'},
  {name:'Retro Bowl',url:'https://www.crazygames.com/embed/retro-bowl',cat:'sports',emoji:'🏈'},
  {name:'Retro Bowl College',url:'https://www.crazygames.com/embed/retro-bowl-college',cat:'sports',emoji:'🏈'},
  {name:'Burrito Bison',url:'https://www.crazygames.com/embed/burrito-bison',cat:'action',emoji:'🌯'},
  {name:'Learn to Fly 3',url:'https://www.crazygames.com/embed/learn-to-fly-3',cat:'action',emoji:'🐧'},
  {name:'Doodle Jump',url:'https://www.crazygames.com/embed/doodle-jump',cat:'action',emoji:'🌀'},
  {name:'Kugel',url:'https://www.crazygames.com/embed/kugel',cat:'puzzle',emoji:'🔵'},
  {name:'Color Road',url:'https://www.crazygames.com/embed/color-road',cat:'action',emoji:'🌈'},
  {name:'Color Switch',url:'https://www.crazygames.com/embed/color-switch',cat:'action',emoji:'🌈'},
  {name:'Sprinter',url:'https://www.crazygames.com/embed/sprinter',cat:'sports',emoji:'🏃'},
  {name:'Javelin Fighting',url:'https://www.crazygames.com/embed/javelin-fighting',cat:'action',emoji:'🏹'},
  {name:'Copter.io',url:'https://www.crazygames.com/embed/copter-io',cat:'multiplayer',emoji:'🚁'},
  {name:'Lordz.io',url:'https://www.crazygames.com/embed/lordz-io',cat:'strategy',emoji:'⚔️'},
  {name:'Zombie Mission',url:'https://www.crazygames.com/embed/zombie-mission',cat:'action',emoji:'🧟'},
  {name:'Zombie Mission 2',url:'https://www.crazygames.com/embed/zombie-mission-2',cat:'action',emoji:'🧟'},
  {name:'Zombie Mission 3',url:'https://www.crazygames.com/embed/zombie-mission-3',cat:'action',emoji:'🧟'},
  {name:'Zombie Mission 10',url:'https://www.crazygames.com/embed/zombie-mission-10',cat:'action',emoji:'🧟'},
  {name:'Dungeon Escape',url:'https://www.crazygames.com/embed/dungeon-escape',cat:'adventure',emoji:'⚔️'},
  {name:'Fortnite Online',url:'https://www.crazygames.com/embed/fortnite-online',cat:'multiplayer',emoji:'🏗️'},
  {name:'Narrow One',url:'https://www.crazygames.com/embed/narrow-one',cat:'multiplayer',emoji:'🏹'},
  {name:'Snowfall',url:'https://www.crazygames.com/embed/snowfall',cat:'action',emoji:'❄️'},
  {name:'Drive Mad',url:'https://www.crazygames.com/embed/drive-mad',cat:'racing',emoji:'🚗'},
  {name:'Car Rush',url:'https://www.crazygames.com/embed/car-rush',cat:'racing',emoji:'🚗'},
  {name:'Rally Point 6',url:'https://www.crazygames.com/embed/rally-point-6',cat:'racing',emoji:'🏎️'},
  {name:'Rocket Cars',url:'https://www.crazygames.com/embed/rocket-cars',cat:'racing',emoji:'🚀'},
  {name:'Burnin Rubber 5',url:'https://www.crazygames.com/embed/burnin-rubber-5-hd',cat:'racing',emoji:'🏁'},
  {name:'Burnin Rubber Crash n Burn',url:'https://www.crazygames.com/embed/burnin-rubber-crash-n-burn',cat:'racing',emoji:'🏁'},
  {name:'Street Racing 3D',url:'https://www.crazygames.com/embed/street-racing-3d',cat:'racing',emoji:'🏎️'},
  {name:'Crazy Cars',url:'https://www.crazygames.com/embed/crazy-cars',cat:'racing',emoji:'🚗'},
  {name:'Stunt Car Extreme',url:'https://www.crazygames.com/embed/stunt-car-extreme',cat:'racing',emoji:'🚗'},
  {name:'Trial Bike Epic Stunts',url:'https://www.crazygames.com/embed/trial-bike-epic-stunts',cat:'racing',emoji:'🏍️'},
  {name:'Rooftop Snipers',url:'https://www.crazygames.com/embed/rooftop-snipers',cat:'action',emoji:'🎯'},
  {name:'Rooftop Snipers 2',url:'https://www.crazygames.com/embed/rooftop-snipers-2',cat:'action',emoji:'🎯'},
  {name:'Penalty Shooters 2',url:'https://www.crazygames.com/embed/penalty-shooters-2',cat:'sports',emoji:'⚽'},
  {name:'Minigolf Adventures',url:'https://www.crazygames.com/embed/minigolf-adventures',cat:'sports',emoji:'⛳'},
  {name:'Billiards',url:'https://www.crazygames.com/embed/8-ball-billiards-classic',cat:'sports',emoji:'🎱'},
  {name:'8 Ball Pool',url:'https://www.crazygames.com/embed/8-ball-pool',cat:'sports',emoji:'🎱'},
  {name:'Smash the Code',url:'https://www.crazygames.com/embed/smash-the-code',cat:'puzzle',emoji:'💻'},
  {name:'World Craft',url:'https://www.crazygames.com/embed/worldcraft',cat:'adventure',emoji:'⛏️'},
  {name:'Minecraft Classic',url:'https://classic.minecraft.net',cat:'adventure',emoji:'⛏️'},
  {name:'Paper Minecraft',url:'https://www.crazygames.com/embed/paper-minecraft',cat:'adventure',emoji:'📄'},
  {name:'Roblox (open)',url:'https://www.crazygames.com/embed/roblox',cat:'multiplayer',emoji:'🟦'},
  {name:'Townscaper',url:'https://oskarstalberg.com/Townscaper/',cat:'adventure',emoji:'🏘️'},
  {name:'Little Alchemy 2',url:'https://www.crazygames.com/embed/little-alchemy-2',cat:'puzzle',emoji:'⚗️'},
  {name:'Dumb Ways to Die',url:'https://www.crazygames.com/embed/dumb-ways-to-die',cat:'action',emoji:'💀'},
  {name:'Dumb Ways to Die 2',url:'https://www.crazygames.com/embed/dumb-ways-to-die-2',cat:'action',emoji:'💀'},
  {name:'Cat Ninja',url:'https://www.crazygames.com/embed/cat-ninja',cat:'action',emoji:'🐱'},
  {name:'Plazma Burst 2',url:'https://www.crazygames.com/embed/plazma-burst-2',cat:'action',emoji:'🔫'},
  {name:'Sniper Assassin',url:'https://www.crazygames.com/embed/sniper-assassin',cat:'action',emoji:'🎯'},
  {name:'Box Tower',url:'https://www.crazygames.com/embed/box-tower',cat:'puzzle',emoji:'📦'},
  {name:'Trollface Quest',url:'https://www.crazygames.com/embed/trollface-quest',cat:'puzzle',emoji:'😈'},
  {name:'Trollface Quest Video Games',url:'https://www.crazygames.com/embed/trollface-quest-video-games',cat:'puzzle',emoji:'😈'},
  {name:'I Am Fish',url:'https://www.crazygames.com/embed/i-am-fish',cat:'adventure',emoji:'🐟'},
  {name:'Idle Factory Inc',url:'https://www.crazygames.com/embed/idle-factory-inc',cat:'idle',emoji:'🏭'},
  {name:'AdVenture Capitalist',url:'https://www.crazygames.com/embed/adventure-capitalist',cat:'idle',emoji:'💰'},
  {name:'Idle Miner',url:'https://www.crazygames.com/embed/idle-miner-clicker',cat:'idle',emoji:'⛏️'},
  {name:'Bitcoin Miner',url:'https://www.crazygames.com/embed/bitcoin-miner',cat:'idle',emoji:'₿'},
  {name:'Egg Farm Simulator',url:'https://www.crazygames.com/embed/egg-farm-simulator',cat:'idle',emoji:'🥚'},
  {name:'Spacebar Clicker',url:'https://www.crazygames.com/embed/spacebar-clicker',cat:'idle',emoji:'⌨️'},
  {name:'Number Clicker',url:'https://www.crazygames.com/embed/number-clicker',cat:'idle',emoji:'🔢'},
  {name:'Raft Wars',url:'https://www.crazygames.com/embed/raft-wars',cat:'action',emoji:'🚣'},
  {name:'Raft Wars 2',url:'https://www.crazygames.com/embed/raft-wars-2',cat:'action',emoji:'🚣'},
  {name:'Battleship',url:'https://www.crazygames.com/embed/battleship',cat:'strategy',emoji:'⚓'},
  {name:'Risk',url:'https://www.crazygames.com/embed/risk',cat:'strategy',emoji:'🗺️'},
  {name:'Ludo Club',url:'https://www.crazygames.com/embed/ludo-club',cat:'strategy',emoji:'🎲'},
  {name:'Uno Online',url:'https://www.crazygames.com/embed/uno-online',cat:'multiplayer',emoji:'🃏'},
  {name:'Checkers Legend',url:'https://www.crazygames.com/embed/checkers-legend',cat:'strategy',emoji:'⚫'},
  {name:'Backgammon',url:'https://www.crazygames.com/embed/backgammon',cat:'strategy',emoji:'🎲'},
  {name:'Reversi',url:'https://www.crazygames.com/embed/reversi',cat:'strategy',emoji:'⚫'},
  {name:'Gobang',url:'https://www.crazygames.com/embed/gobang',cat:'strategy',emoji:'⚫'},
  {name:'Tetris',url:'https://www.crazygames.com/embed/tetris',cat:'puzzle',emoji:'🧱'},
  {name:'Tetris Unblocked',url:'https://www.crazygames.com/embed/tetris-unblocked',cat:'puzzle',emoji:'🧱'},
  {name:'Tetris.io',url:'https://jstris.jezevec10.com',cat:'multiplayer',emoji:'🧱'},
  {name:'Klondike Solitaire',url:'https://www.crazygames.com/embed/solitaire-classic',cat:'puzzle',emoji:'🃏'},
  {name:'Blackjack',url:'https://www.crazygames.com/embed/blackjack-21',cat:'puzzle',emoji:'🃏'},
  {name:'Poker',url:'https://www.crazygames.com/embed/video-poker',cat:'puzzle',emoji:'🃏'},
  {name:'Jackpot Slots',url:'https://www.crazygames.com/embed/jackpot-slots',cat:'puzzle',emoji:'🎰'},
  {name:'Tanki X',url:'https://www.crazygames.com/embed/tanki-x',cat:'multiplayer',emoji:'💣'},
  {name:'Hordes.io',url:'https://hordes.io',cat:'multiplayer',emoji:'⚔️'},
  {name:'Starblast.io',url:'https://starblast.io',cat:'multiplayer',emoji:'🚀'},
  {name:'Evowars.io',url:'https://www.crazygames.com/embed/evowars-io',cat:'multiplayer',emoji:'⚔️'},
  {name:'Splix.io',url:'https://www.crazygames.com/embed/splixio',cat:'multiplayer',emoji:'📄'},
  {name:'Snake.io',url:'https://www.crazygames.com/embed/snake-io',cat:'multiplayer',emoji:'🐍'},
  {name:'Zapper.io',url:'https://www.crazygames.com/embed/zapper-io',cat:'multiplayer',emoji:'⚡'},
  {name:'Hexar.io',url:'https://www.crazygames.com/embed/hexar-io',cat:'multiplayer',emoji:'🔷'},
  {name:'Wings.io',url:'https://www.crazygames.com/embed/wings-io',cat:'multiplayer',emoji:'✈️'},
  {name:'Lordz2.io',url:'https://www.crazygames.com/embed/lordz2-io',cat:'strategy',emoji:'⚔️'},
  {name:'Wormate.io',url:'https://www.crazygames.com/embed/wormateio',cat:'multiplayer',emoji:'🐛'},
  {name:'Build Royale',url:'https://www.crazygames.com/embed/build-royale',cat:'multiplayer',emoji:'🏗️'},
  {name:'Territorial.io',url:'https://territorial.io',cat:'strategy',emoji:'🗺️'},
  {name:'Generals.io',url:'https://generals.io',cat:'strategy',emoji:'🗺️'},
  {name:'Spore Online',url:'https://www.crazygames.com/embed/spore',cat:'strategy',emoji:'🦠'},
  {name:'Stacky Dash',url:'https://www.crazygames.com/embed/stacky-dash',cat:'action',emoji:'🧱'},
  {name:'Falling Balls',url:'https://www.crazygames.com/embed/falling-balls',cat:'action',emoji:'🔵'},
  {name:'Ball Blast',url:'https://www.crazygames.com/embed/ball-blast',cat:'action',emoji:'🔵'},
  {name:'Stick Merge',url:'https://www.crazygames.com/embed/stick-merge',cat:'idle',emoji:'🕹️'},
  {name:'Merge Cannon Ball Blast',url:'https://www.crazygames.com/embed/merge-cannon-ball-blast',cat:'idle',emoji:'💣'},
  {name:'Anthill',url:'https://www.crazygames.com/embed/anthill',cat:'strategy',emoji:'🐜'},
  {name:'Tower Defense Kingdom',url:'https://www.crazygames.com/embed/tower-defense-kingdom',cat:'strategy',emoji:'🗼'},
  {name:'Ninja Hands',url:'https://www.crazygames.com/embed/ninja-hands',cat:'action',emoji:'🥷'},
  {name:'Shadow Fight Arena',url:'https://www.crazygames.com/embed/shadow-fight-arena',cat:'action',emoji:'👊'},
  {name:'Stickman Fight',url:'https://www.crazygames.com/embed/stickman-fighter-epic-battle',cat:'action',emoji:'🥊'},
  {name:'Stickman Boost 2',url:'https://www.crazygames.com/embed/stickman-boost-2',cat:'action',emoji:'🕺'},
  {name:'Stickman Parkour',url:'https://www.crazygames.com/embed/stickman-parkour',cat:'action',emoji:'🏃'},
  {name:'Crazy Steve',url:'https://www.crazygames.com/embed/crazy-steve',cat:'action',emoji:'😵'},
  {name:'Neon Blaster',url:'https://www.crazygames.com/embed/neon-blaster',cat:'action',emoji:'💥'},
  {name:'Starfall.io',url:'https://www.crazygames.com/embed/starfall-io',cat:'multiplayer',emoji:'⭐'},
  {name:'Goblin Rush',url:'https://www.crazygames.com/embed/goblin-rush',cat:'strategy',emoji:'👺'},
  {name:'Tower Crush',url:'https://www.crazygames.com/embed/tower-crush',cat:'strategy',emoji:'🗼'},
  {name:'Pigeon Pop',url:'https://www.crazygames.com/embed/pigeon-pop',cat:'puzzle',emoji:'🐦'},
  {name:'Dig Dug',url:'https://www.crazygames.com/embed/dig-dug',cat:'action',emoji:'⛏️'},
  {name:'Pac-Man',url:'https://www.crazygames.com/embed/pac-man',cat:'action',emoji:'👻'},
  {name:'Ms. Pac-Man',url:'https://www.crazygames.com/embed/ms-pac-man',cat:'action',emoji:'👻'},
  {name:'Donkey Kong',url:'https://www.crazygames.com/embed/donkey-kong',cat:'action',emoji:'🦍'},
  {name:'Super Mario Bros',url:'https://www.crazygames.com/embed/super-mario-bros',cat:'adventure',emoji:'🍄'},
  {name:'Galaga',url:'https://www.crazygames.com/embed/galaga',cat:'action',emoji:'👾'},
  {name:'Space Invaders',url:'https://www.crazygames.com/embed/space-invaders',cat:'action',emoji:'👾'},
  {name:'Pong',url:'https://www.crazygames.com/embed/pong',cat:'action',emoji:'🏓'},
  {name:'Asteroids',url:'https://www.crazygames.com/embed/asteroids',cat:'action',emoji:'☄️'},
  {name:'Breakout',url:'https://www.crazygames.com/embed/breakout',cat:'action',emoji:'🎮'},
  {name:'Digger Machine',url:'https://www.crazygames.com/embed/digger-machine',cat:'action',emoji:'⛏️'},
  {name:'Duck Hunt',url:'https://www.crazygames.com/embed/duck-hunt',cat:'action',emoji:'🦆'},
  {name:'Snow Rider 3D',url:'https://www.crazygames.com/embed/snow-rider-3d',cat:'action',emoji:'🏔️'},
  {name:'Powerline.io',url:'https://www.crazygames.com/embed/powerline-io',cat:'multiplayer',emoji:'⚡'},
  {name:'Narwhale.io',url:'https://www.crazygames.com/embed/narwhale-io',cat:'multiplayer',emoji:'🐋'},
  {name:'Planet Clicker',url:'https://www.crazygames.com/embed/planet-clicker',cat:'idle',emoji:'🌍'},
  {name:'Planet Clicker 2',url:'https://www.crazygames.com/embed/planet-clicker-2',cat:'idle',emoji:'🌍'},
  {name:'Coffee Clicker',url:'https://www.crazygames.com/embed/coffee-clicker',cat:'idle',emoji:'☕'},
  {name:'Cats & Soup',url:'https://www.crazygames.com/embed/cats-and-soup',cat:'idle',emoji:'🐱'},
  {name:'Town City Hotel Building',url:'https://www.crazygames.com/embed/town-city-hotel-building',cat:'idle',emoji:'🏙️'},
  {name:'Tank Stars',url:'https://www.crazygames.com/embed/tank-stars',cat:'action',emoji:'💣'},
  {name:'Minecraft Tower Defense',url:'https://www.crazygames.com/embed/minecraft-tower-defense',cat:'strategy',emoji:'🏰'},
  {name:'Bomb It',url:'https://www.crazygames.com/embed/bomb-it',cat:'action',emoji:'💣'},
  {name:'Bomb It 2',url:'https://www.crazygames.com/embed/bomb-it-2',cat:'action',emoji:'💣'},
  {name:'Bomb It 7',url:'https://www.crazygames.com/embed/bomb-it-7',cat:'action',emoji:'💣'},
  {name:'Battleship War',url:'https://www.crazygames.com/embed/battleship-war',cat:'strategy',emoji:'⚓'},
  {name:'Worms Zone',url:'https://www.crazygames.com/embed/worms-zone-io',cat:'multiplayer',emoji:'🐛'},
  {name:'Chompers.io',url:'https://www.crazygames.com/embed/chompers-io',cat:'multiplayer',emoji:'👄'},
  {name:'Skribbl.io',url:'https://skribbl.io',cat:'multiplayer',emoji:'✏️'},
  {name:'Gartic.io',url:'https://gartic.io',cat:'multiplayer',emoji:'🎨'},
  {name:'Jackbox Games',url:'https://jackbox.tv',cat:'multiplayer',emoji:'🎮'},
  {name:'Kart Fighter',url:'https://www.crazygames.com/embed/kart-fighter',cat:'racing',emoji:'🏎️'},
  {name:'Turbo Dismount',url:'https://www.crazygames.com/embed/turbo-dismount',cat:'action',emoji:'🚗'},
  {name:'Infinite Craft',url:'https://neal.fun/infinite-craft/',cat:'puzzle',emoji:'⚗️'},
  {name:'Gravity Ninja',url:'https://www.crazygames.com/embed/gravity-ninja',cat:'action',emoji:'🥷'},
  {name:'Ninja.io',url:'https://www.crazygames.com/embed/ninja-io',cat:'multiplayer',emoji:'🥷'},
  {name:'Pixel War',url:'https://www.crazygames.com/embed/pixel-war',cat:'multiplayer',emoji:'🎨'},
  {name:'Maze',url:'https://www.crazygames.com/embed/maze',cat:'puzzle',emoji:'🌀'},
  {name:'Pipe Push Paradise',url:'https://www.crazygames.com/embed/pipe-push-paradise',cat:'puzzle',emoji:'🔧'},
  {name:'Flow Free',url:'https://www.crazygames.com/embed/flow-free',cat:'puzzle',emoji:'🌊'},
  {name:'Nonogram Puzzle',url:'https://www.crazygames.com/embed/nonogram-puzzle',cat:'puzzle',emoji:'🔢'},
  {name:'Hexanaut.io',url:'https://www.crazygames.com/embed/hexanaut-io',cat:'multiplayer',emoji:'🔷'},
  {name:'Forge of Empires',url:'https://www.crazygames.com/embed/forge-of-empires',cat:'strategy',emoji:'🏰'},
  {name:'Tribal Wars',url:'https://www.crazygames.com/embed/tribal-wars',cat:'strategy',emoji:'⚔️'},
  {name:'Football Heads',url:'https://www.crazygames.com/embed/football-heads',cat:'sports',emoji:'🏈'},
  {name:'Cartoon Strike',url:'https://www.crazygames.com/embed/cartoon-strike',cat:'action',emoji:'🔫'},
  {name:'Pixel Warfare',url:'https://www.crazygames.com/embed/pixel-warfare',cat:'action',emoji:'🔫'},
  {name:'Army of Ages',url:'https://www.crazygames.com/embed/army-of-ages',cat:'strategy',emoji:'⚔️'},
  {name:'Jacksmith',url:'https://www.crazygames.com/embed/jacksmith',cat:'adventure',emoji:'⚒️'},
  {name:'Papas Pizzeria',url:'https://www.crazygames.com/embed/papas-pizzeria',cat:'idle',emoji:'🍕'},
  {name:'Papas Burgeria',url:'https://www.crazygames.com/embed/papas-burgeria',cat:'idle',emoji:'🍔'},
  {name:'Papas Cupcakeria',url:'https://www.crazygames.com/embed/papas-cupcakeria',cat:'idle',emoji:'🧁'},
  {name:'Papas Freezeria',url:'https://www.crazygames.com/embed/papas-freezeria',cat:'idle',emoji:'🍦'},
  {name:'Papas Pancakeria',url:'https://www.crazygames.com/embed/papas-pancakeria',cat:'idle',emoji:'🥞'},
  {name:'Papas Donuteria',url:'https://www.crazygames.com/embed/papas-donuteria',cat:'idle',emoji:'🍩'},
  {name:'Papas Hot Doggeria',url:'https://www.crazygames.com/embed/papas-hot-doggeria',cat:'idle',emoji:'🌭'},
  {name:'Papas Sushiria',url:'https://www.crazygames.com/embed/papas-sushiria',cat:'idle',emoji:'🍣'},
  {name:'Papas Pastaria',url:'https://www.crazygames.com/embed/papas-pastaria',cat:'idle',emoji:'🍝'},
  {name:'Papas Taco Mia',url:'https://www.crazygames.com/embed/papas-taco-mia',cat:'idle',emoji:'🌮'},
  {name:'Papas Wingeria',url:'https://www.crazygames.com/embed/papas-wingeria',cat:'idle',emoji:'🍗'},
  {name:'Papas Bakeria',url:'https://www.crazygames.com/embed/papas-bakeria',cat:'idle',emoji:'🥧'},
  {name:'Papas Cheeseria',url:'https://www.crazygames.com/embed/papas-cheeseria',cat:'idle',emoji:'🧀'},
  {name:'Papas Cluckeria',url:'https://www.crazygames.com/embed/papas-cluckeria-to-go',cat:'idle',emoji:'🍗'},
  {name:'Papas Mocharia',url:'https://www.crazygames.com/embed/papas-mocharia-to-go',cat:'idle',emoji:'☕'},
  {name:'Papas Scooperia',url:'https://www.crazygames.com/embed/papas-scooperia-to-go',cat:'idle',emoji:'🍦'},
  {name:'Papas Paleteria',url:'https://www.crazygames.com/embed/papas-paleteria-to-go',cat:'idle',emoji:'🍡'},
  {name:'Parking Fury',url:'https://www.crazygames.com/embed/parking-fury',cat:'racing',emoji:'🅿️'},
  {name:'Parking Fury 3D',url:'https://www.crazygames.com/embed/parking-fury-3d',cat:'racing',emoji:'🅿️'},
  {name:'Euro Truck Driver',url:'https://www.crazygames.com/embed/euro-truck-driver',cat:'racing',emoji:'🚛'},
  {name:'City Car Driving',url:'https://www.crazygames.com/embed/city-car-driving-3d',cat:'racing',emoji:'🚗'},
  {name:'American Truck Simulator',url:'https://www.crazygames.com/embed/american-truck-simulator',cat:'racing',emoji:'🚛'},
  {name:'Bricky',url:'https://www.crazygames.com/embed/bricky',cat:'puzzle',emoji:'🧱'},
  {name:'Color Fill',url:'https://www.crazygames.com/embed/color-fill',cat:'puzzle',emoji:'🎨'},
  {name:'Helix Jump',url:'https://www.crazygames.com/embed/helix-jump',cat:'action',emoji:'🌀'},
  {name:'Stack',url:'https://www.crazygames.com/embed/stack',cat:'action',emoji:'📦'},
  {name:'Rolling Ball 3D',url:'https://www.crazygames.com/embed/rolling-ball-3d',cat:'action',emoji:'🔵'},
  {name:'Hole in the Wall',url:'https://www.crazygames.com/embed/hole-in-the-wall',cat:'action',emoji:'🕳️'},
  {name:'Mr Beast World',url:'https://www.crazygames.com/embed/mr-beast-world',cat:'action',emoji:'😱'},
  {name:'Baldis Basics',url:'https://www.crazygames.com/embed/baldis-basics',cat:'adventure',emoji:'📏'},
  {name:'Five Nights at Freddys',url:'https://www.crazygames.com/embed/five-nights-at-freddys',cat:'adventure',emoji:'🐻'},
  {name:'FNAF 2',url:'https://www.crazygames.com/embed/fnaf-2',cat:'adventure',emoji:'🐻'},
  {name:'FNAF 3',url:'https://www.crazygames.com/embed/fnaf-3',cat:'adventure',emoji:'🐻'},
  {name:'FNAF 4',url:'https://www.crazygames.com/embed/fnaf-4',cat:'adventure',emoji:'🐻'},
  {name:'Into the Dead',url:'https://www.crazygames.com/embed/into-the-dead',cat:'action',emoji:'🧟'},
  {name:'Dead Zed',url:'https://www.crazygames.com/embed/dead-zed',cat:'action',emoji:'🧟'},
  {name:'Zombie Road',url:'https://www.crazygames.com/embed/zombie-road',cat:'action',emoji:'🧟'},
  {name:'Z Escape',url:'https://www.crazygames.com/embed/z-escape',cat:'adventure',emoji:'🏃'},
  {name:'Vex 3',url:'https://www.crazygames.com/embed/vex-3',cat:'action',emoji:'🏃'},
  {name:'Vex 4',url:'https://www.crazygames.com/embed/vex-4',cat:'action',emoji:'🏃'},
  {name:'Vex 5',url:'https://www.crazygames.com/embed/vex-5',cat:'action',emoji:'🏃'},
  {name:'Vex 6',url:'https://www.crazygames.com/embed/vex-6',cat:'action',emoji:'🏃'},
  {name:'Vex 7',url:'https://www.crazygames.com/embed/vex-7',cat:'action',emoji:'🏃'},
  {name:'Red Ball 4',url:'https://www.crazygames.com/embed/red-ball-4',cat:'action',emoji:'🔴'},
  {name:'Red Ball 6',url:'https://www.crazygames.com/embed/red-ball-6',cat:'action',emoji:'🔴'},
  {name:'Bouncing Ball',url:'https://www.crazygames.com/embed/bouncing-ball',cat:'action',emoji:'🔵'},
  {name:'Stick Golf',url:'https://www.crazygames.com/embed/stick-golf',cat:'sports',emoji:'⛳'},
  {name:'Golf Battle',url:'https://www.crazygames.com/embed/golf-battle',cat:'sports',emoji:'⛳'},
  {name:'Cyber Surfer',url:'https://www.crazygames.com/embed/cyber-surfer',cat:'action',emoji:'🛹'},
  {name:'Hanger',url:'https://www.crazygames.com/embed/hanger',cat:'action',emoji:'🔗'},
  {name:'Hanger 2',url:'https://www.crazygames.com/embed/hanger-2',cat:'action',emoji:'🔗'},
  {name:'Elastoman',url:'https://www.crazygames.com/embed/elastoman',cat:'action',emoji:'🤸'}
]; return x; })();

var embeddedGamesCats = ['all','action','puzzle','racing','sports','strategy','idle','multiplayer','adventure'];
var embeddedCatLabels = {all:'All',action:'Action',puzzle:'Puzzle',racing:'Racing',sports:'Sports',strategy:'Strategy',idle:'Idle/Clicker',multiplayer:'Multiplayer',adventure:'Adventure'};

function convertTabToEmbedded(tabId) {
  for (var i = 0; i < tabs.length; i++) {
    if (tabs[i].id === tabId) {
      tabs[i].type = 'embedded';
      tabs[i].label = 'Embedded';
      break;
    }
  }
  var el = document.getElementById('tabContent-' + tabId);
  el.innerHTML = '';
  var container = document.createElement('div');
  container.style.cssText = 'display:flex;flex-direction:column;height:100%;overflow:hidden;background:var(--bg-primary);';

  var header = document.createElement('div');
  header.style.cssText = 'padding:8px 14px 0;flex-shrink:0;';
  var title = document.createElement('div');
  title.style.cssText = 'font-size:16px;font-weight:700;color:var(--text-primary);margin-bottom:8px;';
  title.textContent = '🎮 Browser Games';
  header.appendChild(title);

  var searchRow = document.createElement('div');
  searchRow.style.cssText = 'display:flex;gap:8px;margin-bottom:8px;flex-wrap:wrap;';
  var searchInput = document.createElement('input');
  searchInput.type = 'text';
  searchInput.placeholder = 'Search 200+ games...';
  searchInput.style.cssText = 'flex:1;min-width:150px;padding:7px 12px;border:none;border-radius:6px;background:var(--bg-tertiary);color:var(--text-primary);font-size:13px;outline:none;';
  searchRow.appendChild(searchInput);
  header.appendChild(searchRow);

  var catRow = document.createElement('div');
  catRow.style.cssText = 'display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;';
  embeddedGamesCats.forEach(function(cat) {
    var btn = document.createElement('button');
    btn.textContent = embeddedCatLabels[cat];
    btn.setAttribute('data-cat', cat);
    btn.style.cssText = 'padding:4px 12px;border-radius:20px;border:1px solid var(--border);background:' + (cat==='all'?'var(--accent)':'var(--bg-tertiary)') + ';color:' + (cat==='all'?'#fff':'var(--text-secondary)') + ';font-size:12px;cursor:pointer;transition:all 0.15s;';
    catRow.appendChild(btn);
  });
  header.appendChild(catRow);
  container.appendChild(header);

  var listContainer = document.createElement('div');
  listContainer.style.cssText = 'flex:1;overflow-y:auto;padding:0 14px 14px;';
  container.appendChild(listContainer);

  var activeCat = 'all';
  var recentlyPlayed = JSON.parse(localStorage.getItem('embed_recent') || '[]');
  var favorites = JSON.parse(localStorage.getItem('embed_favorites') || '[]');

  function saveRecent(name) {
    var arr = JSON.parse(localStorage.getItem('embed_recent') || '[]');
    arr = arr.filter(function(n) { return n !== name; });
    arr.unshift(name);
    if (arr.length > 12) arr = arr.slice(0,12);
    localStorage.setItem('embed_recent', JSON.stringify(arr));
  }
  function toggleFavorite(name) {
    var arr = JSON.parse(localStorage.getItem('embed_favorites') || '[]');
    var idx = arr.indexOf(name);
    if (idx >= 0) arr.splice(idx,1); else arr.push(name);
    localStorage.setItem('embed_favorites', JSON.stringify(arr));
    return arr;
  }

  function gameProxyUrl(url) {
    return url;
  }

  function openEmbeddedGame(game) {
    saveRecent(game.name);
    container.innerHTML = '';
    var gameContainer = document.createElement('div');
    gameContainer.style.cssText = 'display:flex;flex-direction:column;flex:1;min-height:0;background:#000;';
    var toolbar = document.createElement('div');
    toolbar.style.cssText = 'display:flex;align-items:center;gap:8px;padding:8px 12px;background:var(--bg-primary);border-bottom:1px solid var(--border);flex-shrink:0;';
    var backBtn = document.createElement('button');
    backBtn.textContent = '← Back';
    backBtn.style.cssText = 'padding:5px 12px;background:var(--bg-tertiary);color:var(--text-primary);border:none;border-radius:4px;cursor:pointer;font-size:13px;';
    backBtn.addEventListener('click', function() { convertTabToEmbedded(tabId); });
    toolbar.appendChild(backBtn);
    var nameSpan = document.createElement('span');
    nameSpan.textContent = game.emoji + ' ' + game.name;
    nameSpan.style.cssText = 'font-size:14px;font-weight:600;color:var(--text-primary);flex:1;';
    toolbar.appendChild(nameSpan);
    var favBtn = document.createElement('button');
    var curFavs = JSON.parse(localStorage.getItem('embed_favorites') || '[]');
    favBtn.textContent = curFavs.indexOf(game.name) >= 0 ? '★ Unfavorite' : '☆ Favorite';
    favBtn.style.cssText = 'padding:5px 12px;background:var(--bg-tertiary);color:var(--yellow,#f0b232);border:none;border-radius:4px;cursor:pointer;font-size:13px;';
    favBtn.addEventListener('click', function() {
      var fav = toggleFavorite(game.name);
      favBtn.textContent = fav.indexOf(game.name) >= 0 ? '★ Unfavorite' : '☆ Favorite';
    });
    toolbar.appendChild(favBtn);
    var newTabBtn = document.createElement('button');
    newTabBtn.textContent = '↗ Open in New Tab';
    newTabBtn.style.cssText = 'padding:5px 12px;background:var(--accent);color:#fff;border:none;border-radius:4px;cursor:pointer;font-size:13px;';
    newTabBtn.addEventListener('click', function() { window.open(game.url, '_blank'); });
    toolbar.appendChild(newTabBtn);
    var fsBtn = document.createElement('button');
    fsBtn.title = 'Fullscreen';
    fsBtn.textContent = '⛶';
    fsBtn.style.cssText = 'padding:5px 10px;background:var(--bg-tertiary);color:var(--text-primary);border:none;border-radius:4px;cursor:pointer;font-size:16px;line-height:1;';
    fsBtn.addEventListener('click', function() {
      var target = gameContainer || wrap || frame;
      if (target.requestFullscreen) target.requestFullscreen();
      else if (target.webkitRequestFullscreen) target.webkitRequestFullscreen();
      else if (target.mozRequestFullScreen) target.mozRequestFullScreen();
      else if (target.msRequestFullscreen) target.msRequestFullscreen();
    });
    toolbar.appendChild(fsBtn);
    gameContainer.appendChild(toolbar);
    var frame = document.createElement('iframe');
    frame.src = gameProxyUrl(game.url);
    frame.style.cssText = 'flex:1;width:100%;height:100%;border:none;min-height:0;';
    frame.allow = 'fullscreen; autoplay; gamepad; payment';
    frame.setAttribute('allowfullscreen', '');
    var errOverlay = document.createElement('div');
    errOverlay.style.cssText = 'display:none;position:absolute;inset:0;background:rgba(0,0,0,0.85);color:#fff;align-items:center;justify-content:center;flex-direction:column;gap:14px;text-align:center;padding:24px;';
    var wrap = document.createElement('div');
    wrap.style.cssText = 'position:relative;flex:1;min-height:0;overflow:hidden;display:flex;flex-direction:column;';
    errOverlay.style.position = 'absolute';
    errOverlay.innerHTML = '<div style="font-size:32px;">🚫</div><div style="font-size:18px;font-weight:700;">Game blocked by browser</div><div style="font-size:13px;color:#ccc;">This game does not allow embedding.<br>Open it directly instead.</div>';
    var errOpenBtn = document.createElement('button');
    errOpenBtn.textContent = 'Open in New Tab';
    errOpenBtn.style.cssText = 'padding:10px 20px;background:var(--accent);color:#fff;border:none;border-radius:6px;cursor:pointer;font-size:14px;';
    errOpenBtn.addEventListener('click', function() { window.open(game.url, '_blank'); });
    errOverlay.appendChild(errOpenBtn);
    wrap.appendChild(frame);
    wrap.appendChild(errOverlay);
    gameContainer.appendChild(wrap);
    // Spinner while loading
    var spinner = document.createElement('div');
    spinner.style.cssText = 'position:absolute;inset:0;background:var(--bg-primary);display:flex;align-items:center;justify-content:center;flex-direction:column;gap:12px;z-index:5;';
    spinner.innerHTML = '<div style="width:40px;height:40px;border:4px solid var(--border);border-top-color:var(--accent);border-radius:50%;animation:spin 0.8s linear infinite;"></div><div style="font-size:13px;color:var(--text-muted);">Loading ' + escapeHtml(game.name) + '...</div>';
    wrap.appendChild(spinner);
    var loadTimeout = setTimeout(function() {
      spinner.style.display = 'none';
      errOverlay.style.display = 'flex';
      errOverlay.querySelector('div:nth-child(2)').textContent = 'Game failed to load';
    }, 12000);
    frame.addEventListener('load', function() {
      clearTimeout(loadTimeout);
      spinner.style.display = 'none';
    });
    frame.addEventListener('error', function() {
      clearTimeout(loadTimeout);
      spinner.style.display = 'none';
      errOverlay.style.display = 'flex';
    });
    // Update tab label with game name
    for (var _ti = 0; _ti < tabs.length; _ti++) {
      if (tabs[_ti].id === tabId) { tabs[_ti].label = game.emoji + ' ' + game.name; break; }
    }
    el.appendChild(gameContainer);
    renderTabBar();
    // Fix blank page after fullscreen exit: restore container visibility
    function _onFsChange() {
      var fsEl = document.fullscreenElement || document.webkitFullscreenElement || document.mozFullScreenElement;
      if (!fsEl) {
        gameContainer.style.display = 'flex';
        wrap.style.display = 'flex';
        frame.style.display = 'block';
        el.style.display = 'flex';
        el.style.flexDirection = 'column';
      }
    }
    document.addEventListener('fullscreenchange', _onFsChange);
    document.addEventListener('webkitfullscreenchange', _onFsChange);
    document.addEventListener('mozfullscreenchange', _onFsChange);
  }

  function renderGames(q, cat) {
    listContainer.innerHTML = '';
    var faves = JSON.parse(localStorage.getItem('embed_favorites') || '[]');
    var recent = JSON.parse(localStorage.getItem('embed_recent') || '[]');
    var filtered = embeddedGamesList.filter(function(g) {
      if (cat !== 'all' && g.cat !== cat) return false;
      if (q && g.name.toLowerCase().indexOf(q.toLowerCase()) === -1) return false;
      return true;
    });
    function makeGameCard(g) {
      var card = document.createElement('div');
      card.style.cssText = 'display:flex;align-items:center;gap:10px;padding:10px 12px;border-radius:8px;cursor:pointer;transition:background 0.1s;margin-bottom:2px;';
      card.setAttribute('data-testid', 'embed-game-' + g.name.replace(/\s/g,'_'));
      card.addEventListener('mouseenter', function() { card.style.background='var(--bg-message-hover)'; });
      card.addEventListener('mouseleave', function() { card.style.background=''; });
      card.addEventListener('click', function() { openEmbeddedGame(g); });
      var emoji = document.createElement('div');
      emoji.textContent = g.emoji;
      emoji.style.cssText = 'font-size:22px;width:36px;text-align:center;flex-shrink:0;';
      card.appendChild(emoji);
      var info = document.createElement('div');
      info.style.cssText = 'flex:1;min-width:0;';
      var nameEl = document.createElement('div');
      nameEl.style.cssText = 'font-size:14px;font-weight:500;color:var(--text-primary);';
      nameEl.textContent = g.name;
      info.appendChild(nameEl);
      var catEl = document.createElement('div');
      catEl.style.cssText = 'font-size:11px;color:var(--text-muted);text-transform:capitalize;margin-top:1px;';
      catEl.textContent = embeddedCatLabels[g.cat] || g.cat;
      info.appendChild(catEl);
      card.appendChild(info);
      if (faves.indexOf(g.name) >= 0) {
        var star = document.createElement('span');
        star.textContent = '★';
        star.style.cssText = 'color:var(--yellow,#f0b232);font-size:14px;';
        card.appendChild(star);
      }
      return card;
    }
    if (!q && cat === 'all') {
      var recentGames = embeddedGamesList.filter(function(g) { return recent.indexOf(g.name) >= 0; })
        .sort(function(a,b) { return recent.indexOf(a.name) - recent.indexOf(b.name); });
      var faveGames = embeddedGamesList.filter(function(g) { return faves.indexOf(g.name) >= 0 && recent.indexOf(g.name) === -1; });
      if (recentGames.length > 0) {
        var rl = document.createElement('div');
        rl.style.cssText = 'font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;padding:12px 2px 6px;';
        rl.textContent = 'Recently Played';
        listContainer.appendChild(rl);
        recentGames.forEach(function(g) { listContainer.appendChild(makeGameCard(g)); });
      }
      if (faveGames.length > 0) {
        var fl = document.createElement('div');
        fl.style.cssText = 'font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;padding:12px 2px 6px;';
        fl.textContent = 'Favorites';
        listContainer.appendChild(fl);
        faveGames.forEach(function(g) { listContainer.appendChild(makeGameCard(g)); });
      }
      var al = document.createElement('div');
      al.style.cssText = 'font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;padding:12px 2px 6px;';
      al.textContent = 'All Games (' + embeddedGamesList.length + ')';
      listContainer.appendChild(al);
      filtered.forEach(function(g) { listContainer.appendChild(makeGameCard(g)); });
    } else {
      if (filtered.length === 0) {
        var empty = document.createElement('div');
        empty.style.cssText = 'text-align:center;color:var(--text-muted);padding:40px;font-size:14px;';
        empty.textContent = 'No games found.';
        listContainer.appendChild(empty);
      } else {
        var al2 = document.createElement('div');
        al2.style.cssText = 'font-size:11px;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:0.5px;padding:12px 2px 6px;';
        al2.textContent = filtered.length + ' games';
        listContainer.appendChild(al2);
        filtered.forEach(function(g) { listContainer.appendChild(makeGameCard(g)); });
      }
    }
  }

  catRow.querySelectorAll('button').forEach(function(btn) {
    btn.addEventListener('click', function() {
      activeCat = btn.getAttribute('data-cat');
      catRow.querySelectorAll('button').forEach(function(b) {
        var isActive = b.getAttribute('data-cat') === activeCat;
        b.style.background = isActive ? 'var(--accent)' : 'var(--bg-tertiary)';
        b.style.color = isActive ? '#fff' : 'var(--text-secondary)';
      });
      renderGames(searchInput.value.trim(), activeCat);
    });
  });
  searchInput.addEventListener('input', function() { renderGames(this.value.trim(), activeCat); });
  searchInput.addEventListener('keydown', function(e) { e.stopPropagation(); });

  el.appendChild(container);
  renderGames('', 'all');
  renderTabBar();
}

function convertTabToBrowser(tabId) {
  for (var i=0;i<tabs.length;i++){if(tabs[i].id===tabId){tabs[i].type='browser';tabs[i].label='Browser';break;}}
  var el=document.getElementById('tabContent-'+tabId);
  el.innerHTML='';

  // State
  var _btabs=[];
  var _act=null;
  var _vpnOn=true;
  var _savedBm=JSON.parse(localStorage.getItem('browser_bookmarks')||'[]');
  var _sid=(function(){var k='_bsid';var v=sessionStorage.getItem(k);if(!v){v=Math.random().toString(36).slice(2)+Date.now().toString(36);sessionStorage.setItem(k,v);}return v;})();

  // Container
  var container=document.createElement('div');
  container.style.cssText='display:flex;flex-direction:column;height:100%;background:var(--bg-primary);overflow:hidden;';
  var progressBar=document.createElement('div');
  progressBar.style.cssText='height:3px;width:0%;background:linear-gradient(90deg,var(--accent),#a78bfa);transition:width 0.4s ease;flex-shrink:0;';
  container.appendChild(progressBar);

  // Toolbar
  var toolbar=document.createElement('div');
  toolbar.style.cssText='display:flex;align-items:center;gap:4px;padding:6px 8px;background:var(--bg-secondary);border-bottom:1px solid var(--border);flex-shrink:0;';
  function mkBtn(html,title,isAcc,sz){
    var b=document.createElement('button');b.innerHTML=html;b.title=title;
    b.style.cssText='width:28px;height:28px;display:flex;align-items:center;justify-content:center;background:'+(isAcc?'var(--accent)':'none')+';color:'+(isAcc?'#fff':'var(--text-muted)')+';border:none;border-radius:50%;cursor:pointer;font-size:'+(sz||'14px')+';flex-shrink:0;transition:background 0.12s,color 0.12s,transform 0.1s;';
    if(isAcc){b.addEventListener('mouseover',function(){this.style.transform='scale(1.1)';});b.addEventListener('mouseout',function(){this.style.transform='scale(1)';});}
    else{b.addEventListener('mouseover',function(){this.style.background='var(--bg-tertiary)';this.style.color='var(--text-primary)';});b.addEventListener('mouseout',function(){this.style.background='none';this.style.color='var(--text-muted)';});}
    return b;
  }
  var backBtn=mkBtn('&#x2190;','Back');
  var fwdBtn=mkBtn('&#x2192;','Forward');
  var refreshBtn=mkBtn('&#x21BB;','Reload');
  var homeBtn=mkBtn('&#x2302;','New tab');
  toolbar.appendChild(backBtn);toolbar.appendChild(fwdBtn);toolbar.appendChild(refreshBtn);toolbar.appendChild(homeBtn);

  // Address bar
  var addrWrap=document.createElement('div');
  addrWrap.style.cssText='flex:1;display:flex;align-items:center;gap:5px;background:var(--bg-tertiary);border-radius:20px;border:1.5px solid transparent;padding:0 12px;min-width:0;cursor:text;transition:border-color 0.15s,background 0.15s;';
  addrWrap.addEventListener('click',function(){urlInput.focus();});
  var lockSpan=document.createElement('span');lockSpan.textContent='🔒';lockSpan.style.cssText='font-size:11px;flex-shrink:0;opacity:0.5;user-select:none;';addrWrap.appendChild(lockSpan);
  var urlInput=document.createElement('input');
  urlInput.type='text';urlInput.id='browser-urlinput-'+tabId;urlInput.placeholder='Search DuckDuckGo or enter a URL...';
  urlInput.style.cssText='flex:1;border:none;background:transparent;color:var(--text-primary);font-size:13px;outline:none;min-width:0;padding:6px 0;';
  urlInput.addEventListener('focus',function(){addrWrap.style.borderColor='rgba(88,101,242,0.55)';addrWrap.style.background='var(--bg-primary)';this.select();});
  urlInput.addEventListener('blur',function(){addrWrap.style.borderColor='transparent';addrWrap.style.background='var(--bg-tertiary)';});
  addrWrap.appendChild(urlInput);
  var vpnSpan=document.createElement('span');vpnSpan.style.cssText='font-size:11px;flex-shrink:0;user-select:none;cursor:default;margin-left:2px;';addrWrap.appendChild(vpnSpan);
  toolbar.appendChild(addrWrap);

  var goBtn=mkBtn('&#x27A4;','Go',true);goBtn.id='browser-go-'+tabId;toolbar.appendChild(goBtn);

  // VPN toggle pill
  var vpnBtn=document.createElement('button');
  vpnBtn.style.cssText='padding:0 9px;height:24px;display:flex;align-items:center;gap:4px;border-radius:12px;cursor:pointer;font-size:11px;font-weight:700;flex-shrink:0;transition:all 0.15s;white-space:nowrap;border:1px solid;';
  function updateVpnBtn(){
    if(_vpnOn){vpnBtn.innerHTML='🛡 VPN';vpnBtn.style.background='rgba(34,197,94,0.15)';vpnBtn.style.color='#22c55e';vpnBtn.style.borderColor='rgba(34,197,94,0.3)';vpnSpan.textContent='🛡';lockSpan.textContent='🔒';}
    else{vpnBtn.innerHTML='\u26A0 Direct';vpnBtn.style.background='rgba(234,179,8,0.15)';vpnBtn.style.color='#eab308';vpnBtn.style.borderColor='rgba(234,179,8,0.3)';vpnSpan.textContent='';lockSpan.textContent='\u26A0';}
  }
  vpnBtn.addEventListener('click',function(){_vpnOn=!_vpnOn;updateVpnBtn();if(_act&&_act.url)navigate(_act.url);});
  vpnBtn.title='Toggle VPN proxy (routes traffic through server)';
  toolbar.appendChild(vpnBtn);

  var bookmarkBtn=mkBtn('&#x2606;','Bookmark this page','','17px');toolbar.appendChild(bookmarkBtn);
  var fsBtn=mkBtn('&#x26F6;','Toggle fullscreen');toolbar.appendChild(fsBtn);
  var newWindowBtn=mkBtn('&#x2197;','Open in new window','','17px');toolbar.appendChild(newWindowBtn);
  container.appendChild(toolbar);

  // Inner browser tab bar
  var innerTabBar=document.createElement('div');
  innerTabBar.style.cssText='display:flex;align-items:stretch;background:var(--bg-secondary);border-bottom:1px solid var(--border);flex-shrink:0;height:30px;overflow-x:auto;scrollbar-width:none;';
  container.appendChild(innerTabBar);

  // Bookmarks bar
  var bkBar=document.createElement('div');
  bkBar.style.cssText='display:flex;align-items:center;gap:3px;padding:3px 10px;background:var(--bg-secondary);border-bottom:1px solid var(--border);flex-shrink:0;min-height:26px;overflow-x:auto;scrollbar-width:none;';
  container.appendChild(bkBar);

  // Frame wrapper
  var frameWrap=document.createElement('div');
  frameWrap.style.cssText='flex:1;position:relative;overflow:hidden;';

  // Home page
  var homePage=document.createElement('div');
  homePage.style.cssText='position:absolute;inset:0;display:none;flex-direction:column;align-items:center;justify-content:center;gap:18px;overflow-y:auto;padding:28px;';
  var hTitle=document.createElement('div');hTitle.style.cssText='font-size:26px;font-weight:800;color:var(--text-primary);';hTitle.innerHTML='🌐 Browser';homePage.appendChild(hTitle);
  var homeSearch=document.createElement('div');
  homeSearch.style.cssText='display:flex;align-items:center;width:100%;max-width:520px;background:var(--bg-tertiary);border:1.5px solid var(--border);border-radius:24px;overflow:hidden;transition:border-color 0.15s;box-shadow:0 2px 8px rgba(0,0,0,0.12);';
  homeSearch.addEventListener('focusin',function(){this.style.borderColor='rgba(88,101,242,0.6)';});homeSearch.addEventListener('focusout',function(){this.style.borderColor='var(--border)';});
  var homeSearchInput=document.createElement('input');homeSearchInput.type='text';homeSearchInput.placeholder='Search DuckDuckGo or enter a URL...';
  homeSearchInput.style.cssText='flex:1;padding:12px 18px;border:none;background:transparent;color:var(--text-primary);font-size:14px;outline:none;';
  var homeSearchBtn=document.createElement('button');homeSearchBtn.innerHTML='&#x27A4;';
  homeSearchBtn.style.cssText='padding:10px 18px;background:var(--accent);color:#fff;border:none;cursor:pointer;font-size:16px;flex-shrink:0;transition:background 0.15s;';
  homeSearchBtn.addEventListener('mouseover',function(){this.style.background='var(--accent-hover)';});homeSearchBtn.addEventListener('mouseout',function(){this.style.background='var(--accent)';});
  homeSearch.appendChild(homeSearchInput);homeSearch.appendChild(homeSearchBtn);homePage.appendChild(homeSearch);
  var homeNote=document.createElement('div');homeNote.style.cssText='display:flex;align-items:center;gap:10px;font-size:11px;color:var(--text-muted);';
  homeNote.innerHTML='<span>🛡 Proxy Active</span><span style="opacity:0.35">|</span><span>🔍 DuckDuckGo</span><span style="opacity:0.35">|</span><span>🚫 Google\u2192DDG</span>';
  homePage.appendChild(homeNote);
  var quickGrid=document.createElement('div');quickGrid.style.cssText='display:grid;grid-template-columns:repeat(auto-fill,minmax(90px,1fr));gap:8px;width:100%;max-width:540px;';
  var quickSites=[
    {e:'🔍',n:'DuckDuckGo',u:'https://lite.duckduckgo.com/lite/'},
    {e:'\u25B6',n:'YouTube',u:'https://youtube.com'},
    {e:'📖',n:'Wikipedia',u:'https://wikipedia.org'},
    {e:'🐙',n:'GitHub',u:'https://github.com'},
    {e:'\u265F',n:'Chess',u:'https://lichess.org'},
    {e:'🧩',n:'Inf.Craft',u:'https://neal.fun/infinite-craft/'},
    {e:'📝',n:'Wordle',u:'https://wordplay.com'},
    {e:'\u270D',n:'AutoDraw',u:'https://autodraw.com'},
    {e:'🌐',n:'Reddit',u:'https://old.reddit.com'},
    {e:'📰',n:'Hacker News',u:'https://news.ycombinator.com'},
    {e:'🎮',n:'Coolmath',u:'https://www.coolmathgames.com'},
    {e:'📡',n:'Archive',u:'https://web.archive.org'},
  ];
  quickSites.forEach(function(s){
    var btn=document.createElement('button');
    btn.style.cssText='display:flex;flex-direction:column;align-items:center;gap:5px;padding:12px 6px;background:var(--bg-tertiary);color:var(--text-primary);border:1px solid var(--border);border-radius:10px;cursor:pointer;font-size:11px;line-height:1.3;transition:background 0.12s,border-color 0.12s,transform 0.1s;';
    btn.innerHTML='<span style="font-size:22px;">'+s.e+'</span>'+escapeHtml(s.n);
    btn.addEventListener('click',function(){navigate(s.u);});
    btn.addEventListener('mouseover',function(){this.style.background='var(--bg-secondary)';this.style.borderColor='var(--accent)';this.style.transform='translateY(-2px)';});
    btn.addEventListener('mouseout',function(){this.style.background='var(--bg-tertiary)';this.style.borderColor='var(--border)';this.style.transform='none';});
    quickGrid.appendChild(btn);
  });
  homePage.appendChild(quickGrid);
  frameWrap.appendChild(homePage);

  // Error overlay
  var blockedMsg=document.createElement('div');
  blockedMsg.style.cssText='display:none;position:absolute;inset:0;background:var(--bg-primary);flex-direction:column;align-items:center;justify-content:center;gap:12px;text-align:center;padding:32px;';
  frameWrap.appendChild(blockedMsg);
  container.appendChild(frameWrap);
  el.appendChild(container);

  // Progress helpers
  var _progTimer=null;
  function startProgress(){progressBar.style.transition='none';progressBar.style.width='0%';setTimeout(function(){progressBar.style.transition='width 2s ease';progressBar.style.width='75%';},20);clearTimeout(_progTimer);}
  function finishProgress(){progressBar.style.transition='width 0.3s ease';progressBar.style.width='100%';_progTimer=setTimeout(function(){progressBar.style.width='0%';},400);}

  // Show/hide
  function showFrame(){if(_act&&_act.frame)_act.frame.style.display='block';homePage.style.display='none';blockedMsg.style.display='none';}
  function showHome(){if(_act&&_act.frame)_act.frame.style.display='none';homePage.style.display='flex';blockedMsg.style.display='none';if(_act){_act.url='';_act.mode='home';}updateBmBtn();}
  function showBlocked(icon,title,body,extUrl){
    if(_act&&_act.frame)_act.frame.style.display='none';homePage.style.display='none';finishProgress();
    blockedMsg.innerHTML='';blockedMsg.style.display='flex';
    var inner=document.createElement('div');inner.style.cssText='display:flex;flex-direction:column;align-items:center;gap:14px;max-width:440px;text-align:center;';
    inner.innerHTML='<div style="font-size:52px;line-height:1;">'+icon+'</div>'+'<div style="font-size:19px;font-weight:800;color:var(--text-primary);">'+escapeHtml(title)+'</div>'+'<div style="font-size:13px;color:var(--text-secondary);line-height:1.7;max-width:360px;">'+body+'</div>';
    var btnRow=document.createElement('div');btnRow.style.cssText='display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-top:4px;';
    if(extUrl){var eb=document.createElement('button');eb.innerHTML='&#x2197; Open in New Window';eb.style.cssText='padding:9px 18px;background:var(--accent);color:#fff;border:none;border-radius:8px;cursor:pointer;font-size:13px;font-weight:600;';eb.addEventListener('click',function(){window.open(extUrl,'_blank');});btnRow.appendChild(eb);}
    var homeB=document.createElement('button');homeB.textContent='🏠 Home';homeB.style.cssText='padding:9px 18px;background:var(--bg-tertiary);color:var(--text-primary);border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:13px;';homeB.addEventListener('click',showHome);btnRow.appendChild(homeB);
    inner.appendChild(btnRow);blockedMsg.appendChild(inner);if(_act)_act.mode='blocked';
  }

  // Bookmark helpers
  function updateBmBtn(){var url=_act?_act.url:'';var isBm=url&&_savedBm.some(function(b){return b.url===url;});bookmarkBtn.innerHTML=isBm?'&#x2605;':'&#x2606;';bookmarkBtn.style.color=isBm?'gold':'';}
  function renderBmBar(){
    bkBar.innerHTML='';
    if(_savedBm.length===0){var h=document.createElement('span');h.style.cssText='font-size:11px;color:var(--text-muted);padding:0 4px;white-space:nowrap;';h.textContent='\u2606 Bookmark pages with the \u2606 button above';bkBar.appendChild(h);return;}
    _savedBm.forEach(function(bm,idx){
      var b=document.createElement('button');b.title=bm.url;b.textContent=bm.name||bm.url.replace(/^https?:\/\//,'').split('/')[0];
      b.style.cssText='padding:2px 8px;background:var(--bg-tertiary);color:var(--text-primary);border:1px solid var(--border);border-radius:4px;cursor:pointer;font-size:11px;white-space:nowrap;';
      b.addEventListener('click',function(){navigate(bm.url);});
      b.addEventListener('contextmenu',function(e){e.preventDefault();_savedBm.splice(idx,1);localStorage.setItem('browser_bookmarks',JSON.stringify(_savedBm));renderBmBar();});
      bkBar.appendChild(b);
    });
  }

  // Inner tab management
  function _mkFrame(){
    var f=document.createElement('iframe');
    f.style.cssText='position:absolute;inset:0;width:100%;height:100%;border:none;display:none;';
    f.allow='fullscreen; autoplay; payment; camera; microphone; gamepad';f.setAttribute('allowfullscreen','');
    f.setAttribute('sandbox','allow-same-origin allow-scripts allow-forms allow-popups allow-popups-to-escape-sandbox allow-top-navigation-by-user-activation');
    frameWrap.insertBefore(f,blockedMsg);return f;
  }
  function renderInnerTabs(){
    innerTabBar.innerHTML='';
    _btabs.forEach(function(t){
      var td=document.createElement('div');var isA=_act&&_act.id===t.id;
      td.style.cssText='display:flex;align-items:center;gap:4px;padding:0 8px 0 10px;min-width:80px;max-width:160px;height:100%;cursor:pointer;border-right:1px solid var(--border);flex-shrink:0;position:relative;background:'+(isA?'var(--bg-primary)':'transparent')+';transition:background 0.1s;';
      if(isA){var ul=document.createElement('div');ul.style.cssText='position:absolute;bottom:0;left:0;right:0;height:2px;background:var(--accent);border-radius:2px 2px 0 0;';td.appendChild(ul);}
      var tl=document.createElement('span');tl.style.cssText='flex:1;font-size:11px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;color:'+(isA?'var(--text-primary)':'var(--text-muted)')+';';tl.textContent=t.label||'New Tab';td.appendChild(tl);
      if(_btabs.length>1){
        var cx=document.createElement('span');cx.textContent='\u00D7';cx.style.cssText='font-size:13px;color:var(--text-muted);border-radius:3px;width:16px;height:16px;display:flex;align-items:center;justify-content:center;flex-shrink:0;line-height:1;';
        cx.addEventListener('mouseover',function(){this.style.background='rgba(255,59,48,0.2)';this.style.color='#ff3b30';});cx.addEventListener('mouseout',function(){this.style.background='none';this.style.color='var(--text-muted)';});
        cx.addEventListener('click',function(e){e.stopPropagation();closeBtab(t.id);});td.appendChild(cx);
      }
      if(!isA){td.addEventListener('mouseover',function(){this.style.background='var(--bg-tertiary)';});td.addEventListener('mouseout',function(){this.style.background='transparent';});}
      td.addEventListener('click',function(){switchBtab(t.id);});
      innerTabBar.appendChild(td);
    });
    var addBtn=document.createElement('button');addBtn.innerHTML='+';addBtn.title='New tab';
    addBtn.style.cssText='padding:0 10px;height:100%;background:none;border:none;border-right:1px solid var(--border);color:var(--text-muted);cursor:pointer;font-size:18px;flex-shrink:0;transition:background 0.1s;';
    addBtn.addEventListener('mouseover',function(){this.style.background='var(--bg-tertiary)';});addBtn.addEventListener('mouseout',function(){this.style.background='none';});
    addBtn.addEventListener('click',function(){addBtab();});innerTabBar.appendChild(addBtn);
  }
  function addBtab(url){
    var id='bt'+Date.now()+Math.random().toString(36).slice(2,5);
    var t={id:id,label:'New Tab',url:'',hist:[],histIdx:-1,frame:_mkFrame(),mode:'home'};
    _btabs.push(t);switchBtab(id);if(url)navigate(url);return t;
  }
  function switchBtab(id){
    _btabs.forEach(function(t){if(t.frame)t.frame.style.display='none';});
    _act=_btabs.find(function(t){return t.id===id;})||(_btabs.length?_btabs[0]:null);
    if(!_act)return;
    urlInput.value=_act.url||'';
    if(_act.mode==='home')showHome();
    else if(_act.mode==='blocked'){blockedMsg.style.display='flex';homePage.style.display='none';}
    else showFrame();
    renderInnerTabs();updateBmBtn();
  }
  function closeBtab(id){
    var idx=_btabs.findIndex(function(t){return t.id===id;});if(idx<0)return;
    frameWrap.removeChild(_btabs[idx].frame);var wasActive=_act&&_act.id===id;_btabs.splice(idx,1);
    if(_btabs.length===0){addBtab();return;}
    if(wasActive)switchBtab(_btabs[Math.min(idx,_btabs.length-1)].id);else renderInnerTabs();
  }

  // Navigate
  function navigate(rawUrl,pushHistory){
    if(!_act)return;
    var url=(rawUrl||'').trim();if(!url){showHome();return;}
    if(!url.match(/^https?:\/\//i)){
      if(url.indexOf('.')>0&&url.indexOf(' ')===-1)url='https://'+url;
      else url='https://lite.duckduckgo.com/lite/?q='+encodeURIComponent(url);
    }
    var ytV=url.match(/(?:youtube\.com\/watch\?(?:.*&)?v=|youtu\.be\/)([a-zA-Z0-9_\-]{11})/);
    if(ytV){urlInput.value=url;_act.url=url;_act.label='YouTube';_pushNav(url,pushHistory);_act.frame.src='https://www.youtube-nocookie.com/embed/'+ytV[1]+'?autoplay=0&rel=0';_act.mode='frame';showFrame();finishProgress();updateBmBtn();renderInnerTabs();return;}
    if(/youtube\.com\/?($|\?|\/results|\/feed)/i.test(url)){
      urlInput.value=url;_act.url=url;_act.label='YouTube';_pushNav(url,pushHistory);
      var q2=(url.match(/search_query=([^&]+)/)||[])[1];
      showBlocked('\u25B6','YouTube','YouTube blocks embedding. Paste a video URL (youtube.com/watch?v=...) to play it directly.','https://www.youtube.com'+(q2?'/results?search_query='+q2:''));renderInnerTabs();return;
    }
    var gQ=url.match(/google\.com\/(search\?(?:.*&)?q=([^&\s]+)|[^\/]*$)/);
    if(gQ){var q3=gQ[2]||'';url=q3?'https://lite.duckduckgo.com/lite/?q='+q3:'https://lite.duckduckgo.com/lite/';}
    var ddgQ=url.match(/duckduckgo\.com\/?\?(?:.*&)?q=([^&]+)/);if(ddgQ)url='https://lite.duckduckgo.com/lite/?q='+ddgQ[1];
    if(/^https?:\/\/(www\.)?(twitter\.com|x\.com|facebook\.com|instagram\.com|tiktok\.com|accounts\.google)/i.test(url)){
      urlInput.value=url;_act.url=url;_pushNav(url,pushHistory);showBlocked('🔒','Login required','This site requires a login and blocks embedding.',url);renderInnerTabs();return;
    }
    urlInput.value=url;_act.url=url;_pushNav(url,pushHistory);updateBmBtn();
    try{_act.label=new URL(url).hostname.replace(/^www\./,'');}catch(ex){_act.label='Tab';}
    // VPN off: show helpful overlay instead of letting browser fire X-Frame-Options error
    if(!_vpnOn){
      showBlocked('🌐','Direct Mode','Most websites block iframe embedding (X-Frame-Options). Enable the VPN to route through the proxy \u2014 that bypasses the block.',url);
      var _vBtn=document.createElement('button');_vBtn.innerHTML='🛡 Enable VPN &amp; Load';
      _vBtn.style.cssText='padding:9px 18px;background:rgba(34,197,94,0.2);color:#22c55e;border:1px solid rgba(34,197,94,0.4);border-radius:8px;cursor:pointer;font-size:13px;font-weight:700;';
      _vBtn.addEventListener('click',function(){_vpnOn=true;updateVpnBtn();navigate(url);});
      var _bRow=blockedMsg.querySelector('div');if(_bRow){var _br2=_bRow.lastElementChild;if(_br2)_br2.insertBefore(_vBtn,_br2.firstChild);}
      renderInnerTabs();return;
    }
    startProgress();
    var proxyUrl='/proxy?url='+encodeURIComponent(url)+'&sid='+encodeURIComponent(_sid);
    _act.frame.src=proxyUrl;
    _act.mode='frame';showFrame();
    renderInnerTabs();
    newWindowBtn.onclick=function(){window.open(url,'_blank');};
    _act.frame.onload=function(){
      finishProgress();
      // Proxy is same-origin so we can read the iframe title
      try{var t=this.contentDocument&&this.contentDocument.title;if(t&&t.trim()){_act.label=t.length>28?t.slice(0,25)+'\u2026':t.trim();renderInnerTabs();}}catch(ex){}
    };
    _act.frame.onerror=function(){showBlocked('🚫','Failed to load','The page could not be loaded through the proxy. Try opening in a new window.',url);};
  }
  function _pushNav(url,doIt){
    if(doIt===false||!_act)return;
    _act.hist=_act.hist.slice(0,_act.histIdx+1);_act.hist.push(url);_act.histIdx=_act.hist.length-1;
  }

  // Fullscreen
  fsBtn.addEventListener('click',function(){
    if(!document.fullscreenElement&&!document.webkitFullscreenElement){
      (container.requestFullscreen||container.webkitRequestFullscreen||function(){}).call(container);
      fsBtn.innerHTML='&#x2715;';
    } else {
      (document.exitFullscreen||document.webkitExitFullscreen||function(){}).call(document);
      fsBtn.innerHTML='&#x26F6;';
    }
  });
  document.addEventListener('fullscreenchange',function(){if(!document.fullscreenElement)fsBtn.innerHTML='&#x26F6;';});
  document.addEventListener('webkitfullscreenchange',function(){if(!document.webkitFullscreenElement)fsBtn.innerHTML='&#x26F6;';});

  // Event listeners
  goBtn.addEventListener('click',function(){navigate(urlInput.value);});
  homeSearchBtn.addEventListener('click',function(){navigate(homeSearchInput.value);});
  homeSearchInput.addEventListener('keydown',function(e){if(e.key==='Enter')navigate(homeSearchInput.value);e.stopPropagation();});
  urlInput.addEventListener('keydown',function(e){if(e.key==='Enter')navigate(urlInput.value);e.stopPropagation();});
  backBtn.addEventListener('click',function(){if(_act&&_act.histIdx>0){_act.histIdx--;navigate(_act.hist[_act.histIdx],false);}});
  fwdBtn.addEventListener('click',function(){if(_act&&_act.histIdx<_act.hist.length-1){_act.histIdx++;navigate(_act.hist[_act.histIdx],false);}});
  refreshBtn.addEventListener('click',function(){if(_act&&_act.url&&_act.mode==='frame'){startProgress();var s=_act.frame.src;_act.frame.src='';setTimeout(function(){_act.frame.src=s;},50);}});
  homeBtn.addEventListener('click',function(){addBtab();});
  bookmarkBtn.addEventListener('click',function(){
    if(!_act||!_act.url)return;var url=_act.url;
    var idx=_savedBm.findIndex(function(b){return b.url===url;});
    if(idx>=0)_savedBm.splice(idx,1);else{_savedBm.push({url:url,name:url.replace(/^https?:\/\//,'').split('/')[0]});}
    localStorage.setItem('browser_bookmarks',JSON.stringify(_savedBm));renderBmBar();updateBmBtn();
  });
  newWindowBtn.addEventListener('click',function(){if(_act&&_act.url)window.open(_act.url,'_blank');});

  // Keyboard shortcuts (Ctrl+T new tab, Ctrl+W close, Ctrl+L focus bar, Ctrl+R reload)
  document.addEventListener('keydown',function _bkbd(e){
    if(!container.isConnected){document.removeEventListener('keydown',_bkbd,true);return;}
    if(container.offsetParent===null)return; // hidden tab
    if(!(e.ctrlKey||e.metaKey))return;
    if(e.key==='t'){e.preventDefault();e.stopPropagation();addBtab();}
    else if(e.key==='w'){e.preventDefault();e.stopPropagation();if(_btabs.length>1)closeBtab(_act&&_act.id);}
    else if(e.key==='l'||e.key==='L'){e.preventDefault();e.stopPropagation();urlInput.focus();urlInput.select();}
    else if(e.key==='r'||e.key==='R'){
      var tag=(document.activeElement||{}).tagName||'';
      if(tag!=='INPUT'&&tag!=='TEXTAREA'){e.preventDefault();e.stopPropagation();refreshBtn.click();}
    }
  },true);

  // Init
  updateVpnBtn();renderBmBar();addBtab();renderTabBar();
}

// ── Balance / Economy Tab ────────────────────────────────────────────────────
function convertTabToBalance(tabId) {
  for(var i=0;i<tabs.length;i++){if(tabs[i].id===tabId){tabs[i].type='balance';tabs[i].label='Balance';break;}}
  renderTabBar();
  var el=document.getElementById('tabContent-'+tabId);
  el.innerHTML='';

  // ── State ─────────────────────────────────────────────────────────────────
  var S={bal:0,inv:[],eqp:{},savings:[],txns:[],idleMoney:0,idleUpgrades:{},
    idleCps:0,idleClickVal:1,activeGame:null,gambleBet:100,isGuest:false,
    shopCat:'nameplate',shopCatalog:[],idleUpgDef:[],innerTab:'dashboard',
    hiloDrawn:7};

  // ── CSS ───────────────────────────────────────────────────────────────────
  var _st=document.createElement('style');
  _st.textContent=
    '.bal-wrap{display:flex;flex-direction:column;height:100%;overflow:hidden;background:var(--bg-secondary)}'+
    '.bal-hdr{display:flex;align-items:center;justify-content:space-between;padding:14px 18px 12px;'+
      'background:linear-gradient(135deg,#1a1a2e 0%,#16213e 50%,#0f3460 100%);border-bottom:1px solid rgba(255,255,255,.07)}'+
    '.bal-hdr-left{display:flex;flex-direction:column}'+
    '.bal-label{font-size:10px;text-transform:uppercase;letter-spacing:2px;color:rgba(255,255,255,.4);margin-bottom:2px}'+
    '.bal-amount{font-size:30px;font-weight:900;background:linear-gradient(135deg,#FFD700,#FFA500);'+
      '-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-family:monospace;transition:all .3s}'+
    '.bal-guest-badge{font-size:10px;color:rgba(255,180,0,.6);margin-top:2px}'+
    '.bal-nav{display:flex;gap:3px;padding:7px 10px;background:var(--bg-tertiary);border-bottom:1px solid rgba(255,255,255,.05);overflow-x:auto;scrollbar-width:none}'+
    '.bal-nav::-webkit-scrollbar{display:none}'+
    '.bal-nav-btn{flex:0 0 auto;padding:6px 13px;border:none;border-radius:18px;font-size:12px;font-weight:700;cursor:pointer;'+
      'background:transparent;color:var(--text-muted);transition:all .2s;white-space:nowrap}'+
    '.bal-nav-btn:hover{background:rgba(255,255,255,.08);color:var(--text-primary)}'+
    '.bal-nav-btn.active{background:var(--accent);color:#fff}'+
    '.bal-content{flex:1;overflow:hidden;position:relative}'+
    '.bal-panel{position:absolute;inset:0;overflow-y:auto;padding:14px;display:none}'+
    '.bal-panel.active{display:block}'+
    // Dashboard
    '.dash-hero{text-align:center;padding:24px 16px;background:linear-gradient(135deg,rgba(79,156,249,.1),rgba(168,85,247,.1));'+
      'border-radius:16px;margin-bottom:14px;border:1px solid rgba(255,255,255,.07)}'+
    '.dash-big-bal{font-size:52px;font-weight:900;background:linear-gradient(135deg,#FFD700,#FFA500,#FF6B6B);'+
      '-webkit-background-clip:text;-webkit-text-fill-color:transparent;font-family:monospace;line-height:1.1}'+
    '.dash-bal-sub{font-size:11px;color:rgba(255,255,255,.35);margin-top:6px}'+
    '.dash-stats{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-bottom:14px}'+
    '.dash-stat{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:12px;'+
      'padding:13px;text-align:center;transition:background .2s;cursor:default}'+
    '.dash-stat:hover{background:rgba(255,255,255,.08)}'+
    '.ds-emoji{font-size:20px;margin-bottom:3px}'+
    '.ds-val{font-size:15px;font-weight:800;color:var(--text-primary);font-family:monospace}'+
    '.ds-lbl{font-size:9px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;margin-top:1px}'+
    '.dash-actions{display:grid;grid-template-columns:repeat(2,1fr);gap:7px;margin-bottom:14px}'+
    '.dash-act-btn{padding:9px 12px;background:rgba(79,156,249,.12);border:1px solid rgba(79,156,249,.25);'+
      'border-radius:10px;color:#4f9cf9;font-size:12px;font-weight:700;cursor:pointer;transition:all .2s}'+
    '.dash-act-btn:hover{background:rgba(79,156,249,.25);transform:translateY(-1px)}'+
    '.sec-title{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted);margin-bottom:7px}'+
    '.dash-tx-list{display:flex;flex-direction:column;gap:3px}'+
    '.dash-tx-row{display:flex;justify-content:space-between;align-items:center;padding:7px 11px;'+
      'background:rgba(255,255,255,.03);border-radius:8px;font-size:12px}'+
    '.dash-tx-row:hover{background:rgba(255,255,255,.06)}'+
    '.tx-reason{color:var(--text-secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;margin-right:8px}'+
    '.tx-amt{font-weight:800;font-family:monospace;flex-shrink:0}'+
    '.tx-pos{color:#22c55e}.tx-neg{color:#ef4444}'+
    '.bal-empty{text-align:center;color:var(--text-muted);padding:28px;font-size:13px;line-height:2}'+
    // Shop
    '.shop-cats{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:12px}'+
    '.shop-cat-btn{padding:5px 11px;border:1px solid rgba(255,255,255,.1);border-radius:14px;background:transparent;'+
      'color:var(--text-muted);font-size:11px;font-weight:700;cursor:pointer;transition:all .2s;white-space:nowrap}'+
    '.shop-cat-btn:hover{background:rgba(255,255,255,.08);color:var(--text-primary)}'+
    '.shop-cat-btn.active{background:var(--accent);border-color:var(--accent);color:#fff}'+
    '.shop-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:9px}'+
    '.shop-card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:14px;'+
      'padding:13px 10px;display:flex;flex-direction:column;gap:5px;transition:all .2s;cursor:default}'+
    '.shop-card:hover{background:rgba(255,255,255,.08);transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,0,0,.3)}'+
    '.shop-card.owned{border-color:rgba(34,197,94,.4);background:rgba(34,197,94,.05)}'+
    '.shop-card.equipped{border-color:rgba(79,156,249,.55);box-shadow:0 0 10px rgba(79,156,249,.2)}'+
    '.sc-emoji{font-size:26px;text-align:center}'+
    '.sc-name{font-size:12px;font-weight:800;color:var(--text-primary);text-align:center}'+
    '.sc-rarity{font-size:9px;font-weight:900;text-align:center;letter-spacing:.8px}'+
    '.sc-desc{font-size:10px;color:var(--text-muted);text-align:center;line-height:1.4}'+
    '.sc-price{font-size:13px;font-weight:900;color:var(--accent);text-align:center;font-family:monospace}'+
    '.sc-btn{width:100%;padding:6px;border:none;border-radius:8px;font-size:11px;font-weight:800;cursor:pointer;'+
      'background:var(--accent);color:#fff;transition:all .2s;margin-top:auto}'+
    '.sc-btn:hover:not(:disabled){opacity:.85}'+
    '.sc-btn.eqp-btn{background:rgba(79,156,249,.15);color:#4f9cf9;border:1px solid rgba(79,156,249,.4)}'+
    '.sc-btn.no-afford{background:rgba(255,255,255,.07);color:var(--text-muted);cursor:not-allowed}'+
    // Savings
    '.sav-create{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:14px;padding:14px;margin-bottom:13px}'+
    '.sav-create-title{font-size:13px;font-weight:800;color:var(--text-primary);margin-bottom:9px}'+
    '.sav-in{width:100%;padding:7px 11px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);'+
      'border-radius:8px;color:var(--text-primary);font-size:13px;box-sizing:border-box;margin-bottom:5px}'+
    '.sav-in::placeholder{color:var(--text-muted)}'+
    '.sav-create-btn{width:100%;padding:8px;background:var(--accent);border:none;border-radius:8px;'+
      'color:#fff;font-size:12px;font-weight:800;cursor:pointer;margin-top:5px;transition:all .2s}'+
    '.sav-create-btn:hover{opacity:.85}'+
    '.sav-plan{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.07);border-radius:14px;padding:13px;margin-bottom:9px}'+
    '.sav-plan-hdr{display:flex;justify-content:space-between;align-items:center;margin-bottom:7px}'+
    '.sav-plan-name{font-size:14px;font-weight:800;color:var(--text-primary)}'+
    '.sav-plan-amts{font-size:11px;color:var(--text-muted);font-family:monospace}'+
    '.sav-bar{height:7px;background:rgba(255,255,255,.08);border-radius:4px;overflow:hidden;margin-bottom:3px}'+
    '.sav-fill{height:100%;border-radius:4px;transition:width .4s ease}'+
    '.sav-pct{font-size:10px;color:var(--text-muted);margin-bottom:8px}'+
    '.sav-btns{display:flex;gap:5px;align-items:center;flex-wrap:wrap}'+
    '.sav-amt-in{flex:1;min-width:70px;padding:5px 9px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);border-radius:7px;color:var(--text-primary);font-size:12px}'+
    '.sav-btn{padding:5px 11px;border:none;border-radius:7px;font-size:11px;font-weight:800;cursor:pointer;transition:all .2s}'+
    '.sav-dep{background:rgba(34,197,94,.18);color:#22c55e;border:1px solid rgba(34,197,94,.3)}'+
    '.sav-dep:hover{background:rgba(34,197,94,.32)}'+
    '.sav-wd{background:rgba(251,191,36,.18);color:#fbbf24;border:1px solid rgba(251,191,36,.3)}'+
    '.sav-wd:hover{background:rgba(251,191,36,.32)}'+
    '.sav-del{background:rgba(239,68,68,.18);color:#ef4444;border:1px solid rgba(239,68,68,.3)}'+
    '.sav-del:hover{background:rgba(239,68,68,.32)}'+
    // Gambling
    '.gam-title{font-size:22px;font-weight:900;text-align:center;margin-bottom:16px;'+
      'background:linear-gradient(135deg,#FFD700,#FF6B6B);-webkit-background-clip:text;-webkit-text-fill-color:transparent}'+
    '.gam-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(145px,1fr));gap:9px;margin-bottom:14px}'+
    '.gam-card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.09);border-radius:16px;'+
      'padding:18px 12px;text-align:center;cursor:pointer;transition:all .25s}'+
    '.gam-card:hover{background:rgba(255,255,255,.1);transform:translateY(-3px);box-shadow:0 12px 32px rgba(0,0,0,.4)}'+
    '.gam-card-emoji{font-size:38px;margin-bottom:7px}'+
    '.gam-card-name{font-size:14px;font-weight:900;color:var(--text-primary);margin-bottom:4px}'+
    '.gam-card-desc{font-size:11px;color:var(--text-muted)}'+
    '.gam-back{padding:6px 13px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.1);'+
      'border-radius:8px;color:var(--text-muted);font-size:12px;cursor:pointer}'+
    '.gam-back:hover{background:rgba(255,255,255,.13)}'+
    '.gam-hdr{display:flex;align-items:center;gap:11px;margin-bottom:13px}'+
    '.gam-hdr-title{font-size:17px;font-weight:900;color:var(--text-primary)}'+
    '.gam-arena{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.06);border-radius:16px;padding:15px}'+
    '.gam-bet-row{display:flex;flex-direction:column;gap:5px;margin-bottom:12px}'+
    '.gam-bet-row label{font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:1px;color:var(--text-muted)}'+
    '.gam-bet-in{padding:8px 11px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);'+
      'border-radius:8px;color:var(--text-primary);font-size:15px;font-weight:800;font-family:monospace;width:100%;box-sizing:border-box}'+
    '.gam-quick{display:flex;gap:5px;flex-wrap:wrap}'+
    '.gam-qbtn{padding:4px 9px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.1);'+
      'border-radius:6px;color:var(--text-secondary);font-size:11px;font-weight:700;cursor:pointer;transition:all .2s}'+
    '.gam-qbtn:hover{background:rgba(255,255,255,.13);color:var(--text-primary)}'+
    '.gam-result{min-height:70px;display:flex;flex-direction:column;align-items:center;justify-content:center;'+
      'gap:6px;padding:12px;border-radius:12px;margin-bottom:10px;font-size:30px;transition:all .3s}'+
    '.gam-result.win{background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.35)}'+
    '.gam-result.lose{background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.35)}'+
    '.gam-result.push{background:rgba(251,191,36,.1);border:1px solid rgba(251,191,36,.35)}'+
    '.gam-result.idle2{background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07)}'+
    '.gam-result-lbl{font-size:13px;font-weight:800}'+
    '.gam-result-amt{font-size:15px;font-weight:900;font-family:monospace}'+
    '.coin-choices{display:flex;gap:9px;margin-bottom:10px}'+
    '.coin-btn{flex:1;padding:12px;background:rgba(79,156,249,.13);border:1px solid rgba(79,156,249,.28);'+
      'border-radius:12px;color:#4f9cf9;font-size:14px;font-weight:800;cursor:pointer;transition:all .2s}'+
    '.coin-btn:hover:not(:disabled){background:rgba(79,156,249,.28)}'+
    '.coin-btn:disabled{opacity:.38;cursor:not-allowed}'+
    '.dice-area{display:flex;justify-content:center;gap:20px;padding:14px;font-size:64px}'+
    '.dice-roll-btn,.slots-spin-btn,.hilo-play-btn{width:100%;padding:11px;background:linear-gradient(135deg,#4f9cf9,#a855f7);'+
      'border:none;border-radius:12px;color:#fff;font-size:14px;font-weight:900;cursor:pointer;transition:all .2s;margin-bottom:9px}'+
    '.dice-roll-btn:hover:not(:disabled),.slots-spin-btn:hover:not(:disabled),.hilo-play-btn:hover:not(:disabled){opacity:.85;transform:translateY(-1px)}'+
    '.dice-roll-btn:disabled,.slots-spin-btn:disabled,.hilo-play-btn:disabled{opacity:.38;cursor:not-allowed}'+
    '.slots-reels{display:flex;justify-content:center;gap:7px;padding:12px 0}'+
    '.slot-reel{width:68px;height:68px;background:rgba(255,255,255,.06);border:2px solid rgba(255,255,255,.14);'+
      'border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:38px;transition:all .3s}'+
    '.roul-choices{display:grid;grid-template-columns:1fr 1fr 1fr;gap:7px;margin-bottom:10px}'+
    '.roul-btn{padding:13px 6px;border:none;border-radius:12px;font-size:13px;font-weight:900;cursor:pointer;transition:all .2s}'+
    '.roul-btn:hover:not(:disabled){opacity:.82;transform:translateY(-1px)}'+
    '.roul-btn:disabled{opacity:.38;cursor:not-allowed}'+
    '.hilo-card-area{display:flex;justify-content:center;align-items:center;gap:20px;padding:10px}'+
    '.hilo-card{width:60px;height:86px;background:rgba(255,255,255,.1);border:2px solid rgba(255,255,255,.2);'+
      'border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:22px;font-weight:900;color:var(--text-primary)}'+
    '.hilo-choices{display:flex;gap:9px;margin-bottom:10px}'+
    '.hilo-btn{flex:1;padding:11px;border:none;border-radius:12px;font-size:13px;font-weight:900;cursor:pointer;transition:all .2s}'+
    '.hilo-btn:hover:not(:disabled){opacity:.85}'+
    '.hilo-btn:disabled{opacity:.38;cursor:not-allowed}'+
    // Idle
    '.idle-top{text-align:center;margin-bottom:10px;padding:14px;background:rgba(255,255,255,.04);'+
      'border-radius:14px;border:1px solid rgba(255,255,255,.07)}'+
    '.idle-money-val{font-size:38px;font-weight:900;font-family:monospace;'+
      'background:linear-gradient(135deg,#FFD700,#FFA500);-webkit-background-clip:text;-webkit-text-fill-color:transparent}'+
    '.idle-cps-row{font-size:11px;color:var(--text-muted);margin-top:3px}'+
    '.idle-click-wrap{display:flex;justify-content:center;margin-bottom:10px}'+
    '.idle-coin{width:110px;height:110px;background:radial-gradient(circle at 35% 35%,#FFD700,#B8860B);'+
      'border:none;border-radius:50%;font-size:52px;cursor:pointer;transition:all .15s;'+
      'box-shadow:0 8px 28px rgba(255,215,0,.3);display:flex;align-items:center;justify-content:center}'+
    '.idle-coin:hover{transform:scale(1.07);box-shadow:0 12px 38px rgba(255,215,0,.5)}'+
    '.idle-coin:active{transform:scale(0.93)}'+
    '.idle-collect-btn{width:100%;padding:9px;background:linear-gradient(135deg,#22c55e,#16a34a);'+
      'border:none;border-radius:11px;color:#fff;font-size:13px;font-weight:800;cursor:pointer;margin-bottom:12px;transition:all .2s}'+
    '.idle-collect-btn:hover{opacity:.85}'+
    '.idle-upg-list{display:flex;flex-direction:column;gap:6px}'+
    '.idle-upg{display:flex;align-items:center;gap:9px;padding:11px;background:rgba(255,255,255,.04);'+
      'border:1px solid rgba(255,255,255,.06);border-radius:12px;transition:background .2s}'+
    '.idle-upg:hover{background:rgba(255,255,255,.07)}'+
    '.idle-upg-ico{font-size:22px;flex-shrink:0}'+
    '.idle-upg-body{flex:1;min-width:0}'+
    '.idle-upg-name{font-size:12px;font-weight:800;color:var(--text-primary)}'+
    '.idle-upg-desc{font-size:10px;color:var(--text-muted)}'+
    '.idle-upg-cnt{font-size:9px;color:var(--accent);font-weight:800;margin-top:1px}'+
    '.idle-upg-buy{flex-shrink:0;padding:7px 11px;background:rgba(79,156,249,.15);border:1px solid rgba(79,156,249,.3);'+
      'border-radius:8px;color:#4f9cf9;font-size:11px;font-weight:800;cursor:pointer;white-space:nowrap;transition:all .2s}'+
    '.idle-upg-buy:hover:not(:disabled){background:rgba(79,156,249,.3)}'+
    '.idle-upg-buy:disabled{opacity:.38;cursor:not-allowed}'+
    '@keyframes balPop{0%{transform:scale(0.95)}50%{transform:scale(1.04)}100%{transform:scale(1)}}';
  el.appendChild(_st);

  // ── Outer structure ────────────────────────────────────────────────────────
  var wrap=document.createElement('div');
  wrap.className='bal-wrap';
  el.appendChild(wrap);

  // Header
  var hdr=document.createElement('div');hdr.className='bal-hdr';
  var hdrL=document.createElement('div');hdrL.className='bal-hdr-left';
  var balLbl=document.createElement('div');balLbl.className='bal-label';balLbl.textContent='Your Balance';
  var balAmt=document.createElement('div');balAmt.className='bal-amount';balAmt.id='bal-amount-'+tabId;balAmt.textContent='$0';
  var guestBadge=document.createElement('div');guestBadge.className='bal-guest-badge';guestBadge.id='bal-gbadge-'+tabId;
  hdrL.appendChild(balLbl);hdrL.appendChild(balAmt);hdrL.appendChild(guestBadge);hdr.appendChild(hdrL);
  wrap.appendChild(hdr);

  // Nav
  var nav=document.createElement('div');nav.className='bal-nav';
  var _navTabs=[['dashboard','📈 Overview'],['shop','🛑 Shop'],['savings','🏦 Savings'],['gamble','🎰 Gamble'],['idle','\u26A1 Idle']];
  var navBtns={};
  _navTabs.forEach(function(t){
    var b=document.createElement('button');b.className='bal-nav-btn'+(t[0]==='dashboard'?' active':'');
    b.dataset.tab=t[0];b.textContent=t[1];
    b.addEventListener('click',function(){switchInner(t[0]);});
    nav.appendChild(b);navBtns[t[0]]=b;
  });
  wrap.appendChild(nav);

  // Content
  var content=document.createElement('div');content.className='bal-content';
  wrap.appendChild(content);
  var panels={};
  ['dashboard','shop','savings','gamble','idle'].forEach(function(t){
    var p=document.createElement('div');p.className='bal-panel'+(t==='dashboard'?' active':'');p.id='bpan-'+tabId+'-'+t;
    content.appendChild(p);panels[t]=p;
  });

  // ── Helpers ────────────────────────────────────────────────────────────────
  function fmtBal(n){return '$'+Math.floor(n).toLocaleString();}
  function fmtIdleMoney(n){
    if(n>=1e9) return '$'+n.toExponential(2);
    if(n>=1e6) return '$'+(n/1e6).toFixed(2)+'M';
    if(n>=1e3) return '$'+(n/1e3).toFixed(1)+'K';
    return '$'+n.toFixed(1);
  }
  function rarityColor(r){return{common:'#9CA3AF',uncommon:'#22c55e',rare:'#3b82f6',epic:'#a855f7',legendary:'#f59e0b',mythic:'#ef4444'}[r]||'#9CA3AF';}
  function updateBalDisplay(){
    var a=document.getElementById('bal-amount-'+tabId);
    if(a){a.textContent=fmtBal(S.bal);}
    var g=document.getElementById('bal-gbadge-'+tabId);
    if(g){g.textContent=S.isGuest?'\u26A0\uFE0F Guest \u2014 balance resets on disconnect':'';}
  }
  function _recalcIdle(){
    S.idleClickVal=1;S.idleCps=0;
    S.idleUpgDef.forEach(function(u){
      var cnt=(S.idleUpgrades[u.id]||0);
      if(u.type==='click') S.idleClickVal+=u.value*cnt;
      else if(u.type==='cps') S.idleCps+=u.value*cnt;
    });
  }
  function switchInner(tab){
    S.innerTab=tab;
    Object.keys(panels).forEach(function(k){panels[k].classList.toggle('active',k===tab);});
    Object.keys(navBtns).forEach(function(k){navBtns[k].classList.toggle('active',k===tab);});
    if(tab==='dashboard') renderDashboard();
    else if(tab==='shop') renderShop();
    else if(tab==='savings') renderSavings();
    else if(tab==='gamble') renderGamble();
    else if(tab==='idle') renderIdle();
  }

  // ── Dashboard ─────────────────────────────────────────────────────────────
  function renderDashboard(){
    var p=panels['dashboard'];p.innerHTML='';
    var hero=document.createElement('div');hero.className='dash-hero';
    hero.innerHTML='<div style="font-size:10px;text-transform:uppercase;letter-spacing:2px;color:rgba(255,255,255,.35);margin-bottom:5px">Your Balance</div>'+
      '<div class="dash-big-bal" id="dash-big-'+tabId+'">'+fmtBal(S.bal)+'</div>'+
      '<div class="dash-bal-sub">'+(S.isGuest?'\u26A0\uFE0F Guest account \u2014 balance resets on disconnect':'✅ Registered \u2014 balance saved permanently')+'</div>';
    p.appendChild(hero);
    var statsWrap=document.createElement('div');statsWrap.className='dash-stats';
    var totalSaved=S.savings.reduce(function(a,s){return a+s.saved;},0);
    [['💰','Balance',fmtBal(S.bal)],['🛍️','Items Owned',S.inv.length+' items'],['🏦','In Savings',fmtBal(totalSaved)],['⚡','Idle Earnings',fmtIdleMoney(S.idleMoney)]].forEach(function(s){
      var c=document.createElement('div');c.className='dash-stat';
      c.innerHTML='<div class="ds-emoji">'+s[0]+'</div><div class="ds-val">'+s[2]+'</div><div class="ds-lbl">'+s[1]+'</div>';
      statsWrap.appendChild(c);
    });
    p.appendChild(statsWrap);
    var actWrap=document.createElement('div');actWrap.className='dash-actions';
    [['🛍️ Visit Shop','shop'],['🏦 Savings','savings'],['🎰 Gamble','gamble'],['⚡ Idle Game','idle']].forEach(function(a){
      var b=document.createElement('button');b.className='dash-act-btn';b.textContent=a[0];
      b.addEventListener('click',function(){switchInner(a[1]);});actWrap.appendChild(b);
    });
    p.appendChild(actWrap);
    var t=document.createElement('div');t.className='sec-title';t.textContent='Recent Transactions';p.appendChild(t);
    var txList=document.createElement('div');txList.className='dash-tx-list';
    if(!S.txns.length){txList.innerHTML='<div class="bal-empty">💸<br>No transactions yet.<br><span style="font-size:11px">Go spend some money!</span></div>';}
    else{S.txns.forEach(function(tx){
      var r=document.createElement('div');r.className='dash-tx-row';
      r.innerHTML='<span class="tx-reason">'+escapeHtml(tx.reason)+'</span>'+
        '<span class="tx-amt '+(tx.amount>=0?'tx-pos':'tx-neg')+'">'+(tx.amount>=0?'+':'')+fmtBal(tx.amount)+'</span>';
      txList.appendChild(r);
    });}
    p.appendChild(txList);
  }

  // ── Shop ──────────────────────────────────────────────────────────────────
  var SHOP_CATS=[
    {id:'nameplate',name:'Nameplates',emoji:'🏷️'},{id:'font',name:'Fonts',emoji:'✍️'},
    {id:'ring',name:'Avatar Rings',emoji:'💫'},{id:'effect',name:'Profile FX',emoji:'✨'},
    {id:'theme',name:'Themes',emoji:'🎨'},{id:'title',name:'Titles',emoji:'🏆'},
    {id:'bubble',name:'Chat Bubbles',emoji:'💬'},{id:'message',name:'Msg Effects',emoji:'⚡'}
  ];
  function renderShop(){
    var p=panels['shop'];p.innerHTML='';
    var catBar=document.createElement('div');catBar.className='shop-cats';
    SHOP_CATS.forEach(function(cat){
      var b=document.createElement('button');b.className='shop-cat-btn'+(S.shopCat===cat.id?' active':'');
      b.textContent=cat.emoji+' '+cat.name;
      b.addEventListener('click',function(){S.shopCat=cat.id;renderShop();});
      catBar.appendChild(b);
    });
    p.appendChild(catBar);
    if(!S.shopCatalog.length){p.innerHTML+='<div class="bal-empty">Loading shop...</div>';return;}
    var grid=document.createElement('div');grid.className='shop-grid';
    var items=S.shopCatalog.filter(function(i){return i.cat===S.shopCat;});
    if(!items.length){p.appendChild(document.createElement('div')).className='bal-empty';p.lastChild.textContent='No items in this category yet.';}
    items.forEach(function(item){
      var owned=S.inv.indexOf(item.id)!==-1;
      var equipped=S.eqp[item.cat]===item.id;
      var canAfford=S.bal>=item.price;
      var card=document.createElement('div');card.className='shop-card'+(owned?' owned':'')+(equipped?' equipped':'');
      var rc=rarityColor(item.rarity);
      card.innerHTML='<div class="sc-emoji">'+escapeHtml(item.emoji)+'</div>'+
        '<div class="sc-name">'+escapeHtml(item.name)+'</div>'+
        '<div class="sc-rarity" style="color:'+rc+'">'+item.rarity.toUpperCase()+'</div>'+
        '<div class="sc-desc">'+escapeHtml(item.desc)+'</div>'+
        '<div class="sc-price">'+(owned?'✅ Owned':fmtBal(item.price))+'</div>';
      var btn=document.createElement('button');btn.className='sc-btn';
      if(owned){btn.classList.add('eqp-btn');btn.textContent=equipped?'✓ Equipped':'Equip';}
      else{btn.textContent=canAfford?'Buy':'Need '+fmtBal(item.price-S.bal)+' more';if(!canAfford)btn.classList.add('no-afford');}
      btn.disabled=!owned&&!canAfford;
      btn.addEventListener('click',(function(iid,icat,isOwned){return function(){
        if(!ws||ws.readyState!==1){showToast('Not connected','error');return;}
        if(isOwned) ws.send(JSON.stringify({type:'shop_equip',item_id:iid,category:icat}));
        else ws.send(JSON.stringify({type:'shop_buy',item_id:iid}));
      };})(item.id,item.cat,owned));
      card.appendChild(btn);grid.appendChild(card);
    });
    p.appendChild(grid);
  }

  // ── Savings ───────────────────────────────────────────────────────────────
  function renderSavings(){
    var p=panels['savings'];p.innerHTML='';
    var form=document.createElement('div');form.className='sav-create';
    form.innerHTML='<div class="sav-create-title">+ New Savings Plan</div>';
    var nameIn=document.createElement('input');nameIn.type='text';nameIn.placeholder='Plan name (e.g. New PC)';nameIn.maxLength=50;nameIn.className='sav-in';
    var goalIn=document.createElement('input');goalIn.type='number';goalIn.placeholder='Goal amount ($)';goalIn.min=1;goalIn.className='sav-in';
    var crow=document.createElement('div');crow.style.cssText='display:flex;gap:7px;align-items:center;margin-bottom:4px;';
    var clbl=document.createElement('span');clbl.style.cssText='font-size:11px;color:var(--text-muted);';clbl.textContent='Color:';
    var colorIn=document.createElement('input');colorIn.type='color';colorIn.value='#4f9cf9';colorIn.style.cssText='height:30px;width:44px;border:none;border-radius:6px;cursor:pointer;padding:0;';
    crow.appendChild(clbl);crow.appendChild(colorIn);
    var createBtn=document.createElement('button');createBtn.className='sav-create-btn';createBtn.textContent='+ Create Plan';
    createBtn.addEventListener('click',function(){
      var n=nameIn.value.trim(),g=parseInt(goalIn.value),c=colorIn.value;
      if(!n){showToast('Enter a plan name','error');return;}
      if(!g||g<1){showToast('Enter a valid goal amount','error');return;}
      if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'savings_create',name:n,goal:g,color:c}));
      nameIn.value='';goalIn.value='';
    });
    form.appendChild(nameIn);form.appendChild(goalIn);form.appendChild(crow);form.appendChild(createBtn);p.appendChild(form);
    if(!S.savings.length){var em=document.createElement('div');em.className='bal-empty';em.innerHTML='🏦<br>No savings plans yet.<br><span style="font-size:11px;color:var(--text-muted)">Create one above to start saving!</span>';p.appendChild(em);return;}
    S.savings.forEach(function(plan){
      var pct=plan.goal>0?Math.min(100,Math.round(plan.saved/plan.goal*100)):0;
      var card=document.createElement('div');card.className='sav-plan';
      card.innerHTML='<div class="sav-plan-hdr"><div class="sav-plan-name">'+escapeHtml(plan.name)+'</div>'+
        '<div class="sav-plan-amts">'+fmtBal(plan.saved)+' / '+fmtBal(plan.goal)+'</div></div>'+
        '<div class="sav-bar"><div class="sav-fill" style="width:'+pct+'%;background:'+plan.color+'"></div></div>'+
        '<div class="sav-pct">'+pct+'% complete'+(pct>=100?' 🎉':'')+'</div>';
      var brow=document.createElement('div');brow.className='sav-btns';
      var amtIn=document.createElement('input');amtIn.type='number';amtIn.placeholder='Amount';amtIn.min=1;amtIn.className='sav-amt-in';
      var dep=document.createElement('button');dep.className='sav-btn sav-dep';dep.textContent='Deposit';
      dep.addEventListener('click',(function(pid,inp){return function(){
        var a=parseInt(inp.value);if(!a||a<1){showToast('Enter amount','error');return;}
        if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'savings_deposit',plan_id:pid,amount:a}));
        inp.value='';
      };})(plan.id,amtIn));
      var wd=document.createElement('button');wd.className='sav-btn sav-wd';wd.textContent='Withdraw';
      wd.addEventListener('click',(function(pid,inp){return function(){
        var a=parseInt(inp.value);if(!a||a<1){showToast('Enter amount','error');return;}
        if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'savings_withdraw',plan_id:pid,amount:a}));
        inp.value='';
      };})(plan.id,amtIn));
      var del=document.createElement('button');del.className='sav-btn sav-del';del.textContent='🗑 Delete';
      del.addEventListener('click',(function(pid){return function(){
        if(confirm('Delete this plan? Saved amount will be returned to your balance.'))
          if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'savings_delete',plan_id:pid}));
      };})(plan.id));
      brow.appendChild(amtIn);brow.appendChild(dep);brow.appendChild(wd);brow.appendChild(del);
      card.appendChild(brow);p.appendChild(card);
    });
  }

  // ── Gambling ──────────────────────────────────────────────────────────────
  var GAMES=[
    {id:'coinflip',name:'Coin Flip',emoji:'🪙',desc:'Call heads or tails \u2014 double or nothing!'},
    {id:'dice',name:'Dice Duel',emoji:'🎲',desc:'Roll higher than the dealer to win!'},
    {id:'slots',name:'Slot Machine',emoji:'🎰',desc:'Match 3 symbols for big wins!'},
    {id:'roulette',name:'Roulette',emoji:'🔴',desc:'Red, Black, or Green \u2014 spin the wheel!'},
    {id:'hilo',name:'Hi-Lo Cards',emoji:'🃏',desc:'Guess if the next card is higher or lower!'},
  ];
  var SLOT_EMOJI={cherry:'🍒',lemon:'🍋',orange:'🍊',grape:'🍇',diamond:'💎',seven:'7️⃣'};
  function renderGamble(){
    var p=panels['gamble'];p.innerHTML='';
    if(!S.activeGame){
      var title=document.createElement('div');title.className='gam-title';title.textContent='🎰 Choose Your Game';p.appendChild(title);
      var grid=document.createElement('div');grid.className='gam-grid';
      GAMES.forEach(function(g){
        var c=document.createElement('div');c.className='gam-card';
        c.innerHTML='<div class="gam-card-emoji">'+g.emoji+'</div><div class="gam-card-name">'+g.name+'</div><div class="gam-card-desc">'+g.desc+'</div>';
        c.addEventListener('click',function(){S.activeGame=g.id;renderGamble();});
        grid.appendChild(c);
      });
      p.appendChild(grid);
    } else {
      var gInfo=GAMES.find(function(g){return g.id===S.activeGame;});
      var hdr=document.createElement('div');hdr.className='gam-hdr';
      var backBtn=document.createElement('button');backBtn.className='gam-back';backBtn.textContent='\u2190 Back';
      backBtn.addEventListener('click',function(){S.activeGame=null;renderGamble();});
      var hTitle=document.createElement('div');hTitle.className='gam-hdr-title';hTitle.textContent=gInfo.emoji+' '+gInfo.name;
      hdr.appendChild(backBtn);hdr.appendChild(hTitle);p.appendChild(hdr);
      var arena=document.createElement('div');arena.className='gam-arena';p.appendChild(arena);
      // Bet row
      var betRow=document.createElement('div');betRow.className='gam-bet-row';
      var betLbl=document.createElement('label');betLbl.textContent='Bet Amount';betRow.appendChild(betLbl);
      var betIn=document.createElement('input');betIn.type='number';betIn.className='gam-bet-in';
      betIn.value=Math.min(S.gambleBet,S.bal);betIn.min=1;betIn.max=S.bal;betRow.appendChild(betIn);
      var qBets=document.createElement('div');qBets.className='gam-quick';
      [10,50,100,500,'Max'].forEach(function(v){
        var qb=document.createElement('button');qb.className='gam-qbtn';
        qb.textContent=v==='Max'?'All In':('$'+v);
        qb.addEventListener('click',function(){betIn.value=v==='Max'?S.bal:Math.min(parseInt(v),S.bal);});
        qBets.appendChild(qb);
      });
      betRow.appendChild(qBets);arena.appendChild(betRow);
      // Result area
      var resDiv=document.createElement('div');resDiv.className='gam-result idle2';resDiv.innerHTML='<div style="font-size:32px">🤞</div><div class="gam-result-lbl">Place your bet!</div>';
      arena.appendChild(resDiv);
      function showResult(win,emoji,label,amount){
        resDiv.className='gam-result '+(amount>0?'win':(amount<0?'lose':'push'));
        resDiv.innerHTML='<div style="font-size:32px">'+emoji+'</div><div class="gam-result-lbl">'+label+'</div>'+
          (amount!==null?'<div class="gam-result-amt">'+(amount>0?'+':'')+fmtBal(amount)+'</div>':'');
      }
      function getBet(){var b=parseInt(betIn.value);if(!b||b<1||b>S.bal){showToast('Invalid bet amount','error');return 0;}S.gambleBet=b;return b;}
      // Game-specific UI
      if(S.activeGame==='coinflip'){
        var coinDisp=document.createElement('div');coinDisp.style.cssText='text-align:center;font-size:72px;padding:8px;';coinDisp.textContent='🪙';arena.appendChild(coinDisp);
        var choices=document.createElement('div');choices.className='coin-choices';
        ['heads','tails'].forEach(function(c){
          var btn=document.createElement('button');btn.className='coin-btn';
          btn.textContent=c==='heads'?'🦅 Heads':'🦁 Tails';
          btn.addEventListener('click',(function(ch){return function(){
            var bet=getBet();if(!bet)return;
            choices.querySelectorAll('button').forEach(function(b){b.disabled=true;});
            coinDisp.textContent='🪙';
            if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'gamble',game:'coinflip',bet:bet,choice:ch}));
          };})(c));
          choices.appendChild(btn);
        });
        arena.appendChild(choices);
        arena.querySelector('.gam-result').remove();arena.appendChild(resDiv);
        arena._onResult=function(d){
          coinDisp.textContent=d.data.flip==='heads'?'🦅':'🦁';
          var won=d.won>0;var push=d.won===0;
          showResult(won,won?'🎉':push?'😐':'💸',won?'You Won!':push?'Push!':'You Lost!',d.won);
          choices.querySelectorAll('button').forEach(function(b){b.disabled=false;});
        };
      } else if(S.activeGame==='dice'){
        var diceArea=document.createElement('div');diceArea.className='dice-area';
        var myDie=document.createElement('span');myDie.textContent='🎲';
        var vs=document.createElement('span');vs.style.cssText='font-size:22px;align-self:center;color:var(--text-muted);';vs.textContent='vs';
        var dlDie=document.createElement('span');dlDie.textContent='🎲';
        diceArea.appendChild(myDie);diceArea.appendChild(vs);diceArea.appendChild(dlDie);arena.appendChild(diceArea);
        var rollBtn=document.createElement('button');rollBtn.className='dice-roll-btn';rollBtn.textContent='🎲 Roll Dice!';
        rollBtn.addEventListener('click',function(){
          var bet=getBet();if(!bet)return;
          rollBtn.disabled=true;
          if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'gamble',game:'dice',bet:bet}));
        });
        arena.querySelector('.gam-result').remove();arena.appendChild(rollBtn);arena.appendChild(resDiv);
        var DICE_FACES=['','⚀','⚁','⚂','⚃','⚄','⚅'];
        arena._onResult=function(d){
          myDie.textContent=DICE_FACES[d.data.my_roll]||d.data.my_roll;
          dlDie.textContent=DICE_FACES[d.data.dealer_roll]||d.data.dealer_roll;
          var won=d.won>0;var push=d.won===0;
          showResult(won,won?'🎉':push?'😐':'💸',won?'You Won!':push?'Tie \u2014 Push!':'Dealer Wins!',d.won);
          rollBtn.disabled=false;
        };
      } else if(S.activeGame==='slots'){
        var reelsDiv=document.createElement('div');reelsDiv.className='slots-reels';
        var reelEls=[];
        for(var ri=0;ri<3;ri++){
          var reel=document.createElement('div');reel.className='slot-reel';reel.textContent='🎰';reelsDiv.appendChild(reel);reelEls.push(reel);
        }
        arena.appendChild(reelsDiv);
        var spinBtn=document.createElement('button');spinBtn.className='slots-spin-btn';spinBtn.textContent='🎰 SPIN!';
        spinBtn.addEventListener('click',function(){
          var bet=getBet();if(!bet)return;
          spinBtn.disabled=true;
          reelEls.forEach(function(r){r.textContent='⏳';});
          if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'gamble',game:'slots',bet:bet}));
        });
        arena.querySelector('.gam-result').remove();arena.appendChild(spinBtn);arena.appendChild(resDiv);
        arena._onResult=function(d){
          d.data.reels.forEach(function(sym,i){reelEls[i].textContent=SLOT_EMOJI[sym]||sym;});
          var won=d.won>0;var push=d.won===0;
          var lbl=won?(d.won>=bet*7?'JACKPOT!':'You Won!'):(push?'Two of a Kind \u2014 Push!':'No Match!');
          showResult(won,won?'🎉':push?'😅':'💸',lbl,d.won);
          spinBtn.disabled=false;
        };
      } else if(S.activeGame==='roulette'){
        var roulDisp=document.createElement('div');roulDisp.style.cssText='text-align:center;font-size:48px;padding:8px;';roulDisp.textContent='🎡';arena.appendChild(roulDisp);
        var roulChoices=document.createElement('div');roulChoices.className='roul-choices';
        [['red','🔴 Red','#ef4444',17],['black','⚫ Black','#374151',17],['green','💚 Green','#16a34a',34]].forEach(function(c){
          var btn=document.createElement('button');btn.className='roul-btn';
          btn.style.cssText='background:'+c[2]+';color:#fff;';
          btn.innerHTML=c[0]==='green'?c[1]+' <small>(17x)</small>':c[1]+' <small>(2x)</small>';
          btn.addEventListener('click',(function(ch){return function(){
            var bet=getBet();if(!bet)return;
            roulChoices.querySelectorAll('button').forEach(function(b){b.disabled=true;});
            roulDisp.textContent='🎡';
            if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'gamble',game:'roulette',bet:bet,choice:ch}));
          };})(c[0]));
          roulChoices.appendChild(btn);
        });
        arena.appendChild(roulChoices);
        arena.querySelector('.gam-result').remove();arena.appendChild(resDiv);
        arena._onResult=function(d){
          var colEmoji={red:'🔴',black:'⚫',green:'💚'}[d.data.color]||'?';
          roulDisp.textContent=colEmoji+' '+d.data.number;
          var won=d.won>0;var push=d.won===0;
          showResult(won,won?'🎉':push?'😐':'💸',won?'You Won!':push?'Push!':'You Lost!',d.won);
          roulChoices.querySelectorAll('button').forEach(function(b){b.disabled=false;});
        };
      } else if(S.activeGame==='hilo'){
        S.hiloDrawn=Math.floor(Math.random()*13)+1;
        var CARD_LABELS=['','A','2','3','4','5','6','7','8','9','10','J','Q','K'];
        var hiloCardArea=document.createElement('div');hiloCardArea.className='hilo-card-area';
        var curCard=document.createElement('div');curCard.className='hilo-card';curCard.textContent=CARD_LABELS[S.hiloDrawn];
        var arrow=document.createElement('span');arrow.style.cssText='font-size:28px;color:var(--text-muted);';arrow.textContent='→';
        var nextCard=document.createElement('div');nextCard.className='hilo-card';nextCard.style.cssText='background:rgba(79,156,249,.1);border-color:rgba(79,156,249,.3);';nextCard.textContent='?';
        hiloCardArea.appendChild(curCard);hiloCardArea.appendChild(arrow);hiloCardArea.appendChild(nextCard);
        arena.appendChild(hiloCardArea);
        var hiloChoices=document.createElement('div');hiloChoices.className='hilo-choices';
        [['higher','\u2191 Higher','#22c55e'],['lower','\u2193 Lower','#ef4444']].forEach(function(c){
          var btn=document.createElement('button');btn.className='hilo-btn';
          btn.style.cssText='background:rgba(255,255,255,.06);color:'+c[2]+';border:1px solid '+c[2]+'40;';
          btn.textContent=c[1];
          btn.addEventListener('click',(function(ch){return function(){
            var bet=getBet();if(!bet)return;
            hiloChoices.querySelectorAll('button').forEach(function(b){b.disabled=true;});
            if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'gamble',game:'hilo',bet:bet,choice:ch,drawn:S.hiloDrawn}));
          };})(c[0]));
          hiloChoices.appendChild(btn);
        });
        arena.appendChild(hiloChoices);
        arena.querySelector('.gam-result').remove();arena.appendChild(resDiv);
        arena._onResult=function(d){
          nextCard.textContent=CARD_LABELS[d.data.next]||d.data.next;
          S.hiloDrawn=Math.floor(Math.random()*13)+1;
          curCard.textContent=CARD_LABELS[S.hiloDrawn];nextCard.textContent='?';
          var won=d.won>0;var push=d.won===0;
          showResult(won,won?'🎉':push?'😐':'💸',won?'You Won!':push?'Tie \u2014 Push!':'Wrong call!',d.won);
          setTimeout(function(){hiloChoices.querySelectorAll('button').forEach(function(b){b.disabled=false;});},700);
        };
        arena._onResult._resDiv=resDiv;
      }
    }
  }

  // ── Idle Game ─────────────────────────────────────────────────────────────
  var _idleTimer=null;
  var _idleDisplay=null;
  function renderIdle(){
    var p=panels['idle'];p.innerHTML='';
    _idleDisplay=null;
    var top=document.createElement('div');top.className='idle-top';
    var idleMoneyEl=document.createElement('div');idleMoneyEl.className='idle-money-val';idleMoneyEl.textContent=fmtIdleMoney(S.idleMoney);
    var idleCpsEl=document.createElement('div');idleCpsEl.className='idle-cps-row';idleCpsEl.textContent=S.idleCps>0?'+'+S.idleCps.toLocaleString()+'/s (click the coin!)':'Click the coin to earn!';
    top.appendChild(idleMoneyEl);top.appendChild(idleCpsEl);p.appendChild(top);
    _idleDisplay={money:idleMoneyEl,cps:idleCpsEl};
    var clickWrap=document.createElement('div');clickWrap.className='idle-click-wrap';
    var coinBtn=document.createElement('button');coinBtn.className='idle-coin';coinBtn.textContent='🪙';
    coinBtn.addEventListener('click',function(){
      if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'idle_click'}));
    });
    clickWrap.appendChild(coinBtn);p.appendChild(clickWrap);
    var collectBtn=document.createElement('button');collectBtn.className='idle-collect-btn';
    collectBtn.textContent=S.idleMoney>=1?('💰 Collect '+fmtIdleMoney(S.idleMoney)+' to Balance'):'No earnings to collect yet';
    collectBtn.disabled=S.idleMoney<1;
    collectBtn.addEventListener('click',function(){
      if(S.idleMoney<1){showToast('Nothing to collect yet','error');return;}
      if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'idle_collect',amount:S.idleMoney}));
    });
    p.appendChild(collectBtn);
    var upgTitle=document.createElement('div');upgTitle.className='sec-title';upgTitle.textContent='Upgrades';p.appendChild(upgTitle);
    var upgList=document.createElement('div');upgList.className='idle-upg-list';
    (S.idleUpgDef||[]).forEach(function(u){
      var cnt=S.idleUpgrades[u.id]||0;
      var price=Math.round(u.base_price*Math.pow(1.15,cnt));
      var canAfford=S.idleMoney>=price;
      var card=document.createElement('div');card.className='idle-upg';
      card.innerHTML='<div class="idle-upg-ico">'+escapeHtml(u.emoji)+'</div>'+
        '<div class="idle-upg-body"><div class="idle-upg-name">'+escapeHtml(u.name)+'</div>'+
        '<div class="idle-upg-desc">'+escapeHtml(u.desc)+'</div>'+
        (cnt>0?'<div class="idle-upg-cnt">Owned: '+cnt+'</div>':'')+'</div>';
      var buyBtn=document.createElement('button');buyBtn.className='idle-upg-buy'+(canAfford?'':' cant-afford');
      buyBtn.textContent=fmtIdleMoney(price);buyBtn.disabled=!canAfford;
      buyBtn.addEventListener('click',(function(uid){return function(){
        if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'idle_upgrade',upgrade_id:uid}));
      };})(u.id));
      card.appendChild(buyBtn);upgList.appendChild(card);
    });
    p.appendChild(upgList);
    // Start CPS ticker (client-side accumulation for display; server is source of truth for upgrades)
    if(_idleTimer) clearInterval(_idleTimer);
    _idleTimer=setInterval(function(){
      if(S.innerTab!=='idle') return;
      if(S.idleCps>0){
        S.idleMoney+=S.idleCps/10;
        if(_idleDisplay&&_idleDisplay.money){
          _idleDisplay.money.textContent=fmtIdleMoney(S.idleMoney);
          _idleDisplay.cps.textContent='+'+S.idleCps.toLocaleString()+'/s \u2014 '+fmtIdleMoney(S.idleMoney);
        }
      }
    },100);
  }

  // ── Message handler ───────────────────────────────────────────────────────
  function onMsg(e){
    var d=e.detail;
    if(d.type==='balance_data'){
      S.bal=d.balance||0;S.inv=d.inventory||[];S.eqp=d.equipped||{};
      S.savings=d.savings||[];S.txns=d.transactions||[];
      S.idleMoney=d.idle_money||0;S.idleUpgrades=d.idle_upgrades||{};
      S.isGuest=!!d.is_guest;S.shopCatalog=d.shop_catalog||[];S.idleUpgDef=d.idle_upgrades_def||[];
      _recalcIdle();updateBalDisplay();
      if(S.innerTab==='dashboard') renderDashboard();
      else if(S.innerTab==='shop') renderShop();
      else if(S.innerTab==='savings') renderSavings();
      else if(S.innerTab==='idle') renderIdle();
      else renderGamble();
    } else if(d.type==='shop_result'){
      if(d.ok){S.bal=d.balance;S.inv=d.inventory||S.inv;updateBalDisplay();renderShop();showToast('Item purchased! 🛍️','success');}
      else showToast(d.error||'Purchase failed','error');
    } else if(d.type==='equip_result'){
      if(d.ok){S.eqp=d.equipped;renderShop();showToast('Equipped!','success');}
    } else if(d.type==='savings_result'){
      if(d.ok){S.savings=d.savings||S.savings;if(d.balance!==undefined){S.bal=d.balance;updateBalDisplay();}renderSavings();}
      else showToast(d.error||'Error','error');
    } else if(d.type==='gamble_result'){
      if(d.ok){
        S.bal=d.new_balance;updateBalDisplay();
        var aEl=panels['gamble'].querySelector('.gam-arena');
        if(aEl&&aEl._onResult) aEl._onResult(d);
        else renderGamble();
        showToast(d.won>0?'You won '+fmtBal(d.won)+'!':'d.won'===0?'Push!':'You lost '+fmtBal(-d.won),d.won>0?'success':'error');
      } else showToast(d.error||'Gamble error','error');
    } else if(d.type==='idle_result'){
      if(d.ok){
        S.idleMoney=d.idle_money||S.idleMoney;
        S.idleUpgrades=d.idle_upgrades||S.idleUpgrades;
        S.idleClickVal=d.click_val||S.idleClickVal;S.idleCps=d.cps||S.idleCps;
        if(_idleDisplay&&_idleDisplay.money) _idleDisplay.money.textContent=fmtIdleMoney(S.idleMoney);
        if(S.innerTab==='idle') renderIdle();
      }
    } else if(d.type==='idle_collect_result'){
      if(d.ok){S.bal=d.balance;S.idleMoney=0;updateBalDisplay();showToast('Collected! 💰','success');if(S.innerTab==='idle') renderIdle();}
    }
  }
  document.addEventListener('_balance_msg',onMsg);

  // Cleanup when tab element removed
  var _mo=new MutationObserver(function(){
    if(!document.getElementById('tabContent-'+tabId)){
      document.removeEventListener('_balance_msg',onMsg);
      if(_idleTimer) clearInterval(_idleTimer);
      _mo.disconnect();
    }
  });
  var _tc=document.getElementById('tabContents');
  if(_tc) _mo.observe(_tc,{childList:true});

  // Initial load
  switchInner('dashboard');
  if(typeof ws!=='undefined'&&ws&&ws.readyState===1) ws.send(JSON.stringify({type:'get_balance'}));
  else setTimeout(function(){if(ws&&ws.readyState===1) ws.send(JSON.stringify({type:'get_balance'}));},800);
}

var allGames = [
  { id: 'tictactoe', name: 'Tic-Tac-Toe', desc: 'Classic strategy game, play X vs O against the computer', badge: 'single' },
  { id: 'snake', name: 'Snake', desc: 'Navigate the snake to eat food and grow without hitting walls', badge: 'single' },
  { id: 'memory', name: 'Memory Match', desc: 'Flip cards and find all matching pairs with fewest moves', badge: 'single' },
  { id: 'blackjack', name: 'Blackjack', desc: 'Beat the dealer by getting as close to 21 as possible', badge: 'single' },
  { id: 'blackjack_multi', name: 'Blackjack (Multiplayer)', desc: 'Play blackjack with friends in real-time rooms', badge: 'multi' },
  { id: 'minesweeper', name: 'Minesweeper', desc: 'Clear the minefield without detonating any hidden mines', badge: 'single' },
  { id: 'war', name: 'War', desc: 'Classic card game - flip cards and battle for the whole deck', badge: 'single' },
  { id: 'crazy_eights', name: 'Crazy Eights', desc: 'Match suits or ranks, play wild 8s to change the suit', badge: 'single' },
  { id: 'solitaire', name: 'Solitaire', desc: 'Classic Klondike solitaire card game with drag and click controls', badge: 'single' },
  { id: 'checkers', name: 'Checkers', desc: 'Play checkers against a simple AI opponent with kings and multi-jumps', badge: 'single' },
  { id: 'twenty_fortyeight', name: '2048', desc: 'Slide and merge tiles to reach the 2048 tile', badge: 'single' },
  { id: 'hangman', name: 'Hangman', desc: 'Guess the hidden word one letter at a time before the hangman is complete', badge: 'single' },
  { id: 'genetic_cars', name: 'Genetic Cars', desc: 'Watch AI-evolved cars learn to drive using genetic algorithms and natural selection', badge: 'single' },
  { id: 'garlic_phone', name: 'Garlic Phone', desc: 'Multiplayer telephone game with drawing — write a phrase, draw it, guess the drawing!', badge: 'multi' },
];

function buildGamesHub(container) {
  var hub = document.createElement('div');
  hub.className = 'games-hub';

  var header = document.createElement('div');
  header.className = 'games-header';
  header.textContent = 'Games';
  hub.appendChild(header);

  var searchDiv = document.createElement('div');
  searchDiv.className = 'games-search';
  var searchInput = document.createElement('input');
  searchInput.type = 'text';
  searchInput.placeholder = 'Search games...';
  searchInput.setAttribute('data-testid', 'input-games-search');
  searchDiv.appendChild(searchInput);
  hub.appendChild(searchDiv);

  var listDiv = document.createElement('div');
  listDiv.className = 'games-list';
  hub.appendChild(listDiv);

  function makeGameRow(g) {
    var row = document.createElement('div');
    row.className = 'game-item';
    row.setAttribute('data-testid', 'game-card-' + g.id);
    var info = document.createElement('div');
    info.className = 'game-item-info';
    var nameEl = document.createElement('div');
    nameEl.className = 'game-item-name';
    nameEl.textContent = g.name;
    info.appendChild(nameEl);
    var descEl = document.createElement('div');
    descEl.className = 'game-item-desc';
    descEl.textContent = g.desc;
    info.appendChild(descEl);
    row.appendChild(info);
    row.addEventListener('click', function() {
      showGame(container, g.id);
    });
    return row;
  }

  function renderGames(filter) {
    listDiv.innerHTML = '';
    var q = (filter || '').toLowerCase();
    var singles = allGames.filter(function(g) {
      if (g.badge !== 'single') return false;
      if (q && g.name.toLowerCase().indexOf(q) === -1 && g.desc.toLowerCase().indexOf(q) === -1) return false;
      return true;
    });
    var multis = allGames.filter(function(g) {
      if (g.badge !== 'multi') return false;
      if (q && g.name.toLowerCase().indexOf(q) === -1 && g.desc.toLowerCase().indexOf(q) === -1) return false;
      return true;
    });
    if (singles.length === 0 && multis.length === 0) {
      var empty = document.createElement('div');
      empty.className = 'newtab-empty';
      empty.textContent = 'No games found';
      listDiv.appendChild(empty);
      return;
    }
    if (singles.length > 0) {
      var sLabel = document.createElement('div');
      sLabel.className = 'newtab-section-label';
      sLabel.textContent = 'Single Player';
      listDiv.appendChild(sLabel);
      singles.forEach(function(g) { listDiv.appendChild(makeGameRow(g)); });
    }
    if (multis.length > 0) {
      var mLabel = document.createElement('div');
      mLabel.className = 'newtab-section-label';
      mLabel.textContent = 'Multiplayer';
      listDiv.appendChild(mLabel);
      multis.forEach(function(g) { listDiv.appendChild(makeGameRow(g)); });
    }
  }

  searchInput.addEventListener('input', function() { renderGames(this.value); });
  searchInput.addEventListener('keydown', function(e) { e.stopPropagation(); });
  renderGames('');

  container.appendChild(hub);
}

var gameNames = {
  tictactoe: 'Tic-Tac-Toe', snake: 'Snake', memory: 'Memory Match',
  blackjack: 'Blackjack', blackjack_multi: 'Blackjack (Multiplayer)', minesweeper: 'Minesweeper',
  solitaire: 'Solitaire', checkers: 'Checkers', hangman: 'Hangman',
  war: 'War', crazy_eights: 'Crazy Eights', twenty_fortyeight: '2048',
  genetic_cars: 'Genetic Cars', garlic_phone: 'Garlic Phone'
};

function showGame(container, gameId) {
  if (typeof window._gameCleanup === 'function') {
    try { window._gameCleanup(); } catch(e) {}
    window._gameCleanup = null;
  }
  if (typeof window._garlicMessageHandler === 'function') {
    window._garlicMessageHandler = null;
  }
  container.innerHTML = '';
  var hub = document.createElement('div');
  hub.className = 'games-hub';

  var header = document.createElement('div');
  header.className = 'games-header';
  var backBtn = document.createElement('button');
  backBtn.className = 'back-btn';
  backBtn.textContent = 'Back';
  backBtn.setAttribute('data-testid', 'button-back-games');
  backBtn.addEventListener('click', function() {
    if (typeof window._gameCleanup === 'function') {
      try { window._gameCleanup(); } catch(e) {}
      window._gameCleanup = null;
    }
    window._garlicMessageHandler = null;
    container.innerHTML = '';
    buildGamesHub(container);
  });
  header.appendChild(backBtn);
  var titleSpan = document.createElement('span');
  titleSpan.textContent = gameNames[gameId] || gameId;
  header.appendChild(titleSpan);
  hub.appendChild(header);

  var playArea = document.createElement('div');
  playArea.className = 'game-play-area';
  hub.appendChild(playArea);
  container.appendChild(hub);

  if (gameId === 'tictactoe') initTicTacToe(playArea);
  else if (gameId === 'snake') initSnake(playArea);
  else if (gameId === 'memory') initMemory(playArea);
  else if (gameId === 'blackjack') initBlackjack(playArea);
  else if (gameId === 'blackjack_multi') initBlackjackMulti(playArea);
  else if (gameId === 'minesweeper') initMinesweeper(playArea);
  else if (gameId === 'solitaire') initSolitaire(playArea);
  else if (gameId === 'checkers') initCheckers(playArea);
  else if (gameId === 'hangman') initHangman(playArea);
  else if (gameId === 'war') initWar(playArea);
  else if (gameId === 'crazy_eights') initCrazyEights(playArea);
  else if (gameId === 'twenty_fortyeight') init2048(playArea);
  else if (gameId === 'genetic_cars') initGeneticCars(playArea);
  else if (gameId === 'garlic_phone') initGarlicPhone(playArea);
}

""" + tictactoe.get_js() + snake.get_js() + memory.get_js() + blackjack.get_js() + blackjack_multi.get_js() + minesweeper.get_js() + solitaire.get_js() + checkers.get_js() + hangman.get_js() + war.get_js() + crazy_eights.get_js() + twenty_fortyeight.get_js() + genetic_cars.get_js() + garlic_phone.get_js() + r"""

tabs.push({ id: 'chat', type: 'chat', label: 'Chat' });
renderTabBar();
bindEmojiPicker();

document.getElementById('newTabBtn').addEventListener('click', function() {
  openNewTab();
});

// ── Right-click context menu ──────────────────────────────────────────────
var _ctxMenu = document.getElementById('msgContextMenu');
var _ctxMsg = null;
function showContextMenu(e, m) {
  e.preventDefault();
  _ctxMsg = m;
  _ctxMenu.innerHTML = '';
  function addItem(icon, label, fn, cls) {
    var d = document.createElement('div');
    d.className = 'ctx-item' + (cls ? ' ' + cls : '');
    d.innerHTML = '<span style="font-size:15px;">' + icon + '</span>' + label;
    d.addEventListener('click', function() { hideCtxMenu(); fn(); });
    _ctxMenu.appendChild(d);
  }
  function addSep() { var s = document.createElement('div'); s.className = 'ctx-sep'; _ctxMenu.appendChild(s); }
  addItem('📋', 'Copy Text', function() {
    if (!m || !m.text) return;
    navigator.clipboard.writeText(m.text).then(function(){ showToast('Copied!','success'); }).catch(function(){
      var t = document.createElement('textarea'); t.value = m.text; document.body.appendChild(t); t.select(); document.execCommand('copy'); document.body.removeChild(t); showToast('Copied!','success');
    });
  });
  addItem('↩', 'Reply', function() { setReplyTo(m); document.getElementById('msgInput').focus(); });
  addItem('👍', 'React 👍', function() { addReaction(getMsgKey(m), '👍'); });
  addItem('❤️', 'React ❤️', function() { addReaction(getMsgKey(m), '❤️'); });
  if (m && m.sender && m.sender !== myUsername) { addSep(); addItem('💬', 'DM ' + (m.display_name || m.sender), function() { openDm(m.sender); }); }
  if (isOwner && m && m.msg_id) { addSep(); addItem('🗑️', 'Delete Message', function() { ws.send(JSON.stringify({type:'delete_log',id:m.msg_id})); }, 'danger'); }
  _ctxMenu.style.display = 'block';
  var x = e.clientX, y = e.clientY;
  if (x + 170 > window.innerWidth) x = window.innerWidth - 175;
  if (y + _ctxMenu.offsetHeight > window.innerHeight) y = window.innerHeight - _ctxMenu.offsetHeight - 8;
  _ctxMenu.style.left = x + 'px';
  _ctxMenu.style.top = y + 'px';
}
function hideCtxMenu() { _ctxMenu.style.display = 'none'; _ctxMsg = null; }
document.addEventListener('click', hideCtxMenu);
document.addEventListener('keydown', function(e) { if (e.key === 'Escape') hideCtxMenu(); });

// ── Confetti easter eggs ──────────────────────────────────────────────────
function triggerConfetti() {
  var canvas = document.createElement('canvas');
  canvas.style.cssText = 'position:fixed;inset:0;pointer-events:none;z-index:99999;width:100%;height:100%;';
  document.body.appendChild(canvas);
  canvas.width = window.innerWidth; canvas.height = window.innerHeight;
  var ctx = canvas.getContext('2d');
  var colors = ['#5865f2','#57f287','#fee75c','#eb459e','#ed4245','#ff9900','#00b0f4'];
  var pieces = Array.from({length:120}, function() {
    return { x: Math.random()*canvas.width, y: Math.random()*-200, r: Math.random()*6+3,
      c: colors[Math.floor(Math.random()*colors.length)], s: Math.random()*3+2,
      vx: (Math.random()-0.5)*3, vy: 0, rot: Math.random()*360, rotV: (Math.random()-0.5)*6 };
  });
  var frame = 0;
  function draw() {
    ctx.clearRect(0,0,canvas.width,canvas.height);
    pieces.forEach(function(p) {
      p.y += p.s; p.x += p.vx; p.rot += p.rotV; p.vy += 0.05; p.y += p.vy;
      ctx.save(); ctx.translate(p.x,p.y); ctx.rotate(p.rot*Math.PI/180);
      ctx.fillStyle = p.c; ctx.fillRect(-p.r,-p.r,p.r*2,p.r*1.4); ctx.restore();
    });
    frame++;
    if (frame < 160) requestAnimationFrame(draw);
    else { canvas.remove(); }
  }
  draw();
}
var _confettiWords = ['gg','congrats','congratulations','happy birthday','🎉','🎊','hbd','you win','winner'];
function checkConfetti(text) {
  if (!text) return;
  var low = text.toLowerCase();
  for (var i = 0; i < _confettiWords.length; i++) { if (low.indexOf(_confettiWords[i]) >= 0) { setTimeout(triggerConfetti, 300); break; } }
}

// ── User hover card ───────────────────────────────────────────────────────
var _hoverCard = document.createElement('div');
_hoverCard.id = 'userHoverCard';
_hoverCard.style.cssText = 'display:none;position:fixed;z-index:9998;background:var(--bg-primary);border:1px solid var(--border);border-radius:10px;padding:16px;min-width:220px;max-width:280px;box-shadow:0 8px 24px rgba(0,0,0,0.5);pointer-events:auto;';
document.body.appendChild(_hoverCard);
function showUserCard(e, senderUsername, displayName, pfpData, bio, status) {
  _hoverCard.innerHTML = '';
  var top = document.createElement('div');
  top.style.cssText = 'display:flex;align-items:center;gap:10px;margin-bottom:10px;';
  var av = document.createElement('div');
  av.style.cssText = 'width:44px;height:44px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:16px;font-weight:700;color:#fff;background:'+avatarColor(displayName||senderUsername)+';background-size:cover;background-position:center;';
  if (pfpData) { av.style.backgroundImage = 'url('+pfpData+')'; av.textContent=''; } else { av.textContent = (displayName||senderUsername||'?').substring(0,2).toUpperCase(); }
  top.appendChild(av);
  var nameCol = document.createElement('div');
  var nm = document.createElement('div');
  nm.style.cssText = 'font-weight:700;font-size:15px;color:var(--text-primary);';
  nm.textContent = displayName || senderUsername;
  nameCol.appendChild(nm);
  if (senderUsername !== displayName) { var un = document.createElement('div'); un.style.cssText = 'font-size:12px;color:var(--text-muted);'; un.textContent = '@'+senderUsername; nameCol.appendChild(un); }
  var statusColors2 = {online:'#3ba55c',idle:'#faa61a',dnd:'#ed4245',invisible:'#747f8d'};
  var statusLabels = {online:'Online',idle:'Idle',dnd:'Do Not Disturb',invisible:'Offline'};
  var st = document.createElement('div');
  st.style.cssText = 'font-size:12px;color:'+((statusColors2[status||'online'])||'#3ba55c')+';';
  st.textContent = '● '+(statusLabels[status||'online']||'Online');
  nameCol.appendChild(st);
  top.appendChild(nameCol);
  _hoverCard.appendChild(top);
  if (bio) { var bioEl = document.createElement('div'); bioEl.style.cssText = 'font-size:13px;color:var(--text-secondary);border-top:1px solid var(--border);padding-top:8px;margin-top:2px;line-height:1.5;'; bioEl.textContent = bio; _hoverCard.appendChild(bioEl); }
  if (senderUsername && senderUsername !== myUsername) {
    var dmBtn = document.createElement('button');
    dmBtn.textContent = '💬 Send DM';
    dmBtn.style.cssText = 'margin-top:10px;width:100%;padding:7px;background:var(--accent);color:#fff;border:none;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;';
    dmBtn.addEventListener('click', function() { hideUserCard(); openDm(senderUsername); });
    _hoverCard.appendChild(dmBtn);
  }
  _hoverCard.style.display = 'block';
  var x = e.clientX, y = e.clientY + 12;
  if (x + 290 > window.innerWidth) x = window.innerWidth - 295;
  if (y + 200 > window.innerHeight) y = e.clientY - _hoverCard.offsetHeight - 8;
  _hoverCard.style.left = x + 'px';
  _hoverCard.style.top = y + 'px';
}
function hideUserCard() { _hoverCard.style.display = 'none'; }
document.addEventListener('click', function(e) { if (!_hoverCard.contains(e.target)) hideUserCard(); });
</script>
<div id="msgContextMenu"></div>
</body>
</html>"""


async def broadcast_to_clients(message):
    data = json.dumps(message)
    tasks = []
    for ws_conn in list(connected.keys()):
        try:
            tasks.append(ws_conn.send_str(data))
        except Exception:
            pass
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def send_to_admin(message):
    global admin_ws
    if admin_ws is not None:
        try:
            await admin_ws.send_str(json.dumps(message))
        except Exception:
            admin_ws = None


async def broadcast_to_staff(message):
    msg_str = json.dumps(message) if isinstance(message, dict) else message
    for sws in list(staff_connected.keys()):
        try:
            await sws.send_str(msg_str)
        except Exception:
            pass


async def broadcast_all(message):
    await broadcast_to_clients(message)
    await send_to_admin(message)
    await broadcast_to_staff(message)


def user_list():
    users = []
    for info in connected.values():
        users.append({
            "name": info["username"],
            "display_name": info.get("display_name", info["username"]),
            "pfp": info.get("pfp_data", ""),
            "bio": info.get("bio", ""),
            "status": info.get("status", "online")
        })
    for sinfo in staff_connected.values():
        if sinfo["username"] not in [u["name"] for u in users]:
            users.append({
                "name": sinfo["username"],
                "display_name": sinfo.get("display_name", sinfo["username"]),
                "pfp": "",
                "bio": sinfo.get("bio", ""),
                "status": sinfo.get("status", "online")
            })
    return users


async def send_user_list():
    users = user_list()
    msg = {"type": "users", "list": users}
    await broadcast_to_clients(msg)
    await send_to_admin(msg)
    await broadcast_to_staff(msg)
    await send_to_admin({"type": "banned_list", "list": list(banned_users)})


async def handle_chat_page(request):
    return web.Response(text=get_client_html(), content_type="text/html")


async def handle_admin_page(request):
    token = ""
    if request.method == "POST":
        data = await request.post()
        token = data.get("token", "")
    else:
        token = request.query.get("token", "")
    if token == OWNER_TOKEN:
        return web.Response(text=get_admin_html(token), content_type="text/html")
    login_html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Admin Login</title>
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: 'gg sans', 'Noto Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  background: #1e1f22; display: flex; align-items: center; justify-content: center;
  min-height: 100vh; color: #f2f3f5; }
.login-box { background: #313338; border-radius: 8px;
  padding: 32px; max-width: 400px; width: 90%; }
h2 { margin-bottom: 8px; font-size: 22px; font-weight: 700; }
p { color: #b5bac1; margin-bottom: 20px; font-size: 14px; }
label { display: block; font-size: 12px; font-weight: 700; margin-bottom: 6px;
  color: #b5bac1; text-transform: uppercase; letter-spacing: 0.5px; }
input { width: 100%; padding: 10px 12px; border: none; border-radius: 4px;
  font-size: 14px; margin-bottom: 16px; background: #1e1f22; color: #f2f3f5; outline: none; }
input:focus { outline: 2px solid #5865f2; }
button { width: 100%; padding: 10px; background: #5865f2; color: #fff; border: none;
  border-radius: 4px; font-size: 14px; font-weight: 600; cursor: pointer; }
button:hover { background: #4752c4; }
.error { color: #ed4245; font-size: 13px; margin-bottom: 10px; display: none; }
</style>
</head>
<body>
<div class="login-box">
  <h2>Admin Login</h2>
  <p>Enter the admin token from the server console.</p>
  <div class="error" id="errorMsg">Invalid token. Please try again.</div>
  <label for="tokenInput">Admin Token</label>
  <input type="password" id="tokenInput" data-testid="input-token" placeholder="Paste token here..." autofocus />
  <button id="loginBtn" data-testid="button-login">Login</button>
</div>
<script>
document.getElementById('loginBtn').addEventListener('click', function() {
  var token = document.getElementById('tokenInput').value.trim();
  if (!token) { var e = document.getElementById('errorMsg'); e.textContent = 'Please enter a token.'; e.style.display = 'block'; return; }
  var form = document.createElement('form');
  form.method = 'POST';
  form.action = '/admin';
  var inp = document.createElement('input');
  inp.type = 'hidden';
  inp.name = 'token';
  inp.value = token;
  form.appendChild(inp);
  document.body.appendChild(form);
  form.submit();
});
document.getElementById('tokenInput').addEventListener('keydown', function(e) {
  if (e.key === 'Enter') { document.getElementById('loginBtn').click(); }
});
</script>
</body>
</html>"""
    return web.Response(text=login_html, content_type="text/html")


def get_dm_pairs():
    pairs = []
    for key in dm_store:
        a = "Admin" if key[0] == "~admin~" else key[0]
        b = "Admin" if key[1] == "~admin~" else key[1]
        pairs.append(a + " & " + b)
    return pairs


async def handle_gc_create(ws, creator, data):
    global gc_counter
    gc_counter += 1
    gc_id = f"gc_{gc_counter}"
    name = data.get("name", "Group").strip() or "Group"
    members = data.get("members", [])
    if len(members) < 2:
        await ws.send_str(json.dumps({"type": "error", "text": "Need at least 2 other members."}))
        return
    all_members = [creator] + members
    gc = {"id": gc_id, "name": name, "members": all_members, "creator": creator, "messages": []}
    gc_store[gc_id] = gc
    gc_info = {"id": gc_id, "name": name, "members": all_members}
    await ws.send_str(json.dumps({"type": "gc_created", "gc": gc_info}))
    for m in members:
        for client_ws, info in connected.items():
            if info["username"] == m:
                try:
                    await client_ws.send_str(json.dumps({"type": "gc_invited", "gc": gc_info}))
                except Exception:
                    pass
                break
    print(f"[GC] {creator} created group '{name}' with {all_members}")


async def handle_gc_message(ws, sender, data):
    gc_id = data.get("gc_id", "")
    text = data.get("text", "").strip()
    gc = gc_store.get(gc_id)
    if not gc or sender not in gc["members"] or not text:
        return
    ts = _time.strftime("%H:%M")
    admin = data.get("admin", False)
    display_name = data.get("name", sender)
    gc["messages"].append({"sender": display_name, "text": text, "time": ts, "admin": admin})
    add_log("gc", gc_id=gc_id, gc_name=gc["name"], sender=display_name, text=text, admin=admin)
    msg = {"type": "gc_message", "gc_id": gc_id, "sender": display_name, "text": text, "admin": admin}
    for m in gc["members"]:
        if m == sender:
            continue
        for client_ws, info in connected.items():
            if info["username"] == m:
                try:
                    await client_ws.send_str(json.dumps(msg))
                except Exception:
                    pass
                break
    await ws.send_str(json.dumps(msg))
    print(f"[GC:{gc['name']}] {display_name}: {text}")


async def send_dm_pairs_to_admin():
    pairs = get_dm_pairs()
    await send_to_admin({"type": "dm_pairs", "pairs": pairs})


async def handle_owner_ws(request):
    global admin_ws
    token = request.query.get("token", "")
    if token != OWNER_TOKEN:
        return web.Response(text="Unauthorized", status=403)

    ws = web.WebSocketResponse()
    await ws.prepare(request)
    admin_ws = ws
    print("[OWNER] Owner connected")

    await send_to_admin({"type": "users", "list": user_list()})
    await send_to_admin({"type": "banned_list", "list": list(banned_users)})
    await send_dm_pairs_to_admin()

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)

                if data["type"] == "kick":
                    target = data["username"]
                    for client_ws, info in list(connected.items()):
                        if info["username"] == target:
                            await client_ws.send_str(json.dumps({
                                "type": "error",
                                "text": "You have been kicked by the owner."
                            }))
                            await client_ws.close()
                            break
                    for sws, sinfo in list(staff_connected.items()):
                        if sinfo["username"] == target:
                            await sws.close()
                            break
                    print(f"[OWNER] Kicked: {target}")

                elif data["type"] == "ban":
                    target = data["username"]
                    banned_users.add(target)
                    for client_ws, info in list(connected.items()):
                        if info["username"] == target:
                            await client_ws.send_str(json.dumps({
                                "type": "error",
                                "text": "You have been banned."
                            }))
                            await client_ws.close()
                            break
                    await send_to_admin({"type": "banned_list", "list": list(banned_users)})
                    print(f"[OWNER] Banned: {target}")

                elif data["type"] == "unban":
                    target = data["username"]
                    banned_users.discard(target)
                    await send_to_admin({"type": "banned_list", "list": list(banned_users)})
                    print(f"[OWNER] Unbanned: {target}")

                elif data["type"] == "react":
                    mid = data.get("msg_id", "")
                    emoji = data.get("emoji", "")
                    if mid and emoji and len(emoji) <= 8:
                        name = data.get("name", "").strip() or "Owner"
                        if mid not in msg_reactions:
                            msg_reactions[mid] = {}
                        reactors = msg_reactions[mid].setdefault(emoji, set())
                        if name in reactors:
                            reactors.discard(name)
                        else:
                            reactors.add(name)
                        react_state = {e: list(u) for e, u in msg_reactions[mid].items() if u}
                        await broadcast_all({"type": "react", "msg_id": mid, "reactions": react_state})

                elif data["type"] == "owner_broadcast":
                    text = data.get("text", "").strip()
                    if text:
                        bcast_msg = {"type": "system", "text": f"📢 [Broadcast] {text}"}
                        await broadcast_all(bcast_msg)
                        add_log("chat", sender="[Broadcast]", text=text, admin=True)
                        print(f"[OWNER BROADCAST] {text}")

                elif data["type"] == "set_motd":
                    motd_text = data.get("text", "").strip()
                    if motd_text:
                        motd_msg = {"type": "system", "text": f"📌 MOTD: {motd_text}"}
                        await broadcast_all(motd_msg)
                        print(f"[MOTD SET] {motd_text}")
                    else:
                        print("[MOTD CLEARED]")

                elif data["type"] == "chat":
                    text = data.get("text", "").strip()
                    name = data.get("name", "").strip() or "Owner"
                    if text:
                        reply_sender = data.get("reply_sender", "")
                        reply_text = data.get("reply_text", "")
                        mid = str(uuid.uuid4())[:12]
                        msg = {"type": "chat", "sender": name, "text": text, "admin": True, "msg_id": mid}
                        if reply_sender: msg["reply_sender"] = reply_sender[:80]
                        if reply_text: msg["reply_text"] = reply_text[:80]
                        await broadcast_all(msg)
                        add_log("chat", sender=name, text=text, admin=True)
                        print(f"[{name} (Owner)] {text}")

                elif data["type"] == "dm_message":
                    target = data.get("target", "").strip()
                    text = data.get("text", "").strip()
                    name = data.get("name", "").strip() or "Owner"
                    if target and text:
                        key = dm_key("~admin~", target)
                        if key not in dm_store:
                            dm_store[key] = []
                        ts = _time.strftime("%H:%M")
                        dm_store[key].append({"sender": name, "recipient": target, "text": text, "time": ts, "admin": True})
                        dm_msg_to_guest = {"type": "dm", "sender": name, "recipient": target, "text": text, "admin": True, "admin_dm": True}
                        dm_msg_to_admin = {"type": "dm", "sender": name, "recipient": target, "text": text, "admin": True}
                        for client_ws, info in connected.items():
                            if info["username"] == target:
                                try:
                                    await client_ws.send_str(json.dumps(dm_msg_to_guest))
                                except Exception:
                                    pass
                                break
                        await ws.send_str(json.dumps(dm_msg_to_admin))
                        await send_dm_pairs_to_admin()
                        add_log("dm", sender=name, recipient=target, text=text, admin=True)
                        print(f"[DM] {name} (Owner) -> {target}: {text}")

                elif data["type"] == "dm_open":
                    target = data.get("target", "")
                    key = dm_key("~admin~", target)
                    history = dm_store.get(key, [])
                    await ws.send_str(json.dumps({
                        "type": "dm_history",
                        "target": target,
                        "messages": history
                    }))

                elif data["type"] == "dm_spy_open":
                    pair_str = data.get("pair", "")
                    parts = pair_str.split(" & ")
                    if len(parts) == 2:
                        a = "~admin~" if parts[0] == "Admin" else parts[0]
                        b = "~admin~" if parts[1] == "Admin" else parts[1]
                        key = dm_key(a, b)
                        history = dm_store.get(key, [])
                        await ws.send_str(json.dumps({
                            "type": "dm_spy",
                            "pair": pair_str,
                            "messages": history
                        }))

                elif data.get("type") == "get_logs":
                    await ws.send_str(json.dumps({"type": "logs_data", "logs": chat_logs}))

                elif data.get("type") == "delete_log":
                    log_id = data.get("log_id")
                    if log_id is not None:
                        delete_log(log_id)

                elif data.get("type") == "create_admin":
                    admin_name = data.get("name", "").strip()
                    if admin_name:
                        new_key = hashlib.sha256((admin_name + str(_time.time())).encode()).hexdigest()[:16]
                        admin_accounts[new_key] = {
                            "name": admin_name,
                            "created": mtn_now().strftime("%Y-%m-%d %H:%M"),
                            "key": new_key
                        }
                        await ws.send_str(json.dumps({
                            "type": "admin_created",
                            "name": admin_name,
                            "key": new_key
                        }))
                        print(f"[OWNER] Created admin account: {admin_name}")

                elif data.get("type") == "get_admins":
                    admins_list = []
                    for k, v in admin_accounts.items():
                        admins_list.append({"name": v["name"], "created": v["created"], "key": k})
                    await ws.send_str(json.dumps({"type": "admins_data", "admins": admins_list}))

                elif data.get("type") == "remove_admin":
                    key_to_remove = data.get("key", "")
                    if key_to_remove in admin_accounts:
                        removed_name = admin_accounts[key_to_remove]["name"]
                        del admin_accounts[key_to_remove]
                        for sws, sinfo in list(staff_connected.items()):
                            if sinfo.get("admin_key") == key_to_remove:
                                await sws.close()
                        print(f"[OWNER] Removed admin: {removed_name}")

                elif data.get("type") == "get_suggestions":
                    await ws.send_str(json.dumps({"type": "suggestions_data", "suggestions": suggestions}))
                    suggestion_counter[0] = 0

                elif data.get("type") == "delete_suggestion":
                    sid = data.get("id")
                    for i, s in enumerate(suggestions):
                        if s.get("id") == sid:
                            suggestions.pop(i)
                            break

                elif data.get("type") == "gc_create":
                    await handle_gc_create(ws, "~admin~", data)

                elif data.get("type") == "gc_message":
                    await handle_gc_message(ws, "~admin~", data)

                elif data.get("type") == "gc_open":
                    gc_id = data.get("gc_id", "")
                    gc = gc_store.get(gc_id)
                    if gc and "~admin~" in gc["members"]:
                        await ws.send_str(json.dumps({
                            "type": "gc_history",
                            "gc_id": gc_id,
                            "messages": gc["messages"]
                        }))

            except Exception as e:
                print(f"[OWNER] Error: {e}")

        elif msg.type == aiohttp.WSMsgType.ERROR:
            break

    admin_ws = None
    print("[OWNER] Owner disconnected")
    return ws


async def handle_staff_ws(request):
    key = request.query.get("key", "")
    if key not in admin_accounts:
        return web.Response(text="Unauthorized", status=403)

    account = admin_accounts[key]
    staff_name = account["name"]

    ws = web.WebSocketResponse()
    await ws.prepare(request)

    staff_connected[ws] = {"username": staff_name, "admin_key": key, "role": "admin"}
    print(f"[STAFF] Admin '{staff_name}' connected")

    await ws.send_str(json.dumps({"type": "welcome", "username": staff_name, "role": "admin"}))
    await broadcast_all({"type": "users", "list": user_list()})

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)

                if data["type"] == "kick":
                    target = data["username"]
                    for client_ws, info in list(connected.items()):
                        if info["username"] == target:
                            await client_ws.send_str(json.dumps({
                                "type": "error",
                                "text": "You have been kicked by an admin."
                            }))
                            await client_ws.close()
                            break
                    print(f"[STAFF:{staff_name}] Kicked: {target}")

                elif data["type"] == "react":
                    mid = data.get("msg_id", "")
                    emoji = data.get("emoji", "")
                    if mid and emoji and len(emoji) <= 8:
                        if mid not in msg_reactions:
                            msg_reactions[mid] = {}
                        reactors = msg_reactions[mid].setdefault(emoji, set())
                        if staff_name in reactors:
                            reactors.discard(staff_name)
                        else:
                            reactors.add(staff_name)
                        react_state = {e: list(u) for e, u in msg_reactions[mid].items() if u}
                        await broadcast_all({"type": "react", "msg_id": mid, "reactions": react_state})

                elif data["type"] == "chat":
                    text = data.get("text", "").strip()
                    if text:
                        reply_sender = data.get("reply_sender", "")
                        reply_text = data.get("reply_text", "")
                        mid = str(uuid.uuid4())[:12]
                        msg = {"type": "chat", "sender": staff_name, "text": text, "admin": True, "msg_id": mid}
                        if reply_sender: msg["reply_sender"] = reply_sender[:80]
                        if reply_text: msg["reply_text"] = reply_text[:80]
                        await broadcast_all(msg)
                        add_log("chat", sender=staff_name, text=text, admin=True)
                        print(f"[{staff_name} (Admin)] {text}")

                elif data["type"] == "dm_message":
                    target = data.get("target", "").strip()
                    text = data.get("text", "").strip()
                    if target and text:
                        identity = "~staff:" + key + "~"
                        k = dm_key(identity, target)
                        if k not in dm_store:
                            dm_store[k] = []
                        ts = _time.strftime("%H:%M")
                        dm_store[k].append({"sender": staff_name, "recipient": target, "text": text, "time": ts, "admin": True})
                        dm_msg = {"type": "dm", "sender": staff_name, "recipient": target, "text": text, "admin": True, "admin_dm": True}
                        for client_ws, info in connected.items():
                            if info["username"] == target:
                                try:
                                    await client_ws.send_str(json.dumps(dm_msg))
                                except Exception:
                                    pass
                                break
                        await ws.send_str(json.dumps({"type": "dm", "sender": staff_name, "recipient": target, "text": text, "admin": True}))
                        add_log("dm", sender=staff_name, recipient=target, text=text, admin=True)

                elif data["type"] == "dm_open":
                    target = data.get("target", "")
                    identity = "~staff:" + key + "~"
                    k = dm_key(identity, target)
                    history = dm_store.get(k, [])
                    await ws.send_str(json.dumps({
                        "type": "dm_history",
                        "target": target,
                        "messages": history
                    }))

                elif data.get("type") == "get_logs":
                    await ws.send_str(json.dumps({"type": "logs_data", "logs": chat_logs}))

                elif data.get("type") == "send_suggestion":
                    text = data.get("text", "").strip()
                    if text:
                        sid = len(suggestions) + 1
                        suggestions.append({
                            "id": sid,
                            "from": staff_name,
                            "text": text,
                            "timestamp": mtn_now().strftime("%Y-%m-%d %H:%M")
                        })
                        suggestion_counter[0] += 1
                        await ws.send_str(json.dumps({"type": "suggestion_sent"}))
                        if admin_ws:
                            try:
                                await admin_ws.send_str(json.dumps({"type": "new_suggestion"}))
                            except Exception:
                                pass
                        print(f"[STAFF:{staff_name}] Suggestion: {text}")

                elif data.get("type") == "gc_create":
                    identity = "~staff:" + key + "~"
                    await handle_gc_create(ws, identity, data)

                elif data.get("type") == "gc_message":
                    identity = "~staff:" + key + "~"
                    await handle_gc_message(ws, identity, data)

                elif data.get("type") == "gc_open":
                    gc_id = data.get("gc_id", "")
                    identity = "~staff:" + key + "~"
                    gc = gc_store.get(gc_id)
                    if gc and identity in gc["members"]:
                        await ws.send_str(json.dumps({
                            "type": "gc_history",
                            "gc_id": gc_id,
                            "messages": gc["messages"]
                        }))

                elif data.get("type") == "bj_action":
                    await handle_bj_action(ws, staff_name, data)

            except Exception as e:
                print(f"[STAFF:{staff_name}] Error: {e}")

        elif msg.type == aiohttp.WSMsgType.ERROR:
            break

    if ws in staff_connected:
        del staff_connected[ws]
    await broadcast_all({"type": "users", "list": user_list()})
    print(f"[STAFF] Admin '{staff_name}' disconnected")
    return ws


def bj_make_deck():
    suits = ['S', 'H', 'D', 'C']
    ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
    deck = [{"suit": s, "rank": r} for s in suits for r in ranks]
    random.shuffle(deck)
    return deck


def bj_card_value(hand):
    total = 0
    aces = 0
    for c in hand:
        r = c["rank"]
        if r == 'A':
            total += 11
            aces += 1
        elif r in ('J', 'Q', 'K'):
            total += 10
        else:
            total += int(r)
    while total > 21 and aces > 0:
        total -= 10
        aces -= 1
    return total


def bj_room_state(room, reveal_dealer=False):
    dealer_hand = []
    for i, c in enumerate(room["dealer_hand"]):
        if i == 1 and not reveal_dealer:
            dealer_hand.append({"suit": "?", "rank": "?", "hidden": True})
        else:
            dealer_hand.append(c)
    players_data = []
    for p in room["players"]:
        pd = {"id": p["id"], "name": p["name"], "hand": p["hand"], "value": bj_card_value(p["hand"]) if p["hand"] else 0, "score": p.get("score", 0)}
        if p.get("result"):
            pd["result"] = p["result"]
        players_data.append(pd)
    current_turn = None
    if room["phase"] == "playing" and 0 <= room["current_turn_idx"] < len(room["players"]):
        current_turn = room["players"][room["current_turn_idx"]]["id"]
    return {
        "room_id": room["room_id"],
        "phase": room["phase"],
        "host": room["host"],
        "players": players_data,
        "dealer_hand": dealer_hand,
        "dealer_value": bj_card_value(room["dealer_hand"]) if reveal_dealer else None,
        "current_turn": current_turn,
    }


async def bj_broadcast_state(room, reveal=False):
    state = bj_room_state(room, reveal)
    for p in room["players"]:
        ws_conn = p.get("ws")
        if ws_conn:
            try:
                await ws_conn.send_str(json.dumps({"type": "bj_state", "state": state}))
            except Exception:
                pass


async def bj_turn_timeout(room_id, turn_idx):
    await asyncio.sleep(30)
    room = bj_rooms.get(room_id)
    if not room or room["phase"] != "playing":
        return
    if room["current_turn_idx"] != turn_idx:
        return
    room["current_turn_idx"] += 1
    if room["current_turn_idx"] >= len(room["players"]):
        await bj_dealer_play(room)
    else:
        asyncio.create_task(bj_turn_timeout(room_id, room["current_turn_idx"]))
        await bj_broadcast_state(room)


async def handle_bj_action(ws, username, data):
    action = data.get("action", "")

    if action == "create":
        room_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        room = {
            "room_id": room_id,
            "players": [{"id": username, "name": username, "ws": ws, "hand": [], "result": None, "score": 0}],
            "deck": [],
            "dealer_hand": [],
            "phase": "waiting",
            "host": username,
            "current_turn_idx": 0,
        }
        bj_rooms[room_id] = room
        state = bj_room_state(room)
        await ws.send_str(json.dumps({"type": "bj_room_created", "room_id": room_id, "player_id": username, "state": state}))

    elif action == "join":
        room_id = data.get("room_id", "").strip().upper()
        room = bj_rooms.get(room_id)
        if not room:
            await ws.send_str(json.dumps({"type": "bj_error", "text": "Room not found."}))
            return
        if len(room["players"]) >= 4:
            await ws.send_str(json.dumps({"type": "bj_error", "text": "Room is full."}))
            return
        if any(p["id"] == username for p in room["players"]):
            await ws.send_str(json.dumps({"type": "bj_error", "text": "Already in this room."}))
            return
        if room["phase"] != "waiting":
            await ws.send_str(json.dumps({"type": "bj_error", "text": "Game already in progress."}))
            return
        room["players"].append({"id": username, "name": username, "ws": ws, "hand": [], "result": None, "score": 0})
        state = bj_room_state(room)
        await ws.send_str(json.dumps({"type": "bj_joined", "room_id": room_id, "player_id": username, "state": state}))
        await bj_broadcast_state(room)

    elif action == "start":
        room_id = data.get("room_id", "")
        room = bj_rooms.get(room_id)
        if not room:
            return
        room["deck"] = bj_make_deck()
        room["dealer_hand"] = [room["deck"].pop(), room["deck"].pop()]
        for p in room["players"]:
            p["hand"] = [room["deck"].pop(), room["deck"].pop()]
            p["result"] = None
        room["phase"] = "playing"
        room["current_turn_idx"] = 0
        asyncio.create_task(bj_turn_timeout(room_id, 0))
        await bj_broadcast_state(room)

    elif action == "hit":
        room_id = data.get("room_id", "")
        room = bj_rooms.get(room_id)
        if not room or room["phase"] != "playing":
            return
        idx = room["current_turn_idx"]
        if idx >= len(room["players"]):
            return
        player = room["players"][idx]
        if player["id"] != username:
            return
        player["hand"].append(room["deck"].pop())
        if bj_card_value(player["hand"]) > 21:
            player["result"] = "Bust"
            room["current_turn_idx"] += 1
            if room["current_turn_idx"] >= len(room["players"]):
                await bj_dealer_play(room)
            else:
                asyncio.create_task(bj_turn_timeout(room_id, room["current_turn_idx"]))
                await bj_broadcast_state(room)
        else:
            await bj_broadcast_state(room)

    elif action == "stand":
        room_id = data.get("room_id", "")
        room = bj_rooms.get(room_id)
        if not room or room["phase"] != "playing":
            return
        idx = room["current_turn_idx"]
        if idx >= len(room["players"]):
            return
        player = room["players"][idx]
        if player["id"] != username:
            return
        room["current_turn_idx"] += 1
        if room["current_turn_idx"] >= len(room["players"]):
            await bj_dealer_play(room)
        else:
            asyncio.create_task(bj_turn_timeout(room_id, room["current_turn_idx"]))
            await bj_broadcast_state(room)

    elif action == "leave":
        room_id = data.get("room_id", "")
        room = bj_rooms.get(room_id)
        if not room:
            return
        room["players"] = [p for p in room["players"] if p["id"] != username]
        if not room["players"]:
            del bj_rooms[room_id]
        else:
            if room["host"] == username:
                room["host"] = room["players"][0]["id"]
            await bj_broadcast_state(room)


async def bj_dealer_play(room):
    room["phase"] = "dealer"
    while bj_card_value(room["dealer_hand"]) < 17:
        room["dealer_hand"].append(room["deck"].pop())
    dv = bj_card_value(room["dealer_hand"])
    for p in room["players"]:
        if p["result"] == "Bust":
            p["result"] = "Lose"
            p["score"] = p.get("score", 0) - 1
            continue
        pv = bj_card_value(p["hand"])
        if dv > 21:
            p["result"] = "Win"
            p["score"] = p.get("score", 0) + 1
        elif pv > dv:
            p["result"] = "Win"
            p["score"] = p.get("score", 0) + 1
        elif pv < dv:
            p["result"] = "Lose"
            p["score"] = p.get("score", 0) - 1
        else:
            p["result"] = "Push"
    room["phase"] = "done"
    await bj_broadcast_state(room, reveal=True)


async def bj_handle_disconnect(username):
    rooms_to_delete = []
    for room_id, room in bj_rooms.items():
        player_idx = None
        for i, p in enumerate(room["players"]):
            if p["id"] == username:
                player_idx = i
                break
        if player_idx is None:
            continue
        was_current_turn = (room["phase"] == "playing" and room["current_turn_idx"] == player_idx)
        room["players"].pop(player_idx)
        if not room["players"]:
            rooms_to_delete.append(room_id)
            continue
        if room["host"] == username:
            room["host"] = room["players"][0]["id"]
        if room["phase"] == "playing":
            if player_idx < room["current_turn_idx"]:
                room["current_turn_idx"] -= 1
            if was_current_turn or room["current_turn_idx"] >= len(room["players"]):
                if room["current_turn_idx"] >= len(room["players"]):
                    await bj_dealer_play(room)
                    continue
        await bj_broadcast_state(room)
    for rid in rooms_to_delete:
        del bj_rooms[rid]


async def handle_client_ws(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    username = None

    async for msg in ws:
        if msg.type == aiohttp.WSMsgType.TEXT:
            try:
                data = json.loads(msg.data)

                if username is None:
                    if data.get("type") != "join" or not data.get("username", "").strip():
                        await ws.send_str(json.dumps({
                            "type": "error",
                            "text": "Send a join message with a username first."
                        }))
                        continue

                    name = data["username"].strip()
                    session_token = data.get("session_token", "").strip()
                    display_name = name
                    pfp_data = ""
                    bio = ""
                    show_changelog = False

                    if session_token:
                        profile = await db_validate_session(session_token)
                        if profile:
                            name = profile["username"]
                            display_name = profile["display_name"]
                            pfp_data = profile.get("pfp_data", "")
                            bio = profile.get("bio", "")

                    if not USERNAME_RE.match(name):
                        await ws.send_str(json.dumps({
                            "type": "error",
                            "text": "Username must be 1-20 characters: letters, numbers, _ or - only."
                        }))
                        continue

                    if RESERVED_RE.search(name):
                        await ws.send_str(json.dumps({
                            "type": "error",
                            "text": "Username cannot contain 'admin', 'mod', or 'owner'."
                        }))
                        continue

                    if name in banned_users:
                        await ws.send_str(json.dumps({
                            "type": "error",
                            "text": "You are banned from this server."
                        }))
                        await ws.close()
                        break

                    if name in [i["username"] for i in connected.values()]:
                        await ws.send_str(json.dumps({
                            "type": "error",
                            "text": f"Username '{name}' is already taken."
                        }))
                        continue

                    username = name
                    connected[ws] = {
                        "username": username, "ws": ws,
                        "display_name": display_name,
                        "pfp_data": pfp_data, "bio": bio,
                        "is_guest": not bool(session_token)
                    }
                    # Load or initialise economy
                    _is_reg = bool(session_token) and db_pool
                    if _is_reg:
                        _econ = await db_get_economy(username)
                        connected[ws]["balance"]       = _econ["balance"]
                        connected[ws]["inventory"]     = _econ["inventory"]
                        connected[ws]["equipped"]      = _econ["equipped"]
                        connected[ws]["idle_money"]    = _econ["idle_money"]
                        connected[ws]["idle_upgrades"] = _econ["idle_upgrades"]
                    else:
                        connected[ws]["balance"]       = 1000
                        connected[ws]["inventory"]     = []
                        connected[ws]["equipped"]      = {}
                        connected[ws]["idle_money"]    = 0.0
                        connected[ws]["idle_upgrades"] = {}
                    connected[ws]["savings"] = []  # loaded on-demand
                    print(f"[+] {username} ({display_name}) joined  ({len(connected)} online)")

                    await ws.send_str(json.dumps({
                        "type": "joined",
                        "username": username,
                        "display_name": display_name,
                        "pfp_data": pfp_data,
                        "bio": bio
                    }))
                    await broadcast_all({"type": "system", "text": f"{display_name} joined the chat"})
                    await send_user_list()

                elif data.get("type") == "react":
                    mid = data.get("msg_id", "")
                    emoji = data.get("emoji", "")
                    if mid and emoji and len(emoji) <= 8:
                        disp = connected[ws].get("display_name", username)
                        if mid not in msg_reactions:
                            msg_reactions[mid] = {}
                        reactors = msg_reactions[mid].setdefault(emoji, set())
                        if disp in reactors:
                            reactors.discard(disp)
                        else:
                            reactors.add(disp)
                        react_state = {e: list(u) for e, u in msg_reactions[mid].items() if u}
                        await broadcast_all({"type": "react", "msg_id": mid, "reactions": react_state})

                elif data.get("type") == "chat":
                    text = data.get("text", "").strip()
                    if text:
                        disp = connected[ws].get("display_name", username)
                        pfp = connected[ws].get("pfp_data", "")
                        reply_sender = data.get("reply_sender", "")
                        reply_text = data.get("reply_text", "")
                        mid = str(uuid.uuid4())[:12]
                        msg = {"type": "chat", "sender": username, "display_name": disp, "pfp": pfp, "text": text, "msg_id": mid}
                        if reply_sender: msg["reply_sender"] = reply_sender[:80]
                        if reply_text: msg["reply_text"] = reply_text[:80]
                        await broadcast_all(msg)
                        add_log("chat", sender=disp, text=text)
                        print(f"[{disp}] {text}")

                elif data.get("type") == "dm_message":
                    target = data.get("target", "").strip()
                    text = data.get("text", "").strip()
                    if target and text and target != username:
                        is_to_admin = (target == "Admin")
                        store_target = "~admin~" if is_to_admin else target
                        key = dm_key(username, store_target)
                        if key not in dm_store:
                            dm_store[key] = []
                        ts = _time.strftime("%H:%M")
                        dm_store[key].append({"sender": username, "recipient": target, "text": text, "time": ts})
                        dm_msg = {"type": "dm", "sender": username, "recipient": target, "text": text}
                        if is_to_admin:
                            await send_to_admin(dm_msg)
                        else:
                            for client_ws_conn, info in connected.items():
                                if info["username"] == target:
                                    try:
                                        await client_ws_conn.send_str(json.dumps(dm_msg))
                                    except Exception:
                                        pass
                                    break
                            spy_pair = key[0] + " & " + key[1]
                            spy_pair_display = spy_pair.replace("~admin~", "Admin")
                            await send_to_admin({"type": "dm_spy_update", "pair": spy_pair_display, "sender": username, "recipient": target, "text": text})
                        await ws.send_str(json.dumps(dm_msg))
                        await send_dm_pairs_to_admin()
                        add_log("dm", sender=username, recipient=target, text=text)
                        print(f"[DM] {username} -> {target}: {text}")

                elif data.get("type") == "dm_open":
                    target = data.get("target", "")
                    store_target = "~admin~" if target == "Admin" else target
                    key = dm_key(username, store_target)
                    history = dm_store.get(key, [])
                    await ws.send_str(json.dumps({
                        "type": "dm_history",
                        "target": target,
                        "messages": history
                    }))

                elif data.get("type") == "gc_create":
                    await handle_gc_create(ws, username, data)

                elif data.get("type") == "gc_message":
                    await handle_gc_message(ws, username, data)

                elif data.get("type") == "gc_open":
                    gc_id = data.get("gc_id", "")
                    gc = gc_store.get(gc_id)
                    if gc and username in gc["members"]:
                        await ws.send_str(json.dumps({
                            "type": "gc_history",
                            "gc_id": gc_id,
                            "messages": gc["messages"]
                        }))

                elif data.get("type") == "send_suggestion":
                    text = data.get("text", "").strip()
                    if text:
                        sid = len(suggestions) + 1
                        suggestions.append({
                            "id": sid,
                            "from": username,
                            "text": text,
                            "timestamp": mtn_now().strftime("%Y-%m-%d %H:%M")
                        })
                        suggestion_counter[0] += 1
                        await ws.send_str(json.dumps({"type": "suggestion_sent"}))
                        if admin_ws:
                            try:
                                await admin_ws.send_str(json.dumps({"type": "new_suggestion"}))
                            except Exception:
                                pass

                elif data.get("type") == "typing":
                    channel = data.get("channel", "general")
                    typing_msg = {"type": "typing", "username": username, "channel": channel}
                    if channel == "general":
                        for c_ws in list(connected.keys()):
                            if c_ws != ws:
                                try:
                                    await c_ws.send_str(json.dumps(typing_msg))
                                except Exception:
                                    pass
                        await send_to_admin(typing_msg)
                        await broadcast_to_staff(typing_msg)
                    elif channel.startswith("dm:"):
                        target = channel[3:]
                        for c_ws, info in connected.items():
                            if info["username"] == target:
                                try:
                                    await c_ws.send_str(json.dumps(typing_msg))
                                except Exception:
                                    pass
                                break

                elif data.get("type") == "set_status":
                    status = data.get("status", "online")
                    if status in ("online", "idle", "dnd", "invisible"):
                        connected[ws]["status"] = status
                        await send_user_list()

                elif data.get("type") == "bj_action":
                    await handle_bj_action(ws, username, data)

                elif data.get("type") == "garlic_action":
                    await handle_garlic_action(ws, username, data)

                elif data.get("type") == "update_display_name":
                    new_dn = data.get("display_name", "").strip()[:30]
                    if new_dn and ws in connected:
                        connected[ws]["display_name"] = new_dn
                        if not connected[ws].get("is_guest", True):
                            if "pfp_data" in data:
                                connected[ws]["pfp_data"] = data.get("pfp_data", "")
                            if "bio" in data:
                                connected[ws]["bio"] = data.get("bio", "")
                        await send_user_list()

                # ── Economy handlers ─────────────────────────────────────────
                elif data.get("type") == "get_balance":
                    if ws not in connected: continue
                    u = username
                    _guest = connected[ws].get("is_guest", True)
                    savings = await db_get_savings(u) if not _guest and db_pool else connected[ws].get("savings", [])
                    txns    = await db_get_transactions(u, 15) if not _guest and db_pool else []
                    await ws.send_str(json.dumps({
                        "type": "balance_data",
                        "balance":       connected[ws].get("balance", 1000),
                        "inventory":     connected[ws].get("inventory", []),
                        "equipped":      connected[ws].get("equipped", {}),
                        "savings":       savings,
                        "idle_money":    connected[ws].get("idle_money", 0.0),
                        "idle_upgrades": connected[ws].get("idle_upgrades", {}),
                        "transactions":  txns,
                        "is_guest":      _guest,
                        "idle_upgrades_def": IDLE_UPGRADES,
                        "shop_catalog":  list({"id":k,**v} for k,v in SHOP_CATALOG.items()),
                    }))

                elif data.get("type") == "shop_buy":
                    if ws not in connected: continue
                    item_id = data.get("item_id","")
                    item = SHOP_CATALOG.get(item_id)
                    if not item:
                        await ws.send_str(json.dumps({"type":"shop_result","ok":False,"error":"Unknown item"})); continue
                    bal = connected[ws].get("balance", 0)
                    inv = list(connected[ws].get("inventory", []))
                    if item_id in inv:
                        await ws.send_str(json.dumps({"type":"shop_result","ok":False,"error":"Already owned"})); continue
                    if bal < item["price"]:
                        await ws.send_str(json.dumps({"type":"shop_result","ok":False,"error":"Not enough balance"})); continue
                    new_bal = bal - item["price"]
                    inv.append(item_id)
                    connected[ws]["balance"]   = new_bal
                    connected[ws]["inventory"] = inv
                    _guest = connected[ws].get("is_guest", True)
                    if not _guest and db_pool:
                        await db_save_economy(username, {"balance":new_bal,"inventory":inv,"equipped":connected[ws].get("equipped",{}),"idle_money":connected[ws].get("idle_money",0),"idle_upgrades":connected[ws].get("idle_upgrades",{})})
                        await db_add_transaction(username, -item["price"], f"Bought: {item['name']}")
                    await ws.send_str(json.dumps({"type":"shop_result","ok":True,"item_id":item_id,"balance":new_bal,"inventory":inv}))

                elif data.get("type") == "shop_equip":
                    if ws not in connected: continue
                    item_id = data.get("item_id","")
                    inv = connected[ws].get("inventory", [])
                    if item_id not in inv:
                        await ws.send_str(json.dumps({"type":"equip_result","ok":False,"error":"Not owned"})); continue
                    item = SHOP_CATALOG.get(item_id, {})
                    cat  = item.get("cat", "")
                    eqp  = dict(connected[ws].get("equipped", {}))
                    if eqp.get(cat) == item_id: del eqp[cat]
                    else: eqp[cat] = item_id
                    connected[ws]["equipped"] = eqp
                    _guest = connected[ws].get("is_guest", True)
                    if not _guest and db_pool:
                        await db_save_economy(username, {"balance":connected[ws].get("balance",1000),"inventory":inv,"equipped":eqp,"idle_money":connected[ws].get("idle_money",0),"idle_upgrades":connected[ws].get("idle_upgrades",{})})
                    await ws.send_str(json.dumps({"type":"equip_result","ok":True,"equipped":eqp}))

                elif data.get("type") == "savings_create":
                    if ws not in connected: continue
                    _guest = connected[ws].get("is_guest", True)
                    sname  = data.get("name","").strip()[:50]
                    sgoal  = max(1, int(data.get("goal", 100)))
                    scol   = data.get("color","#4f9cf9")[:30]
                    if not sname:
                        await ws.send_str(json.dumps({"type":"savings_result","ok":False,"error":"Name required"})); continue
                    if not _guest and db_pool:
                        await db_create_savings(username, sname, sgoal, scol)
                        savings = await db_get_savings(username)
                    else:
                        if "savings" not in connected[ws]: connected[ws]["savings"] = []
                        _pid = int(_time.time()*1000) % 999999
                        connected[ws]["savings"].append({"id":_pid,"name":sname,"goal":sgoal,"saved":0,"color":scol})
                        savings = connected[ws]["savings"]
                    await ws.send_str(json.dumps({"type":"savings_result","ok":True,"savings":savings,"balance":connected[ws].get("balance",0)}))

                elif data.get("type") == "savings_deposit":
                    if ws not in connected: continue
                    _guest  = connected[ws].get("is_guest", True)
                    plan_id = int(data.get("plan_id", 0))
                    amount  = max(1, int(data.get("amount", 0)))
                    bal = connected[ws].get("balance", 0)
                    if bal < amount:
                        await ws.send_str(json.dumps({"type":"savings_result","ok":False,"error":"Insufficient balance"})); continue
                    connected[ws]["balance"] = bal - amount
                    if not _guest and db_pool:
                        await db_update_savings(plan_id, username, amount, "deposit")
                        await db_add_transaction(username, -amount, "Savings deposit")
                        await db_save_economy(username, {"balance":connected[ws]["balance"],"inventory":connected[ws].get("inventory",[]),"equipped":connected[ws].get("equipped",{}),"idle_money":connected[ws].get("idle_money",0),"idle_upgrades":connected[ws].get("idle_upgrades",{})})
                        savings = await db_get_savings(username)
                    else:
                        if "savings" not in connected[ws]: connected[ws]["savings"] = []
                        for p in connected[ws]["savings"]:
                            if p["id"] == plan_id: p["saved"] = min(p["saved"]+amount, p["goal"]); break
                        savings = connected[ws]["savings"]
                    await ws.send_str(json.dumps({"type":"savings_result","ok":True,"balance":connected[ws]["balance"],"savings":savings}))

                elif data.get("type") == "savings_withdraw":
                    if ws not in connected: continue
                    _guest  = connected[ws].get("is_guest", True)
                    plan_id = int(data.get("plan_id", 0))
                    amount  = max(1, int(data.get("amount", 0)))
                    if not _guest and db_pool:
                        savings = await db_get_savings(username)
                        plan = next((p for p in savings if p["id"] == plan_id), None)
                        if not plan or plan["saved"] < amount:
                            await ws.send_str(json.dumps({"type":"savings_result","ok":False,"error":"Not enough in plan"})); continue
                        await db_update_savings(plan_id, username, amount, "withdraw")
                        await db_add_transaction(username, amount, "Savings withdrawal")
                        connected[ws]["balance"] = connected[ws].get("balance",0) + amount
                        await db_save_economy(username, {"balance":connected[ws]["balance"],"inventory":connected[ws].get("inventory",[]),"equipped":connected[ws].get("equipped",{}),"idle_money":connected[ws].get("idle_money",0),"idle_upgrades":connected[ws].get("idle_upgrades",{})})
                        savings = await db_get_savings(username)
                    else:
                        if "savings" not in connected[ws]: connected[ws]["savings"] = []
                        plan = next((p for p in connected[ws]["savings"] if p["id"] == plan_id), None)
                        if not plan or plan["saved"] < amount:
                            await ws.send_str(json.dumps({"type":"savings_result","ok":False,"error":"Not enough in plan"})); continue
                        plan["saved"] -= amount
                        connected[ws]["balance"] = connected[ws].get("balance",0) + amount
                        savings = connected[ws]["savings"]
                    await ws.send_str(json.dumps({"type":"savings_result","ok":True,"balance":connected[ws]["balance"],"savings":savings}))

                elif data.get("type") == "savings_delete":
                    if ws not in connected: continue
                    _guest  = connected[ws].get("is_guest", True)
                    plan_id = int(data.get("plan_id", 0))
                    if not _guest and db_pool:
                        savings = await db_get_savings(username)
                        plan = next((p for p in savings if p["id"] == plan_id), None)
                        if plan and plan["saved"] > 0:
                            connected[ws]["balance"] = connected[ws].get("balance",0) + plan["saved"]
                            await db_add_transaction(username, plan["saved"], "Savings plan deleted (refund)")
                        await db_delete_savings(plan_id, username)
                        if plan and plan["saved"] > 0:
                            await db_save_economy(username, {"balance":connected[ws]["balance"],"inventory":connected[ws].get("inventory",[]),"equipped":connected[ws].get("equipped",{}),"idle_money":connected[ws].get("idle_money",0),"idle_upgrades":connected[ws].get("idle_upgrades",{})})
                        savings = await db_get_savings(username)
                    else:
                        if "savings" not in connected[ws]: connected[ws]["savings"] = []
                        for p in connected[ws]["savings"]:
                            if p["id"] == plan_id and p["saved"] > 0:
                                connected[ws]["balance"] = connected[ws].get("balance",0) + p["saved"]
                        connected[ws]["savings"] = [p for p in connected[ws]["savings"] if p["id"] != plan_id]
                        savings = connected[ws]["savings"]
                    await ws.send_str(json.dumps({"type":"savings_result","ok":True,"balance":connected[ws].get("balance",0),"savings":savings}))

                elif data.get("type") == "gamble":
                    if ws not in connected: continue
                    game   = data.get("game","")
                    bet    = int(data.get("bet", 0))
                    choice = data.get("choice","")
                    bal    = connected[ws].get("balance", 0)
                    if bet <= 0 or bet > bal:
                        await ws.send_str(json.dumps({"type":"gamble_result","ok":False,"error":"Invalid bet amount"})); continue
                    won = 0; result_data = {}
                    if game == "coinflip":
                        flip = random.choice(["heads","tails"])
                        won  = bet if flip == choice else -bet
                        result_data = {"flip": flip, "choice": choice}
                    elif game == "dice":
                        my_r = random.randint(1,6); dl_r = random.randint(1,6)
                        won  = bet if my_r > dl_r else (-bet if my_r < dl_r else 0)
                        result_data = {"my_roll": my_r, "dealer_roll": dl_r}
                    elif game == "slots":
                        syms  = ["cherry","lemon","orange","grape","diamond","seven"]
                        reels = [random.choice(syms) for _ in range(3)]
                        if reels[0]==reels[1]==reels[2]:
                            won = bet*(10 if reels[0]=="diamond" else (7 if reels[0]=="seven" else 3))
                        elif reels[0]==reels[1] or reels[1]==reels[2] or reels[0]==reels[2]:
                            won = 0
                        else:
                            won = -bet
                        result_data = {"reels": reels}
                    elif game == "roulette":
                        num = random.randint(0,36)
                        red_nums = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
                        col = "green" if num==0 else ("red" if num in red_nums else "black")
                        if choice=="green": won = bet*17 if num==0 else -bet
                        elif choice=="red":   won = bet if col=="red" else -bet
                        elif choice=="black": won = bet if col=="black" else -bet
                        result_data = {"number": num, "color": col}
                    elif game == "hilo":
                        drawn    = int(data.get("drawn", 7))
                        next_num = random.randint(1,13)
                        if (choice=="higher" and next_num>drawn) or (choice=="lower" and next_num<drawn): won = bet
                        elif next_num == drawn: won = 0
                        else: won = -bet
                        result_data = {"drawn": drawn, "next": next_num}
                    else:
                        await ws.send_str(json.dumps({"type":"gamble_result","ok":False,"error":"Unknown game"})); continue
                    new_bal = max(0, bal + won)
                    connected[ws]["balance"] = new_bal
                    _guest = connected[ws].get("is_guest", True)
                    if not _guest and db_pool:
                        await db_save_economy(username, {"balance":new_bal,"inventory":connected[ws].get("inventory",[]),"equipped":connected[ws].get("equipped",{}),"idle_money":connected[ws].get("idle_money",0),"idle_upgrades":connected[ws].get("idle_upgrades",{})})
                        await db_add_transaction(username, won, f"Gamble: {game} (bet ${bet})")
                    await ws.send_str(json.dumps({"type":"gamble_result","ok":True,"won":won,"new_balance":new_bal,"game":game,"data":result_data}))

                elif data.get("type") == "idle_upgrade":
                    if ws not in connected: continue
                    upg_id  = data.get("upgrade_id","")
                    upg     = next((u for u in IDLE_UPGRADES if u["id"]==upg_id), None)
                    if not upg:
                        await ws.send_str(json.dumps({"type":"idle_result","ok":False,"error":"Unknown upgrade"})); continue
                    idle_money    = float(connected[ws].get("idle_money", 0))
                    idle_upgrades = dict(connected[ws].get("idle_upgrades", {}))
                    cnt   = idle_upgrades.get(upg_id, 0)
                    price = int(upg["base_price"] * (1.15 ** cnt))
                    if idle_money < price:
                        await ws.send_str(json.dumps({"type":"idle_result","ok":False,"error":"Not enough idle money"})); continue
                    idle_money -= price
                    idle_upgrades[upg_id] = cnt + 1
                    connected[ws]["idle_money"]    = idle_money
                    connected[ws]["idle_upgrades"] = idle_upgrades
                    cv, cps = _calc_idle_stats(idle_upgrades)
                    _guest = connected[ws].get("is_guest", True)
                    if not _guest and db_pool:
                        await db_save_economy(username, {"balance":connected[ws].get("balance",1000),"inventory":connected[ws].get("inventory",[]),"equipped":connected[ws].get("equipped",{}),"idle_money":idle_money,"idle_upgrades":idle_upgrades})
                    await ws.send_str(json.dumps({"type":"idle_result","ok":True,"idle_money":idle_money,"idle_upgrades":idle_upgrades,"click_val":cv,"cps":cps}))

                elif data.get("type") == "idle_click":
                    if ws not in connected: continue
                    idle_upgrades = connected[ws].get("idle_upgrades", {})
                    cv, _ = _calc_idle_stats(idle_upgrades)
                    idle_money = float(connected[ws].get("idle_money", 0)) + cv
                    connected[ws]["idle_money"] = idle_money
                    _, cps = _calc_idle_stats(idle_upgrades)
                    await ws.send_str(json.dumps({"type":"idle_result","ok":True,"idle_money":idle_money,"click_val":cv,"cps":cps,"idle_upgrades":idle_upgrades}))

                elif data.get("type") == "idle_collect":
                    if ws not in connected: continue
                    amt = max(0.0, float(data.get("amount", 0)))
                    if amt > 0:
                        new_bal = connected[ws].get("balance",0) + int(amt)
                        connected[ws]["balance"]    = new_bal
                        connected[ws]["idle_money"] = max(0.0, connected[ws].get("idle_money",0) - amt)
                        _guest = connected[ws].get("is_guest", True)
                        if not _guest and db_pool:
                            await db_save_economy(username, {"balance":new_bal,"inventory":connected[ws].get("inventory",[]),"equipped":connected[ws].get("equipped",{}),"idle_money":connected[ws]["idle_money"],"idle_upgrades":connected[ws].get("idle_upgrades",{})})
                            await db_add_transaction(username, int(amt), "Idle game earnings collected")
                        await ws.send_str(json.dumps({"type":"idle_collect_result","ok":True,"balance":new_bal}))

            except Exception as e:
                print(f"[!] Error: {e}")

        elif msg.type == aiohttp.WSMsgType.ERROR:
            break

    if ws in connected:
        info = connected.pop(ws)
        left = info["username"]
        left_display = info.get("display_name", left)
        print(f"[-] {left} left  ({len(connected)} online)")

        await bj_handle_disconnect(left)
        await garlic_handle_disconnect(left)

        keys_to_remove = [k for k in dm_store if left in k]
        for k in keys_to_remove:
            del dm_store[k]

        await broadcast_all({"type": "system", "text": f"{left_display} left the chat"})
        await broadcast_all({"type": "dm_cleanup", "username": left})
        await send_to_admin({"type": "dm_cleanup", "username": left})
        await send_user_list()
        await send_dm_pairs_to_admin()

    return ws


async def garlic_broadcast_state(room):
    players_info = [{"username": p["username"], "display_name": p.get("display_name", p["username"])} for p in room["players"]]
    for player in room["players"]:
        try:
            await player["ws"].send_str(json.dumps({
                "type": "garlic_state",
                "room_id": room["id"],
                "status": room["status"],
                "players": players_info,
                "is_host": player["username"] == room["host"]
            }))
        except Exception:
            pass


async def garlic_advance_round(room):
    n = len(room["players"])
    current_round = room["round"]
    prompt_type = "text" if current_round % 2 == 0 else "draw"
    for i in range(n):
        book_idx = (i + current_round) % n
        pname = room["players"][i]["username"]
        sub = room["submissions"].get(pname, "")
        room["chains"][book_idx].append({
            "type": prompt_type,
            "content": sub,
            "author": room["players"][i].get("display_name", pname)
        })
    room["round"] += 1
    room["submissions"] = {}
    if room["round"] >= room["total_rounds"]:
        room["status"] = "done"
        player_names = [p.get("display_name", p["username"]) for p in room["players"]]
        for player in room["players"]:
            try:
                await player["ws"].send_str(json.dumps({
                    "type": "garlic_reveal",
                    "room_id": room["id"],
                    "chains": room["chains"],
                    "players": player_names
                }))
            except Exception:
                pass
    else:
        new_round = room["round"]
        next_type = "text" if new_round % 2 == 0 else "draw"
        for i, player in enumerate(room["players"]):
            book_idx = (i + new_round) % n
            last = room["chains"][book_idx][-1] if room["chains"][book_idx] else None
            try:
                await player["ws"].send_str(json.dumps({
                    "type": "garlic_prompt",
                    "room_id": room["id"],
                    "round": new_round,
                    "prompt_type": next_type,
                    "prompt": last["content"] if last else None,
                    "prompt_was_type": last["type"] if last else "text",
                    "players_count": n,
                    "round_of": room["total_rounds"]
                }))
            except Exception:
                pass
        await garlic_broadcast_state(room)


async def handle_garlic_action(ws, username, data):
    action = data.get("action", "")
    display = connected.get(ws, {}).get("display_name", username)

    if action == "create":
        room_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        room = {
            "id": room_id, "host": username, "status": "lobby",
            "round": 0, "total_rounds": 0, "chains": [], "submissions": {},
            "players": [{"username": username, "display_name": display, "ws": ws}]
        }
        garlic_rooms[room_id] = room
        await garlic_broadcast_state(room)

    elif action == "join":
        room_id = data.get("room_id", "").strip().upper()
        room = garlic_rooms.get(room_id)
        if not room:
            await ws.send_str(json.dumps({"type": "garlic_error", "text": "Room not found."}))
            return
        if room["status"] != "lobby":
            await ws.send_str(json.dumps({"type": "garlic_error", "text": "Game already in progress."}))
            return
        if len(room["players"]) >= 8:
            await ws.send_str(json.dumps({"type": "garlic_error", "text": "Room is full (8 max)."}))
            return
        if any(p["username"] == username for p in room["players"]):
            await ws.send_str(json.dumps({"type": "garlic_error", "text": "Already in this room."}))
            return
        room["players"].append({"username": username, "display_name": display, "ws": ws})
        await garlic_broadcast_state(room)

    elif action == "start":
        room_id = data.get("room_id", "")
        room = garlic_rooms.get(room_id)
        if not room or room["host"] != username:
            await ws.send_str(json.dumps({"type": "garlic_error", "text": "Not the host."}))
            return
        if len(room["players"]) < 2:
            await ws.send_str(json.dumps({"type": "garlic_error", "text": "Need at least 2 players."}))
            return
        n = len(room["players"])
        room["status"] = "playing"
        room["round"] = 0
        room["total_rounds"] = n
        room["chains"] = [[] for _ in range(n)]
        room["submissions"] = {}
        for i, player in enumerate(room["players"]):
            try:
                await player["ws"].send_str(json.dumps({
                    "type": "garlic_prompt",
                    "room_id": room_id,
                    "round": 0,
                    "prompt_type": "text",
                    "prompt": None,
                    "prompt_was_type": None,
                    "players_count": n,
                    "round_of": n
                }))
            except Exception:
                pass
        await garlic_broadcast_state(room)

    elif action == "submit":
        room_id = data.get("room_id", "")
        room = garlic_rooms.get(room_id)
        if not room or room["status"] != "playing":
            return
        content = data.get("content", "")
        if not content:
            return
        room["submissions"][username] = content
        await ws.send_str(json.dumps({"type": "garlic_submitted"}))
        if len(room["submissions"]) >= len(room["players"]):
            await garlic_advance_round(room)

    elif action == "leave":
        room_id = data.get("room_id", "")
        if room_id in garlic_rooms:
            room = garlic_rooms[room_id]
            room["players"] = [p for p in room["players"] if p["username"] != username]
            if not room["players"]:
                del garlic_rooms[room_id]
            else:
                if room["host"] == username:
                    room["host"] = room["players"][0]["username"]
                await garlic_broadcast_state(room)


async def garlic_handle_disconnect(username):
    for room_id in list(garlic_rooms.keys()):
        room = garlic_rooms.get(room_id)
        if not room:
            continue
        if any(p["username"] == username for p in room["players"]):
            room["players"] = [p for p in room["players"] if p["username"] != username]
            if not room["players"]:
                del garlic_rooms[room_id]
            else:
                if room["host"] == username:
                    room["host"] = room["players"][0]["username"]
                if room["status"] == "playing":
                    room["submissions"].pop(username, None)
                    if len(room["submissions"]) >= len(room["players"]):
                        await garlic_advance_round(room)
                    else:
                        await garlic_broadcast_state(room)
                else:
                    await garlic_broadcast_state(room)


async def handle_api_register(request):
    try:
        data = await request.json()
    except Exception:
        return web.Response(text=json.dumps({"error": "Invalid JSON"}), content_type="application/json", status=400)
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    display_name = (data.get("display_name", "").strip() or username)[:30]
    if not USERNAME_RE.match(username):
        return web.Response(text=json.dumps({"error": "Username: 1-20 chars, letters/numbers/_/- only"}), content_type="application/json", status=400)
    if RESERVED_RE.search(username):
        return web.Response(text=json.dumps({"error": "Username cannot contain admin/mod/owner"}), content_type="application/json", status=400)
    if len(password) < 6:
        return web.Response(text=json.dumps({"error": "Password must be at least 6 characters"}), content_type="application/json", status=400)
    result = await db_register(username, password, display_name)
    if "error" in result:
        return web.Response(text=json.dumps(result), content_type="application/json", status=400)
    return web.Response(text=json.dumps(result), content_type="application/json")


async def handle_api_login(request):
    try:
        data = await request.json()
    except Exception:
        return web.Response(text=json.dumps({"error": "Invalid JSON"}), content_type="application/json", status=400)
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    result = await db_login(username, password)
    if "error" in result:
        return web.Response(text=json.dumps(result), content_type="application/json", status=401)
    return web.Response(text=json.dumps(result), content_type="application/json")


async def handle_api_profile_get(request):
    token = request.headers.get("X-Session-Token", "")
    user = await db_validate_session(token)
    if not user:
        return web.Response(text=json.dumps({"error": "Unauthorized"}), content_type="application/json", status=401)
    return web.Response(text=json.dumps(user), content_type="application/json")


async def handle_api_profile_update(request):
    token = request.headers.get("X-Session-Token", "")
    try:
        data = await request.json()
    except Exception:
        return web.Response(text=json.dumps({"error": "Invalid JSON"}), content_type="application/json", status=400)
    result = await db_update_profile(
        token,
        display_name=data.get("display_name"),
        bio=data.get("bio"),
        pfp_data=data.get("pfp_data")
    )
    if "error" in result:
        return web.Response(text=json.dumps(result), content_type="application/json", status=400)
    return web.Response(text=json.dumps(result), content_type="application/json")


async def handle_api_changelog_seen(request):
    token = request.headers.get("X-Session-Token", "")
    if request.method == "GET":
        should_show = await db_mark_changelog_seen(token, check_only=True)
        return web.Response(text=json.dumps({"show": should_show}), content_type="application/json")
    else:
        await db_mark_changelog_seen(token)
        return web.Response(text=json.dumps({"ok": True}), content_type="application/json")


import time as _ptime
from collections import OrderedDict as _OrdDict

_proxy_connector = None
_proxy_sessions = {}          # sid -> persistent ClientSession
_proxy_cache = _OrdDict()     # url -> (ts, body, ct) LRU cache for static resources
_PROXY_CACHE_MAX = 300
_PROXY_CACHE_TTL = 600        # 10 minutes


async def _get_proxy_connector():
    global _proxy_connector
    if _proxy_connector is None or _proxy_connector.closed:
        _proxy_connector = aiohttp.TCPConnector(
            ssl=False, limit=100, limit_per_host=6,
            keepalive_timeout=30, enable_cleanup_closed=True
        )
    return _proxy_connector


async def _get_proxy_session(sid):
    """Return a persistent session keyed by sid, or a fresh one-shot session."""
    global _proxy_sessions
    if sid and sid in _proxy_sessions and not _proxy_sessions[sid].closed:
        return _proxy_sessions[sid]
    connector = await _get_proxy_connector()
    jar = aiohttp.CookieJar(unsafe=True) if sid else aiohttp.DummyCookieJar()
    sess = aiohttp.ClientSession(connector=connector, connector_owner=False, cookie_jar=jar)
    if sid:
        _proxy_sessions[sid] = sess
    return sess


def _pcache_get(url):
    if url in _proxy_cache:
        ts, body, ct = _proxy_cache[url]
        if _ptime.time() - ts < _PROXY_CACHE_TTL:
            _proxy_cache.move_to_end(url)
            return body, ct
        del _proxy_cache[url]
    return None, None


def _pcache_set(url, body, ct):
    ct_lo = ct.lower()
    if not any(k in ct_lo for k in ('css', 'javascript', 'image/', 'font', 'woff', 'ttf', 'otf', 'svg')):
        return
    if len(body) > 2 * 1024 * 1024:
        return
    while len(_proxy_cache) >= _PROXY_CACHE_MAX:
        _proxy_cache.popitem(last=False)
    _proxy_cache[url] = (_ptime.time(), body, ct)


async def handle_proxy(request):
    import urllib.parse as _up
    import re as _re
    url = request.rel_url.query.get('url', '').strip()
    if not url or not (url.startswith('http://') or url.startswith('https://')):
        return web.Response(text='Bad URL', status=400, content_type='text/plain')

    req_method = request.method.upper()
    sid = request.rel_url.query.get('sid', '').strip()[:64]

    def _mp(u, base):
        if not u: return u
        u = u.strip()
        skip = ('data:', 'blob:', '#', 'javascript:', 'mailto:', 'tel:', 'about:', '/proxy?', 'chrome:', 'ws:', 'wss:')
        if any(u.startswith(p) for p in skip): return u
        if u.startswith('//'): u = 'https:' + u
        elif not u.startswith(('http://', 'https://')):
            try: u = _up.urljoin(base, u)
            except: return u
        sid_part = ('&sid=' + _up.quote(sid, safe='')) if sid else ''
        return '/proxy?url=' + _up.quote(u, safe='') + sid_part

    def _rewrite_html(text, base):
        def _ra(m):
            return m.group(1) + '=' + m.group(2) + _mp(m.group(3), base) + m.group(2)
        text = _re.sub(r'(?i)(src)=(["\'])([^"\'>\s]{1,2000})\2', _ra, text)
        text = _re.sub(r'(?i)(href)=(["\'])([^"\'>\s]{1,2000})\2', _ra, text)
        text = _re.sub(r'(?i)(action)=(["\'])([^"\'>\s]{1,2000})\2', _ra, text)
        safe_base = base.replace("'", "\\'")
        sid_js = sid.replace("'", "\\'")
        inject = (
            "<script>(function(){"
            "try{"
            "var _b='/proxy?url=';"
            "var _si='" + sid_js + "';"
            "function _p(u){"
            "if(!u||typeof u!=='string')return u;"
            "if(u.indexOf('/proxy?url=')===0||u.startsWith('data:')||u.startsWith('blob:')||u.startsWith('#')||u.startsWith('javascript:'))return u;"
            "if(u.startsWith('//'))u='https:'+u;"
            f"if(!/^https?:/i.test(u)){{try{{u=new URL(u,'{safe_base}').href;}}catch(e){{return u;}}}}"
            "return _b+encodeURIComponent(u)+(_si?'&sid='+encodeURIComponent(_si):'');}"
            "var _of=window.fetch;"
            "window.fetch=function(r,i){if(typeof r==='string')r=_p(r);return _of.call(this,r,i);};"
            "var _ox=XMLHttpRequest.prototype.open;"
            "XMLHttpRequest.prototype.open=function(m,u,a,us,p){return _ox.call(this,m,_p(u),a,us,p);};"
            "}catch(e){}"
            "})();</script>"
        )
        lo = text.lower()
        hi = lo.find('</head>')
        if hi >= 0: text = text[:hi] + inject + text[hi:]
        else: text = inject + text
        return text

    def _rewrite_css(text, base):
        def _rc(m):
            inner = m.group(1).strip().strip('"\'')
            return 'url("' + _mp(inner, base) + '")'
        return _re.sub(r'url\(([^)]{1,500})\)', _rc, text)

    # Serve from cache for GET static resources (instant)
    if req_method == 'GET':
        cached_body, cached_ct = _pcache_get(url)
        if cached_body is not None:
            resp_obj = web.Response(body=cached_body, status=200)
            resp_obj.content_type = cached_ct.split(';')[0].strip()
            resp_obj.headers['Access-Control-Allow-Origin'] = '*'
            resp_obj.headers['X-Frame-Options'] = 'ALLOWALL'
            resp_obj.headers['Content-Security-Policy'] = "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; frame-ancestors *"
            resp_obj.headers['Cache-Control'] = 'public, max-age=300'
            return resp_obj

    try:
        req_body = b''
        if req_method == 'POST':
            try: req_body = await request.read()
            except Exception: pass
        parsed = _up.urlparse(url)
        req_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Host': parsed.netloc,
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        timeout = aiohttp.ClientTimeout(total=20)
        session = await _get_proxy_session(sid)
        _req_kwargs = dict(headers=req_headers, allow_redirects=True, timeout=timeout)
        if req_method == 'POST':
            _req_kwargs['data'] = req_body
            _cm = session.post(url, **_req_kwargs)
        else:
            _cm = session.get(url, **_req_kwargs)
        async with _cm as resp:
            ct = resp.headers.get('Content-Type', 'text/html; charset=utf-8')
            final_url = str(resp.url)
            body = await resp.read()
            ct_lo = ct.lower()
            if 'html' in ct_lo:
                try:
                    text = body.decode('utf-8', errors='replace')
                    text = _rewrite_html(text, final_url)
                    body = text.encode('utf-8')
                except Exception:
                    pass
            elif 'css' in ct_lo:
                try:
                    text = body.decode('utf-8', errors='replace')
                    text = _rewrite_css(text, final_url)
                    body = text.encode('utf-8')
                except Exception:
                    pass
            else:
                # Cache CSS/JS/images/fonts for instant repeat loads
                _pcache_set(url, body, ct.split(';')[0].strip())
            resp_obj = web.Response(body=body, status=resp.status)
            resp_obj.content_type = ct.split(';')[0].strip()
            resp_obj.headers['Access-Control-Allow-Origin'] = '*'
            resp_obj.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            resp_obj.headers['Access-Control-Allow-Headers'] = '*'
            resp_obj.headers['X-Frame-Options'] = 'ALLOWALL'
            resp_obj.headers['Content-Security-Policy'] = "default-src * 'unsafe-inline' 'unsafe-eval' data: blob:; frame-ancestors *"
            return resp_obj
    except Exception as e:
        err_html = f'<html><body style="background:#1e2124;color:#fff;font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;flex-direction:column;gap:12px;"><div style="font-size:40px;">\U0001F6AB</div><div style="font-size:18px;font-weight:700;">Failed to load</div><div style="font-size:13px;color:#aaa;max-width:400px;text-align:center;">{e}</div></body></html>'
        return web.Response(text=err_html, status=502, content_type='text/html')


async def main():
    load_logs()
    await init_db()

    app = web.Application(client_max_size=1024 * 1024 * 5)
    app.router.add_get("/", handle_chat_page)
    app.router.add_get("/admin", handle_admin_page)
    app.router.add_post("/admin", handle_admin_page)
    app.router.add_get("/owner-ws", handle_owner_ws)
    app.router.add_get("/staff-ws", handle_staff_ws)
    app.router.add_get("/ws", handle_client_ws)
    app.router.add_post("/api/register", handle_api_register)
    app.router.add_post("/api/login", handle_api_login)
    app.router.add_get("/api/profile", handle_api_profile_get)
    app.router.add_post("/api/profile", handle_api_profile_update)
    app.router.add_get("/api/changelog-seen", handle_api_changelog_seen)
    app.router.add_post("/api/changelog-seen", handle_api_changelog_seen)
    app.router.add_get("/proxy", handle_proxy)
    app.router.add_post("/proxy", handle_proxy)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 5000)
    await site.start()


    print("=" * 50)
    print("  CHAT SERVER - OWNER PANEL")
    print("=" * 50)
    print()
    print("  Server running on port 5000")
    print()
    print("  OWNER URL (keep this secret!):")
    print(f"  /admin?token={OWNER_TOKEN}")
    print()
    print("  Friends open your Replit URL to chat.")
    print("  No token needed - just pick a username.")
    print()
    print("  Waiting for connections...")
    print("=" * 50)
    print()

    await asyncio.Future()

asyncio.run(main())
