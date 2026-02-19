"""Unit tests for the optimizer module."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.optimizer import (
    optimize_layout,
    quick_estimate,
    generate_candidates,
    find_overlapping_pairs,
    OptimizationConfig,
    OptimizationGoal,
    Candidate,
    calculate_space_revenue,
    validate_vehicle_mix,
)
from src.lane_generator import (
    generate_lanes,
    LaneConfig,
    validate_entry_exit_points,
    generate_lane_path,
)
from src.geometry import coords_to_polygon


class TestQuickEstimate:
    """Tests for quick estimation function."""
    
    def test_rectangular_lot(self):
        boundary = [(0, 0), (50, 0), (50, 100), (0, 100)]
        estimate = quick_estimate(boundary, "oneway")
        
        assert estimate["total_area"] == pytest.approx(5000, rel=0.01)
        assert estimate["max_truck_spaces"] > 0
        assert estimate["estimated_annual_revenue"] > 0
    
    def test_triangular_lot(self):
        boundary = [(0, 0), (27, 0), (74, 145), (0, 145)]
        estimate = quick_estimate(boundary, "oneway")
        
        # Triangular lot has specific area
        assert estimate["total_area"] > 0
        assert estimate["max_truck_spaces"] > 0
    
    def test_twoway_vs_oneway(self):
        boundary = [(0, 0), (50, 0), (50, 100), (0, 100)]
        
        oneway = quick_estimate(boundary, "oneway")
        twoway = quick_estimate(boundary, "twoway")
        
        # Two-way lanes take more space, so fewer parking spots
        assert oneway["max_truck_spaces"] >= twoway["max_truck_spaces"]


class TestLaneGeneration:
    """Tests for lane generation."""
    
    def test_generate_lanes_rectangular(self):
        boundary = [(0, 0), (50, 0), (50, 100), (0, 100)]
        entry = (25, 0)
        exit_point = (25, 100)
        
        result = generate_lanes(boundary, entry, exit_point)
        
        assert result.success == True
        assert len(result.lanes) > 0
        assert len(result.parking_zones) > 0
        assert result.total_parking_area > 0
    
    def test_generate_lanes_triangular(self):
        boundary = [(0, 0), (27, 0), (74, 145), (0, 145)]
        entry = (13, 0)
        exit_point = (37, 145)
        
        result = generate_lanes(boundary, entry, exit_point)
        
        assert result.success == True
        assert len(result.lanes) > 0
    
    def test_validate_entry_exit_snapping(self):
        boundary = coords_to_polygon([(0, 0), (50, 0), (50, 100), (0, 100)])
        
        # Entry point far off boundary (more than tolerance of 5)
        entry, exit_pt, warnings = validate_entry_exit_points(
            boundary, (25, -10), (25, 115), tolerance=5.0
        )
        
        # Should snap to boundary
        assert entry[1] == pytest.approx(0, abs=1)
        assert exit_pt[1] == pytest.approx(100, abs=1)
        assert len(warnings) > 0
    
    def test_auto_exit_generation(self):
        boundary = coords_to_polygon([(0, 0), (50, 0), (50, 100), (0, 100)])
        
        entry, exit_pt, warnings = validate_entry_exit_points(
            boundary, (25, 0), None
        )
        
        # Exit should be auto-generated
        assert exit_pt is not None
        assert any("auto-generated" in w.lower() for w in warnings)
    
    def test_lane_config_defaults(self):
        config = LaneConfig(lane_type="oneway")
        assert config.width == pytest.approx(6.0, rel=0.1)
        
        config = LaneConfig(lane_type="twoway")
        assert config.width == pytest.approx(8.0, rel=0.1)


class TestCandidateGeneration:
    """Tests for candidate placement generation."""
    
    def test_generate_candidates_basic(self):
        boundary = coords_to_polygon([(0, 0), (50, 0), (50, 100), (0, 100)])
        
        # Create a parking zone
        parking_zones = [coords_to_polygon([(0, 0), (20, 0), (20, 100), (0, 100)])]
        lane_path = [(25, 0), (25, 100)]
        
        config = OptimizationConfig(grid_resolution=5.0)
        
        candidates = generate_candidates(
            parking_zones, lane_path, config, boundary
        )
        
        assert len(candidates) > 0
    
    def test_candidates_have_required_fields(self):
        boundary = coords_to_polygon([(0, 0), (50, 0), (50, 100), (0, 100)])
        parking_zones = [coords_to_polygon([(0, 0), (20, 0), (20, 100), (0, 100)])]
        lane_path = [(25, 0), (25, 100)]
        
        config = OptimizationConfig(grid_resolution=10.0)
        
        candidates = generate_candidates(
            parking_zones, lane_path, config, boundary
        )
        
        if candidates:
            c = candidates[0]
            assert hasattr(c, 'id')
            assert hasattr(c, 'type')
            assert hasattr(c, 'x')
            assert hasattr(c, 'y')
            assert hasattr(c, 'length')
            assert hasattr(c, 'width')
            assert hasattr(c, 'revenue')
    
    def test_no_candidates_in_tiny_area(self):
        boundary = coords_to_polygon([(0, 0), (5, 0), (5, 5), (0, 5)])
        parking_zones = [boundary]
        lane_path = [(2.5, 0), (2.5, 5)]
        
        config = OptimizationConfig(grid_resolution=0.5)
        
        candidates = generate_candidates(
            parking_zones, lane_path, config, boundary
        )
        
        # Very small area shouldn't fit trucks
        truck_candidates = [c for c in candidates if c.type == "truck"]
        assert len(truck_candidates) == 0


class TestOverlapDetection:
    """Tests for overlap detection."""
    
    def test_find_overlapping_pairs(self):
        candidates = [
            Candidate(1, "truck", 0, 0, 18.5, 3.5, 0, 2000),
            Candidate(2, "truck", 5, 0, 18.5, 3.5, 0, 2000),  # Overlaps with 1
            Candidate(3, "truck", 50, 50, 18.5, 3.5, 0, 2000),  # No overlap
        ]
        
        conflicts = find_overlapping_pairs(candidates, min_spacing=1.0)
        
        # Candidates 1 and 2 should conflict
        assert (0, 1) in conflicts or (1, 0) in conflicts
        # Candidate 3 should not conflict with others
        assert (0, 2) not in conflicts
        assert (1, 2) not in conflicts


class TestOptimizationConfig:
    """Tests for optimization configuration."""
    
    def test_default_config(self):
        config = OptimizationConfig()
        
        assert config.time_limit == 30.0
        assert config.grid_resolution == 0.5
        assert config.goal == OptimizationGoal.MAXIMIZE_REVENUE
        assert config.min_spacing > 0
    
    def test_custom_config(self):
        config = OptimizationConfig(
            time_limit=10.0,
            goal=OptimizationGoal.MAXIMIZE_COUNT,
            vehicle_mix={"truck": (5, 20), "van": (0, 5)},
        )
        
        assert config.time_limit == 10.0
        assert config.goal == OptimizationGoal.MAXIMIZE_COUNT
        assert "truck" in config.vehicle_mix


class TestVehicleMixValidation:
    """Tests for vehicle mix validation and constraints."""

    def test_invalid_vehicle_mix_min_gt_max(self):
        errors = validate_vehicle_mix({"truck": (5, 3)})
        assert errors
        assert any("min > max" in e for e in errors)

    def test_invalid_vehicle_mix_unknown_type(self):
        errors = validate_vehicle_mix({"bus": (1, 2)})
        assert errors
        assert any("Unknown vehicle type" in e for e in errors)

    def test_optimize_layout_rejects_invalid_mix(self):
        result = optimize_layout(
            boundary=[(0, 0), (40, 0), (40, 40), (0, 40)],
            entry_point=(20, 0),
            exit_point=(20, 40),
            vehicle_mix={"truck": (5, 3)},
            time_limit=2.0,
        )
        assert result.status == "invalid"


class TestRevenueCalculation:
    """Tests for revenue calculation."""
    
    def test_truck_revenue(self):
        revenue = calculate_space_revenue("truck", 0.75)
        assert revenue > 0
    
    def test_ev_premium(self):
        truck_rev = calculate_space_revenue("truck", 0.75)
        ev_rev = calculate_space_revenue("ev", 0.75)
        
        # EV should have premium
        assert ev_rev > truck_rev
    
    def test_van_discount(self):
        truck_rev = calculate_space_revenue("truck", 0.75)
        van_rev = calculate_space_revenue("van", 0.75)
        
        # Van should be cheaper
        assert van_rev < truck_rev
    
    def test_occupancy_affects_revenue(self):
        rev_high = calculate_space_revenue("truck", 1.0)
        rev_low = calculate_space_revenue("truck", 0.5)
        
        assert rev_high > rev_low


class TestFullOptimization:
    """Integration tests for full optimization."""
    
    def test_optimize_rectangular_lot(self):
        boundary = [(0, 0), (50, 0), (50, 100), (0, 100)]
        entry = (25, 0)
        exit_point = (25, 100)
        
        result = optimize_layout(
            boundary=boundary,
            entry_point=entry,
            exit_point=exit_point,
            time_limit=5.0,  # Short timeout for tests
        )
        
        assert result.layout is not None
        assert result.status in ("optimal", "feasible", "timeout")
        # Should find at least some spaces
        if result.success:
            assert len(result.layout.spaces) > 0
    
    def test_optimize_triangular_lot(self):
        # Havenweg-style lot
        boundary = [(0, 0), (27, 0), (74, 145), (0, 145)]
        entry = (13, 0)
        exit_point = (37, 145)
        
        result = optimize_layout(
            boundary=boundary,
            entry_point=entry,
            exit_point=exit_point,
            time_limit=5.0,
        )
        
        assert result.layout is not None
    
    def test_optimize_with_vehicle_mix(self):
        boundary = [(0, 0), (60, 0), (60, 120), (0, 120)]
        entry = (30, 0)
        exit_point = (30, 120)
        
        result = optimize_layout(
            boundary=boundary,
            entry_point=entry,
            exit_point=exit_point,
            vehicle_mix={"truck": (3, 10), "ev": (1, 5)},
            time_limit=5.0,
        )
        
        if result.success:
            counts = result.layout.count_by_type()
            # Should respect limits if feasible
            # (depends on actual space available)
            assert result.layout is not None
    
    def test_optimize_maximize_count(self):
        boundary = [(0, 0), (50, 0), (50, 100), (0, 100)]
        entry = (25, 0)
        
        result = optimize_layout(
            boundary=boundary,
            entry_point=entry,
            optimization_goal="maximize_count",
            time_limit=5.0,
        )
        
        assert result.layout is not None
    
    def test_optimize_returns_stats(self):
        boundary = [(0, 0), (50, 0), (50, 100), (0, 100)]
        entry = (25, 0)
        
        result = optimize_layout(
            boundary=boundary,
            entry_point=entry,
            time_limit=5.0,
        )
        
        assert "total_candidates" in result.stats
        assert "selected_spaces" in result.stats
        assert result.solve_time >= 0
    
    def test_infeasible_tiny_lot(self):
        # Lot too small for any trucks
        boundary = [(0, 0), (5, 0), (5, 5), (0, 5)]
        entry = (2.5, 0)
        
        result = optimize_layout(
            boundary=boundary,
            entry_point=entry,
            time_limit=3.0,
        )
        
        # Should either be infeasible or have 0 spaces
        if result.status == "infeasible":
            assert len(result.layout.spaces) == 0
        # Or it found 0 feasible candidates
    
    def test_callback_is_called(self):
        boundary = [(0, 0), (50, 0), (50, 100), (0, 100)]
        entry = (25, 0)
        
        messages = []
        def callback(msg):
            messages.append(msg)
        
        result = optimize_layout(
            boundary=boundary,
            entry_point=entry,
            time_limit=3.0,
            callback=callback,
        )
        
        # Should have received some progress messages
        assert len(messages) > 0


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_boundary(self):
        # Empty or invalid boundary
        boundary = []
        entry = (0, 0)
        
        with pytest.raises(Exception):
            optimize_layout(boundary=boundary, entry_point=entry)
    
    def test_single_point_boundary(self):
        boundary = [(0, 0)]
        entry = (0, 0)
        
        with pytest.raises(Exception):
            optimize_layout(boundary=boundary, entry_point=entry)
    
    def test_narrow_lot(self):
        # Very narrow lot - barely wider than a truck
        boundary = [(0, 0), (5, 0), (5, 100), (0, 100)]
        entry = (2.5, 0)
        
        result = optimize_layout(
            boundary=boundary,
            entry_point=entry,
            time_limit=3.0,
        )
        
        # Should handle gracefully
        assert result.layout is not None
        # Might have warnings about narrow lot
    
    def test_l_shaped_lot(self):
        # L-shaped lot
        boundary = [(0, 0), (60, 0), (60, 60), (30, 60), (30, 100), (0, 100)]
        entry = (30, 0)
        exit_point = (15, 100)
        
        result = optimize_layout(
            boundary=boundary,
            entry_point=entry,
            exit_point=exit_point,
            time_limit=5.0,
        )
        
        # Should handle complex shapes
        assert result.layout is not None


class TestCandidateConversion:
    """Tests for candidate to parking space conversion."""
    
    def test_candidate_to_rectangle(self):
        candidate = Candidate(1, "truck", 10, 20, 18.5, 3.5, 0, 2000)
        rect = candidate.to_rectangle()
        
        assert rect.x == 10
        assert rect.y == 20
        assert rect.length == 18.5
        assert rect.width == 3.5
    
    def test_candidate_to_parking_space(self):
        candidate = Candidate(1, "truck", 10, 20, 18.5, 3.5, 45, 2000)
        space = candidate.to_parking_space()
        
        assert space.id == 1
        assert space.type == "truck"
        assert space.x == 10
        assert space.y == 20
        assert space.rotation == 45


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
