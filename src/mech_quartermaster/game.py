"""Main game loop and all screen logic."""

import json
import os
import random
from .mech import Mech, Inventory
from .data import (CHASSIS_DATA, PARTS_CATALOG, MISSION_TYPES, WEAPON_NAMES, MECH_PRICES,
                   OVERHEAD_BASE, OVERHEAD_PER_MECH, OVERHEAD_PER_TON)
from .campaigns.base import Campaign
from .campaigns import ALL_CAMPAIGNS
from .missions import simulate_mission
from . import ui
from .ui import C, header, section, hr, prompt, menu, pause, clear, print_mech_detail


# ─── Game State ──────────────────────────────────────────────────────────────

MAX_MECHS   = 8
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

        # Weekly overhead: charge every 7 days
        overhead_messages = []
        if self.day % 7 == 0:
            cost = self.weekly_overhead
            self.inventory.credits -= cost
            self.overhead_paid += cost
            msg = f"Weekly overhead paid: {cost:,}c  (Balance: {self.inventory.credits:,}c)"
            self.event_log.append(f"Day {self.day}: {msg}")
            overhead_messages.append(msg)

        # Refresh available missions daily
        mission_pool = self.campaign.available_mission_types or MISSION_TYPES
        self.daily_missions = random.sample(mission_pool, min(3, len(mission_pool)))

        # Refresh market every 7 days
        if self.day % 7 == 0 or not self.market:
            self._refresh_market()

        # Fire narrative events
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


# ─── Screens ─────────────────────────────────────────────────────────────────

def screen_main(gs: GameState):
    clear()
    diff_color = {"Easy": C.GREEN, "Medium": C.YELLOW, "Hard": C.RED}.get(gs.difficulty, "")
    header(f"MECHBAY COMMAND  —  {gs.company_name}  [{diff_color}{gs.difficulty}{C.RESET}]")
    credit_color = C.RED if gs.inventory.credits < gs.weekly_overhead else C.GREEN
    print(f"  Day: {C.BOLD}{gs.day}{C.RESET}   "
          f"C-Bills: {C.BOLD}{credit_color}{gs.inventory.credits:,}{C.RESET}   "
          f"Tech Hours: {C.BOLD}{gs.tech_hours_remaining}/{gs.tech_hours_per_day}{C.RESET}")
    overhead_color = C.RED if gs.days_until_overhead <= 2 else C.YELLOW
    print(f"  Overhead due in: {overhead_color}{gs.days_until_overhead} day(s){C.RESET}  "
          f"{C.DIM}({gs.weekly_overhead:,}c/week — {gs.overhead_breakdown}){C.RESET}")
    if gs.campaign.victory_missions is not None:
        print(f"  Missions: {C.BOLD}{gs.missions_run}/{gs.campaign.victory_missions}{C.RESET}")

    if gs.pending_narrative:
        section("INCOMING TRANSMISSION")
        for msg in gs.pending_narrative:
            for line in msg.split("\n"):
                print(f"  {C.CYAN}{line}{C.RESET}")
        gs.pending_narrative.clear()

    if gs.mechs:
        section("Lance Status")
        for i, mech in enumerate(gs.mechs, 1):
            ui.print_mech_overview(mech, show_index=i)
    else:
        print(f"\n  {C.RED}LANCE EMPTY — No mechs on roster.{C.RESET}")

    # Show recent log entries
    if gs.event_log:
        section("Recent Activity")
        for entry in gs.event_log[-5:]:
            print(f"  {C.DIM}{entry}{C.RESET}")

    options = [
        ("inspect",  "Inspect Mech"),
        ("repair",   "Repair Mech"),
        ("parts",    "Parts & Inventory"),
        ("order",    "Order Parts"),
        ("market",   "Mech Market (Buy Mechs)"),
        ("deploy",   "Deploy Lance (Mission)"),
        ("advance",  "End Day (advance time)"),
        ("quit",     "Quit"),
    ]
    choice = menu(options, "Main Menu")
    return choice


def screen_inspect(gs: GameState):
    clear()
    header("INSPECT MECH")
    for i, mech in enumerate(gs.mechs, 1):
        ui.print_mech_overview(mech, show_index=i)
    choice = prompt("Select mech number (0 to cancel)")
    if not choice or choice == "0":
        return
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(gs.mechs):
            clear()
            print_mech_detail(gs.mechs[idx])
            pause()
    except ValueError:
        pass


def screen_repair(gs: GameState):
    while True:
        clear()
        header("REPAIR MECH")
        print(f"  Tech Hours Available Today: {C.BOLD}{gs.tech_hours_remaining}{C.RESET}")
        print()
        for i, mech in enumerate(gs.mechs, 1):
            ui.print_mech_overview(mech, show_index=i)
        choice = prompt("Select mech to repair (0 to cancel)")
        if not choice or choice == "0":
            return
        try:
            idx = int(choice) - 1
        except ValueError:
            continue
        if not (0 <= idx < len(gs.mechs)):
            continue

        mech = gs.mechs[idx]

        while True:
            clear()
            header(f"REPAIR: {mech.callsign}")
            print(f"  Tech hours remaining: {C.BOLD}{gs.tech_hours_remaining}/{gs.tech_hours_per_day}{C.RESET}")

            # Build repair job list fresh each loop
            jobs = []
            for loc_name, comp in mech.components.items():
                if comp.armor < comp.max_armor:
                    part = mech.armor_plate_part
                    cost, hours, _ = PARTS_CATALOG[part]
                    jobs.append({
                        "label": f"Repair armor: {loc_name} ({comp.armor}/{comp.max_armor})",
                        "part": part, "hours": hours,
                        "action": ("armor", loc_name), "have": gs.inventory.stock(part),
                    })
                if comp.structure < comp.max_structure:
                    part = mech.structure_brace_part
                    cost, hours, _ = PARTS_CATALOG[part]
                    jobs.append({
                        "label": f"Repair structure: {loc_name} ({comp.structure}/{comp.max_structure})",
                        "part": part, "hours": hours,
                        "action": ("structure", loc_name), "have": gs.inventory.stock(part),
                    })
                for item in comp.destroyed_equipment:
                    if item in WEAPON_NAMES and item in PARTS_CATALOG:
                        cost, hours, _ = PARTS_CATALOG[item]
                        jobs.append({
                            "label": f"Replace {item}: {loc_name}",
                            "part": item, "hours": hours,
                            "action": ("equipment", loc_name, item), "have": gs.inventory.stock(item),
                        })

            if not jobs:
                print(f"\n  {C.GREEN}No repairs needed — mech is at full condition.{C.RESET}")
                pause()
                break

            section("Available Repair Jobs")
            print(f"  {'#':<3} {'Job':<45} {'Part':<25} {'Stock':<6} {'Hours'}")
            hr()
            for i, job in enumerate(jobs, 1):
                stock_color = C.GREEN if job["have"] > 0 else C.RED
                hour_color  = C.RED if job["hours"] > gs.tech_hours_remaining else ""
                print(f"  {i:<3} {job['label']:<45} {job['part']:<25} "
                      f"{stock_color}{job['have']:<6}{C.RESET} {hour_color}{job['hours']}h{C.RESET}")

            print(f"\n  Type job number to perform repair, 'all' to do all possible, 0 to go back.")

            choice = prompt("Select job")
            if not choice or choice == "0":
                break
            if choice.lower() == "all":
                performed = sum(1 for job in jobs if _do_repair(gs, mech, job))
                print(f"\n  {C.GREEN}Completed {performed} repair job(s).{C.RESET}")
                pause()
                continue
            try:
                jidx = int(choice) - 1
                if 0 <= jidx < len(jobs):
                    _do_repair(gs, mech, jobs[jidx], verbose=True)
            except ValueError:
                pass


def _do_repair(gs: GameState, mech: Mech, job: dict, verbose: bool = False) -> bool:
    if gs.tech_hours_remaining < job["hours"]:
        if verbose:
            print(f"  {C.RED}Not enough tech hours remaining ({job['hours']}h needed).{C.RESET}")
        return False
    if gs.inventory.stock(job["part"]) < 1:
        if verbose:
            print(f"  {C.RED}No {job['part']} in inventory.{C.RESET}")
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

    gs.event_log.append(f"Day {gs.day}: {mech.callsign} — {msg}")
    if verbose:
        print(f"  {C.GREEN}✓ {msg} (-1 {job['part']}, -{job['hours']}h){C.RESET}")
    return True


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


def screen_parts(gs: GameState):
    # Generate sell offers once per session so prices don't change mid-screen
    offers = {name: _part_sell_price(name) for name in gs.inventory.parts}

    while True:
        clear()
        header("PARTS INVENTORY")
        print(f"  C-Bills: {C.BOLD}{C.GREEN}{gs.inventory.credits:,}{C.RESET}")

        stock_list = sorted(gs.inventory.parts.items())
        # Add any new items that arrived without an offer price
        for name in gs.inventory.parts:
            if name not in offers:
                offers[name] = _part_sell_price(name)

        section("In Stock  (enter number to sell)")
        if stock_list:
            print(f"  {'#':<4} {'Part':<35} {'Qty':<5} {'Sell price ea.'}")
            hr()
            for i, (name, qty) in enumerate(stock_list, 1):
                print(f"  {i:<4} {name:<35} {qty:<5} {C.YELLOW}{offers[name]:,}c{C.RESET}")
        else:
            print(f"  {C.DIM}Inventory empty.{C.RESET}")

        if gs.inventory.pending_orders:
            section("Pending Orders")
            print(f"  {'Part':<35} {'Qty':<5} {'Arrives Day'}")
            hr()
            for order in gs.inventory.pending_orders:
                print(f"  {order['part']:<35} {order['qty']:<5} Day {order['arrive_day']}")

        if not stock_list:
            pause()
            return

        print(f"\n  {C.DIM}Enter part number to sell, or 0 to exit.{C.RESET}")
        choice = prompt("Sell part #")
        if not choice or choice == "0":
            return
        try:
            pidx = int(choice) - 1
        except ValueError:
            continue
        if not (0 <= pidx < len(stock_list)):
            continue

        part_name, in_stock = stock_list[pidx]
        offer_each = offers[part_name]
        print(f"\n  {part_name}  —  {in_stock} in stock  —  {offer_each:,}c each")
        qty_str = prompt(f"Quantity to sell (max {in_stock})")
        try:
            qty = int(qty_str)
        except (ValueError, TypeError):
            continue
        if qty <= 0 or qty > in_stock:
            print(f"  {C.RED}Invalid quantity.{C.RESET}")
            pause()
            continue

        total = offer_each * qty
        confirm = prompt(f"Sell {qty}x {part_name} for {total:,}c? (y/n)")
        if confirm.lower() != "y":
            continue

        gs.inventory.use_part(part_name, qty)
        gs.inventory.credits += total
        print(f"  {C.GREEN}Sold {qty}x {part_name} for {total:,}c.{C.RESET}")
        gs.event_log.append(f"Day {gs.day}: Sold {qty}x {part_name} for {total:,}c")


def screen_order(gs: GameState):
    clear()
    header("ORDER PARTS")
    print(f"  C-Bills available: {C.BOLD}{C.GREEN}{gs.inventory.credits:,}{C.RESET}")
    print(f"  Orders arrive in 1-3 days (depending on item type).\n")
    section("Parts Catalog")
    parts_list = list(PARTS_CATALOG.items())
    print(f"  {'#':<4} {'Part':<35} {'Cost':>10}   {'Time':>6}  Description")
    hr()
    for i, (name, (cost, hours, desc)) in enumerate(parts_list, 1):
        print(f"  {i:<4} {name:<35} {cost:>10,}c  {hours:>5}h  {C.DIM}{desc}{C.RESET}")

    print()
    choice = prompt("Enter part number to order (0 to cancel)")
    if not choice or choice == "0":
        return
    try:
        pidx = int(choice) - 1
    except ValueError:
        return
    if not (0 <= pidx < len(parts_list)):
        return

    part_name, (cost, hours, desc) = parts_list[pidx]
    qty_str = prompt(f"How many {part_name}? (each costs {cost:,}c)")
    try:
        qty = int(qty_str)
        if qty <= 0:
            return
    except (ValueError, TypeError):
        return

    total = cost * qty
    if total > gs.inventory.credits:
        print(f"  {C.RED}Insufficient funds ({total:,}c needed, {gs.inventory.credits:,}c available).{C.RESET}")
        pause()
        return

    # Delivery time: weapons take longer
    if part_name in WEAPON_NAMES or "Structure" in part_name:
        arrive_days = random.randint(2, 4)
    else:
        arrive_days = random.randint(1, 2)

    gs.inventory.credits -= total
    gs.inventory.pending_orders.append({
        "part": part_name,
        "qty": qty,
        "arrive_day": gs.day + arrive_days,
    })
    print(f"  {C.GREEN}Order placed: {qty}x {part_name} for {total:,}c — arrives Day {gs.day + arrive_days}{C.RESET}")
    gs.event_log.append(f"Day {gs.day}: Ordered {qty}x {part_name} ({total:,}c)")
    pause()


def screen_deploy(gs: GameState):
    clear()
    header("DEPLOY LANCE")
    all_ready = [m for m in gs.mechs if m.is_combat_ready]
    not_ready = [m for m in gs.mechs if not m.is_combat_ready]

    section("Lance Readiness")
    for m in gs.mechs:
        ui.print_mech_overview(m)

    if not_ready:
        print(f"\n  {C.YELLOW}Warning: {len(not_ready)} mech(s) non-operational (will not deploy).{C.RESET}")
    if not all_ready:
        print(f"\n  {C.RED}No combat-ready mechs available!{C.RESET}")
        pause()
        return

    final = gs.campaign.final_mission
    vm = gs.campaign.victory_missions
    is_final = (final is not None and vm is not None and gs.missions_run == vm - 1)
    available = [final] if is_final else gs.daily_missions

    if is_final:
        print(f"\n  {C.BOLD}{C.RED}*** ONE MISSION STANDS BETWEEN YOU AND VICTORY ***{C.RESET}\n")
    section("Available Contracts" + ("  (refresh each day)" if not is_final else ""))
    for i, mt in enumerate(available, 1):
        level     = gs.mission_level(mt['name'])
        pay_mult  = 1.35 ** (level - 1)
        dmg_mult  = 1.20 ** (level - 1)
        min_pay, max_pay = mt["c_bill_reward"]
        scaled_min = int(min_pay * pay_mult)
        scaled_max = int(max_pay * pay_mult)
        salvage_bars = '█' * int(mt['salvage_scale'] * 2.5)
        damage_bars  = '█' * int(mt['damage_scale'] * dmg_mult * 5)
        wreck_bars   = '█' * int(mt['mech_salvage_chance'] / 0.50 * 6)
        cb = mt["class_bonus"]
        bonus_str = "  ".join(
            f"{cls[0]}:{int(cb[cls]*100)}%" for cls in ["Light","Medium","Heavy","Assault"]
        )
        if level == 1:
            lvl_color, lvl_label = C.DIM, f"LVL {level}"
        elif level <= 3:
            lvl_color, lvl_label = C.YELLOW, f"LVL {level} ▲"
        else:
            lvl_color, lvl_label = C.RED, f"LVL {level} ▲▲"
        print(f"  [{C.CYAN}{i}{C.RESET}] {C.BOLD}{mt['name']:<10}{C.RESET}  "
              f"{mt['description']}  {lvl_color}{lvl_label}{C.RESET}")
        pay_suffix = f"  {C.DIM}(×{pay_mult:.2f} difficulty){C.RESET}" if level > 1 else ""
        print(f"      Pay:     {C.GREEN}{scaled_min:>10,} – {scaled_max:,}c{C.RESET}{pay_suffix}")
        print(f"      Salvage: {C.YELLOW}{salvage_bars:<6}{C.RESET}  "
              f"Wreck: {C.BLUE}{wreck_bars:<6}{C.RESET}  "
              f"Damage risk: {C.RED}{damage_bars}{C.RESET}")
        print(f"      Success: {C.DIM}base 60% +per mech: {bonus_str}{C.RESET}")
        print()

    choice = prompt("Select contract (0 to cancel)")
    if not choice or choice == "0":
        return
    try:
        midx = int(choice) - 1
    except ValueError:
        return
    if not (0 <= midx < len(available)):
        return

    mission_type = available[midx]

    # ── Lance Selection ───────────────────────────────────────────────────────
    if len(all_ready) > MAX_DEPLOYED:
        section(f"Select Lance  (choose up to {MAX_DEPLOYED}, e.g. '1 3 4')")
        print(f"  {'#':<3} {'Callsign':<12} {'Chassis':<24} {'Class':<8} {'Status'}")
        hr()
        for i, m in enumerate(all_ready, 1):
            cb = mission_type.get("class_bonus", {})
            bonus = f"+{int(cb.get(m.weight_class, 0) * 100)}%"
            print(f"  {i:<3} {m.callsign:<12} {m.chassis:<24} {m.weight_class:<8} "
                  f"{ui.status_color(m.overall_status)}  {C.DIM}{bonus}{C.RESET}")
        while True:
            raw = prompt(f"Select up to {MAX_DEPLOYED} mechs by number")
            if not raw:
                return
            try:
                indices = [int(x) - 1 for x in raw.split()]
            except ValueError:
                print(f"  {C.RED}Enter space-separated numbers.{C.RESET}")
                continue
            if not indices or len(indices) > MAX_DEPLOYED:
                print(f"  {C.RED}Select between 1 and {MAX_DEPLOYED} mechs.{C.RESET}")
                continue
            if len(set(indices)) != len(indices):
                print(f"  {C.RED}Duplicate selections.{C.RESET}")
                continue
            if any(i < 0 or i >= len(all_ready) for i in indices):
                print(f"  {C.RED}Invalid selection.{C.RESET}")
                continue
            ready = [all_ready[i] for i in indices]
            break
    else:
        ready = all_ready

    # ── Battle Orders ─────────────────────────────────────────────────────────
    clear()
    header("BATTLE ORDERS")
    print(f"  Contract:  {C.BOLD}{mission_type['name']}{C.RESET}")
    print(f"  Deploying: {', '.join(m.callsign for m in ready)}")
    section("Select Battle Orders")
    for i, order in enumerate(BATTLE_ORDERS, 1):
        print(f"  [{C.CYAN}{i}{C.RESET}] {C.BOLD}{order['name']}{C.RESET}")
        print(f"      {order['description']}")
        print(f"      {C.DIM}{order['effects']}{C.RESET}")
        print()
    order_choice = prompt("Select orders (0 to cancel)")
    if not order_choice or order_choice == "0":
        return
    try:
        oidx = int(order_choice) - 1
    except ValueError:
        return
    if not (0 <= oidx < len(BATTLE_ORDERS)):
        return
    order = BATTLE_ORDERS[oidx]

    # Resolve random success modifier for "Show Off"
    if order["success_mod"] is None:
        resolved_success_mod = random.uniform(-0.20, 0.20)
    else:
        resolved_success_mod = order["success_mod"]

    # Build a modified copy of mission_type so the originals are unchanged
    level          = gs.mission_level(mission_type['name'])
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

    print(f"\n  Orders issued: {C.BOLD}{order['name']}{C.RESET}")
    print(f"  {C.DIM}{order['effects']}{C.RESET}")
    confirm = prompt("\n  Confirm deployment? (y/n)")
    if confirm.lower() != "y":
        return

    clear()
    result = simulate_mission(ready, mt, adjusted_damage_mult, resolved_success_mod)
    header("AFTER ACTION REPORT")
    print(f"  Orders: {C.BOLD}{order['name']}{C.RESET}  {C.DIM}({order['effects']}){C.RESET}\n")
    for line in result["events"]:
        print(f"  {line}")

    gs.inventory.credits += result["rewards"]
    color = C.GREEN if result["success"] else C.RED
    print(f"\n  {color}Payment received: {result['rewards']:,} C-Bills{C.RESET}")
    print(f"  New balance: {gs.inventory.credits:,} C-Bills")

    if result["casualties"]:
        print(f"\n  {C.YELLOW}Non-operational post-mission: {', '.join(result['casualties'])}{C.RESET}")

    # Remove total losses from roster
    if result.get("total_losses"):
        before = len(gs.mechs)
        gs.mechs = [m for m in gs.mechs if not m.total_loss]
        removed = before - len(gs.mechs)
        if removed:
            gs.event_log.append(
                f"Day {gs.day}: {removed} mech(s) lost — TOTAL LOSS (reactor destroyed)"
            )

    # Apply salvage
    salvage = result.get("salvage", {})
    salvage_parts = salvage.get("parts", {})
    salvaged_chassis = salvage.get("mech")
    if salvage_parts:
        for part, qty in salvage_parts.items():
            gs.inventory.add_parts(part, qty)
        gs.event_log.append(
            f"Day {gs.day}: Salvage recovered — "
            + ", ".join(f"{q}x {p}" for p, q in salvage_parts.items())
        )
    if salvaged_chassis:
        used_callsigns = {m.callsign for m in gs.mechs}
        used_pilots    = {m.pilot_name for m in gs.mechs}
        callsign = next((c for c in CALLSIGNS if c not in used_callsigns), f"Wreck-{gs.day}")
        pilot    = next((p for p in PILOT_NAMES if p not in used_pilots), f"Rookie-{gs.day}")
        wreck = Mech(chassis=salvaged_chassis, pilot_name=pilot, callsign=callsign)
        # Strip armor, damage structure to 30-55%
        for comp in wreck.components.values():
            comp.armor = 0
            comp.structure = max(1, int(comp.max_structure * random.uniform(0.30, 0.55)))
            # Random equipment losses
            for item in list(comp.equipment):
                if random.random() < 0.5:
                    comp.destroyed_equipment.append(item)
        if len(gs.mechs) >= MAX_MECHS:
            _forced_sell_screen(gs, f"{salvaged_chassis} (salvage wreck)")
        gs.mechs.append(wreck)
        gs.mechs.sort(key=lambda m: m.tonnage)
        print(f"\n  {C.YELLOW}SALVAGED MECH: {salvaged_chassis} assigned callsign '{callsign}'.{C.RESET}")
        print(f"  {C.DIM}Wreck condition — requires full repair before deployment.{C.RESET}")
        gs.event_log.append(f"Day {gs.day}: Salvaged mech wreck — {salvaged_chassis} '{callsign}'")

    if result["success"]:
        gs.missions_run += 1
        name = mission_type['name']
        gs.mission_completions[name] = gs.mission_completions.get(name, 0) + 1
        new_level = gs.mission_level(name)
        if new_level > level:
            print(f"\n  {C.YELLOW}{C.BOLD}CONTRACT DIFFICULTY UP — {name} is now LVL {new_level}! "
                  f"(+20% damage / +35% pay){C.RESET}")
    gs.event_log.append(
        f"Day {gs.day}: {mission_type['name']} — "
        f"{'SUCCESS' if result['success'] else 'FAILED'} "
        f"+{result['rewards']:,}c  [{gs.missions_run}/{gs.campaign.victory_missions} missions]"
    )
    # Advancing time after a mission
    arrivals, overhead_msgs = gs.advance_day()
    if arrivals:
        print()
        for msg in arrivals:
            print(f"  {C.GREEN}{msg}{C.RESET}")
    for msg in overhead_msgs:
        print(f"\n  {C.YELLOW}OVERHEAD: {msg}{C.RESET}")
    pause()


def screen_advance(gs: GameState):
    clear()
    header("END OF DAY")
    print(f"  Ending Day {gs.day}...")
    arrivals, overhead_msgs = gs.advance_day()
    if arrivals:
        print()
        for msg in arrivals:
            print(f"  {C.GREEN}{msg}{C.RESET}")
    else:
        print(f"  No parts arrived.")
    for msg in overhead_msgs:
        print(f"\n  {C.YELLOW}OVERHEAD: {msg}{C.RESET}")
    print(f"\n  {C.DIM}Day {gs.day} begins.{C.RESET}")
    pause()


def _forced_sell_screen(gs: GameState, incoming: str):
    """Called when roster is full. Player must sell a mech before the incoming one is added."""
    clear()
    header("ROSTER FULL — SELL A MECH")
    print(f"  Your roster is at the {MAX_MECHS}-mech cap.")
    print(f"  Incoming: {C.YELLOW}{incoming}{C.RESET}")
    print(f"  You must sell one mech to make room.\n")
    sell_offers = {m.callsign: _mech_sell_price(m) for m in gs.mechs}
    print(f"  {'#':<3} {'Callsign':<12} {'Chassis':<24} {'Status':<18} {'Offer':>12}")
    hr()
    for i, m in enumerate(gs.mechs, 1):
        offer = sell_offers[m.callsign]
        print(f"  {i:<3} {m.callsign:<12} {m.chassis:<24} "
              f"{ui.status_color(m.overall_status):<28} {C.YELLOW}{offer:>12,}c{C.RESET}")
    while True:
        choice = prompt("Select mech to sell (number)")
        if not choice:
            continue
        try:
            idx = int(choice) - 1
        except ValueError:
            continue
        if not (0 <= idx < len(gs.mechs)):
            continue
        mech = gs.mechs[idx]
        offer = sell_offers[mech.callsign]
        confirm = prompt(f"Sell {mech.callsign} ({mech.chassis}) for {offer:,}c? (y/n)")
        if confirm.lower() != "y":
            continue
        gs.inventory.credits += offer
        gs.mechs.remove(mech)
        print(f"  {C.GREEN}Sold {mech.callsign} for {offer:,}c.{C.RESET}")
        gs.event_log.append(f"Day {gs.day}: Sold {mech.callsign} ({mech.chassis}) for {offer:,}c (roster cap)")
        break


def screen_market(gs: GameState):
    clear()
    header("MECH MARKET")
    print(f"  C-Bills available: {C.BOLD}{C.GREEN}{gs.inventory.credits:,}{C.RESET}")
    if not gs.market:
        gs._refresh_market()
    days_until_refresh = 7 - ((gs.day - gs.market_refresh_day) % 7)
    print(f"  Market refreshes in {days_until_refresh} day(s).\n")

    section("Available Mechs")
    print(f"  {'#':<3} {'Chassis':<24} {'Class':<8} {'Tons':<5} {'Condition':<12} {'Price':>14}")
    hr()
    for i, listing in enumerate(gs.market, 1):
        data = CHASSIS_DATA[listing["chassis"]]
        cond = listing["condition"]
        cond_color = C.GREEN if cond == "Pristine" else (C.YELLOW if cond == "Used" else C.RED)
        print(f"  {i:<3} {listing['chassis']:<24} {data['class']:<8} {data['tonnage']:<5} "
              f"{cond_color}{cond:<12}{C.RESET} {listing['price']:>14,}c")

    # ── Sell section ──
    if gs.mechs:
        sell_offers = {m.callsign: _mech_sell_price(m) for m in gs.mechs}
        section("Sell a Mech  (enter 's' + number, e.g. s1)")
        print(f"  {'#':<3} {'Callsign':<12} {'Chassis':<24} {'Status':<18} {'Offer':>12}")
        hr()
        for i, m in enumerate(gs.mechs, 1):
            offer = sell_offers[m.callsign]
            print(f"  s{i:<2} {m.callsign:<12} {m.chassis:<24} "
                  f"{ui.status_color(m.overall_status):<28} {C.YELLOW}{offer:>12,}c{C.RESET}")
        print()

    print()
    raw = prompt("Buy # / Sell s# / 0 to cancel")
    if not raw or raw == "0":
        return

    # ── Sell path ──
    if raw.lower().startswith("s"):
        try:
            sidx = int(raw[1:]) - 1
        except ValueError:
            return
        if not (0 <= sidx < len(gs.mechs)):
            return
        mech = gs.mechs[sidx]
        offer = sell_offers[mech.callsign]
        print(f"\n  {C.BOLD}{mech.callsign}{C.RESET}  ({mech.chassis}, {mech.tonnage}t)")
        print(f"  Condition: {ui.status_color(mech.overall_status)}")
        print(f"  Offer:     {C.YELLOW}{offer:,}c{C.RESET}")
        if len(gs.mechs) == 1:
            print(f"  {C.RED}Warning: selling your last mech will end the game.{C.RESET}")
        confirm = prompt("Accept offer and sell? (y/n)")
        if confirm.lower() != "y":
            return
        gs.inventory.credits += offer
        gs.mechs.remove(mech)
        print(f"\n  {C.GREEN}Sold {mech.callsign} ({mech.chassis}) for {offer:,}c.{C.RESET}")
        gs.event_log.append(f"Day {gs.day}: Sold {mech.callsign} ({mech.chassis}) for {offer:,}c")
        pause()
        return

    # ── Buy path ──
    try:
        midx = int(raw) - 1
    except ValueError:
        return
    if not (0 <= midx < len(gs.market)):
        return

    listing = gs.market[midx]
    chassis = listing["chassis"]
    price = listing["price"]
    cond = listing["condition"]
    data = CHASSIS_DATA[chassis]

    print(f"\n  {C.BOLD}{chassis}{C.RESET}  —  {cond}  —  {price:,}c")
    print(f"  {data['tonnage']}t {data['class']}")
    if len(gs.mechs) >= MAX_MECHS:
        print(f"  {C.YELLOW}Note: roster is full ({MAX_MECHS} mechs). You will be asked to sell one.{C.RESET}")
    if price > gs.inventory.credits:
        print(f"\n  {C.RED}Insufficient funds.{C.RESET}")
        pause()
        return

    confirm = prompt("Confirm purchase? (y/n)")
    if confirm.lower() != "y":
        return

    # Assign pilot and callsign
    used_callsigns = {m.callsign for m in gs.mechs}
    used_pilots = {m.pilot_name for m in gs.mechs}
    available_callsigns = [c for c in CALLSIGNS if c not in used_callsigns]
    available_pilots = [p for p in PILOT_NAMES if p not in used_pilots]
    callsign = random.choice(available_callsigns) if available_callsigns else f"Mech-{gs.day}"
    pilot = random.choice(available_pilots) if available_pilots else f"Rookie-{gs.day}"

    new_mech = Mech(chassis=chassis, pilot_name=pilot, callsign=callsign)

    # Apply pre-existing damage for used/battle-worn mechs
    if listing["damage_pct"] > 0:
        for comp in new_mech.components.values():
            armor_loss = int(comp.max_armor * listing["damage_pct"] * random.uniform(0.5, 1.5))
            armor_loss = min(armor_loss, comp.max_armor)
            comp.armor = max(0, comp.max_armor - armor_loss)

    gs.inventory.credits -= price
    gs.market.pop(midx)  # remove sold listing before forced-sell screen
    if len(gs.mechs) >= MAX_MECHS:
        _forced_sell_screen(gs, f"{chassis} (purchased)")
    gs.mechs.append(new_mech)
    gs.mechs.sort(key=lambda m: m.tonnage)

    print(f"\n  {C.GREEN}Purchase complete!{C.RESET}")
    print(f"  {callsign} ({chassis}) added to roster.")
    print(f"  Assigned pilot: {pilot}")
    if cond != "Pristine":
        print(f"  {C.YELLOW}Note: Mech arrived with pre-existing damage — inspect before deploying.{C.RESET}")
    gs.event_log.append(f"Day {gs.day}: Purchased {chassis} '{callsign}' for {price:,}c")
    pause()


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


def screen_victory(gs: GameState):
    clear()
    ui.hr("═")
    victory_body = gs.campaign.victory_text.format(
        company_name=gs.company_name, missions_run=gs.missions_run
    )
    print(f"""
  {C.BOLD}{C.GREEN}╔══════════════════════════════════════════╗
  ║   CONTRACT FULFILLED — LANCE VICTORIOUS  ║
  ╚══════════════════════════════════════════╝{C.RESET}

{victory_body}
""")
    mech_value, credits, score, diff_mult = _final_score(gs)
    ui.hr()
    print(f"\n  {C.BOLD}Final Statistics — {gs.company_name}  [{gs.difficulty}]{C.RESET}")
    print(f"  Days active:      {gs.day}")
    if gs.campaign.victory_missions is not None:
        print(f"  Missions run:     {gs.missions_run}/{gs.campaign.victory_missions}")
    print(f"  Mechs surviving:  {len(gs.mechs)}")
    surviving = ", ".join(f"{m.callsign} ({m.chassis})" for m in gs.mechs)
    print(f"                    {surviving}")
    print(f"  Fleet value:      {mech_value:,}c")
    print(f"  Final balance:    {credits:,}c")
    print(f"  Overhead paid:    {gs.overhead_paid:,}c")
    print()
    ui.hr()
    print(f"\n  {C.BOLD}FINAL SCORE{C.RESET}")
    print(f"  ({mech_value:,}c fleet  +  {credits:,}c cash)")
    print(f"  x  (100 - {gs.day} days) = {max(0, 100 - gs.day)}")
    print(f"  x  {diff_mult} ({gs.difficulty})")
    print(f"\n  {C.BOLD}{C.GREEN}{score:,}{C.RESET}")
    print()
    ui.hr("═")

    # ── Lance save prompt ─────────────────────────────────────────────────────
    section("Save Lance")
    existing = _load_lance_data()
    if existing:
        print(f"  Existing save: {C.DIM}{_save_summary(existing)}{C.RESET}")
        save_q = prompt("Save this lance? It will overwrite the existing save. (y/n)")
    else:
        save_q = prompt("Save this lance for your next campaign? (y/n)")
    if save_q.strip().lower() == "y":
        _save_lance(gs)
        print(f"  {C.GREEN}Lance saved.{C.RESET}")
    pause()


def screen_game_over(gs: GameState, reason: str):
    clear()
    ui.hr("═")
    print(f"""
  {C.BOLD}{C.RED}╔══════════════════════════════════╗
  ║         COMPANY DISSOLVED        ║
  ╚══════════════════════════════════╝{C.RESET}
""")
    print(f"  {C.RED}{reason}{C.RESET}")
    print()
    ui.hr()
    print(f"\n  {C.BOLD}Final Statistics — {gs.company_name}  [{gs.difficulty}]{C.RESET}")
    print(f"  Days survived:    {gs.day}")
    print(f"  Missions run:     {gs.missions_run}")
    print(f"  Overhead paid:    {gs.overhead_paid:,}c")
    print(f"  Mechs remaining:  {len(gs.mechs)}")
    print(f"  Final balance:    {gs.inventory.credits:,}c")
    print()
    ui.hr("═")
    pause()


# ─── Setup ───────────────────────────────────────────────────────────────────

PILOT_NAMES = [
    "Vasquez", "Kowalski", "Chen", "Okonkwo", "Petrov",
    "Hashimoto", "Reyes", "Bernhardt", "Osei", "Novak",
]
CALLSIGNS = [
    "Ironside", "Banshee", "Hammer", "Wraith", "Bulldozer",
    "Spectre", "Anvil", "Frostbite", "Hellfire", "Longbow",
]

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
    # Components start fully repaired — constructor already sets max armor/structure
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


def _build_lance(starting_lance) -> list[Mech]:
    """Build starting mechs from a campaign's starting_lance spec."""
    used_callsigns: set[str] = set()
    used_pilots: set[str] = set()
    mechs = []

    if isinstance(starting_lance, list):
        chassis_list = starting_lance
    else:
        # dict like {"Light": 2, "Medium": 1, "Heavy": 1}
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


def screen_campaign_select() -> Campaign:
    clear()
    ui.hr("═")
    print(f"\n  {C.BOLD}{C.CYAN}MECHBAY OPERATIONS{C.RESET}\n")
    section("Select Campaign")
    for i, camp in enumerate(ALL_CAMPAIGNS, 1):
        print(f"  [{C.CYAN}{i}{C.RESET}] {C.BOLD}{camp.name}{C.RESET}")
        print(f"      {camp.description}")
        print()
    while True:
        choice = prompt("Enter campaign number")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(ALL_CAMPAIGNS):
                return ALL_CAMPAIGNS[idx]
        except (ValueError, TypeError):
            pass


def setup_game(campaign: Campaign) -> GameState:
    clear()
    ui.hr("═")
    print(f"\n  {C.BOLD}{C.CYAN}{campaign.name.upper()}{C.RESET}\n")
    print(campaign.intro_text)
    print()
    ui.hr("═")

    company = prompt("Enter your company name")
    if not company:
        company = "Iron Lance"

    save_data = _load_lance_data()
    loaded_save = None
    if save_data:
        section("Lance Selection")
        print(f"  [1] New lance")
        print(f"  [2] Load saved lance — {C.DIM}{_save_summary(save_data)}{C.RESET}")
        print()
        while True:
            lc = prompt("Select (1/2, default 1)").strip()
            if lc in ("", "1"):
                mechs = _build_lance(campaign.starting_lance)
                break
            if lc == "2":
                mechs = [_mech_from_dict(m) for m in save_data["mechs"]]
                loaded_save = save_data
                break
            print(f"  {C.YELLOW}Enter 1 or 2.{C.RESET}")
    else:
        mechs = _build_lance(campaign.starting_lance)

    if loaded_save:
        inv = Inventory(starting_credits=loaded_save["credits"])
        for part, qty in loaded_save.get("parts", {}).items():
            inv.add_parts(part, qty)
    else:
        inv = Inventory(starting_credits=campaign.starting_credits)
        for part, qty in campaign.starting_parts.items():
            inv.add_parts(part, qty)

    section("Difficulty")
    for key, cfg in DIFFICULTIES.items():
        color = {"Easy": C.GREEN, "Medium": C.YELLOW, "Hard": C.RED}[key]
        print(f"  {color}{cfg['label']}{C.RESET}")
    diff_map = {"E": "Easy", "M": "Medium", "H": "Hard"}
    while True:
        diff_choice = prompt("Select difficulty (E/M/H, default H)").strip().upper()
        if diff_choice == "":
            difficulty = "Hard"
            break
        if diff_choice in diff_map:
            difficulty = diff_map[diff_choice]
            break
        print(f"  {C.YELLOW}Invalid choice — enter E, M, or H.{C.RESET}")
    print(f"  Difficulty set: {difficulty}")

    gs = GameState(company_name=company, mechs=mechs, inventory=inv,
                   difficulty=difficulty, campaign=campaign)
    if loaded_save:
        gs.mission_completions = {k: v for k, v in loaded_save.get("mission_completions", {}).items()}
    gs.mechs.sort(key=lambda m: m.tonnage)

    print(f"\n  {C.GREEN}Welcome, Quartermaster. Your lance is assembled.{C.RESET}")
    print(f"  Campaign:         {campaign.name}")
    print(f"  Difficulty:       {difficulty}")
    print(f"  Starting C-Bills: {gs.inventory.credits:,}")
    print(f"  Tech hours/day:   {gs.tech_hours_per_day}h")
    print(f"  Starting mechs:   {', '.join(m.callsign for m in mechs)}")
    pause()
    return gs


# ─── Main Loop ───────────────────────────────────────────────────────────────

def run():
    while True:
        campaign = screen_campaign_select()
        gs = setup_game(campaign)
        gs._refresh_market()
        while True:
            # Check end conditions before showing main screen
            if gs.is_victorious:
                screen_victory(gs)
                break
            if gs.is_bankrupt:
                screen_game_over(gs, "You have run out of C-Bills. The company cannot pay its debts.")
                break
            if gs.lance_destroyed:
                screen_game_over(gs, "All mechs have been destroyed. The lance is no more.")
                break

            action = screen_main(gs)
            if action == "inspect":
                screen_inspect(gs)
            elif action == "repair":
                screen_repair(gs)
            elif action == "parts":
                screen_parts(gs)
            elif action == "order":
                screen_order(gs)
            elif action == "market":
                screen_market(gs)
            elif action == "deploy":
                screen_deploy(gs)
            elif action == "advance":
                screen_advance(gs)
            elif action == "quit":
                clear()
                print(f"\n  {C.DIM}Shutting down mechbay systems. Good luck out there.{C.RESET}\n")
                return
