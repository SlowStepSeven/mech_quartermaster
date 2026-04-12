"""Game state, constants, and pure-logic helpers. No UI code."""

import json
import os
import random
from .mech import Mech, Inventory
from .data import (CHASSIS_DATA, PARTS_CATALOG, MISSION_TYPES, WEAPON_NAMES, MECH_PRICES,
                   OVERHEAD_BASE, OVERHEAD_PER_MECH, OVERHEAD_PER_TON)
from .campaigns.base import Campaign
from .campaigns import ALL_CAMPAIGNS
from .missions import simulate_mission


# ─── Constants ───────────────────────────────────────────────────────────────

MAX_MECHS    = 8
MAX_DEPLOYED = 4

BATTLE_ORDERS = [
    {
        "name":        "Keep Your Distance",
        "description": "Preserve the mechs — pull back, reduce exposure, avoid heavy contact.",
        "effects":     "Damage -20%  |  Salvage -20%",
        "damage_mult":  0.80,
        "salvage_mult": 0.80,
        "reward_mult":  1.00,
        "success_mod":  0.00,
    },
    {
        "name":        "Go All Out",
        "description": "Maximum aggression — overwhelm the enemy and take everything left standing.",
        "effects":     "Damage +35%  |  Salvage +50%  |  Success +10%",
        "damage_mult":  1.35,
        "salvage_mult": 1.50,
        "reward_mult":  1.00,
        "success_mod":  0.10,
    },
    {
        "name":        "Show Off for the Client",
        "description": "Put on a performance — the employer pays premium, but results are unpredictable.",
        "effects":     "Payout +40%  |  Success: random ±20%",
        "damage_mult":  1.00,
        "salvage_mult": 1.00,
        "reward_mult":  1.40,
        "success_mod":  None,  # resolved at mission time
    },
]

DIFFICULTIES = {
    "Easy": {
        "overhead_multiplier": 0.50,
        "damage_multiplier":   0.80,
        "tech_hours_bonus":    8,
        "label": "Easy    — 50% overhead, 80% damage, +8 tech hours/day",
    },
    "Medium": {
        "overhead_multiplier": 0.75,
        "damage_multiplier":   0.90,
        "tech_hours_bonus":    4,
        "label": "Medium  — 75% overhead, 90% damage, +4 tech hours/day",
    },
    "Hard": {
        "overhead_multiplier": 1.00,
        "damage_multiplier":   1.00,
        "tech_hours_bonus":    0,
        "label": "Hard    — 100% overhead, 100% damage, no bonus hours",
    },
}


# ─── Game State ──────────────────────────────────────────────────────────────

class GameState:
    def __init__(self, company_name: str, mechs: list[Mech], inventory: Inventory,
                 difficulty: str = "Hard", campaign: Campaign = None):
        self.company_name = company_name
        self.mechs = mechs
        self.inventory = inventory
        self.difficulty = difficulty
        self._diff = DIFFICULTIES[difficulty]
        self.campaign = campaign or ALL_CAMPAIGNS[0]
        self.day = 1
        self.event_log: list[str] = []
        self.tech_hours_per_day = 16 + self._diff["tech_hours_bonus"]
        self.tech_hours_used = 0
        mission_pool = self.campaign.available_mission_types or MISSION_TYPES
        self.daily_missions: list[dict] = random.sample(mission_pool, min(3, len(mission_pool)))
        self.market: list[dict] = []
        self.market_refresh_day: int = 1
        self.overhead_paid = 0
        self.missions_run = 0
        self.mission_completions: dict[str, int] = {}
        self.fired_events: set[str] = set()
        self.pending_narrative: list[str] = []

    def mission_level(self, mission_name: str) -> int:
        """Level 1 at start; +1 for every 2 successful completions of that type."""
        return self.mission_completions.get(mission_name, 0) // 2 + 1

    def advance_day(self, hours_spent: int = 0):
        self.tech_hours_used = 0
        self.day += 1
        arrivals = self.inventory.process_orders(self.day)
        for msg in arrivals:
            self.event_log.append(f"Day {self.day}: {msg}")

        overhead_messages = []
        if self.day % 7 == 0:
            cost = self.weekly_overhead
            self.inventory.credits -= cost
            self.overhead_paid += cost
            msg = f"Weekly overhead paid: {cost:,}c  (Balance: {self.inventory.credits:,}c)"
            self.event_log.append(f"Day {self.day}: {msg}")
            overhead_messages.append(msg)

        mission_pool = self.campaign.available_mission_types or MISSION_TYPES
        self.daily_missions = random.sample(mission_pool, min(3, len(mission_pool)))

        if self.day % 7 == 0 or not self.market:
            self._refresh_market()

        for event in self.campaign.events:
            if event.id not in self.fired_events and event.trigger(self):
                self.pending_narrative.append(event.text)
                if event.effect:
                    event.effect(self)
                if event.once:
                    self.fired_events.add(event.id)

        return arrivals, overhead_messages

    def _refresh_market(self):
        chassis_pool = list(MECH_PRICES.keys())
        random.shuffle(chassis_pool)
        self.market = []
        for chassis in chassis_pool[:5]:
            condition = random.choice(["Pristine", "Used", "Battle-Worn"])
            base = MECH_PRICES[chassis]
            if condition == "Pristine":
                price = base
                damage_pct = 0.0
            elif condition == "Used":
                price = int(base * random.uniform(0.60, 0.75))
                damage_pct = random.uniform(0.1, 0.3)
            else:
                price = int(base * random.uniform(0.40, 0.55))
                damage_pct = random.uniform(0.3, 0.6)
            self.market.append({
                "chassis": chassis,
                "condition": condition,
                "price": price,
                "damage_pct": damage_pct,
            })
        self.market_refresh_day = self.day

    @property
    def tech_hours_remaining(self) -> int:
        return max(0, self.tech_hours_per_day - self.tech_hours_used)

    @property
    def days_until_overhead(self) -> int:
        return 7 - (self.day % 7) if self.day % 7 != 0 else 7

    @property
    def weekly_overhead(self) -> int:
        total_tonnage = sum(m.tonnage for m in self.mechs)
        base = (OVERHEAD_BASE
                + len(self.mechs) * OVERHEAD_PER_MECH
                + total_tonnage * OVERHEAD_PER_TON)
        return int(base * self._diff["overhead_multiplier"])

    @property
    def overhead_breakdown(self) -> str:
        total_tonnage = sum(m.tonnage for m in self.mechs)
        pct = int(self._diff["overhead_multiplier"] * 100)
        return (f"base {OVERHEAD_BASE:,}c  +  "
                f"{len(self.mechs)} mechs x {OVERHEAD_PER_MECH:,}c  +  "
                f"{total_tonnage}t x {OVERHEAD_PER_TON:,}c  x {pct}%")

    @property
    def is_bankrupt(self) -> bool:
        return self.inventory.credits < 0

    @property
    def lance_destroyed(self) -> bool:
        return len(self.mechs) == 0

    @property
    def is_victorious(self) -> bool:
        return self.campaign.victory_condition(self)


# ─── Pure Logic Helpers ───────────────────────────────────────────────────────

def _do_repair(gs: GameState, mech: Mech, job: dict) -> bool:
    """Apply one repair job. Returns True on success, False if preconditions not met."""
    if gs.tech_hours_remaining < job["hours"]:
        return False
    if gs.inventory.stock(job["part"]) < 1:
        return False

    gs.inventory.use_part(job["part"])
    gs.tech_hours_used += job["hours"]

    action = job["action"]
    comp = mech.components[action[1]]

    if action[0] == "armor":
        comp.armor = comp.max_armor
        msg = f"Armor restored: {action[1]}"
    elif action[0] == "structure":
        comp.structure = comp.max_structure
        msg = f"Structure repaired: {action[1]}"
    elif action[0] == "equipment":
        weapon = action[2]
        if weapon in comp.destroyed_equipment:
            comp.destroyed_equipment.remove(weapon)
        msg = f"{weapon} replaced in {action[1]}"
    else:
        msg = "Unknown repair action"

    gs.event_log.append(f"Day {gs.day}: {mech.callsign} — {msg}")
    return True


def _repair_jobs(mech: Mech) -> list[dict]:
    """Return list of all available repair jobs for a mech."""
    jobs = []
    for loc, comp in mech.components.items():
        if comp.armor < comp.max_armor:
            jobs.append({
                "label":  f"Armor — {loc}",
                "part":   mech.armor_plate_part,
                "hours":  2,
                "action": ("armor", loc),
            })
        if comp.structure < comp.max_structure:
            jobs.append({
                "label":  f"Structure — {loc}",
                "part":   mech.structure_brace_part,
                "hours":  4,
                "action": ("structure", loc),
            })
        for item in comp.destroyed_equipment:
            if item in WEAPON_NAMES:
                hours = PARTS_CATALOG[item][1] if item in PARTS_CATALOG else 4
                jobs.append({
                    "label":  f"{item} — {loc}",
                    "part":   item,
                    "hours":  hours,
                    "action": ("equipment", loc, item),
                })
    return jobs


def _part_sell_price(part_name: str) -> int:
    """Offer price for one unit of a part: 25–50% of catalog cost."""
    if part_name not in PARTS_CATALOG:
        return 0
    base_cost = PARTS_CATALOG[part_name][0]
    return int(base_cost * random.uniform(0.25, 0.50))


def _mech_sell_price(mech: Mech) -> int:
    """Offer price for a mech: condition-scaled base price at 50–100%."""
    base = MECH_PRICES.get(mech.chassis, 0)
    total_current = sum(c.armor + c.structure for c in mech.components.values())
    total_max     = sum(c.max_armor + c.max_structure for c in mech.components.values())
    condition = total_current / total_max if total_max > 0 else 0
    return int(base * condition * random.uniform(0.50, 1.00))


def _final_score(gs: GameState) -> tuple[int, int, int, int]:
    """Returns (mech_value, credits, score, diff_mult)."""
    diff_mult = {"Easy": 1, "Medium": 2, "Hard": 3}.get(gs.difficulty, 1)
    mech_value = 0
    for m in gs.mechs:
        base = MECH_PRICES.get(m.chassis, 0)
        total_current = sum(c.armor + c.structure for c in m.components.values())
        total_max     = sum(c.max_armor + c.max_structure for c in m.components.values())
        condition = total_current / total_max if total_max > 0 else 0
        mech_value += int(base * condition)
    credits = gs.inventory.credits
    day_factor = max(0, 1 - gs.day / 100)
    score = int((mech_value + credits) * day_factor * diff_mult)
    return mech_value, credits, score, diff_mult


def _run_mission(gs: GameState, mission_type: dict, lance: list[Mech],
                 order: dict) -> tuple[dict, int]:
    """
    Execute a mission deployment. Mutates gs (credits, mechs, inventory, log).
    Returns (result_dict, new_level) where new_level > old_level if levelled up.
    """
    old_level = gs.mission_level(mission_type["name"])

    # Resolve "Show Off" random success mod
    if order["success_mod"] is None:
        resolved_success_mod = random.uniform(-0.20, 0.20)
    else:
        resolved_success_mod = order["success_mod"]

    level          = old_level
    level_pay_mult = 1.35 ** (level - 1)
    level_dmg_mult = 1.20 ** (level - 1)

    mt = dict(mission_type)
    min_pay, max_pay = mt["c_bill_reward"]
    mt["c_bill_reward"] = (
        int(min_pay * order["reward_mult"] * level_pay_mult),
        int(max_pay * order["reward_mult"] * level_pay_mult),
    )
    mt["salvage_scale"]       = mt["salvage_scale"]       * order["salvage_mult"]
    mt["mech_salvage_chance"] = mt["mech_salvage_chance"] * order["salvage_mult"]

    adjusted_damage_mult = gs._diff["damage_multiplier"] * order["damage_mult"] * level_dmg_mult

    result = simulate_mission(lance, mt, adjusted_damage_mult, resolved_success_mod)

    gs.inventory.credits += result["rewards"]

    # Remove total losses
    if result.get("total_losses"):
        before = len(gs.mechs)
        gs.mechs = [m for m in gs.mechs if not m.total_loss]
        removed = before - len(gs.mechs)
        if removed:
            gs.event_log.append(
                f"Day {gs.day}: {removed} mech(s) lost — TOTAL LOSS (reactor destroyed)"
            )

    # Track completion and check level-up
    new_level = old_level
    if result["success"]:
        gs.missions_run += 1
        name = mission_type["name"]
        gs.mission_completions[name] = gs.mission_completions.get(name, 0) + 1
        new_level = gs.mission_level(name)

    gs.event_log.append(
        f"Day {gs.day}: {mission_type['name']} — "
        f"{'SUCCESS' if result['success'] else 'FAILED'} "
        f"+{result['rewards']:,}c  [{gs.missions_run}/{gs.campaign.victory_missions} missions]"
    )

    return result, new_level


# ─── Setup ───────────────────────────────────────────────────────────────────

PILOT_NAMES = [
    "Vasquez", "Kowalski", "Chen", "Okonkwo", "Petrov",
    "Hashimoto", "Reyes", "Bernhardt", "Osei", "Novak",
]
CALLSIGNS = [
    "Ironside", "Banshee", "Hammer", "Wraith", "Bulldozer",
    "Spectre", "Anvil", "Frostbite", "Hellfire", "Longbow",
]


def _build_lance(starting_lance) -> list[Mech]:
    """Build starting mechs from a campaign's starting_lance spec."""
    used_callsigns: set[str] = set()
    used_pilots: set[str] = set()
    mechs = []

    if isinstance(starting_lance, list):
        chassis_list = starting_lance
    else:
        by_class: dict[str, list[str]] = {}
        for name, data in CHASSIS_DATA.items():
            cls = data["class"]
            by_class.setdefault(cls, []).append(name)
        chassis_list = []
        for cls, count in starting_lance.items():
            chassis_list += random.sample(by_class.get(cls, []), count)

    for chassis in chassis_list:
        callsign = random.choice([c for c in CALLSIGNS if c not in used_callsigns])
        pilot    = random.choice([p for p in PILOT_NAMES  if p not in used_pilots])
        used_callsigns.add(callsign)
        used_pilots.add(pilot)
        mechs.append(Mech(chassis=chassis, pilot_name=pilot, callsign=callsign))
    return mechs


def _new_callsign_pilot(gs: GameState) -> tuple[str, str]:
    """Return an unused (callsign, pilot) pair for a new mech."""
    used_callsigns = {m.callsign for m in gs.mechs}
    used_pilots    = {m.pilot_name for m in gs.mechs}
    callsign = next((c for c in CALLSIGNS if c not in used_callsigns), f"Wreck-{gs.day}")
    pilot    = next((p for p in PILOT_NAMES if p not in used_pilots),  f"Rookie-{gs.day}")
    return callsign, pilot


def build_gamestate(company: str, campaign: Campaign, difficulty: str,
                    mechs: list[Mech], save_data: dict | None) -> GameState:
    """Construct a GameState from setup inputs."""
    if save_data:
        inv = Inventory(starting_credits=save_data["credits"])
        for part, qty in save_data.get("parts", {}).items():
            inv.add_parts(part, qty)
    else:
        inv = Inventory(starting_credits=campaign.starting_credits)
        for part, qty in campaign.starting_parts.items():
            inv.add_parts(part, qty)

    gs = GameState(company_name=company, mechs=mechs, inventory=inv,
                   difficulty=difficulty, campaign=campaign)
    if save_data:
        gs.mission_completions = dict(save_data.get("mission_completions", {}))
    gs.mechs.sort(key=lambda m: m.tonnage)
    gs._refresh_market()
    return gs


# ─── Lance Save / Load ───────────────────────────────────────────────────────

SAVE_PATH = os.path.join(os.path.expanduser("~"), ".mech_qm_lance.json")


def _mech_to_dict(m: Mech) -> dict:
    return {
        "chassis": m.chassis,
        "pilot_name": m.pilot_name,
        "callsign": m.callsign,
        "missions_completed": m.missions_completed,
        "components": {
            loc: {
                "armor": comp.armor,
                "structure": comp.structure,
                "destroyed_equipment": list(comp.destroyed_equipment),
            }
            for loc, comp in m.components.items()
        },
    }


def _mech_from_dict(d: dict) -> Mech:
    m = Mech(chassis=d["chassis"], pilot_name=d["pilot_name"], callsign=d["callsign"])
    m.missions_completed = d.get("missions_completed", 0)
    return m


def _save_lance(gs: GameState):
    data = {
        "company_name": gs.company_name,
        "credits": gs.inventory.credits,
        "parts": dict(gs.inventory.parts),
        "mission_completions": dict(gs.mission_completions),
        "mechs": [_mech_to_dict(m) for m in gs.mechs],
    }
    with open(SAVE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _load_lance_data() -> dict | None:
    if not os.path.exists(SAVE_PATH):
        return None
    try:
        with open(SAVE_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_summary(data: dict) -> str:
    names = ", ".join(f"{m['callsign']} ({m['chassis']})" for m in data["mechs"])
    credits = data.get("credits", 0)
    return f"{data['company_name']} — {credits:,}c — {names}"
