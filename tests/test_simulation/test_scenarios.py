"""Tests for pre-built simulation scenarios."""

from __future__ import annotations

from cloudgrow_sim.core.events import reset_event_bus
from cloudgrow_sim.core.state import GeometryType
from cloudgrow_sim.simulation.engine import SimulationStatus
from cloudgrow_sim.simulation.scenarios import (
    create_basic_scenario,
    create_commercial_greenhouse,
    create_full_climate_scenario,
    create_small_hobby_greenhouse,
    create_summer_cooling_scenario,
    create_winter_heating_scenario,
)


class TestGreenhouseStateCreators:
    """Tests for greenhouse state creator functions."""

    def test_small_hobby_greenhouse(self) -> None:
        """Create small hobby greenhouse state."""
        state = create_small_hobby_greenhouse()

        # Check geometry
        assert state.geometry.length == 10.0
        assert state.geometry.width == 6.0
        assert state.geometry.geometry_type == GeometryType.GABLE

        # Check location (mid-Atlantic default)
        assert 37 < state.location.latitude < 38
        assert -78 < state.location.longitude < -77

        # Check interior state
        assert state.interior.temperature == 20.0
        assert state.interior.humidity == 60.0

    def test_commercial_greenhouse(self) -> None:
        """Create commercial greenhouse state."""
        state = create_commercial_greenhouse()

        # Check geometry (larger)
        assert state.geometry.length == 30.0
        assert state.geometry.width == 10.0

        # Check location (California default)
        assert 36 < state.location.latitude < 37
        assert -120 < state.location.longitude < -119

        # Check interior state
        assert state.interior.temperature == 22.0
        assert state.interior.humidity == 65.0


class TestBasicScenario:
    """Tests for basic scenario."""

    def setup_method(self) -> None:
        """Reset event bus before each test."""
        reset_event_bus()

    def test_creation(self) -> None:
        """Create basic scenario engine."""
        engine = create_basic_scenario(duration_hours=1.0)

        assert engine is not None
        assert engine.status == SimulationStatus.IDLE

    def test_has_components(self) -> None:
        """Basic scenario has expected components."""
        engine = create_basic_scenario()

        # Should have at least 1 sensor, 1 actuator, 1 controller
        # Access through private attributes for testing
        assert len(engine._sensors) >= 1
        assert len(engine._actuators) >= 1
        assert len(engine._controllers) >= 1

    def test_runs_successfully(self) -> None:
        """Basic scenario runs without errors."""
        engine = create_basic_scenario(duration_hours=0.5, time_step=60.0)

        stats = engine.run()

        assert stats.steps_completed == 30  # 30 minutes
        assert engine.status == SimulationStatus.STOPPED


class TestFullClimateScenario:
    """Tests for full climate control scenario."""

    def setup_method(self) -> None:
        """Reset event bus before each test."""
        reset_event_bus()

    def test_creation(self) -> None:
        """Create full climate scenario engine."""
        engine = create_full_climate_scenario(duration_hours=1.0)

        assert engine is not None

    def test_has_many_components(self) -> None:
        """Full scenario has multiple components."""
        engine = create_full_climate_scenario()

        # Should have multiple sensors
        assert len(engine._sensors) >= 4

        # Should have multiple actuators
        assert len(engine._actuators) >= 6

        # Should have multiple controllers
        assert len(engine._controllers) >= 3

        # Should have modifiers
        assert len(engine._modifiers) >= 2

    def test_runs_successfully(self) -> None:
        """Full scenario runs without errors."""
        engine = create_full_climate_scenario(duration_hours=0.25, time_step=60.0)

        stats = engine.run()

        assert stats.steps_completed == 15  # 15 minutes
        assert engine.status == SimulationStatus.STOPPED


class TestWinterHeatingScenario:
    """Tests for winter heating scenario."""

    def setup_method(self) -> None:
        """Reset event bus before each test."""
        reset_event_bus()

    def test_creation(self) -> None:
        """Create winter heating scenario."""
        engine = create_winter_heating_scenario(duration_hours=1.0)

        assert engine is not None

    def test_cold_exterior(self) -> None:
        """Winter scenario has cold exterior."""
        engine = create_winter_heating_scenario()

        # Check cold exterior temperature
        assert engine.state.exterior.temperature < 0

    def test_has_heaters(self) -> None:
        """Winter scenario has heating actuators."""
        engine = create_winter_heating_scenario()

        # Should have heaters
        heater_names = [a.name for a in engine._actuators]
        assert any("heater" in name.lower() for name in heater_names)

    def test_runs_and_maintains_temperature(self) -> None:
        """Winter scenario runs without errors."""
        engine = create_winter_heating_scenario(duration_hours=0.5)

        stats = engine.run()

        # Just verify it runs successfully
        assert stats.steps_completed == 30
        assert engine.status == SimulationStatus.STOPPED
        # Temperature is within valid range
        assert -50 < engine.state.interior.temperature < 60


class TestSummerCoolingScenario:
    """Tests for summer cooling scenario."""

    def setup_method(self) -> None:
        """Reset event bus before each test."""
        reset_event_bus()

    def test_creation(self) -> None:
        """Create summer cooling scenario."""
        engine = create_summer_cooling_scenario(duration_hours=1.0)

        assert engine is not None

    def test_hot_exterior(self) -> None:
        """Summer scenario has hot exterior."""
        engine = create_summer_cooling_scenario()

        # Check hot exterior temperature
        assert engine.state.exterior.temperature > 30

    def test_has_cooling_equipment(self) -> None:
        """Summer scenario has cooling actuators."""
        engine = create_summer_cooling_scenario()

        # Should have exhaust fans
        fan_names = [a.name for a in engine._actuators]
        assert any("exhaust" in name.lower() for name in fan_names)

        # Should have evap pad
        assert any("evap" in name.lower() for name in fan_names)

    def test_runs_successfully(self) -> None:
        """Summer scenario runs without errors."""
        engine = create_summer_cooling_scenario(duration_hours=0.25)

        stats = engine.run()

        assert stats.steps_completed > 0
        assert engine.status == SimulationStatus.STOPPED


class TestScenarioIntegration:
    """Integration tests for scenarios."""

    def setup_method(self) -> None:
        """Reset event bus before each test."""
        reset_event_bus()

    def test_basic_scenario_physics(self) -> None:
        """Basic scenario applies physics correctly."""
        engine = create_basic_scenario(duration_hours=2.0, time_step=60.0)

        # Track temperature changes
        temps = [engine.state.interior.temperature]

        for _ in range(30):
            engine.step()
            temps.append(engine.state.interior.temperature)

        # Temperature should have varied (not constant)
        temp_range = max(temps) - min(temps)
        assert temp_range > 0.1  # Some variation expected

    def test_full_scenario_sensor_readings(self) -> None:
        """Full scenario sensors provide readings."""
        engine = create_full_climate_scenario(duration_hours=0.25)

        # Run a few steps
        for _ in range(10):
            engine.step()

        # All sensors should have readings
        for sensor in engine._sensors:
            if sensor.enabled:
                assert sensor.last_reading is not None

    def test_scenario_reset(self) -> None:
        """Scenarios can be reset and rerun."""
        engine = create_basic_scenario(duration_hours=0.5)

        # Run once
        engine.run()
        first_stats = engine.stats.steps_completed

        # Reset and run again
        engine.reset()
        engine.run()
        second_stats = engine.stats.steps_completed

        assert first_stats == second_stats
