"""Dice RPG — shared catalog data.

Single source of truth for the dice roster. Imported by server.py for the
gacha RNG / pity engine, and shipped to the client (via the dg_get_state
WebSocket message) so the Dex and combat engine render the same numbers.

Per-die SKILL BEHAVIOURS (how each skill/ult actually mutates battle state)
live in the client behaviour map inside games/dice_rpg.py, keyed by die id.
This file only holds JSON-serialisable DATA.
"""

# ─── Global combat constants ─────────────────────────────────────────────────
# Original five elements form one advantage cycle; the nine expansion elements
# form a second, independent cycle. Cross-cycle matchups are neutral (1.0).
ELEMENTS = [
    "Fire", "Ice", "Electric", "Physical", "Arcane",
    "Light", "Dark", "Blood", "Poison", "Nature", "Wind", "Time", "Void", "Earth",
]
# Display colours for every element (consumed by the client to build --e-* vars).
ELEMENT_COLORS = {
    "Fire": "#ff6b4a", "Ice": "#5fd0ff", "Electric": "#ffe14a",
    "Physical": "#d6a07a", "Arcane": "#c98bff",
    "Light": "#ffe9a8", "Dark": "#8b7bd6", "Blood": "#ff4d6d",
    "Poison": "#bff04a", "Nature": "#5fd17a", "Wind": "#86e8d0",
    "Time": "#7fb8ff", "Void": "#b15be0", "Earth": "#c8975a",
}
RARITIES = ["COMMON", "RARE", "LEGENDARY", "MYTHIC", "ETERNAL"]

ULT_COST   = {"COMMON": 60, "RARE": 80, "LEGENDARY": 90, "MYTHIC": 100, "ETERNAL": 110}
RARITY_DIE = {"COMMON": 6,  "RARE": 10, "LEGENDARY": 12, "MYTHIC": 20, "ETERNAL": 24}
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

BASE_RATES = {"COMMON": 0.87, "RARE": 0.09, "LEGENDARY": 0.03, "MYTHIC": 0.009, "ETERNAL": 0.001}

# Mythic soft pity: pull index (1-based count since last mythic) -> rate.
# 1..69 = 1%, then ramps; hard pity at 89 = 100%.
MYTHIC_SOFT_PITY_START = 70
MYTHIC_HARD_PITY       = 89

# Duplicate -> constellation (max C6); overflow -> universal shards by rarity.
MAX_CONSTELLATION       = 6
UNIVERSAL_SHARD_YIELD   = {"COMMON": 5, "RARE": 20, "LEGENDARY": 35, "MYTHIC": 50, "ETERNAL": 90}

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

# ─── Engine tags + team synergy ──────────────────────────────────────────────
# Each die belongs to one or more ENGINE families (its "engine" field). When a
# battle team fields 3+ dice sharing an engine, the whole team gains a synergy
# bonus the client applies at startBattle().
ENGINE_TAGS = [
    "Omen", "Fracture", "Break", "Energy", "Combo",
    "Sustain", "Fortune", "Summon", "Control",
]
ENGINE_SYNERGY = {
    "Omen":     {"min": 3, "name": "Cursed Convergence",
                 "desc": "+25% Omen applied and triggered Omen deals +15% damage.",
                 "effect": {"omen_apply": 0.25, "omen_dmg": 0.15}},
    "Fracture": {"min": 3, "name": "Total Collapse",
                 "desc": "Enemies start with +3 Fracture and gain +25% more Fracture.",
                 "effect": {"start_fracture": 3, "fracture_gain": 0.25}},
    "Break":    {"min": 3, "name": "Pressure Doctrine",
                 "desc": "+25% Break buildup; Broken enemies take an extra +10% damage.",
                 "effect": {"break_gain": 0.25, "broken_dmg": 0.10}},
    "Energy":   {"min": 3, "name": "Power Grid",
                 "desc": "Team starts with +20 Energy and gains +15% Energy all battle.",
                 "effect": {"start_energy": 20, "energy_gain": 0.15}},
    "Combo":    {"min": 3, "name": "Perfect Sequence",
                 "desc": "Combo never resets on the first miss and starts at +3.",
                 "effect": {"start_combo": 3, "combo_safe": 1}},
    "Sustain":  {"min": 3, "name": "Bulwark Order",
                 "desc": "+20% shields and +20% healing for the whole team.",
                 "effect": {"shield": 0.20, "heal": 0.20}},
    "Fortune":  {"min": 3, "name": "Loaded Dice",
                 "desc": "The team gains +1 Fortune and rolls more consistently.",
                 "effect": {"fortune": 1}},
    "Summon":   {"min": 3, "name": "Standing Army",
                 "desc": "All summoned units inherit +20% of their owner's stats.",
                 "effect": {"summon_pct": 0.20}},
    "Control":  {"min": 3, "name": "Iron Grip",
                 "desc": "Crowd-control effects last +1 turn and enemies act 10% slower.",
                 "effect": {"cc_turns": 1, "enemy_spd": -0.10}},
}

# ─── Status / mechanic codex (tooltip text shipped to the client) ────────────
STATUS_INFO = {
    "Omen":        "Stacking curse. When triggered it detonates for 1.2x stacks as damage, then halves. Does not crit.",
    "Fracture":    "Structural stress. 5+ = Exposed (+15% damage taken); 10+ = Shattered (+30% damage & extra Break); 15+ = Collapse (a burst of stored Fracture damage).",
    "Exposed":     "5+ Fracture. The enemy takes +15% damage from all sources.",
    "Shattered":   "10+ Fracture. The enemy takes +30% damage and double Break buildup.",
    "Chill":       "Cold stacks. Each removes 1 SPD (min 20). At 10 the enemy is Frozen.",
    "Frozen":      "Skips its next action and takes +25% damage until it thaws.",
    "Plague":      "Poison-over-time. Spreads between enemies and explodes via Plague skills.",
    "Gravity":     "Weight stacks. Each removes 2 SPD (max -20). At 5 the enemy is Weighed Down.",
    "WeighedDown": "5+ Gravity. -20 SPD and +15% damage taken.",
    "Collapse":    "Void pressure. At 5 the enemy can't gain buffs and takes +20% damage; resistance erodes per stack.",
    "Combo":       "Shared momentum counter. Spent by chain attacks for one hit per stack; resets on a miss.",
    "Jackpot":     "Luck meter built by attacking, critting and taking damage. At 100 the Jackpot Die transforms instead of spending Energy.",
    "Bleed":       "Blood-over-time. Bleeding enemies take extra damage; amplified and detonated by Blood dice.",
    "Break":       "Toughness gauge. When filled the enemy is Broken: +30% damage taken and disables land freely.",
    "Energy":      "Fills each turn by your die roll; spend it on Ultimates. Many dice give, steal or distribute it.",
    "Shield":      "A temporary buffer that soaks damage before HP.",
    "Mirage":      "Illusions that can intercept attacks for allies and explode when destroyed.",
    "Dodge":       "Chance to completely avoid an incoming attack.",
    "Retribution": "Counter charge. Guarded units counterattack when struck; counters grow stronger as they land.",
    "Anomaly":     "A combat rule temporarily rewritten by Fate (e.g. +20% global damage, doubled Energy).",
    "Evolution":   "Permanent mid-battle mutations chosen by Genesis; stack and can be doubled.",
    "Eclipse":     "Form toggle — Day form supports and shields, Night form deals heavy damage with lifesteal.",
    "TimeMark":    "A temporal mark; Delay against a marked enemy becomes a full stun.",
    "Stun":        "The enemy loses its next action entirely.",
    "Summon":      "Allied token units that act in the turn order and copy a share of their owner's stats.",
    "Mutation":    "A stacking permanent buff (ATK/DEF/SPD/Healing) granted by Evolution dice.",
    "Echo":        "Stored memory of ally actions that can be repeated at reduced power.",
    "Resonance":   "A stacking charge. Once enough stacks are built, the die's next action is empowered and the stacks are spent.",
    "Overload":    "A self-inflicted ATK surge with recoil: the die hits far harder but pays a share of the boost in HP.",
    "Lifesteal":   "The die heals for a fraction of the damage it deals.",
    "Reflect":     "A portion of incoming damage is bounced straight back at the attacker.",
    "Execute":     "Attacks against low-HP foes below a threshold deal massive bonus damage.",
    "Ramp":        "The die's ATK grows a little every round, snowballing the longer the fight lasts.",
    "ShieldBreak": "Bonus damage dealt to shielded targets, tearing through buffers fast.",
    "TwinStrike":  "The basic attack lands twice in one action.",
    "Aura":        "A passive team-wide buff to ATK and/or DEF that persists while the die is alive.",
    "Decay":       "Reduces the healing enemies receive, capping their recovery.",
}

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

# ─── v7.0 Relic / Gear system ─────────────────────────────────────────────────
# Relics are equippable gear bought with Crystals. One relic per die; each
# owned copy can only be equipped on one die at a time. Stats are applied
# client-side at unit build (hp_pct/atk_pct/def_pct/spd_pct/spd_flat/
# start_energy/start_shield/heal_recv). Ownership + equips persist in
# campaign.relics = {"owned": {relic_id: count}, "equipped": {die_id: relic_id}}.
RELICS = [
    # Tier 1 — Worn (300 Crystals)
    {"id": "iron_totem",    "name": "Iron Totem",         "tier": "WORN",     "cost": 300,
     "icon": "\u265F", "stat": {"hp_pct": 0.08},
     "desc": "+8% HP. A humble charm carved from meteoric iron."},
    {"id": "whetstone",     "name": "Ancient Whetstone",  "tier": "WORN",     "cost": 300,
     "icon": "\u2694", "stat": {"atk_pct": 0.06},
     "desc": "+6% ATK. Every edge it touches remembers being sharp."},
    {"id": "swift_charm",   "name": "Swift Charm",        "tier": "WORN",     "cost": 300,
     "icon": "\u21AF", "stat": {"spd_flat": 4},
     "desc": "+4 SPD. It hums when the wearer starts running."},
    {"id": "guard_sigil",   "name": "Guard Sigil",        "tier": "WORN",     "cost": 300,
     "icon": "\u26E8", "stat": {"def_pct": 0.08},
     "desc": "+8% DEF. Pressed into shields before every siege."},
    # Tier 2 — Honed (900 Crystals)
    {"id": "vital_core",    "name": "Vital Core",         "tier": "HONED",    "cost": 900,
     "icon": "\u2764", "stat": {"hp_pct": 0.15},
     "desc": "+15% HP. A crystallized heartbeat that never tires."},
    {"id": "war_banner",    "name": "War Banner",         "tier": "HONED",    "cost": 900,
     "icon": "\u2691", "stat": {"atk_pct": 0.10},
     "desc": "+10% ATK. Armies rally to it; dice do too."},
    {"id": "gale_boots",    "name": "Gale Boots",         "tier": "HONED",    "cost": 900,
     "icon": "\u2708", "stat": {"spd_pct": 0.08},
     "desc": "+8% SPD. Stitched from a storm that refused to end."},
    {"id": "aegis_plate",   "name": "Aegis Plate",        "tier": "HONED",    "cost": 900,
     "icon": "\u26CA", "stat": {"def_pct": 0.12, "start_shield": 0.05},
     "desc": "+12% DEF, start with a 5% shield. Dented, never pierced."},
    # Tier 3 — Exalted (2,200 Crystals)
    {"id": "titan_heart",   "name": "Titan Heart",        "tier": "EXALTED",  "cost": 2200,
     "icon": "\u26F0", "stat": {"hp_pct": 0.22, "def_pct": 0.06},
     "desc": "+22% HP, +6% DEF. Still beating. Try not to think about it."},
    {"id": "executioner",   "name": "Executioner's Brand","tier": "EXALTED",  "cost": 2200,
     "icon": "\u2020", "stat": {"atk_pct": 0.16},
     "desc": "+16% ATK. The verdict is always the same."},
    {"id": "stormstride",   "name": "Stormstride",        "tier": "EXALTED",  "cost": 2200,
     "icon": "\u26A1", "stat": {"spd_pct": 0.12, "start_energy": 15},
     "desc": "+12% SPD, start with 15 energy. Arrives before the thunder."},
    {"id": "sanctum_ward",  "name": "Sanctum Ward",       "tier": "EXALTED",  "cost": 2200,
     "icon": "\u269C", "stat": {"start_shield": 0.15, "heal_recv": 0.10},
     "desc": "Start with a 15% shield, +10% healing received. Holy ground, portable."},
    # Tier 4 — Transcendent (4,500 Crystals)
    {"id": "world_engine",  "name": "World Engine",       "tier": "TRANSCENDENT", "cost": 4500,
     "icon": "\u2699", "stat": {"atk_pct": 0.15, "hp_pct": 0.15},
     "desc": "+15% ATK, +15% HP. A fragment of the machine that turns the sky."},
    {"id": "chrono_locket", "name": "Chrono Locket",      "tier": "TRANSCENDENT", "cost": 4500,
     "icon": "\u23F3", "stat": {"start_energy": 30, "spd_flat": 6},
     "desc": "Start with 30 energy, +6 SPD. It ticks backwards on purpose."},
    {"id": "eternity_shell","name": "Eternity Shell",     "tier": "TRANSCENDENT", "cost": 4500,
     "icon": "\u26E9", "stat": {"def_pct": 0.20, "start_shield": 0.20, "heal_recv": 0.10},
     "desc": "+20% DEF, 20% start shield, +10% healing received. Outlives its wearers."},
    {"id": "apex_idol",     "name": "Apex Idol",          "tier": "TRANSCENDENT", "cost": 4500,
     "icon": "\u265B", "stat": {"atk_pct": 0.20, "spd_pct": 0.05},
     "desc": "+20% ATK, +5% SPD. Worshipped by everything that hunts."},
]
RELICS_BY_ID = {r["id"]: r for r in RELICS}
RELIC_TIER_COLORS = {"WORN": "#9aa3b8", "HONED": "#a77bff", "EXALTED": "#ff9d5c", "TRANSCENDENT": "#ffce5a"}

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
    "COMMON":    [30, 50, 80, 120, 180, 260],
    "RARE":      [60, 100, 160, 240, 360, 520],
    "LEGENDARY": [90, 150, 240, 360, 540, 780],
    "MYTHIC":    [120, 200, 320, 480, 720, 1040],
    "ETERNAL":   [200, 340, 540, 820, 1240, 1800],
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
SPEED_OPTIONS = [0.75, 1.0, 1.5, 2.0]

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

    # ═══════════════════════════════════════════════════════════════════════
    # ===== EXPANSION: MYTHIC (16) =====
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "absolute_zero", "name": "Absolute Zero", "rarity": "MYTHIC",
        "element": "Ice", "role": "Freeze Engine", "tags": ["Control"], "engine": ["Control"],
        "stats": {"hp": 1320, "atk": 148, "def": 92, "spd": 98},
        "basic": {"name": "Cold Truth", "desc": "Deal Ice damage and apply 1 Chill stack."},
        "skill": {"name": "Deep Freeze", "desc": "Apply 5 Chill to all enemies. At 10 Chill a foe is Frozen: it skips its next action and takes +25% damage."},
        "ult":   {"name": "Heat Death", "desc": "All enemies gain 8 Chill. For 2 turns Chill cannot decay and Frozen foes take double Break damage."},
        "passive": {"name": "Frozen State", "desc": "Enemies lose 1 SPD per Chill stack (minimum SPD 20)."},
        "lore": "When Absolute Zero arrives, time itself forgets how to flow.",
        "voice": "\u201cThe world does not move. It waits.\u201d",
        "params": {"basic_chill": 1, "skill_chill_all": 5, "ult_chill_all": 8, "chill_lock_turns": 2, "freeze_at": 10},
        "cons": [
            {"level": 1, "desc": "Start battle with 3 Chill on all enemies."},
            {"level": 2, "stat": {"def_pct": 0.15}, "desc": "+15% DEF."},
            {"level": 3, "desc": "Deep Freeze applies 7 Chill instead."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Frozen enemies take +10% extra damage from all sources."},
            {"level": 6, "desc": "Frozen enemies have a 20% chance to skip an additional turn after thawing."},
        ],
    },
    {
        "id": "plague_die", "name": "Plague Die", "rarity": "MYTHIC",
        "element": "Poison", "role": "Spread Engine", "tags": ["Omen"], "engine": ["Omen"],
        "stats": {"hp": 1280, "atk": 150, "def": 78, "spd": 103},
        "basic": {"name": "Infect", "desc": "Deal Poison damage and apply 2 Plague stacks."},
        "skill": {"name": "Contagion", "desc": "Spread all Plague from the target to every enemy, then increase total Plague by 30%."},
        "ult":   {"name": "Pandemic Bloom", "desc": "All enemies take damage equal to 40% of their Plague stacks, then Plague spreads again."},
        "passive": {"name": "Unstoppable Spread", "desc": "When an enemy dies with Plague, it spreads to a random living enemy."},
        "lore": "Everything it touches becomes everything else.",
        "voice": "\u201cOne infection is an accident. Two is a strategy.\u201d",
        "params": {"basic_plague": 2, "spread_bonus": 0.30, "ult_plague_pct": 0.40},
        "cons": [
            {"level": 1, "desc": "Start battle with 5 Plague on a random enemy."},
            {"level": 2, "stat": {"atk_pct": 0.15}, "desc": "+15% ATK."},
            {"level": 3, "desc": "Spread bonus increased to 50%."},
            {"level": 4, "stat": {"hp_pct": 0.12}, "desc": "+12% HP."},
            {"level": 5, "desc": "Pandemic Bloom deals +20% damage."},
            {"level": 6, "desc": "Plague can spread twice per turn."},
        ],
    },
    {
        "id": "singularity_die", "name": "Singularity Die", "rarity": "MYTHIC",
        "element": "Void", "role": "Collapse Engine", "tags": ["Control"], "engine": ["Control"],
        "stats": {"hp": 1350, "atk": 158, "def": 85, "spd": 100},
        "basic": {"name": "Pull", "desc": "Deal Void damage and apply 1 Collapse stack."},
        "skill": {"name": "Event Horizon", "desc": "Pull all enemies in. Foes with 5+ Collapse cannot gain buffs and take +20% damage."},
        "ult":   {"name": "End of Everything", "desc": "Create a Singularity for 2 turns. Each turn end: deal Void damage to all, +2 Collapse, and reduce enemy action speed by 30%."},
        "passive": {"name": "Gravitational End", "desc": "Enemies lose resistance every time they gain Collapse."},
        "lore": "Even victory has weight.",
        "voice": "\u201cEverything returns to nothing.\u201d",
        "params": {"basic_collapse": 1, "skill_collapse_all": 0, "ult_turns": 2, "ult_collapse_tick": 2, "collapse_at": 5},
        "cons": [
            {"level": 1, "desc": "Start battle with 2 Collapse on all enemies."},
            {"level": 2, "stat": {"def_pct": 0.15}, "desc": "+15% DEF."},
            {"level": 3, "desc": "Event Horizon applies 3 extra Collapse."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Singularity lasts 1 additional turn."},
            {"level": 6, "desc": "Enemies at max Collapse are removed from the action order for 1 turn."},
        ],
    },
    {
        "id": "dominion_prime", "name": "Dominion Prime", "rarity": "MYTHIC",
        "element": "Arcane", "role": "Summon Engine", "tags": ["Summon"], "engine": ["Summon"],
        "stats": {"hp": 1380, "atk": 146, "def": 88, "spd": 99},
        "basic": {"name": "Summon Shard", "desc": "Summon a Prime Fragment inheriting 35% of Dominion Prime's stats."},
        "skill": {"name": "Command Chain", "desc": "All summoned units act immediately after Dominion Prime and gain bonus damage this turn."},
        "ult":   {"name": "Full Dominion", "desc": "Summon 4 Prime Fragments. For 3 turns summons act twice per turn, on-hit effects duplicate, and summons cannot be one-shot."},
        "passive": {"name": "Army of One", "desc": "Each summon increases Dominion Prime's damage by 6% (max 6 summons)."},
        "lore": "The die does not fight alone. It commands existence.",
        "voice": "\u201cKneel. Or be counted among the fallen.\u201d",
        "params": {"summon_basic": 1, "summon_pct": 0.35, "ult_summons": 4, "summon_max": 6, "dmg_per_summon": 0.06, "ult_turns": 3},
        "cons": [
            {"level": 1, "desc": "Start battle with 1 Fragment."},
            {"level": 2, "stat": {"hp_pct": 0.15}, "desc": "+15% HP."},
            {"level": 3, "desc": "Fragments inherit 45% of stats."},
            {"level": 4, "stat": {"atk_pct": 0.12}, "desc": "+12% ATK."},
            {"level": 5, "desc": "Summons gain a partial Break effect on hit."},
            {"level": 6, "desc": "When a summon is defeated, replace it once per turn automatically."},
        ],
    },
    {
        "id": "fate_anomaly", "name": "Fate Anomaly", "rarity": "MYTHIC",
        "element": "Arcane", "role": "Rule Break Engine", "tags": ["Fortune"], "engine": ["Fortune"],
        "stats": {"hp": 1310, "atk": 152, "def": 86, "spd": 107},
        "basic": {"name": "Distort", "desc": "Deal Arcane damage and apply 1 Anomaly stack."},
        "skill": {"name": "Rewrite Variable", "desc": "Randomly alter one combat rule for 2 turns: +20% global damage, doubled Energy gain, -30% Break threshold, or disabled Omen decay. Only one anomaly may exist at once."},
        "ult":   {"name": "System Collapse", "desc": "For 2 turns all combat rules become unstable: buffs may double or halve, turn order shifts, and statuses behave unpredictably."},
        "passive": {"name": "Unstable Reality", "desc": "Every anomaly activation grants the team Energy."},
        "lore": "This die does not follow systems \u2014 it edits them.",
        "voice": "\u201cReality is not stable. It is negotiable.\u201d",
        "params": {"anomaly_basic": 1, "anomaly_rules": 1, "ult_turns": 2, "anomaly_energy": 15},
        "cons": [
            {"level": 1, "desc": "Start battle with one anomaly active."},
            {"level": 2, "stat": {"spd_pct": 0.15}, "desc": "+15% SPD."},
            {"level": 3, "desc": "Rewrite Variable affects 2 rules instead of 1."},
            {"level": 4, "stat": {"def_pct": 0.12}, "desc": "+12% DEF."},
            {"level": 5, "desc": "System Collapse lasts 1 additional turn."},
            {"level": 6, "desc": "Anomalies can stack twice simultaneously."},
        ],
    },
    {
        "id": "gravity_die", "name": "Gravity Die", "rarity": "MYTHIC",
        "element": "Arcane", "role": "Gravity Engine", "tags": ["Control"], "engine": ["Control"],
        "stats": {"hp": 1360, "atk": 142, "def": 90, "spd": 96},
        "basic": {"name": "Crush", "desc": "Deal Arcane damage and apply 1 Gravity stack."},
        "skill": {"name": "Collapse", "desc": "Increase every enemy's Gravity by 3. Foes at 5 Gravity become Weighed Down: -20 SPD and +15% damage taken."},
        "ult":   {"name": "Singularity", "desc": "Create a Black Hole for 3 turns. Each turn end: pull enemies together, deal Arcane damage, and +2 Gravity."},
        "passive": {"name": "Heavy Burden", "desc": "Enemies lose 2 SPD per Gravity stack (maximum -20 SPD)."},
        "lore": "Entire battlefields have collapsed beneath a single roll.",
        "voice": "\u201cNo matter how high they rise... everything falls.\u201d",
        "params": {"basic_gravity": 1, "skill_gravity_all": 3, "ult_turns": 3, "ult_gravity_tick": 2, "weighed_at": 5},
        "cons": [
            {"level": 1, "desc": "Battle begins with 2 Gravity on all enemies."},
            {"level": 2, "stat": {"def_pct": 0.15}, "desc": "+15% DEF."},
            {"level": 3, "desc": "Collapse applies 5 Gravity instead."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Black Hole lasts 1 additional turn."},
            {"level": 6, "desc": "Enemies reaching maximum Gravity immediately lose their next turn."},
        ],
    },
    {
        "id": "genesis_die", "name": "Genesis Die", "rarity": "MYTHIC",
        "element": "Nature", "role": "Evolution Engine", "tags": ["Sustain"], "engine": ["Sustain"],
        "stats": {"hp": 1285, "atk": 150, "def": 82, "spd": 102},
        "basic": {"name": "Adapt", "desc": "Deal Nature damage and gain 1 Evolution Point."},
        "skill": {"name": "Mutate", "desc": "Choose a permanent mutation (+20% ATK, +20% DEF, +15 SPD, or +25% Healing). Mutations stack all battle."},
        "ult":   {"name": "Perfect Evolution", "desc": "Double every mutation bonus for 3 turns and fully heal Genesis."},
        "passive": {"name": "Rapid Evolution", "desc": "Whenever an ally defeats an enemy, gain another Evolution Point."},
        "lore": "Every battle changes what Genesis becomes.",
        "voice": "\u201cPerfection isn't born. It's grown.\u201d",
        "params": {"evo_basic": 1, "ult_turns": 3},
        "cons": [
            {"level": 1, "desc": "Start with 2 Evolution Points."},
            {"level": 2, "stat": {"hp_pct": 0.15}, "desc": "+15% HP."},
            {"level": 3, "desc": "Mutations become 25% stronger."},
            {"level": 4, "stat": {"spd_flat": 12}, "desc": "+12 SPD."},
            {"level": 5, "desc": "Perfect Evolution lasts 1 extra turn."},
            {"level": 6, "desc": "Choose two mutations instead of one."},
        ],
    },
    {
        "id": "mirage_die", "name": "Mirage Die", "rarity": "MYTHIC",
        "element": "Wind", "role": "Illusion Engine", "tags": ["Sustain"], "engine": ["Sustain"],
        "stats": {"hp": 1235, "atk": 155, "def": 76, "spd": 110},
        "basic": {"name": "Phantom Slash", "desc": "Deal Wind damage and create 1 Mirage."},
        "skill": {"name": "False Reality", "desc": "Consume 1 Mirage to negate the next attack against any ally."},
        "ult":   {"name": "Hall of Mirrors", "desc": "Summon 4 Mirages. When an ally is targeted, a Mirage has a 50% chance to take the hit instead. Mirages explode when destroyed."},
        "passive": {"name": "Nothing Is Certain", "desc": "Each Mirage increases the team's Dodge rate by 4%."},
        "lore": "Even victory can be an illusion.",
        "voice": "\u201cWhat you hit was never really there.\u201d",
        "params": {"basic_mirage": 1, "ult_mirages": 4, "dodge_per": 0.04},
        "cons": [
            {"level": 1, "desc": "Begin battle with 1 Mirage."},
            {"level": 2, "stat": {"spd_pct": 0.15}, "desc": "+15% SPD."},
            {"level": 3, "desc": "Mirages explode for more damage."},
            {"level": 4, "stat": {"hp_pct": 0.12}, "desc": "+12% HP."},
            {"level": 5, "desc": "Hall of Mirrors creates 6 Mirages."},
            {"level": 6, "desc": "Destroyed Mirages immediately counterattack."},
        ],
    },
    {
        "id": "retribution_die", "name": "Retribution Die", "rarity": "MYTHIC",
        "element": "Light", "role": "Counter Engine", "tags": ["Sustain"], "engine": ["Sustain"],
        "stats": {"hp": 1395, "atk": 146, "def": 95, "spd": 97},
        "basic": {"name": "Judgement", "desc": "Deal Light damage and gain 1 Retribution."},
        "skill": {"name": "Stand Firm", "desc": "Enter Guard Stance: every attack against Retribution Die triggers a counterattack."},
        "ult":   {"name": "Final Verdict", "desc": "For 2 turns every ally counterattacks when damaged. Counterattacks deal 80% damage."},
        "passive": {"name": "Justice Served", "desc": "Each successful counter increases future counters by 5% (stacks up to 10)."},
        "lore": "Every enemy action is another mistake.",
        "voice": "\u201cThey attacked first.\u201d",
        "params": {"counter_pct": 0.80, "guard_turns": 2, "ult_turns": 2, "counter_growth": 0.05, "counter_max": 10},
        "cons": [
            {"level": 1, "desc": "Begin battle with 3 Retribution."},
            {"level": 2, "stat": {"def_pct": 0.15}, "desc": "+15% DEF."},
            {"level": 3, "desc": "Counterattacks heal 5% HP."},
            {"level": 4, "stat": {"atk_pct": 0.12}, "desc": "+12% ATK."},
            {"level": 5, "desc": "Guard Stance lasts 1 additional turn."},
            {"level": 6, "desc": "Counterattacks ignore 30% DEF."},
        ],
    },
    {
        "id": "chainmaster", "name": "Chainmaster Die", "rarity": "MYTHIC",
        "element": "Electric", "role": "Combo Engine", "tags": ["Combo"], "engine": ["Combo"],
        "stats": {"hp": 1260, "atk": 162, "def": 74, "spd": 108},
        "basic": {"name": "Spark", "desc": "Deal Electric damage and increase Combo by 1."},
        "skill": {"name": "Chain Reaction", "desc": "Deal Electric damage once for every Combo stack, then consume all Combo."},
        "ult":   {"name": "Overload", "desc": "For 3 turns Combo no longer resets and every attack gains one bonus hit."},
        "passive": {"name": "Momentum", "desc": "Every consecutive ally attack increases Combo by 1. Missing an attack resets Combo to 0."},
        "lore": "Every combo pushes the next one further.",
        "voice": "\u201cOne strike is an attack. Ten strikes are a masterpiece.\u201d",
        "params": {"basic_combo": 1, "combo_max": 20, "overload_turns": 3},
        "cons": [
            {"level": 1, "desc": "Start battle with 3 Combo."},
            {"level": 2, "stat": {"atk_pct": 0.15}, "desc": "+15% ATK."},
            {"level": 3, "desc": "Maximum Combo increased to 25."},
            {"level": 4, "stat": {"spd_flat": 12}, "desc": "+12 SPD."},
            {"level": 5, "desc": "Overload lasts 1 additional turn."},
            {"level": 6, "desc": "Every fifth Combo hit deals guaranteed Critical Damage."},
        ],
    },
    {
        "id": "jackpot_die", "name": "Jackpot Die", "rarity": "MYTHIC",
        "element": "Light", "role": "Jackpot Engine", "tags": ["Fortune"], "engine": ["Fortune"],
        "stats": {"hp": 1215, "atk": 168, "def": 70, "spd": 106},
        "basic": {"name": "Lucky Strike", "desc": "Deal Light damage and gain 3 Jackpot."},
        "skill": {"name": "Double or Nothing", "desc": "Deal heavy Light damage, gain 15 Jackpot, and a 50% chance to immediately take another action."},
        "ult":   {"name": "\ud83c\udfb0 JACKPOT", "desc": "Requires 100 Jackpot instead of Energy. Transform for 2 turns: +50% damage, +40% crit, skills cost no Energy, and gain one extra action each turn. Afterwards Jackpot resets to 0."},
        "passive": {"name": "High Roller", "desc": "Every attack grants Jackpot, crits grant double, and taking damage grants 2 Jackpot."},
        "lore": "Every loss was merely another step toward inevitability.",
        "voice": "\u201cFortune favors the one who keeps rolling.\u201d",
        "params": {"basic_jackpot": 3, "skill_jackpot": 15, "extra_action_pct": 0.50, "transform_cost": 100, "transform_turns": 2},
        "cons": [
            {"level": 1, "desc": "Begin battle with 20 Jackpot."},
            {"level": 2, "stat": {"hp_pct": 0.15}, "desc": "+15% Max HP."},
            {"level": 3, "desc": "Transformation lasts 1 additional turn."},
            {"level": 4, "stat": {"spd_pct": 0.12}, "desc": "+12% SPD."},
            {"level": 5, "desc": "Jackpot never drops below 25 after transforming."},
            {"level": 6, "desc": "The first transformation each battle grants another turn."},
        ],
    },
    {
        "id": "timekeeper", "name": "Timekeeper Die", "rarity": "MYTHIC",
        "element": "Arcane", "role": "Time Engine", "tags": ["Control"], "engine": ["Control"],
        "stats": {"hp": 1300, "atk": 138, "def": 88, "spd": 112},
        "basic": {"name": "Tick", "desc": "Deal Arcane damage and apply 1 Time Mark."},
        "skill": {"name": "Delay", "desc": "Push an enemy back 30% on the action timeline. If it has a Time Mark, stun it for 1 turn instead."},
        "ult":   {"name": "Frozen Clock", "desc": "Freeze every enemy in place \u2014 each loses its next action \u2014 and all allies gain 20 Energy."},
        "passive": {"name": "Temporal Drift", "desc": "Whenever an enemy's turn is delayed, the whole team heals 4% Max HP."},
        "lore": "The Timekeeper never moves faster than necessary.",
        "voice": "\u201cTomorrow can wait.\u201d",
        "params": {"time_mark": 1, "delay_pct": 0.30, "ult_energy": 20, "drift_heal": 0.04},
        "cons": [
            {"level": 1, "desc": "Begin battle with 1 Time Mark on every enemy."},
            {"level": 2, "stat": {"def_pct": 0.15}, "desc": "+15% DEF."},
            {"level": 3, "desc": "Delay strength increased to 40%."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Ultimate grants 30 Energy instead."},
            {"level": 6, "desc": "Once per battle, an ally about to die instead skips death and takes their turn."},
        ],
    },
    {
        "id": "eclipse_die", "name": "Eclipse Die", "rarity": "MYTHIC",
        "element": "Dark", "role": "Eclipse Engine", "tags": ["Sustain"], "engine": ["Sustain"],
        "stats": {"hp": 1275, "atk": 156, "def": 82, "spd": 104},
        "basic": {"name": "Twilight", "desc": "Deal Dark damage and gain 1 Eclipse Charge."},
        "skill": {"name": "Shift", "desc": "Switch between Day Form (support-focused) and Night Form (damage-focused)."},
        "ult":   {"name": "Total Eclipse", "desc": "Empower the current form for 3 turns. Day: massive healing, shields and buffs. Night: huge damage, lifesteal and splash."},
        "passive": {"name": "Solar Cycle", "desc": "Automatically changes form every 3 turns if not switched manually."},
        "lore": "Even the sun must surrender.",
        "voice": "\u201cDay or night, the end is mine to choose.\u201d",
        "params": {"ult_turns": 3, "auto_cycle": 3},
        "cons": [
            {"level": 1, "desc": "Start battle in your chosen form."},
            {"level": 2, "stat": {"hp_pct": 0.15}, "desc": "+15% HP."},
            {"level": 3, "desc": "Switching forms restores 15 Energy."},
            {"level": 4, "stat": {"atk_pct": 0.12}, "desc": "+12% ATK."},
            {"level": 5, "desc": "Total Eclipse lasts 1 extra turn."},
            {"level": 6, "desc": "Switching forms grants an immediate extra action."},
        ],
    },
    {
        "id": "sacrifice_die", "name": "Sacrifice Die", "rarity": "MYTHIC",
        "element": "Blood", "role": "Sacrifice Engine", "tags": ["Sustain"], "engine": ["Sustain"],
        "stats": {"hp": 1600, "atk": 180, "def": 55, "spd": 94},
        "basic": {"name": "Blood Price", "desc": "Lose 2% HP and deal Blood damage."},
        "skill": {"name": "Offer", "desc": "Sacrifice 10% current HP to increase all allies' damage by 40% for 2 turns."},
        "ult":   {"name": "Final Bargain", "desc": "Reduce own HP to 1, revive all defeated allies, fully restore team Energy, and grant 2 turns of damage immunity."},
        "passive": {"name": "Pain is Power", "desc": "Every 1% HP missing increases damage by 0.5%."},
        "lore": "The strongest victories demand the greatest price.",
        "voice": "\u201cTake my blood. It buys your victory.\u201d",
        "params": {"basic_hp_cost": 0.02, "skill_hp_cost": 0.10, "team_dmg": 0.40, "team_dmg_turns": 2, "pain_per_pct": 0.005, "immunity_turns": 2},
        "cons": [
            {"level": 1, "desc": "Begin battle at 80% HP."},
            {"level": 2, "stat": {"hp_pct": 0.20}, "desc": "+20% HP."},
            {"level": 3, "desc": "Offer only sacrifices 8%."},
            {"level": 4, "stat": {"def_pct": 0.15}, "desc": "+15% DEF."},
            {"level": 5, "stat": {"heal_recv_pct": 0.25}, "desc": "Healing received increased by 25%."},
            {"level": 6, "desc": "Final Bargain no longer reduces HP below 20%."},
        ],
    },
    {
        "id": "dominion_die", "name": "Dominion Die", "rarity": "MYTHIC",
        "element": "Arcane", "role": "Summon Engine", "tags": ["Summon"], "engine": ["Summon"],
        "stats": {"hp": 1325, "atk": 145, "def": 84, "spd": 101},
        "basic": {"name": "Call", "desc": "Summon one Token Die copying 25% of Dominion's stats."},
        "skill": {"name": "Command", "desc": "Order all summoned Dice to attack."},
        "ult":   {"name": "Dice Kingdom", "desc": "Summon 3 empowered Token Dice. For 3 turns they gain 100% Speed, apply your on-hit effects, and cannot be defeated in one hit."},
        "passive": {"name": "Strength in Numbers", "desc": "Each summoned die increases Dominion's damage by 8% (max 5 summons)."},
        "lore": "One die is chance. Four are certainty.",
        "voice": "\u201cMy kingdom answers every roll.\u201d",
        "params": {"summon_basic": 1, "summon_pct": 0.25, "ult_summons": 3, "summon_max": 5, "dmg_per_summon": 0.08, "ult_turns": 3},
        "cons": [
            {"level": 1, "desc": "Begin battle with 1 Token Die."},
            {"level": 2, "stat": {"def_pct": 0.15}, "desc": "+15% DEF."},
            {"level": 3, "desc": "Maximum summons increased to 6."},
            {"level": 4, "stat": {"atk_pct": 0.12}, "desc": "+12% ATK."},
            {"level": 5, "desc": "Summons inherit 40% stats instead."},
            {"level": 6, "desc": "When a summon dies, immediately replace it once per turn."},
        ],
    },
    {
        "id": "singularity_fracture", "name": "Singularity Fracture", "rarity": "MYTHIC",
        "element": "Void", "role": "Fracture Engine", "tags": ["Fracture"], "engine": ["Fracture"],
        "stats": {"hp": 1340, "atk": 160, "def": 88, "spd": 101},
        "basic": {"name": "Reality Chip", "desc": "Deal Void damage and apply 2 Fracture."},
        "skill": {"name": "Cascade Break", "desc": "Increase all enemy Fracture by 4. If any enemy is Exposed, instantly apply Break vulnerability."},
        "ult":   {"name": "Total Structural Failure", "desc": "For 3 turns: all enemies gain Fracture every turn, Exposed foes take bonus damage when hit, and Break is doubled on Shattered targets."},
        "passive": {"name": "Collapse Prediction", "desc": "Whenever an enemy reaches Exposed, allies gain Energy."},
        "lore": "Everything breaks. I just decide when.",
        "voice": "\u201cEverything breaks. I just decide when.\u201d",
        "params": {"basic_fracture": 2, "skill_fracture_all": 4, "ult_turns": 3, "ult_fracture_tick": 2, "expose_energy": 8},
        "cons": [
            {"level": 1, "desc": "Start battle with 5 Fracture on all enemies."},
            {"level": 2, "stat": {"atk_pct": 0.15}, "desc": "+15% ATK."},
            {"level": 3, "desc": "Cascade Break applies 1 extra Fracture."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Total Structural Failure lasts 1 additional turn."},
            {"level": 6, "desc": "Shattered enemies cannot resist Break effects at all."},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # ===== EXPANSION: RARE (20) =====
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "combo_engineer", "name": "Combo Engineer", "rarity": "RARE",
        "element": "Electric", "role": "Chain Support", "tags": ["Combo"], "engine": ["Combo"],
        "stats": {"hp": 820, "atk": 118, "def": 70, "spd": 106},
        "basic": {"name": "Pulse Hit", "desc": "Deal Electric damage and increase Combo by 1."},
        "skill": {"name": "Chain Extension", "desc": "The next ally action counts as part of the Combo chain (boosted damage)."},
        "ult":   {"name": "Overclock Sequence", "desc": "For 2 turns Combo does not reset and all ally attacks gain a bonus hit."},
        "passive": {"name": "Momentum Loop", "desc": "Consecutive ally actions increase damage slightly."},
        "lore": "Sequence is everything.",
        "voice": "\u201cOne action is nothing. Sequence is everything.\u201d",
        "params": {"basic_combo": 1, "skill_combo": 1, "overload_turns": 2},
        "cons": [
            {"level": 1, "desc": "Start battle with 2 Combo."},
            {"level": 2, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 3, "desc": "Skill increases Combo by 2 instead."},
            {"level": 4, "stat": {"atk_pct": 0.12}, "desc": "+12% ATK."},
            {"level": 5, "desc": "Ultimate lasts +1 turn."},
            {"level": 6, "desc": "Every 5 Combo hits increases crit rate."},
        ],
    },
    {
        "id": "null_seal", "name": "Null Seal", "rarity": "RARE",
        "element": "Void", "role": "Debuff Control", "tags": ["Control"], "engine": ["Control"],
        "stats": {"hp": 810, "atk": 120, "def": 66, "spd": 103},
        "basic": {"name": "Void Tap", "desc": "Deal Void damage and remove 1 buff from an enemy."},
        "skill": {"name": "Seal Effect", "desc": "Prevent enemies from gaining buffs for 2 turns."},
        "ult":   {"name": "Absolute Silence", "desc": "Enemies cannot apply buffs or gain Energy for 2 turns."},
        "passive": {"name": "Suppression Field", "desc": "Enemies with no buffs take +10% damage."},
        "lore": "Remove the rules. Then remove the target.",
        "voice": "\u201cRemove the rules. Then remove the target.\u201d",
        "params": {"strip_buff": 1, "seal_turns": 2, "suppress_dmg": 0.10},
        "cons": [
            {"level": 1, "desc": "Start battle reducing enemy buffs."},
            {"level": 2, "stat": {"atk_pct": 0.12}, "desc": "+12% ATK."},
            {"level": 3, "desc": "Skill duration +1 turn."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Ultimate also reduces enemy Energy gain."},
            {"level": 6, "desc": "First buff applied by enemies is negated once per battle."},
        ],
    },
    {
        "id": "echo_stabilizer", "name": "Echo Stabilizer", "rarity": "RARE",
        "element": "Arcane", "role": "Copy Control", "tags": ["Combo"], "engine": ["Combo"],
        "stats": {"hp": 840, "atk": 115, "def": 72, "spd": 101},
        "basic": {"name": "Resonant Hit", "desc": "Deal Arcane damage and store 1 Echo Charge."},
        "skill": {"name": "Controlled Echo", "desc": "Repeat the last ally skill at 50% power."},
        "ult":   {"name": "Perfect Repeat", "desc": "Repeat the last 2 ally actions at 60% power."},
        "passive": {"name": "Echo Efficiency", "desc": "Each Echo increases team damage by 3%."},
        "lore": "If it worked once, it will work again.",
        "voice": "\u201cIf it worked once, it will work again.\u201d",
        "params": {"echo_store": 1, "echo_repeat_pct": 0.50, "ult_repeat_pct": 0.60, "echo_dmg": 0.03},
        "cons": [
            {"level": 1, "desc": "Start battle with 1 Echo Charge."},
            {"level": 2, "stat": {"atk_pct": 0.15}, "desc": "+15% ATK."},
            {"level": 3, "desc": "Echo repeats can crit."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Ultimate repeats 3 actions."},
            {"level": 6, "desc": "Echo repeats ignore 20% enemy DEF."},
        ],
    },
    {
        "id": "ember_analyst", "name": "Ember Analyst", "rarity": "RARE",
        "element": "Fire", "role": "Omen Support", "tags": ["Omen"], "engine": ["Omen"],
        "stats": {"hp": 820, "atk": 118, "def": 62, "spd": 101},
        "basic": {"name": "Sear Insight", "desc": "Deal Fire damage and apply 2 Omen to the target."},
        "skill": {"name": "Predictive Burn", "desc": "Apply Omen to all enemies. If a target already has Omen, increase its stacks instead."},
        "ult":   {"name": "Forecast Collapse", "desc": "Trigger 50% of the Omen on all enemies instantly."},
        "passive": {"name": "Pattern Recognition", "desc": "All allies deal +10% damage to enemies with Omen."},
        "lore": "They don't see the pattern... until it burns them.",
        "voice": "\u201cI already calculated your end.\u201d",
        "params": {"basic_omen": 2, "skill_omen": 2, "skill_omen_all": 1, "ult_omen_trig": 0.50, "omen_dmg": 0.10},
        "cons": [
            {"level": 1, "desc": "Start battle with 5 Omen on all enemies."},
            {"level": 2, "stat": {"atk_pct": 0.12}, "desc": "+12% ATK."},
            {"level": 3, "desc": "Skill applies +1 extra Omen."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Omen-trigger damage increased by 15%."},
            {"level": 6, "desc": "First Omen trigger each battle is doubled."},
        ],
    },
    {
        "id": "circuit_relay", "name": "Circuit Relay", "rarity": "RARE",
        "element": "Electric", "role": "Energy Support", "tags": ["Energy"], "engine": ["Energy"],
        "stats": {"hp": 780, "atk": 110, "def": 70, "spd": 108},
        "basic": {"name": "Spark Link", "desc": "Deal Electric damage and grant 5 Energy to the lowest-energy ally."},
        "skill": {"name": "Overcharge Transfer", "desc": "Distribute Energy equally across all allies; allies above 80% Energy gain bonus turn meter."},
        "ult":   {"name": "Full Relay", "desc": "All allies immediately gain 25 Energy."},
        "passive": {"name": "Flow State", "desc": "Whenever an ally uses a Skill, a random ally gains 2 Energy."},
        "lore": "Power is useless if it doesn't move.",
        "voice": "\u201cPower is useless if it doesn't move.\u201d",
        "params": {"give_energy": 5, "distribute": 1, "ult_team_energy": 25},
        "cons": [
            {"level": 1, "desc": "Start battle with +10 Energy on all allies."},
            {"level": 2, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 3, "desc": "Skill gives +5 extra Energy."},
            {"level": 4, "stat": {"def_pct": 0.12}, "desc": "+12% DEF."},
            {"level": 5, "desc": "Ultimate cooldown reduced by 1 turn."},
            {"level": 6, "desc": "Energy overflow converts into a small shield."},
        ],
    },
    {
        "id": "fragment_scribe", "name": "Fragment Scribe", "rarity": "RARE",
        "element": "Arcane", "role": "Combo Extension", "tags": ["Combo"], "engine": ["Combo"],
        "stats": {"hp": 840, "atk": 122, "def": 68, "spd": 99},
        "basic": {"name": "Echo Mark", "desc": "Deal Arcane damage and store 1 Echo Stack."},
        "skill": {"name": "Rewrite Echo", "desc": "Consume Echo Stacks to repeat the last ally skill at 40% power per stack."},
        "ult":   {"name": "Perfect Record", "desc": "Repeat all ally skills used last turn at 50% power."},
        "passive": {"name": "Memory Drift", "desc": "Each Echo Stack increases team damage by 3%."},
        "lore": "Every action leaves a shadow behind.",
        "voice": "\u201cEvery action leaves a shadow behind.\u201d",
        "params": {"echo_store": 1, "echo_repeat_pct": 0.40, "ult_repeat_pct": 0.50, "echo_dmg": 0.03},
        "cons": [
            {"level": 1, "desc": "Start battle with 2 Echo Stacks."},
            {"level": 2, "stat": {"atk_pct": 0.15}, "desc": "+15% ATK."},
            {"level": 3, "desc": "Echo repeat power increased to 50%."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Ultimate repeats 1 extra skill."},
            {"level": 6, "desc": "Echoes can now crit."},
        ],
    },
    {
        "id": "bastion_guard", "name": "Bastion Guard", "rarity": "RARE",
        "element": "Earth", "role": "Universal Sustain", "tags": ["Sustain"], "engine": ["Sustain"],
        "stats": {"hp": 1050, "atk": 92, "def": 140, "spd": 88},
        "basic": {"name": "Shield Strike", "desc": "Deal Earth damage and grant a small shield to the lowest-HP ally."},
        "skill": {"name": "Fortify Line", "desc": "Grant a team-wide shield based on Bastion's DEF and reduce incoming damage for 2 turns."},
        "ult":   {"name": "Last Wall", "desc": "Grant a massive shield to all allies and cleanse 1 debuff per ally."},
        "passive": {"name": "Steadfast", "desc": "When an ally drops below 30% HP, grant them a shield once per battle."},
        "lore": "You don't fall while I still stand.",
        "voice": "\u201cYou don't fall while I still stand.\u201d",
        "params": {"basic_shield": 0.30, "skill_shield": 1.10, "ult_shield": 2.0, "dr_pct": 0.20, "dr_turns": 2, "cleanse_all": 1},
        "cons": [
            {"level": 1, "desc": "Start battle with a shield on all allies."},
            {"level": 2, "stat": {"def_pct": 0.20}, "desc": "+20% DEF."},
            {"level": 3, "desc": "Skill shield increased by 20%."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Ultimate duration +1 turn."},
            {"level": 6, "desc": "Shields also grant +10% damage reduction."},
        ],
    },
    {
        "id": "rift_tracker", "name": "Rift Tracker", "rarity": "RARE",
        "element": "Void", "role": "Break Support", "tags": ["Break"], "engine": ["Break"],
        "stats": {"hp": 810, "atk": 125, "def": 66, "spd": 104},
        "basic": {"name": "Expose", "desc": "Deal Void damage and increase the Break gauge by a small amount."},
        "skill": {"name": "Fracture Point", "desc": "Increase Break damage taken by enemies for 2 turns."},
        "ult":   {"name": "Structural Collapse", "desc": "Instantly reduce all enemies' Break resistance."},
        "passive": {"name": "Weak Point Analysis", "desc": "Broken enemies take +12% extra damage from all sources."},
        "lore": "Find the weak point. Then widen it.",
        "voice": "\u201cFind the weak point. Then widen it.\u201d",
        "params": {"break_gain": 18, "break_vuln": 0.25, "break_vuln_turns": 2, "broken_dmg": 0.12},
        "cons": [
            {"level": 1, "desc": "Start battle with enemies at 20% Break."},
            {"level": 2, "stat": {"atk_pct": 0.12}, "desc": "+12% ATK."},
            {"level": 3, "desc": "Skill duration +1 turn."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Ultimate increases Break vulnerability more."},
            {"level": 6, "desc": "Broken enemies cannot recover Break resistance for 1 turn."},
        ],
    },
    {
        "id": "flux_mediator", "name": "Flux Mediator", "rarity": "RARE",
        "element": "Electric", "role": "Universal Support", "tags": ["Energy"], "engine": ["Energy"],
        "stats": {"hp": 800, "atk": 112, "def": 74, "spd": 107},
        "basic": {"name": "Static Tap", "desc": "Deal Electric damage and grant 3 Energy to all allies."},
        "skill": {"name": "Current Balance", "desc": "Increase Energy gain for all allies by 20% for 2 turns."},
        "ult":   {"name": "Full Circuit Sync", "desc": "All allies gain 15 Energy and the next ally action is advanced slightly."},
        "passive": {"name": "Flow Correction", "desc": "Whenever an ally gains Energy, gain a stack. At 10 stacks, heal the team slightly."},
        "lore": "Balance is just controlled imbalance.",
        "voice": "\u201cBalance is just controlled imbalance.\u201d",
        "params": {"basic_team_energy": 3, "energy_gain_buff": 0.20, "energy_buff_turns": 2, "ult_team_energy": 15},
        "cons": [
            {"level": 1, "desc": "Start battle with +5 Energy on all allies."},
            {"level": 2, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 3, "desc": "Skill grants +5 extra Energy."},
            {"level": 4, "stat": {"def_pct": 0.12}, "desc": "+12% DEF."},
            {"level": 5, "desc": "Ultimate cooldown reduced by 1 turn."},
            {"level": 6, "desc": "Overflow Energy converts into a small damage buff."},
        ],
    },
    {
        "id": "omen_catalyst", "name": "Omen Catalyst", "rarity": "RARE",
        "element": "Arcane", "role": "Omen Amplifier", "tags": ["Omen"], "engine": ["Omen"],
        "stats": {"hp": 830, "atk": 120, "def": 65, "spd": 102},
        "basic": {"name": "Trace Fate", "desc": "Deal Arcane damage and apply 1 Omen to the target."},
        "skill": {"name": "Pressure Build", "desc": "Increase all existing Omen stacks on enemies by 30%."},
        "ult":   {"name": "Accelerated Doom", "desc": "Trigger 30% of all Omen currently on enemies."},
        "passive": {"name": "Omen Resonance", "desc": "Whenever Omen is triggered, increase the next Omen application by 1."},
        "lore": "It doesn't create fate. It speeds it up.",
        "voice": "\u201cIt doesn't create fate. It speeds it up.\u201d",
        "params": {"basic_omen": 1, "omen_amp": 0.30, "ult_omen_trig": 0.30},
        "cons": [
            {"level": 1, "desc": "Start battle with 3 Omen on all enemies."},
            {"level": 2, "stat": {"atk_pct": 0.12}, "desc": "+12% ATK."},
            {"level": 3, "desc": "Skill increases Omen by 40% instead."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Triggered Omen deals +10% damage."},
            {"level": 6, "desc": "First Omen trigger each battle cannot be reduced."},
        ],
    },
    {
        "id": "chrono_tactician", "name": "Chrono Tactician", "rarity": "RARE",
        "element": "Time", "role": "Turn Manipulation", "tags": ["Control"], "engine": ["Control"],
        "stats": {"hp": 790, "atk": 116, "def": 72, "spd": 109},
        "basic": {"name": "Micro Delay", "desc": "Deal Time damage and slightly reduce the enemy's turn meter."},
        "skill": {"name": "Reorder", "desc": "Push the fastest enemy back on the action timeline."},
        "ult":   {"name": "Perfect Timing", "desc": "The next 2 allied actions immediately advance in turn order."},
        "passive": {"name": "Temporal Awareness", "desc": "The first ally each round gains bonus Energy."},
        "lore": "Speed is irrelevant when you decide the order.",
        "voice": "\u201cSpeed is irrelevant when you decide the order.\u201d",
        "params": {"delay_pct": 0.20, "ult_advance": 2, "round_energy": 8},
        "cons": [
            {"level": 1, "desc": "Start battle with +10 SPD for the team."},
            {"level": 2, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 3, "desc": "Skill always targets the enemy with highest speed."},
            {"level": 4, "stat": {"def_pct": 0.12}, "desc": "+12% DEF."},
            {"level": 5, "desc": "Ultimate affects 3 allies instead of 2."},
            {"level": 6, "desc": "Allies affected gain a 10% damage boost."},
        ],
    },
    {
        "id": "wound_archivist", "name": "Wound Archivist", "rarity": "RARE",
        "element": "Blood", "role": "DoT Amplifier", "tags": ["Omen"], "engine": ["Omen"],
        "stats": {"hp": 860, "atk": 124, "def": 68, "spd": 98},
        "basic": {"name": "Open Wound", "desc": "Deal Blood damage and apply a Bleed stack."},
        "skill": {"name": "Record Trauma", "desc": "Increase all Bleed damage on enemies by 25%."},
        "ult":   {"name": "Pain Index", "desc": "Trigger all Bleed effects immediately, then reapply half of them."},
        "passive": {"name": "Bleeding Memory", "desc": "Enemies with Bleed take +8% increased damage."},
        "lore": "Every injury is data.",
        "voice": "\u201cEvery injury is data.\u201d",
        "params": {"basic_bleed": 2, "bleed_amp": 0.25, "ult_bleed_pct": 0.50, "bleed_dmg": 0.08},
        "cons": [
            {"level": 1, "desc": "Start battle with Bleed on all enemies."},
            {"level": 2, "stat": {"atk_pct": 0.15}, "desc": "+15% ATK."},
            {"level": 3, "desc": "Skill increases Bleed damage by 35%."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Ultimate re-applies full Bleed instead of half."},
            {"level": 6, "desc": "Bleed can stack one additional time."},
        ],
    },
    {
        "id": "shield_weave", "name": "Shield Weave", "rarity": "RARE",
        "element": "Earth", "role": "Shield Synergy", "tags": ["Sustain"], "engine": ["Sustain"],
        "stats": {"hp": 1080, "atk": 88, "def": 142, "spd": 85},
        "basic": {"name": "Weave Guard", "desc": "Deal Earth damage and grant a small shield to the weakest ally."},
        "skill": {"name": "Adaptive Armor", "desc": "Increase all shields by 25% for 2 turns; shielded allies gain damage reduction."},
        "ult":   {"name": "Fortress Pattern", "desc": "Grant a team-wide shield based on total DEF; shields persist 2 turns longer."},
        "passive": {"name": "Layered Defense", "desc": "Whenever a shield is applied, 5% converts into a damage boost."},
        "lore": "Defense is not blocking \u2014 it's adapting.",
        "voice": "\u201cDefense is not blocking. It's adapting.\u201d",
        "params": {"basic_shield": 0.30, "skill_shield_amp": 0.25, "ult_shield": 1.8, "dr_pct": 0.15, "dr_turns": 2},
        "cons": [
            {"level": 1, "desc": "Start battle with a shield on all allies."},
            {"level": 2, "stat": {"def_pct": 0.20}, "desc": "+20% DEF."},
            {"level": 3, "desc": "Skill shields increased by 15%."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Ultimate duration +1 turn."},
            {"level": 6, "desc": "Shielded allies gain resistance to Break effects."},
        ],
    },
    {
        "id": "sync_warden", "name": "Sync Warden", "rarity": "RARE",
        "element": "Arcane", "role": "Team Synchronization", "tags": ["Energy"], "engine": ["Energy"],
        "stats": {"hp": 860, "atk": 114, "def": 78, "spd": 104},
        "basic": {"name": "Rhythm Strike", "desc": "Deal Arcane damage and slightly advance an ally's turn meter."},
        "skill": {"name": "Team Sync", "desc": "Distribute Energy so the lowest allies are brought closer to the highest."},
        "ult":   {"name": "Perfect Sync", "desc": "For 2 turns turn order stabilises and allies gain +10% damage when acting in sequence."},
        "passive": {"name": "Harmonic Flow", "desc": "Whenever allies act in consecutive turns, gain team-wide Energy."},
        "lore": "If one falls out of rhythm, the whole song breaks.",
        "voice": "\u201cIf one falls out of rhythm, the whole song breaks.\u201d",
        "params": {"advance": 0.10, "distribute": 1, "ult_team_dmg": 0.10, "ult_turns": 2},
        "cons": [
            {"level": 1, "desc": "Start battle with +5 Energy on all allies."},
            {"level": 2, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 3, "desc": "Skill also grants a small shield to the lowest-HP ally."},
            {"level": 4, "stat": {"def_pct": 0.12}, "desc": "+12% DEF."},
            {"level": 5, "desc": "Ultimate lasts +1 turn."},
            {"level": 6, "desc": "Consecutive ally actions also increase crit rate."},
        ],
    },
    {
        "id": "rift_cleaner", "name": "Rift Cleaner", "rarity": "RARE",
        "element": "Void", "role": "Debuff Removal Support", "tags": ["Sustain"], "engine": ["Sustain"],
        "stats": {"hp": 900, "atk": 110, "def": 80, "spd": 100},
        "basic": {"name": "Void Sweep", "desc": "Deal Void damage and remove 1 debuff from an ally."},
        "skill": {"name": "Cleanse Field", "desc": "Remove all minor debuffs from the team and gain damage reduction for 1 turn."},
        "ult":   {"name": "Reset State", "desc": "Fully cleanse the team and convert 1 debuff per ally into Energy."},
        "passive": {"name": "Purity Loop", "desc": "Whenever an ally is cleansed, they gain a small damage boost."},
        "lore": "Chaos only wins when you let it stay.",
        "voice": "\u201cChaos only wins when you let it stay.\u201d",
        "params": {"cleanse": 1, "cleanse_all": 1, "dr_pct": 0.20, "dr_turns": 1},
        "cons": [
            {"level": 1, "desc": "Start battle with partial debuff immunity."},
            {"level": 2, "stat": {"def_pct": 0.15}, "desc": "+15% DEF."},
            {"level": 3, "desc": "Skill also heals a small amount."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Ultimate cooldown reduced by 1 turn."},
            {"level": 6, "desc": "Cleanse also grants a temporary shield."},
        ],
    },
    {
        "id": "overclock_broker", "name": "Overclock Broker", "rarity": "RARE",
        "element": "Electric", "role": "Risk/Reward Energy", "tags": ["Energy"], "engine": ["Energy"],
        "stats": {"hp": 780, "atk": 125, "def": 65, "spd": 110},
        "basic": {"name": "Charge Deal", "desc": "Deal Electric damage and gain bonus Energy, but take small recoil damage."},
        "skill": {"name": "Overclock", "desc": "Massively increase team Energy gain for 2 turns; all allies take minor continuous recoil."},
        "ult":   {"name": "Critical Overload", "desc": "All allies instantly gain full Energy and deal greatly increased damage for 1 turn, then become slightly weakened."},
        "passive": {"name": "Debt System", "desc": "Gaining Energy quickly adds a Debt stack that slightly reduces incoming healing until cleared."},
        "lore": "Power is never free. It is just prepaid.",
        "voice": "\u201cPower is never free. It is just prepaid.\u201d",
        "params": {"basic_energy": 8, "recoil": 0.03, "energy_gain_buff": 0.40, "energy_buff_turns": 2, "ult_full_energy": 1},
        "cons": [
            {"level": 1, "desc": "Start battle with 10 Energy on all allies."},
            {"level": 2, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 3, "desc": "Skill increases Energy gain further."},
            {"level": 4, "stat": {"atk_pct": 0.12}, "desc": "+12% ATK."},
            {"level": 5, "desc": "Ultimate also grants a small shield."},
            {"level": 6, "desc": "Debt no longer reduces healing."},
        ],
    },
    {
        "id": "fate_anchor", "name": "Fate Anchor", "rarity": "RARE",
        "element": "Arcane", "role": "Stability Control", "tags": ["Fortune"], "engine": ["Fortune"],
        "stats": {"hp": 920, "atk": 112, "def": 85, "spd": 96},
        "basic": {"name": "Anchor Strike", "desc": "Deal Arcane damage and reduce the enemy's turn meter slightly."},
        "skill": {"name": "Stabilize Fate", "desc": "Reduce randomness in the next enemy action (crit suppression and reduced burst)."},
        "ult":   {"name": "Locked Timeline", "desc": "For 2 turns turn order cannot be disrupted, no bonus turns can occur, and damage becomes consistent."},
        "passive": {"name": "Stability Field", "desc": "Allies take reduced damage from critical hits."},
        "lore": "The future bends, but it does not break.",
        "voice": "\u201cThe future bends, but it does not break.\u201d",
        "params": {"delay_pct": 0.15, "crit_reduce": 0.30, "ult_turns": 2},
        "cons": [
            {"level": 1, "desc": "Start battle with a stability buff for the team."},
            {"level": 2, "stat": {"def_pct": 0.15}, "desc": "+15% DEF."},
            {"level": 3, "desc": "Skill also grants Energy."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Ultimate duration +1 turn."},
            {"level": 6, "desc": "Enemies cannot gain extra actions during the ultimate."},
        ],
    },
    {
        "id": "resonance_thief", "name": "Resonance Thief", "rarity": "RARE",
        "element": "Arcane", "role": "Resource Steal", "tags": ["Energy"], "engine": ["Energy"],
        "stats": {"hp": 800, "atk": 122, "def": 68, "spd": 108},
        "basic": {"name": "Drift Tap", "desc": "Deal Arcane damage and steal a small amount of Energy from an enemy."},
        "skill": {"name": "Resonance Theft", "desc": "Steal Energy and buffs from an enemy for allies. If no buffs exist, increase ally damage instead."},
        "ult":   {"name": "Full Extraction", "desc": "Remove all buffs from enemies and convert each into Energy for allies."},
        "passive": {"name": "Leech Frequency", "desc": "Whenever an enemy gains a buff, Resonance Thief gains a partial benefit."},
        "lore": "Everything you gain... can be taken back.",
        "voice": "\u201cEverything you gain can be taken back.\u201d",
        "params": {"steal_energy": 8, "strip_buff": 1, "distribute": 1},
        "cons": [
            {"level": 1, "desc": "Start battle stealing a little Energy from all enemies."},
            {"level": 2, "stat": {"atk_pct": 0.12}, "desc": "+12% ATK."},
            {"level": 3, "desc": "Skill steals more Energy."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Ultimate also reduces enemy Energy gain."},
            {"level": 6, "desc": "Stolen buffs also increase ally damage temporarily."},
        ],
    },
    {
        "id": "structural_analyst", "name": "Structural Analyst", "rarity": "RARE",
        "element": "Arcane", "role": "Fracture Amplifier", "tags": ["Fracture"], "engine": ["Fracture"],
        "stats": {"hp": 820, "atk": 118, "def": 70, "spd": 102},
        "basic": {"name": "Scan Weakness", "desc": "Deal Arcane damage and apply 2 Fracture."},
        "skill": {"name": "Pressure Mapping", "desc": "Enemies take +25% Fracture gain for 2 turns."},
        "ult":   {"name": "Critical Collapse", "desc": "Trigger all Exposed enemies (5+ Fracture) immediately."},
        "passive": {"name": "Weak Point Study", "desc": "Fractured enemies take increased Break damage."},
        "lore": "You don't break things. You learn where they already are broken.",
        "voice": "\u201cYou learn where they already are broken.\u201d",
        "params": {"basic_fracture": 2, "fracture_gain": 0.25, "fracture_buff_turns": 2, "ult_fracture_trigger": 1},
        "cons": [
            {"level": 1, "desc": "Start battle with 3 Fracture on all enemies."},
            {"level": 2, "stat": {"atk_pct": 0.12}, "desc": "+12% ATK."},
            {"level": 3, "desc": "Skill increases Fracture gain further."},
            {"level": 4, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 5, "desc": "Ultimate deals bonus damage per Fracture."},
            {"level": 6, "desc": "Exposed enemies also lose Energy."},
        ],
    },
    {
        "id": "rift_engineer", "name": "Rift Engineer", "rarity": "RARE",
        "element": "Void", "role": "System Breaker", "tags": ["Fracture"], "engine": ["Fracture"],
        "stats": {"hp": 800, "atk": 124, "def": 68, "spd": 106},
        "basic": {"name": "Pressure Shot", "desc": "Deal Void damage and apply 2 Fracture."},
        "skill": {"name": "System Strain", "desc": "Increase the Fracture allies apply for 2 turns."},
        "ult":   {"name": "Overload Collapse", "desc": "Immediately push all near-threshold enemies into the Exposed state."},
        "passive": {"name": "Structural Instability", "desc": "Enemies with Fracture take increased damage from all sources."},
        "lore": "If the system holds, increase pressure.",
        "voice": "\u201cIf the system holds, increase pressure.\u201d",
        "params": {"basic_fracture": 2, "fracture_gain": 0.25, "fracture_buff_turns": 2, "ult_expose": 1},
        "cons": [
            {"level": 1, "desc": "Start battle with Fracture already applied."},
            {"level": 2, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 3, "desc": "Skill increases Fracture gain further."},
            {"level": 4, "stat": {"atk_pct": 0.12}, "desc": "+12% ATK."},
            {"level": 5, "desc": "Ultimate reduces enemy resistance."},
            {"level": 6, "desc": "Exposed enemies take bonus Break damage."},
        ],
    },

    # ═══════════════════════════════════════════════════════════════════════
    # ===== EXPANSION: COMMON (17) =====
    # ═══════════════════════════════════════════════════════════════════════
    {
        "id": "glass_tap", "name": "Glass Tap", "rarity": "COMMON",
        "element": "Void", "role": "Fracture Starter", "tags": ["Fracture"], "engine": ["Fracture"],
        "stats": {"hp": 520, "atk": 88, "def": 55, "spd": 104},
        "basic": {"name": "Glass Strike", "desc": "Deal Void damage and apply 1 Fracture."},
        "skill": {"name": "Weak Point Mark", "desc": "Apply 3 Fracture to one enemy."},
        "ult":   {"name": "Micro Collapse", "desc": "Trigger the 5-Fracture threshold effect immediately."},
        "passive": {"name": "Crack Sense", "desc": "Fractured enemies take slightly increased damage."},
        "lore": "One crack is all it takes.",
        "voice": "\u201cOne crack is all it takes.\u201d",
        "params": {"basic_fracture": 1, "skill_fracture": 3, "ult_fracture_trigger": 1},
        "cons": [
            {"level": 1, "desc": "Start battle with 2 Fracture on all enemies."},
            {"level": 2, "stat": {"atk_pct": 0.08}, "desc": "+8% ATK."},
            {"level": 3, "desc": "Skill applies +1 Fracture."},
            {"level": 4, "stat": {"spd_flat": 5}, "desc": "+5 SPD."},
            {"level": 5, "desc": "Fracture thresholds trigger slightly stronger effects."},
            {"level": 6, "desc": "First Fracture applied each battle is doubled."},
        ],
    },
    {
        "id": "shatter_spark", "name": "Shatter Spark", "rarity": "COMMON",
        "element": "Electric", "role": "Fracture Accelerator", "tags": ["Fracture"], "engine": ["Fracture"],
        "stats": {"hp": 510, "atk": 90, "def": 54, "spd": 106},
        "basic": {"name": "Pulse Crack", "desc": "Deal Electric damage and apply 1 Fracture."},
        "skill": {"name": "Overload Stress", "desc": "Apply 2 Fracture to all enemies."},
        "ult":   {"name": "Static Break", "desc": "Increase Fracture gain for 1 turn."},
        "passive": {"name": "Voltage Pressure", "desc": "Enemies gain extra Fracture when hit by allies."},
        "lore": "Stress builds faster than strength.",
        "voice": "\u201cStress builds faster than strength.\u201d",
        "params": {"basic_fracture": 1, "skill_fracture_all": 2, "fracture_gain": 0.20, "fracture_buff_turns": 1},
        "cons": [
            {"level": 1, "desc": "Start battle with +1 Fracture on enemies."},
            {"level": 2, "stat": {"spd_flat": 10}, "desc": "+10 SPD."},
            {"level": 3, "desc": "Skill applies +1 Fracture."},
            {"level": 4, "stat": {"atk_pct": 0.08}, "desc": "+8% ATK."},
            {"level": 5, "desc": "Fracture gain increased slightly."},
            {"level": 6, "desc": "Fracture applied by this unit cannot be reduced once per battle."},
        ],
    },
    {
        "id": "fault_line", "name": "Fault Line", "rarity": "COMMON",
        "element": "Earth", "role": "Fracture Builder", "tags": ["Fracture"], "engine": ["Fracture"],
        "stats": {"hp": 600, "atk": 82, "def": 74, "spd": 95},
        "basic": {"name": "Heavy Chip", "desc": "Deal Earth damage and apply 1 Fracture."},
        "skill": {"name": "Structural Weakening", "desc": "Apply 4 Fracture to one target."},
        "ult":   {"name": "Seismic Crack", "desc": "Spread Fracture from one enemy to the others."},
        "passive": {"name": "Pressure Memory", "desc": "Broken enemies gain Fracture faster."},
        "lore": "The ground always remembers pressure.",
        "voice": "\u201cThe ground always remembers pressure.\u201d",
        "params": {"basic_fracture": 1, "skill_fracture": 4, "ult_spread": 1},
        "cons": [
            {"level": 1, "desc": "Start battle with Fracture applied."},
            {"level": 2, "stat": {"def_pct": 0.10}, "desc": "+10% DEF."},
            {"level": 3, "desc": "Skill applies +1 Fracture."},
            {"level": 4, "stat": {"spd_flat": 5}, "desc": "+5 SPD."},
            {"level": 5, "desc": "Fracture spread range increased."},
            {"level": 6, "desc": "First spread each battle doubles Fracture transferred."},
        ],
    },
    {
        "id": "pulse_scout", "name": "Pulse Scout", "rarity": "COMMON",
        "element": "Electric", "role": "Turn Order Support", "tags": ["Energy"], "engine": ["Energy"],
        "stats": {"hp": 520, "atk": 88, "def": 58, "spd": 108},
        "basic": {"name": "Quick Zap", "desc": "Deal Electric damage and slightly advance an ally's turn meter."},
        "skill": {"name": "Initiate Flow", "desc": "Grant a small Speed boost to one ally for 1 turn."},
        "ult":   {"name": "Fast Signal", "desc": "Advance all allies slightly in turn order."},
        "passive": {"name": "Early Advantage", "desc": "The first ally action each battle gains bonus Energy."},
        "lore": "First to move decides the flow.",
        "voice": "\u201cFirst to move decides the flow.\u201d",
        "params": {"advance": 0.10, "spd_buff": 12, "spd_buff_turns": 1, "ult_advance_all": 0.15},
        "cons": [
            {"level": 1, "desc": "Start battle with +3 Energy on the fastest ally."},
            {"level": 2, "stat": {"spd_flat": 8}, "desc": "+8 SPD."},
            {"level": 3, "desc": "Skill gives a stronger Speed buff."},
            {"level": 4, "stat": {"def_pct": 0.05}, "desc": "+5% DEF."},
            {"level": 5, "desc": "Ultimate also grants small Energy."},
            {"level": 6, "desc": "Allies acting after this unit gain a slight damage boost."},
        ],
    },
    {
        "id": "ember_flicker", "name": "Ember Flicker", "rarity": "COMMON",
        "element": "Fire", "role": "Omen Builder", "tags": ["Omen"], "engine": ["Omen"],
        "stats": {"hp": 510, "atk": 92, "def": 55, "spd": 103},
        "basic": {"name": "Heat Tap", "desc": "Deal Fire damage and apply 1 Omen."},
        "skill": {"name": "Searing Pressure", "desc": "Apply Omen to the target and slightly increase existing stacks."},
        "ult":   {"name": "Ignite Signal", "desc": "Trigger a small portion of Omen on all enemies."},
        "passive": {"name": "Slow Burn", "desc": "Enemies with Omen take slightly increased damage over time."},
        "lore": "A spark is just a delayed disaster.",
        "voice": "\u201cA spark is just a delayed disaster.\u201d",
        "params": {"basic_omen": 1, "skill_omen": 2, "omen_amp": 0.15, "ult_omen_trig": 0.25},
        "cons": [
            {"level": 1, "desc": "Start battle with 1 Omen on all enemies."},
            {"level": 2, "stat": {"atk_pct": 0.10}, "desc": "+10% ATK."},
            {"level": 3, "desc": "Skill applies +1 Omen."},
            {"level": 4, "stat": {"spd_flat": 5}, "desc": "+5 SPD."},
            {"level": 5, "desc": "Omen trigger damage slightly increased."},
            {"level": 6, "desc": "First Omen applied each battle is doubled."},
        ],
    },
    {
        "id": "alloy_breaker", "name": "Alloy Breaker", "rarity": "COMMON",
        "element": "Earth", "role": "Break Starter", "tags": ["Break"], "engine": ["Break"],
        "stats": {"hp": 600, "atk": 84, "def": 72, "spd": 96},
        "basic": {"name": "Hammer Tap", "desc": "Deal Earth damage and increase the Break gauge."},
        "skill": {"name": "Stress Point", "desc": "Increase Break buildup significantly on one enemy."},
        "ult":   {"name": "Structural Weakness", "desc": "Increase Break vulnerability for a short duration."},
        "passive": {"name": "Pressure Insight", "desc": "Broken enemies take slightly increased damage from this unit."},
        "lore": "Every structure has its first crack.",
        "voice": "\u201cEvery structure has its first crack.\u201d",
        "params": {"break_gain": 14, "skill_break": 40, "break_vuln": 0.15, "break_vuln_turns": 2},
        "cons": [
            {"level": 1, "desc": "Start battle with slight Break applied."},
            {"level": 2, "stat": {"def_pct": 0.10}, "desc": "+10% DEF."},
            {"level": 3, "desc": "Skill increases Break buildup further."},
            {"level": 4, "stat": {"spd_flat": 5}, "desc": "+5 SPD."},
            {"level": 5, "desc": "Ultimate increases Break duration slightly."},
            {"level": 6, "desc": "First Break applied each battle is stronger."},
        ],
    },
    {
        "id": "arc_carrier", "name": "Arc Carrier", "rarity": "COMMON",
        "element": "Arcane", "role": "Energy Distributor", "tags": ["Energy"], "engine": ["Energy"],
        "stats": {"hp": 530, "atk": 86, "def": 60, "spd": 105},
        "basic": {"name": "Arc Tap", "desc": "Deal Arcane damage and grant a small amount of Energy to an ally."},
        "skill": {"name": "Charge Pass", "desc": "Give Energy to two allies."},
        "ult":   {"name": "Energy Burst", "desc": "Distribute Energy evenly across all allies."},
        "passive": {"name": "Flow Transfer", "desc": "Whenever this unit acts, the lowest-energy ally gains bonus Energy."},
        "lore": "Power means nothing if it's stuck.",
        "voice": "\u201cPower means nothing if it's stuck.\u201d",
        "params": {"give_energy": 4, "skill_give2": 6, "distribute": 1},
        "cons": [
            {"level": 1, "desc": "Start battle with +2 Energy on all allies."},
            {"level": 2, "stat": {"spd_flat": 8}, "desc": "+8 SPD."},
            {"level": 3, "desc": "Skill gives extra Energy."},
            {"level": 4, "stat": {"def_pct": 0.05}, "desc": "+5% DEF."},
            {"level": 5, "desc": "Ultimate distributes more evenly."},
            {"level": 6, "desc": "Overflow Energy slightly increases ally damage."},
        ],
    },
    {
        "id": "stone_warden", "name": "Stone Warden", "rarity": "COMMON",
        "element": "Earth", "role": "Shield Support", "tags": ["Sustain"], "engine": ["Sustain"],
        "stats": {"hp": 750, "atk": 72, "def": 98, "spd": 86},
        "basic": {"name": "Guard Tap", "desc": "Deal Earth damage and grant a small shield to an ally."},
        "skill": {"name": "Protect Line", "desc": "Shield the lowest-HP ally and reduce its damage taken."},
        "ult":   {"name": "Emergency Barrier", "desc": "Grant a team-wide small shield."},
        "passive": {"name": "Stability", "desc": "The first time an ally drops below 30% HP, they gain a shield (once per battle)."},
        "lore": "Stand long enough, and nothing passes.",
        "voice": "\u201cStand long enough, and nothing passes.\u201d",
        "params": {"basic_shield": 0.25, "skill_shield": 0.60, "ult_shield": 0.40, "dr_pct": 0.15, "dr_turns": 2},
        "cons": [
            {"level": 1, "desc": "Start battle with a shield."},
            {"level": 2, "stat": {"def_pct": 0.12}, "desc": "+12% DEF."},
            {"level": 3, "desc": "Skill shield increased."},
            {"level": 4, "stat": {"spd_flat": 5}, "desc": "+5 SPD."},
            {"level": 5, "desc": "Ultimate shield duration increased."},
            {"level": 6, "desc": "Shielded allies gain a slight damage boost."},
        ],
    },
    {
        "id": "iron_pulse", "name": "Iron Pulse", "rarity": "COMMON",
        "element": "Earth", "role": "Break Builder", "tags": ["Break"], "engine": ["Break"],
        "stats": {"hp": 600, "atk": 80, "def": 75, "spd": 95},
        "basic": {"name": "Heavy Tap", "desc": "Deal Earth damage and increase the Break gauge."},
        "skill": {"name": "Structural Pressure", "desc": "Greatly increase Break buildup on the target."},
        "ult":   {"name": "Crack Point", "desc": "Instantly increase Break progress."},
        "passive": {"name": "Weak Spot Learning", "desc": "Broken enemies take slightly increased damage."},
        "lore": "Pressure always finds a crack.",
        "voice": "\u201cPressure always finds a crack.\u201d",
        "params": {"break_gain": 14, "skill_break": 45, "ult_break": 60, "break_vuln": 0.10, "break_vuln_turns": 1},
        "cons": [
            {"level": 1, "desc": "Start battle with small Break progress applied."},
            {"level": 2, "stat": {"def_pct": 0.10}, "desc": "+10% DEF."},
            {"level": 3, "desc": "Skill increases Break buildup further."},
            {"level": 4, "stat": {"spd_flat": 5}, "desc": "+5 SPD."},
            {"level": 5, "desc": "Ultimate applies vulnerability."},
            {"level": 6, "desc": "Broken enemies take bonus damage from this unit."},
        ],
    },
    {
        "id": "flux_courier", "name": "Flux Courier", "rarity": "COMMON",
        "element": "Electric", "role": "Energy Support", "tags": ["Energy"], "engine": ["Energy"],
        "stats": {"hp": 530, "atk": 84, "def": 60, "spd": 107},
        "basic": {"name": "Quick Transfer", "desc": "Deal Electric damage and give 2 Energy to an ally."},
        "skill": {"name": "Energy Drop", "desc": "Give 6 Energy to a chosen ally."},
        "ult":   {"name": "Full Delivery", "desc": "Distribute a small amount of Energy to all allies."},
        "passive": {"name": "Relay Chain", "desc": "Whenever this unit acts, the lowest-energy ally gains bonus Energy."},
        "lore": "Energy moves faster than thought.",
        "voice": "\u201cEnergy moves faster than thought.\u201d",
        "params": {"give_energy": 2, "skill_give": 6, "distribute": 1},
        "cons": [
            {"level": 1, "desc": "Start battle with +3 Energy on all allies."},
            {"level": 2, "stat": {"spd_flat": 8}, "desc": "+8 SPD."},
            {"level": 3, "desc": "Skill gives +2 extra Energy."},
            {"level": 4, "stat": {"def_pct": 0.05}, "desc": "+5% DEF."},
            {"level": 5, "desc": "Ultimate improves distribution."},
            {"level": 6, "desc": "Energy overflow slightly buffs ally damage."},
        ],
    },
    {
        "id": "stone_guard", "name": "Stone Guard", "rarity": "COMMON",
        "element": "Earth", "role": "Mini Sustain", "tags": ["Sustain"], "engine": ["Sustain"],
        "stats": {"hp": 720, "atk": 70, "def": 95, "spd": 88},
        "basic": {"name": "Shield Bash", "desc": "Deal Earth damage and grant a small shield."},
        "skill": {"name": "Protect Ally", "desc": "Grant a shield to the lowest-HP ally."},
        "ult":   {"name": "Emergency Wall", "desc": "The team receives a small shield."},
        "passive": {"name": "Last Line", "desc": "Once per battle, prevent an ally from falling below 1 HP."},
        "lore": "Survival starts with standing still.",
        "voice": "\u201cSurvival starts with standing still.\u201d",
        "params": {"basic_shield": 0.22, "skill_shield": 0.55, "ult_shield": 0.35},
        "cons": [
            {"level": 1, "desc": "Start battle with a shield."},
            {"level": 2, "stat": {"def_pct": 0.12}, "desc": "+12% DEF."},
            {"level": 3, "desc": "Skill shields increased."},
            {"level": 4, "stat": {"spd_flat": 5}, "desc": "+5 SPD."},
            {"level": 5, "desc": "Ultimate shields last longer."},
            {"level": 6, "desc": "Shields slightly increase ally damage."},
        ],
    },
    {
        "id": "rift_spark", "name": "Rift Spark", "rarity": "COMMON",
        "element": "Void", "role": "Break Assist", "tags": ["Break"], "engine": ["Break"],
        "stats": {"hp": 500, "atk": 90, "def": 55, "spd": 106},
        "basic": {"name": "Void Tap", "desc": "Deal Void damage and increase Break slightly."},
        "skill": {"name": "Fracture Assist", "desc": "Increase Break vulnerability slightly."},
        "ult":   {"name": "Soft Collapse", "desc": "Enemies take increased Break damage briefly."},
        "passive": {"name": "Crack Insight", "desc": "Broken enemies take more damage from allies."},
        "lore": "Even fractures begin with light pressure.",
        "voice": "\u201cEven fractures begin with light pressure.\u201d",
        "params": {"break_gain": 12, "break_vuln": 0.12, "break_vuln_turns": 2, "broken_dmg": 0.08},
        "cons": [
            {"level": 1, "desc": "Start battle with slight Break applied."},
            {"level": 2, "stat": {"atk_pct": 0.08}, "desc": "+8% ATK."},
            {"level": 3, "desc": "Skill improves Break vulnerability."},
            {"level": 4, "stat": {"spd_flat": 5}, "desc": "+5 SPD."},
            {"level": 5, "desc": "Ultimate lasts longer."},
            {"level": 6, "desc": "Break effects applied by allies are slightly stronger."},
        ],
    },
    {
        "id": "echo_sprout", "name": "Echo Sprout", "rarity": "COMMON",
        "element": "Arcane", "role": "Copy Starter", "tags": ["Combo"], "engine": ["Combo"],
        "stats": {"hp": 540, "atk": 85, "def": 60, "spd": 101},
        "basic": {"name": "Resonant Tap", "desc": "Deal Arcane damage and store 1 Echo."},
        "skill": {"name": "Light Echo", "desc": "Repeat the last ally Basic Attack at reduced power."},
        "ult":   {"name": "Soft Repeat", "desc": "Repeat the last ally action at 30% power."},
        "passive": {"name": "Memory Seed", "desc": "Each Echo increases ally damage slightly."},
        "lore": "Even echoes begin as whispers.",
        "voice": "\u201cEven echoes begin as whispers.\u201d",
        "params": {"echo_store": 1, "echo_repeat_pct": 0.35, "ult_repeat_pct": 0.30, "echo_dmg": 0.02},
        "cons": [
            {"level": 1, "desc": "Start battle with 1 Echo."},
            {"level": 2, "stat": {"atk_pct": 0.08}, "desc": "+8% ATK."},
            {"level": 3, "desc": "Echo repeats slightly stronger."},
            {"level": 4, "stat": {"spd_flat": 5}, "desc": "+5 SPD."},
            {"level": 5, "desc": "Ultimate repeats at higher power."},
            {"level": 6, "desc": "Echoes can trigger minor on-hit effects."},
        ],
    },
    {
        "id": "spark_initiate", "name": "Spark Initiate", "rarity": "COMMON",
        "element": "Electric", "role": "Energy Starter", "tags": ["Energy"], "engine": ["Energy"],
        "stats": {"hp": 520, "atk": 86, "def": 55, "spd": 105},
        "basic": {"name": "Static Jab", "desc": "Deal Electric damage and gain 3 Energy."},
        "skill": {"name": "Quick Charge", "desc": "Gain 8 Energy. If used after another ally, gain bonus Energy."},
        "ult":   {"name": "Overload Flicker", "desc": "Gain full Energy instantly (small damage bonus)."},
        "passive": {"name": "Momentum Spark", "desc": "The first action in battle grants extra Energy."},
        "lore": "Even the smallest current becomes a storm.",
        "voice": "\u201cEven the smallest current becomes a storm.\u201d",
        "params": {"basic_energy": 3, "skill_energy": 8, "ult_full_energy": 1},
        "cons": [
            {"level": 1, "desc": "Start battle with +5 Energy."},
            {"level": 2, "stat": {"atk_pct": 0.08}, "desc": "+8% ATK."},
            {"level": 3, "desc": "Skill grants +2 extra Energy."},
            {"level": 4, "stat": {"spd_flat": 5}, "desc": "+5 SPD."},
            {"level": 5, "desc": "Ultimate slightly increases crit chance."},
            {"level": 6, "desc": "Energy gain is slightly increased for the entire team."},
        ],
    },
    {
        "id": "blade_runner", "name": "Blade Runner", "rarity": "COMMON",
        "element": "Physical", "role": "Combo Starter", "tags": ["Combo"], "engine": ["Combo"],
        "stats": {"hp": 540, "atk": 92, "def": 60, "spd": 103},
        "basic": {"name": "Clean Cut", "desc": "Deal Physical damage and increase Combo by 1."},
        "skill": {"name": "Follow Through", "desc": "Deal bonus damage if Combo exists and increase Combo further."},
        "ult":   {"name": "Chain Break", "desc": "Consume Combo stacks for burst damage."},
        "passive": {"name": "Flow Trigger", "desc": "The first hit in battle increases Combo twice."},
        "lore": "One strike starts the chain.",
        "voice": "\u201cOne strike starts the chain.\u201d",
        "params": {"basic_combo": 1, "skill_combo": 1, "combo_burst": 1},
        "cons": [
            {"level": 1, "desc": "Start battle with 1 Combo."},
            {"level": 2, "stat": {"atk_pct": 0.08}, "desc": "+8% ATK."},
            {"level": 3, "desc": "Skill increases Combo by +1 extra."},
            {"level": 4, "stat": {"spd_flat": 5}, "desc": "+5 SPD."},
            {"level": 5, "desc": "Ultimate deals more damage per Combo."},
            {"level": 6, "desc": "Combo cannot reset on the first turn."},
        ],
    },
    {
        "id": "arc_whisper", "name": "Arc Whisper", "rarity": "COMMON",
        "element": "Arcane", "role": "Omen Starter", "tags": ["Omen"], "engine": ["Omen"],
        "stats": {"hp": 510, "atk": 88, "def": 58, "spd": 104},
        "basic": {"name": "Silent Mark", "desc": "Deal Arcane damage and apply 1 Omen."},
        "skill": {"name": "Growing Doubt", "desc": "Apply 3 Omen. If the target already has Omen, increase stacks instead."},
        "ult":   {"name": "Minor Ill Omen", "desc": "Trigger 25% of the current Omen."},
        "passive": {"name": "Faint Curse", "desc": "Enemies with Omen take slightly increased damage."},
        "lore": "They never notice the first sign.",
        "voice": "\u201cThey never notice the first sign.\u201d",
        "params": {"basic_omen": 1, "skill_omen": 3, "ult_omen_trig": 0.25, "omen_dmg": 0.05},
        "cons": [
            {"level": 1, "desc": "Start battle with 2 Omen on all enemies."},
            {"level": 2, "stat": {"atk_pct": 0.10}, "desc": "+10% ATK."},
            {"level": 3, "desc": "Skill applies +1 Omen."},
            {"level": 4, "stat": {"spd_flat": 5}, "desc": "+5 SPD."},
            {"level": 5, "desc": "Omen triggered slightly stronger."},
            {"level": 6, "desc": "First Omen application each battle is doubled."},
        ],
    },
    {
        "id": "dust_initiate", "name": "Dust Initiate", "rarity": "COMMON",
        "element": "Physical", "role": "Generalist DPS", "tags": ["Combo"], "engine": [],
        "stats": {"hp": 560, "atk": 96, "def": 58, "spd": 100},
        "basic": {"name": "Quick Strike", "desc": "Deal Physical damage."},
        "skill": {"name": "Focused Hit", "desc": "Deal increased damage if the target has any debuff."},
        "ult":   {"name": "Final Scratch", "desc": "Simple burst damage."},
        "passive": {"name": "Adaptive Edge", "desc": "Deals slightly more damage each turn."},
        "lore": "Even dust can cut.",
        "voice": "\u201cEven dust can cut.\u201d",
        "params": {"debuff_bonus": 0.30, "ramp_per_turn": 0.04},
        "cons": [
            {"level": 1, "desc": "Start battle with a minor ATK buff."},
            {"level": 2, "stat": {"atk_pct": 0.08}, "desc": "+8% ATK."},
            {"level": 3, "desc": "Skill damage increased."},
            {"level": 4, "stat": {"spd_flat": 5}, "desc": "+5 SPD."},
            {"level": 5, "desc": "Ultimate damage increased."},
            {"level": 6, "desc": "First attack each battle has increased crit chance."},
        ],
    },
    {
            "id": "wild_rake",
            "name": "Wild Rake",
            "rarity": "COMMON",
            "element": "Fire",
            "role": "Energy Starter",
            "tags": [
                    "Omen"
            ],
            "engine": [
                    "Omen"
            ],
            "stats": {
                    "hp": 984,
                    "atk": 112,
                    "def": 88,
                    "spd": 106
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little energy."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds energy."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles energy support each turn."
            },
            "lore": "Some dice remember every hand they ever lost. This one keeps the receipts.",
            "voice": "\u201cAnte up. The table's mine.\u201d",
            "params": {
                    "basic_energy": 4,
                    "skill_energy": 10,
                    "passive_energy": 3
            }
    },
    {
            "id": "lunar_streak",
            "name": "Lunar Streak",
            "rarity": "COMMON",
            "element": "Ice",
            "role": "Break Starter",
            "tags": [
                    "Fracture"
            ],
            "engine": [
                    "Fracture"
            ],
            "stats": {
                    "hp": 1180,
                    "atk": 98,
                    "def": 72,
                    "spd": 99
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little break."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds break."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles break support each turn."
            },
            "lore": "It was carved from a debt no one could pay and rolled ever since.",
            "voice": "\u201cI don't gamble. I collect.\u201d",
            "params": {
                    "basic_fracture": 2,
                    "skill_break": 1,
                    "break_gain": 0.2
            }
    },
    {
            "id": "vivid_gambit",
            "name": "Vivid Gambit",
            "rarity": "COMMON",
            "element": "Electric",
            "role": "Omen Starter",
            "tags": [
                    "Break"
            ],
            "engine": [
                    "Break"
            ],
            "stats": {
                    "hp": 1068,
                    "atk": 121,
                    "def": 100,
                    "spd": 92
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little omen."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds omen."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles omen support each turn."
            },
            "lore": "Fortune is a wheel; this die is the axle it turns on.",
            "voice": "\u201cRoll again. I dare you.\u201d",
            "params": {
                    "basic_omen": 2,
                    "skill_omen": 6
            }
    },
    {
            "id": "tidal_comet",
            "name": "Tidal Comet",
            "rarity": "COMMON",
            "element": "Physical",
            "role": "Chill Starter",
            "tags": [
                    "Energy"
            ],
            "engine": [
                    "Energy"
            ],
            "stats": {
                    "hp": 956,
                    "atk": 108,
                    "def": 84,
                    "spd": 104
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little chill."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds chill."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles chill support each turn."
            },
            "lore": "They say it fell from a table in a room that no longer exists.",
            "voice": "\u201cThe count never lies.\u201d",
            "params": {
                    "basic_chill": 1,
                    "skill_chill_all": 4
            }
    },
    {
            "id": "jade_reel",
            "name": "Jade Reel",
            "rarity": "COMMON",
            "element": "Arcane",
            "role": "Shield Starter",
            "tags": [
                    "Combo"
            ],
            "engine": [
                    "Combo"
            ],
            "stats": {
                    "hp": 1152,
                    "atk": 95,
                    "def": 68,
                    "spd": 97
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little shield."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds shield."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles shield support each turn."
            },
            "lore": "Every pip is a promise, and every promise is a threat.",
            "voice": "\u201cEvens or odds, you still lose.\u201d",
            "params": {
                    "skill_shield": 0.2,
                    "shield_pct": 0.18
            }
    },
    {
            "id": "sable_stake",
            "name": "Sable Stake",
            "rarity": "COMMON",
            "element": "Light",
            "role": "Combo Starter",
            "tags": [
                    "Sustain"
            ],
            "engine": [
                    "Sustain"
            ],
            "stats": {
                    "hp": 1040,
                    "atk": 118,
                    "def": 96,
                    "spd": 90
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little combo."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds combo."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles combo support each turn."
            },
            "lore": "Cut from cold starlight, it counts outcomes before they happen.",
            "voice": "\u201cWatch the wheel. Watch it break.\u201d",
            "params": {
                    "basic_combo": 1,
                    "skill_combo": 2,
                    "combo_max": 6
            }
    },
    {
            "id": "frostbound_fold",
            "name": "Frostbound Fold",
            "rarity": "COMMON",
            "element": "Dark",
            "role": "Fortune Starter",
            "tags": [
                    "Fortune"
            ],
            "engine": [
                    "Fortune"
            ],
            "stats": {
                    "hp": 928,
                    "atk": 105,
                    "def": 80,
                    "spd": 103
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little fortune."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds fortune."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles fortune support each turn."
            },
            "lore": "The house forgot it in a drawer. It has been dealing itself in ever since.",
            "voice": "\u201cEvery face is the winning face.\u201d",
            "params": {
                    "give_energy": 8,
                    "team_dmg": 0.1
            }
    },
    {
            "id": "sovereign_hazard",
            "name": "Sovereign Hazard",
            "rarity": "COMMON",
            "element": "Blood",
            "role": "Fracture Starter",
            "tags": [
                    "Summon"
            ],
            "engine": [
                    "Summon"
            ],
            "stats": {
                    "hp": 1124,
                    "atk": 128,
                    "def": 64,
                    "spd": 95
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little fracture."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds fracture."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles fracture support each turn."
            },
            "lore": "Where it lands, probability kneels.",
            "voice": "\u201cLuck? No. Arithmetic.\u201d",
            "params": {
                    "basic_fracture": 3,
                    "skill_fracture": 4
            }
    },
    {
            "id": "grave_comet",
            "name": "Grave Comet",
            "rarity": "COMMON",
            "element": "Poison",
            "role": "Bleed Starter",
            "tags": [
                    "Control"
            ],
            "engine": [
                    "Control"
            ],
            "stats": {
                    "hp": 1012,
                    "atk": 115,
                    "def": 92,
                    "spd": 108
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little bleed."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds bleed."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles bleed support each turn."
            },
            "lore": "A gambler's last breath, pressed into six unforgiving faces.",
            "voice": "\u201cDouble or nothing \u2014 it's always nothing.\u201d",
            "params": {
                    "basic_bleed": 2,
                    "bleed_dmg": 0.15
            }
    },
    {
            "id": "endless_bluff",
            "name": "Endless Bluff",
            "rarity": "COMMON",
            "element": "Nature",
            "role": "Gravity Starter",
            "tags": [
                    "Omen"
            ],
            "engine": [
                    "Omen"
            ],
            "stats": {
                    "hp": 900,
                    "atk": 102,
                    "def": 76,
                    "spd": 101
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little gravity."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds gravity."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles gravity support each turn."
            },
            "lore": "It does not roll so much as decide.",
            "voice": "\u201cI already know your number.\u201d",
            "params": {
                    "basic_gravity": 1,
                    "spd_up": 0.1
            }
    },
    {
            "id": "twisted_mark",
            "name": "Twisted Mark",
            "rarity": "COMMON",
            "element": "Wind",
            "role": "Energy Starter",
            "tags": [
                    "Fracture"
            ],
            "engine": [
                    "Fracture"
            ],
            "stats": {
                    "hp": 1096,
                    "atk": 125,
                    "def": 60,
                    "spd": 94
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little energy."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds energy."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles energy support each turn."
            },
            "lore": "Born in the space between a bet and its regret.",
            "voice": "\u201cThe pot's called. Pay up.\u201d",
            "params": {
                    "basic_energy": 4,
                    "skill_energy": 10,
                    "passive_energy": 3
            }
    },
    {
            "id": "ashen_comet",
            "name": "Ashen Comet",
            "rarity": "COMMON",
            "element": "Time",
            "role": "Break Starter",
            "tags": [
                    "Break"
            ],
            "engine": [
                    "Break"
            ],
            "stats": {
                    "hp": 984,
                    "atk": 112,
                    "def": 88,
                    "spd": 106
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little break."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds break."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles break support each turn."
            },
            "lore": "The odds bend around it like light around a stone.",
            "voice": "\u201cSix ways to fall, one way to win.\u201d",
            "params": {
                    "basic_fracture": 2,
                    "skill_break": 1,
                    "break_gain": 0.2
            }
    },
    {
            "id": "burning_roulette",
            "name": "Burning Roulette",
            "rarity": "COMMON",
            "element": "Void",
            "role": "Omen Starter",
            "tags": [
                    "Energy"
            ],
            "engine": [
                    "Energy"
            ],
            "stats": {
                    "hp": 1180,
                    "atk": 98,
                    "def": 72,
                    "spd": 99
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little omen."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds omen."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles omen support each turn."
            },
            "lore": "It has never lost. It simply has not finished playing.",
            "voice": "\u201cBet against me. Please.\u201d",
            "params": {
                    "basic_omen": 2,
                    "skill_omen": 6
            }
    },
    {
            "id": "withered_ante",
            "name": "Withered Ante",
            "rarity": "COMMON",
            "element": "Earth",
            "role": "Chill Starter",
            "tags": [
                    "Combo"
            ],
            "engine": [
                    "Combo"
            ],
            "stats": {
                    "hp": 1068,
                    "atk": 121,
                    "def": 100,
                    "spd": 92
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little chill."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds chill."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles chill support each turn."
            },
            "lore": "A relic of a game whose rules were rewritten mid-throw.",
            "voice": "\u201cThe dealer folds first.\u201d",
            "params": {
                    "basic_chill": 1,
                    "skill_chill_all": 4
            }
    },
    {
            "id": "broken_bettor",
            "name": "Broken Bettor",
            "rarity": "COMMON",
            "element": "Fire",
            "role": "Shield Starter",
            "tags": [
                    "Sustain"
            ],
            "engine": [
                    "Sustain"
            ],
            "stats": {
                    "hp": 956,
                    "atk": 108,
                    "def": 84,
                    "spd": 104
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little shield."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds shield."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles shield support each turn."
            },
            "lore": "Loaded not with lead, but with certainty.",
            "voice": "\u201cCome closer. Let me read your odds.\u201d",
            "params": {
                    "skill_shield": 0.2,
                    "shield_pct": 0.18
            }
    },
    {
            "id": "ruby_verdict",
            "name": "Ruby Verdict",
            "rarity": "COMMON",
            "element": "Ice",
            "role": "Combo Starter",
            "tags": [
                    "Fortune"
            ],
            "engine": [
                    "Fortune"
            ],
            "stats": {
                    "hp": 1152,
                    "atk": 95,
                    "def": 68,
                    "spd": 97
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little combo."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds combo."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles combo support each turn."
            },
            "lore": "It hums with the sound of every coin that ever hit the felt.",
            "voice": "\u201cThe wheel remembers your name.\u201d",
            "params": {
                    "basic_combo": 1,
                    "skill_combo": 2,
                    "combo_max": 6
            }
    },
    {
            "id": "cursed_tally",
            "name": "Cursed Tally",
            "rarity": "COMMON",
            "element": "Electric",
            "role": "Fortune Starter",
            "tags": [
                    "Summon"
            ],
            "engine": [
                    "Summon"
            ],
            "stats": {
                    "hp": 1040,
                    "atk": 118,
                    "def": 96,
                    "spd": 90
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little fortune."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds fortune."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles fortune support each turn."
            },
            "lore": "The dealer who made it never blinked again.",
            "voice": "\u201cAll in. There was never another option.\u201d",
            "params": {
                    "give_energy": 8,
                    "team_dmg": 0.1
            }
    },
    {
            "id": "hollow_tally",
            "name": "Hollow Tally",
            "rarity": "COMMON",
            "element": "Physical",
            "role": "Fracture Starter",
            "tags": [
                    "Control"
            ],
            "engine": [
                    "Control"
            ],
            "stats": {
                    "hp": 928,
                    "atk": 105,
                    "def": 80,
                    "spd": 103
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little fracture."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds fracture."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles fracture support each turn."
            },
            "lore": "It keeps a tally no ledger could hold.",
            "voice": "\u201cMy pips are your obituary.\u201d",
            "params": {
                    "basic_fracture": 3,
                    "skill_fracture": 4
            }
    },
    {
            "id": "prime_bluff",
            "name": "Prime Bluff",
            "rarity": "COMMON",
            "element": "Arcane",
            "role": "Bleed Starter",
            "tags": [
                    "Omen"
            ],
            "engine": [
                    "Omen"
            ],
            "stats": {
                    "hp": 1124,
                    "atk": 128,
                    "def": 64,
                    "spd": 95
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little bleed."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds bleed."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles bleed support each turn."
            },
            "lore": "Rolled once at the end of the world; it liked the result.",
            "voice": "\u201cThe game ended when I entered it.\u201d",
            "params": {
                    "basic_bleed": 2,
                    "bleed_dmg": 0.15
            }
    },
    {
            "id": "thunderous_chance",
            "name": "Thunderous Chance",
            "rarity": "COMMON",
            "element": "Light",
            "role": "Gravity Starter",
            "tags": [
                    "Fracture"
            ],
            "engine": [
                    "Fracture"
            ],
            "stats": {
                    "hp": 1012,
                    "atk": 115,
                    "def": 92,
                    "spd": 108
            },
            "basic": {
                    "name": "Toss",
                    "desc": "Deal damage and build a little gravity."
            },
            "skill": {
                    "name": "Press",
                    "desc": "A stronger strike that adds gravity."
            },
            "ult": {
                    "name": "Spill",
                    "desc": "A burst of damage across the foe."
            },
            "passive": {
                    "name": "Habit",
                    "desc": "Passively trickles gravity support each turn."
            },
            "lore": "Fate whittled it down to exactly what it needed to be.",
            "voice": "\u201cSpin. I enjoy the noise.\u201d",
            "params": {
                    "basic_gravity": 1,
                    "spd_up": 0.1
            }
    },
    {
            "id": "sanguine_fold",
            "name": "Sanguine Fold",
            "rarity": "RARE",
            "element": "Dark",
            "role": "Energy Specialist",
            "tags": [
                    "Break",
                    "Energy"
            ],
            "engine": [
                    "Break",
                    "Energy"
            ],
            "stats": {
                    "hp": 1050,
                    "atk": 124,
                    "def": 88,
                    "spd": 107
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply energy."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify energy and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored energy."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's energy handling."
            },
            "lore": "Some dice remember every hand they ever lost. This one keeps the receipts.",
            "voice": "\u201cAnte up. The table's mine.\u201d",
            "params": {
                    "basic_energy": 4,
                    "skill_energy": 10,
                    "passive_energy": 3
            }
    },
    {
            "id": "feral_marker",
            "name": "Feral Marker",
            "rarity": "RARE",
            "element": "Blood",
            "role": "Break Specialist",
            "tags": [
                    "Combo"
            ],
            "engine": [
                    "Combo"
            ],
            "stats": {
                    "hp": 1267,
                    "atk": 156,
                    "def": 66,
                    "spd": 96
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply break."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify break and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored break."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's break handling."
            },
            "lore": "It was carved from a debt no one could pay and rolled ever since.",
            "voice": "\u201cI don't gamble. I collect.\u201d",
            "params": {
                    "basic_fracture": 2,
                    "skill_break": 1,
                    "break_gain": 0.2
            }
    },
    {
            "id": "fractal_odds",
            "name": "Fractal Odds",
            "rarity": "RARE",
            "element": "Poison",
            "role": "Omen Specialist",
            "tags": [
                    "Sustain"
            ],
            "engine": [
                    "Sustain"
            ],
            "stats": {
                    "hp": 1143,
                    "atk": 138,
                    "def": 105,
                    "spd": 115
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply omen."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify omen and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored omen."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's omen handling."
            },
            "lore": "Fortune is a wheel; this die is the axle it turns on.",
            "voice": "\u201cRoll again. I dare you.\u201d",
            "params": {
                    "basic_omen": 2,
                    "skill_omen": 6
            }
    },
    {
            "id": "ruby_gambit",
            "name": "Ruby Gambit",
            "rarity": "RARE",
            "element": "Nature",
            "role": "Chill Specialist",
            "tags": [
                    "Fortune",
                    "Summon"
            ],
            "engine": [
                    "Fortune",
                    "Summon"
            ],
            "stats": {
                    "hp": 1360,
                    "atk": 120,
                    "def": 83,
                    "spd": 104
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply chill."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify chill and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored chill."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's chill handling."
            },
            "lore": "They say it fell from a table in a room that no longer exists.",
            "voice": "\u201cThe count never lies.\u201d",
            "params": {
                    "basic_chill": 1,
                    "skill_chill_all": 4
            }
    },
    {
            "id": "broken_trickster",
            "name": "Broken Trickster",
            "rarity": "RARE",
            "element": "Wind",
            "role": "Shield Specialist",
            "tags": [
                    "Control"
            ],
            "engine": [
                    "Control"
            ],
            "stats": {
                    "hp": 1236,
                    "atk": 151,
                    "def": 122,
                    "spd": 93
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply shield."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify shield and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored shield."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's shield handling."
            },
            "lore": "Every pip is a promise, and every promise is a threat.",
            "voice": "\u201cEvens or odds, you still lose.\u201d",
            "params": {
                    "skill_shield": 0.2,
                    "shield_pct": 0.18
            }
    },
    {
            "id": "umbral_ledger",
            "name": "Umbral Ledger",
            "rarity": "RARE",
            "element": "Time",
            "role": "Combo Specialist",
            "tags": [
                    "Omen"
            ],
            "engine": [
                    "Omen"
            ],
            "stats": {
                    "hp": 1112,
                    "atk": 133,
                    "def": 100,
                    "spd": 112
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply combo."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify combo and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored combo."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's combo handling."
            },
            "lore": "Cut from cold starlight, it counts outcomes before they happen.",
            "voice": "\u201cWatch the wheel. Watch it break.\u201d",
            "params": {
                    "basic_combo": 1,
                    "skill_combo": 2,
                    "combo_max": 6
            }
    },
    {
            "id": "sanguine_rounder",
            "name": "Sanguine Rounder",
            "rarity": "RARE",
            "element": "Void",
            "role": "Fortune Specialist",
            "tags": [
                    "Fracture",
                    "Break"
            ],
            "engine": [
                    "Fracture",
                    "Break"
            ],
            "stats": {
                    "hp": 1329,
                    "atk": 115,
                    "def": 77,
                    "spd": 101
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply fortune."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify fortune and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored fortune."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's fortune handling."
            },
            "lore": "The house forgot it in a drawer. It has been dealing itself in ever since.",
            "voice": "\u201cEvery face is the winning face.\u201d",
            "params": {
                    "give_energy": 8,
                    "team_dmg": 0.1
            }
    },
    {
            "id": "eternal_shill",
            "name": "Eternal Shill",
            "rarity": "RARE",
            "element": "Earth",
            "role": "Fracture Specialist",
            "tags": [
                    "Energy"
            ],
            "engine": [
                    "Energy"
            ],
            "stats": {
                    "hp": 1205,
                    "atk": 146,
                    "def": 116,
                    "spd": 90
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply fracture."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify fracture and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored fracture."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's fracture handling."
            },
            "lore": "Where it lands, probability kneels.",
            "voice": "\u201cLuck? No. Arithmetic.\u201d",
            "params": {
                    "basic_fracture": 3,
                    "skill_fracture": 4
            }
    },
    {
            "id": "sanguine_pot",
            "name": "Sanguine Pot",
            "rarity": "RARE",
            "element": "Fire",
            "role": "Bleed Specialist",
            "tags": [
                    "Combo"
            ],
            "engine": [
                    "Combo"
            ],
            "stats": {
                    "hp": 1081,
                    "atk": 128,
                    "def": 94,
                    "spd": 110
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply bleed."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify bleed and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored bleed."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's bleed handling."
            },
            "lore": "A gambler's last breath, pressed into six unforgiving faces.",
            "voice": "\u201cDouble or nothing \u2014 it's always nothing.\u201d",
            "params": {
                    "basic_bleed": 2,
                    "bleed_dmg": 0.15
            }
    },
    {
            "id": "silent_roulette",
            "name": "Silent Roulette",
            "rarity": "RARE",
            "element": "Ice",
            "role": "Gravity Specialist",
            "tags": [
                    "Sustain",
                    "Fortune"
            ],
            "engine": [
                    "Sustain",
                    "Fortune"
            ],
            "stats": {
                    "hp": 1298,
                    "atk": 160,
                    "def": 72,
                    "spd": 98
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply gravity."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify gravity and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored gravity."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's gravity handling."
            },
            "lore": "It does not roll so much as decide.",
            "voice": "\u201cI already know your number.\u201d",
            "params": {
                    "basic_gravity": 1,
                    "spd_up": 0.1
            }
    },
    {
            "id": "static_verdict",
            "name": "Static Verdict",
            "rarity": "RARE",
            "element": "Electric",
            "role": "Energy Specialist",
            "tags": [
                    "Summon"
            ],
            "engine": [
                    "Summon"
            ],
            "stats": {
                    "hp": 1174,
                    "atk": 142,
                    "def": 111,
                    "spd": 118
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply energy."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify energy and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored energy."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's energy handling."
            },
            "lore": "Born in the space between a bet and its regret.",
            "voice": "\u201cThe pot's called. Pay up.\u201d",
            "params": {
                    "basic_energy": 4,
                    "skill_energy": 10,
                    "passive_energy": 3
            }
    },
    {
            "id": "hollow_fold",
            "name": "Hollow Fold",
            "rarity": "RARE",
            "element": "Physical",
            "role": "Break Specialist",
            "tags": [
                    "Control"
            ],
            "engine": [
                    "Control"
            ],
            "stats": {
                    "hp": 1050,
                    "atk": 124,
                    "def": 88,
                    "spd": 107
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply break."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify break and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored break."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's break handling."
            },
            "lore": "The odds bend around it like light around a stone.",
            "voice": "\u201cSix ways to fall, one way to win.\u201d",
            "params": {
                    "basic_fracture": 2,
                    "skill_break": 1,
                    "break_gain": 0.2
            }
    },
    {
            "id": "wild_cascade",
            "name": "Wild Cascade",
            "rarity": "RARE",
            "element": "Arcane",
            "role": "Omen Specialist",
            "tags": [
                    "Omen",
                    "Fracture"
            ],
            "engine": [
                    "Omen",
                    "Fracture"
            ],
            "stats": {
                    "hp": 1267,
                    "atk": 156,
                    "def": 66,
                    "spd": 96
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply omen."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify omen and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored omen."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's omen handling."
            },
            "lore": "It has never lost. It simply has not finished playing.",
            "voice": "\u201cBet against me. Please.\u201d",
            "params": {
                    "basic_omen": 2,
                    "skill_omen": 6
            }
    },
    {
            "id": "burning_bettor",
            "name": "Burning Bettor",
            "rarity": "RARE",
            "element": "Light",
            "role": "Chill Specialist",
            "tags": [
                    "Break"
            ],
            "engine": [
                    "Break"
            ],
            "stats": {
                    "hp": 1143,
                    "atk": 138,
                    "def": 105,
                    "spd": 115
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply chill."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify chill and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored chill."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's chill handling."
            },
            "lore": "A relic of a game whose rules were rewritten mid-throw.",
            "voice": "\u201cThe dealer folds first.\u201d",
            "params": {
                    "basic_chill": 1,
                    "skill_chill_all": 4
            }
    },
    {
            "id": "endless_reel",
            "name": "Endless Reel",
            "rarity": "RARE",
            "element": "Dark",
            "role": "Shield Specialist",
            "tags": [
                    "Energy"
            ],
            "engine": [
                    "Energy"
            ],
            "stats": {
                    "hp": 1360,
                    "atk": 120,
                    "def": 83,
                    "spd": 104
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply shield."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify shield and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored shield."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's shield handling."
            },
            "lore": "Loaded not with lead, but with certainty.",
            "voice": "\u201cCome closer. Let me read your odds.\u201d",
            "params": {
                    "skill_shield": 0.2,
                    "shield_pct": 0.18
            }
    },
    {
            "id": "charged_zenith",
            "name": "Charged Zenith",
            "rarity": "RARE",
            "element": "Blood",
            "role": "Combo Specialist",
            "tags": [
                    "Combo",
                    "Sustain"
            ],
            "engine": [
                    "Combo",
                    "Sustain"
            ],
            "stats": {
                    "hp": 1236,
                    "atk": 151,
                    "def": 122,
                    "spd": 93
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply combo."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify combo and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored combo."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's combo handling."
            },
            "lore": "It hums with the sound of every coin that ever hit the felt.",
            "voice": "\u201cThe wheel remembers your name.\u201d",
            "params": {
                    "basic_combo": 1,
                    "skill_combo": 2,
                    "combo_max": 6
            }
    },
    {
            "id": "shrouded_aeon",
            "name": "Shrouded Aeon",
            "rarity": "RARE",
            "element": "Poison",
            "role": "Fortune Specialist",
            "tags": [
                    "Fortune"
            ],
            "engine": [
                    "Fortune"
            ],
            "stats": {
                    "hp": 1112,
                    "atk": 133,
                    "def": 100,
                    "spd": 112
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply fortune."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify fortune and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored fortune."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's fortune handling."
            },
            "lore": "The dealer who made it never blinked again.",
            "voice": "\u201cAll in. There was never another option.\u201d",
            "params": {
                    "give_energy": 8,
                    "team_dmg": 0.1
            }
    },
    {
            "id": "marked_wager",
            "name": "Marked Wager",
            "rarity": "RARE",
            "element": "Nature",
            "role": "Fracture Specialist",
            "tags": [
                    "Summon"
            ],
            "engine": [
                    "Summon"
            ],
            "stats": {
                    "hp": 1329,
                    "atk": 115,
                    "def": 77,
                    "spd": 101
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply fracture."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify fracture and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored fracture."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's fracture handling."
            },
            "lore": "It keeps a tally no ledger could hold.",
            "voice": "\u201cMy pips are your obituary.\u201d",
            "params": {
                    "basic_fracture": 3,
                    "skill_fracture": 4
            }
    },
    {
            "id": "ruby_nebula",
            "name": "Ruby Nebula",
            "rarity": "RARE",
            "element": "Wind",
            "role": "Bleed Specialist",
            "tags": [
                    "Control",
                    "Omen"
            ],
            "engine": [
                    "Control",
                    "Omen"
            ],
            "stats": {
                    "hp": 1205,
                    "atk": 146,
                    "def": 116,
                    "spd": 90
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply bleed."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify bleed and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored bleed."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's bleed handling."
            },
            "lore": "Rolled once at the end of the world; it liked the result.",
            "voice": "\u201cThe game ended when I entered it.\u201d",
            "params": {
                    "basic_bleed": 2,
                    "bleed_dmg": 0.15
            }
    },
    {
            "id": "gilded_zenith",
            "name": "Gilded Zenith",
            "rarity": "RARE",
            "element": "Time",
            "role": "Gravity Specialist",
            "tags": [
                    "Fracture"
            ],
            "engine": [
                    "Fracture"
            ],
            "stats": {
                    "hp": 1081,
                    "atk": 128,
                    "def": 94,
                    "spd": 110
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply gravity."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify gravity and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored gravity."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's gravity handling."
            },
            "lore": "Fate whittled it down to exactly what it needed to be.",
            "voice": "\u201cSpin. I enjoy the noise.\u201d",
            "params": {
                    "basic_gravity": 1,
                    "spd_up": 0.1
            }
    },
    {
            "id": "verdant_roller",
            "name": "Verdant Roller",
            "rarity": "RARE",
            "element": "Void",
            "role": "Energy Specialist",
            "tags": [
                    "Break"
            ],
            "engine": [
                    "Break"
            ],
            "stats": {
                    "hp": 1298,
                    "atk": 160,
                    "def": 72,
                    "spd": 98
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply energy."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify energy and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored energy."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's energy handling."
            },
            "lore": "Some dice remember every hand they ever lost. This one keeps the receipts.",
            "voice": "\u201cAnte up. The table's mine.\u201d",
            "params": {
                    "basic_energy": 4,
                    "skill_energy": 10,
                    "passive_energy": 3
            }
    },
    {
            "id": "wild_pot",
            "name": "Wild Pot",
            "rarity": "RARE",
            "element": "Earth",
            "role": "Break Specialist",
            "tags": [
                    "Energy",
                    "Combo"
            ],
            "engine": [
                    "Energy",
                    "Combo"
            ],
            "stats": {
                    "hp": 1174,
                    "atk": 142,
                    "def": 111,
                    "spd": 118
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply break."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify break and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored break."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's break handling."
            },
            "lore": "It was carved from a debt no one could pay and rolled ever since.",
            "voice": "\u201cI don't gamble. I collect.\u201d",
            "params": {
                    "basic_fracture": 2,
                    "skill_break": 1,
                    "break_gain": 0.2
            }
    },
    {
            "id": "argent_verdict",
            "name": "Argent Verdict",
            "rarity": "RARE",
            "element": "Fire",
            "role": "Omen Specialist",
            "tags": [
                    "Sustain"
            ],
            "engine": [
                    "Sustain"
            ],
            "stats": {
                    "hp": 1050,
                    "atk": 124,
                    "def": 88,
                    "spd": 107
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply omen."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify omen and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored omen."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's omen handling."
            },
            "lore": "Fortune is a wheel; this die is the axle it turns on.",
            "voice": "\u201cRoll again. I dare you.\u201d",
            "params": {
                    "basic_omen": 2,
                    "skill_omen": 6
            }
    },
    {
            "id": "burning_sentinel",
            "name": "Burning Sentinel",
            "rarity": "RARE",
            "element": "Ice",
            "role": "Chill Specialist",
            "tags": [
                    "Fortune"
            ],
            "engine": [
                    "Fortune"
            ],
            "stats": {
                    "hp": 1267,
                    "atk": 156,
                    "def": 66,
                    "spd": 96
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply chill."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify chill and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored chill."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's chill handling."
            },
            "lore": "They say it fell from a table in a room that no longer exists.",
            "voice": "\u201cThe count never lies.\u201d",
            "params": {
                    "basic_chill": 1,
                    "skill_chill_all": 4
            }
    },
    {
            "id": "fated_reel",
            "name": "Fated Reel",
            "rarity": "RARE",
            "element": "Electric",
            "role": "Shield Specialist",
            "tags": [
                    "Summon",
                    "Control"
            ],
            "engine": [
                    "Summon",
                    "Control"
            ],
            "stats": {
                    "hp": 1143,
                    "atk": 138,
                    "def": 105,
                    "spd": 115
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply shield."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify shield and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored shield."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's shield handling."
            },
            "lore": "Every pip is a promise, and every promise is a threat.",
            "voice": "\u201cEvens or odds, you still lose.\u201d",
            "params": {
                    "skill_shield": 0.2,
                    "shield_pct": 0.18
            }
    },
    {
            "id": "lunar_roller",
            "name": "Lunar Roller",
            "rarity": "RARE",
            "element": "Physical",
            "role": "Combo Specialist",
            "tags": [
                    "Omen"
            ],
            "engine": [
                    "Omen"
            ],
            "stats": {
                    "hp": 1360,
                    "atk": 120,
                    "def": 83,
                    "spd": 104
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply combo."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify combo and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored combo."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's combo handling."
            },
            "lore": "Cut from cold starlight, it counts outcomes before they happen.",
            "voice": "\u201cWatch the wheel. Watch it break.\u201d",
            "params": {
                    "basic_combo": 1,
                    "skill_combo": 2,
                    "combo_max": 6
            }
    },
    {
            "id": "pale_chance",
            "name": "Pale Chance",
            "rarity": "RARE",
            "element": "Arcane",
            "role": "Fortune Specialist",
            "tags": [
                    "Fracture"
            ],
            "engine": [
                    "Fracture"
            ],
            "stats": {
                    "hp": 1236,
                    "atk": 151,
                    "def": 122,
                    "spd": 93
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply fortune."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify fortune and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored fortune."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's fortune handling."
            },
            "lore": "The house forgot it in a drawer. It has been dealing itself in ever since.",
            "voice": "\u201cEvery face is the winning face.\u201d",
            "params": {
                    "give_energy": 8,
                    "team_dmg": 0.1
            }
    },
    {
            "id": "velvet_quasar",
            "name": "Velvet Quasar",
            "rarity": "RARE",
            "element": "Light",
            "role": "Fracture Specialist",
            "tags": [
                    "Break",
                    "Energy"
            ],
            "engine": [
                    "Break",
                    "Energy"
            ],
            "stats": {
                    "hp": 1112,
                    "atk": 133,
                    "def": 100,
                    "spd": 112
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply fracture."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify fracture and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored fracture."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's fracture handling."
            },
            "lore": "Where it lands, probability kneels.",
            "voice": "\u201cLuck? No. Arithmetic.\u201d",
            "params": {
                    "basic_fracture": 3,
                    "skill_fracture": 4
            }
    },
    {
            "id": "fated_herald",
            "name": "Fated Herald",
            "rarity": "RARE",
            "element": "Dark",
            "role": "Bleed Specialist",
            "tags": [
                    "Combo"
            ],
            "engine": [
                    "Combo"
            ],
            "stats": {
                    "hp": 1329,
                    "atk": 115,
                    "def": 77,
                    "spd": 101
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply bleed."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify bleed and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored bleed."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's bleed handling."
            },
            "lore": "A gambler's last breath, pressed into six unforgiving faces.",
            "voice": "\u201cDouble or nothing \u2014 it's always nothing.\u201d",
            "params": {
                    "basic_bleed": 2,
                    "bleed_dmg": 0.15
            }
    },
    {
            "id": "fated_bluff",
            "name": "Fated Bluff",
            "rarity": "RARE",
            "element": "Blood",
            "role": "Gravity Specialist",
            "tags": [
                    "Sustain"
            ],
            "engine": [
                    "Sustain"
            ],
            "stats": {
                    "hp": 1205,
                    "atk": 146,
                    "def": 116,
                    "spd": 90
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply gravity."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify gravity and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored gravity."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's gravity handling."
            },
            "lore": "It does not roll so much as decide.",
            "voice": "\u201cI already know your number.\u201d",
            "params": {
                    "basic_gravity": 1,
                    "spd_up": 0.1
            }
    },
    {
            "id": "molten_bluff",
            "name": "Molten Bluff",
            "rarity": "RARE",
            "element": "Poison",
            "role": "Energy Specialist",
            "tags": [
                    "Fortune",
                    "Summon"
            ],
            "engine": [
                    "Fortune",
                    "Summon"
            ],
            "stats": {
                    "hp": 1081,
                    "atk": 128,
                    "def": 94,
                    "spd": 110
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply energy."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify energy and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored energy."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's energy handling."
            },
            "lore": "Born in the space between a bet and its regret.",
            "voice": "\u201cThe pot's called. Pay up.\u201d",
            "params": {
                    "basic_energy": 4,
                    "skill_energy": 10,
                    "passive_energy": 3
            }
    },
    {
            "id": "withered_reaver",
            "name": "Withered Reaver",
            "rarity": "RARE",
            "element": "Nature",
            "role": "Break Specialist",
            "tags": [
                    "Control"
            ],
            "engine": [
                    "Control"
            ],
            "stats": {
                    "hp": 1298,
                    "atk": 160,
                    "def": 72,
                    "spd": 98
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply break."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify break and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored break."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's break handling."
            },
            "lore": "The odds bend around it like light around a stone.",
            "voice": "\u201cSix ways to fall, one way to win.\u201d",
            "params": {
                    "basic_fracture": 2,
                    "skill_break": 1,
                    "break_gain": 0.2
            }
    },
    {
            "id": "lunar_bluff",
            "name": "Lunar Bluff",
            "rarity": "RARE",
            "element": "Wind",
            "role": "Omen Specialist",
            "tags": [
                    "Omen"
            ],
            "engine": [
                    "Omen"
            ],
            "stats": {
                    "hp": 1174,
                    "atk": 142,
                    "def": 111,
                    "spd": 118
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply omen."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify omen and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored omen."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's omen handling."
            },
            "lore": "It has never lost. It simply has not finished playing.",
            "voice": "\u201cBet against me. Please.\u201d",
            "params": {
                    "basic_omen": 2,
                    "skill_omen": 6
            }
    },
    {
            "id": "hidden_broker",
            "name": "Hidden Broker",
            "rarity": "RARE",
            "element": "Time",
            "role": "Chill Specialist",
            "tags": [
                    "Fracture",
                    "Break"
            ],
            "engine": [
                    "Fracture",
                    "Break"
            ],
            "stats": {
                    "hp": 1050,
                    "atk": 124,
                    "def": 88,
                    "spd": 107
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply chill."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify chill and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored chill."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's chill handling."
            },
            "lore": "A relic of a game whose rules were rewritten mid-throw.",
            "voice": "\u201cThe dealer folds first.\u201d",
            "params": {
                    "basic_chill": 1,
                    "skill_chill_all": 4
            }
    },
    {
            "id": "argent_vortex",
            "name": "Argent Vortex",
            "rarity": "RARE",
            "element": "Void",
            "role": "Shield Specialist",
            "tags": [
                    "Energy"
            ],
            "engine": [
                    "Energy"
            ],
            "stats": {
                    "hp": 1267,
                    "atk": 156,
                    "def": 66,
                    "spd": 96
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply shield."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify shield and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored shield."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's shield handling."
            },
            "lore": "Loaded not with lead, but with certainty.",
            "voice": "\u201cCome closer. Let me read your odds.\u201d",
            "params": {
                    "skill_shield": 0.2,
                    "shield_pct": 0.18
            }
    },
    {
            "id": "doomed_sentinel",
            "name": "Doomed Sentinel",
            "rarity": "RARE",
            "element": "Earth",
            "role": "Combo Specialist",
            "tags": [
                    "Combo"
            ],
            "engine": [
                    "Combo"
            ],
            "stats": {
                    "hp": 1143,
                    "atk": 138,
                    "def": 105,
                    "spd": 115
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply combo."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify combo and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored combo."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's combo handling."
            },
            "lore": "It hums with the sound of every coin that ever hit the felt.",
            "voice": "\u201cThe wheel remembers your name.\u201d",
            "params": {
                    "basic_combo": 1,
                    "skill_combo": 2,
                    "combo_max": 6
            }
    },
    {
            "id": "silent_odds",
            "name": "Silent Odds",
            "rarity": "RARE",
            "element": "Fire",
            "role": "Fortune Specialist",
            "tags": [
                    "Sustain",
                    "Fortune"
            ],
            "engine": [
                    "Sustain",
                    "Fortune"
            ],
            "stats": {
                    "hp": 1360,
                    "atk": 120,
                    "def": 83,
                    "spd": 104
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply fortune."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify fortune and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored fortune."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's fortune handling."
            },
            "lore": "The dealer who made it never blinked again.",
            "voice": "\u201cAll in. There was never another option.\u201d",
            "params": {
                    "give_energy": 8,
                    "team_dmg": 0.1
            }
    },
    {
            "id": "crimson_reel",
            "name": "Crimson Reel",
            "rarity": "RARE",
            "element": "Ice",
            "role": "Fracture Specialist",
            "tags": [
                    "Summon"
            ],
            "engine": [
                    "Summon"
            ],
            "stats": {
                    "hp": 1236,
                    "atk": 151,
                    "def": 122,
                    "spd": 93
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply fracture."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify fracture and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored fracture."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's fracture handling."
            },
            "lore": "It keeps a tally no ledger could hold.",
            "voice": "\u201cMy pips are your obituary.\u201d",
            "params": {
                    "basic_fracture": 3,
                    "skill_fracture": 4
            }
    },
    {
            "id": "fractal_zenith",
            "name": "Fractal Zenith",
            "rarity": "RARE",
            "element": "Electric",
            "role": "Bleed Specialist",
            "tags": [
                    "Control"
            ],
            "engine": [
                    "Control"
            ],
            "stats": {
                    "hp": 1112,
                    "atk": 133,
                    "def": 100,
                    "spd": 112
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply bleed."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify bleed and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored bleed."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's bleed handling."
            },
            "lore": "Rolled once at the end of the world; it liked the result.",
            "voice": "\u201cThe game ended when I entered it.\u201d",
            "params": {
                    "basic_bleed": 2,
                    "bleed_dmg": 0.15
            }
    },
    {
            "id": "gleaming_tally",
            "name": "Gleaming Tally",
            "rarity": "RARE",
            "element": "Physical",
            "role": "Gravity Specialist",
            "tags": [
                    "Omen",
                    "Fracture"
            ],
            "engine": [
                    "Omen",
                    "Fracture"
            ],
            "stats": {
                    "hp": 1329,
                    "atk": 115,
                    "def": 77,
                    "spd": 101
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply gravity."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify gravity and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored gravity."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's gravity handling."
            },
            "lore": "Fate whittled it down to exactly what it needed to be.",
            "voice": "\u201cSpin. I enjoy the noise.\u201d",
            "params": {
                    "basic_gravity": 1,
                    "spd_up": 0.1
            }
    },
    {
            "id": "ruby_whale",
            "name": "Ruby Whale",
            "rarity": "RARE",
            "element": "Arcane",
            "role": "Energy Specialist",
            "tags": [
                    "Break"
            ],
            "engine": [
                    "Break"
            ],
            "stats": {
                    "hp": 1205,
                    "atk": 146,
                    "def": 116,
                    "spd": 90
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply energy."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify energy and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored energy."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's energy handling."
            },
            "lore": "Some dice remember every hand they ever lost. This one keeps the receipts.",
            "voice": "\u201cAnte up. The table's mine.\u201d",
            "params": {
                    "basic_energy": 4,
                    "skill_energy": 10,
                    "passive_energy": 3
            }
    },
    {
            "id": "eternal_reckoner",
            "name": "Eternal Reckoner",
            "rarity": "RARE",
            "element": "Light",
            "role": "Break Specialist",
            "tags": [
                    "Energy"
            ],
            "engine": [
                    "Energy"
            ],
            "stats": {
                    "hp": 1081,
                    "atk": 128,
                    "def": 94,
                    "spd": 110
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply break."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify break and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored break."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's break handling."
            },
            "lore": "It was carved from a debt no one could pay and rolled ever since.",
            "voice": "\u201cI don't gamble. I collect.\u201d",
            "params": {
                    "basic_fracture": 2,
                    "skill_break": 1,
                    "break_gain": 0.2
            }
    },
    {
            "id": "lunar_payout",
            "name": "Lunar Payout",
            "rarity": "RARE",
            "element": "Dark",
            "role": "Omen Specialist",
            "tags": [
                    "Combo",
                    "Sustain"
            ],
            "engine": [
                    "Combo",
                    "Sustain"
            ],
            "stats": {
                    "hp": 1298,
                    "atk": 160,
                    "def": 72,
                    "spd": 98
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply omen."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify omen and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored omen."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's omen handling."
            },
            "lore": "Fortune is a wheel; this die is the axle it turns on.",
            "voice": "\u201cRoll again. I dare you.\u201d",
            "params": {
                    "basic_omen": 2,
                    "skill_omen": 6
            }
    },
    {
            "id": "sovereign_fortune",
            "name": "Sovereign Fortune",
            "rarity": "RARE",
            "element": "Blood",
            "role": "Chill Specialist",
            "tags": [
                    "Fortune"
            ],
            "engine": [
                    "Fortune"
            ],
            "stats": {
                    "hp": 1174,
                    "atk": 142,
                    "def": 111,
                    "spd": 118
            },
            "basic": {
                    "name": "Open",
                    "desc": "Deal damage and apply chill."
            },
            "skill": {
                    "name": "Raise",
                    "desc": "Amplify chill and strike harder."
            },
            "ult": {
                    "name": "Showdown",
                    "desc": "A heavy blow that spends stored chill."
            },
            "passive": {
                    "name": "Read",
                    "desc": "Improves the team's chill handling."
            },
            "lore": "They say it fell from a table in a room that no longer exists.",
            "voice": "\u201cThe count never lies.\u201d",
            "params": {
                    "basic_chill": 1,
                    "skill_chill_all": 4
            }
    },
    {
            "id": "emerald_reaver",
            "name": "Emerald Reaver",
            "rarity": "LEGENDARY",
            "element": "Poison",
            "role": "Resonance Engine",
            "tags": [
                    "Summon"
            ],
            "engine": [
                    "Summon"
            ],
            "stats": {
                    "hp": 1300,
                    "atk": 156,
                    "def": 108,
                    "spd": 113
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Resonant Core",
                    "desc": "The die builds Resonance; every 3 stacks empower the next hit."
            },
            "lore": "Every pip is a promise, and every promise is a threat.",
            "voice": "\u201cEvens or odds, you still lose.\u201d",
            "params": {
                    "resonance_n": 3,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "voidforged_ante",
            "name": "Voidforged Ante",
            "rarity": "LEGENDARY",
            "element": "Nature",
            "role": "Overload Bruiser",
            "tags": [
                    "Control"
            ],
            "engine": [
                    "Control"
            ],
            "stats": {
                    "hp": 1482,
                    "atk": 175,
                    "def": 80,
                    "spd": 102
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Overload",
                    "desc": "The die surges ATK +40% at the cost of recoil HP."
            },
            "lore": "Cut from cold starlight, it counts outcomes before they happen.",
            "voice": "\u201cWatch the wheel. Watch it break.\u201d",
            "params": {
                    "overload_pct": 0.4,
                    "recoil": 0.1,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "pale_roulette",
            "name": "Pale Roulette",
            "rarity": "LEGENDARY",
            "element": "Wind",
            "role": "Vampiric DPS",
            "tags": [
                    "Omen"
            ],
            "engine": [
                    "Omen"
            ],
            "stats": {
                    "hp": 1378,
                    "atk": 164,
                    "def": 129,
                    "spd": 121
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Bloodpact",
                    "desc": "The die heals for 30% of all damage dealt."
            },
            "lore": "The house forgot it in a drawer. It has been dealing itself in ever since.",
            "voice": "\u201cEvery face is the winning face.\u201d",
            "params": {
                    "lifesteal": 0.3,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "gilded_cipher",
            "name": "Gilded Cipher",
            "rarity": "LEGENDARY",
            "element": "Time",
            "role": "Thorn Guard",
            "tags": [
                    "Fracture"
            ],
            "engine": [
                    "Fracture"
            ],
            "stats": {
                    "hp": 1560,
                    "atk": 153,
                    "def": 101,
                    "spd": 110
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Retaliation",
                    "desc": "The die reflects 25% of damage taken."
            },
            "lore": "Where it lands, probability kneels.",
            "voice": "\u201cLuck? No. Arithmetic.\u201d",
            "params": {
                    "reflect": 0.25,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "tidal_nadir",
            "name": "Tidal Nadir",
            "rarity": "LEGENDARY",
            "element": "Void",
            "role": "Executioner",
            "tags": [
                    "Break"
            ],
            "engine": [
                    "Break"
            ],
            "stats": {
                    "hp": 1456,
                    "atk": 172,
                    "def": 150,
                    "spd": 99
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Final Cut",
                    "desc": "The die executes foes below 30% HP for +60% damage."
            },
            "lore": "A gambler's last breath, pressed into six unforgiving faces.",
            "voice": "\u201cDouble or nothing \u2014 it's always nothing.\u201d",
            "params": {
                    "execute_th": 0.3,
                    "execute_pct": 0.6,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "glacial_handle",
            "name": "Glacial Handle",
            "rarity": "LEGENDARY",
            "element": "Earth",
            "role": "Ramping Carry",
            "tags": [
                    "Energy"
            ],
            "engine": [
                    "Energy"
            ],
            "stats": {
                    "hp": 1352,
                    "atk": 161,
                    "def": 122,
                    "spd": 118
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Snowball",
                    "desc": "The die gains +8% ATK every round."
            },
            "lore": "It does not roll so much as decide.",
            "voice": "\u201cI already know your number.\u201d",
            "params": {
                    "ramp_atk": 0.08,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "burning_handle",
            "name": "Burning Handle",
            "rarity": "LEGENDARY",
            "element": "Fire",
            "role": "Shield Breaker",
            "tags": [
                    "Combo"
            ],
            "engine": [
                    "Combo"
            ],
            "stats": {
                    "hp": 1534,
                    "atk": 150,
                    "def": 94,
                    "spd": 107
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Bulwark Bane",
                    "desc": "The die deals +50% damage to shielded foes."
            },
            "lore": "Born in the space between a bet and its regret.",
            "voice": "\u201cThe pot's called. Pay up.\u201d",
            "params": {
                    "shield_break": 0.5,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "pale_broker",
            "name": "Pale Broker",
            "rarity": "LEGENDARY",
            "element": "Ice",
            "role": "Twin Striker",
            "tags": [
                    "Sustain"
            ],
            "engine": [
                    "Sustain"
            ],
            "stats": {
                    "hp": 1430,
                    "atk": 170,
                    "def": 143,
                    "spd": 96
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Double Deal",
                    "desc": "The die basic attack strikes twice."
            },
            "lore": "The odds bend around it like light around a stone.",
            "voice": "\u201cSix ways to fall, one way to win.\u201d",
            "params": {
                    "twin_hit": 1,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "rigged_diviner",
            "name": "Rigged Diviner",
            "rarity": "LEGENDARY",
            "element": "Electric",
            "role": "ATK Anchor",
            "tags": [
                    "Fortune"
            ],
            "engine": [
                    "Fortune"
            ],
            "stats": {
                    "hp": 1326,
                    "atk": 158,
                    "def": 115,
                    "spd": 116
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "War Aura",
                    "desc": "The die grants the team +15% ATK."
            },
            "lore": "It has never lost. It simply has not finished playing.",
            "voice": "\u201cBet against me. Please.\u201d",
            "params": {
                    "aura_atk": 0.15,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "velvet_ledger",
            "name": "Velvet Ledger",
            "rarity": "LEGENDARY",
            "element": "Physical",
            "role": "DEF Anchor",
            "tags": [
                    "Summon"
            ],
            "engine": [
                    "Summon"
            ],
            "stats": {
                    "hp": 1508,
                    "atk": 178,
                    "def": 87,
                    "spd": 104
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Ward Aura",
                    "desc": "The die grants the team +15% DEF."
            },
            "lore": "A relic of a game whose rules were rewritten mid-throw.",
            "voice": "\u201cThe dealer folds first.\u201d",
            "params": {
                    "aura_def": 0.15,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "fractal_rounder",
            "name": "Fractal Rounder",
            "rarity": "LEGENDARY",
            "element": "Arcane",
            "role": "Decay Warden",
            "tags": [
                    "Control"
            ],
            "engine": [
                    "Control"
            ],
            "stats": {
                    "hp": 1404,
                    "atk": 167,
                    "def": 136,
                    "spd": 124
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Withering",
                    "desc": "The die cuts enemy healing by 40%."
            },
            "lore": "Loaded not with lead, but with certainty.",
            "voice": "\u201cCome closer. Let me read your odds.\u201d",
            "params": {
                    "decay": 0.4,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "golden_dealer",
            "name": "Golden Dealer",
            "rarity": "LEGENDARY",
            "element": "Light",
            "role": "Resonance Engine",
            "tags": [
                    "Omen"
            ],
            "engine": [
                    "Omen"
            ],
            "stats": {
                    "hp": 1300,
                    "atk": 156,
                    "def": 108,
                    "spd": 113
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Resonant Core",
                    "desc": "The die builds Resonance; every 3 stacks empower the next hit."
            },
            "lore": "It hums with the sound of every coin that ever hit the felt.",
            "voice": "\u201cThe wheel remembers your name.\u201d",
            "params": {
                    "resonance_n": 3,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "velvet_croupier",
            "name": "Velvet Croupier",
            "rarity": "LEGENDARY",
            "element": "Dark",
            "role": "Overload Bruiser",
            "tags": [
                    "Fracture"
            ],
            "engine": [
                    "Fracture"
            ],
            "stats": {
                    "hp": 1482,
                    "atk": 175,
                    "def": 80,
                    "spd": 102
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Overload",
                    "desc": "The die surges ATK +40% at the cost of recoil HP."
            },
            "lore": "The dealer who made it never blinked again.",
            "voice": "\u201cAll in. There was never another option.\u201d",
            "params": {
                    "overload_pct": 0.4,
                    "recoil": 0.1,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "obsidian_grifter",
            "name": "Obsidian Grifter",
            "rarity": "LEGENDARY",
            "element": "Blood",
            "role": "Vampiric DPS",
            "tags": [
                    "Break"
            ],
            "engine": [
                    "Break"
            ],
            "stats": {
                    "hp": 1378,
                    "atk": 164,
                    "def": 129,
                    "spd": 121
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Bloodpact",
                    "desc": "The die heals for 30% of all damage dealt."
            },
            "lore": "It keeps a tally no ledger could hold.",
            "voice": "\u201cMy pips are your obituary.\u201d",
            "params": {
                    "lifesteal": 0.3,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "ashen_fold",
            "name": "Ashen Fold",
            "rarity": "LEGENDARY",
            "element": "Poison",
            "role": "Thorn Guard",
            "tags": [
                    "Energy"
            ],
            "engine": [
                    "Energy"
            ],
            "stats": {
                    "hp": 1560,
                    "atk": 153,
                    "def": 101,
                    "spd": 110
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Retaliation",
                    "desc": "The die reflects 25% of damage taken."
            },
            "lore": "Rolled once at the end of the world; it liked the result.",
            "voice": "\u201cThe game ended when I entered it.\u201d",
            "params": {
                    "reflect": 0.25,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "jade_quasar",
            "name": "Jade Quasar",
            "rarity": "LEGENDARY",
            "element": "Nature",
            "role": "Executioner",
            "tags": [
                    "Combo"
            ],
            "engine": [
                    "Combo"
            ],
            "stats": {
                    "hp": 1456,
                    "atk": 172,
                    "def": 150,
                    "spd": 99
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Final Cut",
                    "desc": "The die executes foes below 30% HP for +60% damage."
            },
            "lore": "Fate whittled it down to exactly what it needed to be.",
            "voice": "\u201cSpin. I enjoy the noise.\u201d",
            "params": {
                    "execute_th": 0.3,
                    "execute_pct": 0.6,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "iron_spinner",
            "name": "Iron Spinner",
            "rarity": "LEGENDARY",
            "element": "Wind",
            "role": "Ramping Carry",
            "tags": [
                    "Sustain"
            ],
            "engine": [
                    "Sustain"
            ],
            "stats": {
                    "hp": 1352,
                    "atk": 161,
                    "def": 122,
                    "spd": 118
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Snowball",
                    "desc": "The die gains +8% ATK every round."
            },
            "lore": "Some dice remember every hand they ever lost. This one keeps the receipts.",
            "voice": "\u201cAnte up. The table's mine.\u201d",
            "params": {
                    "ramp_atk": 0.08,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "marked_ante",
            "name": "Marked Ante",
            "rarity": "LEGENDARY",
            "element": "Time",
            "role": "Shield Breaker",
            "tags": [
                    "Fortune"
            ],
            "engine": [
                    "Fortune"
            ],
            "stats": {
                    "hp": 1534,
                    "atk": 150,
                    "def": 94,
                    "spd": 107
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Bulwark Bane",
                    "desc": "The die deals +50% damage to shielded foes."
            },
            "lore": "It was carved from a debt no one could pay and rolled ever since.",
            "voice": "\u201cI don't gamble. I collect.\u201d",
            "params": {
                    "shield_break": 0.5,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "prime_rift",
            "name": "Prime Rift",
            "rarity": "LEGENDARY",
            "element": "Void",
            "role": "Twin Striker",
            "tags": [
                    "Summon"
            ],
            "engine": [
                    "Summon"
            ],
            "stats": {
                    "hp": 1430,
                    "atk": 170,
                    "def": 143,
                    "spd": 96
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Double Deal",
                    "desc": "The die basic attack strikes twice."
            },
            "lore": "Fortune is a wheel; this die is the axle it turns on.",
            "voice": "\u201cRoll again. I dare you.\u201d",
            "params": {
                    "twin_hit": 1,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "verdant_fold",
            "name": "Verdant Fold",
            "rarity": "LEGENDARY",
            "element": "Earth",
            "role": "ATK Anchor",
            "tags": [
                    "Control"
            ],
            "engine": [
                    "Control"
            ],
            "stats": {
                    "hp": 1326,
                    "atk": 158,
                    "def": 115,
                    "spd": 116
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "War Aura",
                    "desc": "The die grants the team +15% ATK."
            },
            "lore": "They say it fell from a table in a room that no longer exists.",
            "voice": "\u201cThe count never lies.\u201d",
            "params": {
                    "aura_atk": 0.15,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "verdant_bluff",
            "name": "Verdant Bluff",
            "rarity": "LEGENDARY",
            "element": "Fire",
            "role": "DEF Anchor",
            "tags": [
                    "Omen"
            ],
            "engine": [
                    "Omen"
            ],
            "stats": {
                    "hp": 1508,
                    "atk": 178,
                    "def": 87,
                    "spd": 104
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Ward Aura",
                    "desc": "The die grants the team +15% DEF."
            },
            "lore": "Every pip is a promise, and every promise is a threat.",
            "voice": "\u201cEvens or odds, you still lose.\u201d",
            "params": {
                    "aura_def": 0.15,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "obsidian_aeon",
            "name": "Obsidian Aeon",
            "rarity": "LEGENDARY",
            "element": "Ice",
            "role": "Decay Warden",
            "tags": [
                    "Fracture"
            ],
            "engine": [
                    "Fracture"
            ],
            "stats": {
                    "hp": 1404,
                    "atk": 167,
                    "def": 136,
                    "spd": 124
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Withering",
                    "desc": "The die cuts enemy healing by 40%."
            },
            "lore": "Cut from cold starlight, it counts outcomes before they happen.",
            "voice": "\u201cWatch the wheel. Watch it break.\u201d",
            "params": {
                    "decay": 0.4,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "charged_aeon",
            "name": "Charged Aeon",
            "rarity": "LEGENDARY",
            "element": "Electric",
            "role": "Resonance Engine",
            "tags": [
                    "Break"
            ],
            "engine": [
                    "Break"
            ],
            "stats": {
                    "hp": 1300,
                    "atk": 156,
                    "def": 108,
                    "spd": 113
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Resonant Core",
                    "desc": "The die builds Resonance; every 3 stacks empower the next hit."
            },
            "lore": "The house forgot it in a drawer. It has been dealing itself in ever since.",
            "voice": "\u201cEvery face is the winning face.\u201d",
            "params": {
                    "resonance_n": 3,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "gleaming_cascade",
            "name": "Gleaming Cascade",
            "rarity": "LEGENDARY",
            "element": "Physical",
            "role": "Overload Bruiser",
            "tags": [
                    "Energy"
            ],
            "engine": [
                    "Energy"
            ],
            "stats": {
                    "hp": 1482,
                    "atk": 175,
                    "def": 80,
                    "spd": 102
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Overload",
                    "desc": "The die surges ATK +40% at the cost of recoil HP."
            },
            "lore": "Where it lands, probability kneels.",
            "voice": "\u201cLuck? No. Arithmetic.\u201d",
            "params": {
                    "overload_pct": 0.4,
                    "recoil": 0.1,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "prime_rake",
            "name": "Prime Rake",
            "rarity": "LEGENDARY",
            "element": "Arcane",
            "role": "Vampiric DPS",
            "tags": [
                    "Combo"
            ],
            "engine": [
                    "Combo"
            ],
            "stats": {
                    "hp": 1378,
                    "atk": 164,
                    "def": 129,
                    "spd": 121
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Bloodpact",
                    "desc": "The die heals for 30% of all damage dealt."
            },
            "lore": "A gambler's last breath, pressed into six unforgiving faces.",
            "voice": "\u201cDouble or nothing \u2014 it's always nothing.\u201d",
            "params": {
                    "lifesteal": 0.3,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "withered_nadir",
            "name": "Withered Nadir",
            "rarity": "LEGENDARY",
            "element": "Light",
            "role": "Thorn Guard",
            "tags": [
                    "Sustain"
            ],
            "engine": [
                    "Sustain"
            ],
            "stats": {
                    "hp": 1560,
                    "atk": 153,
                    "def": 101,
                    "spd": 110
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Retaliation",
                    "desc": "The die reflects 25% of damage taken."
            },
            "lore": "It does not roll so much as decide.",
            "voice": "\u201cI already know your number.\u201d",
            "params": {
                    "reflect": 0.25,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "glacial_broker",
            "name": "Glacial Broker",
            "rarity": "LEGENDARY",
            "element": "Dark",
            "role": "Executioner",
            "tags": [
                    "Fortune"
            ],
            "engine": [
                    "Fortune"
            ],
            "stats": {
                    "hp": 1456,
                    "atk": 172,
                    "def": 150,
                    "spd": 99
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Final Cut",
                    "desc": "The die executes foes below 30% HP for +60% damage."
            },
            "lore": "Born in the space between a bet and its regret.",
            "voice": "\u201cThe pot's called. Pay up.\u201d",
            "params": {
                    "execute_th": 0.3,
                    "execute_pct": 0.6,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "phantom_cutter",
            "name": "Phantom Cutter",
            "rarity": "LEGENDARY",
            "element": "Blood",
            "role": "Ramping Carry",
            "tags": [
                    "Summon"
            ],
            "engine": [
                    "Summon"
            ],
            "stats": {
                    "hp": 1352,
                    "atk": 161,
                    "def": 122,
                    "spd": 118
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Snowball",
                    "desc": "The die gains +8% ATK every round."
            },
            "lore": "The odds bend around it like light around a stone.",
            "voice": "\u201cSix ways to fall, one way to win.\u201d",
            "params": {
                    "ramp_atk": 0.08,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "grave_reaver",
            "name": "Grave Reaver",
            "rarity": "LEGENDARY",
            "element": "Poison",
            "role": "Shield Breaker",
            "tags": [
                    "Control"
            ],
            "engine": [
                    "Control"
            ],
            "stats": {
                    "hp": 1534,
                    "atk": 150,
                    "def": 94,
                    "spd": 107
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Bulwark Bane",
                    "desc": "The die deals +50% damage to shielded foes."
            },
            "lore": "It has never lost. It simply has not finished playing.",
            "voice": "\u201cBet against me. Please.\u201d",
            "params": {
                    "shield_break": 0.5,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "charged_broker",
            "name": "Charged Broker",
            "rarity": "LEGENDARY",
            "element": "Nature",
            "role": "Twin Striker",
            "tags": [
                    "Omen"
            ],
            "engine": [
                    "Omen"
            ],
            "stats": {
                    "hp": 1430,
                    "atk": 170,
                    "def": 143,
                    "spd": 96
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Double Deal",
                    "desc": "The die basic attack strikes twice."
            },
            "lore": "A relic of a game whose rules were rewritten mid-throw.",
            "voice": "\u201cThe dealer folds first.\u201d",
            "params": {
                    "twin_hit": 1,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "broken_chance",
            "name": "Broken Chance",
            "rarity": "LEGENDARY",
            "element": "Wind",
            "role": "ATK Anchor",
            "tags": [
                    "Fracture"
            ],
            "engine": [
                    "Fracture"
            ],
            "stats": {
                    "hp": 1326,
                    "atk": 158,
                    "def": 115,
                    "spd": 116
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "War Aura",
                    "desc": "The die grants the team +15% ATK."
            },
            "lore": "Loaded not with lead, but with certainty.",
            "voice": "\u201cCome closer. Let me read your odds.\u201d",
            "params": {
                    "aura_atk": 0.15,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "iron_grifter",
            "name": "Iron Grifter",
            "rarity": "LEGENDARY",
            "element": "Time",
            "role": "DEF Anchor",
            "tags": [
                    "Break"
            ],
            "engine": [
                    "Break"
            ],
            "stats": {
                    "hp": 1508,
                    "atk": 178,
                    "def": 87,
                    "spd": 104
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Ward Aura",
                    "desc": "The die grants the team +15% DEF."
            },
            "lore": "It hums with the sound of every coin that ever hit the felt.",
            "voice": "\u201cThe wheel remembers your name.\u201d",
            "params": {
                    "aura_def": 0.15,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "burning_reel",
            "name": "Burning Reel",
            "rarity": "LEGENDARY",
            "element": "Void",
            "role": "Decay Warden",
            "tags": [
                    "Energy"
            ],
            "engine": [
                    "Energy"
            ],
            "stats": {
                    "hp": 1404,
                    "atk": 167,
                    "def": 136,
                    "spd": 124
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Withering",
                    "desc": "The die cuts enemy healing by 40%."
            },
            "lore": "The dealer who made it never blinked again.",
            "voice": "\u201cAll in. There was never another option.\u201d",
            "params": {
                    "decay": 0.4,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "glacial_pot",
            "name": "Glacial Pot",
            "rarity": "LEGENDARY",
            "element": "Earth",
            "role": "Resonance Engine",
            "tags": [
                    "Combo"
            ],
            "engine": [
                    "Combo"
            ],
            "stats": {
                    "hp": 1300,
                    "atk": 156,
                    "def": 108,
                    "spd": 113
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Resonant Core",
                    "desc": "The die builds Resonance; every 3 stacks empower the next hit."
            },
            "lore": "It keeps a tally no ledger could hold.",
            "voice": "\u201cMy pips are your obituary.\u201d",
            "params": {
                    "resonance_n": 3,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "wild_mark",
            "name": "Wild Mark",
            "rarity": "LEGENDARY",
            "element": "Fire",
            "role": "Overload Bruiser",
            "tags": [
                    "Sustain"
            ],
            "engine": [
                    "Sustain"
            ],
            "stats": {
                    "hp": 1482,
                    "atk": 175,
                    "def": 80,
                    "spd": 102
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Overload",
                    "desc": "The die surges ATK +40% at the cost of recoil HP."
            },
            "lore": "Rolled once at the end of the world; it liked the result.",
            "voice": "\u201cThe game ended when I entered it.\u201d",
            "params": {
                    "overload_pct": 0.4,
                    "recoil": 0.1,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "frostbound_shill",
            "name": "Frostbound Shill",
            "rarity": "LEGENDARY",
            "element": "Ice",
            "role": "Vampiric DPS",
            "tags": [
                    "Fortune"
            ],
            "engine": [
                    "Fortune"
            ],
            "stats": {
                    "hp": 1378,
                    "atk": 164,
                    "def": 129,
                    "spd": 121
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Bloodpact",
                    "desc": "The die heals for 30% of all damage dealt."
            },
            "lore": "Fate whittled it down to exactly what it needed to be.",
            "voice": "\u201cSpin. I enjoy the noise.\u201d",
            "params": {
                    "lifesteal": 0.3,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "sanguine_dealer",
            "name": "Sanguine Dealer",
            "rarity": "LEGENDARY",
            "element": "Electric",
            "role": "Thorn Guard",
            "tags": [
                    "Summon"
            ],
            "engine": [
                    "Summon"
            ],
            "stats": {
                    "hp": 1560,
                    "atk": 153,
                    "def": 101,
                    "spd": 110
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Retaliation",
                    "desc": "The die reflects 25% of damage taken."
            },
            "lore": "Some dice remember every hand they ever lost. This one keeps the receipts.",
            "voice": "\u201cAnte up. The table's mine.\u201d",
            "params": {
                    "reflect": 0.25,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "solar_odds",
            "name": "Solar Odds",
            "rarity": "LEGENDARY",
            "element": "Physical",
            "role": "Executioner",
            "tags": [
                    "Control"
            ],
            "engine": [
                    "Control"
            ],
            "stats": {
                    "hp": 1456,
                    "atk": 172,
                    "def": 150,
                    "spd": 99
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Final Cut",
                    "desc": "The die executes foes below 30% HP for +60% damage."
            },
            "lore": "It was carved from a debt no one could pay and rolled ever since.",
            "voice": "\u201cI don't gamble. I collect.\u201d",
            "params": {
                    "execute_th": 0.3,
                    "execute_pct": 0.6,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "shrouded_rake",
            "name": "Shrouded Rake",
            "rarity": "LEGENDARY",
            "element": "Arcane",
            "role": "Ramping Carry",
            "tags": [
                    "Omen"
            ],
            "engine": [
                    "Omen"
            ],
            "stats": {
                    "hp": 1352,
                    "atk": 161,
                    "def": 122,
                    "spd": 118
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Snowball",
                    "desc": "The die gains +8% ATK every round."
            },
            "lore": "Fortune is a wheel; this die is the axle it turns on.",
            "voice": "\u201cRoll again. I dare you.\u201d",
            "params": {
                    "ramp_atk": 0.08,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "grim_cutter",
            "name": "Grim Cutter",
            "rarity": "LEGENDARY",
            "element": "Light",
            "role": "Shield Breaker",
            "tags": [
                    "Fracture"
            ],
            "engine": [
                    "Fracture"
            ],
            "stats": {
                    "hp": 1534,
                    "atk": 150,
                    "def": 94,
                    "spd": 107
            },
            "basic": {
                    "name": "Ignite",
                    "desc": "A strong strike that feeds the signature engine."
            },
            "skill": {
                    "name": "Escalate",
                    "desc": "Empower the die and unleash its mechanic."
            },
            "ult": {
                    "name": "Overrule",
                    "desc": "A devastating blow amplified by the signature effect."
            },
            "passive": {
                    "name": "Bulwark Bane",
                    "desc": "The die deals +50% damage to shielded foes."
            },
            "lore": "They say it fell from a table in a room that no longer exists.",
            "voice": "\u201cThe count never lies.\u201d",
            "params": {
                    "shield_break": 0.5,
                    "skill_energy": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Signature effect triggers 10% stronger."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.1
                            },
                            "desc": "+10% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill costs 1 less energy to fuel."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "def_pct": 0.12
                            },
                            "desc": "+12% DEF."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate applies the signature effect to all foes."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 12
                            },
                            "desc": "+12 SPD and the passive doubles at low HP."
                    }
            ]
    },
    {
            "id": "blessed_payout",
            "name": "Blessed Payout",
            "rarity": "MYTHIC",
            "element": "Dark",
            "role": "Omen Weaver",
            "tags": [
                    "Omen"
            ],
            "engine": [
                    "Omen"
            ],
            "stats": {
                    "hp": 1415,
                    "atk": 168,
                    "def": 90,
                    "spd": 95
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Omen power."
            },
            "passive": {
                    "name": "Omen Weaver",
                    "desc": "The die spreads and detonates Omen across the field."
            },
            "lore": "Every pip is a promise, and every promise is a threat.",
            "voice": "\u201cEvens or odds, you still lose.\u201d",
            "params": {
                    "basic_omen": 2,
                    "skill_omen_all": 8,
                    "ult_omen_triggers": 2
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "jade_whale",
            "name": "Jade Whale",
            "rarity": "MYTHIC",
            "element": "Blood",
            "role": "Fault Master",
            "tags": [
                    "Fracture"
            ],
            "engine": [
                    "Fracture"
            ],
            "stats": {
                    "hp": 1275,
                    "atk": 152,
                    "def": 76,
                    "spd": 107
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Fracture power."
            },
            "passive": {
                    "name": "Fault Master",
                    "desc": "The die stacks Fracture on every foe."
            },
            "lore": "Cut from cold starlight, it counts outcomes before they happen.",
            "voice": "\u201cWatch the wheel. Watch it break.\u201d",
            "params": {
                    "basic_fracture": 3,
                    "skill_fracture_all": 5,
                    "ult_fracture_tick": 3
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "vivid_stake",
            "name": "Vivid Stake",
            "rarity": "MYTHIC",
            "element": "Poison",
            "role": "Siege Doctrine",
            "tags": [
                    "Break"
            ],
            "engine": [
                    "Break"
            ],
            "stats": {
                    "hp": 1520,
                    "atk": 180,
                    "def": 62,
                    "spd": 100
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Break power."
            },
            "passive": {
                    "name": "Siege Doctrine",
                    "desc": "The die tears through toughness and punishes Broken foes."
            },
            "lore": "The house forgot it in a drawer. It has been dealing itself in ever since.",
            "voice": "\u201cEvery face is the winning face.\u201d",
            "params": {
                    "skill_break": 2,
                    "broken_bonus": 0.5,
                    "break_gain": 0.25
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "radiant_cutter",
            "name": "Radiant Cutter",
            "rarity": "MYTHIC",
            "element": "Nature",
            "role": "Power Nexus",
            "tags": [
                    "Energy"
            ],
            "engine": [
                    "Energy"
            ],
            "stats": {
                    "hp": 1380,
                    "atk": 164,
                    "def": 87,
                    "spd": 112
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Energy power."
            },
            "passive": {
                    "name": "Power Nexus",
                    "desc": "The die floods the team with energy and damage."
            },
            "lore": "Where it lands, probability kneels.",
            "voice": "\u201cLuck? No. Arithmetic.\u201d",
            "params": {
                    "skill_energy": 14,
                    "passive_energy": 4,
                    "team_dmg": 0.12
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "ashen_reckoner",
            "name": "Ashen Reckoner",
            "rarity": "MYTHIC",
            "element": "Wind",
            "role": "Deep Cold",
            "tags": [
                    "Control"
            ],
            "engine": [
                    "Control"
            ],
            "stats": {
                    "hp": 1240,
                    "atk": 148,
                    "def": 72,
                    "spd": 105
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Control power."
            },
            "passive": {
                    "name": "Deep Cold",
                    "desc": "The die freezes the field solid."
            },
            "lore": "A gambler's last breath, pressed into six unforgiving faces.",
            "voice": "\u201cDouble or nothing \u2014 it's always nothing.\u201d",
            "params": {
                    "basic_chill": 2,
                    "skill_chill_all": 6,
                    "freeze_at": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "glacial_reaver",
            "name": "Glacial Reaver",
            "rarity": "MYTHIC",
            "element": "Time",
            "role": "Aegis Heart",
            "tags": [
                    "Sustain"
            ],
            "engine": [
                    "Sustain"
            ],
            "stats": {
                    "hp": 1485,
                    "atk": 176,
                    "def": 58,
                    "spd": 98
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Sustain power."
            },
            "passive": {
                    "name": "Aegis Heart",
                    "desc": "The die shields and drains life for the team."
            },
            "lore": "It does not roll so much as decide.",
            "voice": "\u201cI already know your number.\u201d",
            "params": {
                    "skill_shield": 0.24,
                    "shield_pct": 0.2,
                    "lifesteal": 0.25
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "weighted_reel",
            "name": "Weighted Reel",
            "rarity": "MYTHIC",
            "element": "Void",
            "role": "Loaded Fate",
            "tags": [
                    "Fortune"
            ],
            "engine": [
                    "Fortune"
            ],
            "stats": {
                    "hp": 1345,
                    "atk": 160,
                    "def": 83,
                    "spd": 110
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Fortune power."
            },
            "passive": {
                    "name": "Loaded Fate",
                    "desc": "The die rigs the rolls in the team's favor."
            },
            "lore": "Born in the space between a bet and its regret.",
            "voice": "\u201cThe pot's called. Pay up.\u201d",
            "params": {
                    "team_fortune": 2,
                    "give_energy": 10,
                    "crit_up": 0.12
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "pale_rake",
            "name": "Pale Rake",
            "rarity": "MYTHIC",
            "element": "Earth",
            "role": "Standing Host",
            "tags": [
                    "Summon"
            ],
            "engine": [
                    "Summon"
            ],
            "stats": {
                    "hp": 1590,
                    "atk": 144,
                    "def": 69,
                    "spd": 104
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Summon power."
            },
            "passive": {
                    "name": "Standing Host",
                    "desc": "The die commands summoned dice."
            },
            "lore": "The odds bend around it like light around a stone.",
            "voice": "\u201cSix ways to fall, one way to win.\u201d",
            "params": {
                    "summon_basic": 1,
                    "summon_max": 2,
                    "summon_pct": 0.3
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "fated_mark",
            "name": "Fated Mark",
            "rarity": "MYTHIC",
            "element": "Fire",
            "role": "Chain Reaction",
            "tags": [
                    "Combo"
            ],
            "engine": [
                    "Combo"
            ],
            "stats": {
                    "hp": 1450,
                    "atk": 172,
                    "def": 94,
                    "spd": 97
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Combo power."
            },
            "passive": {
                    "name": "Chain Reaction",
                    "desc": "The die builds and detonates Combo."
            },
            "lore": "It has never lost. It simply has not finished playing.",
            "voice": "\u201cBet against me. Please.\u201d",
            "params": {
                    "basic_combo": 2,
                    "combo_burst": 0.4,
                    "twin_hit": 1
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "loaded_trickster",
            "name": "Loaded Trickster",
            "rarity": "MYTHIC",
            "element": "Ice",
            "role": "Heavy Verdict",
            "tags": [
                    "Control"
            ],
            "engine": [
                    "Control"
            ],
            "stats": {
                    "hp": 1310,
                    "atk": 156,
                    "def": 80,
                    "spd": 109
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Control power."
            },
            "passive": {
                    "name": "Heavy Verdict",
                    "desc": "The die crushes foes under Gravity."
            },
            "lore": "A relic of a game whose rules were rewritten mid-throw.",
            "voice": "\u201cThe dealer folds first.\u201d",
            "params": {
                    "basic_gravity": 2,
                    "skill_gravity_all": 4,
                    "weighed_at": 5
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "endless_chance",
            "name": "Endless Chance",
            "rarity": "MYTHIC",
            "element": "Electric",
            "role": "Doomcaller",
            "tags": [
                    "Omen"
            ],
            "engine": [
                    "Omen"
            ],
            "stats": {
                    "hp": 1555,
                    "atk": 140,
                    "def": 65,
                    "spd": 102
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Omen power."
            },
            "passive": {
                    "name": "Doomcaller",
                    "desc": "The die marks the doomed and executes them."
            },
            "lore": "Loaded not with lead, but with certainty.",
            "voice": "\u201cCome closer. Let me read your odds.\u201d",
            "params": {
                    "basic_omen": 3,
                    "omen_amp": 0.25,
                    "execute_th": 0.3,
                    "execute_pct": 0.5
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "golden_mark",
            "name": "Golden Mark",
            "rarity": "MYTHIC",
            "element": "Physical",
            "role": "Omen Weaver",
            "tags": [
                    "Omen"
            ],
            "engine": [
                    "Omen"
            ],
            "stats": {
                    "hp": 1415,
                    "atk": 168,
                    "def": 90,
                    "spd": 95
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Omen power."
            },
            "passive": {
                    "name": "Omen Weaver",
                    "desc": "The die spreads and detonates Omen across the field."
            },
            "lore": "It hums with the sound of every coin that ever hit the felt.",
            "voice": "\u201cThe wheel remembers your name.\u201d",
            "params": {
                    "basic_omen": 2,
                    "skill_omen_all": 8,
                    "ult_omen_triggers": 2
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "obsidian_herald",
            "name": "Obsidian Herald",
            "rarity": "MYTHIC",
            "element": "Arcane",
            "role": "Fault Master",
            "tags": [
                    "Fracture"
            ],
            "engine": [
                    "Fracture"
            ],
            "stats": {
                    "hp": 1275,
                    "atk": 152,
                    "def": 76,
                    "spd": 107
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Fracture power."
            },
            "passive": {
                    "name": "Fault Master",
                    "desc": "The die stacks Fracture on every foe."
            },
            "lore": "The dealer who made it never blinked again.",
            "voice": "\u201cAll in. There was never another option.\u201d",
            "params": {
                    "basic_fracture": 3,
                    "skill_fracture_all": 5,
                    "ult_fracture_tick": 3
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "ivory_vortex",
            "name": "Ivory Vortex",
            "rarity": "MYTHIC",
            "element": "Light",
            "role": "Siege Doctrine",
            "tags": [
                    "Break"
            ],
            "engine": [
                    "Break"
            ],
            "stats": {
                    "hp": 1520,
                    "atk": 180,
                    "def": 62,
                    "spd": 100
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Break power."
            },
            "passive": {
                    "name": "Siege Doctrine",
                    "desc": "The die tears through toughness and punishes Broken foes."
            },
            "lore": "It keeps a tally no ledger could hold.",
            "voice": "\u201cMy pips are your obituary.\u201d",
            "params": {
                    "skill_break": 2,
                    "broken_bonus": 0.5,
                    "break_gain": 0.25
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "blessed_quasar",
            "name": "Blessed Quasar",
            "rarity": "MYTHIC",
            "element": "Dark",
            "role": "Power Nexus",
            "tags": [
                    "Energy"
            ],
            "engine": [
                    "Energy"
            ],
            "stats": {
                    "hp": 1380,
                    "atk": 164,
                    "def": 87,
                    "spd": 112
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Energy power."
            },
            "passive": {
                    "name": "Power Nexus",
                    "desc": "The die floods the team with energy and damage."
            },
            "lore": "Rolled once at the end of the world; it liked the result.",
            "voice": "\u201cThe game ended when I entered it.\u201d",
            "params": {
                    "skill_energy": 14,
                    "passive_energy": 4,
                    "team_dmg": 0.12
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "fated_quasar",
            "name": "Fated Quasar",
            "rarity": "MYTHIC",
            "element": "Blood",
            "role": "Deep Cold",
            "tags": [
                    "Control"
            ],
            "engine": [
                    "Control"
            ],
            "stats": {
                    "hp": 1240,
                    "atk": 148,
                    "def": 72,
                    "spd": 105
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Control power."
            },
            "passive": {
                    "name": "Deep Cold",
                    "desc": "The die freezes the field solid."
            },
            "lore": "Fate whittled it down to exactly what it needed to be.",
            "voice": "\u201cSpin. I enjoy the noise.\u201d",
            "params": {
                    "basic_chill": 2,
                    "skill_chill_all": 6,
                    "freeze_at": 10
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "cobalt_croupier",
            "name": "Cobalt Croupier",
            "rarity": "MYTHIC",
            "element": "Poison",
            "role": "Aegis Heart",
            "tags": [
                    "Sustain"
            ],
            "engine": [
                    "Sustain"
            ],
            "stats": {
                    "hp": 1485,
                    "atk": 176,
                    "def": 58,
                    "spd": 98
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Sustain power."
            },
            "passive": {
                    "name": "Aegis Heart",
                    "desc": "The die shields and drains life for the team."
            },
            "lore": "Some dice remember every hand they ever lost. This one keeps the receipts.",
            "voice": "\u201cAnte up. The table's mine.\u201d",
            "params": {
                    "skill_shield": 0.24,
                    "shield_pct": 0.2,
                    "lifesteal": 0.25
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "static_fold",
            "name": "Static Fold",
            "rarity": "MYTHIC",
            "element": "Nature",
            "role": "Loaded Fate",
            "tags": [
                    "Fortune"
            ],
            "engine": [
                    "Fortune"
            ],
            "stats": {
                    "hp": 1345,
                    "atk": 160,
                    "def": 83,
                    "spd": 110
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Fortune power."
            },
            "passive": {
                    "name": "Loaded Fate",
                    "desc": "The die rigs the rolls in the team's favor."
            },
            "lore": "It was carved from a debt no one could pay and rolled ever since.",
            "voice": "\u201cI don't gamble. I collect.\u201d",
            "params": {
                    "team_fortune": 2,
                    "give_energy": 10,
                    "crit_up": 0.12
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "phantom_nadir",
            "name": "Phantom Nadir",
            "rarity": "MYTHIC",
            "element": "Wind",
            "role": "Standing Host",
            "tags": [
                    "Summon"
            ],
            "engine": [
                    "Summon"
            ],
            "stats": {
                    "hp": 1590,
                    "atk": 144,
                    "def": 69,
                    "spd": 104
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Summon power."
            },
            "passive": {
                    "name": "Standing Host",
                    "desc": "The die commands summoned dice."
            },
            "lore": "Fortune is a wheel; this die is the axle it turns on.",
            "voice": "\u201cRoll again. I dare you.\u201d",
            "params": {
                    "summon_basic": 1,
                    "summon_max": 2,
                    "summon_pct": 0.3
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "twisted_tally",
            "name": "Twisted Tally",
            "rarity": "MYTHIC",
            "element": "Time",
            "role": "Chain Reaction",
            "tags": [
                    "Combo"
            ],
            "engine": [
                    "Combo"
            ],
            "stats": {
                    "hp": 1450,
                    "atk": 172,
                    "def": 94,
                    "spd": 97
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Combo power."
            },
            "passive": {
                    "name": "Chain Reaction",
                    "desc": "The die builds and detonates Combo."
            },
            "lore": "They say it fell from a table in a room that no longer exists.",
            "voice": "\u201cThe count never lies.\u201d",
            "params": {
                    "basic_combo": 2,
                    "combo_burst": 0.4,
                    "twin_hit": 1
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "gleaming_eclipse",
            "name": "Gleaming Eclipse",
            "rarity": "MYTHIC",
            "element": "Void",
            "role": "Heavy Verdict",
            "tags": [
                    "Control"
            ],
            "engine": [
                    "Control"
            ],
            "stats": {
                    "hp": 1310,
                    "atk": 156,
                    "def": 80,
                    "spd": 109
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Control power."
            },
            "passive": {
                    "name": "Heavy Verdict",
                    "desc": "The die crushes foes under Gravity."
            },
            "lore": "Every pip is a promise, and every promise is a threat.",
            "voice": "\u201cEvens or odds, you still lose.\u201d",
            "params": {
                    "basic_gravity": 2,
                    "skill_gravity_all": 4,
                    "weighed_at": 5
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "ivory_warden",
            "name": "Ivory Warden",
            "rarity": "MYTHIC",
            "element": "Earth",
            "role": "Doomcaller",
            "tags": [
                    "Omen"
            ],
            "engine": [
                    "Omen"
            ],
            "stats": {
                    "hp": 1555,
                    "atk": 140,
                    "def": 65,
                    "spd": 102
            },
            "basic": {
                    "name": "Prelude",
                    "desc": "A precise strike that primes the engine."
            },
            "skill": {
                    "name": "Crescendo",
                    "desc": "Unleash the die's signature control."
            },
            "ult": {
                    "name": "Finale",
                    "desc": "A field-wide catastrophe of Omen power."
            },
            "passive": {
                    "name": "Doomcaller",
                    "desc": "The die marks the doomed and executes them."
            },
            "lore": "Cut from cold starlight, it counts outcomes before they happen.",
            "voice": "\u201cWatch the wheel. Watch it break.\u201d",
            "params": {
                    "basic_omen": 3,
                    "omen_amp": 0.25,
                    "execute_th": 0.3,
                    "execute_pct": 0.5
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "Battle-start bonus: the signature engine begins primed."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.12
                            },
                            "desc": "+12% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "Skill affects an additional target."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.15
                            },
                            "desc": "+15% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Ultimate cooldown and cost reduced."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 14
                            },
                            "desc": "+14 SPD; the passive gains a second trigger."
                    }
            ]
    },
    {
            "id": "prime_tempest",
            "name": "Prime Tempest",
            "rarity": "ETERNAL",
            "element": "Fire",
            "role": "Godhand",
            "tags": [
                    "Fortune",
                    "Sustain"
            ],
            "engine": [
                    "Fortune",
                    "Sustain"
            ],
            "stats": {
                    "hp": 1750,
                    "atk": 199,
                    "def": 106,
                    "spd": 109
            },
            "basic": {
                    "name": "First Law",
                    "desc": "A cosmic strike channeling every signature effect."
            },
            "skill": {
                    "name": "Second Law",
                    "desc": "Reshape the battlefield with combined mechanics."
            },
            "ult": {
                    "name": "Final Law",
                    "desc": "An extinction-level burst that fuses all signature powers."
            },
            "passive": {
                    "name": "Godhand",
                    "desc": "The die radiates an ATK aura, drains life, and executes the weak."
            },
            "lore": "The house forgot it in a drawer. It has been dealing itself in ever since.",
            "voice": "\u201cEvery face is the winning face.\u201d",
            "params": {
                    "aura_atk": 0.2,
                    "lifesteal": 0.35,
                    "execute_th": 0.35,
                    "execute_pct": 0.7
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "All signature mechanics begin the battle pre-charged."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.15
                            },
                            "desc": "+15% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "The ultimate hits every enemy an extra time."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.18
                            },
                            "desc": "+18% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Signature auras and effects are 25% stronger."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 16
                            },
                            "desc": "+16 SPD; the die revives once at 50% HP."
                    }
            ]
    },
    {
            "id": "grave_reel",
            "name": "Grave Reel",
            "rarity": "ETERNAL",
            "element": "Ice",
            "role": "Ascendant Fury",
            "tags": [
                    "Break",
                    "Combo"
            ],
            "engine": [
                    "Break",
                    "Combo"
            ],
            "stats": {
                    "hp": 1678,
                    "atk": 192,
                    "def": 99,
                    "spd": 120
            },
            "basic": {
                    "name": "First Law",
                    "desc": "A cosmic strike channeling every signature effect."
            },
            "skill": {
                    "name": "Second Law",
                    "desc": "Reshape the battlefield with combined mechanics."
            },
            "ult": {
                    "name": "Final Law",
                    "desc": "An extinction-level burst that fuses all signature powers."
            },
            "passive": {
                    "name": "Ascendant Fury",
                    "desc": "The die overloads, ramps, and strikes twice."
            },
            "lore": "Where it lands, probability kneels.",
            "voice": "\u201cLuck? No. Arithmetic.\u201d",
            "params": {
                    "overload_pct": 0.5,
                    "ramp_atk": 0.1,
                    "twin_hit": 1
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "All signature mechanics begin the battle pre-charged."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.15
                            },
                            "desc": "+15% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "The ultimate hits every enemy an extra time."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.18
                            },
                            "desc": "+18% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Signature auras and effects are 25% stronger."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 16
                            },
                            "desc": "+16 SPD; the die revives once at 50% HP."
                    }
            ]
    },
    {
            "id": "sovereign_dealer",
            "name": "Sovereign Dealer",
            "rarity": "ETERNAL",
            "element": "Electric",
            "role": "Absolute Ward",
            "tags": [
                    "Control",
                    "Sustain"
            ],
            "engine": [
                    "Control",
                    "Sustain"
            ],
            "stats": {
                    "hp": 1804,
                    "atk": 205,
                    "def": 92,
                    "spd": 114
            },
            "basic": {
                    "name": "First Law",
                    "desc": "A cosmic strike channeling every signature effect."
            },
            "skill": {
                    "name": "Second Law",
                    "desc": "Reshape the battlefield with combined mechanics."
            },
            "ult": {
                    "name": "Final Law",
                    "desc": "An extinction-level burst that fuses all signature powers."
            },
            "passive": {
                    "name": "Absolute Ward",
                    "desc": "The die reflects, shields the team, and rots enemy healing."
            },
            "lore": "A gambler's last breath, pressed into six unforgiving faces.",
            "voice": "\u201cDouble or nothing \u2014 it's always nothing.\u201d",
            "params": {
                    "reflect": 0.35,
                    "aura_def": 0.2,
                    "decay": 0.5
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "All signature mechanics begin the battle pre-charged."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.15
                            },
                            "desc": "+15% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "The ultimate hits every enemy an extra time."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.18
                            },
                            "desc": "+18% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Signature auras and effects are 25% stronger."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 16
                            },
                            "desc": "+16 SPD; the die revives once at 50% HP."
                    }
            ]
    },
    {
            "id": "rigged_chance",
            "name": "Rigged Chance",
            "rarity": "ETERNAL",
            "element": "Physical",
            "role": "Perfect Cadence",
            "tags": [
                    "Combo",
                    "Fracture"
            ],
            "engine": [
                    "Combo",
                    "Fracture"
            ],
            "stats": {
                    "hp": 1732,
                    "atk": 197,
                    "def": 104,
                    "spd": 125
            },
            "basic": {
                    "name": "First Law",
                    "desc": "A cosmic strike channeling every signature effect."
            },
            "skill": {
                    "name": "Second Law",
                    "desc": "Reshape the battlefield with combined mechanics."
            },
            "ult": {
                    "name": "Final Law",
                    "desc": "An extinction-level burst that fuses all signature powers."
            },
            "passive": {
                    "name": "Perfect Cadence",
                    "desc": "The die resonates, shatters shields, and ramps endlessly."
            },
            "lore": "It does not roll so much as decide.",
            "voice": "\u201cI already know your number.\u201d",
            "params": {
                    "resonance_n": 2,
                    "shield_break": 0.7,
                    "ramp_atk": 0.08
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "All signature mechanics begin the battle pre-charged."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.15
                            },
                            "desc": "+15% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "The ultimate hits every enemy an extra time."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.18
                            },
                            "desc": "+18% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Signature auras and effects are 25% stronger."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 16
                            },
                            "desc": "+16 SPD; the die revives once at 50% HP."
                    }
            ]
    },
    {
            "id": "sable_trickster",
            "name": "Sable Trickster",
            "rarity": "ETERNAL",
            "element": "Arcane",
            "role": "Reaper Sovereign",
            "tags": [
                    "Omen",
                    "Sustain"
            ],
            "engine": [
                    "Omen",
                    "Sustain"
            ],
            "stats": {
                    "hp": 1660,
                    "atk": 190,
                    "def": 97,
                    "spd": 119
            },
            "basic": {
                    "name": "First Law",
                    "desc": "A cosmic strike channeling every signature effect."
            },
            "skill": {
                    "name": "Second Law",
                    "desc": "Reshape the battlefield with combined mechanics."
            },
            "ult": {
                    "name": "Final Law",
                    "desc": "An extinction-level burst that fuses all signature powers."
            },
            "passive": {
                    "name": "Reaper Sovereign",
                    "desc": "The die an executing, life-draining warlord aura."
            },
            "lore": "Born in the space between a bet and its regret.",
            "voice": "\u201cThe pot's called. Pay up.\u201d",
            "params": {
                    "execute_th": 0.4,
                    "execute_pct": 0.8,
                    "lifesteal": 0.4,
                    "aura_atk": 0.18
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "All signature mechanics begin the battle pre-charged."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.15
                            },
                            "desc": "+15% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "The ultimate hits every enemy an extra time."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.18
                            },
                            "desc": "+18% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Signature auras and effects are 25% stronger."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 16
                            },
                            "desc": "+16 SPD; the die revives once at 50% HP."
                    }
            ]
    },
    {
            "id": "gilded_whale",
            "name": "Gilded Whale",
            "rarity": "ETERNAL",
            "element": "Light",
            "role": "Iron Apocalypse",
            "tags": [
                    "Break",
                    "Control"
            ],
            "engine": [
                    "Break",
                    "Control"
            ],
            "stats": {
                    "hp": 1786,
                    "atk": 203,
                    "def": 90,
                    "spd": 112
            },
            "basic": {
                    "name": "First Law",
                    "desc": "A cosmic strike channeling every signature effect."
            },
            "skill": {
                    "name": "Second Law",
                    "desc": "Reshape the battlefield with combined mechanics."
            },
            "ult": {
                    "name": "Final Law",
                    "desc": "An extinction-level burst that fuses all signature powers."
            },
            "passive": {
                    "name": "Iron Apocalypse",
                    "desc": "The die overloads while reflecting and suppressing healing."
            },
            "lore": "The odds bend around it like light around a stone.",
            "voice": "\u201cSix ways to fall, one way to win.\u201d",
            "params": {
                    "overload_pct": 0.45,
                    "reflect": 0.3,
                    "aura_def": 0.18,
                    "decay": 0.4
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "All signature mechanics begin the battle pre-charged."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.15
                            },
                            "desc": "+15% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "The ultimate hits every enemy an extra time."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.18
                            },
                            "desc": "+18% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Signature auras and effects are 25% stronger."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 16
                            },
                            "desc": "+16 SPD; the die revives once at 50% HP."
                    }
            ]
    },
    {
            "id": "doomed_warden",
            "name": "Doomed Warden",
            "rarity": "ETERNAL",
            "element": "Dark",
            "role": "Cascading Star",
            "tags": [
                    "Combo",
                    "Fortune"
            ],
            "engine": [
                    "Combo",
                    "Fortune"
            ],
            "stats": {
                    "hp": 1714,
                    "atk": 196,
                    "def": 103,
                    "spd": 123
            },
            "basic": {
                    "name": "First Law",
                    "desc": "A cosmic strike channeling every signature effect."
            },
            "skill": {
                    "name": "Second Law",
                    "desc": "Reshape the battlefield with combined mechanics."
            },
            "ult": {
                    "name": "Final Law",
                    "desc": "An extinction-level burst that fuses all signature powers."
            },
            "passive": {
                    "name": "Cascading Star",
                    "desc": "The die twin-hits and ramps behind a scaling aura."
            },
            "lore": "It has never lost. It simply has not finished playing.",
            "voice": "\u201cBet against me. Please.\u201d",
            "params": {
                    "twin_hit": 1,
                    "ramp_atk": 0.12,
                    "aura_atk": 0.2
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "All signature mechanics begin the battle pre-charged."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.15
                            },
                            "desc": "+15% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "The ultimate hits every enemy an extra time."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.18
                            },
                            "desc": "+18% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Signature auras and effects are 25% stronger."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 16
                            },
                            "desc": "+16 SPD; the die revives once at 50% HP."
                    }
            ]
    },
    {
            "id": "hidden_chance",
            "name": "Hidden Chance",
            "rarity": "ETERNAL",
            "element": "Blood",
            "role": "Fatebreaker",
            "tags": [
                    "Combo",
                    "Omen"
            ],
            "engine": [
                    "Combo",
                    "Omen"
            ],
            "stats": {
                    "hp": 1840,
                    "atk": 188,
                    "def": 95,
                    "spd": 117
            },
            "basic": {
                    "name": "First Law",
                    "desc": "A cosmic strike channeling every signature effect."
            },
            "skill": {
                    "name": "Second Law",
                    "desc": "Reshape the battlefield with combined mechanics."
            },
            "ult": {
                    "name": "Final Law",
                    "desc": "An extinction-level burst that fuses all signature powers."
            },
            "passive": {
                    "name": "Fatebreaker",
                    "desc": "The die resonant executes with lifesteal."
            },
            "lore": "A relic of a game whose rules were rewritten mid-throw.",
            "voice": "\u201cThe dealer folds first.\u201d",
            "params": {
                    "resonance_n": 3,
                    "lifesteal": 0.35,
                    "execute_th": 0.3,
                    "execute_pct": 0.6
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "All signature mechanics begin the battle pre-charged."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.15
                            },
                            "desc": "+15% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "The ultimate hits every enemy an extra time."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.18
                            },
                            "desc": "+18% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Signature auras and effects are 25% stronger."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 16
                            },
                            "desc": "+16 SPD; the die revives once at 50% HP."
                    }
            ]
    },
    {
            "id": "golden_shill",
            "name": "Golden Shill",
            "rarity": "ETERNAL",
            "element": "Poison",
            "role": "Voidrender",
            "tags": [
                    "Fracture",
                    "Sustain"
            ],
            "engine": [
                    "Fracture",
                    "Sustain"
            ],
            "stats": {
                    "hp": 1768,
                    "atk": 201,
                    "def": 108,
                    "spd": 111
            },
            "basic": {
                    "name": "First Law",
                    "desc": "A cosmic strike channeling every signature effect."
            },
            "skill": {
                    "name": "Second Law",
                    "desc": "Reshape the battlefield with combined mechanics."
            },
            "ult": {
                    "name": "Final Law",
                    "desc": "An extinction-level burst that fuses all signature powers."
            },
            "passive": {
                    "name": "Voidrender",
                    "desc": "The die overloads through shields, healing on the wreckage."
            },
            "lore": "Loaded not with lead, but with certainty.",
            "voice": "\u201cCome closer. Let me read your odds.\u201d",
            "params": {
                    "shield_break": 0.8,
                    "overload_pct": 0.5,
                    "lifesteal": 0.3
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "All signature mechanics begin the battle pre-charged."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.15
                            },
                            "desc": "+15% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "The ultimate hits every enemy an extra time."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.18
                            },
                            "desc": "+18% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Signature auras and effects are 25% stronger."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 16
                            },
                            "desc": "+16 SPD; the die revives once at 50% HP."
                    }
            ]
    },
    {
            "id": "astral_marker",
            "name": "Astral Marker",
            "rarity": "ETERNAL",
            "element": "Nature",
            "role": "Cosmic Warden",
            "tags": [
                    "Fortune",
                    "Control"
            ],
            "engine": [
                    "Fortune",
                    "Control"
            ],
            "stats": {
                    "hp": 1696,
                    "atk": 194,
                    "def": 101,
                    "spd": 122
            },
            "basic": {
                    "name": "First Law",
                    "desc": "A cosmic strike channeling every signature effect."
            },
            "skill": {
                    "name": "Second Law",
                    "desc": "Reshape the battlefield with combined mechanics."
            },
            "ult": {
                    "name": "Final Law",
                    "desc": "An extinction-level burst that fuses all signature powers."
            },
            "passive": {
                    "name": "Cosmic Warden",
                    "desc": "The die the ultimate team aura and enemy suppressor."
            },
            "lore": "It hums with the sound of every coin that ever hit the felt.",
            "voice": "\u201cThe wheel remembers your name.\u201d",
            "params": {
                    "aura_atk": 0.2,
                    "aura_def": 0.2,
                    "decay": 0.5,
                    "reflect": 0.3
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "All signature mechanics begin the battle pre-charged."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.15
                            },
                            "desc": "+15% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "The ultimate hits every enemy an extra time."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.18
                            },
                            "desc": "+18% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Signature auras and effects are 25% stronger."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 16
                            },
                            "desc": "+16 SPD; the die revives once at 50% HP."
                    }
            ]
    },
    {
            "id": "gilded_tempest",
            "name": "Gilded Tempest",
            "rarity": "ETERNAL",
            "element": "Wind",
            "role": "Endless Verdict",
            "tags": [
                    "Break",
                    "Combo"
            ],
            "engine": [
                    "Break",
                    "Combo"
            ],
            "stats": {
                    "hp": 1822,
                    "atk": 186,
                    "def": 94,
                    "spd": 115
            },
            "basic": {
                    "name": "First Law",
                    "desc": "A cosmic strike channeling every signature effect."
            },
            "skill": {
                    "name": "Second Law",
                    "desc": "Reshape the battlefield with combined mechanics."
            },
            "ult": {
                    "name": "Final Law",
                    "desc": "An extinction-level burst that fuses all signature powers."
            },
            "passive": {
                    "name": "Endless Verdict",
                    "desc": "The die a ramping twin-strike executioner."
            },
            "lore": "The dealer who made it never blinked again.",
            "voice": "\u201cAll in. There was never another option.\u201d",
            "params": {
                    "ramp_atk": 0.1,
                    "execute_th": 0.35,
                    "execute_pct": 0.7,
                    "twin_hit": 1
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "All signature mechanics begin the battle pre-charged."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.15
                            },
                            "desc": "+15% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "The ultimate hits every enemy an extra time."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.18
                            },
                            "desc": "+18% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Signature auras and effects are 25% stronger."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 16
                            },
                            "desc": "+16 SPD; the die revives once at 50% HP."
                    }
            ]
    },
    {
            "id": "verdant_rake",
            "name": "Verdant Rake",
            "rarity": "ETERNAL",
            "element": "Time",
            "role": "Zenith Engine",
            "tags": [
                    "Combo",
                    "Break"
            ],
            "engine": [
                    "Combo",
                    "Break"
            ],
            "stats": {
                    "hp": 1750,
                    "atk": 199,
                    "def": 106,
                    "spd": 109
            },
            "basic": {
                    "name": "First Law",
                    "desc": "A cosmic strike channeling every signature effect."
            },
            "skill": {
                    "name": "Second Law",
                    "desc": "Reshape the battlefield with combined mechanics."
            },
            "ult": {
                    "name": "Final Law",
                    "desc": "An extinction-level burst that fuses all signature powers."
            },
            "passive": {
                    "name": "Zenith Engine",
                    "desc": "The die resonant overload with reflect and lifesteal."
            },
            "lore": "It keeps a tally no ledger could hold.",
            "voice": "\u201cMy pips are your obituary.\u201d",
            "params": {
                    "resonance_n": 2,
                    "overload_pct": 0.5,
                    "reflect": 0.3,
                    "lifesteal": 0.35
            },
            "cons": [
                    {
                            "level": 1,
                            "desc": "All signature mechanics begin the battle pre-charged."
                    },
                    {
                            "level": 2,
                            "stat": {
                                    "atk_pct": 0.15
                            },
                            "desc": "+15% ATK."
                    },
                    {
                            "level": 3,
                            "desc": "The ultimate hits every enemy an extra time."
                    },
                    {
                            "level": 4,
                            "stat": {
                                    "hp_pct": 0.18
                            },
                            "desc": "+18% Max HP."
                    },
                    {
                            "level": 5,
                            "desc": "Signature auras and effects are 25% stronger."
                    },
                    {
                            "level": 6,
                            "stat": {
                                    "spd_flat": 16
                            },
                            "desc": "+16 SPD; the die revives once at 50% HP."
                    }
            ]
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
    # ── v7 themed sub-banners — each keeps its OWN 50/50 pity ──────────────
    "eternal_convergence": {
        "id": "eternal_convergence", "name": "Eternal Convergence",
        "subtitle": "Featured: Prime Tempest. The rarest die in creation descends \u2014 all outcomes converge on one.",
        "type": "limited", "sub": True, "theme": "Eternal", "cost": PULL_COST,
        "featured_eternal": "prime_tempest",
        "featured_rares": ["eternal_reckoner", "lunar_payout", "sovereign_fortune"],
    },
    "dawn_procession": {
        "id": "dawn_procession", "name": "Dawn Procession",
        "subtitle": "Featured: Dawnbreaker Apex. The last sunrise marches to war \u2014 stand in its light.",
        "type": "limited", "sub": True, "theme": "Eternal", "cost": PULL_COST,
        "featured_eternal": "dawnbreaker_apex",
        "featured_rares": ["candle_page", "beacon_cadet", "drift_lantern"],
    },
    "solar_dominion": {
        "id": "solar_dominion", "name": "Solar Dominion",
        "subtitle": "Featured: Solar Tyrant. A star that refused to set demands your ante.",
        "type": "limited", "sub": True, "theme": "Combo", "cost": PULL_COST,
        "featured_mythic": "solar_tyrant",
        "featured_rares": ["matchstick", "ember_squire", "glass_arbiter"],
    },
    "winter_court": {
        "id": "winter_court", "name": "The Winter Court",
        "subtitle": "Featured: Glacier Empress. Her palace is other people's stopped hearts.",
        "type": "limited", "sub": True, "theme": "Control", "cost": PULL_COST,
        "featured_mythic": "glacier_empress",
        "featured_rares": ["sleet_pixie", "brine_oracle", "tick_tocker"],
    },
    "grave_requiem": {
        "id": "grave_requiem", "name": "Grave Requiem",
        "subtitle": "Featured: Gravemind Die. Six feet under, six faces up \u2014 the dead count cards.",
        "type": "limited", "sub": True, "theme": "Omen", "cost": PULL_COST,
        "featured_mythic": "gravemind_die",
        "featured_rares": ["black_cat", "moon_moth", "vial_tosser"],
    },
    "hall_of_mirrors": {
        "id": "hall_of_mirrors", "name": "Hall of Mirrors",
        "subtitle": "Featured: Mirror Monarch. Every reflection is a rematch.",
        "type": "limited", "sub": True, "theme": "Echo", "cost": PULL_COST,
        "featured_mythic": "mirror_monarch",
        "featured_rares": ["rune_clerk", "static_jester", "sundial_monk"],
    },
    "iron_stampede": {
        "id": "iron_stampede", "name": "Iron Stampede",
        "subtitle": "Featured: Iron Colossus. Built to break banks. Renovated to break bones.",
        "type": "limited", "sub": True, "theme": "Break", "cost": PULL_COST,
        "featured_mythic": "iron_colossus",
        "featured_rares": ["grit_miner", "anvil_clerk", "scrap_pugilist"],
    },
}

# ─── v4.1 Endgame: Astral Abyss ─────────────────────────────────────────────
# Deep 12-floor endless dungeon. Enemy dicts copy the CAMPAIGN stage enemy
# shape exactly {name, element, hp, atk, def, spd, pow, ai}.
ABYSS_MODIFIERS = {
    "hp_up": {
        "name": "Bloated",
        "desc": "Enemies have +50% Max HP.",
        "hp": 0.5
    },
    "atk_up": {
        "name": "Vicious",
        "desc": "Enemies deal +40% damage.",
        "atk": 0.4
    },
    "fast": {
        "name": "Frenzied",
        "desc": "Enemies have +30% SPD.",
        "spd": 0.3
    },
    "thorns": {
        "name": "Thorned",
        "desc": "Enemies reflect 15% of damage taken.",
        "reflect": 0.15
    },
    "regen": {
        "name": "Regenerating",
        "desc": "Enemies heal 5% of Max HP each round.",
        "heal": 0.05
    },
    "shielded": {
        "name": "Shielded",
        "desc": "Enemies start with a shield worth 20% of Max HP.",
        "shield": 0.2
    },
    "resist_all": {
        "name": "Warded",
        "desc": "Enemies take 20% less damage from all sources.",
        "dr": 0.2
    },
    "enrage": {
        "name": "Enraged",
        "desc": "Enemies gain +5% ATK every round.",
        "atk_per_round": 0.05
    },
    "vampiric": {
        "name": "Vampiric",
        "desc": "Enemies heal for 30% of the damage they deal.",
        "lifesteal": 0.3
    },
    "unstoppable": {
        "name": "Unstoppable",
        "desc": "Bosses are immune to stun and freeze.",
        "cc_immune": 1
    }
}

ABYSS_FLOORS = [
    {
        "id": "a1",
        "name": "The First Descent",
        "lore": "The first step down. The air already tastes like a losing hand.",
        "tier": "NORMAL",
        "modifiers": [
            "hp_up"
        ],
        "enemies": [
            {
                "name": "Abyss Warden",
                "element": "Fire",
                "hp": 1800,
                "atk": 120,
                "def": 60,
                "spd": 96,
                "pow": 1.1,
                "ai": "basic"
            },
            {
                "name": "Abyss Warden",
                "element": "Light",
                "hp": 1800,
                "atk": 120,
                "def": 60,
                "spd": 93,
                "pow": 1.1,
                "ai": "debuff"
            },
            {
                "name": "Abyss Stalker",
                "element": "Nature",
                "hp": 1980,
                "atk": 126,
                "def": 60,
                "spd": 104,
                "pow": 1.05,
                "ai": "basic"
            }
        ],
        "reward": {
            "gems": 150,
            "shards": 10
        }
    },
    {
        "id": "a2",
        "name": "Whispering Dark",
        "lore": "Voices count your chips in a language you almost recognize.",
        "tier": "ELITE",
        "modifiers": [
            "atk_up"
        ],
        "enemies": [
            {
                "name": "Abyss Warden",
                "element": "Physical",
                "hp": 2700,
                "atk": 131,
                "def": 67,
                "spd": 98,
                "pow": 1.1,
                "ai": "basic"
            },
            {
                "name": "Abyss Warden",
                "element": "Poison",
                "hp": 2700,
                "atk": 131,
                "def": 67,
                "spd": 95,
                "pow": 1.1,
                "ai": "debuff"
            },
            {
                "name": "Abyss Reaver",
                "element": "Void",
                "hp": 4320,
                "atk": 150,
                "def": 73,
                "spd": 104,
                "pow": 1.2,
                "ai": "aoe"
            }
        ],
        "reward": {
            "gems": 200,
            "shards": 18
        }
    },
    {
        "id": "a3",
        "name": "Gravity Well",
        "lore": "Everything here falls faster, including your odds.",
        "tier": "NORMAL",
        "modifiers": [
            "fast",
            "regen"
        ],
        "enemies": [
            {
                "name": "Abyss Warden",
                "element": "Dark",
                "hp": 3600,
                "atk": 142,
                "def": 74,
                "spd": 100,
                "pow": 1.1,
                "ai": "basic"
            },
            {
                "name": "Abyss Warden",
                "element": "Time",
                "hp": 3600,
                "atk": 142,
                "def": 74,
                "spd": 97,
                "pow": 1.1,
                "ai": "debuff"
            },
            {
                "name": "Abyss Stalker",
                "element": "Ice",
                "hp": 3960,
                "atk": 148,
                "def": 74,
                "spd": 108,
                "pow": 1.05,
                "ai": "basic"
            }
        ],
        "reward": {
            "gems": 250,
            "shards": 26
        }
    },
    {
        "id": "a4",
        "name": "Mirror Vault",
        "lore": "You face reflections that have already beaten you.",
        "tier": "BOSS",
        "modifiers": [
            "shielded"
        ],
        "enemies": [
            {
                "name": "Abyss Warden",
                "element": "Nature",
                "hp": 4500,
                "atk": 153,
                "def": 81,
                "spd": 102,
                "pow": 1.1,
                "ai": "basic"
            },
            {
                "name": "Abyss Warden",
                "element": "Fire",
                "hp": 4500,
                "atk": 153,
                "def": 81,
                "spd": 99,
                "pow": 1.1,
                "ai": "debuff"
            },
            {
                "name": "Abyssal Sovereign",
                "element": "Arcane",
                "hp": 14400,
                "atk": 198,
                "def": 101,
                "spd": 106,
                "pow": 1.4,
                "ai": "boss"
            }
        ],
        "reward": {
            "gems": 300,
            "shards": 34
        }
    },
    {
        "id": "a5",
        "name": "Bleeding Edge",
        "lore": "Cut the dark and it bleeds back at you.",
        "tier": "NORMAL",
        "modifiers": [
            "thorns",
            "atk_up"
        ],
        "enemies": [
            {
                "name": "Abyss Warden",
                "element": "Void",
                "hp": 5400,
                "atk": 164,
                "def": 88,
                "spd": 104,
                "pow": 1.1,
                "ai": "basic"
            },
            {
                "name": "Abyss Warden",
                "element": "Physical",
                "hp": 5400,
                "atk": 164,
                "def": 88,
                "spd": 101,
                "pow": 1.1,
                "ai": "debuff"
            },
            {
                "name": "Abyss Stalker",
                "element": "Blood",
                "hp": 5940,
                "atk": 170,
                "def": 88,
                "spd": 112,
                "pow": 1.05,
                "ai": "basic"
            }
        ],
        "reward": {
            "gems": 350,
            "shards": 42
        }
    },
    {
        "id": "a6",
        "name": "Warded Sanctum",
        "lore": "A sanctum that refuses damage and mercy alike.",
        "tier": "ELITE",
        "modifiers": [
            "resist_all",
            "hp_up"
        ],
        "enemies": [
            {
                "name": "Abyss Warden",
                "element": "Ice",
                "hp": 6300,
                "atk": 175,
                "def": 95,
                "spd": 106,
                "pow": 1.1,
                "ai": "basic"
            },
            {
                "name": "Abyss Warden",
                "element": "Dark",
                "hp": 6300,
                "atk": 175,
                "def": 95,
                "spd": 103,
                "pow": 1.1,
                "ai": "debuff"
            },
            {
                "name": "Abyss Reaver",
                "element": "Wind",
                "hp": 10080,
                "atk": 201,
                "def": 104,
                "spd": 112,
                "pow": 1.2,
                "ai": "aoe"
            }
        ],
        "reward": {
            "gems": 400,
            "shards": 50
        }
    },
    {
        "id": "a7",
        "name": "Hunger Below",
        "lore": "Something below has learned to eat the light.",
        "tier": "NORMAL",
        "modifiers": [
            "vampiric",
            "fast"
        ],
        "enemies": [
            {
                "name": "Abyss Warden",
                "element": "Arcane",
                "hp": 7200,
                "atk": 186,
                "def": 102,
                "spd": 108,
                "pow": 1.1,
                "ai": "basic"
            },
            {
                "name": "Abyss Warden",
                "element": "Nature",
                "hp": 7200,
                "atk": 186,
                "def": 102,
                "spd": 105,
                "pow": 1.1,
                "ai": "debuff"
            },
            {
                "name": "Abyss Stalker",
                "element": "Earth",
                "hp": 7920,
                "atk": 192,
                "def": 102,
                "spd": 116,
                "pow": 1.05,
                "ai": "basic"
            }
        ],
        "reward": {
            "gems": 450,
            "shards": 58
        }
    },
    {
        "id": "a8",
        "name": "Rising Fury",
        "lore": "The deeper you go, the angrier the house becomes.",
        "tier": "BOSS",
        "modifiers": [
            "enrage",
            "shielded"
        ],
        "enemies": [
            {
                "name": "Abyss Warden",
                "element": "Blood",
                "hp": 8100,
                "atk": 197,
                "def": 109,
                "spd": 110,
                "pow": 1.1,
                "ai": "basic"
            },
            {
                "name": "Abyss Warden",
                "element": "Void",
                "hp": 8100,
                "atk": 197,
                "def": 109,
                "spd": 107,
                "pow": 1.1,
                "ai": "debuff"
            },
            {
                "name": "Abyssal Sovereign",
                "element": "Electric",
                "hp": 25920,
                "atk": 256,
                "def": 136,
                "spd": 114,
                "pow": 1.4,
                "ai": "boss"
            }
        ],
        "reward": {
            "gems": 500,
            "shards": 66
        }
    },
    {
        "id": "a9",
        "name": "The Broken Ladder",
        "lore": "The rungs are missing. So is your margin for error.",
        "tier": "NORMAL",
        "modifiers": [
            "resist_all",
            "thorns",
            "atk_up"
        ],
        "enemies": [
            {
                "name": "Abyss Warden",
                "element": "Wind",
                "hp": 9000,
                "atk": 208,
                "def": 116,
                "spd": 112,
                "pow": 1.1,
                "ai": "basic"
            },
            {
                "name": "Abyss Warden",
                "element": "Ice",
                "hp": 9000,
                "atk": 208,
                "def": 116,
                "spd": 109,
                "pow": 1.1,
                "ai": "debuff"
            },
            {
                "name": "Abyss Stalker",
                "element": "Light",
                "hp": 9900,
                "atk": 214,
                "def": 116,
                "spd": 120,
                "pow": 1.05,
                "ai": "basic"
            }
        ],
        "reward": {
            "gems": 550,
            "shards": 74
        }
    },
    {
        "id": "a10",
        "name": "Feast of Ruin",
        "lore": "The abyss sets a table and you are the meal.",
        "tier": "ELITE",
        "modifiers": [
            "vampiric",
            "regen",
            "hp_up"
        ],
        "enemies": [
            {
                "name": "Abyss Warden",
                "element": "Earth",
                "hp": 9900,
                "atk": 219,
                "def": 123,
                "spd": 114,
                "pow": 1.1,
                "ai": "basic"
            },
            {
                "name": "Abyss Warden",
                "element": "Arcane",
                "hp": 9900,
                "atk": 219,
                "def": 123,
                "spd": 111,
                "pow": 1.1,
                "ai": "debuff"
            },
            {
                "name": "Abyss Reaver",
                "element": "Poison",
                "hp": 15840,
                "atk": 251,
                "def": 135,
                "spd": 120,
                "pow": 1.2,
                "ai": "aoe"
            }
        ],
        "reward": {
            "gems": 600,
            "shards": 82
        }
    },
    {
        "id": "a11",
        "name": "Wrath Ascendant",
        "lore": "Rage made architecture; every wall wants you dead.",
        "tier": "NORMAL",
        "modifiers": [
            "enrage",
            "resist_all",
            "fast"
        ],
        "enemies": [
            {
                "name": "Abyss Warden",
                "element": "Electric",
                "hp": 10800,
                "atk": 230,
                "def": 130,
                "spd": 116,
                "pow": 1.1,
                "ai": "basic"
            },
            {
                "name": "Abyss Warden",
                "element": "Blood",
                "hp": 10800,
                "atk": 230,
                "def": 130,
                "spd": 113,
                "pow": 1.1,
                "ai": "debuff"
            },
            {
                "name": "Abyss Stalker",
                "element": "Time",
                "hp": 11880,
                "atk": 236,
                "def": 130,
                "spd": 124,
                "pow": 1.05,
                "ai": "basic"
            }
        ],
        "reward": {
            "gems": 650,
            "shards": 90
        }
    },
    {
        "id": "a12",
        "name": "The Astral Throne",
        "lore": "The seat of the abyss. Here the House stops pretending to be fair.",
        "tier": "BOSS",
        "modifiers": [
            "unstoppable",
            "enrage",
            "vampiric",
            "resist_all"
        ],
        "enemies": [
            {
                "name": "Abyss Warden",
                "element": "Light",
                "hp": 11700,
                "atk": 241,
                "def": 137,
                "spd": 118,
                "pow": 1.1,
                "ai": "basic"
            },
            {
                "name": "Abyss Warden",
                "element": "Wind",
                "hp": 11700,
                "atk": 241,
                "def": 137,
                "spd": 115,
                "pow": 1.1,
                "ai": "debuff"
            },
            {
                "name": "Abyssal Sovereign",
                "element": "Fire",
                "hp": 37440,
                "atk": 313,
                "def": 171,
                "spd": 122,
                "pow": 1.4,
                "ai": "boss"
            }
        ],
        "reward": {
            "gems": 700,
            "shards": 98
        }
    }
]

ABYSS_FLOOR_IDS = ["a1", "a2", "a3", "a4", "a5", "a6", "a7", "a8", "a9", "a10", "a11", "a12"]

# ─── v7 Expansion: +90 dice (210 -> 300) ────────────────────────────────────
from games.dice_data_v7 import V7_DICE
DICE_CATALOG += V7_DICE

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
            "ELEMENTS": ELEMENTS, "ELEMENT_COLORS": ELEMENT_COLORS,
            "ENGINE_TAGS": ENGINE_TAGS, "ENGINE_SYNERGY": ENGINE_SYNERGY,
            "STATUS_INFO": STATUS_INFO, "TEAM_SIZE": TEAM_SIZE,
            "CONSTELLATION_BONUS": CONSTELLATION_BONUS,
            "MAX_CONSTELLATION": MAX_CONSTELLATION,
            "PULL_COST": PULL_COST, "BEGINNER_PULL_COST": BEGINNER_PULL_COST,
            "BEGINNER_MAX_PULLS": BEGINNER_MAX_PULLS,
            "BATTLE_FIRST_CLEAR_REWARD": BATTLE_FIRST_CLEAR_REWARD,
            # v4.0
            "CRYSTAL_RATE": CRYSTAL_RATE, "GEM_RATE": GEM_RATE,
            "STARTER_GEMS": STARTER_GEMS,
            "BUNDLES": BUNDLES,
            "RELICS": RELICS,
            "RELIC_TIER_COLORS": RELIC_TIER_COLORS,
            "ENDLESS_MILESTONES": ENDLESS_MILESTONES,
            "ENDLESS_SCALE": ENDLESS_SCALE,
            "ASCENSION_MAX_LEVEL": ASCENSION_MAX_LEVEL,
            "ASCENSION_STEP_COST": ASCENSION_STEP_COST,
            "ASCENSION_STAT_PER_LEVEL": ASCENSION_STAT_PER_LEVEL,
            "ACHIEVEMENTS": ACHIEVEMENTS,
            "SPEED_OPTIONS": SPEED_OPTIONS,
            "TEAM_PRESET_SLOTS": TEAM_PRESET_SLOTS,
            "TEAM_COMPS": TEAM_COMPS,
            # v4.1 rarities + endgame
            "RARITIES": RARITIES, "BASE_RATES": BASE_RATES,
            "UNIVERSAL_SHARD_YIELD": UNIVERSAL_SHARD_YIELD,
            "ABYSS_FLOORS": ABYSS_FLOORS, "ABYSS_MODIFIERS": ABYSS_MODIFIERS,
            "ABYSS_FLOOR_IDS": ABYSS_FLOOR_IDS,
        },
    }
