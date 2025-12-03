"""Pytest configuration."""

import sys
from pathlib import Path

# Add the custom_components/temperature_map directory to sys.path
# so we can import heatmap modules directly without triggering __init__.py
heatmap_path = Path(__file__).parent.parent / "custom_components" / "temperature_map"
sys.path.insert(0, str(heatmap_path))
