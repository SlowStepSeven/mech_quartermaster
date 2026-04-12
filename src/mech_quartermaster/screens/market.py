"""Mech market screen — buy and sell mechs."""

import random
from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import Button, DataTable, Static
from textual.containers import Horizontal, Vertical
from rich.text import Text

from ..game import (
    PILOT_NAMES, CALLSIGNS, MAX_MECHS,
    _mech_sell_price, _new_callsign_pilot,
)
from ..data import CHASSIS_DATA, MECH_PRICES
from ..mech import Mech
from ..ui import status_text


class ConfirmModal(ModalScreen[bool]):
    def __init__(self, message: str):
        super().__init__()
        self._message = message

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Static(self._message, markup=True, classes="modal-title")
            with Horizontal(classes="modal-buttons"):
                yield Button("Yes", id="yes")
                yield Button("No",  id="no", classes="-danger")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "yes")


class ForcedSellModal(ModalScreen[int]):
    """Must sell one mech before a new one can be added."""
    def __init__(self, incoming: str):
        super().__init__()
        self._incoming = incoming

    def compose(self) -> ComposeResult:
        gs = self.app.gs
        self._offers = {m.callsign: _mech_sell_price(m) for m in gs.mechs}
        with Vertical(classes="modal-dialog"):
            yield Static(
                f"[bold red]ROSTER FULL — SELL A MECH[/]\n"
                f"Incoming: [yellow]{self._incoming}[/]",
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
        tbl.add_column("Status",   width=18)
        tbl.add_column("Offer",    width=14)
        for m in gs.mechs:
            tbl.add_row(
                Text(m.callsign),
                Text(m.chassis),
                status_text(m.overall_status),
                Text(f"{self._offers[m.callsign]:,}c", style="yellow"),
            )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "sell":
            return
        gs = self.app.gs
        tbl = self.query_one("#sell-tbl", DataTable)
        row = tbl.cursor_row
        if row < 0 or row >= len(gs.mechs):
            return
        mech = gs.mechs[row]
        offer = self._offers[mech.callsign]
        confirmed = await self.app.push_screen_wait(
            ConfirmModal(f"Sell [bold]{mech.callsign}[/] ([dim]{mech.chassis}[/]) for [green]{offer:,}c[/]?")
        )
        if confirmed:
            gs.inventory.credits += offer
            gs.mechs.remove(mech)
            gs.event_log.append(f"Day {gs.day}: Sold {mech.callsign} ({mech.chassis}) for {offer:,}c")
            self.dismiss(row)


class MarketScreen(Screen):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("", id="market-header", markup=True, classes="panel-header")
            with Horizontal():
                with Vertical():
                    yield Static("[bold]Available Mechs[/]", markup=True, classes="section-title")
                    yield DataTable(id="buy-table", cursor_type="row")
                    yield Button("Buy Selected", id="buy")
                with Vertical():
                    yield Static("[bold]Sell a Mech[/]", markup=True, classes="section-title")
                    yield DataTable(id="sell-table", cursor_type="row")
                    yield Button("Sell Selected", id="sell")
            yield Button("Back", id="back")
            yield Static("", id="status-line", markup=True)

    def on_mount(self) -> None:
        bt = self.query_one("#buy-table", DataTable)
        bt.add_column("Chassis",   key="chassis", width=24)
        bt.add_column("Class",     key="class",   width=8)
        bt.add_column("Tons",      key="tons",    width=5)
        bt.add_column("Condition", key="cond",    width=12)
        bt.add_column("Price",     key="price",   width=16)

        st = self.query_one("#sell-table", DataTable)
        st.add_column("Callsign", key="call",   width=12)
        st.add_column("Chassis",  key="chassis", width=24)
        st.add_column("Status",   key="status",  width=18)
        st.add_column("Offer",    key="offer",   width=14)

        self._rebuild()

    def _rebuild(self) -> None:
        gs = self.app.gs
        if not gs.market:
            gs._refresh_market()
        days_left = 7 - ((gs.day - gs.market_refresh_day) % 7)
        self.query_one("#market-header", Static).update(
            f"[bold]MECH MARKET[/]   C-Bills: [bold green]{gs.inventory.credits:,}[/]   "
            f"[dim]Market refreshes in {days_left} day(s)[/]"
        )

        bt = self.query_one("#buy-table", DataTable)
        bt.clear()
        for listing in gs.market:
            data = CHASSIS_DATA[listing["chassis"]]
            cond = listing["condition"]
            cond_style = {"Pristine": "green", "Used": "yellow", "Battle-Worn": "red"}.get(cond, "")
            bt.add_row(
                Text(listing["chassis"]),
                Text(data["class"]),
                Text(str(data["tonnage"])),
                Text(cond, style=cond_style),
                Text(f"{listing['price']:,}c", style="yellow"),
            )

        st = self.query_one("#sell-table", DataTable)
        st.clear()
        self._sell_offers = {m.callsign: _mech_sell_price(m) for m in gs.mechs}
        for m in gs.mechs:
            st.add_row(
                Text(m.callsign),
                Text(m.chassis),
                status_text(m.overall_status),
                Text(f"{self._sell_offers[m.callsign]:,}c", style="yellow"),
            )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
            return
        if event.button.id == "buy":
            await self._do_buy()
        elif event.button.id == "sell":
            await self._do_sell()

    async def _do_buy(self) -> None:
        gs = self.app.gs
        tbl = self.query_one("#buy-table", DataTable)
        row = tbl.cursor_row
        if row < 0 or row >= len(gs.market):
            self.query_one("#status-line", Static).update("[yellow]Select a mech to buy.[/]")
            return

        listing = gs.market[row]
        price   = listing["price"]
        chassis = listing["chassis"]

        if price > gs.inventory.credits:
            self.query_one("#status-line", Static).update(
                f"[red]Insufficient funds ({price:,}c needed).[/]"
            )
            return

        confirmed = await self.app.push_screen_wait(
            ConfirmModal(f"Buy [bold]{chassis}[/] for [green]{price:,}c[/]?")
        )
        if not confirmed:
            return

        # Handle roster cap
        if len(gs.mechs) >= MAX_MECHS:
            await self.app.push_screen_wait(ForcedSellModal(chassis))

        callsign, pilot = _new_callsign_pilot(gs)
        new_mech = Mech(chassis=chassis, pilot_name=pilot, callsign=callsign)

        if listing["damage_pct"] > 0:
            for comp in new_mech.components.values():
                armor_loss = int(comp.max_armor * listing["damage_pct"] * random.uniform(0.5, 1.5))
                comp.armor = max(0, comp.max_armor - min(armor_loss, comp.max_armor))

        gs.inventory.credits -= price
        gs.market.pop(row)
        gs.mechs.append(new_mech)
        gs.mechs.sort(key=lambda m: m.tonnage)
        gs.event_log.append(f"Day {gs.day}: Purchased {chassis} '{callsign}' for {price:,}c")

        self.query_one("#status-line", Static).update(
            f"[green]✓ Purchased {chassis} — callsign '{callsign}', pilot {pilot}[/]"
        )
        self._rebuild()

    async def _do_sell(self) -> None:
        gs = self.app.gs
        tbl = self.query_one("#sell-table", DataTable)
        row = tbl.cursor_row
        if row < 0 or row >= len(gs.mechs):
            self.query_one("#status-line", Static).update("[yellow]Select a mech to sell.[/]")
            return

        mech  = gs.mechs[row]
        offer = self._sell_offers[mech.callsign]

        if len(gs.mechs) == 1:
            self.query_one("#status-line", Static).update(
                "[red]Cannot sell your last mech.[/]"
            )
            return

        confirmed = await self.app.push_screen_wait(
            ConfirmModal(
                f"Sell [bold]{mech.callsign}[/] ([dim]{mech.chassis}[/]) for [green]{offer:,}c[/]?"
            )
        )
        if confirmed:
            gs.inventory.credits += offer
            gs.mechs.remove(mech)
            gs.event_log.append(f"Day {gs.day}: Sold {mech.callsign} ({mech.chassis}) for {offer:,}c")
            self.query_one("#status-line", Static).update(
                f"[green]✓ Sold {mech.callsign} for {offer:,}c[/]"
            )
            self._rebuild()
