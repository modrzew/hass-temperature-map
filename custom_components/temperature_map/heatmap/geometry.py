"""Geometric calculations for temperature map."""

from __future__ import annotations

import math

from .types import Point, Wall


def line_intersection(
    x1: float, y1: float, x2: float, y2: float, x3: float, y3: float, x4: float, y4: float
) -> Point | None:
    """
    Calculate intersection point between two line segments.

    Args:
        x1, y1: Start point of first line
        x2, y2: End point of first line
        x3, y3: Start point of second line
        x4, y4: End point of second line

    Returns:
        Intersection point or None if no intersection
    """
    denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
    if abs(denom) < 1e-10:
        return None

    t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
    u = -((x1 - x2) * (y1 - y3) - (y1 - y2) * (x1 - x3)) / denom

    if 0 <= t <= 1 and 0 <= u <= 1:
        return Point(x=x1 + t * (x2 - x1), y=y1 + t * (y2 - y1))
    return None


def line_intersects_walls(x1: float, y1: float, x2: float, y2: float, walls: list[Wall]) -> bool:
    """
    Check if a line intersects any wall.

    Args:
        x1, y1: Start point of line
        x2, y2: End point of line
        walls: List of walls to check against

    Returns:
        True if line intersects any wall
    """
    for wall in walls:
        intersection = line_intersection(x1, y1, x2, y2, wall.x1, wall.y1, wall.x2, wall.y2)
        if intersection:
            # Check if intersection is within both line segments (including endpoints)
            t1 = (intersection.x - x1) / (x2 - x1) if abs(x2 - x1) > 0.001 else 0
            t2 = (intersection.y - y1) / (y2 - y1) if abs(y2 - y1) > 0.001 else 0
            t_wall1 = (
                (intersection.x - wall.x1) / (wall.x2 - wall.x1)
                if abs(wall.x2 - wall.x1) > 0.001
                else 0
            )
            t_wall2 = (
                (intersection.y - wall.y1) / (wall.y2 - wall.y1)
                if abs(wall.y2 - wall.y1) > 0.001
                else 0
            )

            # Use consistent parameter for both x and y calculations
            t = t1 if abs(x2 - x1) > abs(y2 - y1) else t2
            t_wall = t_wall1 if abs(wall.x2 - wall.x1) > abs(wall.y2 - wall.y1) else t_wall2

            # Include endpoints in intersection detection (0 <= t <= 1)
            if 0 <= t <= 1 and 0 <= t_wall <= 1:
                return True
    return False


def check_wall_proximity(x: float, y: float, walls: list[Wall], radius: float) -> bool:
    """
    Check if a point is within a given radius of any wall.

    Args:
        x, y: Point coordinates
        walls: List of walls to check
        radius: Distance threshold

    Returns:
        True if point is within radius of any wall
    """
    for wall in walls:
        # Calculate distance from point to line segment
        A = x - wall.x1
        B = y - wall.y1
        C = wall.x2 - wall.x1
        D = wall.y2 - wall.y1

        dot = A * C + B * D
        len_sq = C * C + D * D

        if len_sq == 0:
            # Wall is a point
            distance = math.sqrt(A * A + B * B)
            if distance <= radius:
                return True
            continue

        param = dot / len_sq
        param = max(0, min(1, param))  # Clamp to line segment

        xx = wall.x1 + param * C
        yy = wall.y1 + param * D

        dx = x - xx
        dy = y - yy
        distance = math.sqrt(dx * dx + dy * dy)

        if distance <= radius:
            return True

    return False
