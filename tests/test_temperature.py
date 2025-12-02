"""Tests for temperature module."""
import pytest

from custom_components.temperature_map.heatmap.temperature import (
    temperature_to_color,
)


def test_temperature_to_color_cold():
    """Test cold temperature color mapping."""
    # Very cold (below comfort min - transition)
    color = temperature_to_color(10, 20, 26)
    assert color[0] == 0  # Red component
    assert color[1] == 0  # Green component
    assert color[2] > 128  # Blue component (should be bluish)


def test_temperature_to_color_comfort_min():
    """Test comfort minimum temperature."""
    # At comfort minimum
    color = temperature_to_color(20, 20, 26)
    assert color[0] == 0  # Red component
    assert color[1] > 0  # Green component (should have green)
    assert color[2] > 0  # Blue component (blue-green)


def test_temperature_to_color_comfort_zone():
    """Test comfort zone temperature."""
    # Middle of comfort zone
    color = temperature_to_color(23, 20, 26)
    assert color[1] == 255  # Green component should be max


def test_temperature_to_color_comfort_max():
    """Test comfort maximum temperature."""
    # At comfort maximum
    color = temperature_to_color(26, 20, 26)
    assert color[0] == 255  # Red component
    assert color[1] == 255  # Green component (yellow)
    assert color[2] == 0  # Blue component


def test_temperature_to_color_hot():
    """Test hot temperature color mapping."""
    # Very hot (above comfort max + transition)
    color = temperature_to_color(36, 20, 26)
    assert color[0] > 128  # Red component (should be reddish)
    assert color[1] == 0  # Green component
    assert color[2] == 0  # Blue component


def test_temperature_to_color_gradient_continuity():
    """Test that color gradient is continuous."""
    # Test a range of temperatures to ensure smooth transitions
    comfort_min = 20
    comfort_max = 26

    previous_color = None
    for temp in range(10, 40):
        color = temperature_to_color(temp, comfort_min, comfort_max)
        # Ensure all color components are valid
        assert 0 <= color[0] <= 255
        assert 0 <= color[1] <= 255
        assert 0 <= color[2] <= 255

        # Store for continuity check
        if previous_color:
            # Check that color doesn't jump too drastically
            # (allowing up to 128 change per degree in any component during transitions)
            r_diff = abs(color[0] - previous_color[0])
            g_diff = abs(color[1] - previous_color[1])
            b_diff = abs(color[2] - previous_color[2])
            assert max(r_diff, g_diff, b_diff) <= 128

        previous_color = color
