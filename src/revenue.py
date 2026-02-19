"""Revenue calculator for TruckParking Optimizer."""

from dataclasses import dataclass
from typing import Dict
from .models import Layout
from .config import PRICING, SITE


@dataclass
class RevenueProjection:
    """Revenue projection results."""
    daily: float
    weekly: float
    monthly: float
    annual: float
    target: float
    target_percentage: float
    breakdown_by_type: Dict[str, float]
    
    @property
    def meets_target(self) -> bool:
        return self.annual >= self.target
    
    @property
    def status(self) -> str:
        if self.target_percentage >= 100:
            return f"Exceeds target by {self.target_percentage - 100:.1f}%"
        elif self.target_percentage >= 90:
            return f"{100 - self.target_percentage:.1f}% below target"
        else:
            return f"{100 - self.target_percentage:.1f}% below target"


def calculate_revenue(layout: Layout, occupancy_rate: float = 0.75) -> RevenueProjection:
    """Calculate revenue projections for a layout."""
    
    # Space counts
    counts = layout.count_by_type()
    total_spaces = sum(counts.values())
    
    # Base pricing (annual per space)
    annual_per_space = PRICING.get("annual", 2433.60)
    
    # Calculate by type (all treated the same for MVP, can differentiate later)
    type_multipliers = {
        "truck": 1.0,      # Standard rate
        "tractor": 0.7,    # Smaller, lower rate
        "trailer": 0.6,    # Storage only, lower rate
        "ev": 1.3,         # Premium for charging
        "van": 0.5,        # Smaller vehicles
    }
    
    annual_by_type = {}
    total_annual = 0
    
    for space_type, count in counts.items():
        multiplier = type_multipliers.get(space_type, 1.0)
        type_annual = count * annual_per_space * multiplier * occupancy_rate
        annual_by_type[space_type] = type_annual
        total_annual += type_annual
    
    # Time period calculations
    daily = total_annual / 365
    weekly = total_annual / 52
    monthly = total_annual / 12
    
    # Target comparison
    target = SITE.get("revenue_target", 200000)
    target_percentage = (total_annual / target * 100) if target > 0 else 0
    
    return RevenueProjection(
        daily=round(daily, 2),
        weekly=round(weekly, 2),
        monthly=round(monthly, 2),
        annual=round(total_annual, 2),
        target=target,
        target_percentage=round(target_percentage, 1),
        breakdown_by_type=annual_by_type,
    )


def calculate_breakeven_occupancy(layout: Layout, target: float = None) -> float:
    """Calculate the occupancy rate needed to hit revenue target."""
    if target is None:
        target = SITE.get("revenue_target", 200000)
    
    # Calculate max potential revenue at 100% occupancy
    max_projection = calculate_revenue(layout, occupancy_rate=1.0)
    
    if max_projection.annual <= 0:
        return 0.0
    
    breakeven = target / max_projection.annual
    return min(breakeven, 1.0)


def compare_scenarios(scenarios: list) -> Dict:
    """Compare multiple scenarios."""
    results = []
    
    for scenario in scenarios:
        projection = calculate_revenue(scenario.layout, scenario.occupancy_rate)
        results.append({
            "name": scenario.name,
            "spaces": len(scenario.layout.spaces),
            "occupancy": scenario.occupancy_rate * 100,
            "annual_revenue": projection.annual,
            "target_pct": projection.target_percentage,
            "meets_target": projection.meets_target,
        })
    
    return results
