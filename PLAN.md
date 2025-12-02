# Home Assistant Temperature Map Integration - Action Plan

## Overview

Create a Home Assistant custom integration that generates temperature heatmap images in the background, replacing the existing Lovelace frontend-only approach for better performance.

**Source reference:** Original component at `/Users/modrzew/Projects/lovelace-temperature-map/`

## Architecture

```
custom_components/temperature_map/
├── __init__.py           # Integration setup, YAML config handling
├── manifest.json         # Integration metadata
├── const.py              # Constants (DOMAIN, default values)
├── config_flow.py        # Optional: for future UI config
├── image.py              # ImageEntity implementation
├── coordinator.py        # DataUpdateCoordinator for 15-min updates
├── heatmap/              # Core heatmap algorithm (ported from TS)
│   ├── __init__.py
│   ├── types.py          # Wall, Sensor, DistanceGrid types
│   ├── geometry.py       # Line intersection, wall collision
│   ├── distance.py       # Flood fill, distance grid computation
│   └── temperature.py    # Temperature interpolation, color mapping
└── services.yaml         # Optional: manual refresh service
```

Frontend overlay card:
```
www/temperature-map-overlay.js  # Lovelace card for sensor dots overlay
```

## Tasks

### 1. Set up integration scaffold
- Create `custom_components/temperature_map/` directory
- Create `manifest.json` with required fields (domain, name, version, dependencies)
- Create `const.py` with DOMAIN constant and default config values
- Create basic `__init__.py` with YAML config schema and setup function

### 2. Port heatmap algorithm from TypeScript to Python
- Port `types.ts` → `heatmap/types.py` (Wall, TemperatureSensor, DistanceGrid, Point dataclasses)
- Port `geometry.ts` → `heatmap/geometry.py` (line_intersection, line_intersects_walls, check_wall_proximity)
- Port `distance.ts` → `heatmap/distance.py` (flood_fill_distances, compute_distance_grid, get_interpolated_distance, is_point_inside_boundary)
- Port `temperature.ts` → `heatmap/temperature.py` (temperature_to_color, interpolate_temperature_physics, interpolate_temperature_physics_with_circular_blending)

### 3. Implement image generation
- Create function to render heatmap to PIL Image
- Calculate canvas dimensions from walls/sensors (auto-calculate)
- Draw temperature colors pixel by pixel using interpolation
- Draw walls as lines
- Draw sensor dots with labels/temperatures
- Return PNG bytes

### 4. Implement DataUpdateCoordinator
- Create `coordinator.py` with `TemperatureMapCoordinator` class
- Set `update_interval` to 15 minutes (configurable)
- In `_async_update_data`:
  - Fetch current temperatures from sensor entities
  - Call heatmap rendering function
  - Store resulting image bytes
- Handle sensor state changes gracefully

### 5. Implement ImageEntity
- Create `image.py` with `TemperatureMapImage` class extending `ImageEntity`
- Implement `async_image()` to return bytes from coordinator
- Set `content_type` to `"image/png"`
- Update `image_last_updated` when coordinator refreshes
- Set appropriate `unique_id` and `name`

### 6. Wire up YAML configuration
- Define config schema in `__init__.py`:
  ```yaml
  temperature_map:
    - name: "Living Room"
      update_interval: 15  # minutes, optional
      comfort_min_temp: 20
      comfort_max_temp: 26
      ambient_temp: 22
      show_sensor_names: true
      show_sensor_temperatures: true
      rotation: 0  # 0, 90, 180, 270
      walls:
        - { x1: 50, y1: 50, x2: 350, y2: 50 }
      sensors:
        - { entity: "sensor.living_room_temp", x: 100, y: 100, label: "Living Room" }
  ```
- Validate configuration and create coordinator/entity per config entry

### 7. Create Lovelace overlay card
- Create `www/temperature-map-overlay.js` as a custom Lovelace card
- Accept config with image entity ID and sensor definitions
- Render the image entity as background
- Overlay clickable sensor dots at configured positions
- Handle click events to open Home Assistant's more-info dialog
- Support rotation transform to match integration setting

### 8. Write tests for core heatmap functionality
- Test geometry functions (line intersection, wall collision)
- Test flood fill distance computation
- Test temperature interpolation
- Test color mapping
- Focus on algorithm correctness, keep tests lightweight as requested

### 9. Add optional manual refresh service
- Create `services.yaml` defining `temperature_map.refresh` service
- Implement service handler in `__init__.py`
- Allow users to trigger immediate heatmap regeneration

### 10. Documentation
- Add README.md with installation and configuration instructions
- Include example YAML configuration
- Document the overlay card setup
- Add migration notes from the Lovelace-only component

## Key Algorithm Details (from original component)

### Flood Fill Distance (distance.ts)
- BFS-based flood fill from each sensor position
- 8-directional movement (including diagonals) with proper distance costs
- Walls block pathfinding between grid cells
- Boundary propagation passes for edge coverage

### Temperature Interpolation (temperature.ts)
- Physics-based using flood fill distances (not Euclidean)
- Sensor dominance radius of 8 pixels
- Exponential decay with factor 0.008
- Flow bonus based on path distance
- Circular blending around sensors (radius 12) to prevent artifacts

### Color Mapping (temperature.ts)
- Comfort zone gradient: blue-green → green → yellow
- Below comfort: blue gradient (dark blue to medium blue)
- Above comfort: red gradient (medium red to dark red)
- 2-degree transition zones for smooth boundaries

## Dependencies

Python packages (standard library or HA core):
- `Pillow` for image generation
- `homeassistant.helpers.update_coordinator`
- `homeassistant.components.image`

## Notes

- The Python port should maintain identical visual output to the TypeScript version
- Image generation happens in background thread to avoid blocking HA
- Consider caching distance grid between renders (only recompute when wall/sensor positions change)
