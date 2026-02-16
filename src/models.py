"""Data models for TruckParking Optimizer."""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Tuple
from datetime import datetime
import json


@dataclass
class ParkingSpace:
    """A single parking space."""
    id: int
    type: str  # truck, tractor, trailer, ev, van
    x: float  # position in meters
    y: float  # position in meters
    length: float  # meters
    width: float  # meters
    rotation: float = 0.0  # degrees
    label: str = ""
    
    def __post_init__(self):
        if not self.label:
            prefix_map = {"truck": "T", "tractor": "TR", "trailer": "TL", "ev": "EV", "van": "V"}
            self.label = f"{prefix_map.get(self.type, 'S')}-{self.id}"
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "ParkingSpace":
        return cls(**data)
    
    def get_corners(self) -> List[Tuple[float, float]]:
        """Get the four corners of the space (for collision detection)."""
        import math
        
        # Half dimensions
        half_l = self.length / 2
        half_w = self.width / 2
        
        # Corners relative to center (before rotation)
        corners = [
            (-half_l, -half_w),
            (half_l, -half_w),
            (half_l, half_w),
            (-half_l, half_w),
        ]
        
        # Rotate and translate
        rad = math.radians(self.rotation)
        cos_r, sin_r = math.cos(rad), math.sin(rad)
        
        rotated = []
        for cx, cy in corners:
            rx = cx * cos_r - cy * sin_r + self.x + half_l
            ry = cx * sin_r + cy * cos_r + self.y + half_w
            rotated.append((rx, ry))
        
        return rotated


@dataclass
class Lane:
    """A driving lane."""
    id: str
    type: str  # oneway, twoway
    width: float
    path: List[Tuple[float, float]]
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Lane":
        data["path"] = [tuple(p) for p in data["path"]]
        return cls(**data)


@dataclass
class Layout:
    """A complete parking lot layout."""
    name: str
    lot_width: float = 74.0
    lot_length: float = 145.0
    spaces: List[ParkingSpace] = field(default_factory=list)
    lanes: List[Lane] = field(default_factory=list)
    boundary: List[Tuple[float, float]] = field(default_factory=list)
    created: str = ""
    description: str = ""
    
    def __post_init__(self):
        if not self.created:
            self.created = datetime.now().strftime("%Y-%m-%d")
        if not self.boundary:
            # Default triangular boundary
            self.boundary = [(0, 0), (27, 0), (74, 145), (0, 145)]
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "created": self.created,
            "description": self.description,
            "lot": {
                "width": self.lot_width,
                "length": self.lot_length,
                "boundary": self.boundary,
            },
            "spaces": [s.to_dict() for s in self.spaces],
            "lanes": [l.to_dict() for l in self.lanes],
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Layout":
        lot = data.get("lot", {})
        return cls(
            name=data.get("name", "Unnamed"),
            lot_width=lot.get("width", 74),
            lot_length=lot.get("length", 145),
            boundary=[tuple(p) for p in lot.get("boundary", [])],
            spaces=[ParkingSpace.from_dict(s) for s in data.get("spaces", [])],
            lanes=[Lane.from_dict(l) for l in data.get("lanes", [])],
            created=data.get("created", ""),
            description=data.get("description", ""),
        )
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Layout":
        return cls.from_dict(json.loads(json_str))
    
    def get_space_by_id(self, space_id: int) -> Optional[ParkingSpace]:
        for space in self.spaces:
            if space.id == space_id:
                return space
        return None
    
    def add_space(self, space: ParkingSpace) -> None:
        self.spaces.append(space)
    
    def remove_space(self, space_id: int) -> bool:
        for i, space in enumerate(self.spaces):
            if space.id == space_id:
                del self.spaces[i]
                return True
        return False
    
    def get_next_id(self) -> int:
        if not self.spaces:
            return 1
        return max(s.id for s in self.spaces) + 1
    
    def count_by_type(self) -> dict:
        counts = {"truck": 0, "tractor": 0, "trailer": 0, "ev": 0, "van": 0}
        for space in self.spaces:
            if space.type in counts:
                counts[space.type] += 1
        return counts


@dataclass
class Scenario:
    """A scenario with layout and revenue parameters."""
    name: str
    layout: Layout
    occupancy_rate: float = 0.75
    notes: str = ""
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "layout": self.layout.to_dict(),
            "occupancy_rate": self.occupancy_rate,
            "notes": self.notes,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Scenario":
        return cls(
            name=data["name"],
            layout=Layout.from_dict(data["layout"]),
            occupancy_rate=data.get("occupancy_rate", 0.75),
            notes=data.get("notes", ""),
        )
