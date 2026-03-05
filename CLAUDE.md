# Temperature Map Integration - AI Agent Instructions

## Project Overview

This is a Home Assistant custom integration that generates temperature heatmap images using physics-based interpolation with flood-fill pathfinding around walls.

## Code Style

- Use Python 3.11+ features (type hints, dataclasses)
- Follow Home Assistant coding conventions
- Keep functions pure where possible (easier to test)
- Use `async`/`await` for HA APIs, `async_add_executor_job` for blocking code

## Testing Approach

Keep tests lightweight per user request. Focus on:
- Core algorithm correctness (geometry, distance, temperature interpolation)
- Skip integration tests with HA mocking unless necessary

Run tests with: `pytest tests/ -v`

## Quality Checks - REQUIRED BEFORE PUSHING

**CRITICAL**: Before committing and pushing ANY code changes, you MUST run the formatter, linter, and tests:

```bash
# 1. Format code (auto-fixes formatting issues)
ruff format .

# 2. Run linter (must pass with no errors)
ruff check custom_components/

# 3. Run tests (all tests must pass)
pytest tests/ -v
```

**DO NOT** commit or push code that:
- Has formatting issues (check with `ruff format --check .`)
- Has linter errors or warnings
- Has failing tests
- Has not been validated with all three checks

This ensures code quality and prevents breaking changes from being pushed to the repository.

## Important Constraints

1. **Don't block the event loop** - Image rendering must run in executor
2. **Match original output** - The heatmap should look identical to the TypeScript version
3. **Pillow for images** - Don't add numpy or other heavy dependencies unless necessary

## File Structure

```
custom_components/temperature_map/
├── __init__.py
├── manifest.json
├── config_flow.py
├── const.py
├── coordinator.py
├── image.py
├── services.yaml
├── heatmap/
│   ├── __init__.py
│   ├── types.py
│   ├── geometry.py
│   ├── distance.py
│   ├── temperature.py
│   └── renderer.py
└── www/
    └── temperature-map-overlay.js

tests/
├── __init__.py
├── conftest.py
├── test_geometry.py
├── test_distance.py
├── test_temperature.py
├── test_config_flow.py
├── test_options_flow.py
└── test_coordinator.py
```
