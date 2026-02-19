# 🚛 TruckParking Optimizer

An interactive tool for optimizing truck parking lot layouts, ensuring regulatory compliance, and maximizing revenue potential.

## Features

- **🤖 Auto-Generate Layouts** - Input any polygon boundary → get an optimized parking layout automatically
- **Layout Visualizer** - Interactive canvas showing parking lot with spaces color-coded by type
- **Parking Space Management** - Add, edit, delete parking spots (trucks, tractors, trailers, EV, vans)
- **Compliance Checker** - Real-time validation of Dutch/EU parking regulations
- **Revenue Calculator** - Project revenue based on occupancy rates
- **Scenario Planning** - Save and compare different layout configurations
- **Data Export/Import** - JSON and GeoJSON format support

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

### 2. Run the Application

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## 🤖 Auto-Generate Layout

The optimizer automatically generates parking layouts from any polygon boundary:

### Usage

1. Open the **Auto-Generate** panel (expandable at top of page)
2. Choose input method:
   - **Preset Shapes**: Select from common lot shapes
   - **Manual Coordinates**: Enter corner points as `x1,y1; x2,y2; ...`
   - **Upload GeoJSON**: Import from GeoJSON file
3. Set entry/exit points
4. Configure optimization:
   - **Goal**: Maximize Revenue, Count, or Trucks
   - **Lane Type**: One-way (6m) or Two-way (8m)
   - **Vehicle Mix**: Optional min/max limits per type
5. Click **Generate Optimized Layout**

### How It Works

The optimizer uses a multi-stage algorithm:

1. **Lane Generation**: Creates access lanes connecting entry/exit points
2. **Candidate Generation**: Generates potential parking space positions on a grid
3. **Constraint Solving**: Uses Google OR-Tools CP-SAT solver to find optimal placement
4. **Compliance Validation**: Ensures all spaces meet regulations

See [docs/OPTIMIZER_DESIGN.md](docs/OPTIMIZER_DESIGN.md) for detailed algorithm documentation.

### Supported Shapes

- Rectangular lots
- Triangular lots (like Havenweg)
- L-shaped lots
- Any convex or simple concave polygon

## Project Structure

```
truckparking-optimizer/
├── app.py                    # Main Streamlit application
├── src/
│   ├── models.py             # Data models (Layout, ParkingSpace, etc.)
│   ├── compliance.py         # Compliance checking engine
│   ├── revenue.py            # Revenue calculations
│   ├── visualization.py      # Plotly visualization utilities
│   ├── config.py             # Configuration and constants
│   ├── geometry.py           # 🆕 Geometry utilities (Shapely-based)
│   ├── lane_generator.py     # 🆕 Lane generation logic
│   └── optimizer.py          # 🆕 Auto-placement optimizer (OR-Tools)
├── tests/
│   ├── test_geometry.py      # Geometry module tests
│   └── test_optimizer.py     # Optimizer tests
├── data/
│   └── vehicle_specs.json    # Vehicle specifications and pricing
├── layouts/
│   └── example.json          # Example layout
├── docs/
│   ├── REQUIREMENTS.md       # Project requirements
│   ├── PRD.md                # Product requirements document
│   └── OPTIMIZER_DESIGN.md   # 🆕 Optimizer algorithm documentation
├── requirements.txt
└── pyproject.toml
```

## Usage

### Adding Parking Spaces Manually

1. Use the sidebar "Add" tab
2. Select space type (truck, tractor, trailer, EV, van)
3. Set position (X, Y in meters)
4. Adjust dimensions if needed
5. Click "Add Space"

### Checking Compliance

The compliance panel shows real-time validation:
- ✅ Green = All checks passed
- ⚠️ Yellow = Warnings (minor issues)
- ❌ Red = Errors (must fix)

Checks include:
- Minimum space dimensions
- Vehicle spacing (min 1m)
- Boundary violations
- Fire access requirements

### Revenue Projections

1. Adjust the occupancy rate slider
2. View daily/weekly/monthly/annual projections
3. Compare against €200k/year target
4. See breakeven occupancy percentage

### Scenarios

1. Configure a layout (manual or auto-generated)
2. Click "Save as Scenario" in sidebar
3. Save multiple scenarios
4. Compare them in the comparison panel

## Site Specifications (Havenweg 4, Echt)

| Attribute | Value |
|-----------|-------|
| Location | Havenweg 4, Echt, Netherlands |
| Area | ~7,500 m² |
| Shape | Triangular |
| Dimensions | 27m (narrow) to 74m (wide) × 145m long |
| Target | €200,000/year |

## Space Types

| Type | Min Dimensions | Default | Color |
|------|----------------|---------|-------|
| Large Truck | 18.0m × 3.5m | 18.5m × 3.5m | Blue |
| Tractor Only | 8.0m × 3.5m | 8.5m × 3.5m | Orange |
| Trailer Only | 14.0m × 3.5m | 14.5m × 3.5m | Purple |
| EV Charging | 18.0m × 4.0m | 18.5m × 4.0m | Green |
| Small Van | 7.0m × 2.5m | 8.0m × 3.0m | Yellow |

## Compliance Standards

Based on:
- CROW Publication 317: Parking facilities design
- Dutch RVV 1990: Traffic rules
- EU Directive 96/53/EC: Vehicle dimensions

## Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_optimizer.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

## Dependencies

- **Streamlit** - Web UI framework
- **Plotly** - Interactive visualizations
- **Shapely** - Geometry operations
- **OR-Tools** - Constraint optimization solver
- **NumPy/Pandas** - Data handling

## API Reference

### Optimizer API

```python
from src.optimizer import optimize_layout, quick_estimate

# Quick area estimate
estimate = quick_estimate(
    boundary=[(0, 0), (50, 0), (50, 100), (0, 100)],
    lane_type="oneway"
)

# Full optimization
result = optimize_layout(
    boundary=[(0, 0), (27, 0), (74, 145), (0, 145)],
    entry_point=(13, 0),
    exit_point=(37, 145),
    optimization_goal="maximize_revenue",  # or "maximize_count", "maximize_trucks"
    lane_type="oneway",
    time_limit=30.0,
    vehicle_mix={"truck": (5, 50), "ev": (2, 10)},  # optional
    callback=lambda msg: print(msg),  # optional progress
)

print(f"Status: {result.status}")
print(f"Spaces: {result.space_count}")
print(f"Revenue: €{result.estimated_revenue:,.0f}/year")
```

### Lane Generator API

```python
from src.lane_generator import generate_lanes, LaneConfig

result = generate_lanes(
    boundary_coords=[(0, 0), (50, 0), (50, 100), (0, 100)],
    entry_point=(25, 0),
    exit_point=(25, 100),
    config=LaneConfig(lane_type="oneway")
)

print(f"Parking zones: {len(result.parking_zones)}")
print(f"Total parking area: {result.total_parking_area:.0f} m²")
```

## License

MIT License - Green Caravan

---

*Built for Green Caravan • Havenweg 4, Echt*
