"""Visualization utilities for TruckParking Optimizer."""

import plotly.graph_objects as go
from typing import List, Optional
from .models import Layout, ParkingSpace
from .config import COLORS, SPACE_TYPES, DEFAULT_BOUNDARY
from .compliance import ComplianceReport


def create_layout_figure(
    layout: Layout,
    compliance_report: Optional[ComplianceReport] = None,
    highlight_space: Optional[int] = None,
    show_labels: bool = True,
    width: int = 800,
    height: int = 600,
) -> go.Figure:
    """Create a Plotly figure for the parking layout."""
    
    fig = go.Figure()
    
    # Draw lot boundary
    boundary = layout.boundary if layout.boundary else DEFAULT_BOUNDARY
    boundary_x = [p[0] for p in boundary] + [boundary[0][0]]
    boundary_y = [p[1] for p in boundary] + [boundary[0][1]]
    
    fig.add_trace(go.Scatter(
        x=boundary_x,
        y=boundary_y,
        mode="lines",
        name="Lot Boundary",
        line=dict(color=COLORS["boundary"], width=3),
        fill="toself",
        fillcolor="rgba(44, 62, 80, 0.1)",
    ))
    
    # Get violation space IDs for highlighting
    violation_space_ids = set()
    if compliance_report:
        for v in compliance_report.violations:
            violation_space_ids.update(v.space_ids)
    
    # Draw parking spaces
    for space in layout.spaces:
        color = COLORS.get(space.type, "#888888")
        
        # Determine if this space has violations
        has_violation = space.id in violation_space_ids
        is_highlighted = space.id == highlight_space
        
        # Modify appearance based on state
        if has_violation:
            border_color = COLORS["violation"]
            border_width = 3
            opacity = 0.7
        elif is_highlighted:
            border_color = "#000000"
            border_width = 3
            opacity = 1.0
        else:
            border_color = color
            border_width = 1
            opacity = 0.8
        
        # Create rectangle for the space
        x0, y0 = space.x, space.y
        x1, y1 = space.x + space.length, space.y + space.width
        
        fig.add_shape(
            type="rect",
            x0=x0, y0=y0, x1=x1, y1=y1,
            fillcolor=color,
            opacity=opacity,
            line=dict(color=border_color, width=border_width),
            name=space.label,
        )
        
        # Add label
        if show_labels:
            fig.add_annotation(
                x=(x0 + x1) / 2,
                y=(y0 + y1) / 2,
                text=space.label,
                showarrow=False,
                font=dict(size=10, color="white"),
            )
    
    # Draw lanes
    for lane in layout.lanes:
        path = lane.path
        if len(path) >= 2:
            lane_x = [p[0] for p in path]
            lane_y = [p[1] for p in path]
            
            fig.add_trace(go.Scatter(
                x=lane_x,
                y=lane_y,
                mode="lines",
                name=f"Lane: {lane.id}",
                line=dict(color=COLORS["lane"], width=lane.width, dash="dot"),
            ))
    
    # Configure layout
    fig.update_layout(
        title=dict(text=f"🚛 {layout.name}", font=dict(size=18)),
        xaxis=dict(
            title="Width (m)",
            scaleanchor="y",
            scaleratio=1,
            range=[-5, layout.lot_width + 5],
        ),
        yaxis=dict(
            title="Length (m)",
            range=[-5, layout.lot_length + 5],
        ),
        width=width,
        height=height,
        showlegend=False,
        plot_bgcolor="white",
        hovermode="closest",
    )
    
    # Add grid
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor="rgba(0,0,0,0.1)")
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor="rgba(0,0,0,0.1)")
    
    return fig


def create_legend_figure() -> go.Figure:
    """Create a legend figure showing space types."""
    fig = go.Figure()
    
    y_pos = 0
    for space_type, specs in SPACE_TYPES.items():
        fig.add_shape(
            type="rect",
            x0=0, y0=y_pos, x1=2, y1=y_pos + 0.8,
            fillcolor=specs["color"],
            line=dict(color=specs["color"]),
        )
        fig.add_annotation(
            x=2.5, y=y_pos + 0.4,
            text=specs["name"],
            showarrow=False,
            xanchor="left",
            font=dict(size=12),
        )
        y_pos += 1.2
    
    fig.update_layout(
        width=250,
        height=len(SPACE_TYPES) * 50 + 20,
        showlegend=False,
        xaxis=dict(visible=False, range=[-0.5, 15]),
        yaxis=dict(visible=False, range=[-0.5, y_pos]),
        margin=dict(l=10, r=10, t=10, b=10),
        plot_bgcolor="white",
    )
    
    return fig


def create_revenue_chart(revenue_projection, layout) -> go.Figure:
    """Create a revenue breakdown chart."""
    
    # Bar chart for revenue by type
    breakdown = revenue_projection.breakdown_by_type
    
    types = list(breakdown.keys())
    values = list(breakdown.values())
    colors = [SPACE_TYPES.get(t, {}).get("color", "#888") for t in types]
    labels = [SPACE_TYPES.get(t, {}).get("name", t) for t in types]
    
    fig = go.Figure(data=[
        go.Bar(
            x=labels,
            y=values,
            marker_color=colors,
            text=[f"€{v:,.0f}" for v in values],
            textposition="outside",
        )
    ])
    
    # Add target line
    target_per_type = revenue_projection.target / len(types) if types else 0
    fig.add_hline(
        y=target_per_type,
        line_dash="dash",
        line_color="red",
        annotation_text=f"Target avg: €{target_per_type:,.0f}",
        annotation_position="top right",
    )
    
    fig.update_layout(
        title="Annual Revenue by Space Type",
        xaxis_title="Space Type",
        yaxis_title="Annual Revenue (€)",
        height=400,
        showlegend=False,
    )
    
    return fig


def create_scenario_comparison_chart(comparison_data: list) -> go.Figure:
    """Create a bar chart comparing scenarios."""
    
    names = [d["name"] for d in comparison_data]
    revenues = [d["annual_revenue"] for d in comparison_data]
    targets = [d["target_pct"] for d in comparison_data]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=names,
        y=revenues,
        name="Annual Revenue",
        marker_color=["#27ae60" if t >= 100 else "#e74c3c" for t in targets],
        text=[f"€{r:,.0f}" for r in revenues],
        textposition="outside",
    ))
    
    # Target line
    if comparison_data:
        target = comparison_data[0].get("annual_revenue", 0) / (comparison_data[0].get("target_pct", 100) / 100)
        fig.add_hline(
            y=200000,  # Revenue target
            line_dash="dash",
            line_color="red",
            annotation_text="Target: €200,000",
        )
    
    fig.update_layout(
        title="Scenario Revenue Comparison",
        xaxis_title="Scenario",
        yaxis_title="Annual Revenue (€)",
        height=400,
        showlegend=False,
    )
    
    return fig
