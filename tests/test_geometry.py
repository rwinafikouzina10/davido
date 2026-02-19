"""Unit tests for geometry module."""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.geometry import (
    Rectangle,
    coords_to_polygon,
    polygon_to_coords,
    point_in_polygon,
    polygon_area,
    buffer_polygon,
    polygon_difference,
    rectangle_in_polygon,
    rectangles_overlap,
    line_to_lane_polygon,
    point_to_line_distance,
    closest_point_on_line,
    snap_point_to_boundary,
    generate_grid_points,
)


class TestRectangle:
    """Tests for Rectangle class."""
    
    def test_create_rectangle(self):
        rect = Rectangle(x=0, y=0, length=10, width=5, rotation=0)
        assert rect.x == 0
        assert rect.y == 0
        assert rect.length == 10
        assert rect.width == 5
    
    def test_rectangle_center(self):
        rect = Rectangle(x=0, y=0, length=10, width=4, rotation=0)
        center = rect.center
        assert center == (5.0, 2.0)
    
    def test_rectangle_to_polygon(self):
        rect = Rectangle(x=0, y=0, length=10, width=5, rotation=0)
        poly = rect.to_polygon()
        assert poly.area == pytest.approx(50, rel=0.01)
    
    def test_rectangle_corners_no_rotation(self):
        rect = Rectangle(x=0, y=0, length=10, width=5, rotation=0)
        corners = rect.get_corners()
        assert len(corners) == 4
    
    def test_rectangle_with_rotation(self):
        rect = Rectangle(x=0, y=0, length=10, width=5, rotation=90)
        poly = rect.to_polygon()
        # Area should be preserved
        assert poly.area == pytest.approx(50, rel=0.01)


class TestPolygonOperations:
    """Tests for polygon operations."""
    
    def test_coords_to_polygon(self):
        coords = [(0, 0), (10, 0), (10, 10), (0, 10)]
        poly = coords_to_polygon(coords)
        assert poly.area == pytest.approx(100, rel=0.01)
    
    def test_polygon_to_coords(self):
        coords = [(0, 0), (10, 0), (10, 10), (0, 10)]
        poly = coords_to_polygon(coords)
        result = polygon_to_coords(poly)
        assert len(result) >= 4
    
    def test_point_in_polygon(self):
        poly = coords_to_polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        assert point_in_polygon((5, 5), poly) == True
        assert point_in_polygon((15, 15), poly) == False
    
    def test_polygon_area(self):
        poly = coords_to_polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        assert polygon_area(poly) == pytest.approx(100, rel=0.01)
    
    def test_polygon_area_triangle(self):
        poly = coords_to_polygon([(0, 0), (10, 0), (5, 10)])
        assert polygon_area(poly) == pytest.approx(50, rel=0.01)
    
    def test_buffer_polygon_expand(self):
        poly = coords_to_polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        original_area = polygon_area(poly)
        buffered = buffer_polygon(poly, 1.0)
        assert polygon_area(buffered) > original_area
    
    def test_buffer_polygon_shrink(self):
        poly = coords_to_polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        original_area = polygon_area(poly)
        buffered = buffer_polygon(poly, -1.0)
        assert polygon_area(buffered) < original_area
    
    def test_polygon_difference(self):
        outer = coords_to_polygon([(0, 0), (20, 0), (20, 20), (0, 20)])
        inner = coords_to_polygon([(5, 5), (15, 5), (15, 15), (5, 15)])
        diff = polygon_difference(outer, inner)
        expected_area = 400 - 100  # 300
        assert polygon_area(diff) == pytest.approx(expected_area, rel=0.01)


class TestRectangleOperations:
    """Tests for rectangle-specific operations."""
    
    def test_rectangle_in_polygon_contained(self):
        boundary = coords_to_polygon([(0, 0), (50, 0), (50, 50), (0, 50)])
        rect = Rectangle(x=10, y=10, length=10, width=5, rotation=0)
        assert rectangle_in_polygon(rect, boundary) == True
    
    def test_rectangle_in_polygon_outside(self):
        boundary = coords_to_polygon([(0, 0), (50, 0), (50, 50), (0, 50)])
        rect = Rectangle(x=60, y=60, length=10, width=5, rotation=0)
        assert rectangle_in_polygon(rect, boundary) == False
    
    def test_rectangle_in_polygon_partial(self):
        boundary = coords_to_polygon([(0, 0), (50, 0), (50, 50), (0, 50)])
        rect = Rectangle(x=45, y=45, length=10, width=10, rotation=0)
        # Rectangle extends beyond boundary
        assert rectangle_in_polygon(rect, boundary) == False
    
    def test_rectangles_overlap_yes(self):
        r1 = Rectangle(x=0, y=0, length=10, width=5, rotation=0)
        r2 = Rectangle(x=5, y=2, length=10, width=5, rotation=0)
        assert rectangles_overlap(r1, r2) == True
    
    def test_rectangles_overlap_no(self):
        r1 = Rectangle(x=0, y=0, length=10, width=5, rotation=0)
        r2 = Rectangle(x=20, y=20, length=10, width=5, rotation=0)
        assert rectangles_overlap(r1, r2) == False
    
    def test_rectangles_overlap_with_gap(self):
        r1 = Rectangle(x=0, y=0, length=10, width=5, rotation=0)
        r2 = Rectangle(x=10, y=0, length=10, width=5, rotation=0)
        # Touching but no overlap
        assert rectangles_overlap(r1, r2, min_gap=0) == True  # Touching counts as overlap
        # But should trigger with min_gap
        assert rectangles_overlap(r1, r2, min_gap=1.0) == True


class TestLaneOperations:
    """Tests for lane-related geometry."""
    
    def test_line_to_lane_polygon(self):
        path = [(0, 0), (100, 0)]
        lane = line_to_lane_polygon(path, width=6)
        # Lane should have width and length
        assert lane.area > 0
        assert lane.area == pytest.approx(600, rel=0.1)  # 100m x 6m
    
    def test_point_to_line_distance(self):
        line = [(0, 0), (100, 0)]
        # Point directly above middle of line
        dist = point_to_line_distance((50, 10), line)
        assert dist == pytest.approx(10, rel=0.01)
    
    def test_closest_point_on_line(self):
        line = [(0, 0), (100, 0)]
        closest = closest_point_on_line((50, 10), line)
        assert closest[0] == pytest.approx(50, rel=0.1)
        assert closest[1] == pytest.approx(0, rel=0.1)


class TestBoundaryOperations:
    """Tests for boundary-related operations."""
    
    def test_snap_point_to_boundary(self):
        poly = coords_to_polygon([(0, 0), (100, 0), (100, 100), (0, 100)])
        # Point outside, should snap to nearest edge
        snapped = snap_point_to_boundary((50, -10), poly)
        assert snapped[0] == pytest.approx(50, rel=0.1)
        assert snapped[1] == pytest.approx(0, rel=0.1)
    
    def test_generate_grid_points(self):
        poly = coords_to_polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
        points = generate_grid_points(poly, spacing=2.0)
        assert len(points) > 0
        # All points should be inside
        for p in points:
            assert point_in_polygon(p, poly) == True


class TestComplexShapes:
    """Tests for complex polygon shapes."""
    
    def test_triangular_boundary(self):
        # Havenweg-style triangular lot
        coords = [(0, 0), (27, 0), (74, 145), (0, 145)]
        poly = coords_to_polygon(coords)
        area = polygon_area(poly)
        # Should be a valid polygon with reasonable area
        assert area > 0
        assert area == pytest.approx(7322.5, rel=0.1)
    
    def test_l_shaped_boundary(self):
        # L-shaped lot
        # Shape: (0,0) -> (60,0) -> (60,60) -> (30,60) -> (30,100) -> (0,100)
        # This is a rectangle 60x60 with a 30x40 extension on top-left
        # Area = 60*60 + 30*40 = 3600 + 1200 = 4800
        coords = [(0, 0), (60, 0), (60, 60), (30, 60), (30, 100), (0, 100)]
        poly = coords_to_polygon(coords)
        area = polygon_area(poly)
        expected = 60*60 + 30*40  # 4800
        assert area == pytest.approx(expected, rel=0.01)
    
    def test_rectangle_fits_in_triangle(self):
        triangle = coords_to_polygon([(0, 0), (27, 0), (74, 145), (0, 145)])
        # Small rectangle that should fit
        rect = Rectangle(x=5, y=50, length=10, width=3, rotation=0)
        assert rectangle_in_polygon(rect, triangle) == True
        
    def test_rectangle_too_wide_for_narrow_part(self):
        triangle = coords_to_polygon([(0, 0), (27, 0), (74, 145), (0, 145)])
        # Rectangle at the narrow end that shouldn't fit
        rect = Rectangle(x=5, y=5, length=25, width=3, rotation=0)
        # This extends past the boundary
        assert rectangle_in_polygon(rect, triangle) == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
