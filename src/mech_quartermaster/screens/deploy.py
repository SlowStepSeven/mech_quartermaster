"""Deploy screen — 4-step mission wizard using ContentSwitcher."""

import random
from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import (
    Button, ContentSwitcher, DataTable, Label, SelectionList,
    Static, ListItem, ListView,
)
from textual.widgets.selection_list import Selection
from textual.containers import Horizontal, Vertical, VerticalScroll, ScrollableContainer
from rich.text import Text

from ..game import (
    BATTLE_ORDERS, MAX_DEPLOYED, PILOT_NAMES, CALLSIGNS,
    _mech_sell_price, _run_mission, _new_callsign_pilot,
)
from ..data import CHASSIS_DATA, MECH_PRICES
from ..mech import Mech
from ..ui import mech_overview_markup, bar, status_text


# ── Forced-sell modal (reused if salvage fills roster) ────────────────────────

class ForcedSellModal(ModalScreen[None]):
    def __init__(self, incoming: str):
        super().__init__()
        self._incoming = incoming

    def compose(self) -> ComposeResult:
        gs = self.app.gs
        self._offers = {m.callsign: _mech_sell_price(m) for m in gs.mechs}
        with Vertical(classes="modal-dialog"):
            yield Static(
                f"[bold red]ROSTER FULL — SELL A MECH[/]\nIncoming: [yellow]{self._incoming}[/]",
                markup=True, classes="modal-title",
            )
            tbl = DataTable(id="sell-tbl", cursor_type="row")
            yield tbl
            yield Button("Sell Selected", id="sell")

    def on_mount(self) -> None:
        gs = self.app.gs
        tbl = self.query_one("#sell-tbl", DataTable)
        tbl.add_column("Callsign", width=12)
        tbl.add_column("Chassis",  width=24)
        tbl.add_column("Status",   width=16)
        tbl.add_column("Offer",    width=14)
        for m in gs.mechs:
            tbl.add_row(
                Text(m.callsign), Text(m.chassis),
                status_text(m.overall_status),
                Text(f"{self._offers[m.callsign]:,}c", style="yellow"),
            )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "sell":
            return
        gs = self.app.gs
        tbl = self.query_one("#sell-tbl", DataTable)
        row = tbl.cursor_row
        if 0 <= row < len(gs.mechs):
            mech  = gs.mechs[row]
            offer = self._offers[mech.callsign]
            gs.inventory.credits += offer
            gs.mechs.remove(mech)
            gs.event_log.append(
                f"Day {gs.day}: Sold {mech.callsign} ({mech.chassis}) for {offer:,}c (roster cap)"
            )
            self.dismiss(None)


# ── Main deploy screen ────────────────────────────────────────────────────────

class DeployScreen(Screen):
    def __init__(self):
        super().__init__()
        self._step: int = 0
        self._contract: dict | None = None
        self._lance: list[Mech] = []
        self._order: dict | None = None
        self._all_ready: list[Mech] = []
        self._aar_lines: list[str] = []
        self._level_up_msg: str = ""

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("", id="step-header", markup=True, classes="panel-header")
            with ContentSwitcher(initial="step0", id="switcher"):
                # Step 0 — Contract selection
                with Vertical(id="step0"):
                    yield Static("", id="readiness", markup=True)
                    yield Static("[bold]Available Contracts[/]", markup=True, classes="section-title")
                    yield DataTable(id="contract-table", cursor_type="row")
                    with Horizontal():
                        yield Button("Select Contract →", id="select-contract", classes="-deploy")
                        yield Button("Cancel",            id="cancel0", classes="-danger")

                # Step 1 — Lance selection (shown only when > MAX_DEPLOYED ready)
                with Vertical(id="step1"):
                    yield Static("", id="lance-context", markup=True)
                    yield Static(
                        f"  [bold]Select Lance[/]  [dim](choose up to {MAX_DEPLOYED})[/]",
                        markup=True, classes="section-title",
                    )
                    yield SelectionList(id="lance-list")
                    with Horizontal():
                        yield Button("Confirm Lance →", id="confirm-lance", classes="-deploy")
                        yield Button("← Back",         id="back1")

                # Step 2 — Battle orders
                with Vertical(id="step2"):
                    yield Static("", id="order-context", markup=True)
                    yield Static("[bold]Select Battle Orders[/]", markup=True, classes="section-title")
                    for i, order in enumerate(BATTLE_ORDERS):
                        yield Button(
                            f"{order['name']}  |  {order['effects']}\n  {order['description']}",
                            id=f"order_{i}",
                        )
                    yield Button("← Back", id="back2")

                # Step 3 — AAR
                with Vertical(id="step3"):
                    yield Static("", id="aar-header", markup=True)
                    with ScrollableContainer(classes="aar-log"):
                        yield Static("", id="aar-body", markup=True)
                    yield Button("Return to Command", id="done", classes="-deploy")

    # ── Mount ────────────────────────────────────────────────────────────────

    def on_mount(self) -> None:
        gs = self.app.gs
        self._all_ready = [m for m in gs.mechs if m.is_combat_ready]
        self._build_step0()
        self._show_step(0)

    # ── Step builders ────────────────────────────────────────────────────────

    def _build_step0(self) -> None:
        gs = self.app.gs
        not_ready = [m for m in gs.mechs if not m.is_combat_ready]

        lines = []
        if not_ready:
            lines.append(
                f"  [yellow]⚠ {len(not_ready)} mech(s) non-operational and will not deploy.[/]"
            )
        for m in gs.mechs:
            lines.append("  " + mech_overview_markup(m))
        self.query_one("#readiness", Static).update("\n".join(lines))

        # Contract table
        tbl = self.query_one("#contract-table", DataTable)
        tbl.clear()
        if not tbl.columns:
            tbl.add_column("Mission",    key="name",    width=14)
            tbl.add_column("Level",      key="lvl",     width=8)
            tbl.add_column("Pay (min)",  key="pay",     width=16)
            tbl.add_column("Damage",     key="dmg",     width=8)
            tbl.add_column("Salvage",    key="salv",    width=8)
            tbl.add_column("Description", key="desc",   width=34)

        final = gs.campaign.final_mission
        vm    = gs.campaign.victory_missions
        is_final = (final is not None and vm is not None and gs.missions_run == vm - 1)
        self._available = [final] if is_final else gs.daily_missions

        for mt in self._available:
            level     = gs.mission_level(mt["name"])
            pay_mult  = 1.35 ** (level - 1)
            dmg_mult  = 1.20 ** (level - 1)
            min_pay, _ = mt["c_bill_reward"]
            lvl_style = "dim" if level == 1 else ("yellow" if level <= 3 else "red")
            lvl_label = f"LVL {level}" + ("" if level == 1 else " ▲" if level <= 3 else " ▲▲")
            tbl.add_row(
                Text(mt["name"], style="bold"),
                Text(lvl_label,  style=lvl_style),
                Text(f"{int(min_pay * pay_mult):,}c", style="green"),
                bar(int(10 - dmg_mult * mt["damage_scale"] * 5), 10, width=6, as_text=True),
                bar(int(mt["salvage_scale"] * 2), 10, width=6, as_text=True),
                Text(mt["description"], style="dim"),
            )

    def _build_step1(self) -> None:
        gs = self.app.gs
        self.query_one("#lance-context", Static).update(
            f"  Contract: [bold]{self._contract['name']}[/]"
        )
        sl = self.query_one("#lance-list", SelectionList)
        sl.clear_options()
        cb = self._contract.get("class_bonus", {})
        for i, m in enumerate(self._all_ready):
            bonus = int(cb.get(m.weight_class, 0) * 100)
            label = (
                f"{m.callsign:<12} {m.chassis:<22} {m.weight_class:<8} "
                f"[dim]+{bonus}% bonus[/]"
            )
            sl.add_option(Selection(label, i, initial_state=False))

    def _build_step2(self) -> None:
        lance_str = ", ".join(m.callsign for m in self._lance)
        self.query_one("#order-context", Static).update(
            f"  Contract: [bold]{self._contract['name']}[/]   "
            f"Lance: [dim]{lance_str}[/]"
        )

    # ── Navigation ────────────────────────────────────────────────────────────

    def _show_step(self, step: int) -> None:
        self._step = step
        self.query_one("#switcher", ContentSwitcher).current = f"step{step}"
        headers = [
            "DEPLOY — Step 1: Select Contract",
            "DEPLOY — Step 2: Select Lance",
            "DEPLOY — Step 3: Battle Orders",
            "DEPLOY — After Action Report",
        ]
        self.query_one("#step-header", Static).update(f"[bold cyan]{headers[step]}[/]")

    # ── Button handler ────────────────────────────────────────────────────────

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id

        # ── Step 0 ──────────────────────────────────────────────────────────
        if bid == "cancel0":
            self.app.pop_screen()
            return

        if bid == "select-contract":
            tbl = self.query_one("#contract-table", DataTable)
            row = tbl.cursor_row
            if row < 0 or row >= len(self._available):
                return
            self._contract = self._available[row]
            if not self._all_ready:
                return
            # Skip lance selection if at or under cap
            if len(self._all_ready) <= MAX_DEPLOYED:
                self._lance = list(self._all_ready)
                self._build_step2()
                self._show_step(2)
            else:
                self._build_step1()
                self._show_step(1)
            return

        # ── Step 1 ──────────────────────────────────────────────────────────
        if bid == "back1":
            self._show_step(0)
            return

        if bid == "confirm-lance":
            sl = self.query_one("#lance-list", SelectionList)
            selected_values = sl.selected
            if not selected_values or len(selected_values) > MAX_DEPLOYED:
                return
            self._lance = [self._all_ready[v] for v in selected_values]
            self._build_step2()
            self._show_step(2)
            return

        # ── Step 2 ──────────────────────────────────────────────────────────
        if bid == "back2":
            if len(self._all_ready) <= MAX_DEPLOYED:
                self._show_step(0)
            else:
                self._show_step(1)
            return

        if bid and bid.startswith("order_"):
            oidx = int(bid.split("_")[1])
            self._order = BATTLE_ORDERS[oidx]
            await self._execute_mission()
            return

        # ── Step 3 ──────────────────────────────────────────────────────────
        if bid == "done":
            self.app.pop_screen()

    # ── Mission execution ─────────────────────────────────────────────────────

    async def _execute_mission(self) -> None:
        gs = self.app.gs
        mt       = self._contract
        lance    = self._lance
        order    = self._order
        old_level = gs.mission_level(mt["name"])

        result, new_level = _run_mission(gs, mt, lance, order)

        # Handle salvage
        salvage = result.get("salvage", {})
        salvage_parts = salvage.get("parts", {})
        salvaged_chassis = salvage.get("mech")

        if salvage_parts:
            for part, qty in salvage_parts.items():
                gs.inventory.add_parts(part, qty)
            gs.event_log.append(
                "Day {}: Salvage recovered — {}".format(
                    gs.day, ", ".join(f"{q}x {p}" for p, q in salvage_parts.items())
                )
            )

        if salvaged_chassis:
            if len(gs.mechs) >= __import__("mech_quartermaster.game", fromlist=["MAX_MECHS"]).MAX_MECHS:
                await self.app.push_screen_wait(ForcedSellModal(salvaged_chassis))
            callsign, pilot = _new_callsign_pilot(gs)
            wreck = Mech(chassis=salvaged_chassis, pilot_name=pilot, callsign=callsign)
            for comp in wreck.components.values():
                comp.armor = 0
                comp.structure = max(1, int(comp.max_structure * random.uniform(0.30, 0.55)))
                for item in list(comp.equipment):
                    if random.random() < 0.5:
                        comp.destroyed_equipment.append(item)
            gs.mechs.append(wreck)
            gs.mechs.sort(key=lambda m: m.tonnage)
            gs.event_log.append(
                f"Day {gs.day}: Salvaged mech wreck — {salvaged_chassis} '{callsign}'"
            )

        # Advance day
        arrivals, overhead_msgs = gs.advance_day()

        # Build AAR
        lines = []
        lines.append(
            f"[bold]Orders:[/] {order['name']}  [dim]({order['effects']})[/]"
        )
        lines.append("")
        for line in result["events"]:
            if "MISSION SUCCESS" in line:
                lines.append(f"[bold green]{line}[/]")
            elif "MISSION FAILED" in line:
                lines.append(f"[bold red]{line}[/]")
            elif "CRITICAL" in line or "DESTROYED" in line:
                lines.append(f"[red]{line}[/]")
            elif "armor breached" in line:
                lines.append(f"[yellow]{line}[/]")
            else:
                lines.append(line)

        cred_color = "green" if result["success"] else "red"
        lines.append("")
        lines.append(
            f"[{cred_color}]Payment: {result['rewards']:,} C-Bills[/]   "
            f"Balance: {gs.inventory.credits:,}c"
        )

        if result.get("casualties"):
            lines.append(f"[yellow]Non-operational: {', '.join(result['casualties'])}[/]")

        if salvage_parts:
            lines.append(
                "[cyan]Salvage: " + ", ".join(f"{q}x {p}" for p, q in salvage_parts.items()) + "[/]"
            )
        if salvaged_chassis:
            lines.append(f"[cyan]Salvaged wreck: {salvaged_chassis} '{callsign}'[/]")

        if new_level > old_level:
            lines.append("")
            lines.append(
                f"[bold yellow]CONTRACT DIFFICULTY UP — {mt['name']} is now LVL {new_level}! "
                f"(+20% damage / +35% pay)[/]"
            )

        if arrivals:
            lines.append("")
            for msg in arrivals:
                lines.append(f"[green]  ✓ {msg}[/]")
        if overhead_msgs:
            for msg in overhead_msgs:
                lines.append(f"[yellow]  ⚠ {msg}[/]")

        aar_header = (
            f"[bold cyan]AFTER ACTION REPORT — {mt['name'].upper()}[/]\n"
            f"[dim]Day {gs.day - 1} → Day {gs.day}[/]"
        )
        self.query_one("#aar-header", Static).update(aar_header)
        self.query_one("#aar-body", Static).update("\n".join(lines))
        self._show_step(3)
