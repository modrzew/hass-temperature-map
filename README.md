# Home Assistant Temperature Map Integration

A custom Home Assistant integration that generates temperature heatmap images in the background, showing interpolated temperature distributions across your home based on physical sensor locations.

## Features

- **Physics-based temperature interpolation** - Heat flows naturally around walls and obstacles using flood-fill pathfinding
- **Background image generation** - Updates every 15 minutes (configurable) without blocking the UI
- **Image entity** - Exposes a standard Home Assistant image entity that can be displayed anywhere
- **Customizable appearance** - Configure comfort zones, colors, sensor labels, and rotation
- **Lovelace overlay card** - Optional card with clickable sensor dots for easy access to sensor details
- **Manual refresh service** - Trigger immediate heatmap regeneration when needed

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Go to "Integrations"
3. Click the three dots in the top right and select "Custom repositories"
4. Add this repository URL: `https://github.com/modrzew/hass-temperature-map`
5. Select "Integration" as the category
6. Click "Install"
7. Restart Home Assistant

The frontend overlay card is automatically registered - no manual resource configuration needed!

### Manual Installation

1. Copy the `custom_components/temperature_map` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

### YAML Configuration

Add the following to your `configuration.yaml`:

```yaml
temperature_map:
  - name: "Living Room"
    update_interval: 15  # minutes (optional, default: 15)
    comfort_min_temp: 20  # °C (optional, default: 20)
    comfort_max_temp: 26  # °C (optional, default: 26)
    ambient_temp: 22  # °C (optional, default: 22)
    show_sensor_names: true  # optional, default: true
    show_sensor_temperatures: true  # optional, default: true
    rotation: 0  # 0, 90, 180, or 270 (optional, default: 0)
    walls:
      - { x1: 50, y1: 50, x2: 350, y2: 50 }
      - { x1: 350, y1: 50, x2: 350, y2: 250 }
      - { x1: 350, y1: 250, x2: 50, y2: 250 }
      - { x1: 50, y1: 250, x2: 50, y2: 50 }
      - { x1: 200, y1: 50, x2: 200, y2: 150 }  # Interior wall
    sensors:
      - entity: sensor.living_room_temperature
        x: 100
        y: 100
        label: "Living Room"  # optional
      - entity: sensor.kitchen_temperature
        x: 280
        y: 100
        label: "Kitchen"
      - entity: sensor.bedroom_temperature
        x: 100
        y: 200
        label: "Bedroom"
```

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `name` | string | **required** | Unique name for this temperature map |
| `update_interval` | integer | 15 | Update interval in minutes |
| `comfort_min_temp` | float | 20 | Minimum comfort temperature (°C). Below this appears blue |
| `comfort_max_temp` | float | 26 | Maximum comfort temperature (°C). Above this appears red |
| `ambient_temp` | float | 22 | Ambient temperature for areas without sensor influence |
| `show_sensor_names` | boolean | true | Display sensor labels on the map |
| `show_sensor_temperatures` | boolean | true | Display temperature values on the map |
| `rotation` | integer | 0 | Rotate the image (0, 90, 180, or 270 degrees) |
| `walls` | list | **required** | List of wall segments (see below) |
| `sensors` | list | **required** | List of temperature sensors (see below) |

#### Wall Configuration

Each wall is defined by two points (start and end):

```yaml
walls:
  - x1: 50   # Start X coordinate
    y1: 50   # Start Y coordinate
    x2: 350  # End X coordinate
    y2: 50   # End Y coordinate
```

Walls block heat flow in the interpolation algorithm and are drawn as lines on the map.

#### Sensor Configuration

Each sensor requires an entity ID and coordinates:

```yaml
sensors:
  - entity: sensor.living_room_temperature  # Required: HA temperature sensor entity
    x: 100                                  # Required: X coordinate
    y: 100                                  # Required: Y coordinate
    label: "Living Room"                    # Optional: Display label (defaults to friendly name)
```

## Usage

### Basic Image Display

Once configured, the integration creates an image entity that you can display in any Lovelace card:

```yaml
type: picture
image: image.temperature_map_living_room
```

### Lovelace Overlay Card (Recommended)

For interactive sensor dots, use the custom overlay card. The frontend resource is **automatically registered** when you install the integration - no manual setup required!

Simply add the card to your dashboard:

```yaml
type: custom:temperature-map-overlay
image_entity: image.temperature_map_living_room
rotation: 0  # Optional: must match the integration rotation setting
sensors:
  - entity: sensor.living_room_temperature
    x: 100
    y: 100
  - entity: sensor.kitchen_temperature
    x: 280
    y: 100
  - entity: sensor.bedroom_temperature
    x: 100
    y: 200
```

**Notes:**
- The sensor coordinates in the card must match those in the integration configuration
- After installing/updating via HACS, do a hard refresh (Ctrl+Shift+R / Cmd+Shift+R) in your browser to load the new frontend resources

### Manual Refresh

To manually trigger a heatmap refresh:

```yaml
service: temperature_map.refresh
```

Or call it from an automation or script:

```yaml
automation:
  - alias: "Refresh temperature map hourly"
    trigger:
      - platform: time_pattern
        minutes: "/60"
    action:
      - service: temperature_map.refresh
```

## How It Works

### Temperature Interpolation

The integration uses a physics-based algorithm to interpolate temperatures:

1. **Flood Fill Distance Calculation** - For each sensor, compute the shortest path distance to every point on the map, considering walls as obstacles
2. **Temperature Blending** - Blend sensor temperatures based on path distances with exponential decay
3. **Circular Blending** - Apply smooth circular blending around sensors to prevent artifacts
4. **Color Mapping** - Convert temperatures to colors based on comfort zones

### Color Scheme

- **Very Cold** (< comfort_min - 2°C): Dark blue → Medium blue
- **Cold** (comfort_min - 2°C to comfort_min): Blue → Blue-green
- **Comfort Zone** (comfort_min to comfort_max): Blue-green → Green → Yellow
- **Warm** (comfort_max to comfort_max + 2°C): Yellow → Orange-red
- **Very Hot** (> comfort_max + 2°C): Red → Dark red

## Migrating from Lovelace-only Component

If you're migrating from the frontend-only [lovelace-temperature-map](https://github.com/modrzew/lovelace-temperature-map):

1. Keep your existing wall and sensor coordinates - they work exactly the same way
2. Move the configuration from Lovelace card config to `configuration.yaml`
3. Replace the old card with either:
   - A simple `picture` card showing the image entity, or
   - The new `temperature-map-overlay` card for clickable sensors
4. The visual output should be identical to the original component

### Benefits of Migration

- **Better Performance** - Image generation runs in background, not during UI render
- **Lower Browser Load** - Static image instead of live canvas rendering
- **Persistent State** - Image persists even when dashboard isn't open
- **Easier Sharing** - Can display the image in multiple places, automations, notifications, etc.

## Troubleshooting

### Image not updating

1. Check the Home Assistant logs for errors
2. Verify all sensor entities are available and returning numeric values
3. Try manually calling the `temperature_map.refresh` service

### Sensors not showing valid temperatures

The integration skips sensors that are unavailable or have non-numeric states. Check that:
- Sensor entities exist and are spelled correctly
- Sensors are returning numeric temperature values
- Sensors aren't in "unknown" or "unavailable" state

### Walls not blocking heat flow correctly

- Verify wall coordinates are correct
- Ensure walls form complete barriers where needed
- Remember that heat can flow around wall endpoints

### Performance issues

- Reduce `update_interval` to update less frequently
- Simplify wall geometry if very complex
- The first render may take a few seconds; subsequent renders use cached calculations

## Development

### Running Tests

```bash
pytest tests/ -v
```

### Project Structure

```
custom_components/temperature_map/
├── __init__.py          # Integration setup, YAML config
├── manifest.json        # Integration metadata
├── const.py             # Constants
├── coordinator.py       # DataUpdateCoordinator
├── image.py             # ImageEntity platform
├── services.yaml        # Service definitions
└── heatmap/             # Core algorithms
    ├── types.py         # Data classes
    ├── geometry.py      # Line intersection, wall collision
    ├── distance.py      # Flood fill, distance computation
    ├── temperature.py   # Temperature interpolation, colors
    └── renderer.py      # Pillow image generation
```

## License

MIT License - see LICENSE file for details

## Credits

Ported from the original [lovelace-temperature-map](https://github.com/modrzew/lovelace-temperature-map) frontend component by [@modrzew](https://github.com/modrzew).

## Support

For issues, feature requests, or questions:
- [GitHub Issues](https://github.com/modrzew/hass-temperature-map/issues)
- [Home Assistant Community Forum](https://community.home-assistant.io/)
