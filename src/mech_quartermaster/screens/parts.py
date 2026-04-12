"""Parts inventory screen — view stock, sell parts, track orders."""

from textual.app import ComposeResult
from textual.screen import Screen, ModalScreen
from textual.widgets import Button, DataTable, Input, Label, Static
from textual.containers import Horizontal, Vertical
from rich.text import Text

from textual import work
from ..game import _part_sell_price
from ..data import PARTS_CATALOG


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


class PartsScreen(Screen):
    def __init__(self):
        super().__init__()
        self._offers: dict[str, int] = {}
        self._part_names: list[str] = []

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("", id="cred-header", markup=True, classes="panel-header")
            with Vertical(classes="fill-height"):
                yield Static("[bold]In Stock[/]", markup=True, classes="section-title")
                yield DataTable(id="stock-table", cursor_type="row")
                yield Static("[bold]Pending Orders[/]", markup=True, classes="section-title")
                yield DataTable(id="orders-table", cursor_type="none")
            with Horizontal():
                yield Input(placeholder="Quantity to sell", id="qty-input")
                yield Button("Sell Selected", id="sell")
            yield Button("Back", id="back")
            yield Static("", id="status-line", markup=True)

    def on_mount(self) -> None:
        st = self.query_one("#stock-table", DataTable)
        st.add_column("Part",      key="part",  width=34)
        st.add_column("Qty",       key="qty",   width=5)
        st.add_column("Sell/ea",   key="price", width=12)

        ot = self.query_one("#orders-table", DataTable)
        ot.add_column("Part",      key="part",  width=34)
        ot.add_column("Qty",       key="qty",   width=5)
        ot.add_column("Arrives",   key="day",   width=10)

        self._rebuild()

    def _rebuild(self) -> None:
        gs = self.app.gs
        self.query_one("#cred-header", Static).update(
            f"[bold]PARTS INVENTORY[/]   C-Bills: [bold green]{gs.inventory.credits:,}[/]"
        )

        st = self.query_one("#stock-table", DataTable)
        st.clear()
        self._part_names = list(gs.inventory.parts.keys())
        self._offers = {name: _part_sell_price(name) for name in self._part_names}
        for name in self._part_names:
            qty   = gs.inventory.parts[name]
            price = self._offers[name]
            st.add_row(
                Text(name),
                Text(str(qty),     style="green"),
                Text(f"{price:,}c", style="yellow"),
            )

        ot = self.query_one("#orders-table", DataTable)
        ot.clear()
        for order in gs.inventory.pending_orders:
            ot.add_row(
                Text(order["part"]),
                Text(str(order["qty"])),
                Text(f"Day {order['arrive_day']}"),
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "sell":
            self._do_sell()

    @work
    async def _do_sell(self) -> None:
        gs = self.app.gs
        tbl = self.query_one("#stock-table", DataTable)
        row = tbl.cursor_row
        if row < 0 or row >= len(self._part_names):
            self.query_one("#status-line", Static).update("[yellow]Select a part first.[/]")
            return

        qty_str = self.query_one("#qty-input", Input).value.strip()
        try:
            qty = int(qty_str)
            if qty <= 0:
                raise ValueError
        except ValueError:
            self.query_one("#status-line", Static).update("[red]Enter a valid quantity.[/]")
            return

        name     = self._part_names[row]
        in_stock = gs.inventory.parts.get(name, 0)
        if qty > in_stock:
            self.query_one("#status-line", Static).update(
                f"[red]Only {in_stock} in stock.[/]"
            )
            return

        price = self._offers[name]
        total = price * qty
        confirmed = await self.app.push_screen_wait(
            ConfirmModal(f"Sell [bold]{qty}x {name}[/] for [green]{total:,}c[/]?")
        )
        if confirmed:
            gs.inventory.use_part(name, qty)
            gs.inventory.credits += total
            gs.event_log.append(f"Day {gs.day}: Sold {qty}x {name} for {total:,}c")
            self.query_one("#status-line", Static).update(
                f"[green]✓ Sold {qty}x {name} for {total:,}c[/]"
            )
            self.call_after_refresh(self._rebuild)
