"""Lane generation for TruckParking Optimizer.

Automatically generates access lanes through a parking lot polygon,
connecting entry and exit points while maximizing usable parking area.
"""

from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field
import math

from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union

from .geometry import (
    coords_to_polygon,
    polygon_to_coords,
    line_to_lane_polygon,
    buffer_polygon,
    polygon_difference,
    snap_point_to_boundary,
    is_point_on_boundary,
    compute_medial_axis_path,
    polygon_centroid,
    get_polygon_edges,
    get_multipolygon_parts,
)
from .config import COMPLIANCE
from .models import Lane


@dataclass
class LaneConfig:
    """Configuration for lane generation."""
    lane_type: str = "oneway"  # oneway, twoway
    width: float = None  # Auto-calculated based on type if None
    buffer: float = None  # Extra maneuvering space, auto if None
    
    def __post_init__(self):
        if self.width is None:
            if self.lane_type == "twoway":
                self.width = COMPLIANCE.get("lane_width_recommended_twoway", 8.0)
            else:
                self.width = COMPLIANCE.get("lane_width_recommended_oneway", 6.0)
        
        if self.buffer is None:
            self.buffer = 1.0 if self.lane_type == "oneway" else 2.0
    
    @property
    def total_width(self) -> float:
        """Total width including buffer."""
        return self.width + self.buffer


@dataclass 
class LaneGenerationResult:
    """Result of lane generation."""
    lanes: List[Lane] = field(default_factory=list)
    parking_zones: List[Polygon] = field(default_factory=list)
    lane_polygons: List[Polygon] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    success: bool = True
    
    @property
    def total_parking_area(self) -> float:
        """Total area available for parking."""
        return sum(p.area for p in self.parking_zones)
    
    def get_parking_zone_coords(self) -> List[List[Tuple[float, float]]]:
        """Get coordinates for all parking zones."""
        return [polygon_to_coords(p) for p in self.parking_zones]


def validate_entry_exit_points(
    boundary: Polygon,
    entry: Tuple[float, float],
    exit_point: Optional[Tuple[float, float]],
    tolerance: float = 5.0
) -> Tuple[Tuple[float, float], Tuple[float, float], List[str]]:
    """
    Validate and adjust entry/exit points.
    
    Args:
        boundary: Lot boundary polygon
        entry: Entry point coordinates
        exit_point: Exit point coordinates (optional)
        tolerance: Max distance to snap to boundary
        
    Returns:
        (adjusted_entry, adjusted_exit, warnings)
    """
    warnings = []
    
    # Validate entry point
    if not is_point_on_boundary(entry, boundary, tolerance):
        old_entry = entry
        entry = snap_point_to_boundary(entry, boundary)
        warnings.append(f"Entry point snapped to boundary: {old_entry} → {entry}")
    
    # If no exit specified, find opposite point
    if exit_point is None:
        # Find point on boundary furthest from entry
        centroid = polygon_centroid(boundary)
        
        # Vector from entry to centroid
        dx = centroid[0] - entry[0]
        dy = centroid[1] - entry[1]
        
        # Extend past centroid
        far_point = (centroid[0] + dx, centroid[1] + dy)
        exit_point = snap_point_to_boundary(far_point, boundary)
        warnings.append(f"Exit point auto-generated at opposite side: {exit_point}")
    else:
        # Validate exit point
        if not is_point_on_boundary(exit_point, boundary, tolerance):
            old_exit = exit_point
            exit_point = snap_point_to_boundary(exit_point, boundary)
            warnings.append(f"Exit point snapped to boundary: {old_exit} → {exit_point}")
    
    return entry, exit_point, warnings


def generate_lane_path(
    boundary: Polygon,
    entry: Tuple[float, float],
    exit_point: Tuple[float, float],
    config: LaneConfig
) -> List[Tuple[float, float]]:
    """
    Generate the centerline path for a lane.
    
    Args:
        boundary: Lot boundary polygon
        entry: Entry point
        exit_point: Exit point
        config: Lane configuration
        
    Returns:
        List of (x, y) points forming the lane centerline
    """
    # Try direct path first
    direct = LineString([entry, exit_point])
    
    # Inset the boundary to keep lane inside with buffer
    inset = buffer_polygon(boundary, -config.total_width / 2 - 0.5)
    
    if inset.is_empty or inset.area < 10:
        # Boundary too small for inset, use direct path
        return [entry, exit_point]
    
    # Check if direct path stays inside (with some tolerance for boundary points)
    # Need to check the interior portion, excluding endpoints
    if direct.length > 1:
        interior_check = direct.buffer(0.1)
        interior_check = interior_check.difference(Point(entry).buffer(config.total_width/2))
        interior_check = interior_check.difference(Point(exit_point).buffer(config.total_width/2))
        
        if boundary.contains(interior_check) or interior_check.is_empty:
            return [entry, exit_point]
    
    # Need to route through interior
    # Use medial axis approach for complex shapes
    path = compute_medial_axis_path(boundary, entry, exit_point)
    
    # Smooth the path if it has many points
    if len(path) > 3:
        path = smooth_path(path, boundary, config.total_width / 2)
    
    return path


def smooth_path(
    path: List[Tuple[float, float]], 
    boundary: Polygon,
    min_distance: float
) -> List[Tuple[float, float]]:
    """
    Smooth a path while keeping it inside the boundary.
    
    Args:
        path: Original path points
        boundary: Containing polygon
        min_distance: Minimum distance from boundary
        
    Returns:
        Smoothed path
    """
    if len(path) <= 2:
        return path
    
    # Simple smoothing: try to remove intermediate points if direct segments work
    smoothed = [path[0]]
    i = 0
    
    while i < len(path) - 1:
        # Try to skip to furthest reachable point
        j = len(path) - 1
        while j > i + 1:
            segment = LineString([path[i], path[j]])
            buffered = segment.buffer(min_distance)
            if boundary.contains(buffered):
                break
            j -= 1
        
        smoothed.append(path[j])
        i = j
    
    return smoothed


def generate_lanes(
    boundary_coords: List[Tuple[float, float]],
    entry_point: Tuple[float, float],
    exit_point: Optional[Tuple[float, float]] = None,
    config: Optional[LaneConfig] = None
) -> LaneGenerationResult:
    """
    Generate access lanes for a parking lot.
    
    Args:
        boundary_coords: Polygon boundary coordinates
        entry_point: Entry point (x, y)
        exit_point: Exit point (x, y), optional
        config: Lane configuration
        
    Returns:
        LaneGenerationResult with lanes and parking zones
    """
    result = LaneGenerationResult()
    
    if config is None:
        config = LaneConfig()
    
    # Convert boundary to polygon
    boundary = coords_to_polygon(boundary_coords)
    
    if boundary.is_empty or boundary.area < 50:
        result.success = False
        result.warnings.append("Boundary polygon is too small or invalid")
        return result
    
    # Validate and adjust entry/exit points
    entry, exit_pt, warnings = validate_entry_exit_points(
        boundary, entry_point, exit_point
    )
    result.warnings.extend(warnings)
    
    # Generate lane centerline path
    path = generate_lane_path(boundary, entry, exit_pt, config)
    
    # Create lane polygon
    lane_polygon = line_to_lane_polygon(path, config.total_width)
    
    # Intersect with boundary to ensure it stays inside
    lane_polygon = lane_polygon.intersection(boundary)
    if isinstance(lane_polygon, list):
        lane_polygon = unary_union(lane_polygon)
    
    # Store lane polygon
    if not lane_polygon.is_empty:
        result.lane_polygons.append(lane_polygon)
    
    # Create Lane model object
    lane = Lane(
        id="main",
        type=config.lane_type,
        width=config.width,
        path=path
    )
    result.lanes.append(lane)
    
    # Compute parking zones (boundary minus lane)
    parking_area = polygon_difference(boundary, lane_polygon)
    
    # Handle multi-polygon results
    parking_parts = get_multipolygon_parts(parking_area)
    
    # Filter out tiny fragments
    min_usable_area = 30  # m² - enough for at least one small space
    for part in parking_parts:
        if part.area >= min_usable_area:
            result.parking_zones.append(part)
    
    if not result.parking_zones:
        result.warnings.append("No usable parking zones after lane generation")
        # Fall back to using the whole boundary minus a small lane buffer
        small_lane = line_to_lane_polygon(path, config.width)
        parking_area = polygon_difference(boundary, small_lane)
        parking_parts = get_multipolygon_parts(parking_area)
        for part in parking_parts:
            if part.area >= min_usable_area:
                result.parking_zones.append(part)
    
    # Calculate statistics
    total_area = boundary.area
    lane_area = sum(p.area for p in result.lane_polygons)
    parking_area = result.total_parking_area
    
    result.warnings.append(
        f"Area distribution: Total={total_area:.0f}m², "
        f"Lanes={lane_area:.0f}m², Parking={parking_area:.0f}m²"
    )
    
    return result


def generate_perimeter_lanes(
    boundary_coords: List[Tuple[float, float]],
    entry_point: Tuple[float, float],
    exit_point: Optional[Tuple[float, float]] = None,
    config: Optional[LaneConfig] = None
) -> LaneGenerationResult:
    """
    Generate lanes along the perimeter of the lot.
    
    Useful for lots where the center should be used for parking
    and access is around the edges.
    
    Args:
        boundary_coords: Polygon boundary coordinates
        entry_point: Entry point (x, y)
        exit_point: Exit point (x, y), optional
        config: Lane configuration
        
    Returns:
        LaneGenerationResult with perimeter lanes
    """
    result = LaneGenerationResult()
    
    if config is None:
        config = LaneConfig()
    
    # Convert boundary to polygon
    boundary = coords_to_polygon(boundary_coords)
    
    # Create perimeter lane by buffering inward
    inset = config.total_width
    inner = buffer_polygon(boundary, -inset)
    
    if inner.is_empty or inner.area < 50:
        result.success = False
        result.warnings.append("Lot too small for perimeter lanes")
        return result
    
    # Lane is the ring between boundary and inner
    lane_ring = polygon_difference(boundary, inner)
    
    if isinstance(lane_ring, Polygon) and not lane_ring.is_empty:
        result.lane_polygons.append(lane_ring)
    
    # The inner polygon is the parking zone
    result.parking_zones.append(inner)
    
    # Create a simplified lane object (perimeter path)
    perimeter_path = polygon_to_coords(boundary)
    lane = Lane(
        id="perimeter",
        type=config.lane_type,
        width=config.width,
        path=perimeter_path
    )
    result.lanes.append(lane)
    
    return result


def find_optimal_lane_direction(
    boundary: Polygon,
    space_length: float = 18.5
) -> float:
    """
    Find the optimal lane direction to maximize parking spaces.
    
    The optimal direction is typically along the longest dimension
    of the lot, allowing perpendicular parking on both sides.
    
    Args:
        boundary: Lot boundary polygon
        space_length: Typical parking space length
        
    Returns:
        Angle in degrees for optimal lane direction
    """
    from .geometry import minimum_bounding_rectangle
    
    origin, width, height, angle = minimum_bounding_rectangle(boundary)
    
    # Lane should go along the longer dimension
    if width >= height:
        return angle
    else:
        return angle + 90


def estimate_lane_requirements(
    boundary: Polygon,
    num_rows: int = 2
) -> Dict[str, Any]:
    """
    Estimate lane requirements for a given boundary.
    
    Args:
        boundary: Lot boundary polygon
        num_rows: Desired number of parking rows
        
    Returns:
        Dict with lane width, coverage estimates
    """
    from .geometry import minimum_bounding_rectangle
    
    origin, width, height, angle = minimum_bounding_rectangle(boundary)
    
    # Typical space width
    space_width = 3.5  # meters
    lane_width = 6.0  # one-way
    
    # Estimate how many lanes needed
    short_dim = min(width, height)
    
    # Each row needs: space_width + half lane width
    row_width = space_width + lane_width / 2
    
    # Available for parking (minus one full lane)
    available = short_dim - lane_width
    possible_rows = int(available / row_width)
    
    return {
        "recommended_lane_width": lane_width,
        "possible_rows": max(1, possible_rows),
        "lot_width": short_dim,
        "lot_length": max(width, height),
        "optimal_angle": angle if width >= height else angle + 90,
    }
