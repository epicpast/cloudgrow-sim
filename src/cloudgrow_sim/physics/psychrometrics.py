"""ASHRAE psychrometric calculations.

Reference: ASHRAE Handbook-Fundamentals (2021), Chapter 1

This module implements psychrometric calculations for moist air following
ASHRAE standards. All functions use SI units:
- Temperature: C (internally converted to K for calculations)
- Pressure: Pa
- Humidity ratio: kg_water / kg_dry_air

Key equations implemented:
- Saturation pressure (Hyland-Wexler correlation)
- Humidity ratio
- Wet-bulb temperature (iterative)
- Dew point temperature
- Enthalpy of moist air
- Air density
"""

from __future__ import annotations

import math
from typing import Final

from cloudgrow_sim.physics.constants import (
    EPSILON,
    GAS_CONSTANT_DRY_AIR,
    LATENT_HEAT_VAPORIZATION_0C,
    SAT_PRESSURE_ICE_C1,
    SAT_PRESSURE_ICE_C2,
    SAT_PRESSURE_ICE_C3,
    SAT_PRESSURE_ICE_C4,
    SAT_PRESSURE_ICE_C5,
    SAT_PRESSURE_ICE_C6,
    SAT_PRESSURE_ICE_C7,
    SAT_PRESSURE_WATER_C1,
    SAT_PRESSURE_WATER_C2,
    SAT_PRESSURE_WATER_C3,
    SAT_PRESSURE_WATER_C4,
    SAT_PRESSURE_WATER_C5,
    SAT_PRESSURE_WATER_C6,
    STANDARD_PRESSURE,
    celsius_to_kelvin,
)

# =============================================================================
# ASHRAE Psychrometric Constants
# Reference: ASHRAE Handbook-Fundamentals (2021), Chapter 1
# =============================================================================

# M2 Fix: Extract magic numbers to named constants with ASHRAE references

#: Latent heat of vaporization at 0 C (kJ/kg)
#: ASHRAE Handbook-Fundamentals (2021), Chapter 1, Table 2
#: Used in psychrometric equation for humidity ratio from wet-bulb
_LATENT_HEAT_0C_KJ: Final[float] = 2501.0

#: Temperature coefficient for latent heat above freezing (kJ/(kg*C))
#: ASHRAE Handbook-Fundamentals (2021), Chapter 1, Equation 35
#: h_fg(T) = 2501 - 2.326*T for T >= 0 C
_LATENT_HEAT_COEF_WATER: Final[float] = 2.326

#: Specific heat of dry air at constant pressure (kJ/(kg*K))
#: ASHRAE Handbook-Fundamentals (2021), Chapter 1
_CP_DRY_AIR_KJ: Final[float] = 1.006

#: Specific heat of water vapor at constant pressure (kJ/(kg*K))
#: ASHRAE Handbook-Fundamentals (2021), Chapter 1
_CP_WATER_VAPOR_KJ: Final[float] = 1.86

#: Specific heat of liquid water (kJ/(kg*K))
#: ASHRAE Handbook-Fundamentals (2021), Chapter 1
_CP_LIQUID_WATER_KJ: Final[float] = 4.186

#: Latent heat of sublimation at 0 C (kJ/kg)
#: ASHRAE Handbook-Fundamentals (2021), Chapter 1
#: Used in psychrometric equation below freezing
_LATENT_HEAT_SUBLIMATION_0C_KJ: Final[float] = 2830.0

#: Temperature coefficient for latent heat below freezing (kJ/(kg*C))
#: ASHRAE Handbook-Fundamentals (2021), Chapter 1
_LATENT_HEAT_COEF_ICE: Final[float] = 0.24

#: Specific heat of ice (kJ/(kg*K))
#: ASHRAE Handbook-Fundamentals (2021), Chapter 1
_CP_ICE_KJ: Final[float] = 2.1

#: Minimum temperature bound for wet-bulb calculation (in C)
#: This prevents numerical issues at extreme low humidity conditions
_WET_BULB_MIN_TEMP: Final[float] = -100.0

#: Absolute minimum tolerance floor for humidity ratio comparisons
#: M5 Fix: Prevents numerical issues in very dry air conditions
#: where w_target approaches zero
_HUMIDITY_RATIO_MIN_TOL: Final[float] = 1e-8

#: Molecular weight ratio correction factor for moist air density
#: ASHRAE Handbook-Fundamentals (2021), Chapter 1, Equation 28
#:
#: The factor 1.6078 accounts for the difference in molecular weight between
#: dry air and water vapor:
#:   1.6078 = (M_air / M_water) - 1 = (28.966 / 18.015) - 1
#:
#: This correction factor appears because moist air is less dense than dry air
#: at the same temperature and pressure, due to water vapor's lower molecular
#: weight. The exact value derives from the ratio of molecular weights:
#:   M_air = 28.966 g/mol (dry air)
#:   M_water = 18.015 g/mol (water vapor)
#:   Ratio = 28.966 / 18.015 = 1.6078
_MOLECULAR_WEIGHT_RATIO_FACTOR: Final[float] = 1.6078


def saturation_pressure(t: float, *, ice: bool = False) -> float:
    """Calculate saturation vapor pressure using ASHRAE Hyland-Wexler correlation.

    ASHRAE Handbook-Fundamentals, Chapter 1, Equations 5 and 6.

    Args:
        t: Dry-bulb temperature in C.
        ice: If True, calculate over ice (for T < 0C). Default auto-selects.

    Returns:
        Saturation vapor pressure in Pa.

    Raises:
        ValueError: If temperature is outside valid range.

    Examples:
        >>> saturation_pressure(20.0)  # At 20C
        2338.8...
        >>> saturation_pressure(0.0)  # At 0C
        611.2...
        >>> saturation_pressure(-10.0, ice=True)  # Over ice at -10C
        259.9...
    """
    # Auto-select ice/water based on temperature
    if not ice and t < 0:
        ice = True

    t_k = celsius_to_kelvin(t)

    if ice:
        # Valid range: -100C to 0C
        if t < -100 or t > 0:
            msg = f"Temperature {t}C outside valid range for ice [-100, 0]"
            raise ValueError(msg)

        # ASHRAE equation 5 (over ice)
        ln_pws = (
            SAT_PRESSURE_ICE_C1 / t_k
            + SAT_PRESSURE_ICE_C2
            + SAT_PRESSURE_ICE_C3 * t_k
            + SAT_PRESSURE_ICE_C4 * t_k**2
            + SAT_PRESSURE_ICE_C5 * t_k**3
            + SAT_PRESSURE_ICE_C6 * t_k**4
            + SAT_PRESSURE_ICE_C7 * math.log(t_k)
        )
    else:
        # Valid range: 0C to 200C
        if t < 0 or t > 200:
            msg = f"Temperature {t}C outside valid range for water [0, 200]"
            raise ValueError(msg)

        # ASHRAE equation 6 (over water)
        ln_pws = (
            SAT_PRESSURE_WATER_C1 / t_k
            + SAT_PRESSURE_WATER_C2
            + SAT_PRESSURE_WATER_C3 * t_k
            + SAT_PRESSURE_WATER_C4 * t_k**2
            + SAT_PRESSURE_WATER_C5 * t_k**3
            + SAT_PRESSURE_WATER_C6 * math.log(t_k)
        )

    return math.exp(ln_pws)


def humidity_ratio(
    t: float,
    rh: float,
    p: float = STANDARD_PRESSURE,
) -> float:
    """Calculate humidity ratio from temperature and relative humidity.

    ASHRAE Handbook-Fundamentals, Chapter 1, Equation 22.

    The humidity ratio W is the mass of water vapor per unit mass of dry air.

    Args:
        t: Dry-bulb temperature in C.
        rh: Relative humidity as percentage (0-100).
        p: Total atmospheric pressure in Pa.

    Returns:
        Humidity ratio in kg_water/kg_dry_air.

    Raises:
        ValueError: If relative humidity is outside [0, 100].

    Examples:
        >>> humidity_ratio(20.0, 50.0)  # 20C, 50% RH
        0.00727...
        >>> humidity_ratio(30.0, 80.0)  # 30C, 80% RH
        0.02162...
    """
    if not 0 <= rh <= 100:
        msg = f"Relative humidity {rh}% must be in [0, 100]"
        raise ValueError(msg)

    # Saturation pressure at temperature
    p_ws = saturation_pressure(t)

    # Partial pressure of water vapor
    p_w = (rh / 100.0) * p_ws

    # Humidity ratio (ASHRAE Eq. 22)
    # W = 0.621945 * p_w / (p - p_w)
    if p - p_w <= 0:
        msg = f"Invalid pressure condition: p={p}, p_w={p_w}"
        raise ValueError(msg)

    return EPSILON * p_w / (p - p_w)


def humidity_ratio_from_wet_bulb(
    t_db: float,
    t_wb: float,
    p: float = STANDARD_PRESSURE,
) -> float:
    """Calculate humidity ratio from dry-bulb and wet-bulb temperatures.

    ASHRAE Handbook-Fundamentals, Chapter 1, Equation 35.

    Args:
        t_db: Dry-bulb temperature in C.
        t_wb: Wet-bulb temperature in C.
        p: Total atmospheric pressure in Pa.

    Returns:
        Humidity ratio in kg_water/kg_dry_air.

    Raises:
        ValueError: If wet-bulb exceeds dry-bulb temperature.
    """
    if t_wb > t_db:
        msg = f"Wet-bulb {t_wb}C cannot exceed dry-bulb {t_db}C"
        raise ValueError(msg)

    # Saturation humidity ratio at wet-bulb temperature
    w_s_wb = humidity_ratio(t_wb, 100.0, p)

    # ASHRAE psychrometric equation (Equation 35)
    # M2 Fix: Using named constants instead of magic numbers
    # For temperatures above 0C (over water):
    #   W = ((2501 - 2.326*t_wb)*W_s - 1.006*(t_db - t_wb)) /
    #       (2501 + 1.86*t_db - 4.186*t_wb)
    if t_wb >= 0:
        numerator = (
            _LATENT_HEAT_0C_KJ - _LATENT_HEAT_COEF_WATER * t_wb
        ) * w_s_wb - _CP_DRY_AIR_KJ * (t_db - t_wb)
        denominator = (
            _LATENT_HEAT_0C_KJ + _CP_WATER_VAPOR_KJ * t_db - _CP_LIQUID_WATER_KJ * t_wb
        )
        w = numerator / denominator
    else:
        # Below freezing (uses ice constants)
        # W = ((2830 - 0.24*t_wb)*W_s - 1.006*(t_db - t_wb)) /
        #     (2830 + 1.86*t_db - 2.1*t_wb)
        numerator = (
            _LATENT_HEAT_SUBLIMATION_0C_KJ - _LATENT_HEAT_COEF_ICE * t_wb
        ) * w_s_wb - _CP_DRY_AIR_KJ * (t_db - t_wb)
        denominator = (
            _LATENT_HEAT_SUBLIMATION_0C_KJ
            + _CP_WATER_VAPOR_KJ * t_db
            - _CP_ICE_KJ * t_wb
        )
        w = numerator / denominator

    return max(0.0, w)


def relative_humidity(
    t: float,
    w: float,
    p: float = STANDARD_PRESSURE,
) -> float:
    """Calculate relative humidity from temperature and humidity ratio.

    Inverse of humidity_ratio function.

    Args:
        t: Dry-bulb temperature in C.
        w: Humidity ratio in kg_water/kg_dry_air.
        p: Total atmospheric pressure in Pa.

    Returns:
        Relative humidity as percentage (0-100).
    """
    # Saturation pressure
    p_ws = saturation_pressure(t)

    # Partial pressure of water vapor from humidity ratio
    p_w = p * w / (EPSILON + w)

    # Relative humidity
    rh = 100.0 * p_w / p_ws

    return min(100.0, max(0.0, rh))


def wet_bulb_temperature(
    t: float,
    rh: float,
    p: float = STANDARD_PRESSURE,
    *,
    tol: float = 0.001,
    max_iter: int = 100,
) -> float:
    """Calculate wet-bulb temperature using iterative method.

    ASHRAE Handbook-Fundamentals, Chapter 1.

    Uses bisection method to find wet-bulb temperature that satisfies
    the psychrometric equation.

    Args:
        t: Dry-bulb temperature in C.
        rh: Relative humidity as percentage (0-100).
        p: Total atmospheric pressure in Pa.
        tol: Convergence tolerance in C.
        max_iter: Maximum iterations for convergence.

    Returns:
        Wet-bulb temperature in C.

    Raises:
        RuntimeError: If iteration fails to converge.
    """
    # Target humidity ratio
    w_target = humidity_ratio(t, rh, p)

    # Wet-bulb is between dew point and dry-bulb
    # Use bisection method with safe lower bound
    # The dew point can be very low at low RH, so we clamp to a reasonable minimum
    t_dew = dew_point(t, rh)
    t_low = max(_WET_BULB_MIN_TEMP, t_dew - 1)  # Start slightly below dew point
    t_high = t

    for _ in range(max_iter):
        t_mid = (t_low + t_high) / 2

        # Calculate humidity ratio at this wet-bulb guess
        w_calc = humidity_ratio_from_wet_bulb(t, t_mid, p)

        # M5 Fix: Use absolute tolerance floor for very dry air conditions
        # When w_target is very small (dry air), the relative tolerance
        # tol * w_target could become too small for meaningful comparison.
        # Using max(tol * w_target, _HUMIDITY_RATIO_MIN_TOL) ensures
        # numerical stability across all humidity conditions.
        effective_tol = max(tol * w_target, _HUMIDITY_RATIO_MIN_TOL)
        if abs(w_calc - w_target) < effective_tol:
            return t_mid

        if w_calc < w_target:
            t_low = t_mid
        else:
            t_high = t_mid

    msg = f"Wet-bulb calculation did not converge after {max_iter} iterations"
    raise RuntimeError(msg)


def dew_point(t: float, rh: float) -> float:
    """Calculate dew point temperature.

    Uses Magnus-Tetens approximation for simplicity.
    ASHRAE Handbook-Fundamentals provides more complex formulations.

    Args:
        t: Dry-bulb temperature in C.
        rh: Relative humidity as percentage (0-100).

    Returns:
        Dew point temperature in C.

    Raises:
        ValueError: If relative humidity is outside valid range.
    """
    if not 0 < rh <= 100:
        if rh == 0:
            return -273.15  # Absolute zero (no moisture)
        msg = f"Relative humidity {rh}% must be in (0, 100]"
        raise ValueError(msg)

    # Magnus-Tetens coefficients
    a = 17.27
    b = 237.7  # C

    # Intermediate calculation
    alpha = (a * t / (b + t)) + math.log(rh / 100.0)

    # Dew point temperature
    t_dp = (b * alpha) / (a - alpha)

    return t_dp


def dew_point_from_humidity_ratio(
    w: float,
    p: float = STANDARD_PRESSURE,
) -> float:
    """Calculate dew point from humidity ratio.

    Args:
        w: Humidity ratio in kg_water/kg_dry_air.
        p: Total atmospheric pressure in Pa.

    Returns:
        Dew point temperature in C.
    """
    # Partial pressure of water vapor
    p_w = p * w / (EPSILON + w)

    # Find temperature where p_ws = p_w using bisection
    t_low = -100.0
    t_high = 100.0

    for _ in range(100):
        t_mid = (t_low + t_high) / 2
        p_ws = saturation_pressure(t_mid)

        if abs(p_ws - p_w) < 0.1:  # 0.1 Pa tolerance
            return t_mid

        if p_ws < p_w:
            t_low = t_mid
        else:
            t_high = t_mid

    return t_mid


def enthalpy(t: float, w: float) -> float:
    """Calculate specific enthalpy of moist air.

    ASHRAE Handbook-Fundamentals, Chapter 1, Equation 32.

    The reference state is dry air at 0C and liquid water at 0C.

    Args:
        t: Dry-bulb temperature in C.
        w: Humidity ratio in kg_water/kg_dry_air.

    Returns:
        Specific enthalpy in kJ/kg_dry_air.

    Examples:
        >>> enthalpy(20.0, 0.0074)  # Typical indoor conditions
        38.8...
        >>> enthalpy(30.0, 0.020)  # Warm, humid conditions
        81.2...
    """
    # ASHRAE Equation 32
    # h = 1.006*t + w*(2501 + 1.86*t)
    # Result in kJ/kg_da
    # M2 Fix: Using named constants
    h = _CP_DRY_AIR_KJ * t + w * (_LATENT_HEAT_0C_KJ + _CP_WATER_VAPOR_KJ * t)
    return h


def air_density(
    t: float,
    w: float,
    p: float = STANDARD_PRESSURE,
) -> float:
    """Calculate density of moist air.

    ASHRAE Handbook-Fundamentals, Chapter 1, Equation 28.

    Args:
        t: Dry-bulb temperature in C.
        w: Humidity ratio in kg_water/kg_dry_air.
        p: Total atmospheric pressure in Pa.

    Returns:
        Density in kg/m3 (of moist air, not dry air).

    Examples:
        >>> air_density(20.0, 0.0074)  # Typical indoor conditions
        1.199...
        >>> air_density(30.0, 0.020)  # Warm, humid conditions
        1.135...
    """
    t_k = celsius_to_kelvin(t)

    # ASHRAE Equation 28 for moist air density
    # rho = p / (R_da * T * (1 + 1.6078 * W))
    #
    # The factor 1.6078 accounts for the difference in molecular weight between
    # dry air and water vapor:
    #   1.6078 = (M_air / M_water) - 1 = (28.966 / 18.015) - 1
    #
    # This correction factor appears because moist air is less dense than dry
    # air at the same temperature and pressure, due to water vapor's lower
    # molecular weight.
    # Reference: ASHRAE Handbook-Fundamentals (2021), Chapter 1, Equation 28
    rho = p / (GAS_CONSTANT_DRY_AIR * t_k * (1 + _MOLECULAR_WEIGHT_RATIO_FACTOR * w))

    return rho


def specific_volume(
    t: float,
    w: float,
    p: float = STANDARD_PRESSURE,
) -> float:
    """Calculate specific volume of moist air.

    ASHRAE Handbook-Fundamentals, Chapter 1, Equation 28.

    Args:
        t: Dry-bulb temperature in C.
        w: Humidity ratio in kg_water/kg_dry_air.
        p: Total atmospheric pressure in Pa.

    Returns:
        Specific volume in m3/kg_dry_air.
    """
    t_k = celsius_to_kelvin(t)

    # ASHRAE Equation 28 (inverted for specific volume)
    # The 1.6078 factor is explained in air_density() - see
    # _MOLECULAR_WEIGHT_RATIO_FACTOR constant definition.
    v = GAS_CONSTANT_DRY_AIR * t_k * (1 + _MOLECULAR_WEIGHT_RATIO_FACTOR * w) / p

    return v


def mixing_ratio_to_humidity_ratio(mixing_ratio: float) -> float:
    """Convert mixing ratio (meteorological) to humidity ratio (HVAC).

    In meteorology, mixing ratio is often in g/kg; in HVAC it's kg/kg.

    Args:
        mixing_ratio: Mixing ratio in g_water/kg_dry_air.

    Returns:
        Humidity ratio in kg_water/kg_dry_air.
    """
    return mixing_ratio / 1000.0


def adiabatic_saturation_temperature(
    t: float,
    rh: float,
    p: float = STANDARD_PRESSURE,
) -> float:
    """Calculate adiabatic saturation temperature.

    For moist air, the adiabatic saturation temperature equals the
    thermodynamic wet-bulb temperature.

    Args:
        t: Dry-bulb temperature in C.
        rh: Relative humidity as percentage (0-100).
        p: Total atmospheric pressure in Pa.

    Returns:
        Adiabatic saturation temperature in C.
    """
    return wet_bulb_temperature(t, rh, p)


def degree_of_saturation(t: float, rh: float, p: float = STANDARD_PRESSURE) -> float:
    """Calculate degree of saturation (mu).

    ASHRAE Handbook-Fundamentals, Chapter 1, Equation 12.

    The degree of saturation is the ratio of humidity ratio to
    the saturation humidity ratio at the same temperature.

    Args:
        t: Dry-bulb temperature in C.
        rh: Relative humidity as percentage (0-100).
        p: Total atmospheric pressure in Pa.

    Returns:
        Degree of saturation (0-1).
    """
    w = humidity_ratio(t, rh, p)
    w_s = humidity_ratio(t, 100.0, p)

    if w_s == 0:
        return 0.0

    return w / w_s


def vapor_pressure(t: float, rh: float) -> float:
    """Calculate partial pressure of water vapor.

    Args:
        t: Dry-bulb temperature in C.
        rh: Relative humidity as percentage (0-100).

    Returns:
        Partial pressure of water vapor in Pa.
    """
    p_ws = saturation_pressure(t)
    return (rh / 100.0) * p_ws


def latent_heat_of_vaporization(t: float) -> float:
    """Calculate latent heat of vaporization as function of temperature.

    Linear approximation valid for 0-100C range.

    Args:
        t: Temperature in C.

    Returns:
        Latent heat of vaporization in J/kg.
    """
    # Linear approximation: h_fg = 2501000 - 2370*t
    return LATENT_HEAT_VAPORIZATION_0C - 2370.0 * t
