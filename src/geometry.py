"""Geometry utilities for TruckParking Optimizer.

Uses Shapely for robust polygon operations.
"""

from typing import List, Tuple, Optional, Union
from dataclasses import dataclass
import math

from shapely.geometry import Polygon, Point, LineString, MultiPolygon, box
from shapely.ops import unary_union
from shapely.affinity import rotate, translate
import numpy as np


@dataclass
class Rectangle:
    """A rectangle defined by position, size, and rotation."""
    x: float  # Bottom-left corner x
    y: float  # Bottom-left corner y
    length: float  # Size along x-axis before rotation
    width: float  # Size along y-axis before rotation
    rotation: float = 0.0  # Degrees, counter-clockwise
    
    @property
    def center(self) -> Tuple[float, float]:
        """Get center point of rectangle."""
        cx = self.x + self.length / 2
        cy = self.y + self.width / 2
        return (cx, cy)
    
    def to_polygon(self) -> Polygon:
        """Convert rectangle to Shapely polygon."""
        # Create axis-aligned box at origin
        rect = box(0, 0, self.length, self.width)
        
        # Rotate around center of the original box position
        if self.rotation != 0:
            center_x = self.length / 2
            center_y = self.width / 2
            rect = rotate(rect, self.rotation, origin=(center_x, center_y))
        
        # Translate to final position
        rect = translate(rect, self.x, self.y)
        return rect
    
    def get_corners(self) -> List[Tuple[float, float]]:
        """Get the four corners of the rectangle."""
        poly = self.to_polygon()
        coords = list(poly.exterior.coords)[:-1]  # Remove duplicate last point
        return [(c[0], c[1]) for c in coords]


def coords_to_polygon(coords: List[Tuple[float, float]]) -> Polygon:
    """Convert list of coordinates to Shapely polygon."""
    return Polygon(coords)


def polygon_to_coords(polygon: Polygon) -> List[Tuple[float, float]]:
    """Convert Shapely polygon to list of coordinates."""
    if polygon.is_empty:
        return []
    return [(c[0], c[1]) for c in polygon.exterior.coords]


def point_in_polygon(point: Tuple[float, float], polygon: Polygon) -> bool:
    """Check if a point is inside a polygon."""
    return polygon.contains(Point(point))


def polygon_area(polygon: Polygon) -> float:
    """Calculate polygon area."""
    return polygon.area


def buffer_polygon(polygon: Polygon, distance: float) -> Polygon:
    """
    Buffer (expand/shrink) a polygon.
    
    Args:
        polygon: Input polygon
        distance: Positive = expand, Negative = shrink
        
    Returns:
        Buffered polygon
    """
    buffered = polygon.buffer(distance, join_style=2)  # Mitre join
    if isinstance(buffered, MultiPolygon):
        # Return largest polygon if buffer creates multiple
        return max(buffered.geoms, key=lambda p: p.area)
    return buffered


def polygon_difference(a: Polygon, b: Union[Polygon, List[Polygon]]) -> Union[Polygon, MultiPolygon]:
    """
    Subtract polygon(s) b from polygon a.
    
    Args:
        a: Base polygon
        b: Polygon(s) to subtract
        
    Returns:
        Resulting polygon (may be MultiPolygon)
    """
    if isinstance(b, list):
        b = unary_union(b)
    return a.difference(b)


def polygon_intersection(a: Polygon, b: Polygon) -> Union[Polygon, MultiPolygon]:
    """Get intersection of two polygons."""
    return a.intersection(b)


def rectangle_in_polygon(rect: Rectangle, polygon: Polygon, tolerance: float = 0.01) -> bool:
    """
    Check if a rectangle is fully contained within a polygon.
    
    Args:
        rect: Rectangle to check
        polygon: Containing polygon
        tolerance: Small buffer for numerical stability
        
    Returns:
        True if rectangle is fully inside polygon
    """
    rect_poly = rect.to_polygon()
    # Use slight negative buffer on polygon to ensure full containment
    return polygon.buffer(-tolerance).contains(rect_poly)


def rectangles_overlap(r1: Rectangle, r2: Rectangle, min_gap: float = 0.0) -> bool:
    """
    Check if two rectangles overlap (or are too close).
    
    Args:
        r1: First rectangle
        r2: Second rectangle
        min_gap: Minimum required gap between rectangles
        
    Returns:
        True if rectangles overlap or gap is less than min_gap
    """
    p1 = r1.to_polygon()
    p2 = r2.to_polygon()
    
    if min_gap > 0:
        # Buffer one rectangle by min_gap and check intersection
        p1_buffered = p1.buffer(min_gap / 2)
        p2_buffered = p2.buffer(min_gap / 2)
        return p1_buffered.intersects(p2_buffered)
    else:
        return p1.intersects(p2)


def line_to_lane_polygon(path: List[Tuple[float, float]], width: float) -> Polygon:
    """
    Create a lane polygon by buffering a path.
    
    Args:
        path: List of (x, y) points defining lane centerline
        width: Total lane width
        
    Returns:
        Polygon representing the lane
    """
    if len(path) < 2:
        return Polygon()
    
    line = LineString(path)
    lane = line.buffer(width / 2, cap_style=2)  # Flat end caps
    
    if isinstance(lane, MultiPolygon):
        return max(lane.geoms, key=lambda p: p.area)
    return lane


def point_to_line_distance(point: Tuple[float, float], line: List[Tuple[float, float]]) -> float:
    """
    Calculate shortest distance from point to line.
    
    Args:
        point: (x, y) point
        line: List of (x, y) points defining the line
        
    Returns:
        Distance in same units as coordinates
    """
    p = Point(point)
    l = LineString(line)
    return p.distance(l)


def closest_point_on_line(point: Tuple[float, float], line: List[Tuple[float, float]]) -> Tuple[float, float]:
    """
    Find the closest point on a line to a given point.
    
    Args:
        point: (x, y) point
        line: List of (x, y) points defining the line
        
    Returns:
        (x, y) of closest point on line
    """
    p = Point(point)
    l = LineString(line)
    closest = l.interpolate(l.project(p))
    return (closest.x, closest.y)


def minimum_bounding_rectangle(polygon: Polygon) -> Tuple[Tuple[float, float], float, float, float]:
    """
    Compute minimum area bounding rectangle for a polygon.
    
    Returns:
        (origin, width, height, angle) where:
        - origin: Bottom-left corner of rectangle
        - width: Size along rotated x-axis
        - height: Size along rotated y-axis
        - angle: Rotation angle in degrees
    """
    from shapely.geometry import box as shapely_box
    
    # Get convex hull
    hull = polygon.convex_hull
    if hull.is_empty:
        return ((0, 0), 0, 0, 0)
    
    # Get hull coordinates
    coords = np.array(hull.exterior.coords[:-1])
    
    if len(coords) < 3:
        # Degenerate case
        bounds = polygon.bounds
        return ((bounds[0], bounds[1]), bounds[2] - bounds[0], bounds[3] - bounds[1], 0)
    
    # Try all edge directions
    best_area = float('inf')
    best_result = None
    
    for i in range(len(coords)):
        # Edge vector
        edge = coords[(i + 1) % len(coords)] - coords[i]
        edge_len = np.linalg.norm(edge)
        if edge_len == 0:
            continue
            
        # Normalize
        edge = edge / edge_len
        
        # Perpendicular
        perp = np.array([-edge[1], edge[0]])
        
        # Project all points
        projections_edge = coords @ edge
        projections_perp = coords @ perp
        
        # Bounding box in rotated frame
        min_e, max_e = projections_edge.min(), projections_edge.max()
        min_p, max_p = projections_perp.min(), projections_perp.max()
        
        width = max_e - min_e
        height = max_p - min_p
        area = width * height
        
        if area < best_area:
            best_area = area
            angle = math.degrees(math.atan2(edge[1], edge[0]))
            origin = edge * min_e + perp * min_p
            best_result = ((origin[0], origin[1]), width, height, angle)
    
    return best_result if best_result else ((0, 0), 0, 0, 0)


def polygon_centroid(polygon: Polygon) -> Tuple[float, float]:
    """Get centroid of a polygon."""
    c = polygon.centroid
    return (c.x, c.y)


def simplify_polygon(polygon: Polygon, tolerance: float = 0.5) -> Polygon:
    """
    Simplify a polygon to reduce vertices.
    
    Args:
        polygon: Input polygon
        tolerance: Maximum deviation allowed
        
    Returns:
        Simplified polygon
    """
    return polygon.simplify(tolerance, preserve_topology=True)


def compute_medial_axis_path(polygon: Polygon, start: Tuple[float, float], 
                              end: Tuple[float, float]) -> List[Tuple[float, float]]:
    """
    Compute a path through the polygon following the medial axis (skeleton).
    
    For simple cases, returns direct path. For complex shapes, uses
    the polygon's medial axis to find a path that stays inside.
    
    Args:
        polygon: The containing polygon
        start: Starting point
        end: Ending point
        
    Returns:
        List of points forming the path
    """
    # For MVP: Use simple direct path if it stays inside polygon
    direct_line = LineString([start, end])
    
    if polygon.contains(direct_line):
        return [start, end]
    
    # Otherwise, try to find a path through centroid
    centroid = polygon_centroid(polygon)
    
    # Try going through centroid
    path1 = LineString([start, centroid])
    path2 = LineString([centroid, end])
    
    if polygon.contains(path1) and polygon.contains(path2):
        return [start, centroid, end]
    
    # For complex cases, use polygon shrinking approach
    # Shrink polygon and find path along boundary
    shrunk = buffer_polygon(polygon, -2.0)  # 2m inward
    if shrunk.is_empty or shrunk.area < 10:
        # Too small to shrink, use boundary
        shrunk = polygon
    
    # Find points on shrunk polygon boundary closest to start/end
    boundary = shrunk.exterior
    start_on_boundary = boundary.interpolate(boundary.project(Point(start)))
    end_on_boundary = boundary.interpolate(boundary.project(Point(end)))
    
    # Extract path along boundary
    start_dist = boundary.project(Point(start))
    end_dist = boundary.project(Point(end))
    
    # Simple approach: straight line through interior
    # More sophisticated: follow medial axis
    mid_point = (
        (start_on_boundary.x + end_on_boundary.x) / 2,
        (start_on_boundary.y + end_on_boundary.y) / 2
    )
    
    return [start, mid_point, end]


def get_polygon_edges(polygon: Polygon) -> List[Tuple[Tuple[float, float], Tuple[float, float]]]:
    """
    Get all edges of a polygon.
    
    Returns:
        List of ((x1, y1), (x2, y2)) edge tuples
    """
    coords = list(polygon.exterior.coords)
    edges = []
    for i in range(len(coords) - 1):
        edges.append((
            (coords[i][0], coords[i][1]),
            (coords[i+1][0], coords[i+1][1])
        ))
    return edges


def snap_point_to_boundary(point: Tuple[float, float], polygon: Polygon) -> Tuple[float, float]:
    """
    Snap a point to the nearest location on polygon boundary.
    
    Args:
        point: Point to snap
        polygon: Target polygon
        
    Returns:
        Point on polygon boundary
    """
    p = Point(point)
    boundary = polygon.exterior
    nearest = boundary.interpolate(boundary.project(p))
    return (nearest.x, nearest.y)


def is_point_on_boundary(point: Tuple[float, float], polygon: Polygon, tolerance: float = 1.0) -> bool:
    """
    Check if a point is on or near the polygon boundary.
    
    Args:
        point: Point to check
        polygon: Target polygon
        tolerance: Maximum distance from boundary
        
    Returns:
        True if point is within tolerance of boundary
    """
    p = Point(point)
    return polygon.exterior.distance(p) <= tolerance


def generate_grid_points(polygon: Polygon, spacing: float) -> List[Tuple[float, float]]:
    """
    Generate a grid of points inside a polygon.
    
    Args:
        polygon: Containing polygon
        spacing: Grid spacing
        
    Returns:
        List of (x, y) points inside polygon
    """
    bounds = polygon.bounds  # (minx, miny, maxx, maxy)
    points = []
    
    x = bounds[0]
    while x <= bounds[2]:
        y = bounds[1]
        while y <= bounds[3]:
            if polygon.contains(Point(x, y)):
                points.append((x, y))
            y += spacing
        x += spacing
    
    return points


def polygon_contains_polygon(outer: Polygon, inner: Polygon) -> bool:
    """Check if outer polygon fully contains inner polygon."""
    return outer.contains(inner)


def get_multipolygon_parts(geom: Union[Polygon, MultiPolygon]) -> List[Polygon]:
    """
    Extract individual polygons from a geometry.
    
    Args:
        geom: Polygon or MultiPolygon
        
    Returns:
        List of Polygon objects
    """
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    elif isinstance(geom, Polygon):
        return [geom] if not geom.is_empty else []
    return []
