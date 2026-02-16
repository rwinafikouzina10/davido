"""
TruckParking Optimizer - Main Streamlit Application
A tool for optimizing truck parking lot layouts.
"""

import streamlit as st
import json
from pathlib import Path
from datetime import datetime

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
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .stMetric {
        background-color: #f0f2f6;
        padding: 10px;
        border-radius: 5px;
    }
    .status-valid { color: #27ae60; font-weight: bold; }
    .status-warning { color: #f39c12; font-weight: bold; }
    .status-error { color: #e74c3c; font-weight: bold; }
    div[data-testid="stExpander"] {
        background-color: #f9f9f9;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)


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


def render_sidebar():
    """Render the sidebar with controls."""
    with st.sidebar:
        st.title("🚛 TruckParking Optimizer")
        st.markdown("---")
        
        # Layout name
        st.session_state.layout.name = st.text_input(
            "Layout Name",
            value=st.session_state.layout.name,
        )
        
        # Tabs for different operations
        tab1, tab2, tab3 = st.tabs(["➕ Add", "📂 Load/Save", "⚙️ Settings"])
        
        with tab1:
            render_add_space_form()
        
        with tab2:
            render_load_save()
        
        with tab3:
            render_settings()


def render_add_space_form():
    """Render the form to add a new parking space."""
    st.subheader("Add New Space")
    
    space_type = st.selectbox(
        "Type",
        options=list(SPACE_TYPES.keys()),
        format_func=lambda x: SPACE_TYPES[x]["name"],
    )
    
    specs = SPACE_TYPES[space_type]
    
    col1, col2 = st.columns(2)
    with col1:
        x = st.number_input("X Position (m)", min_value=0.0, max_value=100.0, value=5.0, step=1.0)
        length = st.number_input("Length (m)", min_value=1.0, max_value=30.0, value=specs["default_length"], step=0.5)
    with col2:
        y = st.number_input("Y Position (m)", min_value=0.0, max_value=200.0, value=5.0, step=1.0)
        width = st.number_input("Width (m)", min_value=1.0, max_value=10.0, value=specs["default_width"], step=0.5)
    
    rotation = st.slider("Rotation (°)", min_value=0, max_value=90, value=0, step=15)
    
    if st.button("➕ Add Space", type="primary", use_container_width=True):
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
        st.success(f"Added space {new_space.label}")
        st.rerun()


def render_load_save():
    """Render load/save functionality."""
    st.subheader("Data Management")
    
    # Export to JSON
    if st.button("📥 Export Layout (JSON)", use_container_width=True):
        json_str = st.session_state.layout.to_json()
        st.download_button(
            label="Download JSON",
            data=json_str,
            file_name=f"{st.session_state.layout.name.replace(' ', '_')}.json",
            mime="application/json",
        )
    
    # Import from JSON
    uploaded_file = st.file_uploader("📤 Import Layout", type=["json"])
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
    
    if st.button("💾 Save as Scenario", use_container_width=True):
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
                st.text(f"📋 {scenario.name}")
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
    if st.button("🗑️ Clear All Spaces", use_container_width=True):
        st.session_state.layout.spaces = []
        st.rerun()


def render_main_canvas():
    """Render the main layout canvas."""
    layout = st.session_state.layout
    
    # Run compliance check
    compliance = check_layout(layout)
    
    # Create and display the figure
    fig = create_layout_figure(
        layout,
        compliance_report=compliance,
        highlight_space=st.session_state.selected_space,
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    return compliance


def render_space_list(compliance: ComplianceReport):
    """Render the list of parking spaces with edit/delete options."""
    st.subheader("🅿️ Parking Spaces")
    
    layout = st.session_state.layout
    
    if not layout.spaces:
        st.info("No parking spaces yet. Add some using the sidebar!")
        return
    
    # Group by type
    by_type = {}
    for space in layout.spaces:
        if space.type not in by_type:
            by_type[space.type] = []
        by_type[space.type].append(space)
    
    # Get violation IDs
    violation_ids = set()
    for v in compliance.violations:
        violation_ids.update(v.space_ids)
    
    for space_type, spaces in by_type.items():
        type_name = SPACE_TYPES.get(space_type, {}).get("name", space_type)
        with st.expander(f"**{type_name}** ({len(spaces)} spaces)", expanded=True):
            for space in spaces:
                has_violation = space.id in violation_ids
                icon = "⚠️" if has_violation else "✅"
                
                col1, col2, col3, col4 = st.columns([2, 3, 1, 1])
                with col1:
                    st.markdown(f"{icon} **{space.label}**")
                with col2:
                    st.caption(f"{space.length}m × {space.width}m @ ({space.x}, {space.y})")
                with col3:
                    if st.button("✏️", key=f"edit_{space.id}", help="Edit"):
                        st.session_state.selected_space = space.id
                with col4:
                    if st.button("🗑️", key=f"del_{space.id}", help="Delete"):
                        layout.remove_space(space.id)
                        st.rerun()


def render_space_editor():
    """Render editor for selected space."""
    if st.session_state.selected_space is None:
        return
    
    space = st.session_state.layout.get_space_by_id(st.session_state.selected_space)
    if space is None:
        st.session_state.selected_space = None
        return
    
    st.subheader(f"✏️ Edit Space: {space.label}")
    
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
    
    space.rotation = st.slider("Rotation", 0, 90, int(space.rotation), 15, key="edit_rotation")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Done Editing", use_container_width=True):
            st.session_state.selected_space = None
            st.rerun()
    with col2:
        if st.button("🗑️ Delete Space", use_container_width=True, type="secondary"):
            st.session_state.layout.remove_space(space.id)
            st.session_state.selected_space = None
            st.rerun()


def render_compliance_panel(compliance: ComplianceReport):
    """Render the compliance status panel."""
    st.subheader("📋 Compliance Check")
    
    # Overall status
    if compliance.errors > 0:
        st.error(f"❌ **{compliance.errors} Errors** found")
    elif compliance.warnings > 0:
        st.warning(f"⚠️ **{compliance.warnings} Warnings** found")
    else:
        st.success("✅ All checks passed!")
    
    # Show violations
    if compliance.violations:
        for v in compliance.violations:
            icon = "❌" if v.severity == "error" else "⚠️"
            st.markdown(f"{icon} `{v.category}`: {v.message}")


def render_revenue_panel():
    """Render the revenue calculator panel."""
    st.subheader("💰 Revenue Calculator")
    
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
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Daily", f"€{projection.daily:,.0f}")
    with col2:
        st.metric("Weekly", f"€{projection.weekly:,.0f}")
    with col3:
        st.metric("Monthly", f"€{projection.monthly:,.0f}")
    with col4:
        delta_color = "normal" if projection.meets_target else "inverse"
        st.metric(
            "Annual",
            f"€{projection.annual:,.0f}",
            f"{projection.target_percentage - 100:.1f}% vs target",
            delta_color=delta_color,
        )
    
    # Target status
    st.markdown(f"**Target: €{projection.target:,.0f}/year** → {projection.status}")
    
    # Breakeven occupancy
    breakeven = calculate_breakeven_occupancy(layout)
    st.caption(f"💡 Breakeven occupancy: **{breakeven * 100:.1f}%**")
    
    # Revenue chart
    with st.expander("📊 Revenue Breakdown", expanded=False):
        fig = create_revenue_chart(projection, layout)
        st.plotly_chart(fig, use_container_width=True)


def render_scenario_comparison():
    """Render scenario comparison panel."""
    if not st.session_state.scenarios:
        st.info("Save scenarios using the sidebar to compare them here.")
        return
    
    st.subheader("📊 Scenario Comparison")
    
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
    
    st.markdown("### 📈 Summary")
    
    cols = st.columns(len(counts) + 1)
    with cols[0]:
        st.metric("Total Spaces", total)
    
    for i, (space_type, count) in enumerate(counts.items()):
        with cols[i + 1]:
            name = SPACE_TYPES.get(space_type, {}).get("name", space_type).split()[0]
            st.metric(name, count)


def main():
    """Main application entry point."""
    init_session_state()
    render_sidebar()
    
    # Main content area
    st.title("🚛 TruckParking Layout Optimizer")
    st.markdown(f"*Location: Havenweg 4, Echt • Target: €{SITE['revenue_target']:,}/year*")
    
    # Summary stats at top
    render_summary_stats()
    
    st.markdown("---")
    
    # Main layout area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        compliance = render_main_canvas()
        
        # Space editor (if space selected)
        render_space_editor()
    
    with col2:
        # Compliance panel
        render_compliance_panel(compliance)
        
        st.markdown("---")
        
        # Revenue panel
        render_revenue_panel()
    
    st.markdown("---")
    
    # Bottom section: Space list and scenarios
    col1, col2 = st.columns([1, 1])
    
    with col1:
        render_space_list(compliance)
    
    with col2:
        render_scenario_comparison()


if __name__ == "__main__":
    main()
