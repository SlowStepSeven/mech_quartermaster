"""Repair screen — select mech, apply repair jobs."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, DataTable, ListView, ListItem, Label, Static
from textual.containers import Horizontal, Vertical
from rich.text import Text

from ..game import _do_repair, _repair_jobs
from ..ui import mech_overview_markup, status_text


class RepairScreen(Screen):
    def __init__(self):
        super().__init__()
        self._selected_mech_idx: int | None = None
        self._current_jobs: list[dict] = []

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("", id="tech-header", markup=True, classes="panel-header")
            with Horizontal():
                with Vertical(classes="mech-list-panel"):
                    yield Static("[bold]Select Mech[/]", markup=True, classes="section-title")
                    yield ListView(id="mech-list")
                with Vertical():
                    yield Static("[bold]Repair Jobs[/]", markup=True, classes="section-title")
                    yield DataTable(id="jobs-table", cursor_type="row")
                    with Horizontal(classes="modal-buttons"):
                        yield Button("Repair Selected", id="repair-one")
                        yield Button("Repair All",      id="repair-all")
                        yield Button("Back",            id="back", classes="-danger")
            yield Static("", id="status-line", markup=True)

    def on_mount(self) -> None:
        gs = self.app.gs
        lv = self.query_one("#mech-list", ListView)
        for m in gs.mechs:
            lv.append(ListItem(Label(mech_overview_markup(m), markup=True)))

        tbl = self.query_one("#jobs-table", DataTable)
        tbl.add_column("Job",       key="label", width=32)
        tbl.add_column("Part",      key="part",  width=28)
        tbl.add_column("Stock",     key="stock", width=6)
        tbl.add_column("Hours",     key="hours", width=6)

        self._update_tech_header()

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        idx = self.query_one("#mech-list", ListView).index
        if idx is not None:
            self._selected_mech_idx = idx
            self._rebuild_jobs_table()

    def _update_tech_header(self) -> None:
        gs = self.app.gs
        self.query_one("#tech-header", Static).update(
            f"[bold]REPAIR MECH[/]   Tech Hours: [bold]{gs.tech_hours_remaining}/{gs.tech_hours_per_day}[/]"
        )

    def _rebuild_jobs_table(self) -> None:
        gs = self.app.gs
        idx = self._selected_mech_idx
        tbl = self.query_one("#jobs-table", DataTable)
        tbl.clear()

        if idx is None or idx >= len(gs.mechs):
            self._current_jobs = []
            return

        mech = gs.mechs[idx]
        self._current_jobs = _repair_jobs(mech)

        for job in self._current_jobs:
            stock = gs.inventory.stock(job["part"])
            can_do = stock >= 1 and gs.tech_hours_remaining >= job["hours"]
            style = "" if can_do else "dim red"
            tbl.add_row(
                Text(job["label"], style=style),
                Text(job["part"],  style=style),
                Text(str(stock),   style="green" if stock > 0 else "red"),
                Text(str(job["hours"]) + "h", style="green" if gs.tech_hours_remaining >= job["hours"] else "red"),
            )

    def _do_selected(self) -> None:
        gs = self.app.gs
        idx = self._selected_mech_idx
        if idx is None or idx >= len(gs.mechs):
            return
        tbl = self.query_one("#jobs-table", DataTable)
        row = tbl.cursor_row
        if row < len(self._current_jobs):
            job = self._current_jobs[row]
            ok = _do_repair(gs, gs.mechs[idx], job)
            msg = f"[green]✓ {job['label']} — done[/]" if ok else "[red]✗ Cannot repair (check parts/hours)[/]"
            self.query_one("#status-line", Static).update(msg)
            self._update_tech_header()
            self._rebuild_jobs_table()

    def _do_all(self) -> None:
        gs = self.app.gs
        idx = self._selected_mech_idx
        if idx is None or idx >= len(gs.mechs):
            return
        mech = gs.mechs[idx]
        done = 0
        for job in list(self._current_jobs):
            if _do_repair(gs, mech, job):
                done += 1
        self.query_one("#status-line", Static).update(
            f"[green]✓ {done} repair(s) completed[/]" if done else "[yellow]No repairs possible[/]"
        )
        self._update_tech_header()
        self._rebuild_jobs_table()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
        elif event.button.id == "repair-one":
            self._do_selected()
        elif event.button.id == "repair-all":
            self._do_all()
