"""Configuration and constants for TruckParking Optimizer."""

import json
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
LAYOUTS_DIR = ROOT_DIR / "layouts"

# Load vehicle specifications
with open(DATA_DIR / "vehicle_specs.json") as f:
    SPECS = json.load(f)

SPACE_TYPES = SPECS["space_types"]
COMPLIANCE = SPECS["compliance"]
PRICING = SPECS["pricing"]
SITE = SPECS["site"]

# Colors for visualization
COLORS = {
    "truck": "#3498db",
    "tractor": "#e67e22", 
    "trailer": "#9b59b6",
    "ev": "#27ae60",
    "van": "#f39c12",
    "boundary": "#2c3e50",
    "lane": "#95a5a6",
    "violation": "#e74c3c",
    "valid": "#2ecc71",
}

# Default lot boundary (triangular shape)
DEFAULT_BOUNDARY = [
    (0, 0),
    (27, 0),
    (74, 145),
    (0, 145),
    (0, 0),  # Close the polygon
]
