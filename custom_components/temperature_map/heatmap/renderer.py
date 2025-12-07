"""Image rendering for temperature map using Pillow."""

from __future__ import annotations

import logging
from io import BytesIO
from typing import Any

from PIL import Image, ImageDraw, ImageFont

from .distance import compute_distance_grid
from .temperature import (
    interpolate_temperature_physics_with_circular_blending,
    temperature_to_color,
)
from .types import TemperatureSensor, Wall

_LOGGER = logging.getLogger(__name__)


def _transform_point(
    x: float, y: float, rotation: int, orig_width: int, orig_height: int
) -> tuple[float, float]:
    """
    Transform a point's coordinates based on image rotation.

    When PIL rotates an image with expand=True, points move to new positions.
    This function calculates where a point (x, y) ends up after rotation.

    Args:
        x: Original x coordinate
        y: Original y coordinate
        rotation: Rotation angle (0, 90, 180, 270)
        orig_width: Original image width before rotation
        orig_height: Original image height before rotation

    Returns:
        Tuple of (new_x, new_y) coordinates after rotation
    """
    if rotation == 90:
        # rotate(-90) clockwise: point (x,y) moves to (height-y, x)
        return (orig_height - y, x)
    elif rotation == 180:
        # rotate(180): point (x,y) moves to (width-x, height-y)
        return (orig_width - x, orig_height - y)
    elif rotation == 270:
        # rotate(90) counterclockwise: point (x,y) moves to (y, width-x)
        return (y, orig_width - x)
    else:
        # No rotation
        return (x, y)


def render_heatmap_image(
    walls: list[dict[str, int]],
    sensors: list[dict[str, Any]],
    comfort_min: float = 20,
    comfort_max: float = 26,
    ambient_temp: float = 22,
    show_names: bool = True,
    show_temps: bool = True,
    rotation: int = 0,
) -> tuple[bytes, list[dict[str, Any]]]:
    """
    Render the complete heatmap image with temperature colors, walls, and sensors.

    Args:
        walls: List of wall dictionaries with x1, y1, x2, y2
        sensors: List of sensor dictionaries with x, y, temp, label
        comfort_min: Minimum comfort temperature
        comfort_max: Maximum comfort temperature
        ambient_temp: Ambient temperature for areas without sensor influence
        show_names: Whether to show sensor names
        show_temps: Whether to show sensor temperatures
        rotation: Image rotation (0, 90, 180, 270)

    Returns:
        Tuple of (PNG image as bytes, adjusted sensor coordinates with rotation applied)
    """
    # Convert dict walls to Wall objects
    wall_objects = [Wall(x1=w["x1"], y1=w["y1"], x2=w["x2"], y2=w["y2"]) for w in walls]

    # Convert dict sensors to TemperatureSensor objects
    sensor_objects = [
        TemperatureSensor(
            entity=s.get("entity", ""), x=s["x"], y=s["y"], temp=s["temp"], label=s.get("label")
        )
        for s in sensors
    ]

    # Calculate canvas dimensions from walls and sensors
    all_x = []
    all_y = []

    for wall in wall_objects:
        all_x.extend([wall.x1, wall.x2])
        all_y.extend([wall.y1, wall.y2])

    for sensor in sensor_objects:
        all_x.append(sensor.x)
        all_y.append(sensor.y)

    if not all_x or not all_y:
        # Default size if no walls or sensors
        width, height = 400, 300
    else:
        # Add padding around the content
        padding = 40
        min_x = min(all_x)
        max_x = max(all_x)
        min_y = min(all_y)
        max_y = max(all_y)

        width = int(max_x - min_x + padding * 2)
        height = int(max_y - min_y + padding * 2)

        # Adjust wall and sensor coordinates to account for padding
        offset_x = padding - min_x
        offset_y = padding - min_y

        wall_objects = [
            Wall(x1=w.x1 + offset_x, y1=w.y1 + offset_y, x2=w.x2 + offset_x, y2=w.y2 + offset_y)
            for w in wall_objects
        ]

        sensor_objects = [
            TemperatureSensor(
                entity=s.entity, x=s.x + offset_x, y=s.y + offset_y, temp=s.temp, label=s.label
            )
            for s in sensor_objects
        ]

    _LOGGER.debug(
        "Rendering temperature map: %dx%d pixels, %d walls, %d sensors",
        width,
        height,
        len(wall_objects),
        len(sensor_objects),
    )

    # Create image
    img = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    pixels = img.load()

    # Only render heatmap if we have sensors
    if sensor_objects:
        _LOGGER.debug("Computing distance grid and rendering heatmap...")
        # Compute distance grid
        distance_grid = compute_distance_grid(sensor_objects, wall_objects, width, height)

        # Pre-compute boundary points once (avoid recomputing for each pixel)
        from .distance import _compute_boundary_points

        boundary_points = _compute_boundary_points(wall_objects, width, height, sensor_objects)
        _LOGGER.debug("Boundary contains %d points", len(boundary_points))

        # Render heatmap pixel by pixel
        for y in range(height):
            for x in range(width):
                # Check if point is inside boundary (using pre-computed boundary)
                if f"{int(x)},{int(y)}" in boundary_points:
                    # Interpolate temperature at this point
                    temp = interpolate_temperature_physics_with_circular_blending(
                        x, y, sensor_objects, distance_grid, ambient_temp, wall_objects
                    )

                    # Convert temperature to color
                    color = temperature_to_color(temp, comfort_min, comfort_max)

                    # Set pixel color with full opacity
                    pixels[x, y] = (*color, 255)
        _LOGGER.debug("Heatmap rendering complete")
    else:
        _LOGGER.info(
            "No sensors available - rendering floor plan only (walls without temperature data)"
        )

    # Draw walls
    draw = ImageDraw.Draw(img)
    for wall in wall_objects:
        draw.line([(wall.x1, wall.y1), (wall.x2, wall.y2)], fill=(51, 51, 51), width=2)

    # Draw sensors (dots only - labels drawn after rotation)
    radius = 6
    for sensor in sensor_objects:
        draw.ellipse(
            [sensor.x - radius, sensor.y - radius, sensor.x + radius, sensor.y + radius],
            fill=(255, 255, 255),
            outline=(51, 51, 51),
            width=2,
        )

    # Store original dimensions and sensor positions for coordinate transformation
    orig_width = width
    orig_height = height

    # Apply rotation if requested
    if rotation == 90:
        img = img.rotate(-90, expand=True)
        _LOGGER.debug("Applied 90° rotation")
    elif rotation == 180:
        img = img.rotate(180, expand=True)
        _LOGGER.debug("Applied 180° rotation")
    elif rotation == 270:
        img = img.rotate(90, expand=True)
        _LOGGER.debug("Applied 270° rotation")

    # Draw labels AFTER rotation so they stay upright
    if show_names or show_temps:
        # Create new draw context after rotation
        draw = ImageDraw.Draw(img)

        # Load font once
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 12)
        except OSError:
            _LOGGER.debug("DejaVu font not found, using default font")
            font = ImageFont.load_default()

        for sensor in sensor_objects:
            # Transform sensor coordinates based on rotation
            sensor_x, sensor_y = _transform_point(
                sensor.x, sensor.y, rotation, orig_width, orig_height
            )

            # Build label text
            labels = []
            if show_names and sensor.label:
                labels.append(sensor.label)
            if show_temps:
                labels.append(f"{sensor.temp:.1f}°C")

            if labels:
                label_text = "\n".join(labels)

                # Position label below the sensor dot
                text_y = sensor_y + radius + 5
                bbox = draw.textbbox((0, 0), label_text, font=font, align="center")
                text_width = bbox[2] - bbox[0]

                # Center text horizontally
                text_x = sensor_x - text_width / 2

                # Draw text directly without background (fully transparent)
                draw.text(
                    (text_x, text_y),
                    label_text,
                    fill=(51, 51, 51),
                    font=font,
                    align="center",
                )

    # Convert to PNG bytes
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    image_bytes = buffer.getvalue()
    _LOGGER.debug(
        "Image rendering complete: %d bytes, final size %dx%d",
        len(image_bytes),
        img.width,
        img.height,
    )

    # Build adjusted sensor coordinates for frontend overlay
    # These match the positions where sensors were actually rendered in the image
    adjusted_sensors = []
    for sensor in sensor_objects:
        # Transform coordinates based on rotation to match rendered positions
        sensor_x, sensor_y = _transform_point(sensor.x, sensor.y, rotation, orig_width, orig_height)

        adjusted_sensors.append(
            {
                "entity": sensor.entity,
                "x": sensor_x,
                "y": sensor_y,
                "label": sensor.label,
            }
        )

    return image_bytes, adjusted_sensors
