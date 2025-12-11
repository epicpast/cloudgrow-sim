"""Tests for YAML scenario files."""

from __future__ import annotations

from pathlib import Path

import pytest

from cloudgrow_sim.core.config import load_config
from cloudgrow_sim.core.registry import reset_registry
from cloudgrow_sim.simulation.factory import (
    create_engine_from_config,
    ensure_components_registered,
)


def get_scenarios_dir() -> Path:
    """Get the examples/scenarios directory."""
    # Find the project root by looking for pyproject.toml
    current = Path(__file__).parent
    while current != current.parent:
        if (current / "pyproject.toml").exists():
            scenarios_dir = current / "examples" / "scenarios"
            if scenarios_dir.exists():
                return scenarios_dir
        current = current.parent

    # Fallback
    return Path("examples/scenarios")


SCENARIOS_DIR = get_scenarios_dir()


class TestBuiltinScenarios:
    """Tests for built-in YAML scenario files."""

    def setup_method(self) -> None:
        """Reset registry before each test."""
        reset_registry()
        ensure_components_registered()

    @pytest.mark.skipif(
        not (SCENARIOS_DIR / "basic.yaml").exists(),
        reason="Scenario file not found",
    )
    def test_basic_yaml_loads_and_validates(self) -> None:
        """Test that basic.yaml loads and validates."""
        config = load_config(SCENARIOS_DIR / "basic.yaml")

        assert config.name == "Basic Hobby Greenhouse"
        assert config.time_step == 60.0
        assert config.duration == 86400.0
        assert len(config.components.sensors) == 1
        assert len(config.components.actuators) == 1
        assert len(config.components.controllers) == 1

    @pytest.mark.skipif(
        not (SCENARIOS_DIR / "full-climate.yaml").exists(),
        reason="Scenario file not found",
    )
    def test_full_climate_yaml_loads_and_validates(self) -> None:
        """Test that full-climate.yaml loads and validates."""
        config = load_config(SCENARIOS_DIR / "full-climate.yaml")

        assert config.name == "Full Climate Control"
        assert len(config.components.sensors) >= 4
        assert len(config.components.actuators) >= 8
        assert len(config.components.controllers) >= 3
        assert len(config.components.modifiers) >= 2

    @pytest.mark.skipif(
        not (SCENARIOS_DIR / "winter-heating.yaml").exists(),
        reason="Scenario file not found",
    )
    def test_winter_heating_yaml_loads_and_validates(self) -> None:
        """Test that winter-heating.yaml loads and validates."""
        config = load_config(SCENARIOS_DIR / "winter-heating.yaml")

        assert config.name == "Winter Heating Scenario"
        assert config.duration == 172800.0  # 48 hours
        # Should have heaters
        actuator_types = [a.type for a in config.components.actuators]
        assert "unit_heater" in actuator_types

    @pytest.mark.skipif(
        not (SCENARIOS_DIR / "summer-cooling.yaml").exists(),
        reason="Scenario file not found",
    )
    def test_summer_cooling_yaml_loads_and_validates(self) -> None:
        """Test that summer-cooling.yaml loads and validates."""
        config = load_config(SCENARIOS_DIR / "summer-cooling.yaml")

        assert config.name == "Summer Cooling Scenario"
        assert config.duration == 172800.0  # 48 hours
        # Should have exhaust fans and evap pad
        actuator_types = [a.type for a in config.components.actuators]
        assert "exhaust_fan" in actuator_types
        assert "evaporative_pad" in actuator_types

    @pytest.mark.skipif(
        not (SCENARIOS_DIR / "basic.yaml").exists(),
        reason="Scenario file not found",
    )
    def test_basic_yaml_creates_engine(self) -> None:
        """Test that basic.yaml creates a valid engine."""
        config = load_config(SCENARIOS_DIR / "basic.yaml")
        engine = create_engine_from_config(config)

        assert engine is not None
        assert len(engine._sensors) == 1
        assert len(engine._actuators) == 1
        assert len(engine._controllers) == 1

    @pytest.mark.skipif(
        not (SCENARIOS_DIR / "full-climate.yaml").exists(),
        reason="Scenario file not found",
    )
    def test_full_climate_yaml_creates_engine(self) -> None:
        """Test that full-climate.yaml creates a valid engine."""
        config = load_config(SCENARIOS_DIR / "full-climate.yaml")
        engine = create_engine_from_config(config)

        assert engine is not None
        assert len(engine._sensors) >= 4
        assert len(engine._actuators) >= 8

    @pytest.mark.skipif(
        not (SCENARIOS_DIR / "winter-heating.yaml").exists(),
        reason="Scenario file not found",
    )
    def test_winter_heating_yaml_creates_engine(self) -> None:
        """Test that winter-heating.yaml creates a valid engine."""
        config = load_config(SCENARIOS_DIR / "winter-heating.yaml")
        engine = create_engine_from_config(config)

        assert engine is not None
        assert len(engine._actuators) >= 2  # main + backup heater

    @pytest.mark.skipif(
        not (SCENARIOS_DIR / "summer-cooling.yaml").exists(),
        reason="Scenario file not found",
    )
    def test_summer_cooling_yaml_creates_engine(self) -> None:
        """Test that summer-cooling.yaml creates a valid engine."""
        config = load_config(SCENARIOS_DIR / "summer-cooling.yaml")
        engine = create_engine_from_config(config)

        assert engine is not None
        assert len(engine._actuators) >= 5  # 4 fans + evap pad

    @pytest.mark.skipif(
        not (SCENARIOS_DIR / "basic.yaml").exists(),
        reason="Scenario file not found",
    )
    def test_basic_scenario_runs_to_completion(self) -> None:
        """Test that basic scenario can run a short simulation."""
        config = load_config(SCENARIOS_DIR / "basic.yaml")

        # Override duration to just 10 minutes for faster test
        config = config.model_copy(update={"duration": 600.0})

        engine = create_engine_from_config(config)
        stats = engine.run()

        assert stats.steps_completed > 0
        assert stats.simulation_time.total_seconds() == 600.0


class TestScenarioStructure:
    """Tests for scenario file structure and consistency."""

    def setup_method(self) -> None:
        """Reset registry before each test."""
        reset_registry()
        ensure_components_registered()

    @pytest.mark.skipif(
        not SCENARIOS_DIR.exists(),
        reason="Scenarios directory not found",
    )
    def test_all_scenarios_have_required_fields(self) -> None:
        """Test that all scenarios have required fields."""
        scenario_files = list(SCENARIOS_DIR.glob("*.yaml"))

        for scenario_file in scenario_files:
            config = load_config(scenario_file)

            # Required fields
            assert config.name, f"{scenario_file.name} missing name"
            assert config.time_step > 0, f"{scenario_file.name} invalid time_step"
            assert config.duration > 0, f"{scenario_file.name} invalid duration"
            assert config.location.latitude is not None
            assert config.location.longitude is not None
            assert config.geometry.length > 0
            assert config.geometry.width > 0

    @pytest.mark.skipif(
        not SCENARIOS_DIR.exists(),
        reason="Scenarios directory not found",
    )
    def test_all_scenarios_use_valid_component_types(self) -> None:
        """Test that all scenarios use valid component types."""
        valid_sensor_types = {
            "temperature",
            "humidity",
            "temp_humidity",
            "solar_radiation",
            "par",
            "co2",
            "wind",
        }
        valid_actuator_types = {
            "exhaust_fan",
            "intake_fan",
            "circulation_fan",
            "unit_heater",
            "radiant_heater",
            "evaporative_pad",
            "fogger",
            "roof_vent",
            "side_vent",
            "shade_curtain",
            "thermal_curtain",
        }
        valid_controller_types = {"pid", "hysteresis", "staged", "schedule"}
        valid_modifier_types = {"covering", "thermal_mass"}

        scenario_files = list(SCENARIOS_DIR.glob("*.yaml"))

        for scenario_file in scenario_files:
            config = load_config(scenario_file)

            for sensor in config.components.sensors:
                assert sensor.type in valid_sensor_types, (
                    f"{scenario_file.name}: Invalid sensor type '{sensor.type}'"
                )

            for actuator in config.components.actuators:
                assert actuator.type in valid_actuator_types, (
                    f"{scenario_file.name}: Invalid actuator type '{actuator.type}'"
                )

            for controller in config.components.controllers:
                assert controller.type in valid_controller_types, (
                    f"{scenario_file.name}: Invalid controller type '{controller.type}'"
                )

            for modifier in config.components.modifiers:
                assert modifier.type in valid_modifier_types, (
                    f"{scenario_file.name}: Invalid modifier type '{modifier.type}'"
                )
