"""Tests for solar radiation calculations."""

from __future__ import annotations

import math
from datetime import UTC, datetime

from cloudgrow_sim.physics.solar import (
    air_mass,
    day_of_year,
    diffuse_radiation,
    direct_normal_irradiance,
    equation_of_time,
    extraterrestrial_radiation,
    hour_angle,
    par_from_solar,
    radiation_on_tilted_surface,
    solar_declination,
    solar_position,
    sunrise_sunset_times,
)


class TestDayOfYear:
    """Tests for day of year calculation."""

    def test_january_first(self) -> None:
        """January 1st is day 1."""
        dt = datetime(2025, 1, 1, tzinfo=UTC)
        assert day_of_year(dt) == 1

    def test_december_31_non_leap(self) -> None:
        """December 31st is day 365 in non-leap year."""
        dt = datetime(2025, 12, 31, tzinfo=UTC)
        assert day_of_year(dt) == 365

    def test_december_31_leap(self) -> None:
        """December 31st is day 366 in leap year."""
        dt = datetime(2024, 12, 31, tzinfo=UTC)
        assert day_of_year(dt) == 366


class TestSolarDeclination:
    """Tests for solar declination angle."""

    def test_summer_solstice(self) -> None:
        """Maximum declination around day 172 (June 21)."""
        decl = solar_declination(172)
        # Should be around +23.45°
        assert 22 < decl < 24

    def test_winter_solstice(self) -> None:
        """Minimum declination around day 355 (Dec 21)."""
        decl = solar_declination(355)
        # Should be around -23.45°
        assert -24 < decl < -22

    def test_equinox(self) -> None:
        """Declination near zero at equinoxes."""
        # Spring equinox around day 80 (March 21)
        decl = solar_declination(80)
        assert abs(decl) < 2


class TestEquationOfTime:
    """Tests for equation of time."""

    def test_range(self) -> None:
        """Equation of time should be within ±17 minutes."""
        for day in range(1, 366):
            eot = equation_of_time(day)
            assert -17 < eot < 17

    def test_february_peak(self) -> None:
        """Large magnitude around early February."""
        eot = equation_of_time(45)  # Mid-February
        # EOT has significant magnitude (can be negative or positive
        # depending on formula convention)
        assert abs(eot) > 5


class TestHourAngle:
    """Tests for hour angle calculation."""

    def test_solar_noon(self) -> None:
        """Hour angle is zero at solar noon."""
        # At solar noon, local solar time is 12:00
        ha = hour_angle(12.0)
        assert abs(ha) < 0.01

    def test_morning(self) -> None:
        """Hour angle is negative in morning."""
        ha = hour_angle(9.0)
        assert ha < 0

    def test_afternoon(self) -> None:
        """Hour angle is positive in afternoon."""
        ha = hour_angle(15.0)
        assert ha > 0


class TestSolarPosition:
    """Tests for solar position calculation."""

    def test_solar_noon_summer(self) -> None:
        """Summer has higher altitude than winter at same time."""
        lat = 37.0  # Northern hemisphere
        lon = 0.0  # Use prime meridian for simplicity
        # Use noon UTC directly for prime meridian
        dt_summer = datetime(2025, 6, 21, 12, 0, tzinfo=UTC)
        dt_winter = datetime(2025, 12, 21, 12, 0, tzinfo=UTC)

        pos_summer = solar_position(lat, lon, dt_summer)
        pos_winter = solar_position(lat, lon, dt_winter)

        # Summer noon should be much higher than winter noon
        assert pos_summer.altitude > pos_winter.altitude
        # Summer declination is positive
        assert pos_summer.declination > 20  # Close to 23.45°

    def test_solar_noon_winter(self) -> None:
        """Winter has lower altitude and negative declination."""
        lat = 37.0
        lon = 0.0
        dt = datetime(2025, 12, 21, 12, 0, tzinfo=UTC)
        pos = solar_position(lat, lon, dt)

        # Winter declination is negative
        assert pos.declination < -20  # Close to -23.45°

    def test_night(self) -> None:
        """Very low or negative altitude when sun is low."""
        lat = 37.0
        lon = 0.0
        # Early morning at prime meridian
        dt = datetime(2025, 3, 21, 3, 0, tzinfo=UTC)
        pos = solar_position(lat, lon, dt)

        # Sun should be very low (before sunrise)
        assert pos.altitude < 10

    def test_zenith_plus_altitude(self) -> None:
        """Zenith + altitude should equal 90°."""
        lat = 37.0
        lon = 0.0
        dt = datetime(2025, 6, 21, 12, 0, tzinfo=UTC)
        pos = solar_position(lat, lon, dt)

        assert abs(pos.altitude + pos.zenith - 90) < 0.1


class TestExtraterrestrialRadiation:
    """Tests for extraterrestrial radiation."""

    def test_range(self) -> None:
        """Extraterrestrial radiation varies ~3.3% through the year."""
        min_val = min(extraterrestrial_radiation(d) for d in range(1, 366))
        max_val = max(extraterrestrial_radiation(d) for d in range(1, 366))

        # Solar constant is ~1367 W/m²
        assert 1320 < min_val < 1370
        assert 1380 < max_val < 1420

    def test_perihelion(self) -> None:
        """Maximum around January 3 (perihelion)."""
        g0_jan = extraterrestrial_radiation(3)
        g0_jul = extraterrestrial_radiation(185)
        assert g0_jan > g0_jul


class TestAirMass:
    """Tests for air mass calculation."""

    def test_zenith(self) -> None:
        """Air mass is 1 at zenith (altitude 90°)."""
        am = air_mass(90.0)
        assert abs(am - 1.0) < 0.01

    def test_low_angle(self) -> None:
        """Air mass increases at low sun angles."""
        am_90 = air_mass(90.0)
        am_30 = air_mass(30.0)
        am_10 = air_mass(10.0)

        assert am_30 > am_90
        assert am_10 > am_30

    def test_horizon(self) -> None:
        """Very high air mass near horizon."""
        am = air_mass(1.0)
        assert am > 20


class TestDirectNormalIrradiance:
    """Tests for direct normal irradiance."""

    def test_high_altitude(self) -> None:
        """High DNI at high sun altitude."""
        dni = direct_normal_irradiance(90.0, 172)
        # Should be close to extraterrestrial (reduced by atmosphere)
        assert 800 < dni < 1000

    def test_low_altitude(self) -> None:
        """Lower DNI at low sun altitude."""
        dni_high = direct_normal_irradiance(60.0, 172)
        dni_low = direct_normal_irradiance(20.0, 172)
        assert dni_low < dni_high

    def test_below_horizon(self) -> None:
        """Zero DNI below horizon."""
        dni = direct_normal_irradiance(-10.0, 172)
        assert dni == 0.0


class TestDiffuseRadiation:
    """Tests for diffuse radiation."""

    def test_positive(self) -> None:
        """Diffuse radiation is positive for clear sky."""
        ghi = 800.0
        dni = 600.0
        altitude = 45.0
        diffuse = diffuse_radiation(ghi, dni, altitude)
        assert diffuse > 0

    def test_mostly_diffuse_overcast(self) -> None:
        """When DNI is low, diffuse is high."""
        ghi = 400.0
        dni = 50.0  # Overcast
        altitude = 45.0
        diffuse = diffuse_radiation(ghi, dni, altitude)
        # Most of GHI should be diffuse
        assert diffuse > ghi * 0.7


class TestPARFromSolar:
    """Tests for PAR conversion."""

    def test_conversion_factor(self) -> None:
        """PAR is approximately 45% of solar * 4.57."""
        solar = 1000.0  # W/m²
        par = par_from_solar(solar)
        # PAR = solar * 0.45 * 4.57 ≈ 2057 µmol/m²/s
        assert 1900 < par < 2200

    def test_zero(self) -> None:
        """Zero solar gives zero PAR."""
        assert par_from_solar(0.0) == 0.0


class TestSunriseSunsetTimes:
    """Tests for sunrise/sunset calculation."""

    def test_summer(self) -> None:
        """Long days in summer."""
        lat = 37.0  # Northern hemisphere
        day = 172  # Summer solstice
        sunrise, sunset = sunrise_sunset_times(lat, day)
        # Very early sunrise, late sunset
        assert sunrise < 6.0
        assert sunset > 19.0

    def test_winter(self) -> None:
        """Short days in winter."""
        lat = 37.0
        day = 355  # Winter solstice
        sunrise, sunset = sunrise_sunset_times(lat, day)
        # Later sunrise, earlier sunset
        assert sunrise > 7.0
        assert sunset < 18.0

    def test_polar_day(self) -> None:
        """24-hour daylight in Arctic summer."""
        lat = 70.0  # Arctic
        day = 172
        sunrise, sunset = sunrise_sunset_times(lat, day)
        # No sunrise/sunset (polar day)
        assert sunrise is None or sunset is None or (sunset - sunrise) > 23


class TestRadiationOnTiltedSurface:
    """Tests for tilted surface irradiance."""

    def test_horizontal(self) -> None:
        """Horizontal surface gets GHI."""
        dni = 600.0
        diffuse = 200.0
        altitude = 60.0  # 90 - 30 zenith
        azimuth = 180.0  # South

        irr = radiation_on_tilted_surface(
            dni, diffuse, altitude, azimuth, tilt=0.0, surface_azimuth=180.0
        )
        # Horizontal surface should get approximately GHI
        ghi = dni * math.cos(math.radians(90 - altitude)) + diffuse
        assert abs(irr - ghi) < 50

    def test_optimal_tilt(self) -> None:
        """Surface tilted toward sun gets more radiation."""
        dni = 800.0
        diffuse = 150.0
        altitude = 50.0  # Sun at 50° altitude
        azimuth = 180.0

        # Horizontal
        irr_flat = radiation_on_tilted_surface(
            dni, diffuse, altitude, azimuth, tilt=0.0, surface_azimuth=180.0
        )
        # Tilted toward sun
        irr_tilted = radiation_on_tilted_surface(
            dni, diffuse, altitude, azimuth, tilt=40.0, surface_azimuth=180.0
        )

        assert irr_tilted > irr_flat
