"""Schedule-based controller implementation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time

from cloudgrow_sim.core.base import Controller
from cloudgrow_sim.core.registry import register_component
from cloudgrow_sim.core.state import GreenhouseState


@dataclass
class ScheduleEntry:
    """A single entry in a schedule.

    Attributes:
        time: Time of day for this entry.
        value: Setpoint or output value at this time.
    """

    time: time
    value: float


@register_component("controller", "schedule")
class ScheduleController(Controller):
    """Time-based schedule controller.

    Provides setpoints or outputs based on time-of-day schedules.
    Can operate in two modes:
    - Setpoint mode: Provides setpoint values for another controller
    - Direct mode: Directly controls output based on schedule

    Supports linear interpolation between schedule points.

    Example schedule for temperature setpoints:
    - 06:00: 18°C (morning warm-up)
    - 08:00: 24°C (daytime)
    - 18:00: 22°C (evening)
    - 22:00: 16°C (night)

    Attributes:
        schedule: List of ScheduleEntry objects.
        interpolate: Whether to interpolate between schedule points.
        mode: 'setpoint' or 'direct'.
    """

    def __init__(
        self,
        name: str,
        *,
        schedule: list[tuple[str, float]] | None = None,
        interpolate: bool = True,
        mode: str = "setpoint",
        default_value: float = 20.0,
        enabled: bool = True,
    ) -> None:
        """Initialize schedule controller.

        Args:
            name: Unique identifier.
            schedule: List of (time_str, value) tuples. Time format: "HH:MM".
            interpolate: If True, interpolate between schedule points.
            mode: 'setpoint' (provides setpoint) or 'direct' (controls output).
            default_value: Value to use if no schedule is defined.
            enabled: Whether controller is active.
        """
        super().__init__(name, setpoint=default_value, enabled=enabled)
        self._interpolate = interpolate
        self._mode = mode
        self._default_value = default_value

        # Parse schedule
        self._schedule: list[ScheduleEntry] = []
        if schedule:
            for time_str, value in schedule:
                self.add_entry(time_str, value)

    @property
    def schedule(self) -> list[ScheduleEntry]:
        """Schedule entries."""
        return self._schedule

    @property
    def interpolate(self) -> bool:
        """Whether to interpolate between schedule points."""
        return self._interpolate

    @interpolate.setter
    def interpolate(self, value: bool) -> None:
        """Set interpolation mode."""
        self._interpolate = value

    @property
    def mode(self) -> str:
        """Controller mode ('setpoint' or 'direct')."""
        return self._mode

    def add_entry(self, time_str: str, value: float) -> None:
        """Add an entry to the schedule.

        Args:
            time_str: Time in "HH:MM" format.
            value: Value at this time.
        """
        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0

        entry = ScheduleEntry(time=time(hour, minute), value=value)
        self._schedule.append(entry)
        # Sort by time
        self._schedule.sort(key=lambda e: (e.time.hour, e.time.minute))

    def clear_schedule(self) -> None:
        """Remove all schedule entries."""
        self._schedule.clear()

    def get_scheduled_value(self, current_time: time) -> float:
        """Get the scheduled value for a given time.

        Args:
            current_time: Time to look up.

        Returns:
            Scheduled value (interpolated if enabled).
        """
        if not self._schedule:
            return self._default_value

        # Convert current time to minutes since midnight
        current_minutes = current_time.hour * 60 + current_time.minute

        # Find surrounding schedule entries
        prev_entry: ScheduleEntry | None = None
        next_entry: ScheduleEntry | None = None

        for entry in self._schedule:
            entry_minutes = entry.time.hour * 60 + entry.time.minute
            if entry_minutes <= current_minutes:
                prev_entry = entry
            if entry_minutes > current_minutes and next_entry is None:
                next_entry = entry

        # Handle wrap-around at midnight
        if prev_entry is None:
            prev_entry = self._schedule[-1]  # Last entry from yesterday
        if next_entry is None:
            next_entry = self._schedule[0]  # First entry for tomorrow

        if not self._interpolate:
            # Return value from previous entry
            return prev_entry.value

        # Interpolate between entries
        prev_minutes = prev_entry.time.hour * 60 + prev_entry.time.minute
        next_minutes = next_entry.time.hour * 60 + next_entry.time.minute

        # Handle midnight wrap-around
        if next_minutes < prev_minutes:
            next_minutes += 24 * 60
        if current_minutes < prev_minutes:
            current_minutes += 24 * 60

        # Linear interpolation
        if next_minutes == prev_minutes:
            return prev_entry.value

        fraction = (current_minutes - prev_minutes) / (next_minutes - prev_minutes)
        return prev_entry.value + fraction * (next_entry.value - prev_entry.value)

    def compute(
        self,
        process_value: float,
        dt: float,
    ) -> float:
        """Compute output based on schedule.

        In setpoint mode, this updates the setpoint property.
        In direct mode, this returns the scheduled output directly.

        Args:
            process_value: Current measured value (unused in direct mode).
            dt: Time step duration (unused).

        Returns:
            Scheduled value.
        """
        del process_value, dt  # Unused in schedule controller

        # Get current time from process value context
        # In actual use, this would come from the simulation state
        # For now, use the scheduled value based on internal tracking
        current = datetime.now().time()
        scheduled_value = self.get_scheduled_value(current)

        if self._mode == "setpoint":
            self._setpoint = scheduled_value
            # In setpoint mode, return unchanged (actual control elsewhere)
            self._output = scheduled_value
        else:
            # Direct mode - output the scheduled value
            self._output = scheduled_value

        return self._output

    def update(self, dt: float, state: GreenhouseState) -> None:
        """Update controller using simulation time.

        Args:
            dt: Time step in seconds.
            state: Current greenhouse state (provides time).
        """
        del dt  # Unused - schedule doesn't need time step
        if not self.enabled:
            return

        # Use simulation time instead of system time
        current = state.time.time()
        scheduled_value = self.get_scheduled_value(current)

        if self._mode == "setpoint":
            self._setpoint = scheduled_value
        else:
            self._output = scheduled_value

        # Apply to connected actuators
        for actuator in self._connected_actuators:
            actuator.set_output(self._output)

    def reset(self) -> None:
        """Reset controller to initial state."""
        super().reset()
        self._output = self._default_value
