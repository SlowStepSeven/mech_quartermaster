"""UI helpers — pure string/markup functions for Textual rendering."""

from rich.text import Text

WIDTH = 72


class C:
    """Rich markup tag constants."""
    RESET    = "[/]"
    BOLD     = "[bold]"
    RED      = "[red]"
    YELLOW   = "[yellow]"
    GREEN    = "[green]"
    CYAN     = "[cyan]"
    BLUE     = "[blue]"
    DIM      = "[dim]"
    WHITE    = "[white]"
    BOLD_RED = "[bold red]"


# Status string → Rich color tag
_STATUS_COLOR = {
    "OK":              "[green]",
    "SCUFFED":         "[green]",
    "DAMAGED":         "[yellow]",
    "EXPOSED":         "[yellow]",
    "CRITICAL":        "[red]",
    "DESTROYED":       "[bold red]",
    "COMBAT READY":    "[green]",
    "MINOR DAMAGE":    "[yellow]",
    "MODERATE DAMAGE": "[yellow]",
    "HEAVY DAMAGE":    "[red]",
    "NON-OPERATIONAL": "[bold red]",
}


def status_color(status: str) -> str:
    """Return Rich markup string: colored status label."""
    tag = _STATUS_COLOR.get(status, "")
    return f"{tag}{status}[/]" if tag else status


def status_text(status: str) -> Text:
    """Return a rich.text.Text object for use in DataTable cells."""
    tag = _STATUS_COLOR.get(status, "")
    style = tag.strip("[]") if tag else ""
    return Text(status, style=style)


def bar(current: int, maximum: int, width: int = 12, as_text: bool = False):
    """
    Render a progress bar.
    Returns Rich markup string by default, or rich.text.Text if as_text=True.
    """
    if maximum == 0:
        raw = "[" + " " * width + "]"
        return Text(raw) if as_text else raw
    filled = int((current / maximum) * width)
    pct = current / maximum
    color = "green" if pct > 0.6 else ("yellow" if pct > 0.3 else "red")
    inner = "█" * filled + "░" * (width - filled)
    if as_text:
        t = Text()
        t.append("[", style="dim")
        t.append(inner, style=color)
        t.append("]", style="dim")
        return t
    return f"[dim][[/][{color}]{inner}[/][dim]][/]"


def mech_overview_markup(mech, show_index: int | None = None) -> str:
    """Rich markup string: single-line mech summary for lists."""
    prefix = f"[cyan]\\[{show_index}][/] " if show_index is not None else "    "
    return (
        f"{prefix}[bold]{mech.callsign:<12}[/] "
        f"[dim]{mech.chassis:<24}[/] "
        f"{mech.tonnage}t  {status_color(mech.overall_status)}"
    )


def mech_detail_markup(mech) -> str:
    """Rich markup string: full component breakdown for inspect view."""
    from .data import LOC_SHORT, WEAPON_NAMES

    lines = []
    lines.append(
        f"[bold cyan]{'═' * WIDTH}[/]\n"
        f"  [bold cyan]{mech.callsign}  —  {mech.chassis}  "
        f"({mech.tonnage}t {mech.weight_class})[/]\n"
        f"[bold cyan]{'═' * WIDTH}[/]"
    )
    lines.append(f"  Pilot: [bold]{mech.pilot_name}[/]    Missions: {mech.missions_completed}")
    lines.append(f"  Status: {status_color(mech.overall_status)}")
    lines.append(f"\n  [bold]Component Status[/]\n  {'─' * WIDTH}")
    lines.append(f"  {'Location':<18} {'Sh':<4} {'Armor':<19} {'Structure':<19} Status")
    lines.append(f"  {'─' * WIDTH}")

    for loc_name, comp in mech.components.items():
        short = LOC_SHORT[loc_name]
        armor_bar  = bar(comp.armor,     comp.max_armor)
        struct_bar = bar(comp.structure, comp.max_structure)
        s = status_color(comp.status)
        lines.append(
            f"  {loc_name:<18} {short:<4} "
            f"{armor_bar} {comp.armor:>3}/{comp.max_armor:<3}  "
            f"{struct_bar} {comp.structure:>3}/{comp.max_structure:<3}  {s}"
        )
        for item in comp.equipment:
            if item in comp.destroyed_equipment:
                lines.append(f"    [red]✗ {item} [DESTROYED][/]")
            elif item in WEAPON_NAMES:
                lines.append(f"    [green]✓ {item}[/]")
            else:
                lines.append(f"    [dim]· {item}[/]")

    lines.append(f"\n  [bold]Working Weapons[/]\n  {'─' * WIDTH}")
    weapons = mech.working_weapons
    if weapons:
        for loc, wpn in weapons:
            lines.append(f"  [green]{LOC_SHORT[loc]}[/]: {wpn}")
    else:
        lines.append("  [bold red]NO OPERATIONAL WEAPONS[/]")

    return "\n".join(lines)
