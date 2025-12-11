# CLI Reference

The `cgsim` command-line interface provides easy access to greenhouse simulations without writing code.

## Commands

### cgsim run

Run a greenhouse simulation from a YAML configuration file or built-in scenario.

**Usage:**
```bash
cgsim run [OPTIONS] [CONFIG_PATH]
```

**Arguments:**
- `CONFIG_PATH` - Path to YAML configuration file (optional if using --scenario)

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--scenario` | `-s` | TEXT | - | Run a built-in scenario by name |
| `--duration` | `-d` | FLOAT | - | Override duration in hours |
| `--time-step` | `-t` | FLOAT | - | Override time step in seconds |
| `--output-dir` | `-o` | PATH | - | Output directory for results |
| `--format` | `-f` | TEXT | console | Output format: console, csv, json |
| `--quiet` | `-q` | FLAG | False | Suppress progress output |

**Examples:**

```bash
# Run from a YAML config file
cgsim run my-greenhouse.yaml

# Run a built-in scenario
cgsim run --scenario basic
cgsim run -s full-climate

# Override duration to 48 hours
cgsim run config.yaml --duration 48
cgsim run config.yaml -d 48

# Override time step to 30 seconds
cgsim run config.yaml --time-step 30
cgsim run config.yaml -t 30

# Output results to a directory
cgsim run config.yaml --output-dir ./results

# Choose output format
cgsim run config.yaml --format json --output-dir ./results
cgsim run config.yaml -f csv -o ./results

# Run quietly (no progress output)
cgsim run config.yaml --quiet

# Combine options
cgsim run config.yaml -d 48 -t 30 -f json -o ./results -q
```

**Exit Codes:**
- `0` - Simulation completed successfully
- `1` - Error (invalid config, file not found, etc.)

---

### cgsim list

List all available built-in scenarios.

**Usage:**
```bash
cgsim list
```

**Output:**
```
Available Scenarios
┏━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name             ┃ Description                             ┃
┡━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ basic            │ Basic Hobby Greenhouse                  │
│ full-climate     │ Full Climate Control                    │
│ winter-heating   │ Winter Heating Scenario                 │
│ summer-cooling   │ Summer Cooling Scenario                 │
└──────────────────┴─────────────────────────────────────────┘
```

---

### cgsim init

Generate a starter YAML configuration file with sensible defaults.

**Usage:**
```bash
cgsim init [OPTIONS] NAME
```

**Arguments:**
- `NAME` - Name for the greenhouse scenario (required)

**Options:**
| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | PATH | - | Output file path (default: slugified name) |

**Examples:**

```bash
# Create with default filename (my-greenhouse.yaml)
cgsim init "My Greenhouse"

# Specify output path
cgsim init "Summer Test" -o experiments/summer-test.yaml
cgsim init "Production Config" --output /path/to/production.yaml
```

**Generated File Structure:**

The generated file includes:
- Basic simulation parameters (time_step, duration)
- Location configuration
- Geometry configuration
- Empty component sections with comments

---

### cgsim validate

Validate a configuration file without running the simulation.

**Usage:**
```bash
cgsim validate CONFIG_PATH
```

**Arguments:**
- `CONFIG_PATH` - Path to YAML configuration file (required)

**Examples:**

```bash
# Validate a config file
cgsim validate my-greenhouse.yaml
```

**Success Output:**
```
✓ Valid: My Greenhouse
  Duration: 24.0 hours
  Time step: 60.0 seconds
  Components:
    Sensors: 2
    Actuators: 3
    Controllers: 1
    Modifiers: 0
```

**Error Output:**
```
✗ Invalid: my-greenhouse.yaml
  - location.latitude: Input should be less than or equal to 90
```

**Exit Codes:**
- `0` - Configuration is valid
- `1` - Configuration is invalid or file not found

---

## Output Formats

### Console (default)

Human-readable output displayed in the terminal with progress indicators.

```bash
cgsim run config.yaml
```

Output includes:
- Simulation progress bar
- Final statistics summary
- Key metrics

### JSON

Machine-readable JSON output saved to file.

```bash
cgsim run config.yaml --format json --output-dir ./results
```

Creates `results/results.json`:
```json
{
  "scenario_name": "My Greenhouse",
  "steps_completed": 1440,
  "simulation_time_seconds": 86400.0,
  "wall_time_seconds": 2.5,
  "final_state": {
    "interior_temperature": 24.5,
    "interior_humidity": 65.2,
    "exterior_temperature": 18.0
  }
}
```

### CSV

Tabular output for spreadsheet analysis.

```bash
cgsim run config.yaml --format csv --output-dir ./results
```

Creates `results/results.csv`:
```csv
metric,value
scenario_name,My Greenhouse
steps_completed,1440
simulation_time_seconds,86400.0
wall_time_seconds,2.5
final_interior_temperature,24.5
final_interior_humidity,65.2
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `CGSIM_SCENARIOS_DIR` | Custom scenarios directory path |
| `NO_COLOR` | Disable colored output when set |

---

## Error Messages

### Common Errors

**"Config file not found"**
```
Error: Config file 'missing.yaml' not found
```
The specified file does not exist. Check the path.

**"Cannot specify both"**
```
Error: Cannot specify both a config file and --scenario
```
Use either a config file path OR the --scenario flag, not both.

**"Provide a config file"**
```
Error: Provide a config file path or use --scenario
```
The run command requires either a config file or --scenario flag.

**"Scenario not found"**
```
Error: Scenario 'invalid' not found. Use 'cgsim list' to see available scenarios.
```
The specified scenario name doesn't exist. Run `cgsim list` to see options.

### Validation Errors

Validation errors show the specific field and issue:

```
✗ Invalid: config.yaml
  - location.latitude: Input should be less than or equal to 90
  - geometry.height_eave: Eave height cannot exceed ridge height
  - components.sensors[0].type: Invalid sensor type 'unknown'
```

---

## Tips

### Batch Processing

```bash
# Process multiple configs
for config in configs/*.yaml; do
    cgsim run "$config" -q -f json -o "results/$(basename "$config" .yaml)"
done
```

### Quick Validation

```bash
# Validate all configs in a directory
for config in configs/*.yaml; do
    echo "Checking $config..."
    cgsim validate "$config" || echo "  FAILED"
done
```

### Development Workflow

```bash
# Generate, validate, and run
cgsim init "Test" -o test.yaml
# Edit test.yaml...
cgsim validate test.yaml
cgsim run test.yaml -d 1 -q  # Quick 1-hour test
```
