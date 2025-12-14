"""Tests for event system."""

from __future__ import annotations

from datetime import datetime

import pytest

from cloudgrow_sim.core.events import (
    Event,
    EventBus,
    EventType,
    emit_alarm,
    emit_sensor_reading,
    emit_state_update,
    get_event_bus,
    reset_event_bus,
)


class TestEventType:
    """Tests for EventType enum."""

    def test_simulation_events(self) -> None:
        """Simulation events exist."""
        assert EventType.SIMULATION_START.value == "simulation.start"
        assert EventType.SIMULATION_STOP.value == "simulation.stop"
        assert EventType.SIMULATION_STEP.value == "simulation.step"

    def test_state_events(self) -> None:
        """State events exist."""
        assert EventType.STATE_UPDATE.value == "state.update"
        assert EventType.TEMPERATURE_CHANGE.value == "state.temperature"
        assert EventType.HUMIDITY_CHANGE.value == "state.humidity"

    def test_alarm_events(self) -> None:
        """Alarm events exist."""
        assert EventType.ALARM_HIGH_TEMP.value == "alarm.high_temperature"
        assert EventType.ALARM_LOW_TEMP.value == "alarm.low_temperature"


class TestEvent:
    """Tests for Event dataclass."""

    def test_creation(self) -> None:
        """Create event with all fields."""
        event = Event(
            event_type=EventType.SIMULATION_START,
            source="test",
            data={"key": "value"},
            message="Test message",
        )

        assert event.event_type == EventType.SIMULATION_START
        assert event.source == "test"
        assert event.data == {"key": "value"}
        assert event.message == "Test message"
        assert event.timestamp is not None

    def test_default_timestamp(self) -> None:
        """Event gets automatic timestamp."""
        event = Event(event_type=EventType.SIMULATION_START)
        assert isinstance(event.timestamp, datetime)

    def test_to_dict(self) -> None:
        """Convert event to dictionary."""
        event = Event(
            event_type=EventType.SENSOR_READING,
            source="sensor1",
            data={"temperature": 25.0},
        )

        d = event.to_dict()
        assert d["event_type"] == "component.sensor_reading"
        assert d["source"] == "sensor1"
        assert d["data"]["temperature"] == 25.0

    def test_str(self) -> None:
        """String representation."""
        event = Event(
            event_type=EventType.ALARM_HIGH_TEMP,
            source="controller",
            message="Temperature exceeded 35°C",
        )

        s = str(event)
        assert "alarm.high_temperature" in s
        assert "controller" in s


class TestEventBus:
    """Tests for EventBus class."""

    def test_subscribe_and_emit(self) -> None:
        """Subscribe to events and receive them."""
        bus = EventBus()
        received = []

        def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.SIMULATION_START, handler)
        bus.emit(Event(event_type=EventType.SIMULATION_START))

        assert len(received) == 1
        assert received[0].event_type == EventType.SIMULATION_START

    def test_subscribe_string(self) -> None:
        """Subscribe using string event type."""
        bus = EventBus()
        received = []

        def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe("simulation.start", handler)
        bus.emit(Event(event_type=EventType.SIMULATION_START))

        assert len(received) == 1

    def test_subscribe_all(self) -> None:
        """Subscribe to all events with wildcard."""
        bus = EventBus()
        received = []

        def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe("*", handler)
        bus.emit(Event(event_type=EventType.SIMULATION_START))
        bus.emit(Event(event_type=EventType.SIMULATION_STOP))
        bus.emit(Event(event_type=EventType.SENSOR_READING))

        assert len(received) == 3

    def test_unsubscribe(self) -> None:
        """Unsubscribe from events."""
        bus = EventBus()
        received = []

        def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.SIMULATION_START, handler)
        bus.unsubscribe(EventType.SIMULATION_START, handler)
        bus.emit(Event(event_type=EventType.SIMULATION_START))

        assert len(received) == 0

    def test_multiple_handlers(self) -> None:
        """Multiple handlers for same event."""
        bus = EventBus()
        count = {"value": 0}

        def handler1(event: Event) -> None:
            count["value"] += 1

        def handler2(event: Event) -> None:
            count["value"] += 10

        bus.subscribe(EventType.SIMULATION_START, handler1)
        bus.subscribe(EventType.SIMULATION_START, handler2)
        bus.emit(Event(event_type=EventType.SIMULATION_START))

        assert count["value"] == 11

    def test_emit_simple(self) -> None:
        """Emit event using emit_simple convenience method."""
        bus = EventBus()
        received = []

        def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.SENSOR_READING, handler)
        bus.emit_simple(
            EventType.SENSOR_READING,
            source="sensor1",
            temperature=25.0,
            humidity=60.0,
        )

        assert len(received) == 1
        assert received[0].data["temperature"] == 25.0
        assert received[0].data["humidity"] == 60.0

    def test_history(self) -> None:
        """Events are stored in history."""
        bus = EventBus()
        bus.emit(Event(event_type=EventType.SIMULATION_START))
        bus.emit(Event(event_type=EventType.SIMULATION_STEP))
        bus.emit(Event(event_type=EventType.SIMULATION_STOP))

        history = bus.get_history()
        assert len(history) == 3

    def test_history_filtered(self) -> None:
        """Filter history by event type."""
        bus = EventBus()
        bus.emit(Event(event_type=EventType.SIMULATION_START))
        bus.emit(Event(event_type=EventType.SENSOR_READING, source="s1"))
        bus.emit(Event(event_type=EventType.SENSOR_READING, source="s2"))

        history = bus.get_history(event_type=EventType.SENSOR_READING)
        assert len(history) == 2

    def test_history_filtered_by_source(self) -> None:
        """Filter history by source."""
        bus = EventBus()
        bus.emit(Event(event_type=EventType.SENSOR_READING, source="s1"))
        bus.emit(Event(event_type=EventType.SENSOR_READING, source="s2"))
        bus.emit(Event(event_type=EventType.SENSOR_READING, source="s1"))

        history = bus.get_history(source="s1")
        assert len(history) == 2

    def test_history_limit(self) -> None:
        """History respects max_history."""
        bus = EventBus(max_history=5)
        for _ in range(10):
            bus.emit(Event(event_type=EventType.SIMULATION_STEP))

        history = bus.get_history()
        assert len(history) == 5

    def test_clear_history(self) -> None:
        """Clear history."""
        bus = EventBus()
        bus.emit(Event(event_type=EventType.SIMULATION_START))
        bus.clear_history()

        assert len(bus.get_history()) == 0

    def test_clear_handlers(self) -> None:
        """Clear all handlers."""
        bus = EventBus()

        def handler(event: Event) -> None:
            pass

        bus.subscribe(EventType.SIMULATION_START, handler)
        bus.clear_handlers()
        # Should not raise even if handler would have been called
        bus.emit(Event(event_type=EventType.SIMULATION_START))


class TestGlobalEventBus:
    """Tests for global event bus functions."""

    def setup_method(self) -> None:
        """Reset event bus before each test."""
        reset_event_bus()

    def test_get_event_bus_singleton(self) -> None:
        """get_event_bus returns same instance."""
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2

    def test_reset_event_bus(self) -> None:
        """reset_event_bus creates new instance."""
        bus1 = get_event_bus()
        bus1.emit(Event(event_type=EventType.SIMULATION_START))

        reset_event_bus()
        bus2 = get_event_bus()

        assert len(bus2.get_history()) == 0


class TestConvenienceFunctions:
    """Tests for convenience emit functions."""

    def setup_method(self) -> None:
        """Reset event bus before each test."""
        reset_event_bus()

    def test_emit_state_update(self) -> None:
        """emit_state_update creates correct event."""
        bus = get_event_bus()
        received = []

        def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.STATE_UPDATE, handler)
        emit_state_update("engine", temperature=25.0, humidity=60.0)

        assert len(received) == 1
        assert received[0].source == "engine"
        assert received[0].data["temperature"] == 25.0

    def test_emit_sensor_reading(self) -> None:
        """emit_sensor_reading creates correct event."""
        bus = get_event_bus()
        received = []

        def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.SENSOR_READING, handler)
        emit_sensor_reading("temp_sensor", {"temperature": 25.5})

        assert len(received) == 1
        assert received[0].source == "temp_sensor"
        assert received[0].data["readings"]["temperature"] == 25.5

    def test_emit_alarm(self) -> None:
        """emit_alarm creates correct event."""
        bus = get_event_bus()
        received = []

        def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.ALARM_HIGH_TEMP, handler)
        emit_alarm(EventType.ALARM_HIGH_TEMP, "monitor", "Temperature too high!")

        assert len(received) == 1
        assert received[0].message == "Temperature too high!"


class TestEventBusRobustness:
    """Tests for EventBus error handling and edge cases."""

    def test_history_fifo_behavior(self) -> None:
        """Oldest events are removed first when history fills (deque FIFO)."""
        bus = EventBus(max_history=3)

        bus.emit(Event(event_type=EventType.SIMULATION_START, data={"order": 1}))
        bus.emit(Event(event_type=EventType.SIMULATION_STEP, data={"order": 2}))
        bus.emit(Event(event_type=EventType.SIMULATION_STEP, data={"order": 3}))
        bus.emit(Event(event_type=EventType.SIMULATION_STOP, data={"order": 4}))

        history = bus.get_history()
        assert len(history) == 3
        # Should have events 2, 3, 4 (oldest event 1 removed)
        assert history[0].data["order"] == 2
        assert history[1].data["order"] == 3
        assert history[2].data["order"] == 4

    def test_handler_exception_does_not_stop_other_handlers(self) -> None:
        """A failing handler doesn't prevent other handlers from running."""
        bus = EventBus()
        results: list[str] = []

        def good_handler_1(event: Event) -> None:
            results.append("handler1")

        def bad_handler(event: Event) -> None:
            raise ValueError("Handler failure!")

        def good_handler_2(event: Event) -> None:
            results.append("handler2")

        bus.subscribe(EventType.SIMULATION_START, good_handler_1)
        bus.subscribe(EventType.SIMULATION_START, bad_handler)
        bus.subscribe(EventType.SIMULATION_START, good_handler_2)

        # Should not raise, and all good handlers should run
        bus.emit(Event(event_type=EventType.SIMULATION_START))

        assert "handler1" in results
        assert "handler2" in results

    def test_wildcard_handler_exception_isolated(self) -> None:
        """Wildcard handler exceptions don't affect other handlers."""
        bus = EventBus()
        results: list[str] = []

        def specific_handler(event: Event) -> None:
            results.append("specific")

        def bad_wildcard(event: Event) -> None:
            raise RuntimeError("Wildcard failure!")

        def good_wildcard(event: Event) -> None:
            results.append("wildcard")

        bus.subscribe(EventType.SIMULATION_START, specific_handler)
        bus.subscribe_all(bad_wildcard)
        bus.subscribe_all(good_wildcard)

        bus.emit(Event(event_type=EventType.SIMULATION_START))

        assert "specific" in results
        assert "wildcard" in results

    def test_handler_exception_is_logged(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Handler exceptions are logged with useful context."""
        import logging

        bus = EventBus()

        def failing_handler(event: Event) -> None:
            raise ValueError("Test failure!")

        bus.subscribe(EventType.SIMULATION_START, failing_handler)

        with caplog.at_level(logging.ERROR):
            bus.emit(Event(event_type=EventType.SIMULATION_START, source="test_source"))

        assert "failing_handler" in caplog.text
        assert "simulation.start" in caplog.text
        assert "test_source" in caplog.text
