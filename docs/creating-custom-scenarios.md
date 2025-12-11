# Creating Custom Scenarios

This tutorial-style guide walks you through creating your own greenhouse simulation scenarios in cloudgrow-sim. You will learn how to model real-world greenhouse environments and configure all aspects of the simulation.

## Table of Contents

1. [Overview](#overview)
2. [Step-by-Step Guide](#step-by-step-guide)
3. [Modeling Real-World Greenhouses](#modeling-real-world-greenhouses)
4. [Configuring Location](#configuring-location)
5. [Choosing Geometry](#choosing-geometry)
6. [Selecting Covering Materials](#selecting-covering-materials)
7. [Adding Sensors](#adding-sensors)
8. [Configuring Actuators](#configuring-actuators)
9. [Setting Up Controllers](#setting-up-controllers)
10. [Weather Configuration](#weather-configuration)
11. [Adding Modifiers](#adding-modifiers)
12. [Complete Example](#complete-example)
13. [Best Practices](#best-practices)
14. [Troubleshooting](#troubleshooting)

---

## Overview

A custom scenario requires these elements:

1. **GreenhouseState**: Physical structure and initial conditions
2. **WeatherSource**: External weather data
3. **SimulationConfig**: Timing and execution parameters
4. **SimulationEngine**: Orchestrates the simulation
5. **Components**: Sensors, actuators, controllers, and modifiers

The basic structure looks like this:

```python
from datetime import datetime, timedelta, UTC

from cloudgrow_sim.core.state import (
    AirState, Location, GreenhouseGeometry, GeometryType,
    GreenhouseState, COVERING_MATERIALS,
)
from cloudgrow_sim.simulation.engine import SimulationConfig, SimulationEngine
from cloudgrow_sim.simulation.weather import SyntheticWeatherSource, SyntheticWeatherConfig

# 1. Define location
location = Location(...)

# 2. Define geometry
geometry = GreenhouseGeometry(...)

# 3. Create initial state
state = GreenhouseState(
    interior=AirState(...),
    exterior=AirState(...),
    time=datetime(...),
    location=location,
    geometry=geometry,
    covering=COVERING_MATERIALS["..."],
)

# 4. Configure weather
weather = SyntheticWeatherSource(SyntheticWeatherConfig(...))

# 5. Create simulation config
config = SimulationConfig(...)

# 6. Build engine and add components
engine = SimulationEngine(state, weather, config)
engine.add_sensor(...)
engine.add_actuator(...)
engine.add_controller(...)

# 7. Run
stats = engine.run()
```

---

## Step-by-Step Guide

### Step 1: Define Your Location

```python
from cloudgrow_sim.core.state import Location

location = Location(
    latitude=40.7128,           # Degrees North (negative for South)
    longitude=-74.0060,         # Degrees East (negative for West)
    elevation=10.0,             # Meters above sea level
    timezone_str="America/New_York",  # IANA timezone
)
```

**Important Notes:**
- Latitude affects solar calculations (day length, sun angle)
- Elevation affects atmospheric pressure and air density
- Use valid IANA timezone strings (e.g., "Europe/London", "Asia/Tokyo")

### Step 2: Define Greenhouse Geometry

```python
from cloudgrow_sim.core.state import GreenhouseGeometry, GeometryType

geometry = GreenhouseGeometry(
    geometry_type=GeometryType.GABLE,  # Structure type
    length=20.0,                        # North-South dimension (m)
    width=8.0,                          # East-West dimension (m)
    height_eave=2.5,                    # Sidewall height (m)
    height_ridge=4.0,                   # Peak height (m)
    orientation=0.0,                    # Degrees from North (0-360)
)
```

**Available Geometry Types:**
| Type | Description |
|------|-------------|
| `GABLE` | Traditional peaked roof |
| `QUONSET` | Curved/rounded roof |
| `GOTHIC` | Pointed arch roof |
| `VENLO` | Multi-span commercial |
| `HIGH_TUNNEL` | Simple hoop structure |
| `CUSTOM` | User-defined |

**Computed Properties:**
- `geometry.floor_area`: Length x Width (m^2)
- `geometry.volume`: Approximate interior volume (m^3)
- `geometry.wall_area`: Total wall surface area (m^2)
- `geometry.roof_area`: Total roof surface area (m^2)

### Step 3: Select Covering Material

```python
from cloudgrow_sim.core.state import COVERING_MATERIALS, CoveringProperties

# Use a pre-defined material
covering = COVERING_MATERIALS["polycarbonate_twin"]

# Or create custom properties
custom_covering = CoveringProperties(
    material_name="custom_acrylic",
    transmittance_solar=0.82,      # Solar transmittance (0-1)
    transmittance_par=0.80,        # PAR transmittance (0-1)
    transmittance_thermal=0.04,    # Long-wave transmittance (0-1)
    u_value=4.5,                   # Heat transfer coefficient (W/m^2K)
    reflectance_solar=0.10,        # Solar reflectance (0-1)
)
```

**Available Materials:**
| Material | Solar Trans. | PAR Trans. | U-Value | Best For |
|----------|--------------|------------|---------|----------|
| `single_glass` | 0.85 | 0.83 | 5.8 | Light, warmer climates |
| `double_glass` | 0.75 | 0.73 | 3.0 | Better insulation |
| `single_polyethylene` | 0.87 | 0.85 | 6.0 | Budget, temporary |
| `double_polyethylene` | 0.77 | 0.75 | 4.0 | Common hobby greenhouse |
| `polycarbonate_twin` | 0.80 | 0.78 | 3.5 | Good all-around |
| `polycarbonate_triple` | 0.72 | 0.70 | 2.5 | Cold climates |

### Step 4: Create Initial State

```python
from datetime import datetime, UTC
from cloudgrow_sim.core.state import AirState, GreenhouseState

state = GreenhouseState(
    interior=AirState(
        temperature=20.0,    # Initial interior temp (C)
        humidity=60.0,       # Initial RH (%)
        co2_ppm=400.0,       # Initial CO2 (ppm)
    ),
    exterior=AirState(
        temperature=15.0,    # Will be overwritten by weather source
        humidity=50.0,
        co2_ppm=400.0,
    ),
    time=datetime(2025, 6, 21, 6, 0, tzinfo=UTC),  # Start time
    location=location,
    geometry=geometry,
    covering=covering,
    solar_radiation=0.0,     # Will be set by weather source
    wind_speed=2.0,          # Will be set by weather source
    wind_direction=180.0,    # Will be set by weather source
)
```

### Step 5: Configure Weather

```python
from cloudgrow_sim.simulation.weather import SyntheticWeatherSource, SyntheticWeatherConfig

weather = SyntheticWeatherSource(
    SyntheticWeatherConfig(
        latitude=location.latitude,
        temp_mean=20.0,              # Annual mean temp (C)
        temp_amplitude_annual=12.0,  # Annual temp swing (C)
        temp_amplitude_daily=8.0,    # Daily temp swing (C)
        humidity_mean=60.0,          # Mean RH (%)
        humidity_amplitude=20.0,     # Daily humidity swing (%)
        solar_max=1000.0,            # Peak solar radiation (W/m^2)
        wind_mean=2.5,               # Mean wind speed (m/s)
        wind_std=1.5,                # Wind speed variability
        cloud_cover_mean=0.3,        # Mean cloud cover (0-1)
    )
)
```

### Step 6: Create Simulation Config

```python
from datetime import timedelta
from cloudgrow_sim.simulation.engine import SimulationConfig

config = SimulationConfig(
    time_step=60.0,                  # Seconds per step
    start_time=state.time,
    end_time=state.time + timedelta(hours=24),
    emit_events=True,                # Enable event emission
    emit_interval=5,                 # Emit every N steps
)
```

### Step 7: Build Engine and Add Components

```python
from cloudgrow_sim.simulation.engine import SimulationEngine

engine = SimulationEngine(state, weather, config)

# Add components (examples follow in subsequent sections)
engine.add_sensor(...)
engine.add_actuator(...)
engine.add_controller(...)
engine.add_modifier(...)
```

---

## Modeling Real-World Greenhouses

### Hobby Greenhouse (Small Backyard)

```python
# Typical 8x10 foot hobby greenhouse
location = Location(
    latitude=39.0,
    longitude=-77.0,
    elevation=100.0,
    timezone_str="America/New_York",
)

geometry = GreenhouseGeometry(
    geometry_type=GeometryType.GABLE,
    length=3.0,   # ~10 feet
    width=2.4,    # ~8 feet
    height_eave=1.8,
    height_ridge=2.5,
)

covering = COVERING_MATERIALS["double_polyethylene"]

# Simple setup: one exhaust fan, one heater
```

### Market Garden (Small Commercial)

```python
# 30x96 foot high tunnel
location = Location(
    latitude=43.0,
    longitude=-89.0,
    elevation=300.0,
    timezone_str="America/Chicago",
)

geometry = GreenhouseGeometry(
    geometry_type=GeometryType.HIGH_TUNNEL,
    length=29.0,  # ~96 feet
    width=9.1,    # ~30 feet
    height_eave=1.5,
    height_ridge=3.6,
)

covering = COVERING_MATERIALS["single_polyethylene"]

# Setup: roll-up sides, endwall fans
```

### Commercial Production (Vegetable)

```python
# 100m x 20m production house
location = Location(
    latitude=36.5,
    longitude=-119.5,
    elevation=80.0,
    timezone_str="America/Los_Angeles",
)

geometry = GreenhouseGeometry(
    geometry_type=GeometryType.VENLO,
    length=100.0,
    width=20.0,
    height_eave=4.0,
    height_ridge=6.0,
)

covering = COVERING_MATERIALS["single_glass"]

# Full setup: multiple fan stages, evap cooling, heating, screens
```

### Research Greenhouse

```python
# Precision-controlled research facility
location = Location(
    latitude=51.5,
    longitude=-0.1,
    elevation=20.0,
    timezone_str="Europe/London",
)

geometry = GreenhouseGeometry(
    geometry_type=GeometryType.GABLE,
    length=15.0,
    width=10.0,
    height_eave=3.0,
    height_ridge=4.5,
)

covering = COVERING_MATERIALS["double_glass"]

# Tight control: PID controllers, multiple sensor zones
```

---

## Configuring Location

### Climate Considerations by Region

| Climate | Example Locations | Key Challenges |
|---------|-------------------|----------------|
| **Continental** | Chicago, Moscow | Extreme cold, variable |
| **Mediterranean** | Los Angeles, Barcelona | Dry summers, mild winters |
| **Tropical** | Miami, Singapore | High humidity, consistent heat |
| **Desert** | Phoenix, Dubai | Extreme heat, low humidity |
| **Maritime** | Seattle, London | Moderate, cloudy |
| **Highland** | Denver, Mexico City | Intense sun, cool nights |

### Location Example: High-Altitude

```python
# Denver, CO at 1,609m elevation
location = Location(
    latitude=39.7392,
    longitude=-104.9903,
    elevation=1609.0,  # Affects pressure calculations
    timezone_str="America/Denver",
)

# High altitude means:
# - Lower atmospheric pressure (affects psychrometrics)
# - More intense solar radiation
# - Larger day/night temperature swings
```

---

## Choosing Geometry

### Geometry Selection Guide

| Use Case | Recommended Type | Rationale |
|----------|------------------|-----------|
| Hobby/backyard | GABLE or QUONSET | Simple, affordable |
| High tunnel | HIGH_TUNNEL | Low-cost, passive |
| Commercial veg | VENLO or GABLE | Multi-span efficiency |
| Cut flowers | GABLE | Good height for tall crops |
| Seedlings | Any | Focus on environmental control |

### Calculating Proper Sizing

```python
# Rule of thumb: ventilation sizing
# Need 0.75-1.0 air changes per minute for cooling

floor_area = 300.0  # m^2
avg_height = 4.0    # m
volume = floor_area * avg_height  # 1200 m^3

# Required ventilation rate
air_changes_per_minute = 0.75
required_flow = volume * air_changes_per_minute / 60  # 15 m^3/s

# Size fans accordingly
# e.g., 5 fans at 3.0 m^3/s each
```

---

## Selecting Covering Materials

### Decision Matrix

| Priority | Best Choice | Notes |
|----------|-------------|-------|
| Maximum light | Single glass/PE | Higher heat loss |
| Cold climate | Triple PC | Lower light, best insulation |
| Budget | Double PE | Needs replacement every 4 years |
| Durability | Polycarbonate | 10-15 year lifespan |
| Research | Double glass | Consistent properties |

### Custom Material Properties

```python
# Example: Diffused glass (improves light distribution)
diffused_glass = CoveringProperties(
    material_name="diffused_glass",
    transmittance_solar=0.78,      # Slightly lower than clear
    transmittance_par=0.76,
    transmittance_thermal=0.02,
    u_value=5.5,
    reflectance_solar=0.10,
)
```

---

## Adding Sensors

### Available Sensor Types

```python
from cloudgrow_sim.components.sensors.temperature import TemperatureSensor
from cloudgrow_sim.components.sensors.humidity import (
    HumiditySensor,
    CombinedTempHumiditySensor,
)
from cloudgrow_sim.components.sensors.radiation import (
    SolarRadiationSensor,
    PARSensor,
)
```

### Temperature Sensor

```python
from cloudgrow_sim.components.sensors.temperature import TemperatureSensor

# Interior temperature
temp_sensor = TemperatureSensor(
    name="temp_interior_1",
    location="interior",          # "interior" or "exterior"
    noise_std_dev=0.2,           # Measurement noise (C)
    enabled=True,
)
engine.add_sensor(temp_sensor)

# Exterior temperature
temp_ext = TemperatureSensor(
    name="temp_exterior",
    location="exterior",
    noise_std_dev=0.1,
)
engine.add_sensor(temp_ext)
```

### Combined Temperature/Humidity Sensor

```python
from cloudgrow_sim.components.sensors.humidity import CombinedTempHumiditySensor

# Models common DHT22/SHT31 type sensors
dht_sensor = CombinedTempHumiditySensor(
    name="dht_zone_1",
    location="interior",
    temp_noise_std_dev=0.3,      # Temperature noise (C)
    humidity_noise_std_dev=2.0,  # Humidity noise (%)
)
engine.add_sensor(dht_sensor)
```

### Radiation Sensors

```python
from cloudgrow_sim.components.sensors.radiation import SolarRadiationSensor, PARSensor

# Pyranometer (measures total solar radiation)
pyranometer = SolarRadiationSensor(
    name="pyranometer",
    location="exterior",
    noise_std_dev=5.0,  # W/m^2
)
engine.add_sensor(pyranometer)

# PAR sensor (measures photosynthetically active radiation)
par_sensor = PARSensor(
    name="par_canopy",
    location="interior",  # Accounts for covering transmittance
    noise_std_dev=10.0,   # umol/m^2/s
)
engine.add_sensor(par_sensor)
```

### Sensor Placement Strategy

```python
# Multiple sensors for averaging
for i, (x, y) in enumerate([(5, 3), (15, 3), (5, 7), (15, 7)]):
    sensor = CombinedTempHumiditySensor(
        name=f"zone_{i+1}_sensor",
        location="interior",
        temp_noise_std_dev=0.2,
    )
    engine.add_sensor(sensor)
```

---

## Configuring Actuators

### Available Actuator Types

```python
from cloudgrow_sim.components.actuators.fans import (
    ExhaustFan,
    IntakeFan,
    CirculationFan,
)
from cloudgrow_sim.components.actuators.heating import (
    UnitHeater,
    RadiantHeater,
)
from cloudgrow_sim.components.actuators.cooling import (
    EvaporativePad,
    Fogger,
)
from cloudgrow_sim.components.actuators.vents import (
    RoofVent,
    SideVent,
)
```

### Exhaust Fan

```python
from cloudgrow_sim.components.actuators.fans import ExhaustFan

exhaust = ExhaustFan(
    name="exhaust_fan_1",
    max_flow_rate=3.0,          # m^3/s at full speed
    power_consumption=750.0,    # Watts at full speed
    output_limits=(0.0, 1.0),   # Speed range (0-100%)
)
engine.add_actuator(exhaust)
```

### Unit Heater

```python
from cloudgrow_sim.components.actuators.heating import UnitHeater

heater = UnitHeater(
    name="main_heater",
    heating_capacity=20000.0,   # 20 kW maximum output
    efficiency=0.92,            # 92% efficient
)
engine.add_actuator(heater)
```

### Evaporative Pad

```python
from cloudgrow_sim.components.actuators.cooling import EvaporativePad

evap_pad = EvaporativePad(
    name="evap_cooling",
    pad_area=8.0,               # m^2 of pad face area
    pad_thickness=0.15,         # 15 cm thick
    saturation_efficiency=0.85, # 85% wet-bulb approach
)
engine.add_actuator(evap_pad)
```

### Roof Vent

```python
from cloudgrow_sim.components.actuators.vents import RoofVent

vent = RoofVent(
    name="ridge_vent_1",
    width=2.0,                  # Vent width (m)
    height=0.6,                 # Vent height when open (m)
    height_above_floor=4.5,     # Height of vent (m)
    discharge_coefficient=0.65, # Flow coefficient
)
engine.add_actuator(vent)
```

### Sizing Actuators

```python
# Heating sizing: Rule of thumb
# Need 50-100 W/m^2 of floor area for cold climates
floor_area = 300.0  # m^2
heating_need = floor_area * 75  # 22,500 W = 22.5 kW

# Ventilation sizing: See geometry section
# Evap pad sizing: 1 m^2 per 20-30 m^2 floor area
evap_area = floor_area / 25  # 12 m^2
```

---

## Setting Up Controllers

### Available Controller Types

```python
from cloudgrow_sim.controllers.pid import PIDController
from cloudgrow_sim.controllers.hysteresis import HysteresisController
from cloudgrow_sim.controllers.staged import StagedController
from cloudgrow_sim.controllers.schedule import ScheduleController
```

### PID Controller

Best for smooth, precise control (heating, cooling).

```python
from cloudgrow_sim.controllers.pid import PIDController

cooling_pid = PIDController(
    name="cooling_control",
    kp=0.5,                     # Proportional gain
    ki=0.1,                     # Integral gain
    kd=0.05,                    # Derivative gain
    setpoint=24.0,              # Target temperature (C)
    output_limits=(0.0, 1.0),   # Output range
    reverse_acting=True,        # Increase output when PV > SP
    anti_windup=True,           # Prevent integral windup
)
engine.add_controller(cooling_pid)

# Heating (direct-acting: output increases when PV < SP)
heating_pid = PIDController(
    name="heating_control",
    kp=0.8,
    ki=0.2,
    kd=0.1,
    setpoint=18.0,
    output_limits=(0.0, 1.0),
    reverse_acting=False,       # Direct acting for heating
)
engine.add_controller(heating_pid)
```

### PID Tuning Guidelines

| Application | Kp | Ki | Kd | Notes |
|-------------|----|----|----| ------|
| Greenhouse heating | 0.5-1.0 | 0.1-0.3 | 0.05-0.15 | Slower response OK |
| Greenhouse cooling | 0.3-0.8 | 0.05-0.2 | 0.02-0.1 | Prevent overshoot |
| Humidity control | 0.2-0.5 | 0.02-0.1 | 0.01-0.05 | Very slow dynamics |

### Hysteresis Controller

Best for simple on/off control with deadband.

```python
from cloudgrow_sim.controllers.hysteresis import HysteresisController

# Heating: Turn on below 17C, off above 19C
heat_control = HysteresisController(
    name="heater_control",
    setpoint=18.0,              # Center of deadband
    hysteresis=2.0,             # Total deadband width (17-19C)
    output_on=1.0,              # Output when active
    output_off=0.0,             # Output when inactive
    reverse_acting=False,       # Heating mode
)
engine.add_controller(heat_control)

# Cooling: Turn on above 27C, off below 25C
vent_control = HysteresisController(
    name="vent_control",
    setpoint=26.0,
    hysteresis=2.0,
    reverse_acting=True,        # Cooling mode
)
engine.add_controller(vent_control)
```

### Staged Controller

Best for multi-stage equipment (fan banks, multiple heaters).

```python
from cloudgrow_sim.controllers.staged import StagedController

fan_staging = StagedController(
    name="fan_stages",
    stages=[
        (25.0, 0.25),   # Stage 1: 25% at 25C
        (27.0, 0.50),   # Stage 2: 50% at 27C
        (29.0, 0.75),   # Stage 3: 75% at 29C
        (31.0, 1.00),   # Stage 4: 100% at 31C
    ],
    hysteresis=0.5,     # 0.5C deadband between stages
)
engine.add_controller(fan_staging)
```

### Schedule Controller

Best for time-based setpoints.

```python
from cloudgrow_sim.controllers.schedule import ScheduleController

# Day/night temperature schedule
temp_schedule = ScheduleController(
    name="temp_setpoint",
    schedule=[
        ("06:00", 18.0),   # Morning warm-up
        ("08:00", 22.0),   # Daytime
        ("18:00", 20.0),   # Evening
        ("22:00", 16.0),   # Night setback
    ],
    interpolate=True,      # Smooth transitions
    mode="setpoint",       # Updates setpoint property
    default_value=18.0,
)
engine.add_controller(temp_schedule)
```

---

## Weather Configuration

### Synthetic Weather Parameters

```python
SyntheticWeatherConfig(
    latitude=40.0,               # For day length calculation
    temp_mean=15.0,              # Annual average (C)
    temp_amplitude_annual=12.0,  # Summer-winter difference (C)
    temp_amplitude_daily=8.0,    # Day-night difference (C)
    humidity_mean=60.0,          # Average RH (%)
    humidity_amplitude=20.0,     # Day-night RH swing (%)
    solar_max=1000.0,            # Peak clear-sky radiation (W/m^2)
    wind_mean=2.5,               # Average wind (m/s)
    wind_std=1.5,                # Wind variability
    cloud_cover_mean=0.3,        # Average cloud cover (0-1)
)
```

### Climate Presets

```python
# Hot/dry desert (Phoenix)
desert_weather = SyntheticWeatherConfig(
    latitude=33.4,
    temp_mean=23.0,
    temp_amplitude_annual=15.0,
    temp_amplitude_daily=15.0,
    humidity_mean=30.0,
    humidity_amplitude=15.0,
    solar_max=1100.0,
    wind_mean=2.0,
    cloud_cover_mean=0.1,
)

# Cold continental (Minnesota)
continental_weather = SyntheticWeatherConfig(
    latitude=45.0,
    temp_mean=7.0,
    temp_amplitude_annual=25.0,
    temp_amplitude_daily=10.0,
    humidity_mean=70.0,
    humidity_amplitude=15.0,
    solar_max=900.0,
    wind_mean=4.0,
    cloud_cover_mean=0.5,
)

# Tropical (Florida)
tropical_weather = SyntheticWeatherConfig(
    latitude=26.0,
    temp_mean=24.0,
    temp_amplitude_annual=8.0,
    temp_amplitude_daily=6.0,
    humidity_mean=75.0,
    humidity_amplitude=15.0,
    solar_max=1000.0,
    wind_mean=3.0,
    cloud_cover_mean=0.4,
)
```

### Using CSV Weather Data

```python
from cloudgrow_sim.simulation.weather import CSVWeatherSource, CSVWeatherMapping

# Custom column mapping
mapping = CSVWeatherMapping(
    timestamp="datetime",        # Column name for timestamp
    temperature="temp_c",        # Column name for temperature
    humidity="rh_percent",
    solar_radiation="ghi_wm2",
    wind_speed="wind_ms",
)

weather = CSVWeatherSource(
    file_path="/path/to/weather_data.csv",
    mapping=mapping,
    timestamp_format="%Y-%m-%d %H:%M:%S",
)
```

---

## Adding Modifiers

### Thermal Mass

```python
from cloudgrow_sim.components.modifiers.thermal_mass import ThermalMass

# Water barrels (common thermal mass)
water_barrels = ThermalMass(
    name="water_storage",
    mass=2000.0,                  # 10 x 200L barrels = 2000 kg
    specific_heat=4186.0,         # Water: 4186 J/(kg*K)
    surface_area=15.0,            # Total exposed surface (m^2)
    initial_temperature=20.0,     # Starting temp (C)
    heat_transfer_coefficient=10.0,  # Surface h (W/m^2*K)
)
engine.add_modifier(water_barrels)

# Concrete floor thermal mass
concrete_floor = ThermalMass(
    name="concrete_floor",
    mass=floor_area * 240.0,      # 10cm thick = 240 kg/m^2
    specific_heat=880.0,          # Concrete: 880 J/(kg*K)
    surface_area=floor_area,
    initial_temperature=18.0,
)
engine.add_modifier(concrete_floor)
```

### Covering Material Modifier

```python
from cloudgrow_sim.components.modifiers.covering import CoveringMaterial

covering_mod = CoveringMaterial(
    name="greenhouse_cover",
    material="polycarbonate_twin",  # Or provide custom properties
)
engine.add_modifier(covering_mod)
```

---

## Complete Example

Here is a complete working example of a custom scenario:

```python
"""Custom scenario: Small commercial tomato greenhouse."""

from datetime import datetime, timedelta, UTC

from cloudgrow_sim.core.state import (
    AirState,
    Location,
    GreenhouseGeometry,
    GeometryType,
    GreenhouseState,
    COVERING_MATERIALS,
)
from cloudgrow_sim.simulation.engine import SimulationConfig, SimulationEngine
from cloudgrow_sim.simulation.weather import SyntheticWeatherSource, SyntheticWeatherConfig
from cloudgrow_sim.core.events import EventType, get_event_bus

# Component imports
from cloudgrow_sim.components.sensors.temperature import TemperatureSensor
from cloudgrow_sim.components.sensors.humidity import CombinedTempHumiditySensor
from cloudgrow_sim.components.sensors.radiation import PARSensor
from cloudgrow_sim.components.actuators.fans import ExhaustFan, CirculationFan
from cloudgrow_sim.components.actuators.heating import UnitHeater
from cloudgrow_sim.components.actuators.vents import RoofVent
from cloudgrow_sim.components.modifiers.thermal_mass import ThermalMass
from cloudgrow_sim.controllers.pid import PIDController
from cloudgrow_sim.controllers.staged import StagedController
from cloudgrow_sim.controllers.hysteresis import HysteresisController


def create_tomato_greenhouse() -> SimulationEngine:
    """Create a tomato production greenhouse scenario."""

    # === LOCATION: Central Valley, California ===
    location = Location(
        latitude=36.7,
        longitude=-119.8,
        elevation=100.0,
        timezone_str="America/Los_Angeles",
    )

    # === GEOMETRY: 50m x 12m gutter-connected house ===
    geometry = GreenhouseGeometry(
        geometry_type=GeometryType.GABLE,
        length=50.0,
        width=12.0,
        height_eave=3.5,
        height_ridge=5.5,
        orientation=0.0,  # North-South orientation
    )

    # === INITIAL STATE ===
    start_time = datetime(2025, 7, 1, 6, 0, tzinfo=UTC)

    state = GreenhouseState(
        interior=AirState(
            temperature=22.0,
            humidity=65.0,
            co2_ppm=400.0,
        ),
        exterior=AirState(
            temperature=18.0,
            humidity=50.0,
            co2_ppm=400.0,
        ),
        time=start_time,
        location=location,
        geometry=geometry,
        covering=COVERING_MATERIALS["single_glass"],
        solar_radiation=0.0,
        wind_speed=2.0,
        wind_direction=270.0,
    )

    # === WEATHER: Summer California pattern ===
    weather = SyntheticWeatherSource(
        SyntheticWeatherConfig(
            latitude=location.latitude,
            temp_mean=25.0,
            temp_amplitude_annual=0.0,  # Fixed summer
            temp_amplitude_daily=12.0,
            humidity_mean=45.0,
            humidity_amplitude=20.0,
            solar_max=1000.0,
            wind_mean=2.5,
            wind_std=1.0,
            cloud_cover_mean=0.1,
        )
    )

    # === SIMULATION CONFIG ===
    config = SimulationConfig(
        time_step=60.0,  # 1 minute steps
        start_time=start_time,
        end_time=start_time + timedelta(days=7),  # Week-long simulation
        emit_events=True,
        emit_interval=10,  # Emit every 10 minutes
    )

    # === BUILD ENGINE ===
    engine = SimulationEngine(state, weather, config)

    # === SENSORS ===
    # Zone temperature sensors
    engine.add_sensor(TemperatureSensor("temp_zone_1", location="interior"))
    engine.add_sensor(TemperatureSensor("temp_exterior", location="exterior"))

    # Combined sensors
    engine.add_sensor(
        CombinedTempHumiditySensor(
            "dht_canopy",
            location="interior",
            temp_noise_std_dev=0.2,
            humidity_noise_std_dev=2.0,
        )
    )

    # PAR sensor
    engine.add_sensor(PARSensor("par_bench", location="interior"))

    # === ACTUATORS ===
    # Exhaust fans (3 stages)
    for i in range(3):
        engine.add_actuator(
            ExhaustFan(
                f"exhaust_{i+1}",
                max_flow_rate=4.0,
                power_consumption=1000.0,
            )
        )

    # Circulation fans
    engine.add_actuator(CirculationFan("haf_1", power_consumption=150.0))
    engine.add_actuator(CirculationFan("haf_2", power_consumption=150.0))

    # Roof vents
    engine.add_actuator(
        RoofVent("ridge_vent_1", width=3.0, height=0.6, height_above_floor=5.0)
    )
    engine.add_actuator(
        RoofVent("ridge_vent_2", width=3.0, height=0.6, height_above_floor=5.0)
    )

    # Heater
    engine.add_actuator(
        UnitHeater("heater_main", heating_capacity=30000.0, efficiency=0.90)
    )

    # === CONTROLLERS ===
    # Cooling: Staged fans
    engine.add_controller(
        StagedController(
            "fan_staging",
            stages=[
                (26.0, 0.33),  # Stage 1 at 26C
                (28.0, 0.67),  # Stage 2 at 28C
                (30.0, 1.00),  # Stage 3 at 30C
            ],
            hysteresis=0.5,
        )
    )

    # Vent control
    engine.add_controller(
        HysteresisController(
            "vent_control",
            setpoint=25.0,
            hysteresis=2.0,
            reverse_acting=True,
        )
    )

    # Heating: PID for night temperatures
    engine.add_controller(
        PIDController(
            "heating_pid",
            kp=0.6,
            ki=0.15,
            kd=0.08,
            setpoint=18.0,  # Night setpoint
            output_limits=(0.0, 1.0),
            reverse_acting=False,
        )
    )

    # === MODIFIERS ===
    # Thermal mass from irrigation water storage
    engine.add_modifier(
        ThermalMass(
            "water_tank",
            mass=5000.0,  # 5000L tank
            specific_heat=4186.0,
            surface_area=10.0,
            initial_temperature=20.0,
        )
    )

    return engine


def run_simulation():
    """Run the tomato greenhouse simulation with data collection."""

    engine = create_tomato_greenhouse()

    # Data collection
    results = {
        "timestamps": [],
        "interior_temp": [],
        "exterior_temp": [],
        "humidity": [],
        "solar": [],
    }

    def collect_data(event):
        data = event.data
        results["timestamps"].append(event.timestamp)
        results["interior_temp"].append(data.get("interior_temperature", 0))
        results["exterior_temp"].append(data.get("exterior_temperature", 0))
        results["humidity"].append(data.get("interior_humidity", 0))
        results["solar"].append(data.get("solar_radiation", 0))

    bus = get_event_bus()
    bus.clear_handlers()
    bus.subscribe(EventType.STATE_UPDATE, collect_data)

    # Run simulation
    print("Running 7-day tomato greenhouse simulation...")
    stats = engine.run()

    # Report results
    print(f"\nSimulation Complete")
    print(f"Steps: {stats.steps_completed}")
    print(f"Wall time: {stats.wall_time.total_seconds():.1f}s")
    print(f"Performance: {stats.steps_completed / stats.wall_time.total_seconds():.0f} steps/sec")

    if results["interior_temp"]:
        temps = results["interior_temp"]
        print(f"\nTemperature Statistics:")
        print(f"  Min: {min(temps):.1f}C")
        print(f"  Max: {max(temps):.1f}C")
        print(f"  Mean: {sum(temps)/len(temps):.1f}C")

        # Check temperature exceedances
        over_32 = sum(1 for t in temps if t > 32.0)
        under_15 = sum(1 for t in temps if t < 15.0)
        print(f"\nExceedances:")
        print(f"  Above 32C: {over_32} readings ({over_32/len(temps)*100:.1f}%)")
        print(f"  Below 15C: {under_15} readings ({under_15/len(temps)*100:.1f}%)")

    return engine, results


if __name__ == "__main__":
    engine, results = run_simulation()
```

---

## Best Practices

### 1. Start Simple, Add Complexity

```python
# Phase 1: Basic structure
engine = create_basic_greenhouse()
engine.run()

# Phase 2: Add sensors
engine.add_sensor(temp_sensor)

# Phase 3: Add control
engine.add_controller(simple_controller)
engine.add_actuator(actuator)

# Phase 4: Refine
# Tune PID, add staging, add thermal mass
```

### 2. Match Components to Real Equipment

```python
# Research your actual equipment specifications
# Example: Modine PDP200 unit heater
heater = UnitHeater(
    name="modine_pdp200",
    heating_capacity=58600.0,  # 200,000 BTU/h = 58.6 kW
    efficiency=0.80,           # 80% AFUE rating
)
```

### 3. Size Controllers Appropriately

```python
# Deadband should be 2-4x sensor noise
sensor_noise = 0.2  # C
deadband = sensor_noise * 3  # 0.6C minimum

# PID integral time should be 2-4x process time constant
# Greenhouse thermal time constant ~15-30 minutes
# Ti = Ki / Kp, so Ki = Kp / Ti
kp = 0.5
ti = 1200  # 20 minutes in seconds
ki = kp / ti  # ~0.0004 per second
```

### 4. Use Appropriate Time Steps

| Scenario | Time Step | Rationale |
|----------|-----------|-----------|
| Quick tests | 60s | Fast execution |
| Detailed dynamics | 10-30s | Capture fast changes |
| Long-term studies | 60-300s | Reduce computation |

### 5. Validate Against Expected Behavior

```python
# After running, check physics make sense
assert engine.state.interior.temperature > -20.0  # Not frozen
assert engine.state.interior.temperature < 50.0   # Not impossible

# Check conservation
# Solar input should roughly balance losses when stable
```

---

## Troubleshooting

### Temperature Runaway

**Symptom**: Temperature climbs/drops unrealistically

**Causes and Solutions**:
1. **Insufficient cooling capacity**: Add more fans or larger evap pad
2. **Controller not connected**: Verify controller is added to engine
3. **Wrong control direction**: Check `reverse_acting` parameter
4. **Time step too large**: Reduce time step (try 30s)

### Temperature Oscillation

**Symptom**: Temperature bounces around setpoint

**Causes and Solutions**:
1. **PID gains too high**: Reduce Kp, Ki
2. **Hysteresis too small**: Increase deadband
3. **Actuator oversized**: Use smaller equipment or staging

### Simulation Running Slowly

**Symptom**: Wall time much longer than expected

**Causes and Solutions**:
1. **Time step too small**: Increase from 10s to 60s
2. **Too many events**: Increase `emit_interval`
3. **Many components**: Consider if all are needed

### Humidity Always 100%

**Symptom**: Humidity saturates immediately

**Causes and Solutions**:
1. **Ventilation insufficient**: Add more exhaust capacity
2. **Fogging/humidification stuck on**: Check controller logic
3. **Initial conditions unrealistic**: Start with lower RH

### No Temperature Change

**Symptom**: Interior stays at initial temperature

**Causes and Solutions**:
1. **Components disabled**: Check `enabled=True`
2. **Weather not updating**: Verify weather source
3. **Physics disabled**: Unlikely, but check engine configuration

### Debugging Tips

```python
# Print state each step
while engine.step():
    s = engine.state
    print(f"T_int={s.interior.temperature:.1f} T_ext={s.exterior.temperature:.1f} "
          f"Solar={s.solar_radiation:.0f}")

# Check actuator effects
for actuator in engine._actuators:
    effect = actuator.get_effect(engine.state)
    print(f"{actuator.name}: {effect}")

# Check controller outputs
for controller in engine._controllers:
    print(f"{controller.name}: output={controller.output:.2f}")
```

---

## Next Steps

- Review [Scenarios Guide](./scenarios-guide.md) for pre-built examples
- Check source code in `src/cloudgrow_sim/simulation/scenarios.py` for patterns
- Run `examples/basic_simulation.py` to see working code
- Consult physics modules for ASHRAE calculation details
