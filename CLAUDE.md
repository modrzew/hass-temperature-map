# Temperature Map Integration - AI Agent Instructions

## Project Overview

This is a Home Assistant custom integration that generates temperature heatmap images. It ports an existing TypeScript Lovelace card to a Python backend integration for better performance.

## Key Files

- `PLAN.md` - Detailed action plan with all tasks
- `HA_INTEGRATION_GUIDE.md` - How to write Home Assistant integration code
- `lovelace-temperature-map/` - Git submodule with original TypeScript source to port

## Before Starting

1. **Read the plan first**: Start with `PLAN.md` to understand the full scope
2. **Check the submodule**: If `lovelace-temperature-map/` is empty, run:
   ```bash
   git submodule update --init --recursive
   ```
3. **Read source files**: The TypeScript files to port are in `lovelace-temperature-map/src/lib/temperature-map/`

## Code Style

- Use Python 3.11+ features (type hints, dataclasses)
- Follow Home Assistant coding conventions (see `HA_INTEGRATION_GUIDE.md`)
- Keep functions pure where possible (easier to test)
- Use `async`/`await` for HA APIs, `async_add_executor_job` for blocking code

## Testing Approach

Keep tests lightweight per user request. Focus on:
- Core algorithm correctness (geometry, distance, temperature interpolation)
- Skip integration tests with HA mocking unless necessary

Run tests with: `pytest tests/ -v`

## Quality Checks - REQUIRED BEFORE PUSHING

**CRITICAL**: Before committing and pushing ANY code changes, you MUST run both the linter and tests:

```bash
# 1. Run linter (must pass with no errors)
ruff check custom_components/

# 2. Run tests (all tests must pass)
pytest tests/ -v
```

**DO NOT** commit or push code that:
- Has linter errors or warnings
- Has failing tests
- Has not been validated with both checks

This ensures code quality and prevents breaking changes from being pushed to the repository.

## Important Constraints

1. **Don't block the event loop** - Image rendering must run in executor
2. **Match original output** - The heatmap should look identical to the TypeScript version
3. **YAML config only** - No config flow UI for now
4. **Pillow for images** - Don't add numpy or other heavy dependencies unless necessary

## File Structure to Create

```
custom_components/temperature_map/
├── __init__.py
├── manifest.json
├── const.py
├── coordinator.py
├── image.py
└── heatmap/
    ├── __init__.py
    ├── types.py
    ├── geometry.py
    ├── distance.py
    ├── temperature.py
    └── renderer.py

www/
└── temperature-map-overlay.js

tests/
├── __init__.py
├── test_geometry.py
├── test_distance.py
└── test_temperature.py
```

## Algorithm Porting Reference

When porting from TypeScript:

| TypeScript | Python |
|------------|--------|
| `interface Foo {}` | `@dataclass class Foo:` |
| `const x: number` | `x: float` or `x: int` |
| `Array<T>` | `list[T]` |
| `Set<string>` | `set[str]` |
| `Map<K,V>` | `dict[K,V]` |
| `Infinity` | `float('inf')` |
| `Math.sqrt(x)` | `math.sqrt(x)` |
| `arr.push(x)` | `arr.append(x)` |
| `arr.shift()` | `arr.pop(0)` or use `collections.deque` |
| `arr.map(fn)` | `[fn(x) for x in arr]` |
| `arr.filter(fn)` | `[x for x in arr if fn(x)]` |
| `arr.reduce(fn, init)` | `functools.reduce(fn, arr, init)` |

## Quick Reference: Source Files

**Types** (`lovelace-temperature-map/src/lib/temperature-map/types.ts`):
- `Wall` - {x1, y1, x2, y2}
- `TemperatureSensor` - {entity, x, y, label?}
- `DistanceGrid` - {distances[sensor][y][x], width, height}
- `Point` - {x, y}

**Geometry** (`geometry.ts`):
- `lineIntersection(x1,y1,x2,y2, x3,y3,x4,y4)` → Point | null
- `lineIntersectsWalls(x1,y1,x2,y2, walls)` → boolean
- `checkWallProximity(x,y, walls, radius)` → boolean

**Distance** (`distance.ts`):
- `floodFillDistances(sensorX, sensorY, walls, gridW, gridH, scale)` → number[][]
- `computeDistanceGridAsync(...)` - async with progress callback
- `getInterpolatedDistance(x, y, sensorIdx, grid)` → number
- `isPointInsideBoundary(x, y, walls, w, h, sensors)` → boolean

**Temperature** (`temperature.ts`):
- `temperatureToColor(temp, comfortMin, comfortMax)` → "rgb(r,g,b)"
- `interpolateTemperaturePhysics(x, y, sensors, distanceGrid, ambientTemp)` → number
- `interpolateTemperaturePhysicsWithCircularBlending(...)` → number
