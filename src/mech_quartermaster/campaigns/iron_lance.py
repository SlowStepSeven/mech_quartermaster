"""Iron Lance — the original freeplay mercenary campaign."""

from .base import Campaign, NarrativeEvent
from ..data import FINAL_MISSION


def _victory(gs) -> bool:
    return gs.missions_run >= 12 and len(gs.mechs) >= 1


IRON_LANCE_CAMPAIGN = Campaign(
    id="iron_lance",
    name="Iron Lance",
    description="Build a mercenary lance from scratch and survive 12 successful contracts.",

    intro_text=(
        "  You are the quartermaster and chief technician for a\n"
        "  mercenary BattleMech lance. Keep your mechs operational,\n"
        "  manage your parts budget, and deploy for contracts.\n"
        "\n"
        "  Complete 12 successful missions to cement your reputation."
    ),

    victory_text=(
        "  After {missions_run} grueling deployments, {company_name} has\n"
        "  proven itself on the battlefield. Your lance survives.\n"
        "  The C-Bills are rolling in. Time to hang up the wrench."
    ),

    starting_credits=750_000,
    starting_lance={"Light": 2, "Medium": 1, "Heavy": 1},
    starting_parts={
        "Armor Plating (Light)":  3,
        "Armor Plating (Medium)": 4,
        "Armor Plating (Heavy)":  2,
        "Medium Laser":           1,
    },

    victory_condition=_victory,
    victory_missions=12,
    final_mission=FINAL_MISSION,
    available_mission_types=None,   # all mission types

    events=[
        NarrativeEvent(
            id="early_rep",
            trigger=lambda gs: gs.missions_run >= 3,
            text=(
                "TRANSMISSION // Word of your lance's effectiveness is spreading.\n"
                "Contacts are beginning to route better contracts your way."
            ),
        ),
        NarrativeEvent(
            id="closing_in",
            trigger=lambda gs: gs.missions_run >= 9,
            text=(
                "TRANSMISSION // You're close to establishing a permanent reputation.\n"
                "One final push and Iron Lance will be known across the Inner Sphere."
            ),
        ),
    ],

    score_multiplier=1.0,
)
