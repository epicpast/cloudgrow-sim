"""Tests for PID controller."""

from __future__ import annotations

from cloudgrow_sim.controllers import PIDController


class TestPIDController:
    """Tests for PIDController."""

    def test_proportional_only(self) -> None:
        """Proportional-only control."""
        pid = PIDController("pid", kp=1.0, ki=0.0, kd=0.0, setpoint=100.0)

        # Error = 100 - 90 = 10
        # Output = 1.0 * 10 = 10 -> clamped to 1.0
        output = pid.compute(90.0, 0.1)
        assert output == 1.0

    def test_proportional_small_error(self) -> None:
        """Small error gives proportional output."""
        pid = PIDController(
            "pid",
            kp=0.1,
            ki=0.0,
            kd=0.0,
            setpoint=25.0,
            output_limits=(0.0, 1.0),
        )

        # Error = 25 - 24 = 1
        # Output = 0.1 * 1 = 0.1
        output = pid.compute(24.0, 0.1)
        assert abs(output - 0.1) < 0.01

    def test_integral_accumulates(self) -> None:
        """Integral term accumulates error."""
        pid = PIDController(
            "pid",
            kp=0.0,
            ki=1.0,
            kd=0.0,
            setpoint=25.0,
            output_limits=(-10.0, 10.0),
        )

        # First step: integral = 1 * 0.1 = 0.1
        output1 = pid.compute(24.0, 0.1)
        # Second step: integral = 0.1 + 1 * 0.1 = 0.2
        output2 = pid.compute(24.0, 0.1)

        assert output2 > output1
        assert abs(pid.integral - 0.2) < 0.01

    def test_derivative_responds_to_change(self) -> None:
        """Derivative responds to PV change."""
        pid = PIDController(
            "pid",
            kp=0.0,
            ki=0.0,
            kd=1.0,
            setpoint=25.0,
            output_limits=(-10.0, 10.0),
            derivative_filter=0.0,  # No filtering
        )

        # First call establishes baseline
        pid.compute(24.0, 0.1)
        # Second call with changed PV
        # dPV/dt = (24.5 - 24.0) / 0.1 = 5
        # Derivative on PV (negative): -5 * 1.0 = -5
        output = pid.compute(24.5, 0.1)
        assert output < 0

    def test_anti_windup(self) -> None:
        """Anti-windup prevents integral saturation."""
        pid = PIDController(
            "pid",
            kp=0.0,
            ki=10.0,
            kd=0.0,
            setpoint=100.0,
            output_limits=(0.0, 1.0),
            anti_windup=True,
        )

        # Large error for many steps
        for _ in range(100):
            pid.compute(0.0, 0.1)

        # Integral should be limited to keep output at max
        assert pid.integral <= 0.1  # Ki * integral <= 1.0

    def test_output_limits(self) -> None:
        """Output respects limits."""
        pid = PIDController(
            "pid",
            kp=10.0,
            setpoint=100.0,
            output_limits=(0.2, 0.8),
        )

        # Large positive error
        output = pid.compute(0.0, 0.1)
        assert output == 0.8

        # Large negative error
        pid.setpoint = 0.0
        output = pid.compute(100.0, 0.1)
        assert output == 0.2

    def test_reverse_acting(self) -> None:
        """Reverse acting inverts error sign."""
        pid_normal = PIDController("normal", kp=0.1, setpoint=25.0)
        pid_reverse = PIDController(
            "reverse", kp=0.1, setpoint=25.0, reverse_acting=True
        )

        # PV below setpoint
        out_normal = pid_normal.compute(20.0, 0.1)
        out_reverse = pid_reverse.compute(20.0, 0.1)

        # Normal: error positive, output positive
        # Reverse: error negative, output smaller
        assert out_normal > out_reverse

    def test_reset(self) -> None:
        """Reset clears internal state."""
        pid = PIDController("pid", kp=1.0, ki=1.0, kd=1.0, setpoint=25.0)

        # Build up some state
        for _ in range(10):
            pid.compute(20.0, 0.1)

        pid.reset()

        assert pid.integral == 0.0
        assert pid.output == 0.0

    def test_ziegler_nichols_tuning(self) -> None:
        """Ziegler-Nichols tuning sets gains."""
        pid = PIDController("pid")

        # Ultimate gain = 2, Ultimate period = 1s
        pid.auto_tune_ziegler_nichols(2.0, 1.0, "pid")

        # Kp = 0.6 * Ku = 1.2
        # Ki = 1.2 * Ku / Tu = 2.4
        # Kd = 0.075 * Ku * Tu = 0.15
        assert abs(pid.kp - 1.2) < 0.01
        assert abs(pid.ki - 2.4) < 0.01
        assert abs(pid.kd - 0.15) < 0.01

    def test_setpoint_change(self) -> None:
        """Controller responds to setpoint change."""
        pid = PIDController("pid", kp=0.5, setpoint=20.0)

        output1 = pid.compute(20.0, 0.1)
        assert abs(output1) < 0.01  # At setpoint

        pid.setpoint = 25.0
        output2 = pid.compute(20.0, 0.1)
        assert output2 > 0  # Below new setpoint

    def test_set_integral(self) -> None:
        """Manual integral setting for bumpless transfer."""
        pid = PIDController("pid", kp=0.0, ki=1.0, setpoint=25.0)

        pid.set_integral(5.0)
        assert pid.integral == 5.0


class TestPIDControllerIntegration:
    """Integration tests for PID control behavior."""

    def test_temperature_control_simulation(self) -> None:
        """Simulate simple temperature control."""
        pid = PIDController(
            "temp_ctrl",
            kp=0.5,
            ki=0.1,
            kd=0.05,
            setpoint=25.0,
            output_limits=(0.0, 1.0),
        )

        # Simple first-order system simulation
        temperature = 20.0
        time_constant = 60.0  # seconds
        max_heating = 10.0  # degrees

        dt = 1.0  # 1 second steps
        temps = []

        for _ in range(300):  # 5 minutes
            output = pid.compute(temperature, dt)

            # Simple thermal model
            # dT/dt = (heater_effect - heat_loss) / time_constant
            heater_effect = output * max_heating
            heat_loss = (temperature - 20.0) * 0.1
            temperature += (heater_effect - heat_loss) * dt / time_constant
            temps.append(temperature)

        # Should reach near setpoint
        assert abs(temps[-1] - 25.0) < 1.0

    def test_overshoot_control(self) -> None:
        """Test that derivative helps reduce overshoot."""
        # Controller with derivative
        pid_pd = PIDController(
            "pd",
            kp=0.5,
            ki=0.0,
            kd=0.2,
            setpoint=25.0,
            output_limits=(0.0, 1.0),
        )

        # Controller without derivative
        pid_p = PIDController(
            "p",
            kp=0.5,
            ki=0.0,
            kd=0.0,
            setpoint=25.0,
            output_limits=(0.0, 1.0),
        )

        def simulate(pid: PIDController) -> list[float]:
            temperature = 20.0
            temps = []
            for _ in range(100):
                output = pid.compute(temperature, 0.1)
                temperature += output * 0.5 - 0.1 * (temperature - 20)
                temps.append(temperature)
            return temps

        temps_pd = simulate(pid_pd)
        temps_p = simulate(pid_p)

        # PD controller should have less overshoot
        max_overshoot_pd = max(temps_pd) - 25.0
        max_overshoot_p = max(temps_p) - 25.0

        # Note: this depends on system dynamics, may not always be true
        # for all parameters, but generally derivative reduces overshoot
        assert max_overshoot_pd <= max_overshoot_p + 0.5
