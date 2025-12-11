# Scenarios Guide

Scenarios are pre-configured greenhouse simulations that can be run directly from the command line or used as starting points for custom configurations.

## Built-in Scenarios

cloudgrow-sim includes four built-in scenarios covering common use cases:

| Scenario | Description | Duration | Key Features |
|----------|-------------|----------|--------------|
| `basic` | Simple hobby greenhouse | 24 hours | 1 sensor, 1 fan, hysteresis control |
| `full-climate` | Commercial with full HVAC | 24 hours | 4 sensors, 8 actuators, 3 controllers |
| `winter-heating` | Cold weather stress test | 48 hours | -2°C exterior, dual heaters, PID control |
| `summer-cooling` | Hot weather stress test | 48 hours | 38°C exterior, staged fans, evap cooling |

### Using Built-in Scenarios

```bash
# List available scenarios
cgsim list

# Run a scenario
cgsim run --scenario basic
cgsim run -s full-climate
cgsim run -s winter-heating
cgsim run -s summer-cooling
```

---

## Scenario Details

### basic

A minimal hobby greenhouse setup for learning and testing.

**Location:** Richmond, VA (37.5°N, -77.4°W)
**Structure:** 10m × 6m gable greenhouse
**Duration:** 24 hours

**Components:**
- 1 interior temperature sensor
- 1 exhaust fan (1 m³/s capacity)
- Hysteresis controller (setpoint 28°C)

**Use Cases:**
- Learning the simulation framework
- Quick validation tests
- Performance benchmarks

```bash
cgsim run -s basic
```

### full-climate

A commercial greenhouse with comprehensive climate control.

**Location:** Richmond, VA
**Structure:** 30m × 10m gable greenhouse
**Duration:** 24 hours

**Components:**
- Combined temp/humidity sensor
- Exterior temperature sensor
- PAR sensor
- Solar radiation sensor
- 3 exhaust fans (staged)
- 1 circulation fan
- 1 evaporative pad
- 1 unit heater
- 2 roof vents
- Cooling PID controller
- Heating hysteresis controller
- Fan staging controller
- Thermal mass (water barrels)
- Covering material modifier

**Use Cases:**
- Testing complete HVAC systems
- Studying controller interactions
- Energy consumption analysis

```bash
cgsim run -s full-climate
```

### winter-heating

A cold weather stress test focused on heating capacity.

**Location:** Boston, MA (42.3°N, -71.1°W)
**Structure:** 20m × 8m gable with polycarbonate covering
**Duration:** 48 hours
**Weather:** -2°C base, 5°C amplitude (synthetic)

**Components:**
- Interior and exterior temperature sensors
- 25 kW main heater
- 15 kW backup heater
- PID heating controller (setpoint 18°C)
- Polycarbonate covering for insulation

**Use Cases:**
- Heating system sizing
- Cold weather performance validation
- Insulation effectiveness studies

```bash
cgsim run -s winter-heating
```

### summer-cooling

A hot weather stress test focused on cooling capacity.

**Location:** Phoenix, AZ (33.4°N, -112.0°W)
**Structure:** 25m × 9m quonset with double polyethylene
**Duration:** 48 hours
**Weather:** 38°C base, 12°C amplitude (synthetic)

**Components:**
- Combined temp/humidity sensor
- Solar radiation sensor
- 4 high-capacity exhaust fans (3 m³/s each)
- Large evaporative pad (12 m², 85% efficiency)
- 4-stage fan controller
- Evaporative pad hysteresis controller

**Use Cases:**
- Cooling system sizing
- Evaporative cooling effectiveness
- Hot climate performance validation

```bash
cgsim run -s summer-cooling
```

---

## Creating Custom Scenarios

### From Scratch

Use `cgsim init` to generate a starter configuration:

```bash
cgsim init "My Custom Greenhouse" -o my-greenhouse.yaml
```

Then edit the generated file to add components and customize settings.

### From Built-in Scenario

1. Copy the built-in scenario file:
   ```bash
   cp examples/scenarios/basic.yaml my-scenario.yaml
   ```

2. Edit `my-scenario.yaml` to customize

3. Run your custom scenario:
   ```bash
   cgsim run my-scenario.yaml
   ```

### Scenario Design Tips

**Start Simple:**
- Begin with minimal components
- Add complexity incrementally
- Test after each addition

**Match Real Conditions:**
- Use actual location coordinates
- Match geometry to your structure
- Select appropriate covering material

**Balance Detail vs. Speed:**
- Smaller `time_step` = more accuracy, slower execution
- 60-second steps work well for most cases
- Use 30 seconds for fast-changing systems

**Test Edge Cases:**
- Run winter/summer scenarios for extreme conditions
- Override duration for quick tests: `cgsim run config.yaml -d 1`

---

## Scenario Organization

### Recommended Directory Structure

```
my-project/
├── scenarios/
│   ├── baseline.yaml        # Standard operating conditions
│   ├── winter-test.yaml     # Cold weather validation
│   ├── summer-test.yaml     # Hot weather validation
│   ├── energy-study.yaml    # Energy consumption focus
│   └── experiments/
│       ├── new-controller.yaml
│       └── hvac-upgrade.yaml
└── results/
    ├── baseline/
    ├── winter-test/
    └── summer-test/
```

### Version Control

YAML scenarios are ideal for version control:

```bash
# Track scenario changes
git add scenarios/
git commit -m "Add winter heating scenario"

# Compare scenarios
git diff scenarios/baseline.yaml scenarios/energy-study.yaml

# Review history
git log --oneline -- scenarios/
```

### Documentation

Document scenarios with comments:

```yaml
# Energy Optimization Study - Phase 1
#
# Goal: Compare PID vs staged control for exhaust fans
# Baseline: full-climate scenario
# Changes: Replaced staged controller with PID
# Expected: Smoother temperature control, possibly higher energy use
#
# Author: John Doe
# Date: 2025-01-15

name: "Energy Study - PID Control"
# ... rest of config
```

---

## Batch Processing

### Run Multiple Scenarios

```bash
#!/bin/bash
# run-all-scenarios.sh

scenarios=(
    "scenarios/baseline.yaml"
    "scenarios/winter-test.yaml"
    "scenarios/summer-test.yaml"
)

for scenario in "${scenarios[@]}"; do
    name=$(basename "$scenario" .yaml)
    echo "Running: $name"
    cgsim run "$scenario" -q -f json -o "results/$name"
done

echo "All scenarios complete"
```

### Compare Results

```python
import json
from pathlib import Path

results_dir = Path("results")
scenarios = ["baseline", "winter-test", "summer-test"]

for scenario in scenarios:
    result_file = results_dir / scenario / "results.json"
    if result_file.exists():
        data = json.loads(result_file.read_text())
        print(f"{scenario}:")
        print(f"  Final temp: {data['final_state']['interior_temperature']:.1f}°C")
        print(f"  Steps: {data['steps_completed']}")
```

---

## Troubleshooting

### Scenario Won't Load

**Check YAML syntax:**
```bash
cgsim validate my-scenario.yaml
```

**Common issues:**
- Indentation errors (use spaces, not tabs)
- Missing required fields
- Invalid component types

### Simulation Runs Too Slow

**Reduce detail:**
```yaml
time_step: 120.0    # 2 minutes instead of 1
duration: 3600.0    # 1 hour instead of 24
```

**Or use CLI overrides:**
```bash
cgsim run scenario.yaml -d 1 -t 120
```

### Temperature Goes to Extremes

**Check heat balance:**
- Heating capacity vs. heat loss in winter
- Cooling capacity vs. solar gain in summer

**Check controller tuning:**
- PID gains may be too aggressive
- Setpoints may be unrealistic for conditions

### Scenario Files Not Found

**Check paths:**
```bash
# List built-in scenarios
cgsim list

# Verify custom file exists
ls -la my-scenario.yaml
```

**Use absolute paths if needed:**
```bash
cgsim run /full/path/to/my-scenario.yaml
```
