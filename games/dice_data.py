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
BATTLE_FIRST_CLEAR_REWARD = 150  # paid in Gems (v4.0)
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

# Universal constellation bonuses (v4.0 redesign — EFFECTS / utility, never raw
# damage multipliers). Each level grants a battle-start or per-round buff that
# the client combat engine applies in buildAlly()/startBattle()/startRound().
#   key  = machine field the client switches on
#   val  = magnitude for that effect (meaning depends on key)
CONSTELLATION_BONUS = [
    {"level": 1, "key": "start_energy", "val": 15,
     "desc": "Start each battle with 15 Energy."},
    {"level": 2, "key": "max_hp", "val": 0.15,
     "desc": "+15% Max HP."},
    {"level": 3, "key": "skill_cd", "val": 1,
     "desc": "Skill cooldown reduced by 1 turn."},
    {"level": 4, "key": "def_spd", "val": 0.12,
     "desc": "+12% DEF and +12% SPD."},
    {"level": 5, "key": "start_shield", "val": 0.20,
     "desc": "Begin battle with a shield worth 20% of Max HP."},
    {"level": 6, "key": "revive", "val": 0.30,
     "desc": "Once per battle, revive at 30% HP when defeated."},
]

HISTORY_MAX = 200
TEAM_SIZE   = 4

STARTER_DICE = ["green_pip", "chain_pip"]

# ─── v4.0 Two-tier currency ──────────────────────────────────────────────────
# Balance (the chat-wide economy) -> Crystals : 1 : 1
# Crystals -> Gems (the in-game summon/upgrade currency) : 1 : 0.9
# Pulls and upgrades are paid in GEMS.
CRYSTAL_RATE = 1.0   # crystals received per 1 balance spent
GEM_RATE     = 0.9   # gems received per 1 crystal spent
STARTER_GEMS = 1600  # seeded so a new player can immediately 10-pull

# ─── v4.0 Premium bundle shop (small, intentionally not a cash grab) ──────────
# Bundles are bought with CRYSTALS. "gems" bundles convert at a better rate than
# the raw 0.9; "select" bundles grant a die of the player's choice.
BUNDLES = [
    {"id": "gem_pouch",  "name": "Pouch of Gems", "cost_crystals": 500,
     "grant": "gems", "gems": 550,
     "desc": "550 Gems for 500 Crystals — a little better than the table rate."},
    {"id": "gem_chest",  "name": "Chest of Gems", "cost_crystals": 2000,
     "grant": "gems", "gems": 2400, "best": True,
     "desc": "2,400 Gems for 2,000 Crystals — the best Gem value on offer."},
    {"id": "rare_choice", "name": "Rare of Choice", "cost_crystals": 3000,
     "grant": "select", "select_rarity": "RARE",
     "desc": "Pick any Rare die and add it straight to your collection."},
    {"id": "mythic_choice", "name": "Mythic of Choice", "cost_crystals": 14000,
     "grant": "select", "select_rarity": "MYTHIC",
     "desc": "Choose any Mythic die. The grand prize — saved for, never gambled."},
]
BUNDLES_BY_ID = {b["id"]: b for b in BUNDLES}

# ─── v4.0 Endless arena milestone rewards (one-time, by best wave reached) ────
# Claimable once each, in ascending order, only up to the player's best wave.
ENDLESS_MILESTONES = [
    {"wave": 10,  "gems": 300,  "crystals": 0,    "shards": 0},
    {"wave": 25,  "gems": 800,  "crystals": 0,    "shards": 20},
    {"wave": 50,  "gems": 2000, "crystals": 500,  "shards": 0},
    {"wave": 100, "gems": 5000, "crystals": 1500, "shards": 100},
]
MILESTONE_WAVES = [m["wave"] for m in ENDLESS_MILESTONES]
MILESTONES_BY_WAVE = {m["wave"]: m for m in ENDLESS_MILESTONES}

# ─── v4.0 Endless scaling (read by the client wave spawner) ───────────────────
ENDLESS_SCALE = {
    "hp_per_wave":   0.20,   # +20% enemy HP per wave
    "atk_per_wave":  0.12,   # +12% enemy ATK per wave
    "spd_per_wave":  0.010,  # +1% enemy SPD per wave
    "break_per_wave": 0.06,  # +6% enemy toughness (break resistance) per wave
    "elite_mult": 1.8, "boss_mult": 3.4,
}

# ─── v4.0 Dice ascension (Universal Shard sink → flat stat growth) ────────────
# Ascension is a separate progression from constellations. Levels cost shards
# and grant flat stat growth (this is a deliberate power sink, distinct from
# constellations which only grant utility effects).
ASCENSION_MAX_LEVEL = 6
# Cumulative cost reference is per-step; index i = cost to go from level i to i+1.
ASCENSION_STEP_COST = {
    "COMMON": [30, 50, 80, 120, 180, 260],
    "RARE":   [60, 100, 160, 240, 360, 520],
    "MYTHIC": [120, 200, 320, 480, 720, 1040],
}
ASCENSION_STAT_PER_LEVEL = 0.06  # +6% hp/atk/def per ascension level

# ─── v4.0 Achievements (server-verifiable from dice state; claim once each) ────
# "check" is interpreted by the server against the player's dice state.
ACHIEVEMENTS = [
    {"id": "first_summon", "name": "First Roll", "check": "pulls>=1",
     "gems": 100, "crystals": 0, "shards": 0,
     "desc": "Summon for the very first time."},
    {"id": "collector_10", "name": "Getting a Set", "check": "owned>=10",
     "gems": 400, "crystals": 0, "shards": 0,
     "desc": "Own 10 different dice."},
    {"id": "collector_all", "name": "Full House", "check": "owned>=all",
     "gems": 1500, "crystals": 500, "shards": 0,
     "desc": "Collect every die in the Dex."},
    {"id": "own_mythic", "name": "Touch of Fate", "check": "mythic>=1",
     "gems": 300, "crystals": 0, "shards": 0,
     "desc": "Own at least one Mythic die."},
    {"id": "clear_campaign", "name": "Beat the House", "check": "cleared_c6",
     "gems": 800, "crystals": 0, "shards": 0,
     "desc": "Clear the final campaign stage, The House Edge."},
    {"id": "wave_25", "name": "Survivor", "check": "best_wave>=25",
     "gems": 600, "crystals": 0, "shards": 30,
     "desc": "Reach wave 25 in the Endless Arena."},
    {"id": "ascend_die", "name": "Reforged", "check": "ascended>=1",
     "gems": 300, "crystals": 0, "shards": 0,
     "desc": "Ascend any die at least once."},
    {"id": "const_six", "name": "Perfect Six", "check": "const6>=1",
     "gems": 800, "crystals": 0, "shards": 0,
     "desc": "Bring any die to Constellation 6."},
]
ACHIEVEMENTS_BY_ID = {a["id"]: a for a in ACHIEVEMENTS}

# ─── v4.0 Battle pacing / speed options (client UX only) ──────────────────────
SPEED_OPTIONS = [0.75, 1.0, 1.5]

# ─── v4.0 Team presets ───────────────────────────────────────────────────────
TEAM_PRESET_SLOTS = 3

# ─── v4.0 Recommended team comps (archetype guides, by die id) ────────────────
TEAM_COMPS = [
    {"id": "omen", "name": "Omen Doom", "primary": "Omen",
     "desc": "Pile Omen onto a foe, then detonate it for huge Arcane bursts.",
     "core": ["omen_die", "split_fate", "green_pip"], "flex": "house_edge"},
    {"id": "break", "name": "Break Burst", "primary": "Break",
     "desc": "Shatter enemy toughness, then crush them while Broken.",
     "core": ["fracture_die", "pressure_die", "amplifier_die"], "flex": "signal_die"},
    {"id": "fortune", "name": "Fortune Engine", "primary": "Fortune",
     "desc": "Bend the dice: floor your rolls high and crit constantly.",
     "core": ["house_edge", "loaded_clerk", "lucky_tapper"], "flex": "flip_protocol"},
    {"id": "universal", "name": "Universal Goodstuff", "primary": "Universal",
     "desc": "Energy, shields and speed — a reliable team for any fight.",
     "core": ["signal_die", "stability_die", "tempo_die"], "flex": "amplifier_die"},
]


def ascension_step_cost(rarity, level):
    """Shard cost to go from `level` to `level+1` for a die of `rarity`.
    Returns None if already at max."""
    steps = ASCENSION_STEP_COST.get(rarity, ASCENSION_STEP_COST["COMMON"])
    if level < 0 or level >= ASCENSION_MAX_LEVEL or level >= len(steps):
        return None
    return steps[level]


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
            # v4.0
            "CRYSTAL_RATE": CRYSTAL_RATE, "GEM_RATE": GEM_RATE,
            "STARTER_GEMS": STARTER_GEMS,
            "BUNDLES": BUNDLES,
            "ENDLESS_MILESTONES": ENDLESS_MILESTONES,
            "ENDLESS_SCALE": ENDLESS_SCALE,
            "ASCENSION_MAX_LEVEL": ASCENSION_MAX_LEVEL,
            "ASCENSION_STEP_COST": ASCENSION_STEP_COST,
            "ASCENSION_STAT_PER_LEVEL": ASCENSION_STAT_PER_LEVEL,
            "ACHIEVEMENTS": ACHIEVEMENTS,
            "SPEED_OPTIONS": SPEED_OPTIONS,
            "TEAM_PRESET_SLOTS": TEAM_PRESET_SLOTS,
            "TEAM_COMPS": TEAM_COMPS,
        },
    }
