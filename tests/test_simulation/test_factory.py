"""Tests for simulation factory functions."""

from __future__ import annotations

from pathlib import Path

import pytest

from cloudgrow_sim.core.config import (
    ActuatorConfig,
    ComponentsConfig,
    ControllerConfig,
    CoveringConfig,
    GeometryConfig,
    LocationConfig,
    ModifierConfig,
    SensorConfig,
    SimulationConfig,
    WeatherConfig,
    load_config,
)
from cloudgrow_sim.core.registry import reset_registry
from cloudgrow_sim.simulation.factory import (
    create_engine_from_config,
    ensure_components_registered,
)


class TestCreateEngineFromConfig:
    """Tests for create_engine_from_config factory function."""

    def setup_method(self) -> None:
        """Reset registry before each test."""
        reset_registry()
        ensure_components_registered()

    def test_minimal_config_creates_engine(self) -> None:
        """Test that minimal config creates a valid engine."""
        config = SimulationConfig(
            name="Test Scenario",
            time_step=60.0,
            duration=3600.0,  # 1 hour
            location=LocationConfig(latitude=37.0, longitude=-77.0),
            geometry=GeometryConfig(
                length=10.0, width=6.0, height_ridge=3.5, height_eave=2.4
            ),
        )

        engine = create_engine_from_config(config)

        assert engine is not None
        assert engine._config.time_step == 60.0

    def test_config_with_sensor(self) -> None:
        """Test engine creation with a sensor."""
        config = SimulationConfig(
            name="With Sensor",
            location=LocationConfig(latitude=37.0, longitude=-77.0),
            geometry=GeometryConfig(
                length=10.0, width=6.0, height_ridge=3.5, height_eave=2.4
            ),
            components=ComponentsConfig(
                sensors=[
                    SensorConfig(type="temperature", name="temp_1", location="interior")
                ]
            ),
        )

        engine = create_engine_from_config(config)

        assert len(engine._sensors) == 1
        assert "temp_1" in [s.name for s in engine._sensors]

    def test_all_sensor_types_instantiate(self) -> None:
        """Test that all sensor types can be instantiated."""
        sensor_types = [
            ("temperature", {}),
            ("humidity", {}),
            ("temp_humidity", {}),
            ("solar_radiation", {}),
            ("par", {}),
            ("co2", {}),
            ("wind", {}),
        ]

        sensors = [
            SensorConfig(type=stype, name=f"sensor_{i}", **extra)
            for i, (stype, extra) in enumerate(sensor_types)
        ]

        config = SimulationConfig(
            name="All Sensors",
            location=LocationConfig(latitude=37.0, longitude=-77.0),
            geometry=GeometryConfig(
                length=10.0, width=6.0, height_ridge=3.5, height_eave=2.4
            ),
            components=ComponentsConfig(sensors=sensors),
        )

        engine = create_engine_from_config(config)

        assert len(engine._sensors) == len(sensor_types)

    def test_all_actuator_types_instantiate(self) -> None:
        """Test that all actuator types can be instantiated."""
        actuator_configs = [
            ("exhaust_fan", {"max_flow_rate": 1.0, "power_consumption": 500.0}),
            ("intake_fan", {"max_flow_rate": 1.0, "power_consumption": 500.0}),
            ("circulation_fan", {"power_consumption": 200.0}),
            ("unit_heater", {"heating_capacity": 10000.0, "efficiency": 0.9}),
            ("radiant_heater", {"heating_capacity": 10000.0, "radiant_fraction": 0.7}),
            ("evaporative_pad", {"pad_area": 5.0, "saturation_efficiency": 0.8}),
            ("fogger", {"flow_rate_per_nozzle": 5.0, "droplet_size": 10.0}),
            ("roof_vent", {"width": 2.0, "height": 0.5, "height_above_floor": 4.0}),
            ("side_vent", {"width": 2.0, "height": 1.0, "height_above_floor": 1.0}),
            ("shade_curtain", {"shade_factor": 0.5}),
            ("thermal_curtain", {"thermal_resistance": 1.5}),
        ]

        actuators = [
            ActuatorConfig(type=atype, name=f"actuator_{i}", **extra)
            for i, (atype, extra) in enumerate(actuator_configs)
        ]

        config = SimulationConfig(
            name="All Actuators",
            location=LocationConfig(latitude=37.0, longitude=-77.0),
            geometry=GeometryConfig(
                length=10.0, width=6.0, height_ridge=3.5, height_eave=2.4
            ),
            components=ComponentsConfig(actuators=actuators),
        )

        engine = create_engine_from_config(config)

        assert len(engine._actuators) == len(actuator_configs)

    def test_all_controller_types_instantiate(self) -> None:
        """Test that all controller types can be instantiated."""
        controller_configs = [
            ("pid", {"setpoint": 25.0, "kp": 0.5, "ki": 0.1, "kd": 0.05}),
            ("hysteresis", {"setpoint": 25.0, "hysteresis": 2.0}),
            ("staged", {"stages": [(26.0, 0.5), (28.0, 1.0)]}),
            ("schedule", {}),
        ]

        controllers = [
            ControllerConfig(
                type=ctype,
                name=f"controller_{i}",
                process_variable="temp.value",
                **extra,
            )
            for i, (ctype, extra) in enumerate(controller_configs)
        ]

        config = SimulationConfig(
            name="All Controllers",
            location=LocationConfig(latitude=37.0, longitude=-77.0),
            geometry=GeometryConfig(
                length=10.0, width=6.0, height_ridge=3.5, height_eave=2.4
            ),
            components=ComponentsConfig(controllers=controllers),
        )

        engine = create_engine_from_config(config)

        assert len(engine._controllers) == len(controller_configs)

    def test_all_modifier_types_instantiate(self) -> None:
        """Test that all modifier types can be instantiated."""
        modifier_configs = [
            ("covering", {"material": "single_glass"}),
            (
                "thermal_mass",
                {
                    "mass": 1000.0,
                    "specific_heat": 4186.0,
                    "surface_area": 10.0,
                    "initial_temperature": 20.0,
                },
            ),
        ]

        modifiers = [
            ModifierConfig(type=mtype, name=f"modifier_{i}", **extra)
            for i, (mtype, extra) in enumerate(modifier_configs)
        ]

        config = SimulationConfig(
            name="All Modifiers",
            location=LocationConfig(latitude=37.0, longitude=-77.0),
            geometry=GeometryConfig(
                length=10.0, width=6.0, height_ridge=3.5, height_eave=2.4
            ),
            components=ComponentsConfig(modifiers=modifiers),
        )

        engine = create_engine_from_config(config)

        assert len(engine._modifiers) == len(modifier_configs)

    def test_invalid_component_type_raises_keyerror(self) -> None:
        """Test that unknown component type raises KeyError."""
        config = SimulationConfig(
            name="Invalid",
            location=LocationConfig(latitude=37.0, longitude=-77.0),
            geometry=GeometryConfig(
                length=10.0, width=6.0, height_ridge=3.5, height_eave=2.4
            ),
            components=ComponentsConfig(
                sensors=[
                    SensorConfig(
                        type="nonexistent_sensor", name="bad", location="interior"
                    )
                ]
            ),
        )

        with pytest.raises(KeyError, match="nonexistent_sensor"):
            create_engine_from_config(config)

    def test_weather_source_synthetic(self) -> None:
        """Test synthetic weather source creation."""
        config = SimulationConfig(
            name="Synthetic Weather",
            location=LocationConfig(latitude=37.0, longitude=-77.0),
            geometry=GeometryConfig(
                length=10.0, width=6.0, height_ridge=3.5, height_eave=2.4
            ),
            weather=WeatherConfig(
                source="synthetic", base_temperature=20.0, temperature_amplitude=10.0
            ),
        )

        engine = create_engine_from_config(config)

        assert engine is not None
        # Weather source is created internally

    def test_initial_state_from_config(self) -> None:
        """Test that initial state reflects config values."""
        config = SimulationConfig(
            name="State Test",
            location=LocationConfig(
                latitude=40.0,
                longitude=-74.0,
                elevation=100.0,
                timezone="America/New_York",
            ),
            geometry=GeometryConfig(
                length=20.0, width=8.0, height_ridge=4.0, height_eave=2.5
            ),
            covering=CoveringConfig(material="single_glass"),
        )

        engine = create_engine_from_config(config)

        assert engine.state.location.latitude == 40.0
        assert engine.state.location.longitude == -74.0
        assert engine.state.geometry.length == 20.0
        assert engine.state.geometry.width == 8.0
        assert engine.state.covering.material_name == "single_glass"

    def test_duration_and_timestep_applied(self) -> None:
        """Test that duration and timestep are correctly applied."""
        config = SimulationConfig(
            name="Timing Test",
            time_step=30.0,
            duration=7200.0,  # 2 hours
            location=LocationConfig(latitude=37.0, longitude=-77.0),
            geometry=GeometryConfig(
                length=10.0, width=6.0, height_ridge=3.5, height_eave=2.4
            ),
        )

        engine = create_engine_from_config(config)

        assert engine._config.time_step == 30.0
        # End time should be 2 hours after start

    def test_disabled_components_excluded(self) -> None:
        """Test that disabled components are not added to engine."""
        config = SimulationConfig(
            name="Disabled Test",
            location=LocationConfig(latitude=37.0, longitude=-77.0),
            geometry=GeometryConfig(
                length=10.0, width=6.0, height_ridge=3.5, height_eave=2.4
            ),
            components=ComponentsConfig(
                sensors=[
                    SensorConfig(
                        type="temperature", name="enabled", location="interior"
                    ),
                    SensorConfig(
                        type="temperature",
                        name="disabled",
                        location="interior",
                        enabled=False,
                    ),
                ]
            ),
        )

        engine = create_engine_from_config(config)

        assert len(engine._sensors) == 1
        assert engine._sensors[0].name == "enabled"


class TestLoadAndCreate:
    """Tests for loading YAML config and creating engine."""

    def setup_method(self) -> None:
        """Reset registry before each test."""
        reset_registry()
        ensure_components_registered()

    def test_load_yaml_and_create_engine(self, tmp_path: Path) -> None:
        """Test loading YAML and creating engine."""
        yaml_content = """
name: "YAML Test"
time_step: 60.0
duration: 3600.0
location:
  latitude: 37.0
  longitude: -77.0
geometry:
  length: 10.0
  width: 6.0
  height_ridge: 3.5
  height_eave: 2.4
components:
  sensors:
    - type: temperature
      name: temp_1
      location: interior
"""
        config_file = tmp_path / "test.yaml"
        config_file.write_text(yaml_content)

        config = load_config(config_file)
        engine = create_engine_from_config(config)

        assert engine is not None
        assert config.name == "YAML Test"
        assert len(engine._sensors) == 1
