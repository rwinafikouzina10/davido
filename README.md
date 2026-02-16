# 🚛 TruckParking Optimizer

An interactive tool for optimizing truck parking lot layouts, ensuring regulatory compliance, and maximizing revenue potential.

## Features

- **Layout Visualizer** - Interactive canvas showing parking lot with spaces color-coded by type
- **Parking Space Management** - Add, edit, delete parking spots (trucks, tractors, trailers, EV, vans)
- **Compliance Checker** - Real-time validation of Dutch/EU parking regulations
- **Revenue Calculator** - Project revenue based on occupancy rates
- **Scenario Planning** - Save and compare different layout configurations
- **Data Export/Import** - JSON format for layouts

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

## Project Structure

```
truckparking-optimizer/
├── app.py                 # Main Streamlit application
├── src/
│   ├── models.py          # Data models (Layout, ParkingSpace, etc.)
│   ├── compliance.py      # Compliance checking engine
│   ├── revenue.py         # Revenue calculations
│   ├── visualization.py   # Plotly visualization utilities
│   └── config.py          # Configuration and constants
├── data/
│   └── vehicle_specs.json # Vehicle specifications and pricing
├── layouts/
│   └── example.json       # Example layout
├── docs/
│   ├── REQUIREMENTS.md    # Project requirements
│   └── PRD.md             # Product requirements document
├── requirements.txt
└── pyproject.toml
```

## Usage

### Adding Parking Spaces

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

1. Configure a layout
2. Click "Save as Scenario" in sidebar
3. Save multiple scenarios
4. Compare them in the comparison panel

## Site Specifications

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

## License

MIT License - Green Caravan

---

*Built for Green Caravan • Havenweg 4, Echt*
