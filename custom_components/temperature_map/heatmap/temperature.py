"""Temperature and color processing for temperature map."""
from __future__ import annotations

import math

from .types import DistanceGrid, Wall, TemperatureSensor
from .distance import get_interpolated_distance


def temperature_to_color(
    temp: float,
    comfort_min: float,
    comfort_max: float
) -> tuple[int, int, int]:
    """
    Convert temperature value to RGB color tuple based on comfort zone.

    Args:
        temp: Temperature value
        comfort_min: Minimum comfort temperature (below this appears blue/cold)
        comfort_max: Maximum comfort temperature (above this appears red/hot)

    Returns:
        RGB color tuple like (255, 0, 0)
    """
    # Define transition zones for smooth boundaries
    transition_range = 2  # Degrees for smooth transition

    # Far below comfort_min: Pure blue gradients
    if temp <= comfort_min - transition_range:
        # Create gradient from dark blue to medium blue
        cold_range = 8  # Range for cold gradient
        min_temp = comfort_min - transition_range - cold_range
        cold_normalized = max(0, min(1, (temp - min_temp) / cold_range))

        # Dark blue (0, 0, 128) to medium blue (0, 0, 255)
        blue = round(128 + (255 - 128) * cold_normalized)
        return (0, 0, blue)

    # Transition zone: Blue to green (smooth boundary around comfort_min)
    if temp <= comfort_min:
        transition_normalized = (temp - (comfort_min - transition_range)) / transition_range

        # Transition from blue (0, 0, 255) to blue-green (0, 255, 128)
        red = 0
        green = round(255 * transition_normalized)
        blue = round(255 - (255 - 128) * transition_normalized)

        return (red, green, blue)

    # Far above comfort_max: Red gradients
    if temp >= comfort_max + transition_range:
        # Create gradient from medium red to dark red
        warm_range = 8  # Range for warm gradient
        warm_normalized = max(
            0,
            min(1, (temp - (comfort_max + transition_range)) / warm_range)
        )

        # Medium red (255, 0, 0) to dark red (180, 0, 0)
        red = round(255 - (255 - 180) * warm_normalized)
        return (red, 0, 0)

    # Transition zone: Yellow to red (smooth boundary around comfort_max)
    if temp >= comfort_max:
        transition_normalized = (temp - comfort_max) / transition_range

        # Transition from yellow (255, 255, 0) to orange-red (255, 128, 0)
        red = 255
        green = round(255 - (255 - 128) * transition_normalized)
        blue = 0

        return (red, green, blue)

    # Comfort zone: Blue-green -> Green -> Yellow gradient
    comfort_range = comfort_max - comfort_min
    normalized_temp = (temp - comfort_min) / comfort_range

    # Start from blue-green (0, 255, 128) -> Green (0, 255, 0) -> Yellow (255, 255, 0)
    if normalized_temp <= 0.3:
        # First part: blue-green to pure green
        part_normalized = normalized_temp / 0.3
        red = 0
        green = 255
        blue = round(128 * (1 - part_normalized))
        return (red, green, blue)
    else:
        # Second part: green to yellow
        part_normalized = (normalized_temp - 0.3) / 0.7
        red = round(255 * part_normalized)
        green = 255
        blue = 0
        return (red, green, blue)


def interpolate_temperature_physics(
    x: float,
    y: float,
    sensors: list[TemperatureSensor],
    distance_grid: DistanceGrid,
    ambient_temp: float = 22,
    walls: list[Wall] | None = None
) -> float:
    """
    Physics-based temperature interpolation using flood fill distances.

    Heat flows naturally around obstacles like water or air.

    Args:
        x: Point x coordinate
        y: Point y coordinate
        sensors: List of sensor data with positions and temperatures
        distance_grid: Pre-computed distance grid from flood fill
        ambient_temp: Default ambient temperature
        walls: List of walls (for future extensions)

    Returns:
        Interpolated temperature at the given point
    """
    if not sensors:
        return ambient_temp

    # Calculate influences using flood fill distances only - no direct line checks
    # This ensures heat flows naturally around obstacles like water or air
    sensor_influences = []
    for index, sensor in enumerate(sensors):
        path_distance = get_interpolated_distance(x, y, index, distance_grid)

        # If flood fill couldn't reach this point, the sensor has no influence
        if path_distance == float('inf'):
            sensor_influences.append({
                "sensor": sensor,
                "influence": 0,
                "path_distance": float('inf'),
                "effective_distance": float('inf')
            })
            continue

        # Sensor dominance radius - within this distance, use exact sensor temperature
        dominance_radius = 8  # Smaller radius to match smaller sensor dots
        if path_distance <= dominance_radius:
            sensor_influences.append({
                "sensor": sensor,
                "influence": 100,  # High but not overwhelming influence
                "path_distance": path_distance,
                "effective_distance": path_distance
            })
            continue

        # Natural heat diffusion with gentler decay to allow flow-like spreading
        min_distance = 1
        effective_distance = max(path_distance, min_distance)

        # Gentler exponential decay for more natural heat flow
        decay_factor = 0.008  # Slower decay for better flow around obstacles
        influence = math.exp(-effective_distance * decay_factor)

        # Additional flow-based influence: heat spreads better in open areas
        # Bonus influence for sensors that can reach via shorter flood fill paths
        flow_bonus = 1 + math.exp(-path_distance / 30)  # Bonus decreases with path distance

        sensor_influences.append({
            "sensor": sensor,
            "influence": influence * flow_bonus,
            "path_distance": path_distance,
            "effective_distance": effective_distance
        })

    # Filter out unreachable sensors
    reachable_sensors = [s for s in sensor_influences if s["influence"] > 0]

    # If no sensors can reach this point, use ambient temperature
    if not reachable_sensors:
        return ambient_temp

    # Natural temperature blending - no artificial dominance boosts
    # Heat spreads naturally based on path accessibility
    total_influence = sum(s["influence"] for s in reachable_sensors)

    # Calculate weighted temperature based on natural flow influences
    weighted_temp = sum(
        s["sensor"].temp * s["influence"] for s in reachable_sensors
    ) / total_influence

    # Smooth blending with ambient temperature for areas with weak sensor influence
    influence_threshold = 0.02  # Higher threshold for more natural transitions
    if total_influence < influence_threshold:
        blend_factor = (total_influence / influence_threshold) ** 0.5  # Gentler blending curve
        return weighted_temp * blend_factor + ambient_temp * (1 - blend_factor)

    return weighted_temp


def interpolate_temperature_physics_with_circular_blending(
    x: float,
    y: float,
    sensors: list[TemperatureSensor],
    distance_grid: DistanceGrid,
    ambient_temp: float,
    walls: list[Wall]
) -> float:
    """
    Enhanced interpolation with circular blending around sensors to prevent square artifacts.

    Args:
        x: Point x coordinate
        y: Point y coordinate
        sensors: List of sensor data with positions and temperatures
        distance_grid: Pre-computed distance grid from flood fill
        ambient_temp: Default ambient temperature
        walls: List of walls

    Returns:
        Interpolated temperature with circular blending
    """
    # First, check if we're very close to any sensor for circular blending
    for sensor in sensors:
        direct_distance = math.sqrt((x - sensor.x) ** 2 + (y - sensor.y) ** 2)
        blend_radius = 12  # Circular blending radius around sensor

        if direct_distance <= blend_radius:
            # Get the base interpolated temperature (without this sensor's direct influence)
            base_temp = interpolate_temperature_physics(
                x,
                y,
                sensors,
                distance_grid,
                ambient_temp,
                walls
            )

            # Calculate circular blend factor (1.0 at sensor center, 0.0 at blend radius)
            blend_factor = max(0, (blend_radius - direct_distance) / blend_radius)

            # Apply smooth circular blending curve
            smooth_blend = blend_factor * blend_factor * (3 - 2 * blend_factor)  # Smoothstep

            # Blend between sensor temperature and base interpolated temperature
            return sensor.temp * smooth_blend + base_temp * (1 - smooth_blend)

    # If not near any sensor, use normal physics interpolation
    return interpolate_temperature_physics(
        x,
        y,
        sensors,
        distance_grid,
        ambient_temp,
        walls
    )
