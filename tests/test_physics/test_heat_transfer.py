"""Tests for heat transfer calculations."""

from __future__ import annotations

from cloudgrow_sim.physics.heat_transfer import (
    conduction_heat_transfer,
    conduction_resistance,
    convection_coefficient_forced,
    convection_coefficient_mixed,
    convection_coefficient_natural,
    grashof_number,
    ground_temperature_at_depth,
    ground_temperature_surface,
    overall_u_value,
    radiation_coefficient,
    radiation_heat_transfer,
    rayleigh_number,
    reynolds_number,
    sky_temperature,
    surface_heat_balance,
    view_factor_horizontal_to_sky,
    view_factor_tilted_to_sky,
    view_factor_vertical_to_sky,
)


class TestConductionHeatTransfer:
    """Tests for conduction heat transfer."""

    def test_basic(self) -> None:
        """Basic conduction calculation."""
        q = conduction_heat_transfer(
            u_value=5.0,  # W/(m²·K)
            area=100.0,  # m²
            t_inside=25.0,
            t_outside=10.0,
        )
        # Q = U * A * ΔT = 5 * 100 * 15 = 7500 W
        assert abs(q - 7500.0) < 1.0

    def test_no_temperature_difference(self) -> None:
        """Zero heat transfer when temperatures equal."""
        q = conduction_heat_transfer(5.0, 100.0, 20.0, 20.0)
        assert q == 0.0

    def test_heat_gain_when_outside_hotter(self) -> None:
        """Positive heat when outside is hotter (heat gain)."""
        q = conduction_heat_transfer(5.0, 100.0, 20.0, 30.0)
        assert q < 0  # Negative = heat gain (into building)


class TestConductionResistance:
    """Tests for thermal resistance calculation."""

    def test_basic(self) -> None:
        """R = thickness / conductivity."""
        r = conduction_resistance(0.1, 0.04)  # 10cm insulation k=0.04
        assert abs(r - 2.5) < 0.01

    def test_zero_thickness(self) -> None:
        """Zero thickness gives zero resistance."""
        r = conduction_resistance(0.0, 1.0)
        assert r == 0.0


class TestOverallUValue:
    """Tests for overall U-value calculation."""

    def test_single_layer(self) -> None:
        """Single layer with surface coefficients."""
        # R_total = 1/8 + 2.5 + 1/25 = 0.125 + 2.5 + 0.04 = 2.665
        # U = 1/2.665 = 0.375
        u = overall_u_value([2.5], h_inside=8.0, h_outside=25.0)
        expected = 1.0 / (1 / 8.0 + 2.5 + 1 / 25.0)
        assert abs(u - expected) < 0.01

    def test_multiple_layers(self) -> None:
        """Multiple layers sum resistances."""
        u = overall_u_value([1.0, 2.0, 0.5], h_inside=8.0, h_outside=25.0)
        expected = 1.0 / (1 / 8.0 + 1.0 + 2.0 + 0.5 + 1 / 25.0)
        assert abs(u - expected) < 0.01


class TestDimensionlessNumbers:
    """Tests for dimensionless numbers."""

    def test_grashof_positive(self) -> None:
        """Grashof number is positive for positive temperature difference."""
        gr = grashof_number(25.0, 20.0, 1.0)
        assert gr > 0

    def test_rayleigh_is_grashof_times_prandtl(self) -> None:
        """Ra = Gr * Pr."""
        gr = grashof_number(25.0, 20.0, 1.0)
        ra = rayleigh_number(25.0, 20.0, 1.0)
        # Pr for air is about 0.71
        assert 0.6 < ra / gr < 0.8

    def test_reynolds_positive(self) -> None:
        """Reynolds number is positive for positive velocity."""
        re = reynolds_number(5.0, 1.0)
        assert re > 0

    def test_reynolds_increases_with_velocity(self) -> None:
        """Higher velocity gives higher Reynolds number."""
        re_low = reynolds_number(1.0, 1.0)
        re_high = reynolds_number(10.0, 1.0)
        assert re_high > re_low


class TestNaturalConvection:
    """Tests for natural convection coefficient."""

    def test_vertical_surface(self) -> None:
        """Natural convection on vertical surface."""
        h = convection_coefficient_natural(30.0, 20.0, 1.0, orientation="vertical")
        # Typical range 2-10 W/(m²·K)
        assert 2 < h < 15

    def test_horizontal_up(self) -> None:
        """Horizontal surface facing up (hot)."""
        h = convection_coefficient_natural(30.0, 20.0, 1.0, orientation="horizontal_up")
        assert h > 0

    def test_horizontal_down(self) -> None:
        """Horizontal surface facing down (hot)."""
        h = convection_coefficient_natural(
            30.0, 20.0, 1.0, orientation="horizontal_down"
        )
        assert h > 0

    def test_no_temp_diff(self) -> None:
        """Minimal convection when no temperature difference."""
        h = convection_coefficient_natural(20.0, 20.0, 1.0, orientation="vertical")
        assert h < 1  # Very small


class TestForcedConvection:
    """Tests for forced convection coefficient."""

    def test_flat_plate(self) -> None:
        """Forced convection on flat plate."""
        h = convection_coefficient_forced(5.0, 1.0, geometry="flat_plate")
        # Typical range for moderate wind (empirical correlations vary)
        assert 5 < h < 50

    def test_cylinder(self) -> None:
        """Forced convection on cylinder."""
        h = convection_coefficient_forced(5.0, 0.1, geometry="cylinder")
        assert h > 0

    def test_increases_with_velocity(self) -> None:
        """Higher velocity gives higher coefficient."""
        h_low = convection_coefficient_forced(1.0, 1.0, geometry="flat_plate")
        h_high = convection_coefficient_forced(10.0, 1.0, geometry="flat_plate")
        assert h_high > h_low


class TestMixedConvection:
    """Tests for mixed convection coefficient."""

    def test_combines_natural_and_forced(self) -> None:
        """Mixed convection combines both."""
        h_nat = 5.0
        h_forced = 20.0
        h_mixed = convection_coefficient_mixed(h_nat, h_forced, n=3)

        # Mixed should be between forced and sum
        assert h_forced < h_mixed < h_nat + h_forced

    def test_dominated_by_larger(self) -> None:
        """Dominated by larger component."""
        h_mixed = convection_coefficient_mixed(2.0, 20.0)
        # Should be close to forced value
        assert 19 < h_mixed < 22


class TestRadiationHeatTransfer:
    """Tests for radiation heat transfer."""

    def test_basic(self) -> None:
        """Basic radiation calculation."""
        q = radiation_heat_transfer(
            emissivity=0.9,
            area=100.0,
            t_surface=25.0,
            t_surroundings=10.0,
        )
        # Should be positive (losing heat)
        assert q > 0

    def test_no_temp_diff(self) -> None:
        """Zero radiation when temperatures equal."""
        q = radiation_heat_transfer(0.9, 100.0, 20.0, 20.0)
        assert abs(q) < 0.1

    def test_fourth_power_dependence(self) -> None:
        """Radiation depends on T^4."""
        q1 = radiation_heat_transfer(0.9, 1.0, 50.0, 0.0)
        q2 = radiation_heat_transfer(0.9, 1.0, 100.0, 0.0)
        # Doubling T should increase by more than factor of 16
        # (because T in K, not °C)
        assert q2 / q1 > 2


class TestRadiationCoefficient:
    """Tests for linearized radiation coefficient."""

    def test_typical_value(self) -> None:
        """Radiation coefficient at typical temperatures."""
        h_r = radiation_coefficient(0.9, 25.0, 10.0)
        # Typical range 4-6 W/(m²·K)
        assert 4 < h_r < 7


class TestViewFactors:
    """Tests for view factors."""

    def test_horizontal_to_sky(self) -> None:
        """Horizontal surface sees full sky."""
        assert view_factor_horizontal_to_sky() == 1.0

    def test_vertical_to_sky(self) -> None:
        """Vertical surface sees half sky."""
        assert view_factor_vertical_to_sky() == 0.5

    def test_tilted_zero(self) -> None:
        """Horizontal (0° tilt) sees full sky."""
        vf = view_factor_tilted_to_sky(0.0)
        assert abs(vf - 1.0) < 0.01

    def test_tilted_90(self) -> None:
        """Vertical (90° tilt) sees half sky."""
        vf = view_factor_tilted_to_sky(90.0)
        assert abs(vf - 0.5) < 0.01


class TestSkyTemperature:
    """Tests for sky temperature calculation."""

    def test_clear_sky_cold(self) -> None:
        """Clear sky is colder than ambient."""
        t_sky = sky_temperature(20.0, 50.0, cloud_cover=0.0)  # Clear
        assert t_sky < 20.0

    def test_cloudy_warmer(self) -> None:
        """Cloudy sky is warmer than clear."""
        t_clear = sky_temperature(20.0, 50.0, cloud_cover=0.0)
        t_cloudy = sky_temperature(20.0, 50.0, cloud_cover=1.0)
        assert t_cloudy > t_clear

    def test_humid_warmer(self) -> None:
        """More humid air gives warmer sky temp."""
        t_dry = sky_temperature(20.0, 30.0, cloud_cover=0.0)
        t_humid = sky_temperature(20.0, 80.0, cloud_cover=0.0)
        assert t_humid > t_dry


class TestGroundTemperature:
    """Tests for ground temperature calculation."""

    def test_surface(self) -> None:
        """Surface temperature has full amplitude."""
        t_surf = ground_temperature_surface(15.0, 10.0, 180)
        # At day 180 (summer), surface should be warmer than mean
        assert t_surf > 15.0

    def test_deep_is_mean(self) -> None:
        """Deep temperature approaches annual mean."""
        t_deep = ground_temperature_at_depth(15.0, 10.0, 180, 10.0)  # 10m
        # Should be close to mean
        assert abs(t_deep - 15.0) < 2.0

    def test_amplitude_decreases_with_depth(self) -> None:
        """Temperature swing decreases with depth."""
        # Summer (warmer than mean)
        t_surf = ground_temperature_at_depth(15.0, 10.0, 180, 0.0)
        t_1m = ground_temperature_at_depth(15.0, 10.0, 180, 1.0)
        t_5m = ground_temperature_at_depth(15.0, 10.0, 180, 5.0)

        # Deviation from mean decreases with depth
        assert abs(t_surf - 15.0) > abs(t_1m - 15.0)
        assert abs(t_1m - 15.0) > abs(t_5m - 15.0)


class TestSurfaceHeatBalance:
    """Tests for surface heat balance."""

    def test_all_positive(self) -> None:
        """Sum of all heat fluxes."""
        # q_net = q_solar - q_convection - q_radiation - q_conduction
        # = 500 - 50 - 100 - 150 = 200
        q_net = surface_heat_balance(
            q_solar=500.0,
            q_convection=50.0,
            q_radiation=100.0,
            q_conduction=150.0,
        )
        assert abs(q_net - 200.0) < 0.1

    def test_all_zero(self) -> None:
        """Zero net when all zero."""
        q_net = surface_heat_balance(0.0, 0.0, 0.0, 0.0)
        assert q_net == 0.0
