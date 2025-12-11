#!/usr/bin/env python3
"""Basic greenhouse simulation example.

This script demonstrates how to run greenhouse climate simulations
using the pre-built scenarios and custom configurations.

Run with: uv run python examples/basic_simulation.py
"""

from cloudgrow_sim.core.events import EventType, get_event_bus
from cloudgrow_sim.simulation.scenarios import (
    create_basic_scenario,
    create_full_climate_scenario,
)


def run_basic_scenario() -> None:
    """Run a basic 24-hour simulation with minimal components."""
    print("=" * 60)
    print("BASIC SCENARIO: Small hobby greenhouse")
    print("=" * 60)

    engine = create_basic_scenario(duration_hours=24.0)
    state = engine.state

    print(f"Location: {state.location.latitude}°N, {state.location.longitude}°W")
    print(f"Greenhouse: {state.geometry.length}m x {state.geometry.width}m")
    print(f"Start time: {state.time.strftime('%Y-%m-%d %H:%M %Z')}")
    print(f"Initial interior temp: {state.interior.temperature}°C")
    print()

    # Track hourly data
    hourly_temps: list[tuple[int, float, float]] = []

    def on_state_update(event: object) -> None:
        data = getattr(event, "data", {})
        hourly_temps.append((
            len(hourly_temps),
            data.get("interior_temperature", 0),
            data.get("exterior_temperature", 0),
        ))

    bus = get_event_bus()
    bus.subscribe(EventType.STATE_UPDATE, on_state_update)

    print("Running simulation...")
    stats = engine.run()

    print()
    print(f"Completed {stats.steps_completed} steps in {stats.wall_time.total_seconds():.2f}s")
    print(f"Avg step time: {stats.avg_step_time:.3f}ms")
    print()

    # Print hourly summary (sample every 6 hours)
    print("Temperature Summary (every 6 hours):")
    print("-" * 40)
    print(f"{'Hour':>6} {'Interior':>12} {'Exterior':>12}")
    print(f"{'':>6} {'(°C)':>12} {'(°C)':>12}")
    print("-" * 40)
    for hour, t_int, t_ext in hourly_temps[::6]:
        print(f"{hour:>6} {t_int:>12.1f} {t_ext:>12.1f}")
    print("-" * 40)

    if hourly_temps:
        temps = [t[1] for t in hourly_temps]
        print(f"Interior range: {min(temps):.1f}°C - {max(temps):.1f}°C")
    print()


def run_full_climate_scenario() -> None:
    """Run a full commercial greenhouse simulation."""
    print("=" * 60)
    print("FULL CLIMATE SCENARIO: Commercial greenhouse")
    print("=" * 60)

    engine = create_full_climate_scenario(duration_hours=24.0)
    state = engine.state

    print(f"Location: {state.location.latitude}°N (California)")
    print(f"Greenhouse: {state.geometry.length}m x {state.geometry.width}m")
    print(f"Components: {len(engine._sensors)} sensors, "
          f"{len(engine._actuators)} actuators, "
          f"{len(engine._controllers)} controllers")
    print()

    # Track detailed data
    data_log: list[dict[str, float]] = []

    def on_state_update(event: object) -> None:
        data = getattr(event, "data", {})
        data_log.append({
            "hour": len(data_log),
            "t_int": data.get("interior_temperature", 0),
            "t_ext": data.get("exterior_temperature", 0),
            "rh": data.get("interior_humidity", 0),
            "solar": data.get("solar_radiation", 0),
        })

    bus = get_event_bus()
    # Clear previous subscriptions to avoid duplicates
    bus.clear_handlers()
    bus.subscribe(EventType.STATE_UPDATE, on_state_update)

    print("Running simulation...")
    stats = engine.run()

    print()
    print(f"Completed {stats.steps_completed} steps in {stats.wall_time.total_seconds():.2f}s")
    print()

    # Print every 4 hours
    print("Climate Summary (every 4 hours):")
    print("-" * 60)
    print(f"{'Hour':>4} {'Interior':>10} {'Exterior':>10} {'Humidity':>10} {'Solar':>10}")
    print(f"{'':>4} {'(°C)':>10} {'(°C)':>10} {'(%)':>10} {'(W/m²)':>10}")
    print("-" * 60)
    for entry in data_log[::4]:
        print(f"{entry['hour']:>4} {entry['t_int']:>10.1f} {entry['t_ext']:>10.1f} "
              f"{entry['rh']:>10.1f} {entry['solar']:>10.0f}")
    print("-" * 60)

    if data_log:
        temps = [d["t_int"] for d in data_log]
        print(f"Interior temp range: {min(temps):.1f}°C - {max(temps):.1f}°C")
        print(f"Final state: {engine.state.interior.temperature:.1f}°C, "
              f"{engine.state.interior.humidity:.1f}% RH")
    print()


def main() -> None:
    """Run greenhouse simulation examples."""
    print()
    print("CLOUDGROW-SIM: Greenhouse Climate Simulation")
    print("ASHRAE-compliant physics engine")
    print()

    # Run basic scenario first
    run_basic_scenario()

    # Run full commercial scenario
    run_full_climate_scenario()

    print("=" * 60)
    print("Simulations complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
