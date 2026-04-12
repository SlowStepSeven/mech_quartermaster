"""Order parts screen — browse catalog and place purchase orders."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, DataTable, Input, Static
from textual.containers import Horizontal, Vertical
from rich.text import Text

from ..data import PARTS_CATALOG, WEAPON_NAMES


_CATALOG_ITEMS = list(PARTS_CATALOG.items())  # [(name, (cost, hours, desc)), ...]


class OrderScreen(Screen):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("", id="cred-header", markup=True, classes="panel-header")
            yield Static(
                "  [dim]Orders arrive in 1–4 days depending on part type.[/]",
                markup=True,
            )
            yield DataTable(id="catalog", cursor_type="row")
            with Horizontal():
                yield Input(placeholder="Quantity", id="qty-input")
                yield Button("Place Order", id="order")
                yield Button("Back",        id="back")
            yield Static("", id="status-line", markup=True)

    def on_mount(self) -> None:
        tbl = self.query_one("#catalog", DataTable)
        tbl.add_column("Part",        key="part",  width=34)
        tbl.add_column("Cost",        key="cost",  width=12)
        tbl.add_column("Repair hrs",  key="hours", width=10)
        tbl.add_column("Description", key="desc",  width=36)

        for name, (cost, hours, desc) in _CATALOG_ITEMS:
            tbl.add_row(
                Text(name),
                Text(f"{cost:,}c",  style="yellow"),
                Text(f"{hours}h",   style="cyan"),
                Text(desc,          style="dim"),
            )
        self._update_header()

    def _update_header(self) -> None:
        gs = self.app.gs
        self.query_one("#cred-header", Static).update(
            f"[bold]ORDER PARTS[/]   C-Bills: [bold green]{gs.inventory.credits:,}[/]"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
            return
        if event.button.id != "order":
            return

        gs = self.app.gs
        tbl = self.query_one("#catalog", DataTable)
        row = tbl.cursor_row
        if row < 0 or row >= len(_CATALOG_ITEMS):
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

        name, (cost, hours, _) = _CATALOG_ITEMS[row]
        total = cost * qty
        if total > gs.inventory.credits:
            self.query_one("#status-line", Static).update(
                f"[red]Insufficient funds ({total:,}c needed, {gs.inventory.credits:,}c available).[/]"
            )
            return

        # Delivery time: weapons and structure parts take longer
        import random
        if name in WEAPON_NAMES or "Structure" in name:
            arrive_days = random.randint(2, 4)
        else:
            arrive_days = random.randint(1, 2)

        gs.inventory.credits -= total
        gs.inventory.pending_orders.append({
            "part": name, "qty": qty, "arrive_day": gs.day + arrive_days
        })
        gs.event_log.append(
            f"Day {gs.day}: Ordered {qty}x {name} ({total:,}c) — arrives Day {gs.day + arrive_days}"
        )
        self.query_one("#status-line", Static).update(
            f"[green]✓ Ordered {qty}x {name} for {total:,}c — arrives Day {gs.day + arrive_days}[/]"
        )
        self.query_one("#qty-input", Input).value = ""
        self._update_header()
