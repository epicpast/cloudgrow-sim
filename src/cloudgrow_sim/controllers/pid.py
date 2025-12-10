"""PID controller implementation with anti-windup and bumpless transfer."""

from __future__ import annotations

from cloudgrow_sim.core.base import Controller
from cloudgrow_sim.core.registry import register_component


@register_component("controller", "pid")
class PIDController(Controller):
    """PID controller with anti-windup and derivative filtering.

    Implements a full-featured PID controller suitable for greenhouse
    climate control applications.

    Features:
    - Anti-windup using integral clamping
    - Derivative filtering to reduce noise sensitivity
    - Bumpless transfer when setpoint changes
    - Configurable output limits

    The control equation is:
        u(t) = Kp * e(t) + Ki * ∫e(τ)dτ + Kd * de/dt

    Where e(t) = setpoint - process_value (negative feedback).

    Attributes:
        kp: Proportional gain.
        ki: Integral gain.
        kd: Derivative gain.
        output_limits: Tuple of (min, max) output values.
        anti_windup: Whether to use integral anti-windup.
        derivative_filter: Time constant for derivative filtering.
    """

    def __init__(
        self,
        name: str,
        *,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
        setpoint: float = 0.0,
        output_limits: tuple[float, float] = (0.0, 1.0),
        anti_windup: bool = True,
        derivative_filter: float = 0.1,
        reverse_acting: bool = False,
        enabled: bool = True,
    ) -> None:
        """Initialize PID controller.

        Args:
            name: Unique identifier.
            kp: Proportional gain (default 1.0).
            ki: Integral gain (default 0.0 = no integral action).
            kd: Derivative gain (default 0.0 = no derivative action).
            setpoint: Initial setpoint value.
            output_limits: Tuple of (min, max) output values.
            anti_windup: Enable integral anti-windup (default True).
            derivative_filter: Derivative filter time constant in seconds.
            reverse_acting: If True, output increases when PV > SP.
            enabled: Whether controller is active.
        """
        super().__init__(name, setpoint=setpoint, enabled=enabled)
        self._kp = kp
        self._ki = ki
        self._kd = kd
        self._output_limits = output_limits
        self._anti_windup = anti_windup
        self._derivative_filter = derivative_filter
        self._reverse_acting = reverse_acting

        # Internal state
        self._integral: float = 0.0
        self._last_error: float | None = None
        self._last_derivative: float = 0.0
        self._last_pv: float | None = None

    @property
    def kp(self) -> float:
        """Proportional gain."""
        return self._kp

    @kp.setter
    def kp(self, value: float) -> None:
        """Set proportional gain."""
        self._kp = value

    @property
    def ki(self) -> float:
        """Integral gain."""
        return self._ki

    @ki.setter
    def ki(self, value: float) -> None:
        """Set integral gain."""
        self._ki = value

    @property
    def kd(self) -> float:
        """Derivative gain."""
        return self._kd

    @kd.setter
    def kd(self, value: float) -> None:
        """Set derivative gain."""
        self._kd = value

    @property
    def integral(self) -> float:
        """Current integral term value."""
        return self._integral

    @property
    def output_limits(self) -> tuple[float, float]:
        """Output limits as (min, max) tuple."""
        return self._output_limits

    def compute(
        self,
        process_value: float,
        dt: float,
    ) -> float:
        """Compute PID control output.

        Args:
            process_value: Current measured value of controlled variable.
            dt: Time step duration in seconds.

        Returns:
            Control output value (clamped to output_limits).
        """
        if dt <= 0:
            return self._output

        # Calculate error
        error = self._setpoint - process_value
        if self._reverse_acting:
            error = -error

        # Proportional term
        p_term = self._kp * error

        # Integral term with anti-windup
        self._integral += error * dt
        i_term = self._ki * self._integral

        # Derivative term with filtering
        if self._last_pv is not None and dt > 0:
            # Derivative on PV to avoid derivative kick on setpoint change
            d_pv = -(process_value - self._last_pv) / dt

            # Low-pass filter for derivative
            if self._derivative_filter > 0:
                alpha = dt / (self._derivative_filter + dt)
                self._last_derivative = (
                    alpha * d_pv + (1 - alpha) * self._last_derivative
                )
            else:
                self._last_derivative = d_pv
        else:
            self._last_derivative = 0.0

        d_term = self._kd * self._last_derivative

        # Calculate raw output
        output = p_term + i_term + d_term

        # Apply output limits
        min_out, max_out = self._output_limits
        clamped_output = max(min_out, min(max_out, output))

        # Anti-windup: back-calculate integral if output is saturated
        if self._anti_windup and self._ki != 0 and output != clamped_output:
            # Reduce integral to bring output back to limit
            self._integral = (clamped_output - p_term - d_term) / self._ki

        # Store state for next iteration
        self._last_error = error
        self._last_pv = process_value
        self._output = clamped_output

        return clamped_output

    def reset(self) -> None:
        """Reset controller internal state."""
        super().reset()
        self._integral = 0.0
        self._last_error = None
        self._last_derivative = 0.0
        self._last_pv = None

    def set_integral(self, value: float) -> None:
        """Manually set integral term (for bumpless transfer).

        Args:
            value: New integral value.
        """
        self._integral = value

    def auto_tune_ziegler_nichols(
        self,
        ku: float,
        tu: float,
        controller_type: str = "pid",
    ) -> None:
        """Apply Ziegler-Nichols tuning from ultimate gain and period.

        Args:
            ku: Ultimate gain (gain at sustained oscillation).
            tu: Ultimate period in seconds.
            controller_type: 'p', 'pi', or 'pid'.
        """
        if controller_type == "p":
            self._kp = 0.5 * ku
            self._ki = 0.0
            self._kd = 0.0
        elif controller_type == "pi":
            self._kp = 0.45 * ku
            self._ki = 0.54 * ku / tu
            self._kd = 0.0
        else:  # pid
            self._kp = 0.6 * ku
            self._ki = 1.2 * ku / tu
            self._kd = 0.075 * ku * tu
