"""Test the Temperature Map config flow."""

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
def mock_setup_entry():
    """Mock async_setup_entry."""
    with patch(
        "custom_components.temperature_map.async_setup_entry",
        return_value=True,
    ) as mock_setup:
        yield mock_setup


async def test_user_flow_minimal(hass: HomeAssistant, mock_setup_entry):
    """Test user config flow with minimal input."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # Submit basic config
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Test Map",
            "update_interval": 15,
            "comfort_min_temp": 20,
            "comfort_max_temp": 26,
            "ambient_temp": 22,
            "show_sensor_names": True,
            "show_sensor_temperatures": True,
            "rotation": 0,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "geometry"

    # Submit geometry config
    walls_json = '[{"x1": 50, "y1": 50, "x2": 350, "y2": 50}]'
    sensors_json = '[{"entity": "sensor.test_temp", "x": 100, "y": 100}]'

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_WALLS: walls_json,
            CONF_SENSORS: sensors_json,
        },
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test Map"
    assert result["data"]["name"] == "Test Map"
    assert result["options"][CONF_UPDATE_INTERVAL] == 15
    assert result["options"][CONF_WALLS] == [{"x1": 50, "y1": 50, "x2": 350, "y2": 50}]
    assert result["options"][CONF_SENSORS] == [{"entity": "sensor.test_temp", "x": 100, "y": 100}]


async def test_user_flow_invalid_json(hass: HomeAssistant):
    """Test user flow with invalid JSON."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Submit basic config
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Test Map",
        },
    )

    # Submit invalid JSON
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_WALLS: "not valid json",
            CONF_SENSORS: '[{"entity": "sensor.test", "x": 100, "y": 100}]',
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"]


async def test_user_flow_invalid_wall_schema(hass: HomeAssistant):
    """Test user flow with invalid wall schema."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Submit basic config
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Test Map",
        },
    )

    # Submit wall missing required field
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_WALLS: '[{"x1": 50, "y1": 50}]',  # Missing x2, y2
            CONF_SENSORS: '[{"entity": "sensor.test", "x": 100, "y": 100}]',
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"]


async def test_user_flow_empty_sensors(hass: HomeAssistant):
    """Test user flow with empty sensors list."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Submit basic config
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Test Map",
        },
    )

    # Submit empty sensors
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_WALLS: '[{"x1": 50, "y1": 50, "x2": 350, "y2": 50}]',
            CONF_SENSORS: "[]",
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"]["base"]


async def test_user_flow_duplicate_name(hass: HomeAssistant, mock_setup_entry):
    """Test user flow with duplicate name."""
    # Create first entry
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Test Map",
        },
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_WALLS: '[{"x1": 50, "y1": 50, "x2": 350, "y2": 50}]',
            CONF_SENSORS: '[{"entity": "sensor.test", "x": 100, "y": 100}]',
        },
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Try to create second entry with same name
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Test Map",  # Same name
        },
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_import_flow(hass: HomeAssistant, mock_setup_entry):
    """Test import from YAML."""
    yaml_config = {
        "name": "Living Room",
        "update_interval": 20,
        "comfort_min_temp": 19.0,
        "comfort_max_temp": 25.0,
        "ambient_temp": 21.0,
        "show_sensor_names": False,
        "show_sensor_temperatures": True,
        "rotation": 90,
        "walls": [{"x1": 50, "y1": 50, "x2": 350, "y2": 50}],
        "sensors": [{"entity": "sensor.living_room_temp", "x": 100, "y": 100, "label": "LR"}],
    }

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data=yaml_config,
    )

    assert result["type"] == FlowResultType.CREATE_ENTRY
    assert result["title"] == "Living Room"
    assert result["data"]["name"] == "Living Room"
    assert result["options"]["update_interval"] == 20
    assert result["options"]["comfort_min_temp"] == 19.0
    assert result["options"]["rotation"] == 90
    assert result["options"]["show_sensor_names"] is False


async def test_import_flow_duplicate(hass: HomeAssistant, mock_setup_entry):
    """Test importing duplicate YAML config."""
    yaml_config = {
        "name": "Living Room",
        "walls": [{"x1": 50, "y1": 50, "x2": 350, "y2": 50}],
        "sensors": [{"entity": "sensor.test", "x": 100, "y": 100}],
    }

    # Import first time
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data=yaml_config,
    )
    assert result["type"] == FlowResultType.CREATE_ENTRY

    # Import second time (should abort)
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_IMPORT},
        data=yaml_config,
    )
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
