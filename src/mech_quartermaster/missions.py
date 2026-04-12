"""Mission simulation — generates damage to mechs after deployment."""

import random
from .mech import Mech


def simulate_mission(mechs: list[Mech], mission_type: dict, damage_multiplier: float = 1.0,
                     success_modifier: float = 0.0) -> dict:
    """
    Simulate a mission. Returns a report dict with:
    - success: bool
    - events: list of strings (battle log)
    - rewards: int (C-Bills earned)
    - casualties: list of mech callsigns that are non-operational post-battle
    """
    scale = mission_type["damage_scale"] * damage_multiplier
    events = []
    events.append(f"=== MISSION: {mission_type['name'].upper()} ===")
    events.append(mission_type["description"])
    events.append("")

    # Mechs that can fight
    ready = [m for m in mechs if m.is_combat_ready]
    if not ready:
        return {
            "success": False,
            "events": events + ["Lance has no combat-ready mechs. Mission aborted."],
            "rewards": 0,
            "casualties": [m.callsign for m in mechs],
        }

    # Base 60%, plus per-mech class bonus, minus damage scale penalty
    class_bonus = mission_type.get("class_bonus", {})
    success_chance = (0.60
        + sum(class_bonus.get(m.weight_class, 0.06) for m in ready)
        - (scale - 0.5) * 0.15
        + success_modifier)
    success_chance = min(max(success_chance, 0.05), 0.95)  # clamp 5–95%
    success = random.random() < success_chance

    for mech in ready:
        mech.missions_completed += 1
        events.append(f"--- {mech.callsign} ({mech.chassis}) ---")
        mech_events = _damage_mech(mech, scale, success)
        events.extend(mech_events)
        events.append("")

    reward_range = mission_type["c_bill_reward"]
    base_reward = random.randint(*reward_range)
    if not success:
        base_reward = int(base_reward * 0.3)  # partial payment for failure

    total_losses = [m for m in ready if m.total_loss]
    casualties = [m.callsign for m in ready if not m.is_combat_ready and not m.total_loss]

    if success:
        events.append("MISSION SUCCESS — Lance completes objectives.")
    else:
        events.append("MISSION FAILED — Lance forced to withdraw.")
    events.append(f"Contract payment: {base_reward:,} C-Bills")

    if total_losses:
        events.append("")
        events.append("*** TOTAL LOSSES ***")
        for m in total_losses:
            events.append(f"  {m.callsign} ({m.chassis}) — REACTOR DESTROYED. Pilot {m.pilot_name}: KIA.")

    salvage = _generate_salvage(mission_type, len(ready), success)
    if salvage["parts"] or salvage["mech"]:
        events.append("")
        events.append("--- SALVAGE RECOVERED ---")
        for part, qty in salvage["parts"].items():
            events.append(f"  {qty}x {part}")
        if salvage["mech"]:
            events.append(f"  ** MECH WRECK: {salvage['mech']} (salvageable) **")

    return {
        "success": success,
        "events": events,
        "rewards": base_reward,
        "casualties": casualties,
        "total_losses": [m.callsign for m in total_losses],
        "salvage": salvage,
    }


def _generate_salvage(mission_type: dict, mechs_deployed: int, success: bool) -> dict:
    """Generate salvage from a mission. Returns {parts: {name: qty}, mech: chassis_str or None}."""
    scale = mission_type.get("salvage_scale", 0.5)
    if not success:
        scale *= 0.35  # retreating forces leave most salvage behind

    # Number of part drops: scale * mechs * random variance
    count = int(scale * mechs_deployed * random.uniform(0.8, 2.0))

    # Weighted salvage pool: armor most common, weapons rarer
    pool = (
        [("Armor Plating (Light)",    10),
         ("Armor Plating (Medium)",   10),
         ("Armor Plating (Heavy)",     7),
         ("Armor Plating (Assault)",   4),
         ("Structure Brace (Light)",   6),
         ("Structure Brace (Medium)",  6),
         ("Structure Brace (Heavy)",   4),
         ("Structure Brace (Assault)", 2),
         ("Heat Sink",                 8),
         ("Ammo Bin",                  7),
         ("Actuator (Arm)",            5),
         ("Actuator (Leg)",            4),
         ("Machine Gun",                6),
         ("Small Laser",               5),
         ("Medium Laser",              4),
         ("Large Laser",               2),
         ("SRM-4",                     3),
         ("SRM-6",                     3),
         ("LRM-10",                    2),
         ("LRM-15",                    2),
         ("LRM-20",                    1),
         ("AC/5",                      2),
         ("AC/10",                     1),
         ("AC/20",                     1),
         ("PPC",                       1)]
    )
    items   = [p for p, _ in pool]
    weights = [w for _, w in pool]

    parts: dict[str, int] = {}
    for _ in range(count):
        item = random.choices(items, weights=weights, k=1)[0]
        parts[item] = parts.get(item, 0) + 1

    # Mech wreck salvage — chance varies ±50% around the mission's base value
    base_chance = mission_type.get("mech_salvage_chance", 0.05)
    mech_chance = random.uniform(base_chance * 0.5, base_chance * 1.5)
    if not success:
        mech_chance *= 0.25  # very unlikely to drag a wreck home while retreating
    salvaged_mech = None
    if random.random() < mech_chance:
        # Lighter chassis more common as field salvage
        chassis_pool = [
            # Lights (most common salvage)
            ("Locust LCT-1V",       10),
            ("Spider SDR-5V",        9),
            ("Commando COM-2D",      8),
            ("Firestarter FS9-H",    8),
            ("Jenner JR7-D",         7),
            # Mediums
            ("Vindicator VND-1R",    6),
            ("Centurion CN9-A",      6),
            ("Hunchback HBK-4G",     5),
            ("Trebuchet TBT-5N",     5),
            ("Griffin GRF-1N",       5),
            ("Wolverine WVR-6R",     5),
            # Heavies
            ("Dragon DRG-1N",        3),
            ("Catapult CPLT-C1",     3),
            ("Thunderbolt TDR-5S",   3),
            ("Warhammer WHM-6R",     2),
            ("Marauder MAD-3R",      2),
            # Assaults (rare)
            ("Victor VTR-9B",        1),
            ("Stalker STK-3F",       1),
            ("Battlemaster BLR-1G",  1),
            ("Atlas AS7-D",          1),
        ]
        chassis_list   = [c for c, _ in chassis_pool]
        chassis_weights = [w for _, w in chassis_pool]
        salvaged_mech = random.choices(chassis_list, weights=chassis_weights, k=1)[0]

    return {"parts": parts, "mech": salvaged_mech}


def _damage_mech(mech: Mech, scale: float, mission_success: bool) -> list[str]:
    """Apply randomised damage to one mech, return event list."""
    events = []
    tonnage = mech.tonnage

    # Total damage budget: lighter mechs get hit relatively harder
    # Scale by mission intensity and random variance
    base_damage = int(tonnage * scale * random.uniform(0.3, 1.1))
    if not mission_success:
        base_damage = int(base_damage * random.uniform(1.2, 1.8))

    if base_damage < 5:
        events.append("  No significant damage sustained.")
        return events

    events.append(f"  Incoming damage assessment: ~{base_damage} damage points")

    # Distribute damage hits across random locations
    # Weight towards arms/torsos (more exposed), legs less so, head rarely
    location_weights = {
        "Head": 1, "Center Torso": 8, "Left Torso": 7, "Right Torso": 7,
        "Left Arm": 9, "Right Arm": 9, "Left Leg": 5, "Right Leg": 5,
    }
    loc_pool = list(location_weights.keys())
    weights = list(location_weights.values())

    remaining = base_damage
    hit_count = 0
    while remaining > 0 and hit_count < 20:
        loc = random.choices(loc_pool, weights=weights, k=1)[0]
        comp = mech.components[loc]
        if comp.is_destroyed:
            # Skip destroyed locations (hits transfer to CT or adjacent)
            loc = "Center Torso"
            comp = mech.components[loc]
        hit_size = random.randint(5, max(5, int(remaining * 0.6)))
        hit_size = min(hit_size, remaining)
        hit_events = comp.apply_damage(hit_size)
        if hit_events:
            events.extend([f"  {e}" for e in hit_events])
        remaining -= hit_size
        hit_count += 1
        # CT destroyed = reactor breach = total loss
        if mech.components["Center Torso"].is_destroyed:
            mech.total_loss = True
            events.append(f"  !!! REACTOR BREACH — {mech.callsign} EXPLODES !!!")
            events.append(f"  !!! Pilot {mech.pilot_name} is KILLED IN ACTION !!!")
            break

    return events
