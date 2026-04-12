"""Mech inspection screen — read-only detailed component view."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, ListView, ListItem, Label, Static
from textual.containers import Horizontal, Vertical, VerticalScroll

from ..ui import mech_overview_markup, mech_detail_markup


class InspectScreen(Screen):
    def __init__(self):
        super().__init__()
        self._selected = 0

    def compose(self) -> ComposeResult:
        gs = self.app.gs
        with Horizontal():
            with Vertical(style="width: 36"):
                yield Static("[bold cyan]INSPECT LANCE[/]", markup=True, classes="panel-header")
                lv = ListView(id="mech-list")
                yield lv
                yield Button("Back", id="back")
            with VerticalScroll(classes="detail-panel"):
                yield Static("", id="detail", markup=True)

    def on_mount(self) -> None:
        gs = self.app.gs
        lv = self.query_one("#mech-list", ListView)
        for m in gs.mechs:
            lv.append(ListItem(Label(mech_overview_markup(m), markup=True)))
        if gs.mechs:
            self._show_detail(0)

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if event.item is not None:
            idx = self.query_one("#mech-list", ListView).index
            if idx is not None:
                self._show_detail(idx)

    def _show_detail(self, idx: int) -> None:
        gs = self.app.gs
        if 0 <= idx < len(gs.mechs):
            self.query_one("#detail", Static).update(mech_detail_markup(gs.mechs[idx]))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
