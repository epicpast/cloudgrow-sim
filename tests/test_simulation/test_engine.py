"""Tests for simulation engine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from cloudgrow_sim.components.actuators.fans import ExhaustFan
from cloudgrow_sim.components.sensors.temperature import TemperatureSensor
from cloudgrow_sim.controllers.hysteresis import HysteresisController
from cloudgrow_sim.core.base import Actuator
from cloudgrow_sim.core.events import EventType, get_event_bus, reset_event_bus
from cloudgrow_sim.core.state import (
    COVERING_MATERIALS,
    AirState,
    GeometryType,
    GreenhouseGeometry,
    GreenhouseState,
    Location,
)
from cloudgrow_sim.simulation.engine import (
    _MAX_TEMP_CHANGE_RATE,
    SimulationConfig,
    SimulationEngine,
    SimulationStats,
    SimulationStatus,
)
from cloudgrow_sim.simulation.weather import SyntheticWeatherSource


def create_test_state() -> GreenhouseState:
    """Create a simple test state."""
    return GreenhouseState(
        interior=AirState(temperature=22.0, humidity=55.0, co2_ppm=400.0),
        exterior=AirState(temperature=15.0, humidity=60.0, co2_ppm=400.0),
        time=datetime(2025, 6, 21, 6, 0, tzinfo=UTC),
        location=Location(
            latitude=37.5, longitude=-77.4, elevation=50.0, timezone_str="UTC"
        ),
        geometry=GreenhouseGeometry(
            geometry_type=GeometryType.GABLE,
            length=10.0,
            width=6.0,
            height_eave=2.4,
            height_ridge=3.5,
        ),
        covering=COVERING_MATERIALS["double_polyethylene"],
        solar_radiation=0.0,
        wind_speed=2.0,
        wind_direction=180.0,
    )


class TestSimulationConfig:
    """Tests for SimulationConfig."""

    def test_default_config(self) -> None:
        """Default configuration values."""
        config = SimulationConfig()
        assert config.time_step == 60.0
        assert config.real_time_factor == 0.0
        assert config.emit_events is True
        assert config.emit_interval == 1

    def test_custom_config(self) -> None:
        """Custom configuration values."""
        start = datetime(2025, 1, 1, 0, 0, tzinfo=UTC)
        end = datetime(2025, 1, 2, 0, 0, tzinfo=UTC)
        config = SimulationConfig(
            time_step=30.0,
            start_time=start,
            end_time=end,
            emit_events=False,
        )
        assert config.time_step == 30.0
        assert config.start_time == start
        assert config.end_time == end
        assert config.emit_events is False


class TestSimulationStats:
    """Tests for SimulationStats."""

    def test_default_stats(self) -> None:
        """Default statistics values."""
        stats = SimulationStats()
        assert stats.steps_completed == 0
        assert stats.avg_step_time == 0.0

    def test_avg_step_time(self) -> None:
        """Average step time calculation."""
        stats = SimulationStats(
            steps_completed=100,
            wall_time=timedelta(seconds=1.0),
        )
        assert stats.avg_step_time == 10.0  # 10 ms per step


class TestSimulationEngine:
    """Tests for SimulationEngine."""

    def setup_method(self) -> None:
        """Reset event bus before each test."""
        reset_event_bus()

    def test_initialization(self) -> None:
        """Engine initializes with state and weather."""
        state = create_test_state()
        config = SimulationConfig(start_time=state.time)
        engine = SimulationEngine(state, config=config)

        assert engine.state == state
        assert engine.status == SimulationStatus.IDLE
        assert engine.current_time == datetime(2025, 6, 21, 6, 0, tzinfo=UTC)

    def test_add_components(self) -> None:
        """Add sensors, actuators, and controllers."""
        state = create_test_state()
        engine = SimulationEngine(state)

        # Add sensor
        sensor = TemperatureSensor("temp_test")
        engine.add_sensor(sensor)

        # Add actuator
        fan = ExhaustFan("fan_test", max_flow_rate=1.0, power_consumption=500.0)
        engine.add_actuator(fan)

        # Add controller
        controller = HysteresisController("ctrl_test", setpoint=28.0, hysteresis=2.0)
        engine.add_controller(controller)

        # Verify they were added (by running a step)
        engine.step()

    def test_single_step(self) -> None:
        """Execute a single simulation step."""
        state = create_test_state()
        start_time = state.time
        config = SimulationConfig(time_step=60.0, start_time=start_time)
        engine = SimulationEngine(state, config=config)

        result = engine.step()

        assert result is True  # Should continue
        assert engine.current_time == start_time + timedelta(seconds=60)
        assert engine.stats.steps_completed == 1

    def test_run_multiple_steps(self) -> None:
        """Run simulation for multiple steps."""
        state = create_test_state()
        config = SimulationConfig(
            time_step=60.0,
            start_time=state.time,
            emit_events=False,
        )
        engine = SimulationEngine(state, config=config)

        stats = engine.run(steps=10)

        assert stats.steps_completed == 10
        assert engine.status == SimulationStatus.STOPPED

    def test_run_until_end_time(self) -> None:
        """Run simulation until end time."""
        state = create_test_state()
        end_time = state.time + timedelta(hours=1)
        config = SimulationConfig(
            time_step=60.0,
            start_time=state.time,
            end_time=end_time,
            emit_events=False,
        )
        engine = SimulationEngine(state, config=config)

        stats = engine.run()

        # 1 hour / 60 seconds = 60 steps
        assert stats.steps_completed == 60
        assert engine.current_time >= end_time

    def test_exterior_updates_from_weather(self) -> None:
        """Exterior conditions update from weather source."""
        state = create_test_state()
        weather = SyntheticWeatherSource()
        engine = SimulationEngine(state, weather=weather)

        # Run a few steps to let weather change
        engine.run(steps=10)

        # Exterior should be updated (may or may not differ)
        assert engine.state.exterior.temperature is not None

    def test_interior_state_changes(self) -> None:
        """Interior state changes through simulation."""
        state = create_test_state()
        config = SimulationConfig(
            time_step=60.0,
            start_time=state.time,
            emit_events=False,
        )
        engine = SimulationEngine(state, config=config)

        # Run simulation
        engine.run(steps=60)

        # Temperature should have changed (due to heat exchange)
        # The exact direction depends on weather/physics
        # Just verify it's a valid temperature
        assert -50 < engine.state.interior.temperature < 100

    def test_reset(self) -> None:
        """Reset simulation to initial state."""
        state = create_test_state()
        initial_time = state.time
        config = SimulationConfig(
            time_step=60.0,
            start_time=initial_time,
            emit_events=False,
        )
        engine = SimulationEngine(state, config=config)

        # Run some steps
        engine.run(steps=10)
        assert engine.stats.steps_completed == 10

        # Reset
        engine.reset()

        assert engine.current_time == initial_time
        assert engine.stats.steps_completed == 0
        assert engine.status == SimulationStatus.IDLE

    def test_reset_with_new_state(self) -> None:
        """Reset simulation with new initial state."""
        state = create_test_state()
        config = SimulationConfig(emit_events=False)
        engine = SimulationEngine(state, config=config)

        engine.run(steps=5)

        # Create new state
        new_state = create_test_state()
        new_state = GreenhouseState(
            interior=AirState(temperature=30.0, humidity=70.0, co2_ppm=500.0),
            exterior=new_state.exterior,
            time=new_state.time,
            location=new_state.location,
            geometry=new_state.geometry,
            covering=new_state.covering,
        )

        engine.reset(new_state)

        assert engine.state.interior.temperature == 30.0
        assert engine.state.interior.humidity == 70.0


class TestSimulationEngineEvents:
    """Tests for simulation engine events."""

    def setup_method(self) -> None:
        """Reset event bus before each test."""
        reset_event_bus()

    def test_emits_start_event(self) -> None:
        """Engine emits start event."""
        state = create_test_state()
        config = SimulationConfig(
            start_time=state.time,
            emit_events=True,
        )
        engine = SimulationEngine(state, config=config)

        events: list = []
        bus = get_event_bus()
        bus.subscribe(EventType.SIMULATION_START, lambda e: events.append(e))

        engine.run(steps=1)

        assert len(events) == 1
        assert events[0].event_type == EventType.SIMULATION_START

    def test_emits_stop_event(self) -> None:
        """Engine emits stop event."""
        state = create_test_state()
        config = SimulationConfig(
            start_time=state.time,
            emit_events=True,
        )
        engine = SimulationEngine(state, config=config)

        events: list = []
        bus = get_event_bus()
        bus.subscribe(EventType.SIMULATION_STOP, lambda e: events.append(e))

        engine.run(steps=5)

        assert len(events) == 1
        assert events[0].event_type == EventType.SIMULATION_STOP

    def test_emits_state_updates(self) -> None:
        """Engine emits state update events."""
        state = create_test_state()
        config = SimulationConfig(
            start_time=state.time,
            emit_events=True,
            emit_interval=1,  # Every step
        )
        engine = SimulationEngine(state, config=config)

        events: list = []
        bus = get_event_bus()
        bus.subscribe(EventType.STATE_UPDATE, lambda e: events.append(e))

        engine.run(steps=5)

        assert len(events) == 5  # One per step
        for event in events:
            assert "interior_temperature" in event.data
            assert "exterior_temperature" in event.data

    def test_emit_interval(self) -> None:
        """Emit interval controls event frequency."""
        state = create_test_state()
        config = SimulationConfig(
            start_time=state.time,
            emit_events=True,
            emit_interval=5,  # Every 5 steps
        )
        engine = SimulationEngine(state, config=config)

        events: list = []
        bus = get_event_bus()
        bus.subscribe(EventType.STATE_UPDATE, lambda e: events.append(e))

        engine.run(steps=20)

        # Should emit at steps 0, 5, 10, 15 = 4 events
        assert len(events) == 4


class TestSimulationEngineWithComponents:
    """Tests for simulation engine with components."""

    def setup_method(self) -> None:
        """Reset event bus before each test."""
        reset_event_bus()

    def test_sensors_read(self) -> None:
        """Sensors are read during simulation."""
        state = create_test_state()
        config = SimulationConfig(emit_events=False)
        engine = SimulationEngine(state, config=config)

        sensor = TemperatureSensor("temp_sensor", location="interior")
        engine.add_sensor(sensor)

        engine.run(steps=5)

        # Sensor should have been updated
        assert sensor.last_reading is not None
        assert "temperature" in sensor.last_reading

    def test_controllers_execute(self) -> None:
        """Controllers execute during simulation."""
        state = create_test_state()
        config = SimulationConfig(emit_events=False)
        engine = SimulationEngine(state, config=config)

        controller = HysteresisController(
            "vent_ctrl",
            setpoint=25.0,
            hysteresis=2.0,
        )
        engine.add_controller(controller)

        engine.run(steps=5)

        # Controller should have computed output
        assert controller.output is not None

    def test_actuators_apply(self) -> None:
        """Actuators apply effects during simulation."""
        state = create_test_state()
        config = SimulationConfig(emit_events=False)
        engine = SimulationEngine(state, config=config)

        fan = ExhaustFan(
            "exhaust_fan",
            max_flow_rate=1.0,
            power_consumption=500.0,
        )
        fan.set_output(1.0)  # Full on
        engine.add_actuator(fan)

        engine.run(steps=5)

        # Fan should have provided effect
        effect = fan.get_effect(state)
        assert "ventilation_rate" in effect


class TestTemperatureRateLimiting:
    """Tests for temperature change rate limiting."""

    def setup_method(self) -> None:
        """Reset event bus before each test."""
        reset_event_bus()

    def test_temperature_change_rate_limited(self) -> None:
        """Test that temperature changes are rate-limited."""
        state = create_test_state()
        # Use 1 second time step for easier calculation
        config = SimulationConfig(
            time_step=1.0,
            start_time=state.time,
            emit_events=False,
        )
        engine = SimulationEngine(state, config=config)
        initial_temp = engine.state.interior.temperature

        engine.step()

        max_change = _MAX_TEMP_CHANGE_RATE * 1.0  # 1 second time step
        actual_change = abs(engine.state.interior.temperature - initial_temp)
        # Allow small tolerance for floating point
        assert actual_change <= max_change + 0.001

    def test_temperature_change_scales_with_time_step(self) -> None:
        """Test that maximum temperature change scales with time step."""
        state1 = create_test_state()
        state2 = create_test_state()

        # Short time step
        config1 = SimulationConfig(
            time_step=1.0,
            start_time=state1.time,
            emit_events=False,
        )
        engine1 = SimulationEngine(state1, config=config1)
        initial_temp1 = engine1.state.interior.temperature
        engine1.step()
        change1 = abs(engine1.state.interior.temperature - initial_temp1)

        # Longer time step
        config2 = SimulationConfig(
            time_step=60.0,
            start_time=state2.time,
            emit_events=False,
        )
        engine2 = SimulationEngine(state2, config=config2)
        initial_temp2 = engine2.state.interior.temperature
        engine2.step()
        change2 = abs(engine2.state.interior.temperature - initial_temp2)

        # Max change for 60s should be 60x max change for 1s
        max_change_1s = _MAX_TEMP_CHANGE_RATE * 1.0
        max_change_60s = _MAX_TEMP_CHANGE_RATE * 60.0

        assert change1 <= max_change_1s + 0.001
        assert change2 <= max_change_60s + 0.001

    def test_temperature_clamped_to_lower_bound(self) -> None:
        """Test temperature is clamped to valid lower bound (-50)."""
        # Create state with very cold conditions to drive temperature down
        state = GreenhouseState(
            interior=AirState(temperature=-45.0, humidity=30.0, co2_ppm=400.0),
            exterior=AirState(temperature=-50.0, humidity=30.0, co2_ppm=400.0),
            time=datetime(2025, 1, 15, 2, 0, tzinfo=UTC),
            location=Location(
                latitude=70.0, longitude=25.0, elevation=50.0, timezone_str="UTC"
            ),
            geometry=GreenhouseGeometry(
                geometry_type=GeometryType.GABLE,
                length=10.0,
                width=6.0,
                height_eave=2.4,
                height_ridge=3.5,
            ),
            covering=COVERING_MATERIALS["double_polyethylene"],
            solar_radiation=0.0,
            wind_speed=10.0,
            wind_direction=0.0,
        )

        config = SimulationConfig(
            time_step=60.0,
            start_time=state.time,
            emit_events=False,
        )
        engine = SimulationEngine(state, config=config)

        # Run many steps to try to push temperature below -50
        engine.run(steps=100)

        # Temperature should never go below -50 (AirState valid range)
        assert engine.state.interior.temperature >= -50.0

    def test_temperature_clamped_to_upper_bound(self) -> None:
        """Test temperature is clamped to valid upper bound (60)."""
        # Create state with extreme hot conditions
        state = GreenhouseState(
            interior=AirState(temperature=55.0, humidity=20.0, co2_ppm=400.0),
            exterior=AirState(temperature=50.0, humidity=15.0, co2_ppm=400.0),
            time=datetime(2025, 7, 15, 14, 0, tzinfo=UTC),
            location=Location(
                latitude=25.0, longitude=-110.0, elevation=50.0, timezone_str="UTC"
            ),
            geometry=GreenhouseGeometry(
                geometry_type=GeometryType.GABLE,
                length=10.0,
                width=6.0,
                height_eave=2.4,
                height_ridge=3.5,
            ),
            covering=COVERING_MATERIALS["double_polyethylene"],
            solar_radiation=1200.0,  # High solar radiation
            wind_speed=0.5,
            wind_direction=180.0,
        )

        config = SimulationConfig(
            time_step=60.0,
            start_time=state.time,
            emit_events=False,
        )
        engine = SimulationEngine(state, config=config)

        # Run many steps to try to push temperature above 60
        engine.run(steps=100)

        # Temperature should never exceed 60 (AirState valid range)
        assert engine.state.interior.temperature <= 60.0


class MockCO2Injector(Actuator):
    """Mock CO2 injector actuator for testing."""

    def __init__(
        self,
        name: str,
        injection_rate: float = 0.0001,
    ) -> None:
        """Initialize mock CO2 injector.

        Args:
            name: Actuator name.
            injection_rate: CO2 injection rate in m^3/s of pure CO2.
        """
        super().__init__(name)
        self._injection_rate = injection_rate
        self._output = 0.0

    def set_output(self, value: float) -> None:
        """Set output level (0-1)."""
        self._output = max(0.0, min(1.0, value))

    def get_effect(self, state: GreenhouseState) -> dict[str, Any]:
        """Get CO2 injection effect."""
        del state  # Unused
        return {"co2_injection_rate": self._injection_rate * self._output}

    def _apply_effect(self, dt: float, state: GreenhouseState) -> None:
        """Apply effect (handled by engine)."""
        del dt, state  # Unused


class TestCO2Balance:
    """Tests for CO2 balance calculations."""

    def setup_method(self) -> None:
        """Reset event bus before each test."""
        reset_event_bus()

    def test_co2_ventilation_exchange(self) -> None:
        """Test CO2 exchange through ventilation."""
        # Set interior CO2 higher than exterior
        state = GreenhouseState(
            interior=AirState(temperature=22.0, humidity=55.0, co2_ppm=1000.0),
            exterior=AirState(temperature=20.0, humidity=50.0, co2_ppm=400.0),
            time=datetime(2025, 6, 21, 12, 0, tzinfo=UTC),
            location=Location(
                latitude=37.5, longitude=-77.4, elevation=50.0, timezone_str="UTC"
            ),
            geometry=GreenhouseGeometry(
                geometry_type=GeometryType.GABLE,
                length=10.0,
                width=6.0,
                height_eave=2.4,
                height_ridge=3.5,
            ),
            covering=COVERING_MATERIALS["double_polyethylene"],
            solar_radiation=500.0,
            wind_speed=2.0,
            wind_direction=180.0,
        )

        config = SimulationConfig(
            time_step=60.0,
            start_time=state.time,
            emit_events=False,
        )
        engine = SimulationEngine(state, config=config)

        # Add ventilation actuator at full output
        fan = ExhaustFan("vent_fan", max_flow_rate=2.0, power_consumption=500.0)
        fan.set_output(1.0)
        engine.add_actuator(fan)

        initial_co2 = engine.state.interior.co2_ppm

        # Run several steps
        engine.run(steps=60)

        # CO2 should decrease toward exterior level due to ventilation
        assert engine.state.interior.co2_ppm < initial_co2
        # CO2 should be moving toward exterior level (400 ppm)
        assert engine.state.interior.co2_ppm < 1000.0

    def test_co2_injection(self) -> None:
        """Test CO2 injection from actuator."""
        state = create_test_state()
        # Start with low CO2
        state = GreenhouseState(
            interior=AirState(temperature=22.0, humidity=55.0, co2_ppm=400.0),
            exterior=state.exterior,
            time=state.time,
            location=state.location,
            geometry=state.geometry,
            covering=state.covering,
            solar_radiation=0.0,
            wind_speed=0.0,  # No wind to minimize ventilation effects
            wind_direction=0.0,
        )

        config = SimulationConfig(
            time_step=60.0,
            start_time=state.time,
            emit_events=False,
        )
        engine = SimulationEngine(state, config=config)

        # Add CO2 injector
        injector = MockCO2Injector("co2_injector", injection_rate=0.001)
        injector.set_output(1.0)
        engine.add_actuator(injector)

        initial_co2 = engine.state.interior.co2_ppm

        # Run several steps
        engine.run(steps=30)

        # CO2 should increase due to injection
        assert engine.state.interior.co2_ppm > initial_co2

    def test_co2_clamped_to_lower_bound(self) -> None:
        """Test CO2 stays above 200 ppm lower bound."""
        # Create state with low interior CO2 and high ventilation potential
        state = GreenhouseState(
            interior=AirState(temperature=22.0, humidity=55.0, co2_ppm=250.0),
            exterior=AirState(
                temperature=20.0, humidity=50.0, co2_ppm=200.0
            ),  # Exterior at lower bound
            time=datetime(2025, 6, 21, 12, 0, tzinfo=UTC),
            location=Location(
                latitude=37.5, longitude=-77.4, elevation=50.0, timezone_str="UTC"
            ),
            geometry=GreenhouseGeometry(
                geometry_type=GeometryType.GABLE,
                length=10.0,
                width=6.0,
                height_eave=2.4,
                height_ridge=3.5,
            ),
            covering=COVERING_MATERIALS["double_polyethylene"],
            solar_radiation=500.0,
            wind_speed=5.0,
            wind_direction=180.0,
        )

        config = SimulationConfig(
            time_step=60.0,
            start_time=state.time,
            emit_events=False,
        )
        engine = SimulationEngine(state, config=config)

        # Add high ventilation
        fan = ExhaustFan("vent_fan", max_flow_rate=5.0, power_consumption=1000.0)
        fan.set_output(1.0)
        engine.add_actuator(fan)

        # Run many steps
        engine.run(steps=100)

        # CO2 should never go below 200 ppm
        assert engine.state.interior.co2_ppm >= 200.0

    def test_co2_clamped_to_upper_bound(self) -> None:
        """Test CO2 stays below 5000 ppm upper bound."""
        state = create_test_state()
        # Start with high CO2
        state = GreenhouseState(
            interior=AirState(temperature=22.0, humidity=55.0, co2_ppm=4800.0),
            exterior=state.exterior,
            time=state.time,
            location=state.location,
            geometry=state.geometry,
            covering=state.covering,
            solar_radiation=0.0,
            wind_speed=0.0,  # No ventilation
            wind_direction=0.0,
        )

        config = SimulationConfig(
            time_step=60.0,
            start_time=state.time,
            emit_events=False,
        )
        engine = SimulationEngine(state, config=config)

        # Add aggressive CO2 injection
        injector = MockCO2Injector("co2_injector", injection_rate=0.01)
        injector.set_output(1.0)
        engine.add_actuator(injector)

        # Run many steps
        engine.run(steps=100)

        # CO2 should never exceed 5000 ppm
        assert engine.state.interior.co2_ppm <= 5000.0

    def test_co2_equilibrium_with_ventilation(self) -> None:
        """Test CO2 approaches equilibrium with constant ventilation."""
        # Start with elevated interior CO2
        state = GreenhouseState(
            interior=AirState(temperature=22.0, humidity=55.0, co2_ppm=800.0),
            exterior=AirState(temperature=20.0, humidity=50.0, co2_ppm=420.0),
            time=datetime(2025, 6, 21, 12, 0, tzinfo=UTC),
            location=Location(
                latitude=37.5, longitude=-77.4, elevation=50.0, timezone_str="UTC"
            ),
            geometry=GreenhouseGeometry(
                geometry_type=GeometryType.GABLE,
                length=10.0,
                width=6.0,
                height_eave=2.4,
                height_ridge=3.5,
            ),
            covering=COVERING_MATERIALS["double_polyethylene"],
            solar_radiation=500.0,
            wind_speed=2.0,
            wind_direction=180.0,
        )

        config = SimulationConfig(
            time_step=60.0,
            start_time=state.time,
            emit_events=False,
        )
        engine = SimulationEngine(state, config=config)

        # Add moderate ventilation
        fan = ExhaustFan("vent_fan", max_flow_rate=1.0, power_consumption=500.0)
        fan.set_output(0.5)
        engine.add_actuator(fan)

        # Run for extended period
        engine.run(steps=120)

        # CO2 should be closer to exterior level (420 ppm) than initial (800 ppm)
        final_co2 = engine.state.interior.co2_ppm
        distance_from_exterior = abs(final_co2 - 420.0)
        initial_distance = abs(800.0 - 420.0)

        assert distance_from_exterior < initial_distance
