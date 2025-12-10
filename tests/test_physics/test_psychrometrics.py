"""Tests for psychrometric calculations with CoolProp validation.

These tests verify ASHRAE psychrometric calculations against CoolProp
reference implementation where available.
"""

from __future__ import annotations

import pytest

from cloudgrow_sim.physics.psychrometrics import (
    air_density,
    dew_point,
    dew_point_from_humidity_ratio,
    enthalpy,
    humidity_ratio,
    humidity_ratio_from_wet_bulb,
    latent_heat_of_vaporization,
    relative_humidity,
    saturation_pressure,
    specific_volume,
    vapor_pressure,
    wet_bulb_temperature,
)

# Try to import CoolProp for cross-validation
try:
    import CoolProp.HumidAirProp as HAP

    COOLPROP_AVAILABLE = True
except ImportError:
    COOLPROP_AVAILABLE = False


class TestSaturationPressure:
    """Tests for saturation pressure calculation."""

    def test_zero_celsius(self) -> None:
        """Saturation pressure at 0°C should be ~611.2 Pa."""
        p_sat = saturation_pressure(0.0)
        assert abs(p_sat - 611.2) < 1.0  # Within 1 Pa

    def test_twenty_celsius(self) -> None:
        """Saturation pressure at 20°C should be ~2338 Pa."""
        p_sat = saturation_pressure(20.0)
        assert abs(p_sat - 2338.8) < 5.0  # Within 5 Pa

    def test_hundred_celsius(self) -> None:
        """Saturation pressure at 100°C should be ~101325 Pa (1 atm)."""
        p_sat = saturation_pressure(100.0)
        # At 100°C, water boils at 1 atm
        assert abs(p_sat - 101325) < 500  # Within 0.5%

    def test_negative_temperature(self) -> None:
        """Saturation pressure over ice at -10°C."""
        p_sat = saturation_pressure(-10.0, ice=True)
        # Should be around 260 Pa
        assert 250 < p_sat < 270

    def test_invalid_temperature_water(self) -> None:
        """Raise error for temperature outside valid range."""
        with pytest.raises(ValueError, match="outside valid range"):
            saturation_pressure(250.0)

    def test_invalid_temperature_ice(self) -> None:
        """Raise error for temperature outside ice range."""
        with pytest.raises(ValueError, match="outside valid range"):
            saturation_pressure(-150.0, ice=True)

    @pytest.mark.skipif(not COOLPROP_AVAILABLE, reason="CoolProp not installed")
    @pytest.mark.parametrize("temp", [0, 10, 20, 30, 40, 50])
    def test_against_coolprop(self, temp: float) -> None:
        """Validate saturation pressure against CoolProp."""
        # CoolProp returns pressure at 100% RH
        expected = HAP.HAPropsSI("P_w", "T", temp + 273.15, "P", 101325, "R", 1.0)
        actual = saturation_pressure(temp)
        rel_error = abs(actual - expected) / expected
        assert rel_error < 0.01, f"At {temp}°C: {actual} vs {expected} (CoolProp)"


class TestHumidityRatio:
    """Tests for humidity ratio calculation."""

    def test_zero_humidity(self) -> None:
        """Humidity ratio at 0% RH should be 0."""
        w = humidity_ratio(20.0, 0.0)
        assert w == 0.0

    def test_typical_conditions(self) -> None:
        """Humidity ratio at 20°C, 50% RH."""
        w = humidity_ratio(20.0, 50.0)
        # Should be around 0.0073 kg/kg
        assert 0.006 < w < 0.008

    def test_high_humidity(self) -> None:
        """Humidity ratio at 30°C, 80% RH."""
        w = humidity_ratio(30.0, 80.0)
        # Should be around 0.0216 kg/kg
        assert 0.020 < w < 0.023

    def test_invalid_rh_low(self) -> None:
        """Raise error for RH < 0."""
        with pytest.raises(ValueError, match="Relative humidity"):
            humidity_ratio(20.0, -10.0)

    def test_invalid_rh_high(self) -> None:
        """Raise error for RH > 100."""
        with pytest.raises(ValueError, match="Relative humidity"):
            humidity_ratio(20.0, 110.0)


class TestWetBulbTemperature:
    """Tests for wet-bulb temperature calculation."""

    def test_saturated_air(self) -> None:
        """Wet-bulb equals dry-bulb at 100% RH."""
        t_wb = wet_bulb_temperature(25.0, 100.0)
        assert abs(t_wb - 25.0) < 0.5

    def test_typical_conditions(self) -> None:
        """Wet-bulb at 30°C, 50% RH should be around 22°C."""
        t_wb = wet_bulb_temperature(30.0, 50.0)
        assert 20 < t_wb < 24

    def test_dry_conditions(self) -> None:
        """Wet-bulb at 35°C, 20% RH should be much lower."""
        t_wb = wet_bulb_temperature(35.0, 20.0)
        # Large wet-bulb depression for hot/dry conditions
        assert t_wb < 25.0


class TestDewPoint:
    """Tests for dew point calculation."""

    def test_saturated_air(self) -> None:
        """Dew point equals dry-bulb at 100% RH."""
        t_dp = dew_point(25.0, 100.0)
        assert abs(t_dp - 25.0) < 0.5

    def test_typical_conditions(self) -> None:
        """Dew point at 25°C, 50% RH should be around 14°C."""
        t_dp = dew_point(25.0, 50.0)
        assert 12 < t_dp < 16

    def test_zero_humidity(self) -> None:
        """Dew point at 0% RH should be very low."""
        t_dp = dew_point(25.0, 0.0)
        assert t_dp < -200  # Approaches absolute zero


class TestEnthalpy:
    """Tests for moist air enthalpy calculation."""

    def test_dry_air_zero(self) -> None:
        """Enthalpy of dry air at 0°C is 0 kJ/kg."""
        h = enthalpy(0.0, 0.0)
        assert abs(h) < 0.1

    def test_typical_conditions(self) -> None:
        """Enthalpy at 20°C with W=0.0074."""
        h = enthalpy(20.0, 0.0074)
        # Should be around 38.8 kJ/kg
        assert 35 < h < 42

    def test_hot_humid(self) -> None:
        """Enthalpy at 30°C with W=0.020."""
        h = enthalpy(30.0, 0.020)
        # Should be around 81 kJ/kg
        assert 75 < h < 85


class TestAirDensity:
    """Tests for moist air density calculation."""

    def test_standard_conditions(self) -> None:
        """Air density at 20°C, low humidity."""
        rho = air_density(20.0, 0.0074)
        # Should be around 1.2 kg/m³
        assert 1.15 < rho < 1.25

    def test_hot_humid_less_dense(self) -> None:
        """Hot humid air is less dense than cool dry air."""
        rho_cool = air_density(20.0, 0.005)
        rho_hot = air_density(35.0, 0.025)
        assert rho_hot < rho_cool


class TestRelativeHumidity:
    """Tests for relative humidity from humidity ratio."""

    def test_roundtrip(self) -> None:
        """Roundtrip: RH -> W -> RH."""
        t = 25.0
        rh_original = 60.0
        w = humidity_ratio(t, rh_original)
        rh_calc = relative_humidity(t, w)
        assert abs(rh_calc - rh_original) < 0.5


class TestVaporPressure:
    """Tests for vapor pressure calculation."""

    def test_at_saturation(self) -> None:
        """Vapor pressure equals saturation pressure at 100% RH."""
        t = 25.0
        p_v = vapor_pressure(t, 100.0)
        p_sat = saturation_pressure(t)
        assert abs(p_v - p_sat) < 1.0


class TestLatentHeat:
    """Tests for latent heat of vaporization."""

    def test_at_zero(self) -> None:
        """Latent heat at 0°C should be ~2.501 MJ/kg."""
        h_fg = latent_heat_of_vaporization(0.0)
        assert 2.45e6 < h_fg < 2.55e6

    def test_decreases_with_temp(self) -> None:
        """Latent heat decreases with temperature."""
        h_0 = latent_heat_of_vaporization(0.0)
        h_50 = latent_heat_of_vaporization(50.0)
        assert h_50 < h_0


class TestHumidityRatioFromWetBulb:
    """Tests for humidity ratio from wet-bulb temperature."""

    def test_wb_equals_db(self) -> None:
        """At saturation, wet-bulb equals dry-bulb."""
        # At saturation, T_wb = T_db
        w = humidity_ratio_from_wet_bulb(25.0, 25.0)
        w_sat = humidity_ratio(25.0, 100.0)
        assert abs(w - w_sat) / w_sat < 0.05

    def test_wb_less_than_db(self) -> None:
        """Wet-bulb less than dry-bulb gives positive humidity ratio."""
        w = humidity_ratio_from_wet_bulb(30.0, 20.0)
        assert w > 0

    def test_invalid_wb_greater_than_db(self) -> None:
        """Error when wet-bulb exceeds dry-bulb."""
        with pytest.raises(ValueError, match="cannot exceed"):
            humidity_ratio_from_wet_bulb(20.0, 25.0)


class TestSpecificVolume:
    """Tests for specific volume calculation."""

    def test_standard_conditions(self) -> None:
        """Specific volume at standard conditions."""
        v = specific_volume(20.0, 0.007)
        # Should be around 0.84 m³/kg
        assert 0.80 < v < 0.90

    def test_inverse_of_density(self) -> None:
        """Specific volume is inverse of density for dry air."""
        t = 25.0
        w = 0.010
        v = specific_volume(t, w)
        rho = air_density(t, w)
        # Note: specific_volume is per kg_dry_air, density is per m³
        # For moist air: v ≈ 1/rho * (1 + w)
        # Allow 2% tolerance for thermodynamic approximations
        assert abs(v * rho - (1 + 1.6078 * w)) < 0.02


class TestDewPointFromHumidityRatio:
    """Tests for dew point from humidity ratio."""

    def test_roundtrip(self) -> None:
        """Roundtrip: T,RH -> W -> T_dp, then check T_dp."""
        t = 30.0
        rh = 60.0
        w = humidity_ratio(t, rh)
        t_dp_calc = dew_point_from_humidity_ratio(w)
        t_dp_direct = dew_point(t, rh)
        # Should be close (within 1°C)
        assert abs(t_dp_calc - t_dp_direct) < 1.0
