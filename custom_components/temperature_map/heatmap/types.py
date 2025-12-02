"""Type definitions for the temperature map heatmap algorithms."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Wall:
    """Represents a wall segment."""
    x1: int
    y1: int
    x2: int
    y2: int


@dataclass
class TemperatureSensor:
    """Represents a temperature sensor with position and current reading."""
    entity: str
    x: int
    y: int
    temp: float
    label: str | None = None


@dataclass
class Point:
    """Represents a point in 2D space."""
    x: float
    y: float


@dataclass
class DistanceGrid:
    """Stores distance computations for each sensor."""
    distances: list[list[list[float]]]  # [sensorIndex][y][x] = distance
    width: int
    height: int
