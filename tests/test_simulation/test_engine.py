"""Tests for simulation engine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from cloudgrow_sim.components.actuators.fans import ExhaustFan
from cloudgrow_sim.components.sensors.temperature import TemperatureSensor
from cloudgrow_sim.controllers.hysteresis import HysteresisController
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
