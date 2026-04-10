"""Terminal UI helpers."""

import os
import sys

# Color codes (disable on Windows if not supported)
def _supports_color():
    return sys.stdout.isatty() or os.environ.get("FORCE_COLOR")

USE_COLOR = _supports_color()

class C:
    RESET  = "\033[0m"  if USE_COLOR else ""
    BOLD   = "\033[1m"  if USE_COLOR else ""
    RED    = "\033[91m" if USE_COLOR else ""
    YELLOW = "\033[93m" if USE_COLOR else ""
    GREEN  = "\033[92m" if USE_COLOR else ""
    CYAN   = "\033[96m" if USE_COLOR else ""
    BLUE   = "\033[94m" if USE_COLOR else ""
    DIM    = "\033[2m"  if USE_COLOR else ""
    WHITE  = "\033[97m" if USE_COLOR else ""

WIDTH = 72

def hr(char="─"):
    print(char * WIDTH)

def header(title: str):
    print()
    hr("═")
    print(f"  {C.BOLD}{C.CYAN}{title}{C.RESET}")
    hr("═")

def section(title: str):
    print()
    print(f"  {C.BOLD}{title}{C.RESET}")
    hr("─")

def status_color(status: str) -> str:
    colors = {
        "OK":             C.GREEN,
        "SCUFFED":        C.GREEN,
        "DAMAGED":        C.YELLOW,
        "EXPOSED":        C.YELLOW,
        "CRITICAL":       C.RED,
        "DESTROYED":      C.RED + C.BOLD,
        "COMBAT READY":   C.GREEN,
        "MINOR DAMAGE":   C.YELLOW,
        "MODERATE DAMAGE":C.YELLOW,
        "HEAVY DAMAGE":   C.RED,
        "NON-OPERATIONAL":C.RED + C.BOLD,
    }
    color = colors.get(status, "")
    return f"{color}{status}{C.RESET}"

def bar(current: int, maximum: int, width: int = 12) -> str:
    if maximum == 0:
        return "[" + " " * width + "]"
    filled = int((current / maximum) * width)
    pct = current / maximum
    if pct > 0.6:
        color = C.GREEN
    elif pct > 0.3:
        color = C.YELLOW
    else:
        color = C.RED
    return f"{color}[{'█' * filled}{'░' * (width - filled)}]{C.RESET}"

def prompt(text: str) -> str:
    try:
        return input(f"\n{C.BOLD}{C.WHITE}  > {text}: {C.RESET}").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return ""

def menu(options: list[tuple[str, str]], title: str = "Choose an action") -> str:
    """
    Display a numbered menu, return selected key or empty string.
    options: list of (key, label)
    """
    section(title)
    for i, (key, label) in enumerate(options, 1):
        print(f"  [{C.CYAN}{i}{C.RESET}] {label}")
    print(f"  [{C.DIM}0{C.RESET}] Back / Cancel")
    choice = prompt("Enter number")
    if not choice or choice == "0":
        return ""
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(options):
            return options[idx][0]
    except ValueError:
        pass
    return ""

def pause():
    input(f"\n  {C.DIM}[ Press Enter to continue ]{C.RESET}")

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def print_mech_overview(mech, show_index: int = None):
    from .data import LOC_SHORT
    prefix = f"[{show_index}] " if show_index is not None else "    "
    status = mech.overall_status
    print(f"  {C.BOLD}{prefix}{mech.callsign:<12}{C.RESET} "
          f"{C.DIM}{mech.chassis:<24}{C.RESET} "
          f"{mech.tonnage}t  {status_color(status)}")

def print_mech_detail(mech):
    from .data import LOC_SHORT, WEAPON_NAMES
    header(f"{mech.callsign}  —  {mech.chassis}  ({mech.tonnage}t {mech.weight_class})")
    print(f"  Pilot: {mech.pilot_name:<20}  Missions: {mech.missions_completed}")
    print(f"  Status: {status_color(mech.overall_status)}")
    section("Component Status")
    print(f"  {'Location':<18} {'Short':<5} {'Armor':<20} {'Struct':<20} {'Status':<12}")
    hr()
    for loc_name, comp in mech.components.items():
        short = LOC_SHORT[loc_name]
        armor_bar  = bar(comp.armor, comp.max_armor)
        struct_bar = bar(comp.structure, comp.max_structure)
        s = status_color(comp.status)
        print(f"  {loc_name:<18} {short:<5} "
              f"{armor_bar} {comp.armor:>3}/{comp.max_armor:<3}  "
              f"{struct_bar} {comp.structure:>3}/{comp.max_structure:<3}  {s}")
        # Equipment
        for item in comp.equipment:
            if item in comp.destroyed_equipment:
                print(f"    {C.RED}✗ {item} [DESTROYED]{C.RESET}")
            else:
                if item in WEAPON_NAMES:
                    print(f"    {C.GREEN}✓ {item}{C.RESET}")
    section("Working Weapons")
    weapons = mech.working_weapons
    if weapons:
        for loc, wpn in weapons:
            print(f"  {LOC_SHORT[loc]}: {wpn}")
    else:
        print(f"  {C.RED}NO OPERATIONAL WEAPONS{C.RESET}")
