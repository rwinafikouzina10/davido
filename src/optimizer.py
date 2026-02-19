"""Auto-placement optimizer for TruckParking Optimizer.

Uses Google OR-Tools CP-SAT solver for constraint-based space placement
optimization.
"""

from typing import List, Tuple, Optional, Dict, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
import time
import math

from shapely.geometry import Polygon, Point

from .geometry import (
    coords_to_polygon,
    polygon_to_coords,
    Rectangle,
    rectangle_in_polygon,
    rectangles_overlap,
    point_to_line_distance,
    polygon_area,
    buffer_polygon,
    generate_grid_points,
    get_multipolygon_parts,
)
from .lane_generator import (
    generate_lanes,
    LaneConfig,
    LaneGenerationResult,
)
from .models import Layout, ParkingSpace, Lane
from .config import SPACE_TYPES, COMPLIANCE, PRICING


class OptimizationGoal(Enum):
    """Optimization objective."""
    MAXIMIZE_REVENUE = "maximize_revenue"
    MAXIMIZE_COUNT = "maximize_count"
    MAXIMIZE_TRUCKS = "maximize_trucks"  # Prioritize large trucks


@dataclass
class OptimizationConfig:
    """Configuration for the optimization process."""
    time_limit: float = 30.0  # Seconds
    grid_resolution: float = 0.5  # Meters
    orientations: List[float] = field(default_factory=lambda: [0, 90])
    goal: OptimizationGoal = OptimizationGoal.MAXIMIZE_REVENUE
    vehicle_mix: Optional[Dict[str, Tuple[int, int]]] = None  # {type: (min, max)}
    min_spacing: float = None  # Override from config
    fire_access_distance: float = None  # Override from config
    
    def __post_init__(self):
        if self.min_spacing is None:
            self.min_spacing = COMPLIANCE.get("min_vehicle_spacing", 1.0)
        if self.fire_access_distance is None:
            self.fire_access_distance = COMPLIANCE.get("fire_access_max_distance", 10.0)


@dataclass
class Candidate:
    """A candidate parking space placement."""
    id: int
    type: str
    x: float
    y: float
    length: float
    width: float
    rotation: float
    revenue: float  # Annual revenue
    
    def to_rectangle(self) -> Rectangle:
        return Rectangle(self.x, self.y, self.length, self.width, self.rotation)
    
    def to_parking_space(self) -> ParkingSpace:
        return ParkingSpace(
            id=self.id,
            type=self.type,
            x=self.x,
            y=self.y,
            length=self.length,
            width=self.width,
            rotation=self.rotation,
        )


@dataclass
class OptimizationResult:
    """Result of the optimization process."""
    layout: Layout
    stats: Dict[str, Any] = field(default_factory=dict)
    status: str = "unknown"  # optimal, feasible, infeasible, timeout
    warnings: List[str] = field(default_factory=list)
    solve_time: float = 0.0
    
    @property
    def success(self) -> bool:
        return self.status in ("optimal", "feasible")
    
    @property
    def space_count(self) -> int:
        return len(self.layout.spaces)
    
    @property
    def estimated_revenue(self) -> float:
        return self.stats.get("total_revenue", 0.0)


def validate_vehicle_mix(vehicle_mix: Optional[Dict[str, Tuple[int, int]]]) -> List[str]:
    """Validate vehicle mix constraints and return validation errors."""
    if not vehicle_mix:
        return []

    errors = []
    valid_types = set(SPACE_TYPES.keys())

    for space_type, limits in vehicle_mix.items():
        if space_type not in valid_types:
            errors.append(f"Unknown vehicle type in mix: {space_type}")
            continue
        min_count, max_count = limits
        if min_count < 0 or max_count < 0:
            errors.append(f"Vehicle mix for {space_type} cannot be negative")
        if min_count > max_count:
            errors.append(f"Vehicle mix for {space_type} has min > max ({min_count} > {max_count})")

    return errors


def calculate_space_revenue(space_type: str, occupancy: float = 0.75) -> float:
    """
    Calculate annual revenue for a space type.
    
    Args:
        space_type: Type of parking space
        occupancy: Expected occupancy rate
        
    Returns:
        Annual revenue in euros
    """
    base_annual = PRICING.get("annual", 2433.60)
    
    multipliers = {
        "truck": 1.0,
        "tractor": 0.7,
        "trailer": 0.6,
        "ev": 1.3,
        "van": 0.5,
    }
    
    multiplier = multipliers.get(space_type, 1.0)
    return base_annual * multiplier * occupancy


def generate_candidates(
    parking_zones: List[Polygon],
    lane_path: List[Tuple[float, float]],
    config: OptimizationConfig,
    boundary: Polygon,
) -> List[Candidate]:
    """
    Generate candidate parking space placements.
    
    Args:
        parking_zones: Available parking zone polygons
        lane_path: Lane centerline for accessibility check
        config: Optimization configuration
        boundary: Original lot boundary
        
    Returns:
        List of valid candidates
    """
    candidates = []
    candidate_id = 1
    
    # Space types to consider
    space_types = list(SPACE_TYPES.keys())
    
    # If vehicle mix specified, only consider those types
    if config.vehicle_mix:
        space_types = [t for t in space_types if t in config.vehicle_mix]
    
    for zone in parking_zones:
        # Get bounding box
        bounds = zone.bounds  # (minx, miny, maxx, maxy)
        
        # Generate grid positions
        x = bounds[0]
        while x <= bounds[2]:
            y = bounds[1]
            while y <= bounds[3]:
                # Try each space type
                for space_type in space_types:
                    specs = SPACE_TYPES[space_type]
                    length = specs["default_length"]
                    width = specs["default_width"]
                    turning_radius = specs.get("turning_radius", 12.0)
                    
                    # Try each orientation
                    for rotation in config.orientations:
                        # Create candidate rectangle
                        rect = Rectangle(x, y, length, width, rotation)
                        
                        # Check if fully contained in zone
                        if not rectangle_in_polygon(rect, zone):
                            continue
                        
                        # Check accessibility from lane
                        space_center = rect.center
                        dist_to_lane = point_to_line_distance(space_center, lane_path)
                        
                        # Space should be reachable (within turning radius + some margin)
                        max_distance = turning_radius + length
                        if dist_to_lane > max_distance:
                            continue
                        
                        # Check fire access (distance to boundary)
                        dist_to_boundary = boundary.exterior.distance(Point(space_center))
                        if dist_to_boundary > config.fire_access_distance:
                            # Also check distance to lane as alternative fire access
                            if dist_to_lane > config.fire_access_distance:
                                continue
                        
                        # Valid candidate
                        revenue = calculate_space_revenue(space_type)
                        
                        candidate = Candidate(
                            id=candidate_id,
                            type=space_type,
                            x=x,
                            y=y,
                            length=length,
                            width=width,
                            rotation=rotation,
                            revenue=revenue,
                        )
                        candidates.append(candidate)
                        candidate_id += 1
                
                y += config.grid_resolution
            x += config.grid_resolution
    
    return candidates


def find_overlapping_pairs(
    candidates: List[Candidate],
    min_spacing: float
) -> List[Tuple[int, int]]:
    """
    Find all pairs of candidates that would overlap.
    
    Args:
        candidates: List of candidate placements
        min_spacing: Minimum required spacing between spaces
        
    Returns:
        List of (index1, index2) pairs that conflict
    """
    conflicts = []
    
    # Pre-compute rectangles
    rectangles = [c.to_rectangle() for c in candidates]
    
    # Simple O(n²) comparison - could optimize with spatial index for large n
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            if rectangles_overlap(rectangles[i], rectangles[j], min_spacing):
                conflicts.append((i, j))
    
    return conflicts


def solve_with_ortools(
    candidates: List[Candidate],
    conflicts: List[Tuple[int, int]],
    config: OptimizationConfig,
    callback: Optional[Callable] = None,
) -> Tuple[List[int], str]:
    """
    Solve the placement problem using OR-Tools CP-SAT.
    
    Args:
        candidates: List of candidate placements
        conflicts: List of conflicting pairs
        config: Optimization configuration
        callback: Progress callback function
        
    Returns:
        (selected_indices, status)
    """
    try:
        from ortools.sat.python import cp_model
    except ImportError:
        # Fallback to greedy if OR-Tools not available
        return solve_greedy(candidates, conflicts, config)
    
    model = cp_model.CpModel()
    
    # Create boolean variable for each candidate
    selected = {}
    for i, c in enumerate(candidates):
        selected[i] = model.NewBoolVar(f"space_{i}")
    
    # Constraint: No overlapping spaces
    for i, j in conflicts:
        model.Add(selected[i] + selected[j] <= 1)
    
    # Constraint: Vehicle mix limits
    if config.vehicle_mix:
        for space_type, (min_count, max_count) in config.vehicle_mix.items():
            type_vars = [selected[i] for i, c in enumerate(candidates) if c.type == space_type]
            if min_count > 0 and not type_vars:
                return [], "infeasible"
            if type_vars:
                if min_count > 0:
                    model.Add(sum(type_vars) >= min_count)
                if max_count < float('inf'):
                    model.Add(sum(type_vars) <= max_count)
    
    # Objective
    if config.goal == OptimizationGoal.MAXIMIZE_REVENUE:
        # Maximize total revenue
        objective = sum(int(c.revenue * 100) * selected[i] for i, c in enumerate(candidates))
        model.Maximize(objective)
    elif config.goal == OptimizationGoal.MAXIMIZE_COUNT:
        # Maximize number of spaces
        model.Maximize(sum(selected[i] for i in range(len(candidates))))
    elif config.goal == OptimizationGoal.MAXIMIZE_TRUCKS:
        # Prioritize trucks with higher weight
        weights = {"truck": 10, "ev": 9, "tractor": 5, "trailer": 4, "van": 2}
        objective = sum(weights.get(c.type, 1) * selected[i] for i, c in enumerate(candidates))
        model.Maximize(objective)
    
    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = config.time_limit
    solver.parameters.num_search_workers = 1
    
    # Add callback for progress updates
    class SolutionCallback(cp_model.CpSolverSolutionCallback):
        def __init__(self, callback_fn):
            cp_model.CpSolverSolutionCallback.__init__(self)
            self.callback_fn = callback_fn
            self.solution_count = 0
        
        def on_solution_callback(self):
            self.solution_count += 1
            if self.callback_fn:
                selected_count = sum(self.Value(selected[i]) for i in range(len(candidates)))
                self.callback_fn(f"Found solution {self.solution_count} with {selected_count} spaces")
    
    solution_callback = SolutionCallback(callback) if callback else None
    
    if solution_callback:
        status = solver.Solve(model, solution_callback)
    else:
        status = solver.Solve(model)
    
    # Extract solution
    status_map = {
        cp_model.OPTIMAL: "optimal",
        cp_model.FEASIBLE: "feasible",
        cp_model.INFEASIBLE: "infeasible",
        cp_model.MODEL_INVALID: "invalid",
        cp_model.UNKNOWN: "timeout",
    }
    
    result_status = status_map.get(status, "unknown")
    
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        selected_indices = [i for i in range(len(candidates)) if solver.Value(selected[i])]
        return selected_indices, result_status
    else:
        return [], result_status


def solve_greedy(
    candidates: List[Candidate],
    conflicts: List[Tuple[int, int]],
    config: OptimizationConfig,
) -> Tuple[List[int], str]:
    """
    Greedy fallback solver when OR-Tools is not available.
    
    Sorts candidates by revenue and greedily selects non-conflicting ones.
    
    Args:
        candidates: List of candidate placements
        conflicts: List of conflicting pairs
        config: Optimization configuration
        
    Returns:
        (selected_indices, status)
    """
    # Build conflict adjacency
    conflict_map = {}
    for i, j in conflicts:
        conflict_map.setdefault(i, set()).add(j)
        conflict_map.setdefault(j, set()).add(i)
    
    # Sort by revenue (descending) or other criteria
    if config.goal == OptimizationGoal.MAXIMIZE_REVENUE:
        sorted_indices = sorted(range(len(candidates)), key=lambda i: -candidates[i].revenue)
    elif config.goal == OptimizationGoal.MAXIMIZE_TRUCKS:
        type_priority = {"truck": 0, "ev": 1, "tractor": 2, "trailer": 3, "van": 4}
        sorted_indices = sorted(range(len(candidates)), 
                                key=lambda i: (type_priority.get(candidates[i].type, 5), -candidates[i].revenue))
    else:
        sorted_indices = list(range(len(candidates)))
    
    # Greedy selection
    selected = []
    excluded = set()
    
    for i in sorted_indices:
        if i in excluded:
            continue
        
        # Check vehicle mix limits
        if config.vehicle_mix:
            space_type = candidates[i].type
            if space_type in config.vehicle_mix:
                _, max_count = config.vehicle_mix[space_type]
                current_count = sum(1 for j in selected if candidates[j].type == space_type)
                if current_count >= max_count:
                    continue
        
        selected.append(i)
        
        # Exclude conflicting candidates
        for j in conflict_map.get(i, []):
            excluded.add(j)

    # Validate minimum mix requirements in fallback mode
    if config.vehicle_mix:
        counts = {}
        for idx in selected:
            counts[candidates[idx].type] = counts.get(candidates[idx].type, 0) + 1
        for space_type, (min_count, _) in config.vehicle_mix.items():
            if counts.get(space_type, 0) < min_count:
                return [], "infeasible"

    return selected, "feasible"


def optimize_layout(
    boundary: List[Tuple[float, float]],
    entry_point: Tuple[float, float],
    exit_point: Optional[Tuple[float, float]] = None,
    vehicle_mix: Optional[Dict[str, Tuple[int, int]]] = None,
    optimization_goal: str = "maximize_revenue",
    time_limit: float = 30.0,
    lane_type: str = "oneway",
    orientations: Optional[List[float]] = None,
    layout_name: str = "Optimized Layout",
    callback: Optional[Callable] = None,
) -> OptimizationResult:
    """
    Main entry point for layout optimization.
    
    Args:
        boundary: Polygon boundary coordinates [(x, y), ...]
        entry_point: Entry point (x, y)
        exit_point: Exit point (x, y), optional
        vehicle_mix: Optional dict {type: (min_count, max_count)}
        optimization_goal: "maximize_revenue", "maximize_count", or "maximize_trucks"
        time_limit: Maximum solving time in seconds
        lane_type: "oneway" or "twoway"
        orientations: Optional list of allowed placement angles in degrees
        layout_name: Name for the generated layout
        callback: Progress callback function(message: str)
        
    Returns:
        OptimizationResult with generated layout
    """
    start_time = time.time()

    if not boundary or len(boundary) < 3:
        raise ValueError("Boundary must contain at least 3 coordinate points")
    if entry_point is None or len(entry_point) != 2:
        raise ValueError("Entry point must be a valid (x, y) tuple")

    mix_errors = validate_vehicle_mix(vehicle_mix)
    if mix_errors:
        return OptimizationResult(
            layout=Layout(name=layout_name),
            status="invalid",
            warnings=mix_errors,
            solve_time=0.0,
        )
    
    # Convert goal string to enum
    goal_map = {
        "maximize_revenue": OptimizationGoal.MAXIMIZE_REVENUE,
        "maximize_count": OptimizationGoal.MAXIMIZE_COUNT,
        "maximize_trucks": OptimizationGoal.MAXIMIZE_TRUCKS,
    }
    goal = goal_map.get(optimization_goal, OptimizationGoal.MAXIMIZE_REVENUE)
    
    # Create configuration
    config = OptimizationConfig(
        time_limit=time_limit,
        goal=goal,
        vehicle_mix=vehicle_mix,
    )
    if orientations:
        config.orientations = sorted(set(float(o) for o in orientations))
    
    # Create boundary polygon
    boundary_poly = coords_to_polygon(boundary)
    
    # Calculate lot dimensions
    bounds = boundary_poly.bounds
    lot_width = bounds[2] - bounds[0]
    lot_length = bounds[3] - bounds[1]
    
    # Generate lanes
    if callback:
        callback("Generating access lanes...")
    
    lane_config = LaneConfig(lane_type=lane_type)
    lane_result = generate_lanes(boundary, entry_point, exit_point, lane_config)
    
    if not lane_result.success or not lane_result.parking_zones:
        return OptimizationResult(
            layout=Layout(name=layout_name, lot_width=lot_width, lot_length=lot_length),
            status="infeasible",
            warnings=["Failed to generate lanes: " + "; ".join(lane_result.warnings)],
            solve_time=time.time() - start_time,
        )
    
    # Get lane path for accessibility checks
    lane_path = lane_result.lanes[0].path if lane_result.lanes else [(0, 0), (lot_width, lot_length)]
    
    # Generate candidates
    if callback:
        callback("Generating candidate placements...")
    
    candidates = generate_candidates(
        lane_result.parking_zones,
        lane_path,
        config,
        boundary_poly,
    )
    
    if not candidates:
        return OptimizationResult(
            layout=Layout(name=layout_name, lot_width=lot_width, lot_length=lot_length, 
                         lanes=lane_result.lanes, boundary=boundary),
            status="infeasible",
            warnings=["No valid candidate placements found"],
            solve_time=time.time() - start_time,
        )
    
    if callback:
        callback(f"Generated {len(candidates)} candidates, finding optimal placement...")
    
    # Find conflicts
    conflicts = find_overlapping_pairs(candidates, config.min_spacing)
    
    if callback:
        callback(f"Found {len(conflicts)} conflicts, solving...")
    
    # Solve
    remaining_time = max(1.0, time_limit - (time.time() - start_time))
    config.time_limit = remaining_time
    
    selected_indices, status = solve_with_ortools(candidates, conflicts, config, callback)
    
    # Build result layout
    layout = Layout(
        name=layout_name,
        lot_width=lot_width,
        lot_length=lot_length,
        boundary=boundary,
        lanes=lane_result.lanes,
    )
    
    # Add selected spaces
    total_revenue = 0.0
    for idx in selected_indices:
        candidate = candidates[idx]
        space = candidate.to_parking_space()
        layout.add_space(space)
        total_revenue += candidate.revenue
    
    # Renumber spaces
    for i, space in enumerate(layout.spaces, 1):
        space.id = i
        prefix_map = {"truck": "T", "tractor": "TR", "trailer": "TL", "ev": "EV", "van": "V"}
        space.label = f"{prefix_map.get(space.type, 'S')}-{i}"
    
    # Collect statistics
    stats = {
        "total_candidates": len(candidates),
        "total_conflicts": len(conflicts),
        "selected_spaces": len(selected_indices),
        "total_revenue": total_revenue,
        "space_counts": layout.count_by_type(),
        "lot_area": polygon_area(boundary_poly),
        "parking_area": lane_result.total_parking_area,
    }
    
    solve_time = time.time() - start_time
    
    return OptimizationResult(
        layout=layout,
        stats=stats,
        status=status,
        warnings=lane_result.warnings,
        solve_time=solve_time,
    )


def quick_estimate(
    boundary: List[Tuple[float, float]],
    lane_type: str = "oneway",
) -> Dict[str, Any]:
    """
    Quick estimate of how many spaces could fit.
    
    Does not run full optimization, just estimates based on area.
    
    Args:
        boundary: Polygon boundary coordinates
        lane_type: "oneway" or "twoway"
        
    Returns:
        Dict with estimates
    """
    boundary_poly = coords_to_polygon(boundary)
    total_area = polygon_area(boundary_poly)
    
    # Estimate lane area (roughly 15-20% for one-way, 20-25% for two-way)
    lane_pct = 0.17 if lane_type == "oneway" else 0.22
    parking_area = total_area * (1 - lane_pct)
    
    # Typical space size
    truck_area = 18.5 * 3.5  # ~65 m²
    tractor_area = 8.5 * 3.5  # ~30 m²
    
    # Space efficiency factor (accounts for spacing, maneuvering)
    efficiency = 0.6
    
    # Estimate counts
    max_trucks = int(parking_area * efficiency / truck_area)
    max_tractors = int(parking_area * efficiency / tractor_area)
    
    # Revenue estimate
    base_annual = PRICING.get("annual", 2433.60)
    estimated_revenue = max_trucks * base_annual * 0.75  # 75% occupancy
    
    return {
        "total_area": total_area,
        "estimated_parking_area": parking_area,
        "max_truck_spaces": max_trucks,
        "max_tractor_spaces": max_tractors,
        "estimated_annual_revenue": estimated_revenue,
        "efficiency_factor": efficiency,
    }
