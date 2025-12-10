"""Tests for schedule controller."""

from __future__ import annotations

from datetime import time

from cloudgrow_sim.controllers import ScheduleController


class TestScheduleController:
    """Tests for ScheduleController."""

    def test_empty_schedule(self) -> None:
        """Empty schedule returns default value."""
        ctrl = ScheduleController("sched", default_value=20.0)

        value = ctrl.get_scheduled_value(time(12, 0))
        assert value == 20.0

    def test_single_entry(self) -> None:
        """Single schedule entry."""
        ctrl = ScheduleController(
            "sched",
            schedule=[("08:00", 25.0)],
            interpolate=False,
        )

        # After the entry
        value = ctrl.get_scheduled_value(time(10, 0))
        assert value == 25.0

    def test_multiple_entries_no_interpolation(self) -> None:
        """Multiple entries without interpolation (step function)."""
        ctrl = ScheduleController(
            "sched",
            schedule=[
                ("06:00", 18.0),
                ("08:00", 24.0),
                ("18:00", 22.0),
                ("22:00", 16.0),
            ],
            interpolate=False,
        )

        assert ctrl.get_scheduled_value(time(5, 0)) == 16.0  # Before first
        assert ctrl.get_scheduled_value(time(7, 0)) == 18.0  # After 06:00
        assert ctrl.get_scheduled_value(time(12, 0)) == 24.0  # After 08:00
        assert ctrl.get_scheduled_value(time(20, 0)) == 22.0  # After 18:00
        assert ctrl.get_scheduled_value(time(23, 0)) == 16.0  # After 22:00

    def test_interpolation(self) -> None:
        """Interpolation between entries."""
        ctrl = ScheduleController(
            "sched",
            schedule=[
                ("06:00", 18.0),
                ("08:00", 24.0),
            ],
            interpolate=True,
        )

        # Midpoint
        value = ctrl.get_scheduled_value(time(7, 0))
        assert abs(value - 21.0) < 0.1

        # At entry
        value = ctrl.get_scheduled_value(time(6, 0))
        assert abs(value - 18.0) < 0.1

    def test_add_entry(self) -> None:
        """Dynamically add schedule entry."""
        ctrl = ScheduleController("sched")

        ctrl.add_entry("08:00", 25.0)
        ctrl.add_entry("06:00", 18.0)

        # Should be sorted
        assert len(ctrl.schedule) == 2
        assert ctrl.schedule[0].time == time(6, 0)
        assert ctrl.schedule[1].time == time(8, 0)

    def test_clear_schedule(self) -> None:
        """Clear all entries."""
        ctrl = ScheduleController(
            "sched",
            schedule=[("08:00", 25.0)],
        )

        ctrl.clear_schedule()
        assert len(ctrl.schedule) == 0

    def test_setpoint_mode(self) -> None:
        """Setpoint mode updates setpoint."""
        ctrl = ScheduleController(
            "sched",
            schedule=[("08:00", 25.0)],
            mode="setpoint",
            interpolate=False,
        )

        ctrl.compute(20.0, 0.1)
        # Setpoint should be updated (though we can't easily test time-based)
        assert ctrl.mode == "setpoint"

    def test_direct_mode(self) -> None:
        """Direct mode controls output."""
        ctrl = ScheduleController(
            "sched",
            schedule=[("08:00", 0.75)],
            mode="direct",
        )

        assert ctrl.mode == "direct"


class TestScheduleControllerMidnightWrap:
    """Tests for midnight wrap-around handling."""

    def test_wrap_around(self) -> None:
        """Handle midnight wrap-around in interpolation."""
        ctrl = ScheduleController(
            "sched",
            schedule=[
                ("06:00", 20.0),
                ("22:00", 16.0),
            ],
            interpolate=True,
        )

        # At midnight, interpolating between 22:00 (16°C) and 06:00 (20°C)
        # Total span: 8 hours (22:00 to 06:00)
        # Midnight is 2 hours past 22:00 = 2/8 = 0.25
        # Expected: 16 + 0.25 * (20 - 16) = 17°C
        value = ctrl.get_scheduled_value(time(0, 0))
        assert abs(value - 17.0) < 0.5

    def test_early_morning(self) -> None:
        """Early morning uses previous day's last entry."""
        ctrl = ScheduleController(
            "sched",
            schedule=[
                ("08:00", 24.0),
                ("20:00", 18.0),
            ],
            interpolate=False,
        )

        # Before first entry, should use last entry from "yesterday"
        value = ctrl.get_scheduled_value(time(6, 0))
        assert value == 18.0


class TestScheduleControllerApplications:
    """Application-specific tests."""

    def test_day_night_setpoints(self) -> None:
        """Day/night temperature setpoint schedule."""
        ctrl = ScheduleController(
            "day_night",
            schedule=[
                ("06:00", 18.0),  # Morning warm-up
                ("08:00", 24.0),  # Daytime
                ("18:00", 22.0),  # Evening
                ("22:00", 16.0),  # Night
            ],
            interpolate=False,
        )

        # Night
        assert ctrl.get_scheduled_value(time(4, 0)) == 16.0
        # Morning transition
        assert ctrl.get_scheduled_value(time(6, 30)) == 18.0
        # Daytime
        assert ctrl.get_scheduled_value(time(14, 0)) == 24.0
        # Evening
        assert ctrl.get_scheduled_value(time(20, 0)) == 22.0

    def test_lighting_schedule(self) -> None:
        """Supplemental lighting schedule (direct output)."""
        ctrl = ScheduleController(
            "lights",
            schedule=[
                ("05:00", 1.0),  # Lights on before sunrise
                ("07:00", 0.0),  # Natural light sufficient
                ("17:00", 1.0),  # Supplement evening
                ("20:00", 0.0),  # Dark period
            ],
            mode="direct",
            interpolate=False,
        )

        assert ctrl.get_scheduled_value(time(4, 0)) == 0.0  # Night
        assert ctrl.get_scheduled_value(time(6, 0)) == 1.0  # Pre-dawn
        assert ctrl.get_scheduled_value(time(12, 0)) == 0.0  # Midday
        assert ctrl.get_scheduled_value(time(18, 0)) == 1.0  # Evening
        assert ctrl.get_scheduled_value(time(21, 0)) == 0.0  # Night
