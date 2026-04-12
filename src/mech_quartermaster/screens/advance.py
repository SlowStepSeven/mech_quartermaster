"""End-of-day modal — shows arrivals and overhead after advance_day()."""

from textual.app import ComposeResult
from textual.screen import ModalScreen
from textual.widgets import Button, Static
from textual.containers import Vertical


class AdvanceScreen(ModalScreen):
    def __init__(self, arrivals: list[str], overhead_msgs: list[str], day: int):
        super().__init__()
        self._arrivals = arrivals
        self._overhead = overhead_msgs
        self._day = day

    def compose(self) -> ComposeResult:
        lines = [f"[bold cyan]END OF DAY — Day {self._day} begins[/]\n"]
        if self._arrivals:
            for msg in self._arrivals:
                lines.append(f"[green]  ✓ {msg}[/]")
        if self._overhead:
            for msg in self._overhead:
                lines.append(f"[yellow]  ⚠ {msg}[/]")
        if not self._arrivals and not self._overhead:
            lines.append("[dim]  No overnight events.[/]")

        with Vertical(classes="modal-dialog"):
            yield Static("\n".join(lines), markup=True)
            yield Button("Continue", id="continue")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "continue":
            self.app.pop_screen()
