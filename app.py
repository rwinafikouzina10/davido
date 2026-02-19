"""
TruckParking Optimizer - Main Streamlit Application
A tool for optimizing truck parking lot layouts.
"""

import streamlit as st
import json
import pandas as pd

# Local imports
from src.models import Layout, ParkingSpace, Scenario
from src.compliance import check_layout, ComplianceReport
from src.revenue import calculate_revenue, calculate_breakeven_occupancy
from src.visualization import (
    create_layout_figure,
    create_revenue_chart,
    create_scenario_comparison_chart,
)
from src.config import SPACE_TYPES, SITE, LAYOUTS_DIR

# Page config
st.set_page_config(
    page_title="TruckParking Optimizer",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&display=swap');
    :root {
        --tp-bg-top: #f8fbff;
        --tp-bg-bottom: #edf2f7;
        --tp-ink: #0f172a;
        --tp-muted: #475569;
        --tp-border: #d9e2ee;
        --tp-card: #ffffff;
        --tp-primary: #0ea5e9;
        --tp-primary-ink: #ffffff;
        --tp-sidebar-top: #0a1b31;
        --tp-sidebar-bottom: #123153;
    }
    .block-container {
        padding-top: 0.85rem;
        padding-bottom: 2rem;
        max-width: 1360px;
    }
    .stApp {
        background:
            radial-gradient(1200px 450px at 0% -10%, rgba(56, 189, 248, 0.10), transparent 65%),
            radial-gradient(900px 300px at 100% 0%, rgba(16, 185, 129, 0.08), transparent 65%),
            linear-gradient(180deg, var(--tp-bg-top) 0%, var(--tp-bg-bottom) 100%);
        color: var(--tp-ink);
        font-family: 'Manrope', 'Segoe UI', sans-serif;
    }
    [data-testid="stAppViewContainer"] > .main {
        background: transparent;
    }
    h1, h2, h3 {
        color: var(--tp-ink) !important;
        letter-spacing: 0;
        font-weight: 800 !important;
    }
    p, li, label, .stMarkdown, .stCaption, [data-testid="stWidgetLabel"] {
        font-family: 'Manrope', 'Segoe UI', sans-serif !important;
    }
    .stMarkdown, .stMarkdown p, .stCaption, [data-testid="stWidgetLabel"] {
        color: var(--tp-ink) !important;
    }
    .stCaption {
        color: #334155 !important;
    }
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, var(--tp-sidebar-top) 0%, var(--tp-sidebar-bottom) 100%);
        border-right: 1px solid rgba(255, 255, 255, 0.14);
    }
    [data-testid="stSidebar"] * {
        color: #e2e8f0 !important;
    }
    [data-testid="stSidebar"] [data-baseweb="input"] > div,
    [data-testid="stSidebar"] [data-baseweb="textarea"] > div,
    [data-testid="stSidebar"] [data-baseweb="select"] > div {
        background: rgba(2, 12, 27, 0.75) !important;
        border: 1px solid rgba(148, 163, 184, 0.32) !important;
    }
    [data-testid="stSidebar"] [data-baseweb="input"] input,
    [data-testid="stSidebar"] [data-baseweb="textarea"] textarea,
    [data-testid="stSidebar"] [data-baseweb="select"] * {
        color: #e2e8f0 !important;
    }
    [data-testid="stSidebar"] [data-baseweb="tag"] {
        background: rgba(14, 165, 233, 0.25) !important;
        color: #e0f2fe !important;
    }
    [data-testid="stSidebar"] [data-baseweb="button-group"] button {
        background: rgba(2, 12, 27, 0.75) !important;
        color: #e2e8f0 !important;
        border: 1px solid rgba(148, 163, 184, 0.32) !important;
    }
    [data-testid="stSidebar"] [data-baseweb="button-group"] button[aria-pressed="true"] {
        background: #0ea5e9 !important;
        color: #ffffff !important;
        border-color: #38bdf8 !important;
    }
    [data-testid="stSidebar"] [data-testid="stAlertContainer"] {
        background: rgba(14, 116, 180, 0.35) !important;
        border: 1px solid rgba(56, 189, 248, 0.35) !important;
        border-radius: 10px;
    }
    [data-testid="stSidebar"] [data-testid="stAlertContainer"] * {
        color: #e0f2fe !important;
    }
    .tp-kicker {
        font-size: 0.8rem;
        font-weight: 700;
        color: var(--tp-muted);
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 0.15rem;
    }
    .tp-section {
        background: rgba(255, 255, 255, 0.74);
        border: 1px solid var(--tp-border);
        border-radius: 14px;
        padding: 0.75rem 0.9rem;
        box-shadow: 0 6px 16px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMetric"] {
        background-color: var(--tp-card);
        padding: 14px;
        border-radius: 12px;
        border: 1px solid var(--tp-border);
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
    }
    [data-testid="stMetricLabel"] {
        color: #334155 !important;
        font-weight: 700 !important;
    }
    [data-testid="stMetricValue"] {
        color: var(--tp-ink) !important;
        font-size: 1.4rem !important;
    }
    div[data-testid="stExpander"] {
        background-color: var(--tp-card);
        border: 1px solid var(--tp-border);
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.03);
    }
    div[data-testid="stExpander"] details > summary {
        background: #f8fafc !important;
        border: 1px solid #dbe3ee !important;
        border-radius: 10px !important;
        padding: 0.45rem 0.7rem !important;
    }
    div[data-testid="stExpander"] details > summary,
    div[data-testid="stExpander"] details > summary * {
        color: #0f172a !important;
        opacity: 1 !important;
    }
    [data-testid="stDataFrame"] {
        border-radius: 10px;
        overflow: hidden;
    }
    [data-testid="stHorizontalBlock"] [data-testid="stMetric"] {
        min-height: 112px;
    }
    .stButton > button[kind="primary"] {
        border-radius: 10px;
        border: none;
        background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%);
        color: var(--tp-primary-ink);
        font-weight: 700;
    }
    .stButton > button {
        border-radius: 10px;
    }
    .stButton > button:not([kind="primary"]) {
        background: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
        font-weight: 700 !important;
    }
    .stButton > button:not([kind="primary"]):hover {
        border-color: #94a3b8 !important;
        background: #f8fafc !important;
    }
    [data-testid="stTabs"] button[role="tab"] {
        border-radius: 10px 10px 0 0;
        font-weight: 700;
        color: #334155;
    }
    [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
        color: #0f172a !important;
    }
    [data-testid="stRadio"] label,
    [data-testid="stRadio"] label *,
    [role="radiogroup"] label,
    [role="radiogroup"] label * {
        color: #0f172a !important;
        opacity: 1 !important;
    }
    [data-testid="stDataEditor"] {
        border-radius: 12px;
        border: 1px solid var(--tp-border);
        overflow: hidden;
        background: #fff;
    }
    [data-testid="stDataEditor"] * {
        color: #0f172a !important;
    }
    [data-baseweb="input"] > div,
    [data-baseweb="textarea"] > div,
    [data-baseweb="select"] > div {
        background: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        color: #0f172a !important;
    }
    [data-baseweb="input"] input,
    [data-baseweb="textarea"] textarea,
    [data-baseweb="select"] * {
        color: #0f172a !important;
    }
    [data-baseweb="tag"] {
        background: #e2e8f0 !important;
        color: #0f172a !important;
    }
    [data-baseweb="button-group"] button {
        background: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #cbd5e1 !important;
    }
    [data-baseweb="button-group"] button[aria-pressed="true"] {
        background: #0ea5e9 !important;
        color: #ffffff !important;
        border-color: #0284c7 !important;
    }
    div[data-testid="stExpander"] summary,
    div[data-testid="stExpander"] summary * {
        color: #0f172a !important;
    }
    [data-testid="stAlertContainer"] * {
        color: #0f172a !important;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] label,
    [data-testid="stSidebar"] [data-testid="stRadio"] label *,
    [data-testid="stSidebar"] [role="radiogroup"] label,
    [data-testid="stSidebar"] [role="radiogroup"] label * {
        color: #e2e8f0 !important;
        opacity: 1 !important;
    }
</style>
""", unsafe_allow_html=True)


# Preset boundaries for quick selection
PRESET_BOUNDARIES = {
    "Havenweg (Triangular)": {
        "boundary": [(0, 0), (27, 0), (74, 145), (0, 145)],
        "entry": (13, 0),
        "exit": (37, 145),
        "description": "Original Havenweg 4, Echt site - triangular shape"
    },
    "Rectangle (50x100)": {
        "boundary": [(0, 0), (50, 0), (50, 100), (0, 100)],
        "entry": (25, 0),
        "exit": (25, 100),
        "description": "Standard rectangular lot"
    },
    "Rectangle (80x120)": {
        "boundary": [(0, 0), (80, 0), (80, 120), (0, 120)],
        "entry": (40, 0),
        "exit": (40, 120),
        "description": "Large rectangular lot"
    },
    "L-Shape": {
        "boundary": [(0, 0), (60, 0), (60, 60), (30, 60), (30, 100), (0, 100)],
        "entry": (30, 0),
        "exit": (15, 100),
        "description": "L-shaped lot with two wings"
    },
    "Wide Triangle": {
        "boundary": [(0, 0), (100, 0), (50, 80)],
        "entry": (50, 0),
        "exit": (50, 80),
        "description": "Wide triangular lot"
    },
}


def parse_manual_boundary(coords_input: str):
    """Parse semicolon-separated x,y pairs into a boundary list."""
    points = []
    for part in coords_input.split(";"):
        raw = part.strip()
        if not raw:
            continue
        chunks = [c.strip() for c in raw.split(",")]
        if len(chunks) != 2:
            raise ValueError(f"Invalid point format: '{raw}'")
        points.append((float(chunks[0]), float(chunks[1])))
    if len(points) < 3:
        raise ValueError("At least 3 points are required to define a polygon")
    return points


def extract_polygon_coords(geojson_obj):
    """Extract polygon coordinates from GeoJSON object."""
    obj_type = geojson_obj.get("type")

    if obj_type == "FeatureCollection":
        features = geojson_obj.get("features", [])
        for feature in features:
            geom = feature.get("geometry", {})
            coords = extract_polygon_coords(geom)
            if coords:
                return coords
        raise ValueError("No Polygon geometry found in FeatureCollection")

    if obj_type == "Feature":
        return extract_polygon_coords(geojson_obj.get("geometry", {}))

    if obj_type == "Polygon":
        rings = geojson_obj.get("coordinates", [])
        if not rings or len(rings[0]) < 3:
            raise ValueError("Polygon coordinates are missing or invalid")
        return [(float(c[0]), float(c[1])) for c in rings[0]]

    raise ValueError(f"Unsupported GeoJSON type: {obj_type}")


def rotate_space(space: ParkingSpace, delta_degrees: int):
    """Rotate a space by delta degrees with 0-345 wrap-around."""
    space.rotation = float((int(space.rotation) + delta_degrees) % 360)


def format_currency_compact(value: float) -> str:
    """Compact human-readable currency."""
    abs_val = abs(value)
    if abs_val >= 1_000_000:
        return f"EUR {value / 1_000_000:.2f}M"
    if abs_val >= 1_000:
        return f"EUR {value / 1_000:.1f}K"
    return f"EUR {value:,.0f}"


def refresh_space_labels(layout: Layout):
    """Keep labels aligned with current ids/types."""
    prefix_map = {"truck": "T", "tractor": "TR", "trailer": "TL", "ev": "EV", "van": "V"}
    for s in layout.spaces:
        s.label = f"{prefix_map.get(s.type, 'S')}-{s.id}"


def init_session_state():
    """Initialize session state variables."""
    if "layout" not in st.session_state:
        # Try to load example layout
        example_path = LAYOUTS_DIR / "example.json"
        if example_path.exists():
            with open(example_path) as f:
                st.session_state.layout = Layout.from_dict(json.load(f))
        else:
            st.session_state.layout = Layout(name="New Layout")
    
    if "scenarios" not in st.session_state:
        st.session_state.scenarios = []
    
    if "selected_space" not in st.session_state:
        st.session_state.selected_space = None
    
    if "occupancy_rate" not in st.session_state:
        st.session_state.occupancy_rate = 75
    
    if "optimization_log" not in st.session_state:
        st.session_state.optimization_log = []
    
    if "custom_boundary" not in st.session_state:
        st.session_state.custom_boundary = None


def render_sidebar():
    """Render the sidebar with controls."""
    with st.sidebar:
        st.title("TruckParking Optimizer")
        st.markdown("---")
        
        # Layout name
        st.session_state.layout.name = st.text_input(
            "Layout Name",
            value=st.session_state.layout.name,
        )
        
        # Tabs for different operations
        tab1, tab2, tab3, tab4 = st.tabs(["Auto", "Add", "Load/Save", "Settings"])
        
        with tab1:
            render_auto_generate_sidebar()
        
        with tab2:
            render_add_space_form()
        
        with tab3:
            render_load_save()
        
        with tab4:
            render_settings()


def render_auto_generate_sidebar():
    """Render the auto-generate controls in sidebar."""
    st.subheader("Auto-Generate Layout")
    
    st.info("Use the Auto-Generate panel in the main area for full controls, or quick-generate here.")
    
    # Quick preset selection
    preset = st.selectbox(
        "Quick Preset",
        options=list(PRESET_BOUNDARIES.keys()),
        key="sidebar_preset"
    )
    
    preset_data = PRESET_BOUNDARIES[preset]
    st.caption(preset_data["description"])
    
    # Quick optimization goal
    goal = st.radio(
        "Goal",
        options=["Maximize Revenue", "Maximize Spaces", "Prioritize Trucks"],
        horizontal=True,
        key="sidebar_goal"
    )
    
    goal_map = {
        "Maximize Revenue": "maximize_revenue",
        "Maximize Spaces": "maximize_count",
        "Prioritize Trucks": "maximize_trucks",
    }
    
    if st.button("Quick Generate", type="primary", use_container_width=True):
        run_optimization(
            boundary=preset_data["boundary"],
            entry_point=preset_data["entry"],
            exit_point=preset_data["exit"],
            optimization_goal=goal_map[goal],
            lane_type="oneway",
            time_limit=15.0,
        )
        st.rerun()


def render_add_space_form():
    """Render the form to add a new parking space."""
    st.subheader("Add New Space")
    
    space_type = st.selectbox(
        "Type",
        options=list(SPACE_TYPES.keys()),
        format_func=lambda x: SPACE_TYPES[x]["name"],
    )
    
    specs = SPACE_TYPES[space_type]
    
    boundary_x = [p[0] for p in st.session_state.layout.boundary] if st.session_state.layout.boundary else [0, st.session_state.layout.lot_width]
    boundary_y = [p[1] for p in st.session_state.layout.boundary] if st.session_state.layout.boundary else [0, st.session_state.layout.lot_length]
    max_x = max(boundary_x)
    max_y = max(boundary_y)

    col1, col2 = st.columns(2)
    with col1:
        x = st.number_input("X Position (m)", min_value=0.0, max_value=float(max_x), value=5.0, step=1.0)
        length = st.number_input("Length (m)", min_value=1.0, max_value=30.0, value=specs["default_length"], step=0.5)
    with col2:
        y = st.number_input("Y Position (m)", min_value=0.0, max_value=float(max_y), value=5.0, step=1.0)
        width = st.number_input("Width (m)", min_value=1.0, max_value=10.0, value=specs["default_width"], step=0.5)
    
    rotation = st.slider("Rotation (°)", min_value=0, max_value=345, value=0, step=15)
    
    if st.button("Add Space", type="primary", use_container_width=True):
        new_id = st.session_state.layout.get_next_id()
        new_space = ParkingSpace(
            id=new_id,
            type=space_type,
            x=x,
            y=y,
            length=length,
            width=width,
            rotation=rotation,
        )
        st.session_state.layout.add_space(new_space)
        refresh_space_labels(st.session_state.layout)
        st.success(f"Added space {new_space.label}")
        st.rerun()


def render_load_save():
    """Render load/save functionality."""
    st.subheader("Data Management")
    
    # Export to JSON
    json_str = st.session_state.layout.to_json()
    st.download_button(
        label="Export Layout (JSON)",
        data=json_str,
        file_name=f"{st.session_state.layout.name.replace(' ', '_')}.json",
        mime="application/json",
        use_container_width=True,
    )
    
    # Import from JSON
    uploaded_file = st.file_uploader("Import Layout", type=["json"])
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            st.session_state.layout = Layout.from_dict(data)
            st.success("Layout imported successfully!")
            st.rerun()
        except Exception as e:
            st.error(f"Error importing: {e}")
    
    st.markdown("---")
    
    # Save as scenario
    st.subheader("Scenarios")
    scenario_name = st.text_input("Scenario Name", value=f"Scenario {len(st.session_state.scenarios) + 1}")
    
    if st.button("Save as Scenario", use_container_width=True):
        scenario = Scenario(
            name=scenario_name,
            layout=Layout.from_dict(st.session_state.layout.to_dict()),  # Deep copy
            occupancy_rate=st.session_state.occupancy_rate / 100,
        )
        st.session_state.scenarios.append(scenario)
        st.success(f"Saved scenario: {scenario_name}")
    
    # List saved scenarios
    if st.session_state.scenarios:
        st.markdown("**Saved Scenarios:**")
        for i, scenario in enumerate(st.session_state.scenarios):
            col1, col2 = st.columns([3, 1])
            with col1:
                st.text(scenario.name)
            with col2:
                if st.button("Load", key=f"load_{i}"):
                    st.session_state.layout = Layout.from_dict(scenario.layout.to_dict())
                    st.session_state.occupancy_rate = int(scenario.occupancy_rate * 100)
                    st.rerun()


def render_settings():
    """Render settings panel."""
    st.subheader("Layout Settings")
    
    st.session_state.layout.lot_width = st.number_input(
        "Lot Width (m)",
        min_value=10.0,
        max_value=200.0,
        value=float(st.session_state.layout.lot_width),
        step=1.0,
    )
    
    st.session_state.layout.lot_length = st.number_input(
        "Lot Length (m)",
        min_value=10.0,
        max_value=300.0,
        value=float(st.session_state.layout.lot_length),
        step=1.0,
    )
    
    st.markdown("---")
    
    # Clear all spaces
    if st.button("Clear All Spaces", use_container_width=True):
        st.session_state.layout.spaces = []
        st.rerun()


def run_optimization(
    boundary,
    entry_point,
    exit_point,
    optimization_goal,
    lane_type,
    time_limit,
    vehicle_mix=None,
    orientations=None,
):
    """Run the optimization and update session state."""
    try:
        from src.optimizer import optimize_layout
        
        st.session_state.optimization_log = []
        
        def log_callback(message):
            st.session_state.optimization_log.append(message)
        
        result = optimize_layout(
            boundary=boundary,
            entry_point=entry_point,
            exit_point=exit_point,
            optimization_goal=optimization_goal,
            lane_type=lane_type,
            orientations=orientations,
            time_limit=time_limit,
            vehicle_mix=vehicle_mix,
            layout_name=st.session_state.layout.name or "Optimized Layout",
            callback=log_callback,
        )
        
        if result.success:
            st.session_state.layout = result.layout
            st.session_state.optimization_log.append(
                f"Optimization complete: {result.space_count} spaces, "
                f"EUR {result.estimated_revenue:,.0f}/year estimated revenue"
            )
            st.session_state.optimization_log.append(
                f"Solved in {result.solve_time:.1f}s (status: {result.status})"
            )
        else:
            st.session_state.optimization_log.append(
                f"Optimization failed: {result.status}"
            )
            for warning in result.warnings:
                st.session_state.optimization_log.append(f"Warning: {warning}")
                
    except ImportError as e:
        st.session_state.optimization_log.append(
            f"Missing dependency: {e}. Install with: pip install shapely ortools"
        )
    except Exception as e:
        st.session_state.optimization_log.append(f"Error: {e}")


def render_auto_generate_panel():
    """Render the auto-generate panel in the main content area."""
    with st.expander("Auto-Generate Layout - Create optimized layout from boundary", expanded=False):
        st.markdown("""
        Define your lot boundary and let the optimizer automatically place parking spaces 
        and lanes for maximum efficiency.
        """)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("#### Boundary Definition")
            
            input_method = st.radio(
                "Input Method",
                options=["Preset Shapes", "Manual Coordinates", "Upload GeoJSON"],
                horizontal=True,
            )
            
            boundary = None
            entry_point = None
            exit_point = None
            
            if input_method == "Preset Shapes":
                preset = st.selectbox(
                    "Select Preset",
                    options=list(PRESET_BOUNDARIES.keys()),
                    key="main_preset"
                )
                preset_data = PRESET_BOUNDARIES[preset]
                boundary = preset_data["boundary"]
                entry_point = preset_data["entry"]
                exit_point = preset_data["exit"]
                
                st.caption(preset_data["description"])
                st.caption(f"Entry: {entry_point}, Exit: {exit_point}")
                
            elif input_method == "Manual Coordinates":
                st.markdown("Enter corner points (x, y) separated by semicolons:")
                coords_input = st.text_area(
                    "Boundary Points",
                    value="0,0; 27,0; 74,145; 0,145",
                    help="Format: x1,y1; x2,y2; x3,y3; ..."
                )
                
                try:
                    boundary = parse_manual_boundary(coords_input)
                    st.success(f"Parsed {len(boundary)} points")
                except ValueError as exc:
                    st.error(str(exc))
                
                # Entry/exit points
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    entry_x = st.number_input("Entry X", value=13.0, key="entry_x")
                    entry_y = st.number_input("Entry Y", value=0.0, key="entry_y")
                    entry_point = (entry_x, entry_y)
                with col_e2:
                    exit_x = st.number_input("Exit X", value=37.0, key="exit_x")
                    exit_y = st.number_input("Exit Y", value=145.0, key="exit_y")
                    exit_point = (exit_x, exit_y)
                    
            elif input_method == "Upload GeoJSON":
                uploaded_geojson = st.file_uploader("Upload GeoJSON", type=["json", "geojson"])
                if uploaded_geojson:
                    try:
                        geojson = json.load(uploaded_geojson)
                        boundary = extract_polygon_coords(geojson)
                        st.success(f"Loaded {len(boundary)} points from GeoJSON")
                        
                        # Default entry/exit at first and middle points
                        entry_point = boundary[0]
                        exit_point = boundary[len(boundary) // 2]
                    except Exception as e:
                        st.error(f"Error parsing GeoJSON: {e}")
                else:
                    st.info("Upload a GeoJSON file with a Polygon geometry")
                    
                # Entry/exit override
                if boundary:
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        entry_x = st.number_input("Entry X", value=entry_point[0] if entry_point else 0.0, key="geo_entry_x")
                        entry_y = st.number_input("Entry Y", value=entry_point[1] if entry_point else 0.0, key="geo_entry_y")
                        entry_point = (entry_x, entry_y)
                    with col_e2:
                        exit_x = st.number_input("Exit X", value=exit_point[0] if exit_point else 0.0, key="geo_exit_x")
                        exit_y = st.number_input("Exit Y", value=exit_point[1] if exit_point else 0.0, key="geo_exit_y")
                        exit_point = (exit_x, exit_y)
        
        with col2:
            st.markdown("#### Optimization Settings")
            
            optimization_goal = st.selectbox(
                "Optimization Goal",
                options=[
                    ("maximize_revenue", "Maximize Revenue"),
                    ("maximize_count", "Maximize Space Count"),
                    ("maximize_trucks", "Prioritize Large Trucks"),
                ],
                format_func=lambda x: x[1],
                key="opt_goal"
            )[0]
            
            lane_type = st.radio(
                "Lane Type",
                options=["oneway", "twoway"],
                format_func=lambda x: "One-Way (6m)" if x == "oneway" else "Two-Way (8m)",
                horizontal=True,
            )

            orientation_choices = st.multiselect(
                "Allowed Space Orientations",
                options=[0, 15, 30, 45, 60, 75, 90],
                default=[0, 90],
                help="Use this to allow angled parking in auto-generation.",
            )
            
            time_limit = st.slider(
                "Time Limit (seconds)",
                min_value=5,
                max_value=60,
                value=30,
                step=5,
            )
            
            st.markdown("#### Vehicle Mix (Optional)")
            
            use_vehicle_mix = st.checkbox("Specify vehicle mix limits")
            vehicle_mix = None
            invalid_vehicle_mix = False
            
            if use_vehicle_mix:
                vehicle_mix = {}
                mix_cols = st.columns(3)
                
                types_info = [
                    ("truck", "Trucks"),
                    ("ev", "EV"),
                    ("tractor", "Tractors"),
                    ("trailer", "Trailers"),
                    ("van", "Vans"),
                ]
                
                for i, (vtype, label) in enumerate(types_info):
                    with mix_cols[i % 3]:
                        min_v = st.number_input(f"Min {label}", min_value=0, value=0, key=f"min_{vtype}")
                        max_v = st.number_input(f"Max {label}", min_value=0, value=100, key=f"max_{vtype}")
                        vehicle_mix[vtype] = (min_v, max_v)
                        if min_v > max_v:
                            invalid_vehicle_mix = True
                            st.error(f"Invalid limits for {label}: min cannot exceed max")
        
        st.markdown("---")
        
        # Quick estimate
        if boundary:
            try:
                from src.optimizer import quick_estimate
                estimate = quick_estimate(boundary, lane_type)
                
                est_cols = st.columns(4)
                with est_cols[0]:
                    st.metric("Total Area", f"{estimate['total_area']:,.0f} m²", border=True)
                with est_cols[1]:
                    st.metric("Parking Area", f"{estimate['estimated_parking_area']:,.0f} m²", border=True)
                with est_cols[2]:
                    st.metric("Est. Max Trucks", estimate['max_truck_spaces'], border=True)
                with est_cols[3]:
                    st.metric("Est. Revenue", f"{format_currency_compact(estimate['estimated_annual_revenue'])}/yr", border=True)
            except:
                pass
        
        # Generate button
        col_btn1, col_btn2 = st.columns([2, 1])
        with col_btn1:
            generate_clicked = st.button(
                "Generate Optimized Layout",
                type="primary",
                use_container_width=True,
                disabled=(boundary is None or invalid_vehicle_mix),
            )
        with col_btn2:
            if st.button("Clear Current", use_container_width=True):
                st.session_state.layout.spaces = []
                st.session_state.layout.lanes = []
                st.rerun()
        
        if generate_clicked and boundary:
            with st.spinner("Optimizing layout... This may take up to 30 seconds."):
                run_optimization(
                    boundary=boundary,
                    entry_point=entry_point,
                    exit_point=exit_point,
                    optimization_goal=optimization_goal,
                    lane_type=lane_type,
                    orientations=orientation_choices or [0, 90],
                    time_limit=float(time_limit),
                    vehicle_mix=vehicle_mix if use_vehicle_mix else None,
                )
            st.rerun()
        
        # Show optimization log
        if st.session_state.optimization_log:
            st.markdown("#### Optimization Log")
            log_text = "\n".join(st.session_state.optimization_log)
            st.code(log_text, language=None)


def render_main_canvas(compliance: ComplianceReport):
    """Render the main layout canvas."""
    layout = st.session_state.layout

    # Create and display the figure
    fig = create_layout_figure(
        layout,
        compliance_report=compliance,
        highlight_space=st.session_state.selected_space,
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_space_list(compliance: ComplianceReport):
    """Render the list of parking spaces with edit/delete options."""
    st.subheader("Parking Spaces")
    
    layout = st.session_state.layout
    
    if not layout.spaces:
        st.info("No parking spaces yet. Use Auto-Generate or add manually!")
        return
    
    violation_ids = set()
    for v in compliance.violations:
        violation_ids.update(v.space_ids)

    rows = []
    for s in layout.spaces:
        rows.append({
            "id": s.id,
            "label": s.label,
            "type": s.type,
            "x": s.x,
            "y": s.y,
            "length": s.length,
            "width": s.width,
            "rotation": s.rotation,
            "status": "Issue" if s.id in violation_ids else "OK",
        })

    table = pd.DataFrame(rows)
    st.caption("Inline editing pattern: update values directly in the grid, then apply once.")
    edited = st.data_editor(
        table,
        hide_index=True,
        use_container_width=True,
        disabled=("id", "label", "status"),
        column_config={
            "id": st.column_config.NumberColumn("ID"),
            "label": st.column_config.TextColumn("Label"),
            "type": st.column_config.SelectboxColumn("Type", options=list(SPACE_TYPES.keys())),
            "x": st.column_config.NumberColumn("X (m)", step=0.5, format="%.1f"),
            "y": st.column_config.NumberColumn("Y (m)", step=0.5, format="%.1f"),
            "length": st.column_config.NumberColumn("Length (m)", step=0.5, format="%.1f"),
            "width": st.column_config.NumberColumn("Width (m)", step=0.5, format="%.1f"),
            "rotation": st.column_config.NumberColumn("Rotation", step=15, format="%.0f"),
            "status": st.column_config.TextColumn("Status"),
        },
        key="spaces_table_editor",
    )

    col_apply, col_edit, col_del = st.columns([1.3, 1, 1])
    with col_apply:
        if st.button("Apply Table Changes", type="primary", use_container_width=True):
            space_map = {s.id: s for s in layout.spaces}
            for _, row in edited.iterrows():
                sid = int(row["id"])
                if sid not in space_map:
                    continue
                s = space_map[sid]
                s.type = str(row["type"])
                s.x = float(row["x"])
                s.y = float(row["y"])
                s.length = float(row["length"])
                s.width = float(row["width"])
                s.rotation = float(row["rotation"]) % 360
            refresh_space_labels(layout)
            st.success("Parking space changes applied")
            st.rerun()
    with col_edit:
        edit_target = st.selectbox("Edit Space", options=[s.id for s in layout.spaces], format_func=lambda sid: f"Space {sid}")
        if st.button("Open Editor", use_container_width=True):
            st.session_state.selected_space = int(edit_target)
            st.rerun()
    with col_del:
        delete_ids = st.multiselect("Delete IDs", options=[s.id for s in layout.spaces], default=[])
        if st.button("Delete Selected", use_container_width=True):
            for sid in delete_ids:
                layout.remove_space(int(sid))
            refresh_space_labels(layout)
            st.success(f"Deleted {len(delete_ids)} space(s)")
            st.rerun()

    st.markdown("#### Quick Rotate")
    rot_col1, rot_col2, rot_col3, rot_col4 = st.columns([2, 1, 1, 1])
    with rot_col1:
        rotate_ids = st.multiselect("IDs", options=[s.id for s in layout.spaces], default=[])
    with rot_col2:
        rotate_step = st.segmented_control("Step", [15, 30, 45], default=15, key="rotate_step")
    with rot_col3:
        rotate_left = st.button("Rotate -", use_container_width=True)
    with rot_col4:
        rotate_right = st.button("Rotate +", use_container_width=True)
    if rotate_left and rotate_ids:
        for sid in rotate_ids:
            sp = layout.get_space_by_id(int(sid))
            if sp:
                rotate_space(sp, -int(rotate_step or 15))
        st.rerun()
    if rotate_right and rotate_ids:
        for sid in rotate_ids:
            sp = layout.get_space_by_id(int(sid))
            if sp:
                rotate_space(sp, int(rotate_step or 15))
        st.rerun()


def render_space_editor():
    """Render editor for selected space."""
    if st.session_state.selected_space is None:
        return
    
    space = st.session_state.layout.get_space_by_id(st.session_state.selected_space)
    if space is None:
        st.session_state.selected_space = None
        return
    
    st.subheader(f"Edit Space: {space.label}")
    
    col1, col2 = st.columns(2)
    with col1:
        space.x = st.number_input("X Position", value=space.x, step=1.0, key="edit_x")
        space.length = st.number_input("Length", value=space.length, step=0.5, key="edit_length")
    with col2:
        space.y = st.number_input("Y Position", value=space.y, step=1.0, key="edit_y")
        space.width = st.number_input("Width", value=space.width, step=0.5, key="edit_width")
    
    space.type = st.selectbox(
        "Type",
        options=list(SPACE_TYPES.keys()),
        index=list(SPACE_TYPES.keys()).index(space.type),
        format_func=lambda x: SPACE_TYPES[x]["name"],
        key="edit_type",
    )
    
    space.rotation = st.slider("Rotation", 0, 345, int(space.rotation) % 360, 15, key="edit_rotation")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Done Editing", use_container_width=True):
            refresh_space_labels(st.session_state.layout)
            st.session_state.selected_space = None
            st.rerun()
    with col2:
        if st.button("Delete Space", use_container_width=True, type="secondary"):
            st.session_state.layout.remove_space(space.id)
            st.session_state.selected_space = None
            st.rerun()


def render_compliance_panel(compliance: ComplianceReport):
    """Render the compliance status panel."""
    st.subheader("Compliance Check")
    
    # Overall status
    if compliance.errors > 0:
        st.error(f"**{compliance.errors} Errors** found")
    elif compliance.warnings > 0:
        st.warning(f"**{compliance.warnings} Warnings** found")
    else:
        st.success("All checks passed")
    
    if compliance.violations:
        by_category = {}
        for v in compliance.violations:
            by_category[v.category] = by_category.get(v.category, 0) + 1
        st.caption("Category counts: " + ", ".join(f"{k} {n}" for k, n in by_category.items()))
        with st.expander("Violation Details", expanded=False):
            for v in compliance.violations:
                prefix = "Error" if v.severity == "error" else "Warning"
                st.markdown(f"**{prefix}** `{v.category}`: {v.message}")


def render_revenue_panel():
    """Render the revenue calculator panel."""
    st.subheader("Revenue Calculator")
    
    layout = st.session_state.layout
    
    # Occupancy slider
    st.session_state.occupancy_rate = st.slider(
        "Occupancy Rate (%)",
        min_value=10,
        max_value=100,
        value=st.session_state.occupancy_rate,
        step=5,
    )
    
    # Calculate revenue
    projection = calculate_revenue(layout, st.session_state.occupancy_rate / 100)
    
    # Key metrics
    col1, col2 = st.columns(2, gap="small")
    with col1:
        st.metric("Daily", format_currency_compact(projection.daily), border=True)
    with col2:
        st.metric("Weekly", format_currency_compact(projection.weekly), border=True)
    col3, col4 = st.columns(2, gap="small")
    with col3:
        st.metric("Monthly", format_currency_compact(projection.monthly), border=True)
    with col4:
        delta_color = "normal" if projection.meets_target else "inverse"
        st.metric(
            "Annual",
            format_currency_compact(projection.annual),
            f"{projection.target_percentage - 100:.1f}% vs target",
            delta_color=delta_color,
            border=True,
        )
    
    # Target status
    st.markdown(f"**Target: {format_currency_compact(projection.target)}/year** -> {projection.status}")
    
    # Breakeven occupancy
    breakeven = calculate_breakeven_occupancy(layout)
    st.caption(f"Breakeven occupancy: **{breakeven * 100:.1f}%**")
    
    # Revenue chart
    with st.expander("Revenue Breakdown", expanded=False):
        fig = create_revenue_chart(projection, layout)
        st.plotly_chart(fig, use_container_width=True)


def render_scenario_comparison():
    """Render scenario comparison panel."""
    if not st.session_state.scenarios:
        st.info("Save scenarios using the sidebar to compare them here.")
        return
    
    st.subheader("Scenario Comparison")
    
    comparison_data = []
    for scenario in st.session_state.scenarios:
        projection = calculate_revenue(scenario.layout, scenario.occupancy_rate)
        comparison_data.append({
            "name": scenario.name,
            "spaces": len(scenario.layout.spaces),
            "occupancy": scenario.occupancy_rate * 100,
            "annual_revenue": projection.annual,
            "target_pct": projection.target_percentage,
            "meets_target": projection.meets_target,
        })
    
    # Table
    st.dataframe(
        comparison_data,
        column_config={
            "name": "Scenario",
            "spaces": "Spaces",
            "occupancy": st.column_config.NumberColumn("Occupancy %", format="%.0f%%"),
            "annual_revenue": st.column_config.NumberColumn("Annual Revenue", format="€%.0f"),
            "target_pct": st.column_config.NumberColumn("vs Target", format="%.1f%%"),
            "meets_target": st.column_config.CheckboxColumn("Target Met"),
        },
        hide_index=True,
        use_container_width=True,
    )
    
    # Chart
    fig = create_scenario_comparison_chart(comparison_data)
    st.plotly_chart(fig, use_container_width=True)


def render_summary_stats():
    """Render summary statistics."""
    layout = st.session_state.layout
    counts = layout.count_by_type()
    total = sum(counts.values())
    
    st.markdown('<div class="tp-kicker">Dashboard</div>', unsafe_allow_html=True)
    st.markdown("### Summary")
    
    cols = st.columns(len(counts) + 1)
    with cols[0]:
        st.metric("Total Spaces", total, border=True)
    
    for i, (space_type, count) in enumerate(counts.items()):
        with cols[i + 1]:
            name = SPACE_TYPES.get(space_type, {}).get("name", space_type).split()[0]
            st.metric(name, count, border=True)


def main():
    """Main application entry point."""
    init_session_state()
    render_sidebar()
    
    # Main content area
    st.markdown('<div class="tp-kicker">Planning Workspace</div>', unsafe_allow_html=True)
    st.title("TruckParking Layout Optimizer")
    st.caption(f"Location: Havenweg 4, Echt | Revenue target: {format_currency_compact(SITE['revenue_target'])}/year")
    
    st.markdown('<div class="tp-section">', unsafe_allow_html=True)
    render_auto_generate_panel()
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown('<div class="tp-section">', unsafe_allow_html=True)
    render_summary_stats()
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    compliance = check_layout(st.session_state.layout)

    # Main layout area
    col1, col2 = st.columns([1.9, 1.1])

    with col1:
        main_tabs = st.tabs(["Parking Spaces", "Layout Canvas"])
        with main_tabs[0]:
            st.markdown('<div class="tp-section">', unsafe_allow_html=True)
            render_space_list(compliance)
            render_space_editor()
            st.markdown("</div>", unsafe_allow_html=True)
        with main_tabs[1]:
            st.markdown('<div class="tp-section">', unsafe_allow_html=True)
            render_main_canvas(compliance)
            st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        right_tabs = st.tabs(["Compliance & Revenue", "Scenarios"])
        with right_tabs[0]:
            st.markdown('<div class="tp-section">', unsafe_allow_html=True)
            render_compliance_panel(compliance)
            st.markdown("---")
            render_revenue_panel()
            st.markdown("</div>", unsafe_allow_html=True)
        with right_tabs[1]:
            st.markdown('<div class="tp-section">', unsafe_allow_html=True)
            render_scenario_comparison()
            st.markdown("</div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
