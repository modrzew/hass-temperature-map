"""Test the Temperature Map options flow."""

from __future__ import annotations

import pytest

# Try to import homeassistant, skip all tests if not available
try:
    from homeassistant import config_entries
    from homeassistant.core import HomeAssistant
    from homeassistant.data_entry_flow import FlowResultType
    from custom_components.temperature_map.const import (
        CONF_COMFORT_MAX_TEMP,
        CONF_COMFORT_MIN_TEMP,
        CONF_ROTATION,
        CONF_SENSORS,
        CONF_UPDATE_INTERVAL,
        CONF_WALLS,
        DOMAIN,
    )

    HA_AVAILABLE = True
except ImportError:
    HA_AVAILABLE = False
    # Define dummy values to allow module import
    CONF_COMFORT_MAX_TEMP = None
    CONF_COMFORT_MIN_TEMP = None
    CONF_ROTATION = None
    CONF_SENSORS = None
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
            "ambient_temp": 22.0,
            "show_sensor_names": True,
            "show_sensor_temperatures": True,
            CONF_ROTATION: 0,
            CONF_WALLS: [{"x1": 50, "y1": 50, "x2": 350, "y2": 50}],
            CONF_SENSORS: [{"entity": "sensor.test_temp", "x": 100, "y": 100}],
        },
        source="user",
        unique_id="test_map",
    )
    entry.add_to_hass(hass)
    return entry


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
            "ambient_temp": 21.0,
            "show_sensor_names": False,
            "show_sensor_temperatures": False,
            CONF_ROTATION: 90,
        },
    )

    # Move to geometry step and keep existing
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
    assert result["data"][CONF_UPDATE_INTERVAL] == 30
    assert result["data"][CONF_ROTATION] == 90


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
            "ambient_temp": 22.0,
            "show_sensor_names": True,
            "show_sensor_temperatures": True,
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
