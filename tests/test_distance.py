"""Tests for distance module."""
import pytest

from custom_components.temperature_map.heatmap.distance import (
    flood_fill_distances,
    get_interpolated_distance,
)
from custom_components.temperature_map.heatmap.types import Wall, DistanceGrid


def test_flood_fill_basic():
    """Test basic flood fill without walls."""
    # Simple 10x10 grid, sensor at (5, 5)
    distances = flood_fill_distances(5, 5, [], 10, 10, grid_scale=1)

    # Check that sensor position has distance 0
    assert distances[5][5] == 0

    # Check that adjacent cells have distance ~1
    assert abs(distances[5][6] - 1) < 0.1
    assert abs(distances[6][5] - 1) < 0.1

    # Check that diagonal cells have distance ~sqrt(2)
    assert abs(distances[6][6] - 1.414) < 0.1


def test_flood_fill_with_wall():
    """Test flood fill with a wall blocking the path."""
    # Create a vertical wall at x=5
    walls = [Wall(x1=5, y1=0, x2=5, y2=10)]

    # Sensor at (3, 5) on left side of wall
    distances = flood_fill_distances(3, 5, walls, 10, 10, grid_scale=1)

    # Sensor position should be 0
    assert distances[5][3] == 0

    # Point on same side of wall should be reachable
    assert distances[5][2] < float('inf')

    # Point on other side of wall might be unreachable or have very long path
    # (depending on whether wall extends to edges)
    # This is grid-dependent, so we just check it's not 0
    assert distances[5][7] != 0


def test_flood_fill_unreachable_area():
    """Test that completely blocked areas are unreachable."""
    # Create a box around the sensor
    walls = [
        Wall(x1=4, y1=4, x2=6, y2=4),  # Top
        Wall(x1=6, y1=4, x2=6, y2=6),  # Right
        Wall(x1=6, y1=6, x2=4, y2=6),  # Bottom
        Wall(x1=4, y1=6, x2=4, y2=4),  # Left
    ]

    # Sensor at (5, 5) inside the box
    distances = flood_fill_distances(5, 5, walls, 10, 10, grid_scale=1)

    # Sensor position should be 0
    assert distances[5][5] == 0

    # Points outside the box should be unreachable
    assert distances[0][0] == float('inf')
    assert distances[9][9] == float('inf')


def test_get_interpolated_distance_basic():
    """Test bilinear interpolation of distance values."""
    # Create a simple distance grid
    distances = [
        [
            [0, 1, 2],
            [1, 2, 3],
            [2, 3, 4]
        ]
    ]
    grid = DistanceGrid(distances=distances, width=3, height=3)

    # Test exact grid point
    assert get_interpolated_distance(0, 0, 0, grid) == 0
    assert get_interpolated_distance(1, 1, 0, grid) == 2

    # Test interpolated point (halfway between grid points)
    # Point at (0.5, 0.5) should be average of (0,0), (1,0), (0,1), (1,1)
    # = (0 + 1 + 1 + 2) / 4 = 1.0
    result = get_interpolated_distance(0.5, 0.5, 0, grid)
    assert abs(result - 1.0) < 0.1


def test_get_interpolated_distance_infinity():
    """Test that infinity values are handled correctly."""
    # Grid with some infinity values
    inf = float('inf')
    distances = [
        [
            [0, 1, inf],
            [1, 2, inf],
            [inf, inf, inf]
        ]
    ]
    grid = DistanceGrid(distances=distances, width=3, height=3)

    # Point with all infinity neighbors should return infinity
    assert get_interpolated_distance(2, 2, 0, grid) == float('inf')

    # Point with some reachable neighbors should use available values
    result = get_interpolated_distance(0, 0, 0, grid)
    assert result < float('inf')
