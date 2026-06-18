"""Dice RPG — shared catalog data.

Single source of truth for the dice roster. Imported by server.py for the
gacha RNG / pity engine, and shipped to the client (via the dg_get_state
WebSocket message) so the Dex and combat engine render the same numbers.

Per-die SKILL BEHAVIOURS (how each skill/ult actually mutates battle state)
live in the client behaviour map inside games/dice_rpg.py, keyed by die id.
This file only holds JSON-serialisable DATA.
"""

# ─── Global combat constants ─────────────────────────────────────────────────
ELEMENTS = ["Fire", "Ice", "Electric", "Physical", "Arcane"]
RARITIES = ["COMMON", "RARE", "MYTHIC"]

ULT_COST   = {"COMMON": 60, "RARE": 80, "MYTHIC": 100}
RARITY_DIE = {"COMMON": 6,  "RARE": 10, "MYTHIC": 20}
DMG_MULT   = {"BASIC": 0.015, "SKILL": 0.045, "ULT": 0.18}
CRIT_MULT  = 1.5
CRIT_BASE  = 0.08  # ~8% baseline crit

BREAK_THRESHOLD = {"NORMAL": 100, "ELITE": 180, "BOSS": 300}
OMEN_TYPE_MULT  = {"NORMAL": 1.20, "ELITE": 1.10, "BOSS": 1.05}
OMEN_SOFT_CAP   = 9999
BROKEN_DMG_MULT = 1.30

# ─── Gacha / progression config ──────────────────────────────────────────────
PULL_COST            = 160
BEGINNER_PULL_COST   = 128   # -20%
BEGINNER_MAX_PULLS   = 50
BEGINNER_RARE_BY     = 10
BEGINNER_MYTHIC_BY   = 40
BATTLE_FIRST_CLEAR_REWARD = 50
# Campaign stage ids the server will honor for one-time first-clear rewards.
# Must stay in sync with the CAMPAIGN array in games/dice_rpg.py.
CAMPAIGN_STAGE_IDS = ["c1", "c2", "c3", "c4", "c5", "c6"]

BASE_RATES = {"MYTHIC": 0.01, "RARE": 0.05, "COMMON": 0.94}

# Mythic soft pity: pull index (1-based count since last mythic) -> rate.
# 1..69 = 1%, then ramps; hard pity at 89 = 100%.
MYTHIC_SOFT_PITY_START = 70
MYTHIC_HARD_PITY       = 89

# Duplicate -> constellation (max C6); overflow -> universal shards by rarity.
MAX_CONSTELLATION       = 6
UNIVERSAL_SHARD_YIELD   = {"COMMON": 5, "RARE": 20, "MYTHIC": 50}

# Universal constellation bonuses (applied in the client combat engine).
CONSTELLATION_BONUS = [
    {"level": 1, "desc": "+8% ATK"},
    {"level": 2, "desc": "+12% Max HP"},
    {"level": 3, "desc": "Skill effects +20%"},
    {"level": 4, "desc": "+10% DEF, +8% SPD"},
    {"level": 5, "desc": "Ultimate damage +25%"},
    {"level": 6, "desc": "+15% all damage dealt"},
]

HISTORY_MAX = 200
TEAM_SIZE   = 4

STARTER_DICE = ["green_pip", "chain_pip"]


def mythic_rate_at(pity):
    """Mythic probability given `pity` = pulls since last mythic (this pull is pity+1)."""
    n = pity + 1
    if n >= MYTHIC_HARD_PITY:
        return 1.0
    if n < MYTHIC_SOFT_PITY_START:
        return BASE_RATES["MYTHIC"]
    # 70->5%, +5% per pull, 89->100%
    steps = n - MYTHIC_SOFT_PITY_START  # 0 at pull 70
    return min(1.0, 0.05 + 0.05 * steps)


# ─── Dice roster ─────────────────────────────────────────────────────────────
# stats: hp / atk / def / spd.  params: numeric knobs read by the behaviour map.
DICE_CATALOG = [
    # ===== MYTHIC =====
    {
        "id": "omen_die", "name": "Omen Die", "rarity": "MYTHIC",
        "element": "Arcane", "role": "Omen Engine", "tags": ["Omen"],
        "stats": {"hp": 1280, "atk": 152, "def": 78, "spd": 103},
        "basic": {"name": "Ill Tidings", "desc": "Deal Arcane damage and apply 2 Omen."},
        "skill": {"name": "Mark of Fate", "desc": "Apply 12 Omen to a foe, then immediately trigger all of its Omen."},
        "ult":   {"name": "Inevitability", "desc": "AoE Arcane damage; trigger every foe's Omen 3 times and add 5 Omen to all."},
        "passive": {"name": "Cursed Synergy", "desc": "Allied hits apply Omen and never consume your Omen stacks."},
        "lore": "Every gambler swears they feel it coming. The Omen Die is that feeling, given six weighted faces.",
        "voice": "\u201cThe odds were never in your favor.\u201d",
        "params": {"basic_omen": 2, "skill_omen": 12, "ult_omen_triggers": 3, "ult_bonus_omen": 5},
    },
    {
        "id": "house_edge", "name": "House Edge", "rarity": "MYTHIC",
        "element": "Arcane", "role": "RNG Control", "tags": ["Fortune"],
        "stats": {"hp": 1240, "atk": 146, "def": 82, "spd": 108},
        "basic": {"name": "Double Down", "desc": "Roll two d20 and strike for the higher result as bonus damage."},
        "skill": {"name": "Rig the Table", "desc": "Grant the team +2 Fortune and guarantee their next rolls."},
        "ult":   {"name": "Reality Break", "desc": "On a natural 20, fracture the turn order: take an immediate extra action and amplify Omen & Break (2-turn cooldown)."},
        "passive": {"name": "The House Always Wins", "desc": "Roll twice for every fortune roll and keep your choice."},
        "lore": "The House never cheats. It simply owns every outcome before the dice leave your hand.",
        "voice": "\u201cPlace your bets. I already know how this ends.\u201d",
        "params": {"team_fortune": 2, "reality_cooldown": 2, "edge_bonus": 0.5},
    },

    # ===== RARE =====
    {
        "id": "split_fate", "name": "Split Fate", "rarity": "RARE",
        "element": "Physical", "role": "Multi-Hit DPS", "tags": ["Omen"],
        "stats": {"hp": 1080, "atk": 158, "def": 60, "spd": 110},
        "basic": {"name": "Quick Cut", "desc": "Deal Physical damage in a single strike."},
        "skill": {"name": "Threefold", "desc": "Strike 3 times; each hit applies Omen and detonates any Omen present."},
        "ult":   {"name": "Severance", "desc": "Unleash a flurry of cuts; bonus damage scaling with the target's Omen."},
        "passive": {"name": "Forked Path", "desc": "With no Omen Die present act as raw DPS; with one, scale every hit off Omen."},
        "lore": "Two futures, one blade. It cuts the timeline you don't want and bills you for the one you keep.",
        "voice": "\u201cHeads you lose. Tails I win.\u201d",
        "params": {"skill_hits": 3, "skill_omen": 1},
    },
    {
        "id": "loaded_clerk", "name": "Loaded Clerk", "rarity": "RARE",
        "element": "Electric", "role": "RNG Stabilizer", "tags": ["Fortune"],
        "stats": {"hp": 1160, "atk": 120, "def": 92, "spd": 99},
        "basic": {"name": "Tally", "desc": "Deal Electric damage and bank a little team energy."},
        "skill": {"name": "Minimum Wage", "desc": "For 2 turns no ally can roll below 30% of their die's maximum."},
        "ult":   {"name": "Audit", "desc": "Stabilise all variance: cleanse the team and grant guaranteed average rolls next turn."},
        "passive": {"name": "Cooked Books", "desc": "Reduces the team's roll variance every turn."},
        "lore": "He doesn't stop the dice from rolling. He just makes sure the ledger always balances in your favor.",
        "voice": "\u201cNumbers don't lie. I do.\u201d",
        "params": {"floor_pct": 0.30, "skill_turns": 2},
    },
    {
        "id": "flip_protocol", "name": "Flip Protocol", "rarity": "RARE",
        "element": "Arcane", "role": "Action Manipulator", "tags": ["Fortune"],
        "stats": {"hp": 1100, "atk": 130, "def": 74, "spd": 116},
        "basic": {"name": "Coin Toss", "desc": "Deal Arcane damage; on heads, gain extra energy."},
        "skill": {"name": "Hand Off", "desc": "Grant a chosen ally an immediate extra action."},
        "ult":   {"name": "Turn Inversion", "desc": "Reverse the initiative order and reroll an ally's last action for greater effect."},
        "passive": {"name": "Sleight", "desc": "Occasionally rerolls an ally's failed action."},
        "lore": "It never asks whose turn it is. It decides.",
        "voice": "\u201cYour move. No\u2014 mine.\u201d",
        "params": {"reroll_chance": 0.25},
    },
    {
        "id": "variance_weaver", "name": "Variance Weaver", "rarity": "RARE",
        "element": "Ice", "role": "RNG Converter", "tags": ["Fortune"],
        "stats": {"hp": 1140, "atk": 126, "def": 86, "spd": 101},
        "basic": {"name": "Thread Pull", "desc": "Deal Ice damage and store one RNG event."},
        "skill": {"name": "Weave", "desc": "Spend stored RNG events to buff the team or debuff foes."},
        "ult":   {"name": "Tapestry", "desc": "Convert all stored variance into a burst of buffs and Ice damage."},
        "passive": {"name": "Loomkeeper", "desc": "Every high or low roll on the field is stored as a thread."},
        "lore": "Luck is just thread. She collects the loose ends and weaves them into something that bites.",
        "voice": "\u201cEvery slip becomes a stitch.\u201d",
        "params": {"max_threads": 5},
    },
    {
        "id": "fracture_die", "name": "Fracture Die", "rarity": "RARE",
        "element": "Physical", "role": "Break DPS", "tags": ["Break"],
        "stats": {"hp": 1120, "atk": 162, "def": 66, "spd": 96},
        "basic": {"name": "Hairline", "desc": "Deal Physical damage and build Break value."},
        "skill": {"name": "Shatterpoint", "desc": "Heavy Break damage; bonus damage if the foe is already Broken."},
        "ult":   {"name": "Collapse", "desc": "Massive single-target hit that scales with the target's missing toughness."},
        "passive": {"name": "Stress Fractures", "desc": "Deals bonus damage to Broken enemies."},
        "lore": "Pressure is just patience with a deadline.",
        "voice": "\u201cEverything has a crack. I find it.\u201d",
        "params": {"broken_bonus": 0.5},
    },
    {
        "id": "signal_die", "name": "Signal Die", "rarity": "RARE",
        "element": "Electric", "role": "Energy Battery", "tags": ["Universal"],
        "stats": {"hp": 1150, "atk": 118, "def": 90, "spd": 107},
        "basic": {"name": "Ping", "desc": "Deal Electric damage and generate team energy."},
        "skill": {"name": "Broadcast", "desc": "Flood the team with energy and reduce cooldowns."},
        "ult":   {"name": "Uplink", "desc": "Charge the lowest-energy ally toward their Ultimate instantly."},
        "passive": {"name": "Carrier Wave", "desc": "Generates a trickle of team energy each turn."},
        "lore": "A relay tower for luck. It doesn't roll well\u2014it makes sure everyone else can.",
        "voice": "\u201cSignal's clear. Light 'em up.\u201d",
        "params": {"skill_energy": 12, "passive_energy": 3},
    },
    {
        "id": "relay_die", "name": "Relay Die", "rarity": "RARE",
        "element": "Arcane", "role": "Echo Support", "tags": ["Universal"],
        "stats": {"hp": 1130, "atk": 124, "def": 84, "spd": 100},
        "basic": {"name": "Relay", "desc": "Deal Arcane damage; mark an ally to be copied."},
        "skill": {"name": "Repeat", "desc": "Copy a chosen ally's last action at reduced power."},
        "ult":   {"name": "Cascade", "desc": "Replay the team's last actions in a weakened chain."},
        "passive": {"name": "Standing Wave", "desc": "Has a chance to echo allied skills."},
        "lore": "It has no moves of its own. It just believes very hard in yours.",
        "voice": "\u201cAgain. Do it again.\u201d",
        "params": {"copy_power": 0.6},
    },
    {
        "id": "amplifier_die", "name": "Amplifier Die", "rarity": "RARE",
        "element": "Fire", "role": "Damage Amp", "tags": ["Universal", "Break"],
        "stats": {"hp": 1110, "atk": 132, "def": 80, "spd": 104},
        "basic": {"name": "Spark", "desc": "Deal Fire damage and mark a foe."},
        "skill": {"name": "Overclock", "desc": "Increase the team's damage for 2 turns."},
        "ult":   {"name": "Resonance", "desc": "Greatly raise damage taken by all foes, especially while Broken."},
        "passive": {"name": "Gain Stage", "desc": "Boosts Break damage dealt by the team."},
        "lore": "Turns a whisper of luck into a scream.",
        "voice": "\u201cLouder. LOUDER.\u201d",
        "params": {"dmg_up": 0.25, "skill_turns": 2},
    },
    {
        "id": "tempo_die", "name": "Tempo Die", "rarity": "RARE",
        "element": "Ice", "role": "Speed Support", "tags": ["Universal"],
        "stats": {"hp": 1120, "atk": 122, "def": 82, "spd": 119},
        "basic": {"name": "Tick", "desc": "Deal Ice damage and nudge an ally forward in the order."},
        "skill": {"name": "Quicken", "desc": "Boost the team's Speed for 2 turns."},
        "ult":   {"name": "Stutter", "desc": "Delay every foe's next turn and hasten the team."},
        "passive": {"name": "Metronome", "desc": "Allies act slightly sooner each cycle."},
        "lore": "Time is a table game, and the Tempo Die keeps the dealer's rhythm.",
        "voice": "\u201cToo slow.\u201d",
        "params": {"spd_up": 0.20, "skill_turns": 2},
    },
    {
        "id": "stability_die", "name": "Stability Die", "rarity": "RARE",
        "element": "Physical", "role": "Cleanse / Tank", "tags": ["Universal"],
        "stats": {"hp": 1420, "atk": 104, "def": 120, "spd": 92},
        "basic": {"name": "Brace", "desc": "Deal Physical damage and gain a small shield."},
        "skill": {"name": "Steady Hand", "desc": "Cleanse the team and grant crowd-control resistance."},
        "ult":   {"name": "Bedrock", "desc": "Shield the whole team and taunt all foes."},
        "passive": {"name": "Anchor", "desc": "Reduces the team's chance to be disabled."},
        "lore": "When every other die is tumbling, this one simply refuses to move.",
        "voice": "\u201cHold the line.\u201d",
        "params": {"shield_pct": 0.18},
    },

    # ===== COMMON =====
    {
        "id": "green_pip", "name": "Green Pip", "rarity": "COMMON",
        "element": "Physical", "role": "Energy & Setup", "tags": ["Universal", "Omen"],
        "stats": {"hp": 980, "atk": 108, "def": 70, "spd": 100},
        "basic": {"name": "Nudge", "desc": "Deal damage, grant 3 energy and apply 1 Omen."},
        "skill": {"name": "Kickstart", "desc": "Apply 4 Omen and give the team 5 energy."},
        "ult":   {"name": "Green Light", "desc": "Apply 6 Omen and flood the team with 10 energy."},
        "passive": {"name": "Fresh Roll", "desc": "Starts each battle with bonus energy."},
        "lore": "The smallest pip on the cheapest die\u2014and somehow always where the run begins.",
        "voice": "\u201cGo, go, go!\u201d",
        "params": {"basic_energy": 3, "basic_omen": 1, "skill_omen": 4, "skill_energy": 5, "ult_omen": 6, "ult_energy": 10},
    },
    {
        "id": "chain_pip", "name": "Chain Pip", "rarity": "COMMON",
        "element": "Electric", "role": "Multi-Hit", "tags": ["Universal"],
        "stats": {"hp": 1000, "atk": 130, "def": 64, "spd": 105},
        "basic": {"name": "Link", "desc": "Deal Electric damage with a chance to strike twice."},
        "skill": {"name": "Chain Reaction", "desc": "Hit a random foe several times."},
        "ult":   {"name": "Overload", "desc": "Bounce lightning across all foes."},
        "passive": {"name": "Daisy Chain", "desc": "Each consecutive hit adds a little damage."},
        "lore": "One pip becomes two, two becomes a storm. Cheap, loud, effective.",
        "voice": "\u201cAnd again, and again!\u201d",
        "params": {"double_chance": 0.35, "skill_hits": 4},
    },
    {
        "id": "lucky_tapper", "name": "Lucky Tapper", "rarity": "COMMON",
        "element": "Fire", "role": "Crit Support", "tags": ["Fortune"],
        "stats": {"hp": 960, "atk": 116, "def": 68, "spd": 109},
        "basic": {"name": "Tap", "desc": "Deal Fire damage with raised crit chance."},
        "skill": {"name": "Hot Streak", "desc": "Boost the team's crit chance for 2 turns."},
        "ult":   {"name": "Jackpot", "desc": "Guarantee the team's next hits crit."},
        "passive": {"name": "Beginner's Luck", "desc": "Small permanent crit bonus to the team."},
        "lore": "Taps the table twice for luck before every roll. It actually works for them.",
        "voice": "\u201cFeelin' lucky!\u201d",
        "params": {"crit_up": 0.20, "skill_turns": 2},
    },
    {
        "id": "pressure_die", "name": "Pressure Die", "rarity": "COMMON",
        "element": "Ice", "role": "Defense Down", "tags": ["Break"],
        "stats": {"hp": 1020, "atk": 120, "def": 72, "spd": 98},
        "basic": {"name": "Press", "desc": "Deal Ice damage and lower the foe's DEF slightly."},
        "skill": {"name": "Vice", "desc": "Heavily reduce a foe's DEF for 2 turns."},
        "ult":   {"name": "Crush", "desc": "Shred the DEF of all foes and build Break."},
        "passive": {"name": "Weight", "desc": "Foes you hit take more damage briefly."},
        "lore": "It leans on the odds until they buckle.",
        "voice": "\u201cFeel that?\u201d",
        "params": {"def_down": 0.25, "skill_turns": 2},
    },
    {
        "id": "shield_fragment", "name": "Shield Fragment", "rarity": "COMMON",
        "element": "Physical", "role": "Shielder", "tags": ["Universal"],
        "stats": {"hp": 1180, "atk": 96, "def": 104, "spd": 94},
        "basic": {"name": "Chip", "desc": "Deal Physical damage and gain a tiny shield."},
        "skill": {"name": "Aegis", "desc": "Grant a flat shield to a chosen ally."},
        "ult":   {"name": "Bulwark", "desc": "Shield the entire team."},
        "passive": {"name": "Splinter", "desc": "Starts the battle with a small shield."},
        "lore": "A broken piece of a greater die, still stubbornly protecting everyone near it.",
        "voice": "\u201cGet behind me.\u201d",
        "params": {"shield_pct": 0.15},
    },
    {
        "id": "echo_die", "name": "Echo Die", "rarity": "COMMON",
        "element": "Arcane", "role": "Echo", "tags": ["Universal"],
        "stats": {"hp": 1000, "atk": 114, "def": 74, "spd": 102},
        "basic": {"name": "Mimic", "desc": "Deal Arcane damage and remember the action."},
        "skill": {"name": "Reverb", "desc": "Repeat your own last skill at reduced power."},
        "ult":   {"name": "Resound", "desc": "Echo the team's last ultimate weakly."},
        "passive": {"name": "Afterimage", "desc": "Small chance to repeat its own basic."},
        "lore": "Says nothing original, and yet you keep hearing it twice.",
        "voice": "\u201c...twice. ...twice.\u201d",
        "params": {"echo_power": 0.5},
    },
    {
        "id": "baseline_die", "name": "Baseline Die", "rarity": "COMMON",
        "element": "Electric", "role": "Energy", "tags": ["Universal"],
        "stats": {"hp": 1040, "atk": 110, "def": 78, "spd": 100},
        "basic": {"name": "Charge", "desc": "Deal Electric damage and gain energy."},
        "skill": {"name": "Top Up", "desc": "Give a chosen ally a chunk of energy."},
        "ult":   {"name": "Surge", "desc": "Restore energy to the whole team."},
        "passive": {"name": "Idle Current", "desc": "Slowly regenerates its own energy."},
        "lore": "The control group of dice. Boringly reliable, quietly essential.",
        "voice": "\u201cSteady as she goes.\u201d",
        "params": {"skill_energy": 15, "ult_energy": 10},
    },
]

# ─── Banner config ───────────────────────────────────────────────────────────
BANNERS = {
    "standard": {
        "id": "standard", "name": "Eternal Table",
        "subtitle": "Every permanent Dice. The House always has room at the table.",
        "type": "standard", "cost": PULL_COST, "featured": [],
    },
    "limited": {
        "id": "limited", "name": "Fractured Reality",
        "subtitle": "Featured: House Edge. When you win the 50/50, the House loses.",
        "type": "limited", "cost": PULL_COST,
        "featured_mythic": "house_edge",
        "featured_rares": ["flip_protocol", "variance_weaver", "loaded_clerk"],
    },
    "beginner": {
        "id": "beginner", "name": "Novice's Gambit",
        "subtitle": "First 50 pulls only \u2022 20% off \u2022 guaranteed Rare by 10, Mythic by 40.",
        "type": "beginner", "cost": BEGINNER_PULL_COST,
        "featured": [],
    },
}

# ─── Lookups ─────────────────────────────────────────────────────────────────
DICE_BY_ID = {d["id"]: d for d in DICE_CATALOG}
IDS_BY_RARITY = {
    r: [d["id"] for d in DICE_CATALOG if d["rarity"] == r] for r in RARITIES
}


def public_catalog():
    """Catalog plus global constants, shipped to the client."""
    return {
        "dice": DICE_CATALOG,
        "banners": BANNERS,
        "constants": {
            "ULT_COST": ULT_COST, "RARITY_DIE": RARITY_DIE, "DMG_MULT": DMG_MULT,
            "CRIT_MULT": CRIT_MULT, "CRIT_BASE": CRIT_BASE,
            "BREAK_THRESHOLD": BREAK_THRESHOLD, "OMEN_TYPE_MULT": OMEN_TYPE_MULT,
            "OMEN_SOFT_CAP": OMEN_SOFT_CAP, "BROKEN_DMG_MULT": BROKEN_DMG_MULT,
            "ELEMENTS": ELEMENTS, "TEAM_SIZE": TEAM_SIZE,
            "CONSTELLATION_BONUS": CONSTELLATION_BONUS,
            "MAX_CONSTELLATION": MAX_CONSTELLATION,
            "PULL_COST": PULL_COST, "BEGINNER_PULL_COST": BEGINNER_PULL_COST,
            "BEGINNER_MAX_PULLS": BEGINNER_MAX_PULLS,
            "BATTLE_FIRST_CLEAR_REWARD": BATTLE_FIRST_CLEAR_REWARD,
        },
    }
