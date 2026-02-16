"""Compliance checking engine for TruckParking Optimizer."""

from dataclasses import dataclass
from typing import List, Tuple, Optional
import math

from .models import Layout, ParkingSpace
from .config import SPACE_TYPES, COMPLIANCE


@dataclass
class Violation:
    """A compliance violation."""
    severity: str  # error, warning
    category: str  # dimensions, spacing, lane, fire
    message: str
    space_ids: List[int]
    location: Optional[Tuple[float, float]] = None


@dataclass
class ComplianceReport:
    """Full compliance check report."""
    is_valid: bool
    violations: List[Violation]
    warnings: int
    errors: int
    
    @property
    def status(self) -> str:
        if self.errors > 0:
            return "❌ Non-Compliant"
        elif self.warnings > 0:
            return "⚠️ Compliant with Warnings"
        return "✅ Fully Compliant"
    
    @property
    def status_color(self) -> str:
        if self.errors > 0:
            return "red"
        elif self.warnings > 0:
            return "orange"
        return "green"


def check_space_dimensions(space: ParkingSpace) -> List[Violation]:
    """Check if space dimensions meet minimum requirements."""
    violations = []
    specs = SPACE_TYPES.get(space.type, {})
    
    min_length = specs.get("min_length", 0)
    min_width = specs.get("min_width", 0)
    
    if space.length < min_length:
        violations.append(Violation(
            severity="error",
            category="dimensions",
            message=f"Space {space.label}: Length {space.length}m is below minimum {min_length}m for {space.type}",
            space_ids=[space.id],
            location=(space.x, space.y),
        ))
    
    if space.width < min_width:
        violations.append(Violation(
            severity="error",
            category="dimensions",
            message=f"Space {space.label}: Width {space.width}m is below minimum {min_width}m for {space.type}",
            space_ids=[space.id],
            location=(space.x, space.y),
        ))
    
    return violations


def rectangles_overlap(r1: ParkingSpace, r2: ParkingSpace, min_gap: float = 0) -> bool:
    """Check if two rectangles overlap (with optional minimum gap)."""
    # Simple AABB check (assumes no rotation for simplicity)
    # Add min_gap to create buffer zone
    
    r1_left = r1.x - min_gap
    r1_right = r1.x + r1.length + min_gap
    r1_bottom = r1.y - min_gap
    r1_top = r1.y + r1.width + min_gap
    
    r2_left = r2.x
    r2_right = r2.x + r2.length
    r2_bottom = r2.y
    r2_top = r2.y + r2.width
    
    # Check for non-overlap conditions
    if r1_right <= r2_left or r2_right <= r1_left:
        return False
    if r1_top <= r2_bottom or r2_top <= r1_bottom:
        return False
    
    return True


def check_spacing(spaces: List[ParkingSpace]) -> List[Violation]:
    """Check minimum spacing between vehicles."""
    violations = []
    min_spacing = COMPLIANCE.get("min_vehicle_spacing", 1.0)
    
    checked_pairs = set()
    
    for i, space1 in enumerate(spaces):
        for j, space2 in enumerate(spaces):
            if i >= j:
                continue
            
            pair_key = (min(space1.id, space2.id), max(space1.id, space2.id))
            if pair_key in checked_pairs:
                continue
            checked_pairs.add(pair_key)
            
            # Check if spaces are too close (overlap with min_spacing buffer)
            if rectangles_overlap(space1, space2, min_gap=0):
                violations.append(Violation(
                    severity="error",
                    category="spacing",
                    message=f"Spaces {space1.label} and {space2.label} overlap!",
                    space_ids=[space1.id, space2.id],
                    location=((space1.x + space2.x) / 2, (space1.y + space2.y) / 2),
                ))
            elif rectangles_overlap(space1, space2, min_gap=min_spacing):
                # Calculate actual distance
                dx = abs(space1.x + space1.length/2 - space2.x - space2.length/2)
                dy = abs(space1.y + space1.width/2 - space2.y - space2.width/2)
                
                violations.append(Violation(
                    severity="warning",
                    category="spacing",
                    message=f"Spaces {space1.label} and {space2.label} have less than {min_spacing}m spacing",
                    space_ids=[space1.id, space2.id],
                    location=((space1.x + space2.x) / 2, (space1.y + space2.y) / 2),
                ))
    
    return violations


def check_boundary(space: ParkingSpace, boundary: List[Tuple[float, float]], lot_width: float, lot_length: float) -> List[Violation]:
    """Check if space is within lot boundary."""
    violations = []
    
    # Simple rectangular bounds check
    if space.x < 0 or space.y < 0:
        violations.append(Violation(
            severity="error",
            category="boundary",
            message=f"Space {space.label} is outside lot boundary (negative coordinates)",
            space_ids=[space.id],
            location=(space.x, space.y),
        ))
    
    if space.x + space.length > lot_width or space.y + space.width > lot_length:
        violations.append(Violation(
            severity="error",
            category="boundary",
            message=f"Space {space.label} extends beyond lot boundary",
            space_ids=[space.id],
            location=(space.x, space.y),
        ))
    
    return violations


def check_fire_access(spaces: List[ParkingSpace], lot_width: float, lot_length: float) -> List[Violation]:
    """Check fire access requirements."""
    violations = []
    max_distance = COMPLIANCE.get("fire_access_max_distance", 10.0)
    
    # Simple check: ensure spaces aren't too far from any edge
    for space in spaces:
        center_x = space.x + space.length / 2
        center_y = space.y + space.width / 2
        
        # Distance to nearest edge
        dist_to_left = center_x
        dist_to_right = lot_width - center_x
        dist_to_bottom = center_y
        dist_to_top = lot_length - center_y
        
        min_dist = min(dist_to_left, dist_to_right, dist_to_bottom, dist_to_top)
        
        if min_dist > max_distance:
            violations.append(Violation(
                severity="warning",
                category="fire",
                message=f"Space {space.label} is {min_dist:.1f}m from nearest access (max recommended: {max_distance}m)",
                space_ids=[space.id],
                location=(space.x, space.y),
            ))
    
    return violations


def check_layout(layout: Layout) -> ComplianceReport:
    """Run all compliance checks on a layout."""
    all_violations = []
    
    # Check each space
    for space in layout.spaces:
        # Dimension checks
        all_violations.extend(check_space_dimensions(space))
        
        # Boundary checks
        all_violations.extend(check_boundary(
            space, layout.boundary, layout.lot_width, layout.lot_length
        ))
    
    # Spacing checks
    all_violations.extend(check_spacing(layout.spaces))
    
    # Fire access checks
    all_violations.extend(check_fire_access(
        layout.spaces, layout.lot_width, layout.lot_length
    ))
    
    # Count by severity
    errors = sum(1 for v in all_violations if v.severity == "error")
    warnings = sum(1 for v in all_violations if v.severity == "warning")
    
    return ComplianceReport(
        is_valid=(errors == 0),
        violations=all_violations,
        warnings=warnings,
        errors=errors,
    )
