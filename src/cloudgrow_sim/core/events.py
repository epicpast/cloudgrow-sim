"""Event system for greenhouse simulation.

This module provides a simple pub/sub event system for notifying
components and external systems about state changes and simulation events.

Events can be used for:
- Logging state changes
- Triggering alarms
- Updating UI/dashboards
- Recording telemetry
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Standard event types for greenhouse simulation."""

    # Simulation lifecycle
    SIMULATION_START = "simulation.start"
    SIMULATION_STOP = "simulation.stop"
    SIMULATION_STEP = "simulation.step"
    SIMULATION_ERROR = "simulation.error"

    # State changes
    STATE_UPDATE = "state.update"
    TEMPERATURE_CHANGE = "state.temperature"
    HUMIDITY_CHANGE = "state.humidity"
    CO2_CHANGE = "state.co2"

    # Component events
    SENSOR_READING = "component.sensor_reading"
    ACTUATOR_OUTPUT = "component.actuator_output"
    CONTROLLER_OUTPUT = "component.controller_output"

    # Alarms
    ALARM_HIGH_TEMP = "alarm.high_temperature"
    ALARM_LOW_TEMP = "alarm.low_temperature"
    ALARM_HIGH_HUMIDITY = "alarm.high_humidity"
    ALARM_LOW_HUMIDITY = "alarm.low_humidity"
    ALARM_EQUIPMENT_FAULT = "alarm.equipment_fault"

    # Custom events
    CUSTOM = "custom"


@dataclass
class Event:
    """An event in the simulation.

    Attributes:
        event_type: Type of event.
        timestamp: When the event occurred.
        source: Name of the component/system that generated the event.
        data: Event-specific data payload.
        message: Human-readable description of the event.
    """

    event_type: EventType | str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    source: str = "system"
    data: dict[str, Any] = field(default_factory=dict)
    message: str = ""

    def __str__(self) -> str:
        """String representation of the event."""
        event_name = (
            self.event_type.value
            if isinstance(self.event_type, EventType)
            else self.event_type
        )
        return f"[{self.timestamp.isoformat()}] {event_name} from {self.source}: {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary for serialization.

        Returns:
            Dictionary representation of the event.
        """
        event_name = (
            self.event_type.value
            if isinstance(self.event_type, EventType)
            else self.event_type
        )
        return {
            "event_type": event_name,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "data": self.data,
            "message": self.message,
        }


# Type alias for event handlers
EventHandler = Callable[[Event], None]


class EventBus:
    """Central event bus for pub/sub messaging.

    Components can subscribe to events by type and receive notifications
    when events are emitted.

    Thread-safety: This implementation is NOT thread-safe. For multi-threaded
    simulations, use appropriate locking or a thread-safe queue.
    """

    def __init__(self, *, max_history: int = 1000) -> None:
        """Initialize event bus.

        Args:
            max_history: Maximum number of events to keep in history.
        """
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._history: deque[Event] = deque(maxlen=max_history)
        self._max_history = max_history

    def subscribe(
        self,
        event_type: EventType | str,
        handler: EventHandler,
    ) -> None:
        """Subscribe to events of a specific type.

        Args:
            event_type: Type of events to subscribe to.
            handler: Callback function to invoke when event occurs.
        """
        key = event_type.value if isinstance(event_type, EventType) else event_type
        if handler not in self._handlers[key]:
            self._handlers[key].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to all events.

        Args:
            handler: Callback function to invoke for any event.
        """
        self.subscribe("*", handler)

    def unsubscribe(
        self,
        event_type: EventType | str,
        handler: EventHandler,
    ) -> bool:
        """Unsubscribe from events.

        Args:
            event_type: Type of events to unsubscribe from.
            handler: The handler to remove.

        Returns:
            True if handler was found and removed.
        """
        key = event_type.value if isinstance(event_type, EventType) else event_type
        if handler in self._handlers[key]:
            self._handlers[key].remove(handler)
            return True
        return False

    def emit(self, event: Event) -> None:
        """Emit an event to all subscribers.

        Handler exceptions are logged but do not prevent other handlers from
        being called. This ensures one buggy handler doesn't break the entire
        event system.

        Args:
            event: The event to emit.
        """
        # Add to history - deque with maxlen handles automatic FIFO trimming
        self._history.append(event)

        # Get event type key
        event_key = (
            event.event_type.value
            if isinstance(event.event_type, EventType)
            else event.event_type
        )

        # Notify specific handlers
        for handler in self._handlers[event_key]:
            try:
                handler(event)
            except Exception:
                handler_name = getattr(handler, "__name__", str(handler))
                logger.exception(
                    "Event handler '%s' failed processing %s event from %s",
                    handler_name,
                    event_key,
                    event.source,
                )

        # Notify wildcard handlers
        for handler in self._handlers["*"]:
            try:
                handler(event)
            except Exception:
                handler_name = getattr(handler, "__name__", str(handler))
                logger.exception(
                    "Event handler '%s' failed processing %s event from %s",
                    handler_name,
                    event_key,
                    event.source,
                )

    def emit_simple(
        self,
        event_type: EventType | str,
        source: str,
        message: str = "",
        **data: Any,
    ) -> Event:
        """Emit an event with simpler syntax.

        Args:
            event_type: Type of event.
            source: Event source name.
            message: Human-readable message.
            **data: Event data as keyword arguments.

        Returns:
            The emitted event.
        """
        event = Event(
            event_type=event_type,
            source=source,
            message=message,
            data=data,
        )
        self.emit(event)
        return event

    def _iter_history_filtered(
        self,
        event_type: EventType | str | None = None,
        source: str | None = None,
    ) -> Iterator[Event]:
        """Iterate over history with filtering applied.

        Uses generator-based filtering to avoid creating full list copies,
        which is more memory efficient for large histories.

        Args:
            event_type: Filter by event type.
            source: Filter by source.

        Yields:
            Events matching the filters.
        """
        type_key: str | None = None
        if event_type is not None:
            type_key = (
                event_type.value if isinstance(event_type, EventType) else event_type
            )

        for event in self._history:
            # Check event type filter
            if type_key is not None:
                event_key = (
                    event.event_type.value
                    if isinstance(event.event_type, EventType)
                    else event.event_type
                )
                if event_key != type_key:
                    continue

            # Check source filter
            if source is not None and event.source != source:
                continue

            yield event

    def get_history(
        self,
        event_type: EventType | str | None = None,
        source: str | None = None,
        limit: int | None = None,
    ) -> list[Event]:
        """Get event history with optional filtering.

        Uses generator-based filtering internally to avoid creating
        intermediate list copies for memory efficiency.

        Args:
            event_type: Filter by event type.
            source: Filter by source.
            limit: Maximum number of events to return.

        Returns:
            List of events matching filters (most recent last).
        """
        # Use generator-based filtering to avoid full copy before filtering
        filtered = list(self._iter_history_filtered(event_type, source))

        if limit is not None:
            return filtered[-limit:]

        return filtered

    def clear_history(self) -> None:
        """Clear event history."""
        self._history.clear()

    def clear_handlers(self) -> None:
        """Remove all event handlers."""
        self._handlers.clear()

    def clear(self) -> None:
        """Clear both history and handlers."""
        self.clear_history()
        self.clear_handlers()


# Global event bus instance
_global_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """Get the global event bus.

    Creates the bus on first call.

    Returns:
        The global EventBus instance.
    """
    global _global_bus
    if _global_bus is None:
        _global_bus = EventBus()
    return _global_bus


def reset_event_bus() -> None:
    """Reset the global event bus.

    Primarily useful for testing. Setting to None allows the old instance
    to be garbage collected; explicit clear() before None is redundant.
    """
    global _global_bus
    # M3 Fix: Removed redundant clear() call before setting to None.
    # The old EventBus instance will be garbage collected when _global_bus
    # is set to None and no other references exist.
    _global_bus = None


# Convenience functions for common events


def emit_state_update(
    source: str,
    temperature: float | None = None,
    humidity: float | None = None,
    co2: float | None = None,
    **extra: Any,
) -> Event:
    """Emit a state update event.

    Args:
        source: Source of the update.
        temperature: Temperature in C (if changed).
        humidity: Humidity in % (if changed).
        co2: CO2 in ppm (if changed).
        **extra: Additional state data.

    Returns:
        The emitted event.
    """
    data: dict[str, Any] = {}
    if temperature is not None:
        data["temperature"] = temperature
    if humidity is not None:
        data["humidity"] = humidity
    if co2 is not None:
        data["co2"] = co2
    data.update(extra)

    bus = get_event_bus()
    return bus.emit_simple(
        EventType.STATE_UPDATE,
        source=source,
        message=f"State update from {source}",
        **data,
    )


def emit_sensor_reading(
    sensor_name: str,
    readings: dict[str, float],
) -> Event:
    """Emit a sensor reading event.

    Args:
        sensor_name: Name of the sensor.
        readings: Dictionary of reading names to values.

    Returns:
        The emitted event.
    """
    bus = get_event_bus()
    return bus.emit_simple(
        EventType.SENSOR_READING,
        source=sensor_name,
        message=f"Reading from {sensor_name}",
        readings=readings,
    )


def emit_alarm(
    alarm_type: EventType,
    source: str,
    message: str,
    value: float | None = None,
    threshold: float | None = None,
) -> Event:
    """Emit an alarm event.

    Args:
        alarm_type: Type of alarm (should be an ALARM_* type).
        source: Source of the alarm.
        message: Alarm message.
        value: Current value that triggered alarm.
        threshold: Threshold that was exceeded.

    Returns:
        The emitted event.
    """
    bus = get_event_bus()
    data: dict[str, Any] = {}
    if value is not None:
        data["value"] = value
    if threshold is not None:
        data["threshold"] = threshold

    return bus.emit_simple(
        alarm_type,
        source=source,
        message=message,
        **data,
    )
