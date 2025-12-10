"""Hysteresis (deadband) controller implementation."""

from __future__ import annotations

from cloudgrow_sim.core.base import Controller
from cloudgrow_sim.core.registry import register_component


@register_component("controller", "hysteresis")
class HysteresisController(Controller):
    """On/off controller with hysteresis (deadband).

    A simple bang-bang controller that turns output on when process
    value exceeds setpoint + hysteresis/2, and off when it drops below
    setpoint - hysteresis/2.

    Common for simple heating/cooling applications where precision
    isn't critical but cycling should be minimized.

    Example: Heating with setpoint=20°C, hysteresis=2°C
    - Heater ON when temperature < 19°C
    - Heater OFF when temperature > 21°C

    Attributes:
        hysteresis: Total deadband width in process value units.
        output_on: Output value when controller is "on".
        output_off: Output value when controller is "off".
    """

    def __init__(
        self,
        name: str,
        *,
        setpoint: float = 20.0,
        hysteresis: float = 2.0,
        output_on: float = 1.0,
        output_off: float = 0.0,
        reverse_acting: bool = False,
        enabled: bool = True,
    ) -> None:
        """Initialize hysteresis controller.

        Args:
            name: Unique identifier.
            setpoint: Target setpoint value.
            hysteresis: Total deadband width.
            output_on: Output value when active.
            output_off: Output value when inactive.
            reverse_acting: If True, turns on when PV > SP (cooling mode).
            enabled: Whether controller is active.
        """
        super().__init__(name, setpoint=setpoint, enabled=enabled)
        self._hysteresis = hysteresis
        self._output_on = output_on
        self._output_off = output_off
        self._reverse_acting = reverse_acting
        self._is_on: bool = False

    @property
    def hysteresis(self) -> float:
        """Total deadband width."""
        return self._hysteresis

    @hysteresis.setter
    def hysteresis(self, value: float) -> None:
        """Set hysteresis value."""
        if value < 0:
            msg = f"Hysteresis must be non-negative, got {value}"
            raise ValueError(msg)
        self._hysteresis = value

    @property
    def output_on(self) -> float:
        """Output value when active."""
        return self._output_on

    @property
    def output_off(self) -> float:
        """Output value when inactive."""
        return self._output_off

    @property
    def is_on(self) -> bool:
        """Whether controller is currently in "on" state."""
        return self._is_on

    @property
    def upper_threshold(self) -> float:
        """Upper threshold (setpoint + hysteresis/2)."""
        return self._setpoint + self._hysteresis / 2

    @property
    def lower_threshold(self) -> float:
        """Lower threshold (setpoint - hysteresis/2)."""
        return self._setpoint - self._hysteresis / 2

    def compute(
        self,
        process_value: float,
        dt: float,
    ) -> float:
        """Compute hysteresis control output.

        Args:
            process_value: Current measured value.
            dt: Time step duration (unused).

        Returns:
            Output value (output_on or output_off).
        """
        del dt  # Unused

        if self._reverse_acting:
            # Cooling mode: turn on when too hot
            if process_value > self.upper_threshold:
                self._is_on = True
            elif process_value < self.lower_threshold:
                self._is_on = False
        else:
            # Heating mode: turn on when too cold
            if process_value < self.lower_threshold:
                self._is_on = True
            elif process_value > self.upper_threshold:
                self._is_on = False

        self._output = self._output_on if self._is_on else self._output_off
        return self._output

    def reset(self) -> None:
        """Reset controller to initial state."""
        super().reset()
        self._is_on = False
