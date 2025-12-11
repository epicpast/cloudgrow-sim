# cloudgrow-sim User Guide

A production-grade greenhouse climate simulation framework following ASHRAE standards.

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Running from Command Line](#running-from-command-line)
4. [Core Concepts](#core-concepts)
5. [Components Reference](#components-reference)
6. [Controllers Reference](#controllers-reference)
7. [Weather Sources](#weather-sources)
8. [Running Simulations](#running-simulations)
9. [Pre-built Scenarios](#pre-built-scenarios)
10. [Physics Reference](#physics-reference)
11. [Examples](#examples)

---

## Installation

### Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager (recommended)

### Install from Source

```bash
git clone https://github.com/OWNER/cloudgrow-sim.git
cd cloudgrow-sim
uv sync
```

### Verify Installation

```bash
uv run python -c "from cloudgrow_sim import __version__; print(__version__)"
```

---

## Quick Start

### Run a Pre-built Scenario

```python
from cloudgrow_sim.simulation import create_basic_scenario

# Create a 24-hour simulation of a small hobby greenhouse
engine = create_basic_scenario(duration_hours=24.0, time_step=60.0)

# Run the simulation
stats = engine.run()

print(f"Completed {stats.steps_completed} steps")
print(f"Final temperature: {engine.state.interior.temperature:.1f}°C")
```

### Build a Custom Simulation

```python
from datetime import UTC, datetime, timedelta

from cloudgrow_sim.core.state import (
    AirState,
    COVERING_MATERIALS,
    GeometryType,
    GreenhouseGeometry,
    GreenhouseState,
    Location,
)
from cloudgrow_sim.components import (
    TemperatureSensor,
    ExhaustFan,
)
from cloudgrow_sim.controllers import PIDController
from cloudgrow_sim.simulation import (
    SimulationConfig,
    SimulationEngine,
    SyntheticWeatherSource,
)

# 1. Define the greenhouse
state = GreenhouseState(
    interior=AirState(temperature=22.0, humidity=60.0, co2_ppm=400.0),
    exterior=AirState(temperature=18.0, humidity=50.0, co2_ppm=400.0),
    time=datetime(2025, 6, 21, 6, 0, tzinfo=UTC),
    location=Location(
        latitude=37.3,
        longitude=-78.4,
        elevation=130.0,
        timezone_str="America/New_York",
    ),
    geometry=GreenhouseGeometry(
        geometry_type=GeometryType.GABLE,
        length=30.0,
        width=10.0,
        height_eave=3.0,
        height_ridge=5.0,
        orientation=0.0,
    ),
    covering=COVERING_MATERIALS["double_polyethylene"],
)

# 2. Configure simulation
config = SimulationConfig(
    time_step=60.0,  # seconds
    start_time=state.time,
    end_time=state.time + timedelta(hours=24),
)

# 3. Create engine with weather
weather = SyntheticWeatherSource()
engine = SimulationEngine(state, weather, config)

# 4. Add components
engine.add_sensor(TemperatureSensor("temp_interior", location="interior"))
engine.add_actuator(ExhaustFan("main_fan", max_flow_rate=5.0, power_consumption=500.0))
engine.add_controller(PIDController(
    "temp_control",
    kp=0.5,
    ki=0.1,
    kd=0.05,
    setpoint=24.0,
    output_limits=(0.0, 1.0),
))

# 5. Run
stats = engine.run()
```

---

## Running from Command Line

The `cgsim` CLI provides a code-free way to run simulations using YAML configuration files.

### Verify Installation

```bash
cgsim --version
```

### Run a Built-in Scenario

```bash
# List available scenarios
cgsim list

# Run the basic scenario
cgsim run --scenario basic

# Run full climate control scenario
cgsim run --scenario full-climate
```

### Run Your Own Configuration

```bash
# Run a YAML configuration file
cgsim run my-greenhouse.yaml

# Validate a config without running
cgsim validate my-greenhouse.yaml
```

### Generate a Starter Configuration

```bash
# Create a new config file
cgsim init "My Greenhouse" -o my-greenhouse.yaml

# The generated file includes sensible defaults and comments
```

### Override Simulation Parameters

```bash
# Override duration (in hours)
cgsim run config.yaml --duration 48

# Override time step (in seconds)
cgsim run config.yaml --time-step 30

# Combine multiple overrides
cgsim run config.yaml -d 24 -t 30
```

### Output Options

```bash
# Save results to a directory
cgsim run config.yaml --output-dir ./results

# Choose output format
cgsim run config.yaml --format json --output-dir ./results
cgsim run config.yaml --format csv --output-dir ./results

# Available formats: console (default), json, csv
```

### Quiet Mode

```bash
# Suppress progress output (useful for scripts)
cgsim run config.yaml --quiet

# Combine with output for batch processing
cgsim run config.yaml -q -f json -o ./results
```

### Common CLI Errors

**Config file not found:**
```
Error: Config file 'missing.yaml' not found
```
Solution: Check the file path and ensure the YAML file exists.

**Invalid configuration:**
```
Error: Invalid: Field 'latitude' must be between -90 and 90
```
Solution: Run `cgsim validate config.yaml` to see detailed validation errors.

**Cannot specify both config and scenario:**
```
Error: Cannot specify both a config file and --scenario
```
Solution: Use either a config file OR the --scenario flag, not both.

---

## Core Concepts

### GreenhouseState

The central data structure representing the complete state of the simulation:

```python
@dataclass
class GreenhouseState:
    interior: AirState      # Indoor conditions
    exterior: AirState      # Outdoor conditions
    time: datetime          # Current simulation time
    location: Location      # Geographic coordinates
    geometry: GreenhouseGeometry
    covering: CoveringProperties
    solar_radiation: float  # W/m² (exterior)
    wind_speed: float       # m/s
    wind_direction: float   # degrees from North
```

### AirState

Thermodynamic properties of an air mass:

| Property | Type | Unit | Valid Range |
|----------|------|------|-------------|
| `temperature` | float | °C | -50 to 60 |
| `humidity` | float | % RH | 0 to 100 |
| `pressure` | float | Pa | 80,000 to 120,000 |
| `co2_ppm` | float | ppm | 0 to 5,000 |

### Location

Geographic coordinates for solar calculations:

```python
Location(
    latitude=37.3,       # degrees, positive = North
    longitude=-78.4,     # degrees, positive = East
    elevation=130.0,     # meters above sea level
    timezone_str="America/New_York",
)
```

### GreenhouseGeometry

Physical dimensions:

| Property | Type | Unit | Description |
|----------|------|------|-------------|
| `geometry_type` | GeometryType | - | GABLE, QUONSET, GOTHIC, VENLO, HIGH_TUNNEL, CUSTOM |
| `length` | float | m | North-South dimension |
| `width` | float | m | East-West dimension |
| `height_eave` | float | m | Sidewall height |
| `height_ridge` | float | m | Peak height (must be > eave) |
| `orientation` | float | degrees | Rotation from North |

Calculated properties: `floor_area`, `volume`, `wall_area`, `roof_area`, `total_surface_area`

### Covering Materials

Pre-defined materials available via `COVERING_MATERIALS`:

| Key | Solar Trans. | U-Value (W/m²K) |
|-----|--------------|-----------------|
| `single_glass` | 0.85 | 5.8 |
| `double_glass` | 0.75 | 3.0 |
| `single_polyethylene` | 0.87 | 6.0 |
| `double_polyethylene` | 0.77 | 4.0 |
| `polycarbonate_twin` | 0.78 | 3.5 |
| `polycarbonate_triple` | 0.71 | 2.5 |
| `acrylic_double` | 0.83 | 3.2 |

---

## Components Reference

All components inherit from a base `Component` class and must implement `update(dt, state)`.

### Sensors

Sensors read values from the greenhouse state with optional measurement noise.

#### TemperatureSensor

```python
TemperatureSensor(
    name="temp_int",
    location="interior",      # "interior" or "exterior"
    noise_std_dev=0.1,        # Gaussian noise (°C)
)
```

#### HumiditySensor

```python
HumiditySensor(
    name="rh_int",
    location="interior",
    noise_std_dev=2.0,        # Gaussian noise (%)
)
```

#### CombinedTempHumiditySensor

Simulates DHT22-style sensors:

```python
CombinedTempHumiditySensor(
    name="dht_interior",
    location="interior",
    temp_noise_std_dev=0.2,
    humidity_noise_std_dev=2.0,
)
```

#### CO2Sensor

```python
CO2Sensor(
    name="co2_sensor",
    location="interior",
    noise_std_dev=10.0,       # ppm
)
```

#### SolarRadiationSensor

Pyranometer simulation:

```python
SolarRadiationSensor(
    name="pyranometer",
    location="exterior",      # typically exterior
    noise_std_dev=5.0,        # W/m²
)
```

#### PARSensor

Photosynthetically Active Radiation (400-700nm):

```python
PARSensor(
    name="par_sensor",
    location="interior",
    transmittance=0.75,       # covering transmittance for PAR
)
```

#### WindSensor

```python
WindSensor(
    name="anemometer",
    speed_noise_std_dev=0.2,  # m/s
    direction_noise_std_dev=5.0,  # degrees
)
```

### Actuators

Actuators modify the greenhouse climate. Set output via `set_output(value)` where value is typically 0.0-1.0.

#### Fans

```python
# Exhaust fan - removes air from greenhouse
ExhaustFan(
    name="exhaust_1",
    max_flow_rate=5.0,        # m³/s at full speed
    power_consumption=500.0,  # Watts at full speed
)

# Intake fan - brings outside air in
IntakeFan(
    name="intake_1",
    max_flow_rate=3.0,
    power_consumption=300.0,
)

# Circulation fan - internal air movement
CirculationFan(
    name="circ_fan",
    power_consumption=100.0,
)
```

Fan power follows cubic law: `power = max_power * output³`

#### Vents

Natural ventilation through openings:

```python
RoofVent(
    name="roof_vent_1",
    width=2.0,                # m
    height=0.5,               # m (maximum opening)
    height_above_floor=4.5,   # m (for stack effect)
    discharge_coefficient=0.6,
)

SideVent(
    name="side_vent_1",
    width=3.0,
    height=1.0,
    height_above_floor=1.5,
)
```

#### Curtains

```python
# Shade curtain - reduces solar radiation
ShadeCurtain(
    name="shade_ns",
    shade_factor=0.5,         # fraction of solar blocked when closed
)

# Thermal curtain - reduces heat loss
ThermalCurtain(
    name="thermal_curtain",
    r_value=1.5,              # m²K/W thermal resistance
)
```

#### Heating

```python
# Forced-air unit heater
UnitHeater(
    name="heater_1",
    heating_capacity=15000.0, # Watts
    efficiency=0.90,          # combustion efficiency
)

# Radiant heater (split between radiant and convective)
RadiantHeater(
    name="radiant_1",
    heating_capacity=10000.0,
    radiant_fraction=0.7,     # 70% radiant, 30% convective
)
```

#### Cooling

```python
# Evaporative cooling pad
EvaporativePad(
    name="evap_pad",
    pad_area=6.0,             # m²
    saturation_efficiency=0.85,
)

# Fog system
Fogger(
    name="fogger",
    flow_rate=5.0,            # L/h water
    droplet_size=10.0,        # microns
)
```

### Climate Modifiers

Passive elements affecting climate without active control.

#### CoveringMaterial

```python
CoveringMaterial(
    name="covering",
    material="double_polyethylene",  # key from COVERING_MATERIALS
)
# Or custom properties:
CoveringMaterial(
    name="custom_covering",
    transmittance_solar=0.80,
    transmittance_par=0.78,
    u_value=3.5,
)
```

#### ThermalMass

Simulates heat storage (concrete floors, water barrels):

```python
ThermalMass(
    name="water_barrels",
    mass=2000.0,              # kg (e.g., 10 × 200L barrels)
    specific_heat=4186.0,     # J/(kg·K) for water
    surface_area=15.0,        # m² exposed surface
    initial_temperature=20.0, # °C
)
```

---

## Controllers Reference

Controllers compute output signals based on process variables and setpoints.

### PIDController

Full-featured PID with anti-windup, derivative filtering:

```python
PIDController(
    name="temp_pid",
    kp=0.5,                   # Proportional gain
    ki=0.1,                   # Integral gain
    kd=0.05,                  # Derivative gain
    setpoint=24.0,            # Target value
    output_limits=(0.0, 1.0), # Output range
    anti_windup=True,         # Integral clamping
    derivative_filter=0.1,    # Filter time constant (s)
    reverse_acting=False,     # True if output increases when PV > SP
)
```

**Methods:**
- `compute(setpoint, process_value, dt)` → output value
- `reset()` → clear integral and derivative state
- `set_integral(value)` → manually set integral term

### StagedController

Multi-stage on/off control for equipment staging:

```python
StagedController(
    name="fan_staging",
    stages=[
        (26.0, 0.33),  # (threshold, output) - Stage 1 at 26°C
        (28.0, 0.66),  # Stage 2 at 28°C
        (30.0, 1.00),  # Stage 3 at 30°C
    ],
    hysteresis=0.5,           # Deadband to prevent chattering
)
```

### HysteresisController

Simple on/off control with deadband:

```python
HysteresisController(
    name="heater_control",
    setpoint=18.0,            # Target temperature
    hysteresis=2.0,           # Deadband width
    reverse_acting=False,     # False = heating mode, True = cooling
    on_output=1.0,            # Output when ON
    off_output=0.0,           # Output when OFF
)
```

**Heating mode (reverse_acting=False):**
- Turns ON when PV < (setpoint - hysteresis/2)
- Turns OFF when PV > (setpoint + hysteresis/2)

**Cooling mode (reverse_acting=True):**
- Turns ON when PV > (setpoint + hysteresis/2)
- Turns OFF when PV < (setpoint - hysteresis/2)

### ScheduleController

Time-based setpoint scheduling:

```python
ScheduleController(
    name="temp_schedule",
    interpolate=True,         # Smooth transitions between setpoints
    mode="setpoint",          # "setpoint" or "direct"
)

# Add schedule entries
controller.add_entry(time(6, 0), 18.0)   # 6:00 AM → 18°C
controller.add_entry(time(8, 0), 24.0)   # 8:00 AM → 24°C
controller.add_entry(time(18, 0), 22.0)  # 6:00 PM → 22°C
controller.add_entry(time(22, 0), 16.0)  # 10:00 PM → 16°C
```

---

## Weather Sources

Weather sources provide exterior conditions to the simulation.

### SyntheticWeatherSource

Generates realistic weather patterns mathematically:

```python
from cloudgrow_sim.simulation import SyntheticWeatherConfig, SyntheticWeatherSource

config = SyntheticWeatherConfig(
    latitude=37.0,
    temp_mean=20.0,           # Annual mean temperature (°C)
    temp_amplitude_annual=12.0,  # Annual variation (°C)
    temp_amplitude_daily=8.0,    # Daily variation (°C)
    humidity_mean=60.0,       # Mean RH (%)
    humidity_amplitude=20.0,  # Daily humidity variation
    solar_max=1000.0,         # Peak solar radiation (W/m²)
    wind_mean=2.5,            # Mean wind speed (m/s)
    wind_std=1.5,             # Wind speed std dev
    cloud_cover_mean=0.3,     # Mean cloud cover (0-1)
)

weather = SyntheticWeatherSource(config)
```

**Generated patterns:**
- **Temperature**: Annual cycle (coldest day ~15, warmest ~196) + daily cycle (coldest 6am, warmest 3pm)
- **Solar**: Bell curve during daylight hours, reduced by cloud cover
- **Humidity**: Inverse relationship with temperature
- **Wind**: Slight diurnal pattern with random variation

### CSVWeatherSource

Load historical weather data from CSV files:

```python
from cloudgrow_sim.simulation import CSVWeatherSource, CSVWeatherMapping

# Default column mapping
weather = CSVWeatherSource("weather_data.csv")

# Custom column mapping
mapping = CSVWeatherMapping(
    timestamp="datetime",
    temperature="temp_c",
    humidity="rh_percent",
    solar_radiation="ghi",
    wind_speed="wind_ms",
)
weather = CSVWeatherSource(
    "weather_data.csv",
    mapping=mapping,
    timestamp_format="%Y-%m-%d %H:%M:%S",
)
```

**CSV format example:**
```csv
timestamp,temperature,humidity,solar_radiation,wind_speed
2025-06-21 00:00:00,15.0,70.0,0.0,2.0
2025-06-21 01:00:00,14.5,72.0,0.0,1.8
...
```

Interpolates between data points for smooth transitions.

---

## Running Simulations

### SimulationConfig

```python
SimulationConfig(
    time_step=60.0,           # Seconds per simulation step
    start_time=datetime(...), # Simulation start
    end_time=datetime(...),   # Simulation end (None = indefinite)
    real_time_factor=0.0,     # 0 = fast as possible, 1.0 = real-time
    emit_events=True,         # Emit to EventBus
    emit_interval=1,          # Emit every N steps
)
```

### SimulationEngine

```python
engine = SimulationEngine(state, weather, config)

# Add components
engine.add_sensor(sensor)
engine.add_actuator(actuator)
engine.add_controller(controller)
engine.add_modifier(modifier)

# Run options:

# 1. Run for N steps
stats = engine.run(steps=100)

# 2. Run until end_time
stats = engine.run()

# 3. Step manually
while engine.step():
    print(f"T={engine.state.interior.temperature:.1f}°C")
    if some_condition:
        break

# Reset and run again
engine.reset()
stats = engine.run()
```

### SimulationStats

Returned from `engine.run()`:

```python
stats.steps_completed    # Number of steps executed
stats.simulation_time    # Total simulated time (timedelta)
stats.wall_time          # Actual elapsed time (timedelta)
stats.avg_step_time      # Average ms per step
```

### Event System

Subscribe to simulation events:

```python
from cloudgrow_sim.core.events import EventType, get_event_bus

bus = get_event_bus()

def on_state_update(event):
    print(f"Interior temp: {event.data['interior_temperature']:.1f}°C")

bus.subscribe(EventType.STATE_UPDATE, on_state_update)

# Available event types:
# EventType.SIMULATION_START
# EventType.SIMULATION_STOP
# EventType.SIMULATION_ERROR
# EventType.STATE_UPDATE
# EventType.SENSOR_READING
# EventType.ACTUATOR_COMMAND
# EventType.CONTROLLER_OUTPUT
# EventType.ALARM
```

---

## Pre-built Scenarios

Ready-to-run simulation configurations:

### create_basic_scenario

Simple hobby greenhouse with minimal components:

```python
from cloudgrow_sim.simulation import create_basic_scenario

engine = create_basic_scenario(
    duration_hours=24.0,
    time_step=60.0,
)
```

**Includes:** Temperature sensor, exhaust fan, hysteresis controller

### create_full_climate_scenario

Commercial greenhouse with complete climate control:

```python
from cloudgrow_sim.simulation import create_full_climate_scenario

engine = create_full_climate_scenario(
    duration_hours=24.0,
    time_step=60.0,
)
```

**Includes:**
- Sensors: Combined temp/humidity, PAR, solar radiation, exterior temp
- Actuators: 3 exhaust fans, circulation fan, evap pad, unit heater, 2 roof vents
- Controllers: Cooling PID, heating hysteresis, fan staging
- Modifiers: Covering material, thermal mass (water barrels)

### create_winter_heating_scenario

Cold weather stress test:

```python
from cloudgrow_sim.simulation import create_winter_heating_scenario

engine = create_winter_heating_scenario(duration_hours=48.0)
```

**Conditions:** -5°C exterior, low solar, high wind, 25kW main heater + 15kW backup

### create_summer_cooling_scenario

Hot weather stress test:

```python
from cloudgrow_sim.simulation import create_summer_cooling_scenario

engine = create_summer_cooling_scenario(duration_hours=48.0)
```

**Conditions:** 35°C+ exterior, high solar (Phoenix, AZ), 4 exhaust fans + evaporative cooling

---

## Physics Reference

All physics calculations follow ASHRAE Handbook—Fundamentals.

### Psychrometrics (Chapter 1)

```python
from cloudgrow_sim.physics.psychrometrics import (
    saturation_pressure,      # Pa from T (Hyland-Wexler)
    humidity_ratio,           # kg_w/kg_da from T, RH
    wet_bulb_temperature,     # °C from T, RH (iterative)
    dew_point,                # °C from T, RH
    enthalpy,                 # kJ/kg_da from T, W
    air_density,              # kg/m³ from T, W, P
    relative_humidity,        # % from T, W
)
```

### Solar Radiation (Chapter 14)

```python
from cloudgrow_sim.physics.solar import (
    solar_position,           # SolarPosition(altitude, azimuth, zenith, ...)
    extraterrestrial_radiation,  # W/m² corrected for Earth-Sun distance
    direct_normal_irradiance, # W/m² with atmospheric transmittance
    diffuse_radiation,        # W/m² (Erbs correlation)
    par_from_solar,           # µmol/m²/s from W/m²
)
```

### Heat Transfer (Chapters 4, 25, 26)

```python
from cloudgrow_sim.physics.heat_transfer import (
    conduction_heat_transfer, # W from U, A, dT
    convection_coefficient_natural,  # W/(m²K)
    convection_coefficient_forced,   # W/(m²K)
    sky_temperature,          # °C (Berdahl-Fromberg)
    ground_temperature,       # °C at depth
)
```

### Ventilation (Chapter 26)

```python
from cloudgrow_sim.physics.ventilation import (
    infiltration_ach_greenhouse,  # ACH from construction quality
    stack_flow_rate,          # m³/s from temperature difference
    wind_driven_flow_rate,    # m³/s from wind speed
    natural_ventilation_rate, # m³/s combined stack + wind
)
```

---

## Examples

### Temperature Control with PID

```python
from datetime import UTC, datetime, timedelta
from cloudgrow_sim.core.state import *
from cloudgrow_sim.components import TemperatureSensor, ExhaustFan
from cloudgrow_sim.controllers import PIDController
from cloudgrow_sim.simulation import *

# Create greenhouse
state = GreenhouseState(
    interior=AirState(temperature=28.0, humidity=60.0),
    exterior=AirState(temperature=20.0, humidity=50.0),
    time=datetime(2025, 6, 21, 12, 0, tzinfo=UTC),
    location=Location(latitude=37.3, longitude=-78.4, elevation=130.0, timezone_str="UTC"),
    geometry=GreenhouseGeometry(
        geometry_type=GeometryType.GABLE,
        length=30.0, width=10.0, height_eave=3.0, height_ridge=5.0,
    ),
    covering=COVERING_MATERIALS["double_polyethylene"],
)

# Create simulation
config = SimulationConfig(
    time_step=60.0,
    start_time=state.time,
    end_time=state.time + timedelta(hours=4),
    emit_events=False,
)
engine = SimulationEngine(state, SyntheticWeatherSource(), config)

# Add components
engine.add_sensor(TemperatureSensor("temp", location="interior"))
engine.add_actuator(ExhaustFan("fan", max_flow_rate=5.0, power_consumption=500.0))
engine.add_controller(PIDController(
    "pid", kp=0.3, ki=0.05, kd=0.02,
    setpoint=24.0, output_limits=(0.0, 1.0), reverse_acting=True,
))

# Run and collect data
temps = []
while engine.step():
    temps.append(engine.state.interior.temperature)

print(f"Initial: {temps[0]:.1f}°C → Final: {temps[-1]:.1f}°C")
```

### Multi-Stage Fan Control

```python
from cloudgrow_sim.components import ExhaustFan
from cloudgrow_sim.controllers import StagedController

# Add three fans
for i in range(3):
    engine.add_actuator(ExhaustFan(
        f"exhaust_{i+1}",
        max_flow_rate=2.0,
        power_consumption=500.0,
    ))

# Staged controller activates fans progressively
engine.add_controller(StagedController(
    "fan_staging",
    stages=[
        (26.0, 0.33),  # 1 fan at 26°C
        (28.0, 0.66),  # 2 fans at 28°C
        (30.0, 1.00),  # 3 fans at 30°C
    ],
    hysteresis=1.0,
))
```

### Day/Night Temperature Schedule

```python
from datetime import time
from cloudgrow_sim.controllers import ScheduleController

schedule = ScheduleController("temp_schedule", interpolate=True)
schedule.add_entry(time(6, 0), 18.0)   # Dawn
schedule.add_entry(time(9, 0), 24.0)   # Morning warm-up
schedule.add_entry(time(17, 0), 22.0)  # Evening cool-down
schedule.add_entry(time(21, 0), 16.0)  # Night setback

engine.add_controller(schedule)
```

---

## Troubleshooting

### Temperature out of valid range error

`AirState` validates temperature within -50 to 60°C. If physics calculations produce extreme values, the simulation clamps to this range. Check:
- Weather source configuration (extreme values?)
- Heating/cooling capacity vs. heat loss
- Time step (too large can cause instability)

### Import errors

Ensure you're using Python 3.14+:
```bash
python --version
uv run python --version
```

### Slow simulation

- Reduce `emit_interval` in `SimulationConfig`
- Set `emit_events=False` if you don't need real-time updates
- Increase `time_step` (but watch for numerical instability)

---

## API Reference

For detailed API documentation, see the docstrings in the source code:

```bash
# In Python REPL
from cloudgrow_sim.components import ExhaustFan
help(ExhaustFan)
```

Or browse the source at `src/cloudgrow_sim/`.
