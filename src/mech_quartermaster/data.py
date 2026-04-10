"""Static data: mech chassis definitions, equipment, part types."""

# Component locations (BT-style)
LOCATIONS = ["Head", "Center Torso", "Left Torso", "Right Torso",
             "Left Arm", "Right Arm", "Left Leg", "Right Leg"]

LOC_SHORT = {
    "Head": "HD", "Center Torso": "CT", "Left Torso": "LT",
    "Right Torso": "RT", "Left Arm": "LA", "Right Arm": "RA",
    "Left Leg": "LL", "Right Leg": "RL"
}

# (max_armor, max_structure) per location for each chassis tonnage class
# Format: [HD, CT, LT, RT, LA, RA, LL, RL]
CHASSIS_DATA = {
    "Commando COM-2D": {
        "tonnage": 25, "class": "Light",
        "armor":     [6,  16, 10, 10,  8,  8, 12, 12],
        "structure": [3,   8,  6,  6,  4,  4,  6,  6],
        "equipment": {
            "Right Arm":   ["SRM-6"],
            "Left Arm":    ["Medium Laser", "Medium Laser"],
            "Center Torso":["Small Laser"],
        }
    },
    "Jenner JR7-D": {
        "tonnage": 35, "class": "Light",
        "armor":     [9, 22, 14, 14, 12, 12, 16, 16],
        "structure": [3, 11,  8,  8,  6,  6,  8,  8],
        "equipment": {
            "Right Arm":   ["Medium Laser", "Medium Laser"],
            "Left Arm":    ["Medium Laser", "Medium Laser"],
            "Center Torso":["SRM-4"],
        }
    },
    "Hunchback HBK-4G": {
        "tonnage": 50, "class": "Medium",
        "armor":     [9, 26, 18, 18, 14, 14, 20, 20],
        "structure": [3, 16, 12, 12,  8,  8, 12, 12],
        "equipment": {
            "Right Torso": ["AC/20"],
            "Left Arm":    ["Medium Laser"],
            "Right Arm":   ["Medium Laser"],
            "Center Torso":["Medium Laser"],
        }
    },
    "Trebuchet TBT-5N": {
        "tonnage": 50, "class": "Medium",
        "armor":     [9, 24, 16, 16, 14, 14, 18, 18],
        "structure": [3, 16, 12, 12,  8,  8, 12, 12],
        "equipment": {
            "Left Arm":    ["LRM-15"],
            "Right Arm":   ["LRM-15"],
            "Left Torso":  ["Medium Laser"],
            "Right Torso": ["Medium Laser"],
            "Center Torso":["Medium Laser"],
        }
    },
    "Dragon DRG-1N": {
        "tonnage": 60, "class": "Heavy",
        "armor":     [9, 30, 20, 20, 18, 18, 22, 22],
        "structure": [3, 20, 14, 14, 10, 10, 14, 14],
        "equipment": {
            "Right Arm":   ["AC/5"],
            "Left Arm":    ["Medium Laser"],
            "Right Torso": ["LRM-10"],
            "Center Torso":["Medium Laser"],
        }
    },
    "Warhammer WHM-6R": {
        "tonnage": 70, "class": "Heavy",
        "armor":     [9, 34, 22, 22, 20, 20, 26, 26],
        "structure": [3, 22, 15, 15, 11, 11, 15, 15],
        "equipment": {
            "Right Arm":   ["PPC"],
            "Left Arm":    ["PPC"],
            "Right Torso": ["Medium Laser", "SRM-6"],
            "Left Torso":  ["Medium Laser", "SRM-6"],
            "Center Torso":["Small Laser"],
        }
    },
    "Atlas AS7-D": {
        "tonnage": 100, "class": "Assault",
        "armor":     [9, 47, 32, 32, 34, 34, 41, 41],
        "structure": [3, 31, 21, 21, 17, 17, 21, 21],
        "equipment": {
            "Right Arm":   ["AC/20"],
            "Left Arm":    ["LRM-20"],
            "Right Torso": ["SRM-6", "Medium Laser"],
            "Left Torso":  ["SRM-6", "Medium Laser"],
            "Center Torso":["Medium Laser"],
        }
    },

    # ── New chassis ──────────────────────────────────────────────────────────

    # Lights
    "Locust LCT-1V": {
        "tonnage": 20, "class": "Light",
        "armor":     [5,  12,  7,  7,  5,  5,  8,  8],
        "structure": [3,   6,  5,  5,  3,  3,  4,  4],
        "equipment": {
            "Left Arm":    ["Machine Gun"],
            "Right Arm":   ["Machine Gun"],
            "Center Torso":["Medium Laser"],
        }
    },
    "Spider SDR-5V": {
        "tonnage": 30, "class": "Light",
        "armor":     [7,  16,  9,  9,  7,  7, 10, 10],
        "structure": [3,  10,  7,  7,  5,  5,  7,  7],
        "equipment": {
            "Left Arm":    ["Medium Laser"],
            "Right Arm":   ["Medium Laser"],
        }
    },
    "Firestarter FS9-H": {
        "tonnage": 35, "class": "Light",
        "armor":     [8,  20, 12, 12,  8,  8, 12, 12],
        "structure": [3,  11,  8,  8,  6,  6,  8,  8],
        "equipment": {
            "Left Arm":    ["Machine Gun", "Medium Laser"],
            "Right Arm":   ["Machine Gun", "Medium Laser"],
        }
    },

    # Mediums
    "Vindicator VND-1R": {
        "tonnage": 45, "class": "Medium",
        "armor":     [8,  22, 14, 14, 10, 10, 14, 14],
        "structure": [3,  14, 11, 11,  7,  7, 11, 11],
        "equipment": {
            "Right Arm":   ["PPC"],
            "Left Arm":    ["Medium Laser"],
            "Left Torso":  ["LRM-10"],
            "Center Torso":["Small Laser"],
        }
    },
    "Centurion CN9-A": {
        "tonnage": 50, "class": "Medium",
        "armor":     [8,  26, 16, 16, 14, 14, 20, 20],
        "structure": [3,  16, 12, 12,  8,  8, 12, 12],
        "equipment": {
            "Right Arm":   ["AC/10"],
            "Left Torso":  ["LRM-10"],
            "Left Arm":    ["Medium Laser"],
        }
    },
    "Griffin GRF-1N": {
        "tonnage": 55, "class": "Medium",
        "armor":     [9,  26, 18, 18, 14, 14, 18, 18],
        "structure": [3,  18, 13, 13,  9,  9, 13, 13],
        "equipment": {
            "Right Arm":   ["PPC"],
            "Left Torso":  ["LRM-10"],
        }
    },
    "Wolverine WVR-6R": {
        "tonnage": 55, "class": "Medium",
        "armor":     [9,  28, 18, 18, 16, 16, 20, 20],
        "structure": [3,  18, 13, 13,  9,  9, 13, 13],
        "equipment": {
            "Right Arm":   ["AC/5", "Medium Laser"],
            "Left Arm":    ["SRM-6"],
            "Left Torso":  ["LRM-10"],
        }
    },

    # Heavies
    "Catapult CPLT-C1": {
        "tonnage": 65, "class": "Heavy",
        "armor":     [9,  32, 22, 22, 16, 16, 24, 24],
        "structure": [3,  21, 15, 15, 10, 10, 15, 15],
        "equipment": {
            "Left Torso":  ["LRM-15"],
            "Right Torso": ["LRM-15"],
            "Left Arm":    ["Medium Laser"],
            "Right Arm":   ["Medium Laser"],
            "Center Torso":["Medium Laser"],
        }
    },
    "Thunderbolt TDR-5S": {
        "tonnage": 65, "class": "Heavy",
        "armor":     [9,  34, 22, 22, 20, 20, 26, 26],
        "structure": [3,  21, 15, 15, 10, 10, 15, 15],
        "equipment": {
            "Right Arm":   ["Large Laser"],
            "Left Torso":  ["LRM-15"],
            "Center Torso":["Medium Laser", "Medium Laser"],
            "Left Arm":    ["Medium Laser"],
        }
    },
    "Marauder MAD-3R": {
        "tonnage": 75, "class": "Heavy",
        "armor":     [9,  36, 24, 24, 22, 22, 28, 28],
        "structure": [3,  23, 16, 16, 12, 12, 16, 16],
        "equipment": {
            "Right Arm":   ["PPC"],
            "Left Arm":    ["PPC"],
            "Right Torso": ["AC/5"],
            "Center Torso":["Medium Laser", "Medium Laser"],
        }
    },

    # Assaults
    "Victor VTR-9B": {
        "tonnage": 80, "class": "Assault",
        "armor":     [9,  38, 26, 26, 24, 24, 30, 30],
        "structure": [3,  25, 17, 17, 13, 13, 17, 17],
        "equipment": {
            "Right Arm":   ["AC/20"],
            "Left Torso":  ["LRM-10"],
            "Right Torso": ["SRM-4"],
            "Left Arm":    ["Medium Laser"],
        }
    },
    "Stalker STK-3F": {
        "tonnage": 85, "class": "Assault",
        "armor":     [9,  41, 28, 28, 26, 26, 34, 34],
        "structure": [3,  27, 18, 18, 14, 14, 18, 18],
        "equipment": {
            "Left Torso":  ["LRM-15", "Medium Laser"],
            "Right Torso": ["LRM-15", "Medium Laser"],
            "Left Arm":    ["Large Laser"],
            "Right Arm":   ["Large Laser"],
        }
    },
    "Battlemaster BLR-1G": {
        "tonnage": 85, "class": "Assault",
        "armor":     [9,  42, 28, 28, 26, 26, 34, 34],
        "structure": [3,  27, 18, 18, 14, 14, 18, 18],
        "equipment": {
            "Right Arm":   ["PPC"],
            "Left Torso":  ["Medium Laser", "Medium Laser"],
            "Right Torso": ["SRM-6", "Medium Laser"],
            "Left Arm":    ["Medium Laser"],
            "Center Torso":["Medium Laser"],
        }
    },
}

# Parts catalog: name -> (base cost, repair_time_hours, description)
PARTS_CATALOG = {
    # Armor plates (per location)
    "Armor Plating (Light)":   (500,   2, "Armor repair for light mechs (25-35t)"),
    "Armor Plating (Medium)":  (800,   3, "Armor repair for medium mechs (40-55t)"),
    "Armor Plating (Heavy)":   (1200,  4, "Armor repair for heavy mechs (60-75t)"),
    "Armor Plating (Assault)": (2000,  6, "Armor repair for assault mechs (80-100t)"),
    # Internal structure
    "Structure Brace (Light)":   (1500,  6,  "Internal structure repair, light"),
    "Structure Brace (Medium)":  (2500,  8,  "Internal structure repair, medium"),
    "Structure Brace (Heavy)":   (4000,  12, "Internal structure repair, heavy"),
    "Structure Brace (Assault)": (7000,  18, "Internal structure repair, assault"),
    # Weapons
    "Machine Gun":    (1200,   1,  "Replace destroyed machine gun"),
    "Small Laser":    (3000,   2,  "Replace destroyed small laser"),
    "Medium Laser":   (8000,   4,  "Replace destroyed medium laser"),
    "Large Laser":    (18000,  8,  "Replace destroyed large laser"),
    "PPC":            (35000,  12, "Replace destroyed PPC"),
    "AC/5":           (15000,  8,  "Replace destroyed AC/5 autocannon"),
    "AC/10":          (25000,  12, "Replace destroyed AC/10 autocannon"),
    "AC/20":          (45000,  20, "Replace destroyed AC/20 autocannon"),
    "SRM-4":          (6000,   4,  "Replace destroyed SRM-4 launcher"),
    "SRM-6":          (9000,   6,  "Replace destroyed SRM-6 launcher"),
    "LRM-10":         (12000,  6,  "Replace destroyed LRM-10 launcher"),
    "LRM-15":         (18000,  8,  "Replace destroyed LRM-15 launcher"),
    "LRM-20":         (25000,  10, "Replace destroyed LRM-20 launcher"),
    # Critical systems
    "Gyro":           (50000,  16, "Replace destroyed gyroscope — mech cannot walk without it"),
    "Engine Shielding":(40000, 12, "Repair engine shielding after core damage"),
    "Cockpit Canopy": (20000,  8,  "Replace head cockpit canopy"),
    "Heat Sink":      (2000,   2,  "Replace damaged heat sink"),
    "Actuator (Arm)": (5000,   4,  "Arm actuator replacement"),
    "Actuator (Leg)": (8000,   6,  "Leg actuator replacement — restores mobility"),
    "Ammo Bin":       (1000,   1,  "Replace destroyed ammo bin"),
}

# Weapons that can appear as equipment
WEAPON_NAMES = {
    "Machine Gun", "Small Laser", "Medium Laser", "Large Laser", "PPC",
    "AC/5", "AC/10", "AC/20", "SRM-4", "SRM-6",
    "LRM-10", "LRM-15", "LRM-20"
}

# Mech market prices (base C-Bill cost, new/pristine)
# Used mechs are sold at 50-80% of base price with some pre-existing damage
# Final contract — only offered when one mission away from victory
FINAL_MISSION = {
    "name": "The Last Contract",
    "description": "A high-value target. Heavy opposition. No quarter given.",
    "damage_scale": 2.0,
    "c_bill_reward": (1_800_000, 2_200_000),
    "salvage_scale": 0,
    "mech_salvage_chance": 0,
    "min_contract_days": 1,
    "class_bonus": {"Light": 0.06, "Medium": 0.08, "Heavy": 0.10, "Assault": 0.10},
}

MECH_PRICES = {
    # Lights
    "Locust LCT-1V":      900_000,
    "Spider SDR-5V":    2_300_000,
    "Commando COM-2D":  1_800_000,
    "Firestarter FS9-H":3_000_000,
    "Jenner JR7-D":     3_200_000,
    # Mediums
    "Vindicator VND-1R":4_200_000,
    "Centurion CN9-A":  5_000_000,
    "Hunchback HBK-4G": 5_500_000,
    "Trebuchet TBT-5N": 4_800_000,
    "Griffin GRF-1N":   6_200_000,
    "Wolverine WVR-6R": 6_500_000,
    # Heavies
    "Dragon DRG-1N":    7_200_000,
    "Catapult CPLT-C1": 8_500_000,
    "Thunderbolt TDR-5S":8_200_000,
    "Warhammer WHM-6R": 9_500_000,
    "Marauder MAD-3R": 11_000_000,
    # Assaults
    "Victor VTR-9B":   13_500_000,
    "Stalker STK-3F":  16_000_000,
    "Battlemaster BLR-1G":15_500_000,
    "Atlas AS7-D":     18_000_000,
}

# Weekly overhead rates (scales with roster size and tonnage)
OVERHEAD_BASE     = 50_000   # fixed: hangar lease, admin, base supplies
OVERHEAD_PER_MECH = 30_000   # per mech: dedicated tech crew wages
OVERHEAD_PER_TON  =  1_500   # per ton: maintenance, coolant, ammo resupply

# Mission types with damage profile weights
MISSION_TYPES = [
    {
        "name": "Recon",
        "description": "Light skirmish — employer pays well, little left on the field",
        "damage_scale": 0.3,
        "c_bill_reward": (120_000, 220_000),
        "salvage_scale": 0.9,
        "mech_salvage_chance": 0.10,
        "min_contract_days": 1,
        # Success bonus per mech by weight class (lights excel at recon)
        "class_bonus": {"Light": 0.10, "Medium": 0.08, "Heavy": 0.06, "Assault": 0.04},
    },
    {
        "name": "Raid",
        "description": "Hit-and-fade strike — balanced pay and pickings",
        "damage_scale": 0.6,
        "c_bill_reward": (140_000, 260_000),
        "salvage_scale": 2.4,
        "mech_salvage_chance": 0.20,
        "min_contract_days": 1,
        # Mediums are ideal raiders; lights and heavies equally useful
        "class_bonus": {"Light": 0.08, "Medium": 0.10, "Heavy": 0.08, "Assault": 0.06},
    },
    {
        "name": "Battle",
        "description": "Full lance engagement — reduced pay, rich salvage",
        "damage_scale": 1.0,
        "c_bill_reward": (160_000, 300_000),
        "salvage_scale": 4.2,
        "mech_salvage_chance": 0.30,
        "min_contract_days": 2,
        # Heavies dominate pitched battles; assaults and mediums strong; lights a liability
        "class_bonus": {"Light": 0.06, "Medium": 0.08, "Heavy": 0.10, "Assault": 0.08},
    },
    {
        "name": "Recovery Op",
        "description": "Extract intact mech wrecks from a contested zone — low parts, high wreck chance",
        "damage_scale": 0.25,
        "c_bill_reward": (50_000, 90_000),
        "salvage_scale": 0.9,
        "mech_salvage_chance": 0.50,
        "min_contract_days": 1,
        "class_bonus": {"Light": 0.10, "Medium": 0.09, "Heavy": 0.07, "Assault": 0.05},
    },
    {
        "name": "Salvage Run",
        "description": "Scavenge a recent battlefield — light opposition, rich pickings",
        "damage_scale": 0.2,
        "c_bill_reward": (40_000, 80_000),
        "salvage_scale": 5.4,
        "mech_salvage_chance": 0.10,
        "min_contract_days": 1,
        # Any mech can scavenge; lights are nimble pickers, assaults overkill
        "class_bonus": {"Light": 0.10, "Medium": 0.09, "Heavy": 0.07, "Assault": 0.05},
    },
    {
        "name": "Assault",
        "description": "Full frontal assault on a hardened target — maximum risk, maximum reward",
        "damage_scale": 1.4,
        "c_bill_reward": (400_000, 600_000),
        "salvage_scale": 6.6,
        "mech_salvage_chance": 0.50,
        "min_contract_days": 3,
        # Assault mechs built for this; heavies solid; mediums marginal; lights a poor fit
        "class_bonus": {"Light": 0.04, "Medium": 0.06, "Heavy": 0.08, "Assault": 0.10},
    },
]
