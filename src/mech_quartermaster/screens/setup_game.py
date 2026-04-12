"""Campaign setup screen — company name, lance selection, difficulty."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, Input, Label, RadioButton, RadioSet, Static
from textual.containers import Vertical, VerticalScroll

from ..campaigns.base import Campaign
from ..game import (
    DIFFICULTIES, _build_lance, _load_lance_data, _mech_from_dict,
    _save_summary, build_gamestate,
)


class SetupGameScreen(Screen):
    def __init__(self, campaign: Campaign):
        super().__init__()
        self._campaign = campaign
        self._save_data = _load_lance_data()

    def compose(self) -> ComposeResult:
        camp = self._campaign
        with VerticalScroll():
            yield Static(
                f"[bold cyan]══════════════════════════════════════════════════════════════════════[/]\n"
                f"  [bold cyan]{camp.name.upper()}[/]\n"
                f"[bold cyan]══════════════════════════════════════════════════════════════════════[/]\n\n"
                f"{camp.intro_text}\n",
                markup=True,
            )

            yield Label("  Company Name:")
            yield Input(placeholder="Iron Lance", id="company_name")
            yield Static("")

            if self._save_data:
                yield Static(
                    "  [bold]Lance Selection[/]\n"
                    "  [dim]──────────────────────────────────────────[/]",
                    markup=True,
                )
                summary = _save_summary(self._save_data)
                with RadioSet(id="lance_choice"):
                    yield RadioButton("New lance", value=True)
                    yield RadioButton(f"Load saved — {summary}")
                yield Static("")

            yield Static(
                "  [bold]Difficulty[/]\n"
                "  [dim]──────────────────────────────────────────[/]",
                markup=True,
            )
            with RadioSet(id="difficulty"):
                for key, cfg in DIFFICULTIES.items():
                    color = {"Easy": "green", "Medium": "yellow", "Hard": "red"}[key]
                    yield RadioButton(cfg['label'], value=(key == "Hard"))
            yield Static("")
            yield Button("Begin Campaign", id="begin")
            yield Button("Back", id="back")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "back":
            self.app.pop_screen()
            return
        if event.button.id != "begin":
            return

        company = self.query_one("#company_name", Input).value.strip() or "Iron Lance"

        # Determine difficulty
        diff_keys = list(DIFFICULTIES.keys())
        diff_set = self.query_one("#difficulty", RadioSet)
        difficulty = diff_keys[diff_set.pressed_index] if diff_set.pressed_index is not None else "Hard"

        # Determine mechs and whether save is loaded
        save_data = None
        if self._save_data:
            lance_set = self.query_one("#lance_choice", RadioSet)
            if lance_set.pressed_index == 1:
                mechs = [_mech_from_dict(m) for m in self._save_data["mechs"]]
                save_data = self._save_data
            else:
                mechs = _build_lance(self._campaign.starting_lance)
        else:
            mechs = _build_lance(self._campaign.starting_lance)

        gs = build_gamestate(company, self._campaign, difficulty, mechs, save_data)
        self.app.gs = gs

        from .main_hub import MainHubScreen
        self.app.switch_screen(MainHubScreen())
