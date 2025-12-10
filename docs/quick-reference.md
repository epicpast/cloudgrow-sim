# cloudgrow-sim Quick Reference

## Installation

```bash
git clone https://github.com/OWNER/cloudgrow-sim.git && cd cloudgrow-sim && uv sync
```

## Minimal Example

```python
from cloudgrow_sim.simulation import create_basic_scenario

engine = create_basic_scenario(duration_hours=24.0)
stats = engine.run()
print(f"Final temp: {engine.state.interior.temperature:.1f}°C")
```

## Components at a Glance

### Sensors

| Class | Location | Key Parameters |
|-------|----------|----------------|
| `TemperatureSensor` | interior/exterior | `noise_std_dev` |
| `HumiditySensor` | interior/exterior | `noise_std_dev` |
| `CombinedTempHumiditySensor` | interior/exterior | `temp_noise_std_dev`, `humidity_noise_std_dev` |
| `CO2Sensor` | interior | `noise_std_dev` |
| `SolarRadiationSensor` | exterior | `noise_std_dev` |
| `PARSensor` | interior | `transmittance` |
| `WindSensor` | exterior | `speed_noise_std_dev`, `direction_noise_std_dev` |

### Actuators

| Class | Effect | Key Parameters |
|-------|--------|----------------|
| `ExhaustFan` | Ventilation (out) | `max_flow_rate` (m³/s), `power_consumption` (W) |
| `IntakeFan` | Ventilation (in) | `max_flow_rate`, `power_consumption` |
| `CirculationFan` | Air mixing | `power_consumption` |
| `RoofVent` | Natural ventilation | `width`, `height`, `height_above_floor` |
| `SideVent` | Natural ventilation | `width`, `height`, `height_above_floor` |
| `ShadeCurtain` | Solar reduction | `shade_factor` (0-1) |
| `ThermalCurtain` | Heat retention | `r_value` (m²K/W) |
| `UnitHeater` | Heat addition | `heating_capacity` (W), `efficiency` |
| `RadiantHeater` | Heat addition | `heating_capacity`, `radiant_fraction` |
| `EvaporativePad` | Cooling + humidity | `pad_area` (m²), `saturation_efficiency` |
| `Fogger` | Cooling + humidity | `flow_rate` (L/h), `droplet_size` (μm) |

### Controllers

| Class | Use Case | Key Parameters |
|-------|----------|----------------|
| `PIDController` | Continuous modulation | `kp`, `ki`, `kd`, `setpoint`, `output_limits` |
| `StagedController` | Multi-stage equipment | `stages=[(threshold, output), ...]`, `hysteresis` |
| `HysteresisController` | On/off with deadband | `setpoint`, `hysteresis`, `reverse_acting` |
| `ScheduleController` | Time-based setpoints | `interpolate`, then `add_entry(time, value)` |

### Modifiers

| Class | Effect | Key Parameters |
|-------|--------|----------------|
| `CoveringMaterial` | Optical/thermal | `material` or custom transmittance/U-value |
| `ThermalMass` | Heat storage | `mass` (kg), `specific_heat`, `surface_area` |

## Covering Materials

```python
from cloudgrow_sim.core.state import COVERING_MATERIALS

# Available keys:
# single_glass, double_glass, single_polyethylene, double_polyethylene,
# polycarbonate_twin, polycarbonate_triple, acrylic_double
```

## Weather Sources

```python
# Synthetic (mathematical patterns)
from cloudgrow_sim.simulation import SyntheticWeatherSource, SyntheticWeatherConfig
weather = SyntheticWeatherSource(SyntheticWeatherConfig(temp_mean=20.0))

# CSV (historical data)
from cloudgrow_sim.simulation import CSVWeatherSource
weather = CSVWeatherSource("weather.csv")
```

## Simulation Config

```python
SimulationConfig(
    time_step=60.0,           # seconds
    start_time=datetime(...),
    end_time=datetime(...),   # or None
    emit_events=True,
    emit_interval=1,          # emit every N steps
)
```

## Run Simulation

```python
engine = SimulationEngine(state, weather, config)
engine.add_sensor(...)
engine.add_actuator(...)
engine.add_controller(...)

# Option 1: Run to completion
stats = engine.run()

# Option 2: Run N steps
stats = engine.run(steps=100)

# Option 3: Manual stepping
while engine.step():
    print(engine.state.interior.temperature)
```

## Pre-built Scenarios

```python
from cloudgrow_sim.simulation import (
    create_basic_scenario,          # Small hobby greenhouse
    create_full_climate_scenario,   # Commercial with full HVAC
    create_winter_heating_scenario, # Cold weather test
    create_summer_cooling_scenario, # Hot weather test
)
```

## Physics Functions

```python
from cloudgrow_sim.physics.psychrometrics import (
    saturation_pressure,    # Pa
    humidity_ratio,         # kg_w/kg_da
    wet_bulb_temperature,   # °C
    dew_point,              # °C
    enthalpy,               # kJ/kg_da
    air_density,            # kg/m³
)

from cloudgrow_sim.physics.solar import (
    solar_position,         # SolarPosition namedtuple
    par_from_solar,         # µmol/m²/s
)

from cloudgrow_sim.physics.heat_transfer import (
    conduction_heat_transfer,  # W
    sky_temperature,           # °C
)
```

## Event Types

```python
from cloudgrow_sim.core.events import EventType, get_event_bus

bus = get_event_bus()
bus.subscribe(EventType.STATE_UPDATE, lambda e: print(e.data))

# EventType.SIMULATION_START, SIMULATION_STOP, SIMULATION_ERROR
# EventType.STATE_UPDATE, SENSOR_READING, ACTUATOR_COMMAND
# EventType.CONTROLLER_OUTPUT, ALARM
```

## State Access

```python
engine.state.interior.temperature  # °C
engine.state.interior.humidity     # %
engine.state.interior.co2_ppm      # ppm
engine.state.exterior.temperature  # °C
engine.state.solar_radiation       # W/m²
engine.state.wind_speed            # m/s
engine.state.geometry.volume       # m³
engine.state.geometry.floor_area   # m²
engine.current_time                # datetime
engine.status                      # SimulationStatus enum
```

## Quality Checks

```bash
make quality    # All checks
make test       # Tests only
make lint       # Ruff
make typecheck  # mypy
```
