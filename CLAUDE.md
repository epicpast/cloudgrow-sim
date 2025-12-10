# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

cloudgrow-sim is an ASHRAE-compliant greenhouse climate simulation framework. Python 3.14+ with strict typing (mypy strict mode). Uses Pydantic v2 for validation, NumPy for calculations.

## Commands

```bash
uv sync                     # Install dependencies
make quality                # Run ALL checks (format, lint, typecheck, security, tests)
make test                   # Run tests only
uv run pytest tests/test_physics/test_psychrometrics.py -v           # Single test file
uv run pytest tests/test_physics/test_psychrometrics.py::TestSaturationPressure -v  # Single class
uv run pytest -k "test_solar_position" -v                            # Pattern match

# Individual checks
make lint                   # ruff check
make typecheck              # mypy
make format                 # auto-fix formatting
```

## Architecture

### Module Hierarchy

```
core/           → Foundation: base classes, state, events, registry, config
physics/        → ASHRAE calculations: psychrometrics, solar, heat_transfer, ventilation
components/     → Plugin-based: sensors/, actuators/, modifiers/
controllers/    → Control algorithms: pid, staged, hysteresis, schedule
simulation/     → Engine: weather sources, simulation loop, scenarios
```

### Key Design Patterns

**Component System**: All sensors/actuators/controllers inherit from `Component` ABC in `core/base.py`. Each must implement `update(dt, state) -> None`. Components are registered via `@register_component("category", "type")` decorator from `core/registry.py`.

**State Flow**: `GreenhouseState` (in `core/state.py`) contains `AirState` for interior/exterior, plus geometry, covering, location, weather. Passed to all components during simulation step.

**Event System**: `EventBus` singleton in `core/events.py` with pub/sub pattern. Event types use dot-notation: `EventType.SIMULATION_START` = `"simulation.start"`.

**Simulation Loop** (in `simulation/engine.py`):
1. Update exterior from weather source
2. Read all sensors
3. Execute all controllers
4. Apply actuator effects
5. Calculate physics (solar gain, conduction, ventilation)
6. Update interior state
7. Emit telemetry events

### Physics Module (ASHRAE Standards)

- `psychrometrics.py`: Hyland-Wexler saturation, humidity ratio, wet-bulb (bisection), dew point, enthalpy, density
- `solar.py`: Solar position returns `SolarPosition` NamedTuple (5 fields: altitude, azimuth, zenith, declination, hour_angle)
- `heat_transfer.py`: Berdahl-Fromberg sky temp uses **dew point in °C** (not Kelvin)
- `ventilation.py`: Stack/wind effects, infiltration with construction_quality parameter

### Naming Conventions

- `Location.timezone_str` (not `timezone`)
- `COVERING_MATERIALS["polycarbonate_twin"]` (not `double_polycarbonate`)
- `CoveringConfig.to_covering()` (not `to_covering_properties()`)
- `emit_sensor_reading(sensor_name, readings_dict)` — second arg is dict, not **kwargs

## Code Style

- Type hints required on all functions
- `del unused_arg` pattern for intentionally unused parameters (ARG002)
- Use `.values()` instead of `.items()` when key not needed (B007)
- No `assert` in production code — use explicit ValueError instead (S101)
- Ruff line length 88, mypy strict mode
- 80% test coverage minimum enforced

## Testing

- CoolProp cross-validation for physics: `@pytest.mark.skipif(not COOLPROP_AVAILABLE)`
- Use `reset_event_bus()` / `reset_registry()` in test `setup_method()` for isolation
- Test physics relationships (e.g., "summer altitude > winter altitude") rather than absolute values when timezone handling is complex
- Use 1-2% relative error tolerance for ASHRAE formula validation
