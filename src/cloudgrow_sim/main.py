"""CLI interface for cloudgrow-sim.

This module provides a command-line interface for running greenhouse
simulations from YAML configuration files without writing code.

Usage:
    cgsim run my-greenhouse.yaml
    cgsim run --scenario basic
    cgsim list
    cgsim init "My Greenhouse" -o my-config.yaml
    cgsim validate my-config.yaml
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

if TYPE_CHECKING:
    from cloudgrow_sim.simulation.engine import SimulationEngine, SimulationStats

from cloudgrow_sim.core.config import (
    ActuatorConfig,
    ComponentsConfig,
    ControllerConfig,
    CoveringConfig,
    GeometryConfig,
    LocationConfig,
    SensorConfig,
    SimulationConfig,
    WeatherConfig,
    load_config,
    save_config,
)
from cloudgrow_sim.simulation.factory import create_engine_from_config

app = typer.Typer(
    name="cgsim",
    help="ASHRAE-compliant greenhouse climate simulation framework.",
    add_completion=False,
    no_args_is_help=True,
)
console = Console()

# Built-in scenario names
BUILTIN_SCENARIOS = ["basic", "full-climate", "winter-heating", "summer-cooling"]


def get_scenarios_dir() -> Path:
    """Get the examples/scenarios directory.

    Looks for scenarios in:
    1. Relative to package root (development)
    2. Relative to current working directory
    """
    # Development: relative to package
    pkg_dir = Path(__file__).parent.parent.parent.parent / "examples" / "scenarios"
    if pkg_dir.exists():
        return pkg_dir

    # CWD fallback
    cwd_dir = Path.cwd() / "examples" / "scenarios"
    if cwd_dir.exists():
        return cwd_dir

    return Path("examples/scenarios")


@app.command()
def run(
    config_path: Annotated[
        Path | None,
        typer.Argument(help="Path to YAML configuration file"),
    ] = None,
    scenario: Annotated[
        str | None,
        typer.Option("--scenario", "-s", help="Built-in scenario name"),
    ] = None,
    duration: Annotated[
        float | None,
        typer.Option("--duration", "-d", help="Override duration in hours"),
    ] = None,
    time_step: Annotated[
        float | None,
        typer.Option("--time-step", "-t", help="Override time step in seconds"),
    ] = None,
    output_dir: Annotated[
        Path | None,
        typer.Option("--output-dir", "-o", help="Output directory for results"),
    ] = None,
    format_: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: console, csv, json"),
    ] = "console",
    quiet: Annotated[
        bool,
        typer.Option("--quiet", "-q", help="Suppress progress output"),
    ] = False,
) -> None:
    """Run a greenhouse simulation from configuration."""
    # Resolve config source
    if config_path and scenario:
        console.print("[red]Error:[/] Cannot specify both config file and --scenario")
        raise typer.Exit(1)

    if scenario:
        if scenario not in BUILTIN_SCENARIOS:
            console.print(f"[red]Error:[/] Unknown scenario '{scenario}'")
            console.print(f"Available: {', '.join(BUILTIN_SCENARIOS)}")
            raise typer.Exit(1)

        config_path = get_scenarios_dir() / f"{scenario}.yaml"
        if not config_path.exists():
            console.print(f"[red]Error:[/] Scenario file not found: {config_path}")
            raise typer.Exit(1)

    if not config_path:
        console.print("[red]Error:[/] Provide a config file or --scenario")
        raise typer.Exit(1)

    # Load and validate config
    try:
        config = load_config(config_path)
    except FileNotFoundError:
        console.print(f"[red]Error:[/] Config file not found: {config_path}")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Error:[/] Invalid configuration: {e}")
        raise typer.Exit(1) from None

    # Apply overrides
    updates: dict[str, float] = {}
    if duration is not None:
        updates["duration"] = duration * 3600  # Convert hours to seconds
    if time_step is not None:
        updates["time_step"] = time_step

    if updates:
        config = config.model_copy(update=updates)

    # Create engine
    try:
        engine = create_engine_from_config(config)
    except KeyError as e:
        console.print(f"[red]Error:[/] Unknown component type: {e}")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Error:[/] Failed to create simulation: {e}")
        raise typer.Exit(1) from None

    # Run simulation
    if not quiet:
        console.print(f"\n[bold]Running:[/] {config.name}")
        console.print(f"  Duration: {config.duration / 3600:.1f} hours")
        console.print(f"  Time step: {config.time_step} seconds\n")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Simulating...", total=None)
            stats = engine.run()
            progress.update(task, description="[green]Complete!")
    else:
        stats = engine.run()

    # Output results
    _output_results(engine, stats, format_, output_dir, quiet)


@app.command("list")
def list_scenarios() -> None:
    """List available built-in scenarios."""
    scenarios_dir = get_scenarios_dir()

    table = Table(title="Available Scenarios")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Duration")

    for name in BUILTIN_SCENARIOS:
        path = scenarios_dir / f"{name}.yaml"
        if path.exists():
            try:
                config = load_config(path)
                duration_hr = config.duration / 3600
                table.add_row(name, config.name, f"{duration_hr:.0f}h")
            except Exception:
                table.add_row(name, "[dim]Error loading[/]", "-")
        else:
            table.add_row(name, "[dim]Not found[/]", "-")

    console.print(table)
    console.print(f"\nScenarios directory: {scenarios_dir}")


@app.command()
def init(
    name: Annotated[str, typer.Argument(help="Name for the new scenario")],
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output file path"),
    ] = None,
) -> None:
    """Generate a starter YAML configuration file."""
    config = SimulationConfig(
        name=name,
        time_step=60.0,
        duration=86400.0,  # 24 hours
        location=LocationConfig(
            latitude=37.5,
            longitude=-77.4,
            elevation=50.0,
            timezone="America/New_York",
        ),
        geometry=GeometryConfig(
            length=10.0,
            width=6.0,
            height_ridge=3.5,
            height_eave=2.4,
            orientation=0.0,
        ),
        covering=CoveringConfig(material="double_polyethylene"),
        components=ComponentsConfig(
            sensors=[
                SensorConfig(type="temperature", name="temp_int", location="interior"),
            ],
            actuators=[
                ActuatorConfig(
                    type="exhaust_fan",
                    name="exhaust_1",
                    controller="vent_control",
                ),
            ],
            controllers=[
                ControllerConfig(
                    type="hysteresis",
                    name="vent_control",
                    process_variable="temp_int.temperature",
                    setpoint=28.0,
                ),
            ],
            modifiers=[],
        ),
        weather=WeatherConfig(source="synthetic"),
    )

    # Generate filename from name if not specified
    if output is None:
        # Convert name to filename: "My Greenhouse" -> "my-greenhouse.yaml"
        filename = name.lower().replace(" ", "-") + ".yaml"
        output = Path(filename)

    save_config(config, output)
    console.print(f"[green]Created:[/] {output}")
    console.print("\nEdit this file to customize your simulation, then run:")
    console.print(f"  cgsim run {output}")


@app.command()
def validate(
    config_path: Annotated[Path, typer.Argument(help="Path to YAML configuration")],
) -> None:
    """Validate a configuration file without running."""
    try:
        config = load_config(config_path)
        console.print(f"[green]Valid:[/] {config.name}")
        console.print(f"  Duration: {config.duration / 3600:.1f} hours")
        console.print(f"  Time step: {config.time_step} seconds")
        console.print(
            f"  Location: {config.location.latitude}N, {config.location.longitude}E"
        )
        console.print(
            f"  Geometry: {config.geometry.length}m x {config.geometry.width}m"
        )
        console.print(f"  Sensors: {len(config.components.sensors)}")
        console.print(f"  Actuators: {len(config.components.actuators)}")
        console.print(f"  Controllers: {len(config.components.controllers)}")
        console.print(f"  Modifiers: {len(config.components.modifiers)}")
    except FileNotFoundError:
        console.print(f"[red]Error:[/] File not found: {config_path}")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Invalid:[/] {e}")
        raise typer.Exit(1) from None


def _output_results(
    engine: SimulationEngine,
    stats: SimulationStats,
    format_: str,
    output_dir: Path | None,
    quiet: bool,
) -> None:
    """Output simulation results in requested format.

    Args:
        engine: The simulation engine after running.
        stats: Statistics from the simulation run.
        format_: Output format (console, csv, json).
        output_dir: Optional directory for file outputs.
        quiet: If True, suppress console output.
    """
    # Console output
    if format_ == "console" and not quiet:
        console.print("\n[bold]Simulation Complete[/]")
        console.print(f"  Steps completed: {stats.steps_completed}")
        console.print(f"  Simulated time: {stats.simulation_time}")
        console.print(f"  Wall time: {stats.wall_time.total_seconds():.2f}s")
        console.print(
            f"  Final interior temp: {engine.state.interior.temperature:.1f}C"
        )
        console.print(f"  Final interior RH: {engine.state.interior.humidity:.1f}%")

    # File outputs
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        if format_ == "json" or format_ == "console":
            result = {
                "steps_completed": stats.steps_completed,
                "simulation_time_seconds": stats.simulation_time.total_seconds(),
                "wall_time_seconds": stats.wall_time.total_seconds(),
                "final_state": {
                    "interior_temperature": engine.state.interior.temperature,
                    "interior_humidity": engine.state.interior.humidity,
                    "interior_co2_ppm": engine.state.interior.co2_ppm,
                    "exterior_temperature": engine.state.exterior.temperature,
                    "exterior_humidity": engine.state.exterior.humidity,
                },
            }
            json_path = output_dir / "results.json"
            json_path.write_text(json.dumps(result, indent=2))
            if not quiet:
                console.print(f"\n[dim]Results saved to {json_path}[/]")

        if format_ == "csv":
            # CSV output with final state summary
            csv_path = output_dir / "results.csv"
            with csv_path.open("w") as f:
                f.write("metric,value\n")
                f.write(f"steps_completed,{stats.steps_completed}\n")
                f.write(
                    f"simulation_time_seconds,{stats.simulation_time.total_seconds()}\n"
                )
                f.write(f"wall_time_seconds,{stats.wall_time.total_seconds()}\n")
                f.write(f"interior_temperature,{engine.state.interior.temperature}\n")
                f.write(f"interior_humidity,{engine.state.interior.humidity}\n")
                f.write(f"exterior_temperature,{engine.state.exterior.temperature}\n")
            if not quiet:
                console.print(f"\n[dim]Results saved to {csv_path}[/]")


def main() -> int:
    """Application entry point.

    Returns:
        Exit code (0 for success).
    """
    try:
        app()
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1


if __name__ == "__main__":
    sys.exit(main())
