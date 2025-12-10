"""Solar radiation calculations following ASHRAE standards.

Reference: ASHRAE Handbook—Fundamentals (2021), Chapter 14

This module implements solar position and radiation calculations:
- Solar position (altitude, azimuth, zenith)
- Extraterrestrial radiation
- Direct normal irradiance
- Diffuse radiation (Erbs correlation)
- Radiation on tilted surfaces
- PAR conversion

All angles are in degrees unless otherwise noted.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import NamedTuple

from cloudgrow_sim.physics.constants import (
    EARTH_AXIAL_TILT,
    PAR_CONVERSION_FACTOR,
    PAR_FRACTION,
    SOLAR_CONSTANT,
)


class SolarPosition(NamedTuple):
    """Solar position angles.

    Attributes:
        altitude: Solar altitude angle in degrees (0 at horizon, 90 at zenith).
        azimuth: Solar azimuth angle in degrees from North (clockwise).
        zenith: Solar zenith angle in degrees (90 - altitude).
        declination: Solar declination in degrees.
        hour_angle: Solar hour angle in degrees.
    """

    altitude: float
    azimuth: float
    zenith: float
    declination: float
    hour_angle: float


def day_of_year(dt: datetime) -> int:
    """Get day of year (1-366) from datetime.

    Args:
        dt: Datetime object.

    Returns:
        Day of year (1 = January 1).
    """
    return dt.timetuple().tm_yday


def solar_declination(day: int) -> float:
    """Calculate solar declination angle.

    ASHRAE Handbook—Fundamentals, Chapter 14, Equation 5.

    The declination is the angle between the equatorial plane and a line
    from the center of the Earth to the center of the Sun.

    Args:
        day: Day of year (1-366).

    Returns:
        Solar declination in degrees.

    Examples:
        >>> solar_declination(172)  # Summer solstice (approx)
        23.44...
        >>> solar_declination(356)  # Winter solstice (approx)
        -23.44...
    """
    # ASHRAE equation (simplified)
    # δ = 23.45 * sin(360 * (284 + n) / 365)
    angle_rad = math.radians(360.0 * (284 + day) / 365.0)
    return EARTH_AXIAL_TILT * math.sin(angle_rad)


def equation_of_time(day: int) -> float:
    """Calculate equation of time correction.

    ASHRAE Handbook—Fundamentals, Chapter 14, Equation 6.

    The equation of time accounts for the eccentricity of Earth's orbit
    and the tilt of Earth's axis.

    Args:
        day: Day of year (1-366).

    Returns:
        Equation of time in minutes.
    """
    b = math.radians(360.0 * (day - 81) / 364.0)

    # ASHRAE equation 6
    eot = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)

    return eot


def solar_time(
    dt: datetime,
    longitude: float,
    *,
    standard_meridian: float | None = None,
) -> float:
    """Calculate apparent solar time.

    Args:
        dt: Local standard time as datetime.
        longitude: Site longitude in degrees (positive East).
        standard_meridian: Standard meridian for timezone (defaults to nearest 15°).

    Returns:
        Apparent solar time as decimal hours.
    """
    # Standard meridian (15° per hour offset from UTC)
    if standard_meridian is None:
        # Estimate from longitude
        standard_meridian = round(longitude / 15.0) * 15.0

    # Local standard time in decimal hours
    lst = dt.hour + dt.minute / 60.0 + dt.second / 3600.0

    # Equation of time correction
    eot = equation_of_time(day_of_year(dt))

    # Longitude correction (4 minutes per degree)
    longitude_correction = 4.0 * (standard_meridian - longitude)

    # Apparent solar time
    ast = lst + eot / 60.0 - longitude_correction / 60.0

    return ast


def hour_angle(solar_time_hours: float) -> float:
    """Calculate solar hour angle.

    The hour angle is the angular displacement of the sun east or west
    of the local meridian. Negative before solar noon, positive after.

    Args:
        solar_time_hours: Apparent solar time in decimal hours.

    Returns:
        Hour angle in degrees.
    """
    # 15° per hour, with solar noon at 0°
    return 15.0 * (solar_time_hours - 12.0)


def solar_position(
    latitude: float,
    longitude: float,
    dt: datetime,
    *,
    standard_meridian: float | None = None,
) -> SolarPosition:
    """Calculate solar position angles.

    ASHRAE Handbook—Fundamentals, Chapter 14.

    Args:
        latitude: Site latitude in degrees (positive North).
        longitude: Site longitude in degrees (positive East).
        dt: Datetime for calculation (should be local standard time).
        standard_meridian: Standard meridian for timezone.

    Returns:
        SolarPosition with altitude, azimuth, zenith, declination, hour_angle.

    Examples:
        >>> from datetime import datetime
        >>> pos = solar_position(37.3, -78.4, datetime(2025, 6, 21, 12, 0))
        >>> pos.altitude  # Near-maximum altitude at summer solstice noon
        75.0...
    """
    # Day of year
    n = day_of_year(dt)

    # Solar declination
    decl = solar_declination(n)
    decl_rad = math.radians(decl)

    # Solar time and hour angle
    ast = solar_time(dt, longitude, standard_meridian=standard_meridian)
    ha = hour_angle(ast)
    ha_rad = math.radians(ha)

    # Latitude in radians
    lat_rad = math.radians(latitude)

    # Solar altitude (elevation) angle
    # sin(altitude) = sin(lat)*sin(decl) + cos(lat)*cos(decl)*cos(ha)
    sin_alt = math.sin(lat_rad) * math.sin(decl_rad) + math.cos(lat_rad) * math.cos(
        decl_rad
    ) * math.cos(ha_rad)
    sin_alt = max(-1.0, min(1.0, sin_alt))  # Clamp for numerical stability
    altitude = math.degrees(math.asin(sin_alt))

    # Solar zenith angle
    zenith = 90.0 - altitude

    # Solar azimuth angle (from North, clockwise)
    # cos(azimuth) = (sin(altitude)*sin(lat) - sin(decl)) / (cos(altitude)*cos(lat))
    cos_alt = math.cos(math.radians(altitude))
    if cos_alt > 0.001:  # Avoid division by zero near zenith
        cos_az = (sin_alt * math.sin(lat_rad) - math.sin(decl_rad)) / (
            cos_alt * math.cos(lat_rad)
        )
        cos_az = max(-1.0, min(1.0, cos_az))
        azimuth = math.degrees(math.acos(cos_az))

        # Adjust for afternoon (azimuth > 180°)
        if ha > 0:
            azimuth = 360.0 - azimuth
    else:
        # Sun at zenith (rare case)
        azimuth = 180.0

    return SolarPosition(
        altitude=altitude,
        azimuth=azimuth,
        zenith=zenith,
        declination=decl,
        hour_angle=ha,
    )


def extraterrestrial_radiation(day: int) -> float:
    """Calculate extraterrestrial radiation on a surface normal to sun rays.

    ASHRAE Handbook—Fundamentals, Chapter 14, Equation 4.

    This is the solar constant corrected for Earth-Sun distance variation.

    Args:
        day: Day of year (1-366).

    Returns:
        Extraterrestrial radiation in W/m².

    Examples:
        >>> extraterrestrial_radiation(1)  # Perihelion (early January)
        1412.0...
        >>> extraterrestrial_radiation(182)  # Aphelion (early July)
        1322.0...
    """
    # ASHRAE equation 4
    # E_o = E_sc * (1 + 0.033 * cos(360 * n / 365))
    angle_rad = math.radians(360.0 * day / 365.0)
    return SOLAR_CONSTANT * (1.0 + 0.033 * math.cos(angle_rad))


def clearness_index(ghi: float, extraterrestrial: float) -> float:
    """Calculate clearness index (Kt).

    The clearness index is the ratio of global horizontal irradiance to
    extraterrestrial radiation.

    Args:
        ghi: Global horizontal irradiance in W/m².
        extraterrestrial: Extraterrestrial radiation in W/m².

    Returns:
        Clearness index (0-1).
    """
    if extraterrestrial <= 0:
        return 0.0
    return max(0.0, min(1.0, ghi / extraterrestrial))


def air_mass(altitude: float) -> float:
    """Calculate relative air mass using Kasten-Young formula.

    The air mass is the path length of sunlight through the atmosphere
    relative to the path length at zenith.

    Args:
        altitude: Solar altitude angle in degrees.

    Returns:
        Relative air mass (1.0 at zenith, higher at lower angles).

    Examples:
        >>> air_mass(90.0)  # Sun at zenith
        1.0
        >>> air_mass(30.0)  # Sun at 30° altitude
        2.0  # Approximately
    """
    if altitude <= 0:
        return 40.0  # Very high value at/below horizon

    zenith = 90.0 - altitude
    zenith_rad = math.radians(zenith)

    # Kasten-Young formula (more accurate at low angles)
    return float(
        1.0 / (math.cos(zenith_rad) + 0.50572 * (96.07995 - zenith) ** -1.6364)
    )


def atmospheric_transmittance(altitude: float, day: int) -> float:
    """Calculate atmospheric transmittance for direct beam radiation.

    Simplified ASHRAE clear-sky model.

    Args:
        altitude: Solar altitude angle in degrees.
        day: Day of year (1-366).

    Returns:
        Atmospheric transmittance (0-1).
    """
    if altitude <= 0:
        return 0.0

    # Air mass (simplified Kasten-Young formula)
    zenith_rad = math.radians(90.0 - altitude)
    air_mass = 1.0 / (
        math.cos(zenith_rad) + 0.50572 * (96.07995 - (90.0 - altitude)) ** -1.6364
    )

    # Optical depth (varies seasonally)
    # Simplified model
    tau_b = 0.3 + 0.1 * math.cos(math.radians(360.0 * (day - 172) / 365.0))

    # Transmittance
    return math.exp(-tau_b * air_mass)


def direct_normal_irradiance(
    altitude: float,
    day: int,
    *,
    turbidity: float = 2.0,
) -> float:
    """Calculate direct normal irradiance under clear sky conditions.

    ASHRAE clear-sky model (simplified).

    Args:
        altitude: Solar altitude angle in degrees.
        day: Day of year (1-366).
        turbidity: Linke turbidity factor (2.0 = clear, 3.0 = hazy).

    Returns:
        Direct normal irradiance in W/m².
    """
    if altitude <= 0:
        return 0.0

    # Extraterrestrial radiation
    e_o = extraterrestrial_radiation(day)

    # Air mass
    zenith_rad = math.radians(90.0 - altitude)
    if altitude > 5:
        air_mass = 1.0 / math.cos(zenith_rad)
    else:
        # Kasten-Young formula for low sun angles
        air_mass = 1.0 / (
            math.cos(zenith_rad) + 0.50572 * (96.07995 - (90.0 - altitude)) ** -1.6364
        )

    # Optical depth (ASHRAE model)
    tau_b = 0.2 + 0.1 * turbidity * math.cos(math.radians(360.0 * (day - 172) / 365.0))

    # Direct normal irradiance
    dni = e_o * math.exp(-tau_b * air_mass)

    return max(0.0, dni)


def diffuse_radiation(
    ghi: float,
    dni: float,
    altitude: float,
) -> float:
    """Calculate diffuse horizontal irradiance using Erbs correlation.

    Reference: Erbs, Klein, and Duffie (1982)

    Args:
        ghi: Global horizontal irradiance in W/m².
        dni: Direct normal irradiance in W/m².
        altitude: Solar altitude angle in degrees.

    Returns:
        Diffuse horizontal irradiance in W/m².
    """
    if altitude <= 0 or ghi <= 0:
        return 0.0

    # Direct beam contribution to GHI
    sin_alt = math.sin(math.radians(altitude))
    direct_horizontal = dni * sin_alt

    # Diffuse is remainder
    diffuse = ghi - direct_horizontal

    return max(0.0, diffuse)


def diffuse_fraction_erbs(kt: float) -> float:
    """Calculate diffuse fraction using Erbs correlation.

    Reference: Erbs, Klein, and Duffie (1982)

    Args:
        kt: Clearness index (0-1).

    Returns:
        Diffuse fraction (0-1).
    """
    if kt <= 0.22:
        return 1.0 - 0.09 * kt
    elif kt <= 0.80:
        return 0.9511 - 0.1604 * kt + 4.388 * kt**2 - 16.638 * kt**3 + 12.336 * kt**4
    else:
        return 0.165


def global_horizontal_irradiance(
    dni: float,
    diffuse: float,
    altitude: float,
) -> float:
    """Calculate global horizontal irradiance from components.

    Args:
        dni: Direct normal irradiance in W/m².
        diffuse: Diffuse horizontal irradiance in W/m².
        altitude: Solar altitude angle in degrees.

    Returns:
        Global horizontal irradiance in W/m².
    """
    if altitude <= 0:
        return diffuse

    sin_alt = math.sin(math.radians(altitude))
    return dni * sin_alt + diffuse


def radiation_on_tilted_surface(
    dni: float,
    diffuse: float,
    altitude: float,
    azimuth: float,
    tilt: float,
    surface_azimuth: float,
    *,
    ground_reflectance: float = 0.2,
) -> float:
    """Calculate total irradiance on a tilted surface.

    Uses isotropic sky model for diffuse radiation.

    Args:
        dni: Direct normal irradiance in W/m².
        diffuse: Diffuse horizontal irradiance in W/m².
        altitude: Solar altitude angle in degrees.
        azimuth: Solar azimuth angle in degrees from North.
        tilt: Surface tilt angle in degrees (0 = horizontal, 90 = vertical).
        surface_azimuth: Surface azimuth in degrees from North.
        ground_reflectance: Ground albedo (0-1).

    Returns:
        Total irradiance on tilted surface in W/m².
    """
    if altitude <= 0:
        return 0.0

    # Convert angles to radians
    alt_rad = math.radians(altitude)
    az_rad = math.radians(azimuth)
    tilt_rad = math.radians(tilt)
    surf_az_rad = math.radians(surface_azimuth)

    # Angle of incidence on tilted surface
    cos_theta = math.sin(alt_rad) * math.cos(tilt_rad) + math.cos(alt_rad) * math.sin(
        tilt_rad
    ) * math.cos(az_rad - surf_az_rad)
    cos_theta = max(0.0, cos_theta)

    # Direct beam on tilted surface
    beam = dni * cos_theta

    # Diffuse (isotropic sky model)
    diffuse_tilted = diffuse * (1 + math.cos(tilt_rad)) / 2

    # Ground reflected (isotropic)
    ghi = global_horizontal_irradiance(dni, diffuse, altitude)
    ground_reflected = ghi * ground_reflectance * (1 - math.cos(tilt_rad)) / 2

    return beam + diffuse_tilted + ground_reflected


def par_from_solar(solar_radiation: float) -> float:
    """Convert solar radiation to Photosynthetically Active Radiation (PAR).

    PAR is the radiation in the 400-700 nm wavelength range that plants
    use for photosynthesis.

    Args:
        solar_radiation: Total solar radiation in W/m².

    Returns:
        PAR in µmol/(m²·s).

    Examples:
        >>> par_from_solar(1000.0)  # Full sun
        2056.5...
        >>> par_from_solar(500.0)  # Cloudy
        1028.2...
    """
    # Solar to PAR W/m² (approximately 45% of total solar)
    par_watts = solar_radiation * PAR_FRACTION

    # Convert W/m² to µmol/(m²·s)
    # 1 W/m² ≈ 4.57 µmol/(m²·s) for sunlight
    return par_watts * PAR_CONVERSION_FACTOR


def daily_solar_radiation(
    latitude: float,
    day: int,
    *,
    clearness: float = 0.75,
) -> float:
    """Estimate daily total solar radiation on horizontal surface.

    Simplified calculation for clear/partly cloudy days.

    Args:
        latitude: Site latitude in degrees.
        day: Day of year (1-366).
        clearness: Atmospheric clearness factor (0-1).

    Returns:
        Daily total radiation in MJ/m²/day.
    """
    # Extraterrestrial daily radiation
    e_o = extraterrestrial_radiation(day)

    # Day length approximation
    decl = solar_declination(day)
    lat_rad = math.radians(latitude)
    decl_rad = math.radians(decl)

    # Sunset hour angle
    cos_ws = -math.tan(lat_rad) * math.tan(decl_rad)
    cos_ws = max(-1.0, min(1.0, cos_ws))
    ws = math.degrees(math.acos(cos_ws))

    # Day length in hours
    day_length = 2 * ws / 15.0

    # Daily extraterrestrial radiation (MJ/m²/day)
    # Simplified: average irradiance * day length
    h_o = e_o * 0.0036 * day_length  # Convert W·h to MJ

    # Apply clearness factor
    return h_o * clearness


def sunrise_sunset_times(
    latitude: float,
    day: int,
) -> tuple[float, float]:
    """Calculate sunrise and sunset times.

    Args:
        latitude: Site latitude in degrees.
        day: Day of year (1-366).

    Returns:
        Tuple of (sunrise, sunset) in decimal hours (solar time).
    """
    decl = solar_declination(day)
    lat_rad = math.radians(latitude)
    decl_rad = math.radians(decl)

    # Sunset hour angle
    cos_ws = -math.tan(lat_rad) * math.tan(decl_rad)
    cos_ws = max(-1.0, min(1.0, cos_ws))

    if cos_ws >= 1:
        # Polar night
        return (12.0, 12.0)
    elif cos_ws <= -1:
        # Midnight sun
        return (0.0, 24.0)

    ws = math.degrees(math.acos(cos_ws))

    # Convert hour angle to solar time
    sunrise = 12.0 - ws / 15.0
    sunset = 12.0 + ws / 15.0

    return (sunrise, sunset)
