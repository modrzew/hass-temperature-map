"""Test the Temperature Map config flow."""

from __future__ import annotations

from unittest.mock import patch

import pytest

# Try to import homeassistant, skip all tests if not available
try:
    from homeassistant import config_entries
    from homeassistant.core import HomeAssistant
    from homeassistant.data_entry_flow import FlowResultType

    from custom_components.temperature_map.const import (
        CONF_SENSORS,
        CONF_UPDATE_INTERVAL,
        CONF_WALLS,
        DOMAIN,
    )

    HA_AVAILABLE = True
except ImportError:
    HA_AVAILABLE = False
    # Define dummy values to allow module import
    CONF_SENSORS = None
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
    assert result["options"]["rotation"] == 90
