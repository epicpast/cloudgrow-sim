"""Tests for ventilation calculations."""

from __future__ import annotations

import pytest

from cloudgrow_sim.physics.ventilation import (
    combined_natural_ventilation,
    fan_flow_rate,
    fan_power,
    infiltration_ach_greenhouse,
    infiltration_rate,
    latent_heat_ventilation,
    moisture_removal_rate,
    required_ach_humidity_control,
    required_ventilation_cooling,
    sensible_heat_ventilation,
    stack_effect_flow,
    stack_effect_pressure,
    total_heat_ventilation,
    vent_opening_area,
    wind_driven_flow,
)


class TestInfiltration:
    """Tests for infiltration calculations."""

    def test_infiltration_rate(self) -> None:
        """Basic infiltration rate calculation."""
        # 1000 m³, 0.5 ACH
        q = infiltration_rate(1000.0, 0.5)
        # Q = V * ACH / 3600 = 1000 * 0.5 / 3600 = 0.139 m³/s
        assert abs(q - 0.139) < 0.01

    def test_zero_ach(self) -> None:
        """Zero ACH gives zero flow."""
        q = infiltration_rate(1000.0, 0.0)
        assert q == 0.0

    def test_greenhouse_tight(self) -> None:
        """Tight greenhouse has low ACH."""
        ach = infiltration_ach_greenhouse(5.0, 10.0, construction_quality="tight")
        assert ach < 0.5

    def test_greenhouse_loose(self) -> None:
        """Loose greenhouse has higher ACH than tight."""
        ach_loose = infiltration_ach_greenhouse(5.0, 10.0, construction_quality="loose")
        ach_tight = infiltration_ach_greenhouse(5.0, 10.0, construction_quality="tight")
        # Loose should be significantly higher than tight
        assert ach_loose > ach_tight * 1.5

    def test_greenhouse_increases_with_wind(self) -> None:
        """ACH increases with wind speed."""
        ach_calm = infiltration_ach_greenhouse(0.0, 10.0)
        ach_windy = infiltration_ach_greenhouse(10.0, 10.0)
        assert ach_windy > ach_calm

    def test_greenhouse_invalid_quality(self) -> None:
        """Error on invalid construction quality."""
        with pytest.raises(ValueError, match="Unknown construction"):
            infiltration_ach_greenhouse(5.0, 10.0, construction_quality="invalid")


class TestStackEffect:
    """Tests for stack effect calculations."""

    def test_stack_pressure_positive(self) -> None:
        """Positive pressure when inside warmer."""
        dp = stack_effect_pressure(4.0, 25.0, 10.0)
        assert dp > 0

    def test_stack_pressure_negative(self) -> None:
        """Negative pressure when inside cooler."""
        dp = stack_effect_pressure(4.0, 10.0, 25.0)
        assert dp < 0

    def test_stack_pressure_zero(self) -> None:
        """Zero pressure when temps equal."""
        dp = stack_effect_pressure(4.0, 20.0, 20.0)
        assert abs(dp) < 0.1

    def test_stack_flow(self) -> None:
        """Stack effect flow is positive."""
        q = stack_effect_flow(1.0, 4.0, 30.0, 20.0)
        assert q > 0

    def test_stack_flow_zero_delta(self) -> None:
        """No flow when temps are equal."""
        q = stack_effect_flow(1.0, 4.0, 20.0, 20.0)
        assert q == 0.0

    def test_stack_flow_increases_with_height(self) -> None:
        """More flow with greater height difference."""
        q_low = stack_effect_flow(1.0, 2.0, 30.0, 20.0)
        q_high = stack_effect_flow(1.0, 6.0, 30.0, 20.0)
        assert q_high > q_low


class TestWindDrivenFlow:
    """Tests for wind-driven flow."""

    def test_basic(self) -> None:
        """Basic wind-driven flow."""
        q = wind_driven_flow(1.0, 5.0)
        assert q > 0

    def test_zero_wind(self) -> None:
        """No flow with zero wind."""
        q = wind_driven_flow(1.0, 0.0)
        assert q == 0.0

    def test_increases_with_wind(self) -> None:
        """Flow increases with wind speed."""
        q_low = wind_driven_flow(1.0, 2.0)
        q_high = wind_driven_flow(1.0, 8.0)
        assert q_high > q_low

    def test_increases_with_area(self) -> None:
        """Flow increases with opening area."""
        q_small = wind_driven_flow(0.5, 5.0)
        q_large = wind_driven_flow(2.0, 5.0)
        assert q_large > q_small


class TestCombinedVentilation:
    """Tests for combined natural ventilation."""

    def test_combines_stack_and_wind(self) -> None:
        """Combined flow uses quadrature."""
        q_combined = combined_natural_ventilation(
            opening_area=1.0,
            height=4.0,
            t_inside=30.0,
            t_outside=20.0,
            wind_speed=5.0,
        )
        q_stack = stack_effect_flow(1.0, 4.0, 30.0, 20.0)
        q_wind = wind_driven_flow(1.0, 5.0)

        # Combined should be sqrt(stack² + wind²)
        expected = (q_stack**2 + q_wind**2) ** 0.5
        assert abs(q_combined - expected) < 0.01


class TestVentOpeningArea:
    """Tests for vent opening area."""

    def test_full_open(self) -> None:
        """Full opening."""
        a = vent_opening_area(2.0, 1.0, 1.0)
        assert a == 2.0

    def test_half_open(self) -> None:
        """Half opening."""
        a = vent_opening_area(2.0, 1.0, 0.5)
        assert a == 1.0

    def test_closed(self) -> None:
        """Closed vent."""
        a = vent_opening_area(2.0, 1.0, 0.0)
        assert a == 0.0


class TestFanCalculations:
    """Tests for fan calculations."""

    def test_fan_flow_rate(self) -> None:
        """Basic fan flow rate."""
        q = fan_flow_rate(5.0, 2, 1.0)
        assert q == 10.0

    def test_fan_flow_reduced_speed(self) -> None:
        """Reduced speed gives reduced flow."""
        q = fan_flow_rate(5.0, 2, 0.5)
        assert q == 5.0

    def test_fan_power(self) -> None:
        """Fan power calculation."""
        p = fan_power(10.0, 100.0, 0.6)
        # P = Q * dP / η = 10 * 100 / 0.6 = 1666.67 W
        assert abs(p - 1666.67) < 1.0

    def test_fan_power_invalid_efficiency(self) -> None:
        """Error with zero efficiency."""
        with pytest.raises(ValueError, match="Efficiency"):
            fan_power(10.0, 100.0, 0.0)


class TestSensibleHeatVentilation:
    """Tests for sensible heat ventilation."""

    def test_cooling(self) -> None:
        """Cooling when outside air cooler."""
        q = sensible_heat_ventilation(1.0, 20.0, 30.0)
        # Negative = removing heat (cooling)
        assert q < 0

    def test_heating(self) -> None:
        """Heating when outside air warmer."""
        q = sensible_heat_ventilation(1.0, 30.0, 20.0)
        # Positive = adding heat
        assert q > 0

    def test_zero(self) -> None:
        """No heat exchange when temps equal."""
        q = sensible_heat_ventilation(1.0, 25.0, 25.0)
        assert abs(q) < 1.0


class TestLatentHeatVentilation:
    """Tests for latent heat ventilation."""

    def test_dehumidification(self) -> None:
        """Dehumidification when outside air drier."""
        q = latent_heat_ventilation(1.0, 25.0, 25.0, 30.0, 70.0)
        # Outside 30%, inside 70% - dehumidifying
        assert q < 0

    def test_humidification(self) -> None:
        """Humidification when outside air moister."""
        q = latent_heat_ventilation(1.0, 25.0, 25.0, 80.0, 40.0)
        # Outside 80%, inside 40% - humidifying
        assert q > 0


class TestTotalHeatVentilation:
    """Tests for total heat ventilation."""

    def test_sum(self) -> None:
        """Total is sum of sensible and latent."""
        q_total = total_heat_ventilation(1.0, 20.0, 25.0, 50.0, 60.0)
        q_s = sensible_heat_ventilation(1.0, 20.0, 25.0)
        q_l = latent_heat_ventilation(1.0, 20.0, 25.0, 50.0, 60.0)
        assert abs(q_total - (q_s + q_l)) < 10.0  # Allow some numerical error


class TestMoistureRemoval:
    """Tests for moisture removal calculations."""

    def test_removal(self) -> None:
        """Moisture removal when inside wetter."""
        m = moisture_removal_rate(1.0, 0.005, 0.015)
        assert m > 0

    def test_addition(self) -> None:
        """Moisture addition when outside wetter."""
        m = moisture_removal_rate(1.0, 0.015, 0.005)
        assert m < 0


class TestVentilationRequirements:
    """Tests for ventilation requirements."""

    def test_required_cooling(self) -> None:
        """Required ventilation for cooling."""
        q = required_ventilation_cooling(10000.0, 25.0, 20.0)
        assert q > 0

    def test_invalid_cooling_temps(self) -> None:
        """Error when outside hotter than inside."""
        with pytest.raises(ValueError, match="must be lower"):
            required_ventilation_cooling(10000.0, 25.0, 30.0)

    def test_required_humidity(self) -> None:
        """Required ACH for humidity control."""
        ach = required_ach_humidity_control(
            moisture_generation=0.001,  # kg/s
            volume=1000.0,  # m³
            w_inside=0.015,
            w_outside=0.010,
        )
        assert ach > 0

    def test_invalid_humidity_conditions(self) -> None:
        """Error when outside more humid."""
        with pytest.raises(ValueError, match="must be lower"):
            required_ach_humidity_control(0.001, 1000.0, 0.010, 0.015)
