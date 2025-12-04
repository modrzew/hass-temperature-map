"""Test the Temperature Map options flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

# Try to import homeassistant, skip all tests if not available
try:
    from homeassistant import config_entries
    from homeassistant.core import HomeAssistant
    from homeassistant.data_entry_flow import FlowResultType
    from custom_components.temperature_map.const import (
        CONF_AMBIENT_TEMP,
        CONF_COMFORT_MAX_TEMP,
        CONF_COMFORT_MIN_TEMP,
        CONF_ROTATION,
        CONF_SENSORS,
        CONF_SHOW_SENSOR_NAMES,
        CONF_SHOW_SENSOR_TEMPERATURES,
        CONF_UPDATE_INTERVAL,
        CONF_WALLS,
        DOMAIN,
    )

    HA_AVAILABLE = True
except ImportError:
    HA_AVAILABLE = False
    # Define dummy values to allow module import
    CONF_AMBIENT_TEMP = None
    CONF_COMFORT_MAX_TEMP = None
    CONF_COMFORT_MIN_TEMP = None
    CONF_ROTATION = None
    CONF_SENSORS = None
    CONF_SHOW_SENSOR_NAMES = None
    CONF_SHOW_SENSOR_TEMPERATURES = None
    CONF_UPDATE_INTERVAL = None
    CONF_WALLS = None
    DOMAIN = None

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not HA_AVAILABLE, reason="Home Assistant not installed"),
]


@pytest.fixture
async def config_entry(hass: HomeAssistant):
    """Create a config entry for testing."""
    entry = config_entries.ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Test Map",
        data={"name": "Test Map"},
        options={
            CONF_UPDATE_INTERVAL: 15,
            CONF_COMFORT_MIN_TEMP: 20.0,
            CONF_COMFORT_MAX_TEMP: 26.0,
            CONF_AMBIENT_TEMP: 22.0,
            CONF_SHOW_SENSOR_NAMES: True,
            CONF_SHOW_SENSOR_TEMPERATURES: True,
            CONF_ROTATION: 0,
            CONF_WALLS: [{"x1": 50, "y1": 50, "x2": 350, "y2": 50}],
            CONF_SENSORS: [{"entity": "sensor.test_temp", "x": 100, "y": 100}],
        },
        source="user",
        unique_id="test_map",
    )
    entry.add_to_hass(hass)
    return entry


async def test_options_flow_init(hass: HomeAssistant, config_entry):
    """Test options flow initialization."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "init"

    # Check that current values are pre-filled
    schema = result["data_schema"].schema
    assert schema[CONF_UPDATE_INTERVAL].default() == 15
    assert schema[CONF_COMFORT_MIN_TEMP].default() == 20.0
    assert schema[CONF_COMFORT_MAX_TEMP].default() == 26.0
    assert schema[CONF_ROTATION].default() == 0


async def test_options_flow_change_temperature_settings(hass: HomeAssistant, config_entry):
    """Test changing temperature settings via options flow."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Change temperature settings
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_UPDATE_INTERVAL: 30,
            CONF_COMFORT_MIN_TEMP: 18.0,
            CONF_COMFORT_MAX_TEMP: 24.0,
            CONF_AMBIENT_TEMP: 21.0,
            CONF_SHOW_SENSOR_NAMES: False,
            CONF_SHOW_SENSOR_TEMPERATURES: False,
            CONF_ROTATION: 90,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "geometry"


async def test_options_flow_change_geometry(hass: HomeAssistant, config_entry):
    """Test changing geometry via options flow."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Submit temperature settings (keeping defaults)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_UPDATE_INTERVAL: 15,
            CONF_COMFORT_MIN_TEMP: 20.0,
            CONF_COMFORT_MAX_TEMP: 26.0,
            CONF_AMBIENT_TEMP: 22.0,
            CONF_SHOW_SENSOR_NAMES: True,
            CONF_SHOW_SENSOR_TEMPERATURES: True,
            CONF_ROTATION: 0,
        },
    )

    # Change geometry
    new_walls = '[{"x1": 100, "y1": 100, "x2": 400, "y2": 100}]'
    new_sensors = '[{"entity": "sensor.new_temp", "x": 200, "y": 200, "label": "New"}]'

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_WALLS: new_walls,
            CONF_SENSORS: new_sensors,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["data"][CONF_WALLS] == [{"x1": 100, "y1": 100, "x2": 400, "y2": 100}]
    assert result["data"][CONF_SENSORS] == [
        {"entity": "sensor.new_temp", "x": 200, "y": 200, "label": "New"}
    ]


async def test_options_flow_keep_existing_geometry(hass: HomeAssistant, config_entry):
    """Test keeping existing geometry (not changing it)."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Submit temperature settings
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_UPDATE_INTERVAL: 20,
            CONF_COMFORT_MIN_TEMP: 19.0,
            CONF_COMFORT_MAX_TEMP: 25.0,
            CONF_AMBIENT_TEMP: 21.5,
            CONF_SHOW_SENSOR_NAMES: True,
            CONF_SHOW_SENSOR_TEMPERATURES: False,
            CONF_ROTATION: 180,
        },
    )

    # Submit geometry step with original values (pre-filled)
    # The default values should be the current geometry as JSON
    original_walls = '[{"x1": 50, "y1": 50, "x2": 350, "y2": 50}]'
    original_sensors = '[{"entity": "sensor.test_temp", "x": 100, "y": 100}]'

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_WALLS: original_walls,
            CONF_SENSORS: original_sensors,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    # Temperature settings should be updated
    assert result["data"][CONF_UPDATE_INTERVAL] == 20
    assert result["data"][CONF_COMFORT_MIN_TEMP] == 19.0
    assert result["data"][CONF_ROTATION] == 180
    # Geometry should remain the same
    assert result["data"][CONF_WALLS] == [{"x1": 50, "y1": 50, "x2": 350, "y2": 50}]
    assert result["data"][CONF_SENSORS] == [{"entity": "sensor.test_temp", "x": 100, "y": 100}]


async def test_options_flow_invalid_geometry_json(hass: HomeAssistant, config_entry):
    """Test options flow with invalid geometry JSON."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Submit temperature settings
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_UPDATE_INTERVAL: 15,
            CONF_COMFORT_MIN_TEMP: 20.0,
            CONF_COMFORT_MAX_TEMP: 26.0,
            CONF_AMBIENT_TEMP: 22.0,
            CONF_SHOW_SENSOR_NAMES: True,
            CONF_SHOW_SENSOR_TEMPERATURES: True,
            CONF_ROTATION: 0,
        },
    )

    # Submit invalid geometry JSON
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_WALLS: "not valid json",
            CONF_SENSORS: '[{"entity": "sensor.test", "x": 100, "y": 100}]',
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "geometry"
    assert result["errors"]["base"]


async def test_options_flow_empty_sensors(hass: HomeAssistant, config_entry):
    """Test options flow with empty sensors."""
    result = await hass.config_entries.options.async_init(config_entry.entry_id)

    # Submit temperature settings
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_UPDATE_INTERVAL: 15,
            CONF_COMFORT_MIN_TEMP: 20.0,
            CONF_COMFORT_MAX_TEMP: 26.0,
            CONF_AMBIENT_TEMP: 22.0,
            CONF_SHOW_SENSOR_NAMES: True,
            CONF_SHOW_SENSOR_TEMPERATURES: True,
            CONF_ROTATION: 0,
        },
    )

    # Submit empty sensors
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_WALLS: '[{"x1": 50, "y1": 50, "x2": 350, "y2": 50}]',
            CONF_SENSORS: "[]",
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "geometry"
    assert result["errors"]["base"]
