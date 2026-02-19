# Auto-Placement Optimizer Design

**Version:** 1.0  
**Date:** 2026-02-19  
**Author:** Auto-generated  

---

## 1. Overview

The auto-placement optimizer generates optimized truck parking layouts from arbitrary polygon boundaries. Users input a plot shape, entry/exit points, and preferences — the system automatically creates a compliant parking layout with lanes and spaces.

### 1.1 Goals
- Support any polygon shape (triangular, rectangular, L-shaped, irregular)
- Generate access lanes respecting turning radius constraints
- Place parking spaces optimally using constraint satisfaction
- Maximize revenue (or space count) while ensuring compliance
- Complete typical optimizations in <30 seconds

---

## 2. Algorithm Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        INPUT STAGE                               │
├─────────────────────────────────────────────────────────────────┤
│  1. Polygon boundary (coordinates)                               │
│  2. Entry/exit points                                            │
│  3. User preferences (vehicle mix, optimization goal)            │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LANE GENERATION                               │
├─────────────────────────────────────────────────────────────────┤
│  1. Connect entry → exit with main access lane                   │
│  2. Generate lane centerline (shortest path or skeleton)         │
│  3. Buffer lane for required width                               │
│  4. Compute "parking zones" = polygon - lane buffers             │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                  SPACE GENERATION                                │
├─────────────────────────────────────────────────────────────────┤
│  1. Grid-based candidate generation in parking zones             │
│  2. Filter candidates for polygon containment                    │
│  3. Filter for lane accessibility (turning radius check)         │
│  4. Build constraint model with OR-Tools CP-SAT                  │
│  5. Solve with timeout                                           │
└──────────────────────────┬──────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                     OUTPUT                                       │
├─────────────────────────────────────────────────────────────────┤
│  Layout with lanes + parking spaces (passes compliance)          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Detailed Design

### 3.1 Geometry Module (`src/geometry.py`)

Core geometric operations:

```python
# Polygon operations using Shapely
- point_in_polygon(point, polygon) -> bool
- polygon_area(polygon) -> float
- buffer_polygon(polygon, distance) -> polygon  # Shrink/expand
- polygon_difference(a, b) -> polygon  # A - B
- polygon_intersection(a, b) -> polygon
- minimum_bounding_rectangle(polygon) -> (origin, width, height, angle)

# Rectangle/space operations
- rectangle_to_polygon(x, y, length, width, rotation) -> polygon
- rectangles_overlap(r1, r2, min_gap) -> bool
- rectangle_in_polygon(rect, polygon) -> bool

# Lane geometry
- line_to_lane_polygon(path, width) -> polygon
- point_to_line_distance(point, line) -> float
```

### 3.2 Lane Generator (`src/lane_generator.py`)

**Input:** 
- Polygon boundary
- Entry point (x, y)
- Exit point (x, y) [optional, defaults to opposite side]
- Lane configuration (one-way/two-way, width)

**Algorithm:**

```
1. ENTRY/EXIT VALIDATION
   - Snap points to polygon boundary if needed
   - Validate points are on or near boundary

2. MAIN ACCESS LANE
   a. For simple shapes (convex): Direct line entry → exit
   b. For complex shapes: 
      - Compute medial axis (skeleton) of polygon
      - Find path through skeleton that stays inside
      - Smooth path with bezier curves
   
3. LANE BUFFERING
   - Create buffer polygon around lane centerline
   - Buffer width = lane_width + maneuvering_space
   - One-way: 6m total (5m lane + 1m buffer)
   - Two-way: 9m total (7m lane + 2m buffer)

4. PARKING ZONE COMPUTATION
   - parking_zone = polygon.difference(lane_buffer)
   - Handle multi-polygon results (for L-shapes etc.)

5. OUTPUT
   - Lane object with centerline path
   - Parking zone polygon(s)
```

### 3.3 Space Placement Optimizer (`src/optimizer.py`)

Uses Google OR-Tools CP-SAT solver for constraint-based optimization.

**Phase 1: Candidate Generation**

```
1. Compute bounding box of parking zones
2. Create grid of candidate positions
   - Grid spacing: 0.5m (fine enough for optimization)
   - For each vehicle type requested
   
3. For each grid position + orientation (0°, 90°):
   - Create candidate space
   - Check if fully contained in parking zone
   - Check if accessible from lane (within turning_radius + space_length)
   - Keep valid candidates

4. Result: List of valid candidate placements
```

**Phase 2: Constraint Model**

```python
# Variables
for each candidate c:
    selected[c] = BoolVar()  # Is this candidate selected?

# Constraints
# C1: No overlaps (including min_spacing)
for each pair (c1, c2) that overlap:
    model.Add(selected[c1] + selected[c2] <= 1)

# C2: Vehicle mix limits (optional)
for each type t:
    model.Add(sum(selected[c] for c of type t) <= max_count[t])
    model.Add(sum(selected[c] for c of type t) >= min_count[t])

# C3: Fire access - each space within 10m of lane/boundary
# (Pre-filtered in candidate generation)

# Objective
if goal == "maximize_revenue":
    model.Maximize(sum(revenue[c] * selected[c] for c))
elif goal == "maximize_count":
    model.Maximize(sum(selected[c] for c))
```

**Phase 3: Solving**

```
1. Set solver time limit (default 30 seconds)
2. Enable solver hints from greedy pre-solution
3. Solve
4. Extract selected candidates
5. Build final Layout object
```

### 3.4 Turning Radius Check

A space is accessible if a vehicle can reach it from the lane:

```
1. Find closest point on lane to space entrance
2. Compute required turning arc from lane to space
3. Check if turning arc stays inside polygon
4. For parallel parking: 
   - Entry from lane end (no sharp turn needed)
   - Check lane width sufficient for maneuver
5. For perpendicular parking:
   - Need turning_radius + vehicle_length clearance
```

Simplified check (MVP):
```
space_accessible = (distance_to_lane <= turning_radius + lane_width)
```

---

## 4. Space Arrangement Strategies

### 4.1 Parallel to Boundary
- Spaces along polygon edges
- Most efficient for narrow lots
- Requires careful lane routing

### 4.2 Herringbone Pattern
- Spaces at 45° angle to lane
- Good for wider areas
- Allows easy entry/exit

### 4.3 Perpendicular Rows
- Spaces 90° to lane
- Standard truck stop layout
- Best for rectangular areas

The optimizer tries multiple patterns and picks the best result.

---

## 5. Implementation Plan

### Step 1: Geometry Module
- [ ] Create `src/geometry.py`
- [ ] Shapely-based polygon operations
- [ ] Unit tests for geometry functions

### Step 2: Lane Generator
- [ ] Create `src/lane_generator.py`
- [ ] Simple direct-path implementation
- [ ] Skeleton-based path for complex shapes
- [ ] Unit tests

### Step 3: Space Optimizer
- [ ] Create `src/optimizer.py`
- [ ] Candidate generation
- [ ] OR-Tools constraint model
- [ ] Solving with timeout
- [ ] Unit tests

### Step 4: UI Integration
- [ ] Add auto-generate section to sidebar
- [ ] Plot input UI (draw/upload/manual)
- [ ] Entry/exit point selection
- [ ] Progress indicator
- [ ] Results display

### Step 5: Testing & Refinement
- [ ] Test on various plot shapes
- [ ] Performance optimization
- [ ] Edge case handling

---

## 6. Configuration

Add to `vehicle_specs.json`:

```json
{
  "optimizer": {
    "grid_resolution": 0.5,
    "time_limit_seconds": 30,
    "lane_buffer_one_way": 1.0,
    "lane_buffer_two_way": 2.0,
    "default_orientations": [0, 90],
    "parallel_parking_factor": 0.8,
    "perpendicular_parking_factor": 1.0
  }
}
```

---

## 7. Edge Cases

| Case | Handling |
|------|----------|
| Very narrow plot | Warn if < min_lane_width + space_length |
| No valid entry point | Error with suggestion |
| No spaces fit | Return empty layout with warning |
| Concave polygon | Use skeleton-based lane routing |
| Multi-polygon result | Treat each sub-polygon separately |
| Solver timeout | Return best solution found |

---

## 8. Performance Considerations

- **Candidate pruning:** Filter obviously invalid candidates early
- **Spatial indexing:** Use R-tree for overlap detection
- **Solver hints:** Provide greedy solution as starting point
- **Incremental solving:** Start with fewer candidates, add more if time allows
- **Caching:** Cache geometry computations per polygon

Expected performance:
- Small lot (< 30 spaces): < 5 seconds
- Medium lot (30-60 spaces): < 15 seconds  
- Large lot (60+ spaces): < 30 seconds

---

## 9. Dependencies

```
shapely>=2.0.0    # Geometry operations
ortools>=9.8      # Constraint solver
numpy>=1.24.0     # Numerical operations
scipy>=1.10.0     # Spatial algorithms (optional)
```

---

## 10. API Design

```python
# Main entry point
def optimize_layout(
    boundary: List[Tuple[float, float]],
    entry_point: Tuple[float, float],
    exit_point: Optional[Tuple[float, float]] = None,
    vehicle_mix: Optional[Dict[str, int]] = None,  # {type: max_count}
    optimization_goal: str = "maximize_revenue",  # or "maximize_count"
    time_limit: float = 30.0,
    lane_type: str = "oneway",
    callback: Optional[Callable] = None,  # Progress updates
) -> OptimizationResult

@dataclass
class OptimizationResult:
    layout: Layout
    stats: Dict[str, Any]  # spaces_count, revenue, solve_time
    status: str  # optimal, feasible, infeasible, timeout
    warnings: List[str]
```
