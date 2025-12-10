# Greenhouse Climate Simulator - Claude Code Project Prompt

## Project Overview

Create a **production-grade, extensible greenhouse climate simulation framework** in Python. The framework must be fully configurable, support any greenhouse geometry, any combination of sensors/actuators/controllers, and follow ASHRAE standards for all physics calculations.

## Core Requirements

### 1. Architecture Principles

- **Plugin-based component system**: All sensors, actuators, controllers, and climate modifiers must be dynamically registrable/discoverable
- **Configuration-driven**: Greenhouse geometry, location, components, and simulation parameters defined in YAML/JSON
- **ASHRAE-compliant physics**: Psychrometrics, heat transfer, solar calculations per ASHRAE Handbook—Fundamentals
- **Clean separation of concerns**: Physics engine, component registry, simulation engine, controllers, and I/O are independent modules
- **Fully typed**: Use Pydantic for configuration validation, full type hints throughout
- **Well-tested**: Pytest with >80% coverage, property-based testing for physics calculations
- **Linted and formatted**: Use `ruff` for linting, `mypy` for type checking

### 2. Technology Stack

- **Python 3.14+** with `astral uv` for package management
- **Pydantic v2** for configuration and data validation
- **NumPy** for numerical calculations
- **simple-pid** as reference (but implement custom PID with anti-windup, bumpless transfer)
- **InfluxDB client** for time-series data export
- **FastAPI** for web UI API backend
- **Rich** for CLI interface
- **Matplotlib/Plotly** for visualization
- **Pytest + pytest-cov + hypothesis** for testing
- **Home Assistant** for integration with Home Assistant
- **MQTT** for integration with MQTT
- **InfluxDB** for time-series data export
- **Redis** for caching

### 3. Physics Engine Requirements

Must implement ASHRAE-compliant calculations for:

#### Psychrometrics (ASHRAE Handbook—Fundamentals Chapter 1)
- Saturation pressure (over water and ice)
- Humidity ratio from temperature and RH
- Wet-bulb temperature (iterative calculation)
- Dew point temperature
- Enthalpy of moist air
- Air density
- Adiabatic mixing of air streams

#### Heat Transfer (ASHRAE Chapters 4, 25, 26)
- Conduction through covering materials (U-value based)
- Natural convection (Grashof/Rayleigh correlations)
- Forced convection (Reynolds correlations)
- Mixed convection (Churchill-Usagi)
- Radiation exchange (Stefan-Boltzmann with view factors)
- Sky temperature estimation (Berdahl-Fromberg)
- Ground temperature at depth (sinusoidal model)
- Infiltration heat loss (sensible + latent)
- Ventilation heat exchange

#### Solar Radiation (ASHRAE Chapter 14)
- Solar position (altitude, azimuth, zenith) for any location/time
- Extraterrestrial radiation
- Direct normal irradiance (atmospheric transmittance model)
- Diffuse horizontal radiation (Erbs correlation)
- Radiation on tilted surfaces
- PAR (Photosynthetically Active Radiation) conversion

### 4. Component System Architecture

Design a plugin-based component registry with these base types:

```
Component (abstract base)
├── Sensor (readable, produces measurements)
│   ├── TemperatureSensor
│   ├── HumiditySensor
│   ├── CombinedTempHumiditySensor
│   ├── CO2Sensor
│   ├── SolarRadiationSensor
│   ├── PARSensor
│   ├── WindSensor
│   ├── SoilMoistureSensor
│   ├── PressureSensor
│   └── [extensible for custom sensors]
│
├── Actuator (controllable, modifies climate)
│   ├── ExhaustFan (variable speed, staged)
│   ├── IntakeFan
│   ├── CirculationFan
│   ├── Vent (roof, side - natural ventilation)
│   ├── Curtain (shade, thermal, blackout)
│   ├── Heater (unit, radiant, hot water)
│   ├── Cooler (evaporative pad, fogging, HVAC)
│   ├── Humidifier
│   ├── Dehumidifier
│   ├── CO2Injector
│   ├── Lighting (supplemental, photoperiod)
│   └── [extensible for robotics, custom actuators]
│
├── Controller (computes control signals)
│   ├── PIDController (with anti-windup, bumpless transfer)
│   ├── StagedController (multi-stage on/off)
│   ├── HysteresisController (deadband)
│   ├── ScheduleController (time-based)
│   ├── MPCController (model predictive - future)
│   └── [extensible for ML-based controllers]
│
└── ClimateModifier (passive elements affecting climate)
    ├── CoveringMaterial (poly, glass, polycarbonate)
    ├── ThermalMass (concrete floor, water barrels)
    ├── Crop (transpiration, CO2 uptake - future)
    └── [extensible]
```

#### Component Registration Pattern
```python
# Components self-register via decorators
@register_component("sensor", "temperature")
class TemperatureSensor(Sensor):
    ...

# Or via entry points for external plugins
[project.entry-points."greenhouse_simulator.components"]
my_custom_sensor = "my_package:CustomSensor"
```

### 5. Configuration System

YAML-based configuration for complete greenhouse definition:

```yaml
# Example: greenhouse_config.yaml
simulation:
  name: "Epic Pastures Greenhouse"
  time_step: 1.0  # seconds
  duration: 86400  # 24 hours
  start_time: "2025-06-15T06:00:00"

location:
  latitude: 37.3
  longitude: -78.4
  elevation: 130  # meters
  timezone: "America/New_York"

geometry:
  type: "gable"  # gable, quonset, gothic, venlo, custom
  length: 30.0  # meters (N-S)
  width: 10.0   # meters (E-W)
  height_ridge: 5.0
  height_eave: 3.0
  orientation: 0  # degrees from north

covering:
  material: "double_polyethylene"
  # Or custom properties:
  # transmittance_solar: 0.77
  # transmittance_par: 0.75
  # u_value: 4.0

components:
  sensors:
    - type: "temp_humidity"
      name: "interior_main"
      location: "interior"
      position: [15.0, 5.0, 2.0]
      noise_std_dev: 0.1
    
    - type: "temp_humidity"
      name: "exterior"
      location: "exterior"
      
    - type: "solar_radiation"
      name: "pyranometer"
      location: "exterior"

  actuators:
    - type: "exhaust_fan"
      name: "main_fan"
      max_flow_rate: 5.0  # m³/s
      power_consumption: 500  # W
      controller: "fan_pid"
      
    - type: "curtain"
      name: "shade_ns"
      orientation: "north_south"
      shade_factor: 0.5
      controller: "shade_controller"
      
    - type: "curtain"
      name: "thermal_ew"
      orientation: "east_west"
      thermal_transmittance: 0.3
      controller: "curtain_pid"
      
    - type: "vent"
      name: "roof_vent_east"
      location: "roof"
      width: 1.0
      height: 0.5
      controller: "vent_controller"

  controllers:
    - type: "pid"
      name: "fan_pid"
      setpoint_source: "schedule"  # or fixed value
      process_variable: "interior_main.temperature"
      output_target: "main_fan.power_level"
      kp: 0.5
      ki: 0.1
      kd: 0.05
      output_limits: [0.0, 1.0]
      anti_windup: true
      
    - type: "staged"
      name: "shade_controller"
      process_variable: "pyranometer.solar_radiation"
      output_target: "shade_ns.position"
      stages:
        - threshold: 400
          output: 0.25
        - threshold: 600
          output: 0.5
        - threshold: 800
          output: 0.75
        - threshold: 1000
          output: 1.0

setpoints:
  schedules:
    temperature:
      - time: "06:00"
        value: 18.0
      - time: "08:00"
        value: 24.0
      - time: "18:00"
        value: 22.0
      - time: "22:00"
        value: 16.0
    
    humidity:
      default: 65.0
      max: 85.0

weather:
  source: "file"  # file, api, synthetic
  file: "weather_data.csv"
  # Or API:
  # source: "open_meteo"
  # Or synthetic:
  # source: "synthetic"
  # typical_summer: true

output:
  influxdb:
    enabled: true
    url: "http://localhost:8086"
    org: "epic_pastures"
    bucket: "greenhouse_sim"
    
  csv:
    enabled: true
    path: "output/simulation_results.csv"
    
  plots:
    enabled: true
    path: "output/plots/"
```

### 6. Simulation Engine

The core simulation loop must:

1. **Initialize** from configuration
2. **Load weather data** (file, API, or synthetic generation)
3. **Execute time-stepped simulation**:
   ```
   for each time step dt:
       1. Update exterior conditions from weather data
       2. Read all sensors
       3. Execute all controllers (compute outputs)
       4. Apply actuator commands
       5. Calculate physics:
          - Solar gain through covering
          - Conduction losses
          - Ventilation/infiltration exchange
          - Actuator effects (heating, cooling, humidity)
       6. Update interior state
       7. Log/emit telemetry
   ```
4. **Support real-time factor** (1x, 10x, 100x, or as-fast-as-possible)
5. **Emit events** for state changes, alarms, controller actions
6. **Checkpoint/restore** simulation state

### 7. Interfaces

#### CLI (using Rich)
```bash
# Run simulation
greenhouse-sim run config.yaml --duration 24h --output results/

# Validate configuration
greenhouse-sim validate config.yaml

# List available components
greenhouse-sim components list

# Generate synthetic weather
greenhouse-sim weather generate --location 37.3,-78.4 --date 2025-06-15 --output weather.csv

# Interactive mode
greenhouse-sim interactive config.yaml
```

#### Web UI API (FastAPI)
- `GET /api/simulation/status` - Current state
- `POST /api/simulation/start` - Start with config
- `POST /api/simulation/stop` - Stop simulation
- `PUT /api/simulation/setpoint/{controller}` - Adjust setpoint
- `GET /api/components` - List components
- `GET /api/telemetry/stream` - WebSocket for real-time data
- `GET /api/history` - Query historical data

#### Programmatic API
```python
from greenhouse_simulator import Greenhouse, SimulationEngine
from greenhouse_simulator.components import ExhaustFan, PIDController

# Load from config
greenhouse = Greenhouse.from_yaml("config.yaml")

# Or build programmatically
greenhouse = Greenhouse(
    geometry=GreenhouseGeometry(length=30, width=10, ...),
    location=Location(latitude=37.3, longitude=-78.4),
)

# Add components
fan = ExhaustFan(name="main_fan", max_flow_rate=5.0)
greenhouse.add_component(fan)

controller = PIDController(
    name="temp_control",
    kp=0.5, ki=0.1, kd=0.05,
    setpoint=24.0,
)
greenhouse.add_component(controller)
controller.connect(
    process_variable=greenhouse.sensors["interior_temp"],
    output=fan,
)

# Run simulation
engine = SimulationEngine(greenhouse)
results = engine.run(duration=timedelta(hours=24))

# Or step manually
engine.initialize()
while engine.time < end_time:
    state = engine.step()
    print(f"T={state.interior.temperature:.1f}°C")
```

### 8. Project Structure

```
greenhouse-simulator/
├── pyproject.toml
├── README.md
├── LICENSE
├── .gitignore
├── .pre-commit-config.yaml
│
├── src/
│   └── greenhouse_simulator/
│       ├── __init__.py
│       ├── py.typed
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── base.py          # Base classes, protocols, types
│       │   ├── state.py         # GreenhouseState, geometry, covering
│       │   ├── registry.py      # Component registry, plugin discovery
│       │   ├── config.py        # Configuration loading/validation
│       │   └── events.py        # Event system
│       │
│       ├── physics/
│       │   ├── __init__.py
│       │   ├── psychrometrics.py
│       │   ├── heat_transfer.py
│       │   ├── solar.py
│       │   ├── ventilation.py
│       │   └── constants.py     # ASHRAE constants
│       │
│       ├── components/
│       │   ├── __init__.py
│       │   ├── sensors/
│       │   │   ├── __init__.py
│       │   │   ├── base.py
│       │   │   ├── temperature.py
│       │   │   ├── humidity.py
│       │   │   ├── radiation.py
│       │   │   └── ...
│       │   ├── actuators/
│       │   │   ├── __init__.py
│       │   │   ├── base.py
│       │   │   ├── fans.py
│       │   │   ├── vents.py
│       │   │   ├── curtains.py
│       │   │   ├── heating.py
│       │   │   ├── cooling.py
│       │   │   └── ...
│       │   └── modifiers/
│       │       ├── __init__.py
│       │       ├── covering.py
│       │       └── thermal_mass.py
│       │
│       ├── controllers/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── pid.py           # Full-featured PID
│       │   ├── staged.py
│       │   ├── hysteresis.py
│       │   ├── schedule.py
│       │   └── mpc.py           # Model Predictive Control (future)
│       │
│       ├── simulation/
│       │   ├── __init__.py
│       │   ├── engine.py        # Main simulation loop
│       │   ├── weather.py       # Weather data loading/generation
│       │   └── scenarios.py     # Pre-built scenarios
│       │
│       ├── io/
│       │   ├── __init__.py
│       │   ├── influxdb.py
│       │   ├── csv_export.py
│       │   └── plotting.py
│       │
│       ├── api/
│       │   ├── __init__.py
│       │   ├── app.py           # FastAPI application
│       │   ├── routes/
│       │   └── schemas.py
│       │
│       └── cli/
│           ├── __init__.py
│           └── main.py          # Rich CLI
│
├── tests/
│   ├── conftest.py
│   ├── test_physics/
│   │   ├── test_psychrometrics.py
│   │   ├── test_heat_transfer.py
│   │   └── test_solar.py
│   ├── test_components/
│   ├── test_controllers/
│   ├── test_simulation/
│   └── test_integration/
│
├── examples/
│   ├── basic_greenhouse.yaml
│   ├── commercial_tomato.yaml
│   ├── high_tunnel.yaml
│   └── notebooks/
│       └── simulation_analysis.ipynb
│
└── docs/
    ├── getting_started.md
    ├── configuration.md
    ├── components.md
    ├── physics.md
    └── extending.md
```

### 9. Implementation Phases

#### Phase 1: Foundation (Core + Physics)
- [ ] Project setup with uv, pyproject.toml, pre-commit
- [ ] Core base classes and protocols
- [ ] Greenhouse state management
- [ ] Configuration system with Pydantic
- [ ] Component registry with plugin discovery
- [ ] ASHRAE psychrometrics (full implementation)
- [ ] Solar position and radiation calculations
- [ ] Heat transfer calculations
- [ ] Unit tests for all physics (validate against ASHRAE tables)

#### Phase 2: Components
- [ ] Sensor base class with noise modeling
- [ ] All sensor types (temp, humidity, CO2, solar, wind, etc.)
- [ ] Actuator base class with response dynamics
- [ ] Fan implementations (exhaust, intake, circulation)
- [ ] Vent implementations (roof, side, natural ventilation)
- [ ] Curtain implementations (shade, thermal)
- [ ] Heater implementations
- [ ] Cooler implementations
- [ ] Unit tests for all components

#### Phase 3: Controllers
- [ ] PID controller with anti-windup, bumpless transfer, derivative filter
- [ ] Staged controller
- [ ] Hysteresis controller
- [ ] Schedule-based controller
- [ ] Controller-actuator binding system
- [ ] Setpoint scheduling
- [ ] Unit tests and tuning validation

#### Phase 4: Simulation Engine
- [ ] Core simulation loop
- [ ] Weather data loading (CSV, synthetic)
- [ ] Time management (real-time factor, acceleration)
- [ ] State checkpointing
- [ ] Event emission system
- [ ] Integration tests with full scenarios

#### Phase 5: I/O and Interfaces
- [ ] InfluxDB integration
- [ ] CSV export
- [ ] Plotting utilities
- [ ] Rich CLI implementation
- [ ] FastAPI web API
- [ ] WebSocket streaming

#### Phase 6: Advanced Features
- [ ] Open-Meteo weather API integration
- [ ] Model Predictive Control (MPC) foundation
- [ ] Crop transpiration models (extensible)
- [ ] Multi-zone greenhouse support
- [ ] Scenario library
- [ ] Performance optimization

### 10. Testing Requirements

- **Unit tests**: Every physics function validated against ASHRAE reference values
- **Property-based tests**: Use Hypothesis for edge cases in psychrometrics
- **Integration tests**: Full simulation scenarios with known outcomes
- **Performance tests**: Ensure real-time simulation is achievable
- **Configuration tests**: Validate all example configs load correctly

### 11. Documentation Requirements

- Docstrings following Google style
- README with quick start
- Configuration reference
- Component catalog with parameters
- Physics documentation with equations and references
- Extension guide for custom components

### 12. Quality Gates

Before considering any phase complete:
- [ ] All tests passing
- [ ] `ruff check` passes with no errors
- [ ] `mypy --strict` passes
- [ ] Test coverage >80%
- [ ] Documentation updated

---

## Deliverable

Produce a detailed **implementation plan** as a markdown document that includes:

1. **Dependency analysis**: What order must modules be built?
2. **Detailed task breakdown**: For each phase, specific files and functions to create
3. **Test strategy**: What tests for each module, what reference data needed
4. **Risk assessment**: What's complex, what might need iteration?
5. **Time estimates**: Rough estimates for each phase
6. **Decision points**: Where are design choices needed?

Focus on Phase 1-3 first with full detail, Phases 4-6 at higher level.

---

## Context

This simulator is for Epic Pastures greenhouse in Farmville, VA. The operator has:
- Curtains running north-south
- Curtains running east-west (PID controlled)
- Exhaust fan (PID controlled)
- Interior and exterior climate monitoring
- Plans to add: additional shade, heating, cooling, and potentially robotics

The goal is a flexible framework that can model any greenhouse configuration, support controller tuning, generate training data for ML models, and eventually run as a digital twin alongside the real greenhouse.

Reference implementations to review:
- GES (Greenhouse Energy Simulation): https://github.com/EECi/GES
- Greenhouses Modelica library: https://greenhouses-library.readthedocs.io/
- GDGCM (Gembloux Dynamic Greenhouse Climate Model)
- Vanthoor thesis: "A model-based greenhouse design method" (Wageningen, 2011)
