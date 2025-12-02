"""Tests for geometry module."""
import pytest

from custom_components.temperature_map.heatmap.geometry import (
    line_intersection,
    line_intersects_walls,
    check_wall_proximity,
)
from custom_components.temperature_map.heatmap.types import Wall


def test_line_intersection_basic():
    """Test basic line intersection."""
    # Two crossing lines
    result = line_intersection(0, 0, 10, 10, 0, 10, 10, 0)
    assert result is not None
    assert abs(result.x - 5) < 0.001
    assert abs(result.y - 5) < 0.001


def test_line_intersection_parallel():
    """Test parallel lines don't intersect."""
    result = line_intersection(0, 0, 10, 0, 0, 5, 10, 5)
    assert result is None


def test_line_intersection_no_overlap():
    """Test non-overlapping line segments."""
    result = line_intersection(0, 0, 1, 1, 2, 2, 3, 3)
    assert result is None


def test_line_intersects_walls_basic():
    """Test line intersecting a wall."""
    walls = [Wall(x1=5, y1=0, x2=5, y2=10)]
    # Line crosses the wall
    assert line_intersects_walls(0, 5, 10, 5, walls) is True
    # Line doesn't cross the wall
    assert line_intersects_walls(0, 0, 4, 0, walls) is False


def test_line_intersects_walls_multiple():
    """Test line with multiple walls."""
    walls = [
        Wall(x1=5, y1=0, x2=5, y2=10),
        Wall(x1=0, y1=5, x2=10, y2=5),
    ]
    # Line crosses both walls
    assert line_intersects_walls(0, 0, 10, 10, walls) is True
    # Line in corner doesn't cross any wall
    assert line_intersects_walls(0, 0, 3, 3, walls) is False


def test_check_wall_proximity_close():
    """Test point close to wall."""
    walls = [Wall(x1=0, y1=0, x2=10, y2=0)]
    # Point very close to wall
    assert check_wall_proximity(5, 1, walls, 2) is True
    # Point far from wall
    assert check_wall_proximity(5, 5, walls, 2) is False


def test_check_wall_proximity_endpoint():
    """Test point near wall endpoint."""
    walls = [Wall(x1=0, y1=0, x2=10, y2=0)]
    # Point near start endpoint
    assert check_wall_proximity(0, 1, walls, 2) is True
    # Point near end endpoint
    assert check_wall_proximity(10, 1, walls, 2) is True


def test_check_wall_proximity_perpendicular():
    """Test perpendicular distance calculation."""
    walls = [Wall(x1=0, y1=0, x2=10, y2=0)]
    # Point directly above middle of wall at distance 3
    assert check_wall_proximity(5, 3, walls, 4) is True
    assert check_wall_proximity(5, 3, walls, 2) is False
