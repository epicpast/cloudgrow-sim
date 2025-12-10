"""Tests for hysteresis controller."""

from __future__ import annotations

import pytest

from cloudgrow_sim.controllers import HysteresisController


class TestHysteresisController:
    """Tests for HysteresisController."""

    def test_heating_mode(self) -> None:
        """Default heating mode behavior."""
        ctrl = HysteresisController(
            "heat",
            setpoint=20.0,
            hysteresis=2.0,
            output_on=1.0,
            output_off=0.0,
        )

        # Cold - turn on
        assert ctrl.compute(18.0, 0.1) == 1.0
        assert ctrl.is_on is True

        # Warming - stays on
        assert ctrl.compute(19.5, 0.1) == 1.0

        # Above upper threshold - turn off
        assert ctrl.compute(21.5, 0.1) == 0.0
        assert ctrl.is_on is False

        # Cooling - stays off
        assert ctrl.compute(20.0, 0.1) == 0.0

        # Below lower threshold - turn on
        assert ctrl.compute(18.5, 0.1) == 1.0

    def test_cooling_mode(self) -> None:
        """Reverse acting (cooling) mode."""
        ctrl = HysteresisController(
            "cool",
            setpoint=25.0,
            hysteresis=2.0,
            output_on=1.0,
            output_off=0.0,
            reverse_acting=True,
        )

        # Hot - turn on
        assert ctrl.compute(27.0, 0.1) == 1.0
        assert ctrl.is_on is True

        # Cooling - stays on
        assert ctrl.compute(25.0, 0.1) == 1.0

        # Below lower threshold - turn off
        assert ctrl.compute(23.5, 0.1) == 0.0
        assert ctrl.is_on is False

        # Warming - stays off
        assert ctrl.compute(25.0, 0.1) == 0.0

        # Above upper threshold - turn on
        assert ctrl.compute(26.5, 0.1) == 1.0

    def test_thresholds(self) -> None:
        """Threshold calculation."""
        ctrl = HysteresisController(
            "test",
            setpoint=20.0,
            hysteresis=4.0,
        )

        assert ctrl.upper_threshold == 22.0
        assert ctrl.lower_threshold == 18.0

    def test_custom_outputs(self) -> None:
        """Custom on/off output values."""
        ctrl = HysteresisController(
            "test",
            setpoint=25.0,
            hysteresis=2.0,
            output_on=0.75,
            output_off=0.25,
        )

        # On state
        ctrl.compute(20.0, 0.1)
        assert ctrl.output == 0.75

        # Off state
        ctrl.compute(30.0, 0.1)
        assert ctrl.output == 0.25

    def test_hysteresis_setter(self) -> None:
        """Set hysteresis dynamically."""
        ctrl = HysteresisController("test", hysteresis=2.0)

        ctrl.hysteresis = 4.0
        assert ctrl.hysteresis == 4.0

    def test_invalid_hysteresis(self) -> None:
        """Error on negative hysteresis."""
        ctrl = HysteresisController("test")

        with pytest.raises(ValueError, match="non-negative"):
            ctrl.hysteresis = -1.0

    def test_reset(self) -> None:
        """Reset clears on state."""
        ctrl = HysteresisController("test", setpoint=20.0)

        ctrl.compute(15.0, 0.1)  # Turn on
        assert ctrl.is_on is True

        ctrl.reset()
        assert ctrl.is_on is False


class TestHysteresisControllerApplications:
    """Application-specific tests."""

    def test_heater_control(self) -> None:
        """Simulate heater thermostat."""
        ctrl = HysteresisController(
            "heater",
            setpoint=18.0,  # Night setpoint
            hysteresis=2.0,
        )

        # Cold night - heater on
        assert ctrl.compute(16.0, 0.1) == 1.0

        # Room warms
        assert ctrl.compute(17.5, 0.1) == 1.0  # Still on
        assert ctrl.compute(19.5, 0.1) == 0.0  # Turns off

        # Room cools
        assert ctrl.compute(18.0, 0.1) == 0.0  # Still off (hysteresis)
        assert ctrl.compute(16.5, 0.1) == 1.0  # Turns on

    def test_vent_control(self) -> None:
        """Simulate vent thermostat (cooling)."""
        ctrl = HysteresisController(
            "vent",
            setpoint=26.0,
            hysteresis=2.0,
            reverse_acting=True,
        )

        # Cool morning
        assert ctrl.compute(22.0, 0.1) == 0.0

        # Warming
        assert ctrl.compute(25.5, 0.1) == 0.0  # Below upper threshold
        assert ctrl.compute(27.5, 0.1) == 1.0  # Above upper - open vent

        # Hot midday
        assert ctrl.compute(30.0, 0.1) == 1.0

        # Evening cooling
        assert ctrl.compute(25.0, 0.1) == 1.0  # Still open
        assert ctrl.compute(24.5, 0.1) == 0.0  # Below lower - close vent
