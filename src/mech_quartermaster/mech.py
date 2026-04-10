"""Mech and component model."""

import random
from dataclasses import dataclass, field
from typing import Optional
from .data import LOCATIONS, LOC_SHORT, CHASSIS_DATA, WEAPON_NAMES


@dataclass
class Component:
    location: str
    max_armor: int
    max_structure: int
    equipment: list[str] = field(default_factory=list)
    # Current state
    armor: int = 0
    structure: int = 0
    destroyed_equipment: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.armor = self.max_armor
        self.structure = self.max_structure

    @property
    def is_destroyed(self) -> bool:
        return self.structure <= 0

    @property
    def armor_pct(self) -> float:
        if self.max_armor == 0:
            return 1.0
        return self.armor / self.max_armor

    @property
    def structure_pct(self) -> float:
        if self.max_structure == 0:
            return 1.0
        return self.structure / self.max_structure

    @property
    def status(self) -> str:
        if self.is_destroyed:
            return "DESTROYED"
        if self.structure < self.max_structure:
            return "CRITICAL"
        if self.armor == 0:
            return "EXPOSED"
        if self.armor < self.max_armor * 0.5:
            return "DAMAGED"
        if self.armor < self.max_armor:
            return "SCUFFED"
        return "OK"

    @property
    def needs_repair(self) -> bool:
        return (self.armor < self.max_armor or
                self.structure < self.max_structure or
                bool(self.destroyed_equipment))

    def apply_damage(self, amount: int) -> list[str]:
        """Apply damage, returns list of events that occurred."""
        events = []
        # Armor absorbs first
        armor_absorbed = min(self.armor, amount)
        self.armor -= armor_absorbed
        remaining = amount - armor_absorbed
        if remaining > 0 and armor_absorbed > 0:
            events.append(f"{self.location} armor breached!")
        # Overflow to structure
        if remaining > 0:
            struct_damage = min(self.structure, remaining)
            self.structure -= struct_damage
            events.append(f"{self.location} internal structure hit! ({struct_damage} damage)")
            # Critical hits: chance to destroy equipment
            for item in list(self.equipment):
                if item not in self.destroyed_equipment:
                    if random.random() < 0.35:
                        self.destroyed_equipment.append(item)
                        events.append(f"  >> CRITICAL: {item} destroyed in {self.location}!")
            if self.structure <= 0:
                events.append(f"  !! {self.location} DESTROYED !!")
        return events


class Mech:
    def __init__(self, chassis: str, pilot_name: str, callsign: str):
        self.chassis = chassis
        self.pilot_name = pilot_name
        self.callsign = callsign
        self.data = CHASSIS_DATA[chassis]
        self.components: dict[str, Component] = {}
        self.repair_log: list[str] = []
        self.missions_completed = 0
        self.total_loss = False  # True when reactor explodes / mech is unrecoverable
        # Build components
        locs = LOCATIONS
        armor_vals = self.data["armor"]
        struct_vals = self.data["structure"]
        equip_map = self.data.get("equipment", {})
        for i, loc in enumerate(locs):
            self.components[loc] = Component(
                location=loc,
                max_armor=armor_vals[i],
                max_structure=struct_vals[i],
                equipment=list(equip_map.get(loc, [])),
            )

    @property
    def tonnage(self) -> int:
        return self.data["tonnage"]

    @property
    def weight_class(self) -> str:
        return self.data["class"]

    @property
    def armor_plate_part(self) -> str:
        return f"Armor Plating ({self.weight_class})"

    @property
    def structure_brace_part(self) -> str:
        return f"Structure Brace ({self.weight_class})"

    @property
    def is_combat_ready(self) -> bool:
        """Can this mech fight? CT/legs/head not destroyed, has some weapons."""
        critical = ["Center Torso", "Left Leg", "Right Leg", "Head"]
        for loc in critical:
            if self.components[loc].is_destroyed:
                return False
        # Must have at least one working weapon
        return len(self.working_weapons) > 0

    @property
    def working_weapons(self) -> list[tuple[str, str]]:
        """List of (location, weapon) for all operational weapons."""
        result = []
        for loc, comp in self.components.items():
            if not comp.is_destroyed:
                for item in comp.equipment:
                    if item in WEAPON_NAMES and item not in comp.destroyed_equipment:
                        result.append((loc, item))
        return result

    @property
    def overall_status(self) -> str:
        if not self.is_combat_ready:
            return "NON-OPERATIONAL"
        damaged = sum(1 for c in self.components.values() if c.needs_repair)
        if damaged == 0:
            return "COMBAT READY"
        if damaged <= 2:
            return "MINOR DAMAGE"
        if damaged <= 5:
            return "MODERATE DAMAGE"
        return "HEAVY DAMAGE"

    def repair_cost_estimate(self, inventory: "Inventory") -> dict:
        """Return breakdown of parts needed for full repair."""
        needed = {}
        for comp in self.components.values():
            if comp.armor < comp.max_armor:
                key = self.armor_plate_part
                needed[key] = needed.get(key, 0) + 1
            if comp.structure < comp.max_structure:
                key = self.structure_brace_part
                needed[key] = needed.get(key, 0) + 1
            for item in comp.destroyed_equipment:
                if item in WEAPON_NAMES:
                    needed[item] = needed.get(item, 0) + 1
        return needed

    def summary_line(self) -> str:
        status = self.overall_status
        ct = self.components["Center Torso"]
        armor_pct = int(ct.armor_pct * 100)
        return (f"{self.callsign:<12} | {self.chassis:<24} | "
                f"{self.tonnage}t {self.weight_class:<7} | {status}")


class Inventory:
    def __init__(self, starting_credits: int = 500000):
        self.credits = starting_credits
        self.parts: dict[str, int] = {}
        self.pending_orders: list[dict] = []  # orders arriving in future turns

    def stock(self, part: str) -> int:
        return self.parts.get(part, 0)

    def add_parts(self, part: str, qty: int):
        self.parts[part] = self.parts.get(part, 0) + qty

    def use_part(self, part: str, qty: int = 1) -> bool:
        if self.parts.get(part, 0) >= qty:
            self.parts[part] -= qty
            if self.parts[part] == 0:
                del self.parts[part]
            return True
        return False

    def process_orders(self, current_day: int) -> list[str]:
        """Check pending orders, receive any due. Returns arrival messages."""
        arrived = []
        still_pending = []
        for order in self.pending_orders:
            if order["arrive_day"] <= current_day:
                self.add_parts(order["part"], order["qty"])
                arrived.append(
                    f"ORDER ARRIVED: {order['qty']}x {order['part']}"
                )
            else:
                still_pending.append(order)
        self.pending_orders = still_pending
        return arrived
