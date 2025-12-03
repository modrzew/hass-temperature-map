"""Distance and boundary calculations for temperature map."""

from __future__ import annotations

import math
from collections import deque
from typing import Any

from .geometry import line_intersects_walls
from .types import DistanceGrid, TemperatureSensor, Wall


def flood_fill_distances(
    sensor_x: float,
    sensor_y: float,
    walls: list[Wall],
    grid_width: int,
    grid_height: int,
    grid_scale: int = 1,
) -> list[list[float]]:
    """
    Flood fill distance computation using BFS.

    Args:
        sensor_x: Sensor x coordinate
        sensor_y: Sensor y coordinate
        walls: List of walls that block pathfinding
        grid_width: Width of the distance grid
        grid_height: Height of the distance grid
        grid_scale: Scale factor for grid resolution

    Returns:
        2D array of distances from sensor to each grid point
    """
    # Initialize distance grid with infinity
    distances: list[list[float]] = [
        [float("inf") for _ in range(grid_width)] for _ in range(grid_height)
    ]

    visited: set[str] = set()
    queue: deque[dict[str, Any]] = deque()

    # Convert sensor coordinates to grid coordinates
    start_gx = max(0, min(round(sensor_x / grid_scale), grid_width - 1))
    start_gy = max(0, min(round(sensor_y / grid_scale), grid_height - 1))

    # Start flood fill from sensor position
    distances[start_gy][start_gx] = 0
    queue.append({"x": start_gx, "y": start_gy, "distance": 0})
    visited.add(f"{start_gx},{start_gy}")

    # Flood fill with BFS
    while queue:
        current = queue.popleft()

        # Check all 8 directions (including diagonals)
        directions = [
            {"dx": -1, "dy": -1, "cost": math.sqrt(2)},
            {"dx": 0, "dy": -1, "cost": 1},
            {"dx": 1, "dy": -1, "cost": math.sqrt(2)},
            {"dx": -1, "dy": 0, "cost": 1},
            {"dx": 1, "dy": 0, "cost": 1},
            {"dx": -1, "dy": 1, "cost": math.sqrt(2)},
            {"dx": 0, "dy": 1, "cost": 1},
            {"dx": 1, "dy": 1, "cost": math.sqrt(2)},
        ]

        for dir in directions:
            new_gx = current["x"] + dir["dx"]
            new_gy = current["y"] + dir["dy"]
            key = f"{new_gx},{new_gy}"

            # Check bounds - ensure we can reach all edge pixels
            if new_gx < 0 or new_gx >= grid_width or new_gy < 0 or new_gy >= grid_height:
                continue
            if key in visited:
                continue

            # Convert back to actual coordinates for wall checking
            actual_x1 = current["x"] * grid_scale
            actual_y1 = current["y"] * grid_scale
            actual_x2 = new_gx * grid_scale
            actual_y2 = new_gy * grid_scale

            # Check if path is blocked by walls
            if not line_intersects_walls(actual_x1, actual_y1, actual_x2, actual_y2, walls):
                new_distance = current["distance"] + dir["cost"] * grid_scale

                if new_distance < distances[new_gy][new_gx]:
                    distances[new_gy][new_gx] = new_distance
                    queue.append({"x": new_gx, "y": new_gy, "distance": new_distance})
                    visited.add(key)

    # Ensure edge pixels are properly covered by adding additional boundary propagation
    for _pass_num in range(2):
        for y in range(grid_height):
            for x in range(grid_width):
                # If this pixel is still unreachable (Infinity), try to propagate from reachable neighbors
                if distances[y][x] == float("inf"):
                    min_neighbor_distance = float("inf")

                    # Check all 8 neighbors
                    for dy in range(-1, 2):
                        for dx in range(-1, 2):
                            if dx == 0 and dy == 0:
                                continue

                            nx = x + dx
                            ny = y + dy

                            if 0 <= nx < grid_width and 0 <= ny < grid_height:
                                if distances[ny][nx] != float("inf"):
                                    # Check if path from neighbor to current pixel is clear
                                    actual_x1 = nx * grid_scale
                                    actual_y1 = ny * grid_scale
                                    actual_x2 = x * grid_scale
                                    actual_y2 = y * grid_scale

                                    if not line_intersects_walls(
                                        actual_x1, actual_y1, actual_x2, actual_y2, walls
                                    ):
                                        step_cost = math.sqrt(dx * dx + dy * dy) * grid_scale
                                        propagated_distance = distances[ny][nx] + step_cost
                                        min_neighbor_distance = min(
                                            min_neighbor_distance, propagated_distance
                                        )

                    if min_neighbor_distance != float("inf"):
                        distances[y][x] = min_neighbor_distance

    return distances


def compute_distance_grid(
    sensors: list[TemperatureSensor], walls: list[Wall], width: int, height: int
) -> DistanceGrid:
    """
    Compute distance grid for all sensors.

    Args:
        sensors: List of sensor positions and temperatures
        walls: List of walls that block pathfinding
        width: Canvas width
        height: Canvas height

    Returns:
        DistanceGrid containing distances for each sensor
    """
    # Use highest resolution grid for precise wall alignment
    grid_scale = 1  # Maximum resolution for perfect wall detection
    grid_width = math.ceil(width / grid_scale)
    grid_height = math.ceil(height / grid_scale)

    distances: list[list[list[float]]] = []

    for sensor in sensors:
        sensor_distances = flood_fill_distances(
            sensor.x, sensor.y, walls, grid_width, grid_height, grid_scale
        )
        distances.append(sensor_distances)

    return DistanceGrid(distances=distances, width=grid_width, height=grid_height)


def get_interpolated_distance(x: float, y: float, sensor_index: int, grid: DistanceGrid) -> float:
    """
    Get interpolated distance from pre-computed grid using bilinear interpolation.

    Args:
        x: Point x coordinate
        y: Point y coordinate
        sensor_index: Index of the sensor in the distance grid
        grid: Pre-computed distance grid

    Returns:
        Interpolated distance value
    """
    grid_scale = 1  # Updated to match the new grid scale
    gx = x / grid_scale
    gy = y / grid_scale

    # Ensure coordinates are within bounds
    x1 = max(0, min(int(gx), grid.width - 1))
    y1 = max(0, min(int(gy), grid.height - 1))
    x2 = max(0, min(x1 + 1, grid.width - 1))
    y2 = max(0, min(y1 + 1, grid.height - 1))

    # Clamp fractional parts to valid range
    fx = max(0, min(gx - x1, 1))
    fy = max(0, min(gy - y1, 1))

    # Get distance values at the four corners
    d11 = (
        grid.distances[sensor_index][y1][x1]
        if y1 < len(grid.distances[sensor_index]) and x1 < len(grid.distances[sensor_index][y1])
        else float("inf")
    )
    d21 = (
        grid.distances[sensor_index][y1][x2]
        if y1 < len(grid.distances[sensor_index]) and x2 < len(grid.distances[sensor_index][y1])
        else float("inf")
    )
    d12 = (
        grid.distances[sensor_index][y2][x1]
        if y2 < len(grid.distances[sensor_index]) and x1 < len(grid.distances[sensor_index][y2])
        else float("inf")
    )
    d22 = (
        grid.distances[sensor_index][y2][x2]
        if y2 < len(grid.distances[sensor_index]) and x2 < len(grid.distances[sensor_index][y2])
        else float("inf")
    )

    # Handle infinity values (unreachable areas)
    if d11 == float("inf"):
        return float("inf")
    if d21 == float("inf"):
        return d11
    if d12 == float("inf"):
        return d11
    if d22 == float("inf"):
        return d21

    # Bilinear interpolation
    d1 = d11 * (1 - fx) + d21 * fx
    d2 = d12 * (1 - fx) + d22 * fx

    return d1 * (1 - fy) + d2 * fy


def is_point_inside_boundary(
    x: float,
    y: float,
    walls: list[Wall],
    canvas_width: int,
    canvas_height: int,
    sensors: list[TemperatureSensor] | None = None,
) -> bool:
    """
    Check if a point is inside the boundary defined by walls and sensor positions.

    Args:
        x: Point x coordinate
        y: Point y coordinate
        walls: List of walls defining boundaries
        canvas_width: Canvas width
        canvas_height: Canvas height
        sensors: List of sensor positions for boundary guidance

    Returns:
        True if point is inside boundary
    """
    if not walls:
        return True

    if sensors is None:
        sensors = []

    boundary_points = _compute_boundary_points(walls, canvas_width, canvas_height, sensors)
    return f"{int(x)},{int(y)}" in boundary_points


def _compute_boundary_points(
    walls: list[Wall], canvas_width: int, canvas_height: int, sensors: list[TemperatureSensor]
) -> set[str]:
    """
    Compute boundary points using flood fill from sensor positions.

    Args:
        walls: List of walls defining boundaries
        canvas_width: Canvas width
        canvas_height: Canvas height
        sensors: List of sensor positions for boundary guidance

    Returns:
        Set of boundary point coordinates as strings
    """
    boundary_points: set[str] = set()

    if not sensors:
        # No sensors to guide us - fall back to bounding box
        all_points = []
        for wall in walls:
            all_points.extend([{"x": wall.x1, "y": wall.y1}, {"x": wall.x2, "y": wall.y2}])

        if not all_points:
            # No walls either - include everything
            for y in range(canvas_height):
                for x in range(canvas_width):
                    boundary_points.add(f"{x},{y}")
            return boundary_points

        min_x = min(p["x"] for p in all_points)
        max_x = max(p["x"] for p in all_points)
        min_y = min(p["y"] for p in all_points)
        max_y = max(p["y"] for p in all_points)

        for y in range(canvas_height):
            for x in range(canvas_width):
                if min_x <= x <= max_x and min_y <= y <= max_y:
                    boundary_points.add(f"{x},{y}")
        return boundary_points

    # Use flood fill from sensor locations to determine interior areas
    grid_scale = 1  # Use 1:1 pixel accuracy for precise boundary detection
    grid_width = math.ceil(canvas_width / grid_scale)
    grid_height = math.ceil(canvas_height / grid_scale)

    visited: set[str] = set()
    queue: deque[dict[str, int]] = deque()

    # Start flood fill from all sensor locations (they're definitely inside)
    for sensor in sensors:
        grid_x = int(sensor.x / grid_scale)
        grid_y = int(sensor.y / grid_scale)
        if 0 <= grid_x < grid_width and 0 <= grid_y < grid_height:
            queue.append({"x": grid_x, "y": grid_y})

    # Flood fill to mark all reachable interior points
    while queue:
        current = queue.popleft()
        key = f"{current['x']},{current['y']}"

        if key in visited:
            continue
        if (
            current["x"] < 0
            or current["x"] >= grid_width
            or current["y"] < 0
            or current["y"] >= grid_height
        ):
            continue

        visited.add(key)

        # Convert grid coordinates to actual coordinates
        actual_x = current["x"] * grid_scale + grid_scale / 2
        actual_y = current["y"] * grid_scale + grid_scale / 2

        # Check all 4 directions
        directions = [
            {"dx": -1, "dy": 0},
            {"dx": 1, "dy": 0},
            {"dx": 0, "dy": -1},
            {"dx": 0, "dy": 1},
        ]

        for dir in directions:
            new_x = current["x"] + dir["dx"]
            new_y = current["y"] + dir["dy"]
            new_key = f"{new_x},{new_y}"

            if new_key in visited:
                continue
            if new_x < 0 or new_x >= grid_width or new_y < 0 or new_y >= grid_height:
                continue

            new_actual_x = new_x * grid_scale + grid_scale / 2
            new_actual_y = new_y * grid_scale + grid_scale / 2

            # Check if movement is blocked by a wall
            if not line_intersects_walls(actual_x, actual_y, new_actual_x, new_actual_y, walls):
                queue.append({"x": new_x, "y": new_y})

    # Mark all points in visited grid cells as interior
    for y in range(canvas_height):
        for x in range(canvas_width):
            grid_x = int(x / grid_scale)
            grid_y = int(y / grid_scale)
            grid_key = f"{grid_x},{grid_y}"

            if grid_key in visited:
                boundary_points.add(f"{x},{y}")

    return boundary_points
