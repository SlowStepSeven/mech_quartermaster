"""Campaign selection screen."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Static
from textual.containers import Vertical

from ..campaigns import ALL_CAMPAIGNS


class CampaignSelectScreen(Screen):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(
                "[bold cyan]══════════════════════════════════════════════════════════════════════[/]\n"
                "  [bold cyan]MECHBAY OPERATIONS — IRON LANCE[/]\n"
                "[bold cyan]══════════════════════════════════════════════════════════════════════[/]",
                markup=True,
            )
            yield Static("  [bold]Select Campaign[/]\n  [dim]──────────────────────────────────────────[/]",
                         markup=True)
            for i, camp in enumerate(ALL_CAMPAIGNS):
                yield Button(
                    f"{camp.name}  —  {camp.description}",
                    id=f"camp_{i}",
                )
            yield Static("")
            yield Button("Quit", id="quit", classes="-quit")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.app.exit()
            return
        if event.button.id and event.button.id.startswith("camp_"):
            idx = int(event.button.id.split("_")[1])
            from .setup_game import SetupGameScreen
            self.app.push_screen(SetupGameScreen(ALL_CAMPAIGNS[idx]))
