"""Campaign dataclasses — the contract between a campaign definition and the game engine."""

from dataclasses import dataclass, field
from typing import Callable, Optional, Any


@dataclass
class NarrativeEvent:
    id: str
    trigger: Callable       # fn(GameState) -> bool
    text: str               # displayed to player when triggered
    effect: Optional[Callable] = None  # fn(GameState) -> None, optional state change
    once: bool = True       # if True, fires at most once per run


@dataclass
class Campaign:
    id: str
    name: str
    description: str        # shown on campaign select screen
    intro_text: str         # shown at game start
    victory_text: str       # shown on victory screen; supports {company_name}, {missions_run}

    # Starting conditions
    starting_credits: int
    starting_lance: Any     # dict {"Light": 2, "Medium": 1} OR list of chassis names
    starting_parts: dict    # part_name -> qty

    # Victory
    victory_condition: Callable     # fn(GameState) -> bool
    victory_missions: Optional[int] = None  # for progress display; None = no counter shown

    # Optional final boss mission (replaces daily contracts when one win away)
    final_mission: Optional[dict] = None

    # Restrict which mission types appear in daily rotation (None = all)
    available_mission_types: Optional[list] = None

    # Narrative events fired during the run
    events: list = field(default_factory=list)

    # Applied to the final score formula
    score_multiplier: float = 1.0
