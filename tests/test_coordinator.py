"""Test the Temperature Map coordinator."""

from datetime import timedelta
from unittest.mock import AsyncMock, Mock

import pytest

# Try to import homeassistant, skip all tests if not available
try:
    from homeassistant import config_entries
    from homeassistant.core import HomeAssistant
    from custom_components.temperature_map.const import (
        CONF_SENSORS,
        CONF_UPDATE_INTERVAL,
        CONF_WALLS,
        DOMAIN,
    )
    from custom_components.temperature_map.coordinator import TemperatureMapCoordinator

    HA_AVAILABLE = True
except ImportError:
    HA_AVAILABLE = False
    # Define dummy values to allow module import
    CONF_SENSORS = None
    CONF_UPDATE_INTERVAL = None
    CONF_WALLS = None
    DOMAIN = None
    TemperatureMapCoordinator = None

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(not HA_AVAILABLE, reason="Home Assistant not installed"),
]


@pytest.fixture
def mock_hass():
    """Create a mock HomeAssistant instance."""
    hass = Mock(spec=HomeAssistant)
    hass.data = {}
    hass.states = Mock()
    hass.async_add_executor_job = AsyncMock()
    return hass


@pytest.fixture
def config_entry():
    """Create a config entry for testing."""
    return config_entries.ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Test Map",
        data={"name": "Test Map"},
        options={
            CONF_UPDATE_INTERVAL: 15,
            "comfort_min_temp": 20.0,
            "comfort_max_temp": 26.0,
            "ambient_temp": 22.0,
            "show_sensor_names": True,
            "show_sensor_temperatures": True,
            "rotation": 0,
            CONF_WALLS: [{"x1": 50, "y1": 50, "x2": 350, "y2": 50}],
            CONF_SENSORS: [{"entity": "sensor.test_temp", "x": 100, "y": 100}],
        },
        source="user",
        unique_id="test_map",
    )


async def test_coordinator_handles_update_interval_change(mock_hass, config_entry):
    """Test that coordinator handles update interval changes."""
    coordinator = TemperatureMapCoordinator(mock_hass, config_entry)

    # Initial interval
    assert coordinator.update_interval == timedelta(minutes=15)

    # Create a new config entry with updated options
    updated_entry = config_entries.ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Test Map",
        data=config_entry.data,
        options={
            **config_entry.options,
            CONF_UPDATE_INTERVAL: 30,  # Changed from 15 to 30
        },
        source="user",
        unique_id="test_map",
    )

    # Update coordinator's reference
    coordinator.config_entry = updated_entry

    # Mock async_request_refresh
    coordinator.async_request_refresh = AsyncMock()

    # Call the update handler
    await coordinator.async_config_entry_updated(mock_hass, updated_entry)

    # Check that interval was updated
    assert coordinator.update_interval == timedelta(minutes=30)

    # Check that refresh was requested
    coordinator.async_request_refresh.assert_called_once()


async def test_coordinator_handles_geometry_change(mock_hass, config_entry):
    """Test that coordinator detects geometry changes."""
    coordinator = TemperatureMapCoordinator(mock_hass, config_entry)

    # Set initial geometry cache
    coordinator._last_walls = config_entry.options[CONF_WALLS]
    coordinator._last_sensors = config_entry.options[CONF_SENSORS]

    # Create a new config entry with updated geometry
    updated_entry = config_entries.ConfigEntry(
        version=1,
        minor_version=0,
        domain=DOMAIN,
        title="Test Map",
        data=config_entry.data,
        options={
            **config_entry.options,
            CONF_WALLS: [{"x1": 100, "y1": 100, "x2": 400, "y2": 100}],  # Changed
        },
        source="user",
        unique_id="test_map",
    )

    # Update coordinator's reference
    coordinator.config_entry = updated_entry

    # Mock async_request_refresh
    coordinator.async_request_refresh = AsyncMock()

    # Call the update handler
    await coordinator.async_config_entry_updated(mock_hass, updated_entry)

    # Check that refresh was requested (geometry changed)
    coordinator.async_request_refresh.assert_called_once()
