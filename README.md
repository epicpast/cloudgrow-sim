# cloudgrow-sim

An ASHRAE-compliant greenhouse climate simulation framework. Simulate temperature, humidity, ventilation, and heating/cooling systems with physics-based models.

## Features

- **ASHRAE-compliant physics**: Psychrometrics, solar radiation, heat transfer, and ventilation calculations
- **Component system**: Sensors, actuators, controllers, and modifiers with plugin architecture
- **YAML configuration**: Define scenarios without writing code
- **CLI interface**: Run simulations from the command line
- **Multiple output formats**: Console, CSV, and JSON

## Installation

```bash
# Using uv (recommended)
uv add cloudgrow-sim

# Using pip
pip install cloudgrow-sim
```

## Quick Start

### Command Line Interface

The `cgsim` CLI provides easy access to simulations:

```bash
# Run a built-in scenario
cgsim run --scenario basic

# Run your own YAML configuration
cgsim run my-greenhouse.yaml

# List available built-in scenarios
cgsim list

# Generate a starter configuration
cgsim init "My Greenhouse" -o my-greenhouse.yaml

# Validate a configuration file
cgsim validate my-greenhouse.yaml
```

### CLI Options

```bash
# Override simulation duration (in hours)
cgsim run config.yaml --duration 48

# Override time step (in seconds)
cgsim run config.yaml --time-step 30

# Output results to directory
cgsim run config.yaml --output-dir ./results

# Choose output format (console, csv, json)
cgsim run config.yaml --format json --output-dir ./results

# Run quietly (suppress progress output)
cgsim run config.yaml --quiet
```

### Python API

```python
from cloudgrow_sim.core.config import load_config
from cloudgrow_sim.simulation.factory import create_engine_from_config

# Load a YAML configuration
config = load_config("my-greenhouse.yaml")

# Create and run the simulation
engine = create_engine_from_config(config)
stats = engine.run()

print(f"Completed {stats.steps_completed} steps")
print(f"Simulation time: {stats.simulation_time}")
```

## YAML Configuration

Define greenhouse scenarios in YAML:

```yaml
name: "My Greenhouse"
time_step: 60.0       # seconds
duration: 86400.0     # 24 hours

location:
  latitude: 37.5
  longitude: -77.4
  elevation: 50.0
  timezone: "America/New_York"

geometry:
  type: gable
  length: 10.0
  width: 6.0
  height_ridge: 3.5
  height_eave: 2.4

components:
  sensors:
    - type: temperature
      name: temp_interior
      location: interior

  actuators:
    - type: exhaust_fan
      name: vent_fan
      controller: temp_control
      max_flow_rate: 1.0
      power_consumption: 500.0

  controllers:
    - type: hysteresis
      name: temp_control
      process_variable: temp_interior.temperature
      setpoint: 28.0
      hysteresis: 2.0
```

See [docs/yaml-configuration.md](docs/yaml-configuration.md) for the complete schema reference.

## Built-in Scenarios

| Scenario | Description |
|----------|-------------|
| `basic` | Simple hobby greenhouse with one fan |
| `full-climate` | Complete climate control system |
| `winter-heating` | Cold weather heating stress test |
| `summer-cooling` | Hot weather cooling stress test |

## Development

```bash
# Clone the repository
git clone https://github.com/OWNER/cloudgrow-sim.git
cd cloudgrow-sim

# Install with dev dependencies
uv sync

# Run tests
make test

# Run all quality checks
make quality
```

## Documentation

- [User Guide](docs/user-guide.md) - Getting started and tutorials
- [CLI Reference](docs/cli-reference.md) - Complete CLI documentation
- [YAML Configuration](docs/yaml-configuration.md) - Configuration schema
- [Scenarios Guide](docs/scenarios.md) - Using and creating scenarios
- [Quick Reference](docs/quick-reference.md) - Cheat sheet

## License

MIT
