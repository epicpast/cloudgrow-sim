# YAML Configuration Reference

This document describes the complete YAML schema for cloudgrow-sim configuration files.

## Overview

Configuration files define greenhouse simulations declaratively. A minimal config requires only `name`, `location`, and `geometry`:

```yaml
name: "My Greenhouse"
location:
  latitude: 37.5
  longitude: -77.4
geometry:
  length: 10.0
  width: 6.0
  height_ridge: 3.5
  height_eave: 2.4
```

## Complete Schema

### Root Properties

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `name` | string | required | Scenario name |
| `time_step` | float | 60.0 | Simulation time step in seconds |
| `duration` | float | 86400.0 | Simulation duration in seconds |
| `start_time` | string | now | ISO 8601 datetime (e.g., "2025-01-15T06:00:00Z") |

```yaml
name: "24-Hour Simulation"
time_step: 60.0           # 1-minute steps
duration: 86400.0         # 24 hours (in seconds)
start_time: "2025-06-21T06:00:00Z"
```

---

### location

Geographic coordinates for solar calculations.

| Property | Type | Default | Valid Range | Description |
|----------|------|---------|-------------|-------------|
| `latitude` | float | required | -90 to 90 | Degrees north |
| `longitude` | float | required | -180 to 180 | Degrees east |
| `elevation` | float | 0.0 | ≥0 | Meters above sea level |
| `timezone` | string | "UTC" | - | IANA timezone name |

```yaml
location:
  latitude: 37.5         # Richmond, VA
  longitude: -77.4
  elevation: 50.0        # 50m above sea level
  timezone: "America/New_York"
```

**Common Timezones:**
- `America/New_York`, `America/Chicago`, `America/Denver`, `America/Los_Angeles`
- `Europe/London`, `Europe/Paris`, `Europe/Berlin`
- `Asia/Tokyo`, `Asia/Shanghai`, `Australia/Sydney`

---

### geometry

Physical dimensions of the greenhouse.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `type` | string | "gable" | Structure type |
| `length` | float | required | North-south dimension (m) |
| `width` | float | required | East-west dimension (m) |
| `height_ridge` | float | required | Peak height (m) |
| `height_eave` | float | required | Sidewall height (m) |
| `orientation` | float | 0.0 | Rotation from north (degrees) |

**Geometry Types:**
- `gable` - Traditional peaked roof
- `quonset` - Curved/hoop structure
- `gothic` - Pointed arch roof
- `venlo` - Multi-span commercial
- `high_tunnel` - Simple hoop house

```yaml
geometry:
  type: gable
  length: 30.0           # 30m long
  width: 10.0            # 10m wide
  height_ridge: 5.0      # 5m at peak
  height_eave: 3.0       # 3m sidewalls
  orientation: 0.0       # Ridge runs N-S
```

**Note:** `height_eave` must be less than `height_ridge`.

---

### covering

Greenhouse covering material properties.

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `material` | string | "double_polyethylene" | Predefined material name |

**OR custom properties:**

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `transmittance_solar` | float | 0.77 | Solar radiation transmittance (0-1) |
| `transmittance_par` | float | 0.70 | PAR transmittance (0-1) |
| `transmittance_thermal` | float | 0.10 | Thermal IR transmittance (0-1) |
| `u_value` | float | 4.0 | Heat transfer coefficient (W/m²K) |
| `reflectance_solar` | float | 0.10 | Solar reflectance (0-1) |

**Predefined Materials:**

| Material Key | Solar Trans. | U-Value | Use Case |
|--------------|--------------|---------|----------|
| `single_glass` | 0.85 | 5.8 | Traditional glass |
| `double_glass` | 0.75 | 3.0 | Insulated glass |
| `single_polyethylene` | 0.87 | 6.0 | Budget film |
| `double_polyethylene` | 0.77 | 4.0 | Standard film |
| `polycarbonate_twin` | 0.78 | 3.5 | Rigid panels |
| `polycarbonate_triple` | 0.71 | 2.5 | High insulation |
| `acrylic_double` | 0.83 | 3.2 | Clear panels |

```yaml
# Use predefined material
covering:
  material: double_polyethylene

# OR custom properties
covering:
  transmittance_solar: 0.80
  transmittance_par: 0.78
  u_value: 3.5
```

---

### components

The components section defines sensors, actuators, controllers, and modifiers.

```yaml
components:
  sensors: []
  actuators: []
  controllers: []
  modifiers: []
```

---

### components.sensors

Sensors read values from the greenhouse state.

**Common Properties (all sensors):**

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `type` | string | required | Sensor type |
| `name` | string | required | Unique identifier |
| `enabled` | bool | true | Whether sensor is active |
| `location` | string | "interior" | Measurement location |

#### temperature

```yaml
- type: temperature
  name: temp_interior
  location: interior       # or "exterior"
  noise_std_dev: 0.1       # Gaussian noise (°C)
```

#### humidity

```yaml
- type: humidity
  name: rh_interior
  location: interior
  noise_std_dev: 2.0       # Gaussian noise (%)
```

#### temp_humidity

Combined DHT22-style sensor.

```yaml
- type: temp_humidity
  name: dht_interior
  location: interior
  temp_noise_std_dev: 0.2
  humidity_noise_std_dev: 2.0
```

#### solar_radiation

Pyranometer for global horizontal irradiance.

```yaml
- type: solar_radiation
  name: pyranometer
  location: exterior
  noise_std_dev: 5.0       # W/m²
```

#### par

Photosynthetically Active Radiation sensor.

```yaml
- type: par
  name: par_sensor
  location: interior
  noise_std_dev: 5.0       # µmol/m²/s
```

#### co2

CO2 concentration sensor.

```yaml
- type: co2
  name: co2_sensor
  location: interior
  noise_std_dev: 10.0      # ppm
```

#### wind

Wind speed and direction sensor.

```yaml
- type: wind
  name: anemometer
  speed_noise_std_dev: 0.2      # m/s
  direction_noise_std_dev: 5.0  # degrees
```

---

### components.actuators

Actuators modify the greenhouse climate.

**Common Properties (all actuators):**

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `type` | string | required | Actuator type |
| `name` | string | required | Unique identifier |
| `enabled` | bool | true | Whether actuator is active |
| `controller` | string | - | Controller name to bind |

#### exhaust_fan

Removes air from greenhouse.

```yaml
- type: exhaust_fan
  name: exhaust_1
  controller: cooling_control    # Optional binding
  max_flow_rate: 5.0             # m³/s at full speed
  power_consumption: 500.0       # Watts at full speed
```

#### intake_fan

Brings outside air in.

```yaml
- type: intake_fan
  name: intake_1
  max_flow_rate: 3.0
  power_consumption: 300.0
```

#### circulation_fan

Internal air circulation (no ventilation).

```yaml
- type: circulation_fan
  name: circ_fan
  power_consumption: 100.0
```

#### unit_heater

Forced-air heater.

```yaml
- type: unit_heater
  name: main_heater
  controller: heating_pid
  heating_capacity: 15000.0      # Watts
  efficiency: 0.90               # Combustion efficiency
```

#### radiant_heater

Infrared/radiant heater.

```yaml
- type: radiant_heater
  name: radiant_1
  heating_capacity: 10000.0
  radiant_fraction: 0.7          # 70% radiant, 30% convective
```

#### evaporative_pad

Evaporative cooling system.

```yaml
- type: evaporative_pad
  name: evap_pad
  controller: evap_control
  pad_area: 6.0                  # m²
  saturation_efficiency: 0.85    # 0-1
```

#### fogger

Fog/mist cooling system.

```yaml
- type: fogger
  name: fogger
  flow_rate: 5.0                 # L/h water
  droplet_size: 10.0             # microns
```

#### roof_vent

Natural ventilation via roof opening.

```yaml
- type: roof_vent
  name: roof_vent_north
  width: 2.0                     # m
  height: 0.5                    # m (max opening)
  height_above_floor: 4.5        # m (for stack effect)
  discharge_coefficient: 0.6     # 0-1
```

#### side_vent

Natural ventilation via sidewall opening.

```yaml
- type: side_vent
  name: side_vent_east
  width: 3.0
  height: 1.0
  height_above_floor: 1.5
```

#### shade_curtain

Retractable shade system.

```yaml
- type: shade_curtain
  name: shade_ns
  shade_factor: 0.5              # Fraction blocked when closed
```

#### thermal_curtain

Retractable thermal/energy curtain.

```yaml
- type: thermal_curtain
  name: thermal_curtain
  r_value: 1.5                   # m²K/W thermal resistance
```

---

### components.controllers

Controllers compute output signals for actuators.

**Common Properties (all controllers):**

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `type` | string | required | Controller type |
| `name` | string | required | Unique identifier |
| `enabled` | bool | true | Whether controller is active |
| `process_variable` | string | required | Sensor reading to monitor |

**Process Variable Format:** `sensor_name.reading_name`

Examples:
- `temp_interior.temperature`
- `dht_interior.humidity`
- `pyranometer.solar_radiation`

#### pid

Proportional-Integral-Derivative controller.

```yaml
- type: pid
  name: cooling_pid
  process_variable: temp_interior.temperature
  setpoint: 24.0
  kp: 0.5                        # Proportional gain
  ki: 0.1                        # Integral gain
  kd: 0.05                       # Derivative gain
  output_limits: [0.0, 1.0]      # Min/max output
  reverse_acting: true           # True for cooling
```

**Tuning Tips:**
- Start with `kp` only, add `ki` for steady-state error
- `kd` reduces overshoot but can amplify noise
- `reverse_acting: true` for cooling (output increases when hot)
- `reverse_acting: false` for heating (output increases when cold)

#### hysteresis

Simple on/off control with deadband.

```yaml
- type: hysteresis
  name: heater_control
  process_variable: temp_interior.temperature
  setpoint: 18.0
  hysteresis: 2.0                # Total deadband width
  reverse_acting: false          # False for heating
  on_output: 1.0                 # Output when ON
  off_output: 0.0                # Output when OFF
```

**Heating mode (reverse_acting: false):**
- ON when temp < setpoint - hysteresis/2 (17°C)
- OFF when temp > setpoint + hysteresis/2 (19°C)

**Cooling mode (reverse_acting: true):**
- ON when temp > setpoint + hysteresis/2
- OFF when temp < setpoint - hysteresis/2

#### staged

Multi-stage equipment control.

```yaml
- type: staged
  name: fan_staging
  process_variable: temp_interior.temperature
  stages:
    - [26.0, 0.33]               # Stage 1: 33% at 26°C
    - [28.0, 0.66]               # Stage 2: 66% at 28°C
    - [30.0, 1.00]               # Stage 3: 100% at 30°C
  hysteresis: 1.0                # Deadband per stage
```

#### schedule

Time-based setpoint control.

```yaml
- type: schedule
  name: temp_schedule
  process_variable: temp_interior.temperature
  interpolate: true              # Smooth transitions
  entries:
    - ["06:00", 18.0]           # 6 AM: 18°C
    - ["09:00", 24.0]           # 9 AM: 24°C
    - ["17:00", 22.0]           # 5 PM: 22°C
    - ["21:00", 16.0]           # 9 PM: 16°C
```

---

### components.modifiers

Passive elements affecting climate.

#### covering

Material covering modifier (alternative to root `covering` section).

```yaml
- type: covering
  name: covering
  material: double_polyethylene
```

#### thermal_mass

Heat storage element (e.g., water barrels, concrete floor).

```yaml
- type: thermal_mass
  name: water_barrels
  mass: 2000.0                   # kg
  specific_heat: 4186.0          # J/(kg·K) - water
  surface_area: 15.0             # m² exposed
  initial_temperature: 20.0      # °C starting temp
```

**Typical Specific Heat Values:**
- Water: 4186 J/(kg·K)
- Concrete: 880 J/(kg·K)
- Soil: 800-1500 J/(kg·K)

---

### weather

Weather data source configuration.

#### Synthetic Weather

Generate realistic patterns mathematically.

```yaml
weather:
  source: synthetic
  base_temperature: 20.0         # Annual mean (°C)
  temperature_amplitude: 10.0    # Daily swing (°C)
  humidity_mean: 60.0            # Mean RH (%)
  solar_max: 1000.0              # Peak solar (W/m²)
  wind_mean: 2.5                 # Mean wind (m/s)
```

#### CSV Weather

Load from historical data file.

```yaml
weather:
  source: csv
  file: "weather_data.csv"
  timestamp_column: "datetime"
  temperature_column: "temp_c"
  humidity_column: "rh"
  solar_column: "ghi"
  wind_column: "wind_ms"
  timestamp_format: "%Y-%m-%d %H:%M:%S"
```

---

## Complete Example

```yaml
# Full Climate Control Example
name: "Full Climate Control"
time_step: 60.0
duration: 86400.0
start_time: "2025-06-21T06:00:00Z"

location:
  latitude: 37.5
  longitude: -77.4
  elevation: 50.0
  timezone: "America/New_York"

geometry:
  type: gable
  length: 30.0
  width: 10.0
  height_ridge: 5.0
  height_eave: 3.0
  orientation: 0.0

covering:
  material: double_polyethylene

components:
  sensors:
    - type: temp_humidity
      name: dht_interior
      location: interior
      temp_noise_std_dev: 0.2
      humidity_noise_std_dev: 2.0

    - type: temperature
      name: temp_exterior
      location: exterior

    - type: solar_radiation
      name: pyranometer
      location: exterior

  actuators:
    - type: exhaust_fan
      name: exhaust_1
      controller: cooling_pid
      max_flow_rate: 5.0
      power_consumption: 500.0

    - type: exhaust_fan
      name: exhaust_2
      controller: cooling_pid
      max_flow_rate: 5.0
      power_consumption: 500.0

    - type: unit_heater
      name: main_heater
      controller: heating_control
      heating_capacity: 15000.0
      efficiency: 0.90

    - type: evaporative_pad
      name: evap_pad
      controller: evap_control
      pad_area: 6.0
      saturation_efficiency: 0.85

  controllers:
    - type: pid
      name: cooling_pid
      process_variable: dht_interior.temperature
      setpoint: 26.0
      kp: 0.5
      ki: 0.1
      kd: 0.05
      output_limits: [0.0, 1.0]
      reverse_acting: true

    - type: hysteresis
      name: heating_control
      process_variable: dht_interior.temperature
      setpoint: 18.0
      hysteresis: 2.0
      reverse_acting: false

    - type: hysteresis
      name: evap_control
      process_variable: dht_interior.temperature
      setpoint: 30.0
      hysteresis: 2.0
      reverse_acting: true

  modifiers:
    - type: thermal_mass
      name: water_barrels
      mass: 2000.0
      specific_heat: 4186.0
      surface_area: 15.0
      initial_temperature: 20.0

weather:
  source: synthetic
  base_temperature: 22.0
  temperature_amplitude: 8.0
```

---

## Validation

Use `cgsim validate` to check configuration files:

```bash
cgsim validate config.yaml
```

Common validation errors:
- `latitude` must be between -90 and 90
- `longitude` must be between -180 and 180
- `height_eave` cannot exceed `height_ridge`
- Component `name` must be unique within type
- `process_variable` must reference valid sensor.reading
