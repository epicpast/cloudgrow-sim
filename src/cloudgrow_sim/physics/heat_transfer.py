"""Heat transfer calculations following ASHRAE standards.

Reference: ASHRAE Handbook—Fundamentals (2021), Chapters 4, 25, 26

This module implements heat transfer calculations for greenhouses:
- Conduction through covering materials
- Natural and forced convection
- Radiation exchange (Stefan-Boltzmann)
- Sky temperature estimation
- Ground temperature models

All functions use SI units.
"""

from __future__ import annotations

import math

from cloudgrow_sim.physics.constants import (
    GRAVITY,
    KINEMATIC_VISCOSITY_AIR,
    PRANDTL_AIR,
    STEFAN_BOLTZMANN,
    THERMAL_CONDUCTIVITY_AIR,
    celsius_to_kelvin,
)

# =============================================================================
# Conduction
# =============================================================================


def conduction_heat_transfer(
    u_value: float,
    area: float,
    t_inside: float,
    t_outside: float,
) -> float:
    """Calculate steady-state conduction heat transfer.

    Q = U * A * ΔT

    Args:
        u_value: Overall heat transfer coefficient in W/(m²·K).
        area: Heat transfer area in m².
        t_inside: Inside temperature in °C.
        t_outside: Outside temperature in °C.

    Returns:
        Heat transfer rate in W (positive = heat loss from inside).

    Examples:
        >>> conduction_heat_transfer(4.0, 100.0, 20.0, 5.0)  # 15K difference
        6000.0
    """
    return u_value * area * (t_inside - t_outside)


def conduction_resistance(thickness: float, conductivity: float) -> float:
    """Calculate conduction thermal resistance.

    R = L / k

    Args:
        thickness: Material thickness in m.
        conductivity: Thermal conductivity in W/(m·K).

    Returns:
        Thermal resistance in (m²·K)/W.
    """
    if conductivity <= 0:
        msg = f"Conductivity must be positive, got {conductivity}"
        raise ValueError(msg)
    return thickness / conductivity


def overall_u_value(
    resistances: list[float],
    h_inside: float = 8.3,
    h_outside: float = 23.0,
) -> float:
    """Calculate overall U-value from layer resistances.

    U = 1 / (R_si + ΣR + R_so)

    Args:
        resistances: List of layer thermal resistances in (m²·K)/W.
        h_inside: Inside surface heat transfer coefficient in W/(m²·K).
        h_outside: Outside surface heat transfer coefficient in W/(m²·K).

    Returns:
        Overall U-value in W/(m²·K).
    """
    r_si = 1.0 / h_inside
    r_so = 1.0 / h_outside
    r_total = r_si + sum(resistances) + r_so
    return 1.0 / r_total


# =============================================================================
# Convection
# =============================================================================


def grashof_number(
    t_surface: float,
    t_fluid: float,
    length: float,
    *,
    nu: float = KINEMATIC_VISCOSITY_AIR,
) -> float:
    """Calculate Grashof number for natural convection.

    Gr = g * β * ΔT * L³ / ν²

    Args:
        t_surface: Surface temperature in °C.
        t_fluid: Fluid (air) temperature in °C.
        length: Characteristic length in m.
        nu: Kinematic viscosity in m²/s.

    Returns:
        Grashof number (dimensionless).
    """
    t_film = (t_surface + t_fluid) / 2.0
    t_film_k = celsius_to_kelvin(t_film)

    # Volumetric thermal expansion coefficient for ideal gas
    beta = 1.0 / t_film_k

    delta_t = abs(t_surface - t_fluid)

    return GRAVITY * beta * delta_t * length**3 / nu**2


def rayleigh_number(
    t_surface: float,
    t_fluid: float,
    length: float,
    *,
    nu: float = KINEMATIC_VISCOSITY_AIR,
    pr: float = PRANDTL_AIR,
) -> float:
    """Calculate Rayleigh number for natural convection.

    Ra = Gr * Pr

    Args:
        t_surface: Surface temperature in °C.
        t_fluid: Fluid (air) temperature in °C.
        length: Characteristic length in m.
        nu: Kinematic viscosity in m²/s.
        pr: Prandtl number.

    Returns:
        Rayleigh number (dimensionless).
    """
    gr = grashof_number(t_surface, t_fluid, length, nu=nu)
    return gr * pr


def reynolds_number(
    velocity: float,
    length: float,
    *,
    nu: float = KINEMATIC_VISCOSITY_AIR,
) -> float:
    """Calculate Reynolds number for forced convection.

    Re = V * L / ν

    Args:
        velocity: Flow velocity in m/s.
        length: Characteristic length in m.
        nu: Kinematic viscosity in m²/s.

    Returns:
        Reynolds number (dimensionless).
    """
    return velocity * length / nu


def convection_coefficient_natural(
    t_surface: float,
    t_fluid: float,
    length: float,
    *,
    orientation: str = "vertical",
) -> float:
    """Calculate natural convection heat transfer coefficient.

    Uses correlations from ASHRAE Handbook—Fundamentals, Chapter 4.

    Args:
        t_surface: Surface temperature in °C.
        t_fluid: Fluid (air) temperature in °C.
        length: Characteristic length in m.
        orientation: Surface orientation ("vertical", "horizontal_up", "horizontal_down").

    Returns:
        Convection coefficient h in W/(m²·K).
    """
    ra = rayleigh_number(t_surface, t_fluid, length)

    if ra < 1:
        # Very small Ra, use minimum value
        return 0.5

    # Nusselt number correlations
    if orientation == "vertical":
        # Vertical plate correlation (Churchill-Chu)
        if ra < 1e9:
            # Laminar
            nu_num = 0.68 + 0.67 * ra**0.25 / (
                1 + (0.492 / PRANDTL_AIR) ** (9 / 16)
            ) ** (4 / 9)
        else:
            # Turbulent
            nu_num = (
                0.825
                + 0.387
                * ra ** (1 / 6)
                / (1 + (0.492 / PRANDTL_AIR) ** (9 / 16)) ** (8 / 27)
            ) ** 2

    elif orientation == "horizontal_up":
        # Hot surface facing up or cold surface facing down
        nu_num = 0.54 * ra**0.25 if ra < 1e7 else 0.15 * ra ** (1 / 3)

    elif orientation == "horizontal_down":
        # Hot surface facing down or cold surface facing up
        nu_num = 0.27 * ra**0.25

    else:
        msg = f"Unknown orientation: {orientation}"
        raise ValueError(msg)

    # Heat transfer coefficient
    h = nu_num * THERMAL_CONDUCTIVITY_AIR / length

    return float(max(0.5, h))  # Minimum practical value


def convection_coefficient_forced(
    velocity: float,
    length: float,
    *,
    geometry: str = "flat_plate",
) -> float:
    """Calculate forced convection heat transfer coefficient.

    Uses correlations from ASHRAE Handbook—Fundamentals, Chapter 4.

    Args:
        velocity: Air velocity in m/s.
        length: Characteristic length in m.
        geometry: Surface geometry ("flat_plate", "cylinder").

    Returns:
        Convection coefficient h in W/(m²·K).
    """
    if velocity <= 0:
        return 0.5  # Minimum value for still air

    re = reynolds_number(velocity, length)

    if geometry == "flat_plate":
        # Flat plate correlation
        if re < 5e5:
            # Laminar
            nu_num = 0.664 * re**0.5 * PRANDTL_AIR ** (1 / 3)
        else:
            # Turbulent (mixed)
            nu_num = (0.037 * re**0.8 - 871) * PRANDTL_AIR ** (1 / 3)

    elif geometry == "cylinder":
        # Cylinder in crossflow (Churchill-Bernstein)
        nu_num = (
            0.3
            + 0.62
            * re**0.5
            * PRANDTL_AIR ** (1 / 3)
            / (1 + (0.4 / PRANDTL_AIR) ** (2 / 3)) ** 0.25
            * (1 + (re / 282000) ** (5 / 8)) ** 0.8
        )

    else:
        msg = f"Unknown geometry: {geometry}"
        raise ValueError(msg)

    # Heat transfer coefficient
    h = nu_num * THERMAL_CONDUCTIVITY_AIR / length

    return float(max(0.5, h))


def convection_coefficient_mixed(
    h_natural: float,
    h_forced: float,
    n: float = 3.0,
) -> float:
    """Combine natural and forced convection using Churchill-Usagi correlation.

    h_mixed = (h_natural^n + h_forced^n)^(1/n)

    Args:
        h_natural: Natural convection coefficient in W/(m²·K).
        h_forced: Forced convection coefficient in W/(m²·K).
        n: Combination exponent (typically 3-4).

    Returns:
        Combined convection coefficient in W/(m²·K).
    """
    return float((h_natural**n + h_forced**n) ** (1.0 / n))


# =============================================================================
# Radiation
# =============================================================================


def radiation_heat_transfer(
    emissivity: float,
    area: float,
    t_surface: float,
    t_surroundings: float,
) -> float:
    """Calculate radiation heat transfer using Stefan-Boltzmann law.

    Q = ε * σ * A * (T_s⁴ - T_surr⁴)

    Args:
        emissivity: Surface emissivity (0-1).
        area: Surface area in m².
        t_surface: Surface temperature in °C.
        t_surroundings: Surroundings temperature in °C.

    Returns:
        Heat transfer rate in W (positive = heat loss from surface).

    Examples:
        >>> radiation_heat_transfer(0.9, 100.0, 20.0, -10.0)
        1697.5...
    """
    t_s_k = celsius_to_kelvin(t_surface)
    t_surr_k = celsius_to_kelvin(t_surroundings)

    return emissivity * STEFAN_BOLTZMANN * area * (t_s_k**4 - t_surr_k**4)


def radiation_coefficient(
    emissivity: float,
    t_surface: float,
    t_surroundings: float,
) -> float:
    """Calculate linearized radiation heat transfer coefficient.

    h_r = ε * σ * (T_s² + T_surr²) * (T_s + T_surr)

    This allows radiation to be treated as a convection-like process
    with Q = h_r * A * (T_s - T_surr).

    Args:
        emissivity: Surface emissivity (0-1).
        t_surface: Surface temperature in °C.
        t_surroundings: Surroundings temperature in °C.

    Returns:
        Radiation coefficient h_r in W/(m²·K).
    """
    t_s_k = celsius_to_kelvin(t_surface)
    t_surr_k = celsius_to_kelvin(t_surroundings)

    return emissivity * STEFAN_BOLTZMANN * (t_s_k**2 + t_surr_k**2) * (t_s_k + t_surr_k)


def sky_temperature(
    t_ambient: float,
    rh: float = 50.0,
    *,
    cloud_cover: float = 0.0,
) -> float:
    """Estimate effective sky temperature for radiation calculations.

    Uses Berdahl-Fromberg correlation.

    The sky temperature is lower than ambient due to the atmosphere's
    transparency in the infrared "window" (8-13 μm).

    Args:
        t_ambient: Ambient air temperature in °C.
        rh: Relative humidity as percentage (0-100).
        cloud_cover: Cloud cover fraction (0-1).

    Returns:
        Effective sky temperature in °C.

    Examples:
        >>> sky_temperature(20.0, 50.0)  # Clear night
        2.5...  # Significantly below ambient
        >>> sky_temperature(20.0, 50.0, cloud_cover=1.0)  # Overcast
        17.5...  # Close to ambient
    """
    t_k = celsius_to_kelvin(t_ambient)

    # Dew point temperature (simplified)
    from cloudgrow_sim.physics.psychrometrics import dew_point as calc_dew_point

    t_dp = calc_dew_point(t_ambient, rh)

    # Clear sky emissivity (Berdahl-Fromberg)
    # Note: This correlation uses dew point in °C, not Kelvin
    epsilon_clear = 0.741 + 0.0062 * t_dp

    # Clamp to valid range (emissivity must be 0-1)
    epsilon_clear = max(0.0, min(1.0, epsilon_clear))

    # Cloud correction
    epsilon_sky = epsilon_clear + cloud_cover * (1.0 - epsilon_clear)

    # Effective sky temperature
    t_sky_k = t_k * float(epsilon_sky**0.25)

    return t_sky_k - 273.15


def view_factor_horizontal_to_sky() -> float:
    """View factor from horizontal surface to sky hemisphere.

    For a horizontal surface, F_sky = 1.0.

    Returns:
        View factor (dimensionless).
    """
    return 1.0


def view_factor_vertical_to_sky() -> float:
    """View factor from vertical surface to sky hemisphere.

    For a vertical surface, F_sky ≈ 0.5.

    Returns:
        View factor (dimensionless).
    """
    return 0.5


def view_factor_tilted_to_sky(tilt: float) -> float:
    """View factor from tilted surface to sky hemisphere.

    F_sky = (1 + cos(tilt)) / 2

    Args:
        tilt: Surface tilt from horizontal in degrees.

    Returns:
        View factor (dimensionless).
    """
    return (1.0 + math.cos(math.radians(tilt))) / 2.0


# =============================================================================
# Ground Temperature
# =============================================================================


def ground_temperature_at_depth(
    t_mean_annual: float,
    t_amplitude: float,
    day: int,
    depth: float,
    *,
    day_of_minimum: int = 35,
    thermal_diffusivity: float = 0.5e-6,
) -> float:
    """Calculate ground temperature at depth using sinusoidal model.

    ASHRAE Handbook—Fundamentals, Chapter 18.

    T(d,t) = T_mean - A * exp(-d*√(π/365α)) * cos(2π(t-t_0)/365 - d*√(π/365α))

    Args:
        t_mean_annual: Mean annual surface temperature in °C.
        t_amplitude: Annual surface temperature amplitude in °C.
        day: Day of year (1-366).
        depth: Depth below surface in m.
        day_of_minimum: Day of year when surface temperature is minimum.
        thermal_diffusivity: Soil thermal diffusivity in m²/s.

    Returns:
        Ground temperature at depth in °C.

    Examples:
        >>> ground_temperature_at_depth(15.0, 10.0, 180, 2.0)  # 2m deep, mid-year
        15.2...  # Nearly constant at depth
    """
    # Convert thermal diffusivity to m²/day
    alpha_day = thermal_diffusivity * 86400

    # Damping depth
    d_0 = math.sqrt(365 * alpha_day / math.pi)

    # Damping factor
    damping = math.exp(-depth / d_0)

    # Phase shift
    phase = depth / d_0

    # Temperature
    t = t_mean_annual - t_amplitude * damping * math.cos(
        2 * math.pi * (day - day_of_minimum) / 365 - phase
    )

    return t


def ground_temperature_surface(
    t_mean_annual: float,
    t_amplitude: float,
    day: int,
    *,
    day_of_minimum: int = 35,
) -> float:
    """Calculate ground surface temperature.

    Simplified sinusoidal model.

    Args:
        t_mean_annual: Mean annual temperature in °C.
        t_amplitude: Annual temperature amplitude in °C.
        day: Day of year (1-366).
        day_of_minimum: Day of year when temperature is minimum.

    Returns:
        Ground surface temperature in °C.
    """
    return t_mean_annual - t_amplitude * math.cos(
        2 * math.pi * (day - day_of_minimum) / 365
    )


# =============================================================================
# Combined Heat Transfer
# =============================================================================


def surface_heat_balance(
    q_solar: float,
    q_convection: float,
    q_radiation: float,
    q_conduction: float,
) -> float:
    """Calculate net heat flux at a surface.

    Args:
        q_solar: Solar heat gain in W (positive into surface).
        q_convection: Convective heat transfer in W (positive = loss).
        q_radiation: Radiative heat transfer in W (positive = loss).
        q_conduction: Conductive heat transfer in W (positive = loss).

    Returns:
        Net heat flux in W (positive = net gain).
    """
    return q_solar - q_convection - q_radiation - q_conduction
