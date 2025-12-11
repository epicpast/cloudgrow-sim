# Scenarios Guide

This guide provides comprehensive documentation for the pre-built simulation scenarios in cloudgrow-sim. Scenarios are complete, ready-to-run greenhouse configurations that demonstrate different aspects of greenhouse climate control.

## Table of Contents

1. [What Are Scenarios?](#what-are-scenarios)
2. [Pre-Built Scenarios](#pre-built-scenarios)
   - [Basic Scenario](#basic-scenario)
   - [Full Climate Scenario](#full-climate-scenario)
   - [Winter Heating Scenario](#winter-heating-scenario)
   - [Summer Cooling Scenario](#summer-cooling-scenario)
3. [Running Scenarios](#running-scenarios)
4. [Event System and Data Collection](#event-system-and-data-collection)
5. [Interpreting Results](#interpreting-results)
6. [Scenario Comparison](#scenario-comparison)

---

## What Are Scenarios?

Scenarios in cloudgrow-sim are pre-configured `SimulationEngine` instances that combine:

- **Greenhouse State**: Location, geometry, covering material, initial conditions
- **Weather Source**: Synthetic weather patterns or historical data
- **Components**: Sensors, actuators, and controllers
- **Simulation Configuration**: Duration, time step, event emission settings

Scenarios serve multiple purposes:

1. **Quick Start**: Get running immediately without manual configuration
2. **Testing**: Validate simulation behavior and physics
3. **Learning**: Understand how components interact
4. **Benchmarking**: Compare different control strategies
5. **Templates**: Starting points for custom configurations

---

## Pre-Built Scenarios

### Basic Scenario

**Purpose**: Minimal configuration for testing basic simulation functionality.

**Function**: `create_basic_scenario(duration_hours=24.0, time_step=60.0)`

#### Greenhouse Configuration

| Property | Value |
|----------|-------|
| Type | Small hobby greenhouse |
| Dimensions | 10m x 6m (60 m^2 floor area) |
| Height | 2.4m eave, 3.5m ridge |
| Geometry | Gable |
| Covering | Double polyethylene |
| Location | Mid-Atlantic US (37.5N, 77.4W) |
| Timezone | America/New_York |

#### Components

**Sensors:**
- `temp_int`: Interior temperature sensor

**Actuators:**
- `exhaust_1`: Exhaust fan (1.0 m^3/s, 500W)

**Controllers:**
- `vent_control`: Hysteresis controller (setpoint 28C, hysteresis 2C, reverse-acting)

#### Weather Configuration

```python
SyntheticWeatherConfig(
    latitude=37.5,
    temp_mean=18.0,
    temp_amplitude_daily=8.0,
)
```

#### Use Cases

- Verifying simulation loop execution
- Testing basic heat balance calculations
- Understanding hysteresis control behavior
- Quick validation of code changes

#### Example

```python
from cloudgrow_sim.simulation.scenarios import create_basic_scenario

engine = create_basic_scenario(duration_hours=24.0)
stats = engine.run()

print(f"Completed {stats.steps_completed} steps")
print(f"Final temperature: {engine.state.interior.temperature:.1f}C")
```

---

### Full Climate Scenario

**Purpose**: Comprehensive commercial greenhouse with complete climate control.

**Function**: `create_full_climate_scenario(duration_hours=24.0, time_step=60.0)`

#### Greenhouse Configuration

| Property | Value |
|----------|-------|
| Type | Commercial production greenhouse |
| Dimensions | 30m x 10m (300 m^2 floor area) |
| Height | 3.0m eave, 5.0m ridge |
| Geometry | Gable |
| Covering | Single glass |
| Location | Central California (36.8N, 119.8W) |
| Timezone | America/Los_Angeles |

#### Components

**Sensors:**
| Name | Type | Location | Parameters |
|------|------|----------|------------|
| `dht_int` | Combined Temp/Humidity | Interior | temp_noise=0.2C, humidity_noise=2% |
| `par_int` | PAR | Interior | - |
| `pyranometer` | Solar Radiation | Exterior | - |
| `temp_ext` | Temperature | Exterior | - |

**Actuators:**
| Name | Type | Specifications |
|------|------|---------------|
| `exhaust_1` | Exhaust Fan | 2.0 m^3/s, 750W |
| `exhaust_2` | Exhaust Fan | 2.0 m^3/s, 750W |
| `exhaust_3` | Exhaust Fan | 2.0 m^3/s, 750W |
| `circ_fan` | Circulation Fan | 200W |
| `evap_pad` | Evaporative Pad | 6.0 m^2, 85% efficiency |
| `heater_1` | Unit Heater | 15 kW, 90% efficiency |
| `vent_roof_1` | Roof Vent | 2.0m x 0.5m, 4.5m height |
| `vent_roof_2` | Roof Vent | 2.0m x 0.5m, 4.5m height |

**Controllers:**
| Name | Type | Configuration |
|------|------|---------------|
| `cooling_pid` | PID | Kp=0.5, Ki=0.1, Kd=0.05, SP=26C, reverse-acting |
| `heating_control` | Hysteresis | SP=18C, hysteresis=2C, direct-acting |
| `fan_staging` | Staged | Stages: (26C, 33%), (28C, 66%), (30C, 100%), hysteresis=0.5C |

**Modifiers:**
| Name | Type | Configuration |
|------|------|---------------|
| `covering` | CoveringMaterial | Single glass |
| `water_barrels` | ThermalMass | 2000 kg, 15 m^2 surface, water specific heat |

#### Weather Configuration

```python
SyntheticWeatherConfig(
    latitude=36.8,
    temp_mean=20.0,
    temp_amplitude_daily=10.0,
    humidity_mean=50.0,
    solar_max=1000.0,
)
```

#### Use Cases

- Testing integrated climate control strategies
- Evaluating PID tuning parameters
- Studying thermal mass effects
- Demonstrating staged fan control
- Simulating typical commercial operations

#### Example

```python
from cloudgrow_sim.simulation.scenarios import create_full_climate_scenario
from cloudgrow_sim.core.events import EventType, get_event_bus

engine = create_full_climate_scenario(duration_hours=48.0)

# Track data
data = []
def log_state(event):
    data.append(event.data.copy())

bus = get_event_bus()
bus.subscribe(EventType.STATE_UPDATE, log_state)

stats = engine.run()

# Analyze results
temps = [d['interior_temperature'] for d in data]
print(f"Temperature range: {min(temps):.1f}C - {max(temps):.1f}C")
```

---

### Winter Heating Scenario

**Purpose**: Cold weather stress test for heating systems.

**Function**: `create_winter_heating_scenario(duration_hours=48.0)`

#### Greenhouse Configuration

| Property | Value |
|----------|-------|
| Type | Cold-climate greenhouse |
| Dimensions | 20m x 8m (160 m^2 floor area) |
| Height | 2.5m eave, 4.0m ridge |
| Geometry | Gable |
| Covering | Twin-wall polycarbonate |
| Location | Boston, MA (42.3N, 71.1W) |
| Timezone | America/New_York |
| Start Date | January 15, 2025 |

#### Initial Conditions

| Parameter | Interior | Exterior |
|-----------|----------|----------|
| Temperature | 18C | -5C |
| Humidity | 50% | 70% |
| Wind Speed | - | 5 m/s |

#### Components

**Sensors:**
- `temp_int`: Interior temperature sensor
- `temp_ext`: Exterior temperature sensor

**Actuators:**
| Name | Type | Specifications |
|------|------|---------------|
| `main_heater` | Unit Heater | 25 kW, 92% efficiency |
| `backup_heater` | Unit Heater | 15 kW, 88% efficiency |

**Controllers:**
| Name | Type | Configuration |
|------|------|---------------|
| `heating_pid` | PID | Kp=0.8, Ki=0.2, Kd=0.1, SP=18C, direct-acting |

**Modifiers:**
| Name | Type | Configuration |
|------|------|---------------|
| `covering` | CoveringMaterial | Twin-wall polycarbonate (U-value 3.5 W/m^2K) |

#### Weather Configuration

```python
SyntheticWeatherConfig(
    latitude=42.3,
    temp_mean=-2.0,
    temp_amplitude_daily=5.0,
    temp_amplitude_annual=0.0,  # Fixed winter conditions
    solar_max=400.0,            # Low winter sun
    wind_mean=4.0,
    cloud_cover_mean=0.6,
)
```

#### Use Cases

- Testing heating system capacity
- Evaluating backup heater activation
- Studying heat loss through different coverings
- Validating PID heating control
- Energy consumption analysis in cold climates

#### Example

```python
from cloudgrow_sim.simulation.scenarios import create_winter_heating_scenario
from cloudgrow_sim.core.events import EventType, get_event_bus

engine = create_winter_heating_scenario(duration_hours=72.0)

min_temp = float('inf')
max_heating_demand = 0.0

def track_conditions(event):
    global min_temp, max_heating_demand
    data = event.data
    if 'interior_temperature' in data:
        min_temp = min(min_temp, data['interior_temperature'])

bus = get_event_bus()
bus.subscribe(EventType.STATE_UPDATE, track_conditions)

engine.run()

print(f"Minimum interior temperature: {min_temp:.1f}C")
print(f"Setpoint maintained: {min_temp >= 16.0}")  # 2C below setpoint
```

---

### Summer Cooling Scenario

**Purpose**: Hot weather stress test for cooling systems.

**Function**: `create_summer_cooling_scenario(duration_hours=48.0)`

#### Greenhouse Configuration

| Property | Value |
|----------|-------|
| Type | Desert climate greenhouse |
| Dimensions | 25m x 9m (225 m^2 floor area) |
| Height | 2.0m eave, 4.5m ridge |
| Geometry | Quonset |
| Covering | Double polyethylene |
| Location | Phoenix, AZ (33.4N, 112.0W) |
| Timezone | America/Phoenix |
| Start Date | July 15, 2025 |

#### Initial Conditions

| Parameter | Interior | Exterior |
|-----------|----------|----------|
| Temperature | 28C | 35C |
| Humidity | 40% | 20% |
| Wind Speed | - | 1 m/s |

#### Components

**Sensors:**
- `dht_int`: Combined temp/humidity sensor (interior)
- `pyranometer`: Solar radiation sensor

**Actuators:**
| Name | Type | Specifications |
|------|------|---------------|
| `exhaust_1` - `exhaust_4` | Exhaust Fans | 3.0 m^3/s each, 1000W |
| `evap_pad` | Evaporative Pad | 12.0 m^2, 85% efficiency |

**Controllers:**
| Name | Type | Configuration |
|------|------|---------------|
| `fan_staging` | Staged | Stages: (28C, 25%), (30C, 50%), (32C, 75%), (34C, 100%), hysteresis=1.0C |
| `evap_control` | Hysteresis | SP=30C, hysteresis=2C, reverse-acting |

#### Weather Configuration

```python
SyntheticWeatherConfig(
    latitude=33.4,
    temp_mean=38.0,
    temp_amplitude_daily=12.0,
    temp_amplitude_annual=0.0,  # Fixed summer conditions
    humidity_mean=25.0,
    solar_max=1100.0,
    wind_mean=2.0,
    cloud_cover_mean=0.1,
)
```

#### Use Cases

- Testing evaporative cooling effectiveness
- Evaluating fan staging strategies
- Studying cooling in low-humidity climates
- Validating extreme temperature management
- Water consumption analysis

#### Example

```python
from cloudgrow_sim.simulation.scenarios import create_summer_cooling_scenario
from cloudgrow_sim.core.events import EventType, get_event_bus

engine = create_summer_cooling_scenario(duration_hours=48.0)

peak_temp = float('-inf')
temps_over_35 = 0

def track_conditions(event):
    global peak_temp, temps_over_35
    data = event.data
    if 'interior_temperature' in data:
        temp = data['interior_temperature']
        peak_temp = max(peak_temp, temp)
        if temp > 35.0:
            temps_over_35 += 1

bus = get_event_bus()
bus.subscribe(EventType.STATE_UPDATE, track_conditions)

stats = engine.run()

print(f"Peak interior temperature: {peak_temp:.1f}C")
print(f"Steps above 35C: {temps_over_35} / {stats.steps_completed}")
```

---

## Running Scenarios

### Basic Execution

```python
from cloudgrow_sim.simulation.scenarios import create_basic_scenario

# Create and run
engine = create_basic_scenario()
stats = engine.run()

# Access results
print(f"Steps: {stats.steps_completed}")
print(f"Simulation time: {stats.simulation_time}")
print(f"Wall time: {stats.wall_time.total_seconds():.2f}s")
print(f"Avg step time: {stats.avg_step_time:.3f}ms")
```

### Step-by-Step Execution

For debugging or interactive analysis:

```python
engine = create_basic_scenario()

# Run specific number of steps
stats = engine.run(steps=100)

# Or iterate manually
while engine.step():
    state = engine.state
    print(f"Time: {state.time}, Temp: {state.interior.temperature:.1f}C")

    # Stop condition
    if state.interior.temperature > 35.0:
        break
```

### Accessing State During Simulation

```python
engine = create_full_climate_scenario()

# Run partial simulation
engine.run(steps=500)

# Check intermediate state
state = engine.state
print(f"Interior: {state.interior.temperature:.1f}C, {state.interior.humidity:.1f}%")
print(f"Exterior: {state.exterior.temperature:.1f}C")
print(f"Solar: {state.solar_radiation:.0f} W/m^2")

# Continue simulation
engine.run()  # Runs to end
```

---

## Event System and Data Collection

The event system enables real-time monitoring and data collection during simulations.

### Event Types

```python
from cloudgrow_sim.core.events import EventType

# Available event types:
EventType.SIMULATION_START      # Simulation begins
EventType.SIMULATION_STOP       # Simulation ends
EventType.SIMULATION_STEP       # Each step completes
EventType.SIMULATION_ERROR      # Error occurred
EventType.STATE_UPDATE          # State changed (configurable interval)
EventType.SENSOR_READING        # Sensor measurement
EventType.ACTUATOR_OUTPUT       # Actuator command
EventType.CONTROLLER_OUTPUT     # Controller decision
EventType.ALARM_HIGH_TEMP       # High temperature alarm
EventType.ALARM_LOW_TEMP        # Low temperature alarm
```

### Subscribing to Events

```python
from cloudgrow_sim.core.events import EventType, get_event_bus

# Get the event bus
bus = get_event_bus()

# Simple handler
def on_state_update(event):
    data = event.data
    print(f"T_int: {data.get('interior_temperature', 'N/A')}")

bus.subscribe(EventType.STATE_UPDATE, on_state_update)

# Subscribe to all events
def log_all(event):
    print(f"[{event.timestamp}] {event.event_type}: {event.message}")

bus.subscribe_all(log_all)
```

### Collecting Time Series Data

```python
from cloudgrow_sim.simulation.scenarios import create_full_climate_scenario
from cloudgrow_sim.core.events import EventType, get_event_bus
import json

engine = create_full_climate_scenario(duration_hours=24.0)

# Data collection
time_series = []

def collect_data(event):
    data = event.data.copy()
    data['timestamp'] = event.timestamp.isoformat()
    time_series.append(data)

bus = get_event_bus()
bus.clear_handlers()  # Clear any previous handlers
bus.subscribe(EventType.STATE_UPDATE, collect_data)

engine.run()

# Export to JSON
with open('simulation_data.json', 'w') as f:
    json.dump(time_series, f, indent=2)

# Or convert to pandas DataFrame
import pandas as pd
df = pd.DataFrame(time_series)
df['timestamp'] = pd.to_datetime(df['timestamp'])
df.set_index('timestamp', inplace=True)
```

### Event Data Fields

The `STATE_UPDATE` event includes these fields:

| Field | Description | Unit |
|-------|-------------|------|
| `interior_temperature` | Interior air temperature | C |
| `interior_humidity` | Interior relative humidity | % |
| `interior_co2` | Interior CO2 concentration | ppm |
| `exterior_temperature` | Exterior air temperature | C |
| `solar_radiation` | Global horizontal irradiance | W/m^2 |
| `wind_speed` | Wind speed | m/s |

### Event History

```python
# Get historical events
history = bus.get_history(
    event_type=EventType.STATE_UPDATE,
    limit=100
)

for event in history[-5:]:
    print(f"{event.timestamp}: {event.data}")

# Filter by source
sensor_events = bus.get_history(source="dht_int")
```

---

## Interpreting Results

### SimulationStats Object

```python
stats = engine.run()

# Available fields:
stats.steps_completed    # Number of simulation steps
stats.simulation_time    # Total simulated time (timedelta)
stats.wall_time          # Actual elapsed time (timedelta)
stats.avg_step_time      # Average ms per step
```

### Temperature Analysis

```python
# Collect temperature data
temps = []
def collect_temp(event):
    t = event.data.get('interior_temperature')
    if t is not None:
        temps.append(t)

bus.subscribe(EventType.STATE_UPDATE, collect_temp)
engine.run()

# Analysis
import statistics

print(f"Min: {min(temps):.1f}C")
print(f"Max: {max(temps):.1f}C")
print(f"Mean: {statistics.mean(temps):.1f}C")
print(f"Std Dev: {statistics.stdev(temps):.2f}C")

# Temperature stability (how well setpoint is maintained)
setpoint = 22.0
deviations = [abs(t - setpoint) for t in temps]
print(f"Mean deviation from setpoint: {statistics.mean(deviations):.2f}C")
```

### Control Performance Metrics

```python
# Overshoot: How far above setpoint
cooling_setpoint = 26.0
overshoots = [t - cooling_setpoint for t in temps if t > cooling_setpoint]
if overshoots:
    print(f"Max overshoot: {max(overshoots):.1f}C")

# Time in range
in_range = sum(1 for t in temps if 18.0 <= t <= 28.0)
print(f"Time in acceptable range: {in_range / len(temps) * 100:.1f}%")

# Cycling detection (temperature oscillations)
direction_changes = sum(
    1 for i in range(1, len(temps) - 1)
    if (temps[i] - temps[i-1]) * (temps[i+1] - temps[i]) < 0
)
print(f"Temperature direction changes: {direction_changes}")
```

---

## Scenario Comparison

### Summary Table

| Feature | Basic | Full Climate | Winter Heating | Summer Cooling |
|---------|-------|--------------|----------------|----------------|
| **Purpose** | Testing | Production | Cold stress | Heat stress |
| **Floor Area** | 60 m^2 | 300 m^2 | 160 m^2 | 225 m^2 |
| **Sensors** | 1 | 4 | 2 | 2 |
| **Actuators** | 1 | 8 | 2 | 5 |
| **Controllers** | 1 | 3 | 1 | 2 |
| **Modifiers** | 0 | 2 | 1 | 0 |
| **Default Duration** | 24h | 24h | 48h | 48h |
| **Weather** | Mild | Moderate | Cold | Hot/dry |
| **Location** | Virginia | California | Massachusetts | Arizona |
| **Control Strategy** | Simple on/off | PID + staged | PID heating | Staged + evap |

### Performance Characteristics

| Scenario | Steps/sec | Complexity | Physics Load |
|----------|-----------|------------|--------------|
| Basic | ~15,000 | Low | Light |
| Full Climate | ~8,000 | High | Heavy |
| Winter Heating | ~10,000 | Medium | Medium |
| Summer Cooling | ~9,000 | Medium | Medium |

### Choosing the Right Scenario

**Use Basic when:**
- Testing code changes
- Learning the API
- Debugging issues
- Quick validation

**Use Full Climate when:**
- Studying integrated control
- Testing PID tuning
- Evaluating thermal mass
- Commercial applications

**Use Winter Heating when:**
- Testing heating capacity
- Cold climate applications
- Energy analysis
- Backup system validation

**Use Summer Cooling when:**
- Testing evaporative cooling
- Hot/dry climate applications
- Water usage analysis
- Fan staging optimization

---

## Next Steps

- **Custom Scenarios**: See [Creating Custom Scenarios](./creating-custom-scenarios.md) for building your own configurations
- **API Reference**: Consult inline docstrings for complete parameter documentation
- **Examples**: Check `examples/basic_simulation.py` for working code
