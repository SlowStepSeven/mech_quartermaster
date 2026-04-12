"""Mech Quartermaster — Textual application root."""

import sys
import os
from textual.app import App
from textual.message import Message

from .game import GameState, _save_lance


def _css_path() -> str:
    base = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(__file__)
    return os.path.join(base, "mq.tcss")


# ─── Cross-screen messages ────────────────────────────────────────────────────

class CampaignEnded(Message):
    """Posted by VictoryScreen / GameOverScreen when the player is done."""


# ─── App ─────────────────────────────────────────────────────────────────────

class MechQMApp(App):
    CSS_PATH = _css_path()

    def __init__(self):
        super().__init__()
        self.gs: GameState | None = None

    def on_mount(self) -> None:
        from .screens.campaign_select import CampaignSelectScreen
        self.push_screen(CampaignSelectScreen())

    def on_campaign_ended(self, _message: CampaignEnded) -> None:
        """Return to campaign select after a campaign ends."""
        from .screens.campaign_select import CampaignSelectScreen
        self.gs = None
        self.switch_screen(CampaignSelectScreen())


def main() -> None:
    MechQMApp().run(size=(180, 45))
