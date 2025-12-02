# Home Assistant Temperature Map Integration - Action Plan

## Overview

Create a Home Assistant custom integration that generates temperature heatmap images in the background, replacing the existing Lovelace frontend-only approach for better performance.

**Source reference:** Original component at `./lovelace-temperature-map/` (git submodule).

If the submodule directory is empty, run:
```bash
git submodule update --init --recursive
```

**Key source files to port:**
- `lovelace-temperature-map/src/lib/temperature-map/types.ts` - Type definitions
- `lovelace-temperature-map/src/lib/temperature-map/geometry.ts` - Line intersection, wall collision
- `lovelace-temperature-map/src/lib/temperature-map/distance.ts` - Flood fill algorithm
- `lovelace-temperature-map/src/lib/temperature-map/temperature.ts` - Temperature interpolation & colors
- `lovelace-temperature-map/src/cards/temperature-map-card.tsx` - Rendering logic reference

**Additional documentation:**
- `HA_INTEGRATION_GUIDE.md` - How to structure Home Assistant integration code

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

## Implementation Notes

### General
- The Python port should maintain identical visual output to the TypeScript version
- Image generation happens in background thread via `async_add_executor_job` to avoid blocking HA
- Consider caching distance grid between renders (only recompute when wall/sensor positions change)

### TypeScript to Python Porting

When porting the algorithms:

1. **Math functions are the same**: `Math.sqrt` → `math.sqrt`, `Math.abs` → `abs()`, `Math.max/min` → `max()/min()`

2. **Type hints**: Use Python dataclasses instead of TypeScript interfaces:
   ```python
   @dataclass
   class Wall:
       x1: int
       y1: int
       x2: int
       y2: int
   ```

3. **Collections**:
   - `Set<string>` → `set[str]` (use f-strings for keys like `f"{x},{y}"`)
   - `Map<K,V>` → `dict[K,V]`
   - `Array<T>` → `list[T]`

4. **Infinity**: `Infinity` → `float('inf')`

5. **Optional chaining**: `obj?.prop` → `obj.prop if obj else None` or use `getattr(obj, 'prop', default)`

### Image Rendering with Pillow

```python
from PIL import Image, ImageDraw, ImageFont

# Create image
img = Image.new('RGBA', (width, height), (255, 255, 255, 0))

# Direct pixel access (for heatmap)
pixels = img.load()
pixels[x, y] = (r, g, b, a)

# Or use putpixel (slower but simpler)
img.putpixel((x, y), (r, g, b, a))

# Drawing overlays
draw = ImageDraw.Draw(img)
draw.line([(x1, y1), (x2, y2)], fill=(51, 51, 51), width=2)
draw.ellipse([x-6, y-6, x+6, y+6], fill=(255,255,255), outline=(51,51,51))
draw.text((x, y), "Label", fill=(51,51,51), anchor="mm")  # mm = middle-middle

# Export to bytes
from io import BytesIO
buffer = BytesIO()
img.save(buffer, format='PNG')
return buffer.getvalue()
```

### Performance Considerations

1. **Distance grid is expensive** - The flood fill runs BFS for each sensor. Cache this between renders if walls/sensors haven't moved.

2. **Pixel-by-pixel rendering** - For a 400x300 image, that's 120,000 pixels. Consider:
   - Using numpy for vectorized operations if available
   - Processing in chunks if memory is a concern
   - The original uses `gridScale=1` (full resolution) - you might start with 2 or 4 for faster initial testing

3. **Run rendering in executor** - Always use `await hass.async_add_executor_job(render_func, ...)` since Pillow operations block

### Lovelace Overlay Card

The overlay card needs to:
1. Display the image entity (use `<hui-image>` or `<img>` with HA auth headers)
2. Position sensor dots absolutely on top
3. Handle click → dispatch `hass-more-info` event

Basic structure:
```javascript
class TemperatureMapOverlay extends HTMLElement {
  setConfig(config) {
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _render() {
    // Get image URL from entity
    const entity = this._hass.states[this._config.image_entity];
    const imageUrl = `/api/image_proxy/${this._config.image_entity}`;

    // Render image + sensor dots
  }

  _handleSensorClick(entityId) {
    const event = new CustomEvent('hass-more-info', {
      detail: { entityId },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }
}
customElements.define('temperature-map-overlay', TemperatureMapOverlay);
```
