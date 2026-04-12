"""Victory and Game Over screens — shown at campaign end."""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Button, RadioSet, RadioButton, Static
from textual.containers import Vertical

from ..app import CampaignEnded
from ..game import _final_score, _save_lance


# ── Victory Screen ────────────────────────────────────────────────────────────

_VICTORY_BANNER = """\
██╗   ██╗██╗ ██████╗████████╗ ██████╗ ██████╗ ██╗   ██╗
██║   ██║██║██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗╚██╗ ██╔╝
██║   ██║██║██║        ██║   ██║   ██║██████╔╝ ╚████╔╝
╚██╗ ██╔╝██║██║        ██║   ██║   ██║██╔══██╗  ╚██╔╝
 ╚████╔╝ ██║╚██████╗   ██║   ╚██████╔╝██║  ██║   ██║
  ╚═══╝  ╚═╝ ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝   ╚═╝  \
"""


class VictoryScreen(Screen):
    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(
                f"[bold green]{_VICTORY_BANNER}[/]",
                markup=True, classes="panel-header",
            )
            yield Static("", id="victory-stats", markup=True)
            yield RadioSet(
                RadioButton("Save lance for next campaign", id="save-yes", value=True),
                RadioButton("No thanks",                   id="save-no"),
                id="save-choice",
            )
            yield Button("Return to Campaign Select", id="done", classes="-deploy")

    def on_mount(self) -> None:
        gs = self.app.gs
        mech_value, credits, score, diff_mult = _final_score(gs)

        mech_lines = []
        for m in gs.mechs:
            mech_lines.append(f"  [cyan]{m.callsign}[/] ([dim]{m.chassis}[/])")

        stats = (
            f"  [bold]Campaign Complete:[/] [green]{gs.campaign.name}[/]\n"
            f"  Company: [bold]{gs.company_name}[/]   "
            f"Days: [dim]{gs.day}[/]   "
            f"Missions: [dim]{gs.missions_run}[/]\n\n"
            f"  [bold]Final Score[/]\n"
            f"  Mech value:  [yellow]{mech_value:,}c[/]\n"
            f"  Credits:     [yellow]{credits:,}c[/]\n"
            f"  Difficulty:  [dim]×{diff_mult}[/]\n"
            f"  [bold green]Score: {score:,}[/]\n\n"
            f"  Surviving lance:\n" + "\n".join(mech_lines)
        )
        self.query_one("#victory-stats", Static).update(stats)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "done":
            return
        gs = self.app.gs
        radio = self.query_one("#save-choice", RadioSet)
        if radio.pressed_button and radio.pressed_button.id == "save-yes":
            _save_lance(gs)
        self.app.post_message(CampaignEnded())


# ── Game Over Screen ──────────────────────────────────────────────────────────

_GAMEOVER_BANNER = """\
 ██████╗  █████╗ ███╗   ███╗███████╗     ██████╗ ██╗   ██╗███████╗██████╗
██╔════╝ ██╔══██╗████╗ ████║██╔════╝    ██╔═══██╗██║   ██║██╔════╝██╔══██╗
██║  ███╗███████║██╔████╔██║█████╗      ██║   ██║██║   ██║█████╗  ██████╔╝
██║   ██║██╔══██║██║╚██╔╝██║██╔══╝      ██║   ██║╚██╗ ██╔╝██╔══╝  ██╔══██╗
╚██████╔╝██║  ██║██║ ╚═╝ ██║███████╗    ╚██████╔╝ ╚████╔╝ ███████╗██║  ██║
 ╚═════╝ ╚═╝  ╚═╝╚═╝     ╚═╝╚══════╝     ╚═════╝   ╚═══╝  ╚══════╝╚═╝  ╚═╝\
"""


class GameOverScreen(Screen):
    def __init__(self, reason: str):
        super().__init__()
        self._reason = reason

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(
                f"[bold red]{_GAMEOVER_BANNER}[/]",
                markup=True, classes="panel-header",
            )
            yield Static("", id="gameover-stats", markup=True)
            yield Button("Return to Campaign Select", id="done", classes="-danger")

    def on_mount(self) -> None:
        gs = self.app.gs
        mech_value, credits, score, diff_mult = _final_score(gs)

        stats = (
            f"  [bold red]{self._reason}[/]\n\n"
            f"  Company: [bold]{gs.company_name}[/]   "
            f"Campaign: [dim]{gs.campaign.name}[/]\n"
            f"  Days survived: [dim]{gs.day}[/]   "
            f"Missions run: [dim]{gs.missions_run}[/]\n\n"
            f"  [bold]Final Tally[/]\n"
            f"  Mech value:  [yellow]{mech_value:,}c[/]\n"
            f"  Credits:     [yellow]{credits:,}c[/]\n"
            f"  Difficulty:  [dim]×{diff_mult}[/]\n"
            f"  [bold red]Score: {score:,}[/]"
        )
        self.query_one("#gameover-stats", Static).update(stats)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "done":
            self.app.post_message(CampaignEnded())
