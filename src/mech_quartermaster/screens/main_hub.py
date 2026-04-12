"""Main hub screen — central navigation and status display."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Static
from textual.containers import Horizontal, Vertical, VerticalScroll

from ..ui import mech_overview_markup


class MainHubScreen(Screen):

    def compose(self) -> ComposeResult:
        with Horizontal():
            with VerticalScroll(classes="content-panel", id="left-panel"):
                yield Static("", id="header-stats", markup=True)
                yield Static("", id="lance-overview", markup=True)
                yield Static("", id="narrative-box", markup=True)
                yield Static("", id="event-log", markup=True)
            with Vertical(classes="menu-panel"):
                yield Static("[bold]MAIN MENU[/]", markup=True, classes="section-title")
                yield Button("Inspect Lance",   id="inspect")
                yield Button("Repair",          id="repair")
                yield Button("Parts Inventory", id="parts")
                yield Button("Order Parts",     id="order")
                yield Button("Mech Market",     id="market")
                yield Button("Deploy Lance",    id="deploy")
                yield Button("End Day",         id="advance")
                yield Button("Quit",            id="quit", classes="-quit")

    def on_screen_resume(self) -> None:
        self._check_end_conditions()
        self._refresh()

    def on_mount(self) -> None:
        self._refresh()

    def _check_end_conditions(self) -> None:
        gs = self.app.gs
        if gs is None:
            return
        if gs.is_victorious:
            from .end_screens import VictoryScreen
            self.app.switch_screen(VictoryScreen())
        elif gs.is_bankrupt:
            from .end_screens import GameOverScreen
            self.app.switch_screen(
                GameOverScreen("You have run out of C-Bills. The company cannot pay its debts.")
            )
        elif gs.lance_destroyed:
            from .end_screens import GameOverScreen
            self.app.switch_screen(
                GameOverScreen("All mechs have been destroyed. The lance is no more.")
            )

    def _refresh(self) -> None:
        gs = self.app.gs
        if gs is None:
            return

        # ── Header stats ──────────────────────────────────────────────────────
        diff_color = {"Easy": "green", "Medium": "yellow", "Hard": "red"}.get(gs.difficulty, "white")
        cred_color = "red" if gs.inventory.credits < gs.weekly_overhead else "green"
        oh_color   = "red" if gs.days_until_overhead <= 2 else "yellow"
        missions_line = ""
        if gs.campaign.victory_missions is not None:
            missions_line = f"  Missions: [bold]{gs.missions_run}[/]/[bold]{gs.campaign.victory_missions}[/]  "

        header = (
            f"[bold cyan]══════════════════════════════════════════════════════════════════════[/]\n"
            f"  [bold]{gs.company_name}[/]   [{diff_color}]{gs.difficulty}[/]\n"
            f"  Day: [bold]{gs.day}[/]   "
            f"C-Bills: [bold][{cred_color}]{gs.inventory.credits:,}[/][/]   "
            f"Tech Hours: [bold]{gs.tech_hours_remaining}/{gs.tech_hours_per_day}[/]\n"
            f"  Overhead: [{oh_color}]{gs.weekly_overhead:,}c in {gs.days_until_overhead}d[/]   "
            f"[dim]({gs.overhead_breakdown})[/]\n"
            f"{missions_line}"
            f"[bold cyan]══════════════════════════════════════════════════════════════════════[/]"
        )
        self.query_one("#header-stats", Static).update(header)

        # ── Narrative ─────────────────────────────────────────────────────────
        if gs.pending_narrative:
            narr = "\n".join(
                f"[yellow]  ▶ {line}[/]" for block in gs.pending_narrative for line in block.split("\n")
            )
            self.query_one("#narrative-box", Static).update(
                f"[bold yellow]  INCOMING TRANSMISSION[/]\n{narr}"
            )
            gs.pending_narrative.clear()
        else:
            self.query_one("#narrative-box", Static).update("")

        # ── Lance overview ────────────────────────────────────────────────────
        if gs.mechs:
            lines = ["  [bold]Lance Status[/]", "  [dim]──────────────────────────────────────────[/]"]
            for m in gs.mechs:
                lines.append("  " + mech_overview_markup(m))
        else:
            lines = ["  [bold red]LANCE EMPTY — purchase mechs from the market.[/]"]
        self.query_one("#lance-overview", Static).update("\n".join(lines))

        # ── Event log ─────────────────────────────────────────────────────────
        recent = gs.event_log[-5:] if gs.event_log else []
        if recent:
            log_lines = ["  [bold]Recent Activity[/]", "  [dim]──────────────────────────────────────────[/]"]
            for entry in recent:
                log_lines.append(f"  [dim]{entry}[/]")
            self.query_one("#event-log", Static).update("\n".join(log_lines))
        else:
            self.query_one("#event-log", Static).update("")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        action = event.button.id
        if action == "quit":
            self.app.exit()
            return
        if action == "advance":
            gs = self.app.gs
            arrivals, overhead_msgs = gs.advance_day()
            from .advance import AdvanceScreen
            self.app.push_screen(AdvanceScreen(arrivals, overhead_msgs, gs.day))
            return

        screen_map = {
            "inspect": ("inspect",  lambda: __import__("mech_quartermaster.screens.inspect",  fromlist=["InspectScreen"]).InspectScreen()),
            "repair":  ("repair",   lambda: __import__("mech_quartermaster.screens.repair",   fromlist=["RepairScreen"]).RepairScreen()),
            "parts":   ("parts",    lambda: __import__("mech_quartermaster.screens.parts",    fromlist=["PartsScreen"]).PartsScreen()),
            "order":   ("order",    lambda: __import__("mech_quartermaster.screens.order",    fromlist=["OrderScreen"]).OrderScreen()),
            "market":  ("market",   lambda: __import__("mech_quartermaster.screens.market",   fromlist=["MarketScreen"]).MarketScreen()),
            "deploy":  ("deploy",   lambda: __import__("mech_quartermaster.screens.deploy",   fromlist=["DeployScreen"]).DeployScreen()),
        }
        if action in screen_map:
            _, factory = screen_map[action]
            self.app.push_screen(factory())
