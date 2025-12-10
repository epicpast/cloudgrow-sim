"""Ventilation and infiltration calculations following ASHRAE standards.

Reference: ASHRAE Handbook—Fundamentals (2021), Chapter 26

This module implements calculations for:
- Infiltration rates
- Natural ventilation (stack and wind effects)
- Mechanical ventilation
- Heat and moisture exchange from air movement

All functions use SI units.
"""

from __future__ import annotations

import math

from cloudgrow_sim.physics.constants import (
    C_P_DRY_AIR,
    GRAVITY,
    celsius_to_kelvin,
)
from cloudgrow_sim.physics.psychrometrics import (
    air_density,
    humidity_ratio,
    latent_heat_of_vaporization,
)

# =============================================================================
# Infiltration
# =============================================================================


def infiltration_rate(
    volume: float,
    ach: float,
) -> float:
    """Calculate infiltration air flow rate from air changes per hour.

    Args:
        volume: Space volume in m³.
        ach: Air changes per hour (1/h).

    Returns:
        Volumetric flow rate in m³/s.

    Examples:
        >>> infiltration_rate(1000.0, 0.5)  # 1000 m³, 0.5 ACH
        0.1388...
    """
    return volume * ach / 3600.0


def infiltration_ach_greenhouse(
    wind_speed: float,
    delta_t: float,
    *,
    construction_quality: str = "average",
) -> float:
    """Estimate greenhouse infiltration rate in air changes per hour.

    Based on empirical correlations for greenhouse structures.

    Args:
        wind_speed: Wind speed in m/s.
        delta_t: Inside-outside temperature difference in K.
        construction_quality: "tight", "average", or "loose".

    Returns:
        Estimated air changes per hour.
    """
    # Base coefficients for different construction quality
    coefficients = {
        "tight": (0.1, 0.01, 0.005),
        "average": (0.3, 0.02, 0.01),
        "loose": (0.6, 0.04, 0.02),
    }

    if construction_quality not in coefficients:
        msg = f"Unknown construction quality: {construction_quality}"
        raise ValueError(msg)

    c_base, c_wind, c_stack = coefficients[construction_quality]

    # Combined infiltration model
    # ACH = c_base + c_wind * V + c_stack * √|ΔT|
    ach = c_base + c_wind * wind_speed + c_stack * math.sqrt(abs(delta_t))

    return ach


# =============================================================================
# Natural Ventilation
# =============================================================================


def stack_effect_pressure(
    height: float,
    t_inside: float,
    t_outside: float,
) -> float:
    """Calculate stack effect pressure difference.

    ΔP = ρ_o * g * h * (T_i - T_o) / T_i

    Args:
        height: Height of neutral pressure level in m.
        t_inside: Inside temperature in °C.
        t_outside: Outside temperature in °C.

    Returns:
        Pressure difference in Pa.
    """
    t_i_k = celsius_to_kelvin(t_inside)
    t_o_k = celsius_to_kelvin(t_outside)

    # Outside air density at standard conditions
    rho_o = air_density(t_outside, 0.0)

    # Stack pressure
    delta_p = rho_o * GRAVITY * height * (t_i_k - t_o_k) / t_i_k

    return delta_p


def stack_effect_flow(
    opening_area: float,
    height: float,
    t_inside: float,
    t_outside: float,
    *,
    discharge_coefficient: float = 0.65,
) -> float:
    """Calculate air flow rate due to stack effect.

    Args:
        opening_area: Effective opening area in m².
        height: Height difference between openings in m.
        t_inside: Inside temperature in °C.
        t_outside: Outside temperature in °C.
        discharge_coefficient: Opening discharge coefficient.

    Returns:
        Volumetric flow rate in m³/s.
    """
    t_i_k = celsius_to_kelvin(t_inside)

    # Stack effect flow (ASHRAE)
    delta_t = abs(t_inside - t_outside)

    if delta_t < 0.1:
        return 0.0

    q = (
        discharge_coefficient
        * opening_area
        * math.sqrt(2 * GRAVITY * height * delta_t / t_i_k)
    )

    return q


def wind_driven_flow(
    opening_area: float,
    wind_speed: float,
    *,
    pressure_coefficient: float = 0.6,
    discharge_coefficient: float = 0.65,
) -> float:
    """Calculate air flow rate due to wind.

    Args:
        opening_area: Effective opening area in m².
        wind_speed: Wind speed in m/s.
        pressure_coefficient: Wind pressure coefficient.
        discharge_coefficient: Opening discharge coefficient.

    Returns:
        Volumetric flow rate in m³/s.
    """
    if wind_speed <= 0:
        return 0.0

    # Wind-driven flow
    # Q = C_d * A * V * √C_p
    q = (
        discharge_coefficient
        * opening_area
        * wind_speed
        * math.sqrt(abs(pressure_coefficient))
    )

    return q


def combined_natural_ventilation(
    opening_area: float,
    height: float,
    t_inside: float,
    t_outside: float,
    wind_speed: float,
    *,
    discharge_coefficient: float = 0.65,
    pressure_coefficient: float = 0.6,
) -> float:
    """Calculate combined stack and wind natural ventilation.

    Uses superposition of flows.

    Args:
        opening_area: Effective opening area in m².
        height: Height difference between openings in m.
        t_inside: Inside temperature in °C.
        t_outside: Outside temperature in °C.
        wind_speed: Wind speed in m/s.
        discharge_coefficient: Opening discharge coefficient.
        pressure_coefficient: Wind pressure coefficient.

    Returns:
        Volumetric flow rate in m³/s.
    """
    q_stack = stack_effect_flow(
        opening_area,
        height,
        t_inside,
        t_outside,
        discharge_coefficient=discharge_coefficient,
    )

    q_wind = wind_driven_flow(
        opening_area,
        wind_speed,
        pressure_coefficient=pressure_coefficient,
        discharge_coefficient=discharge_coefficient,
    )

    # Combine using quadrature (ASHRAE recommendation)
    return math.sqrt(q_stack**2 + q_wind**2)


def vent_opening_area(
    vent_width: float,
    vent_height: float,
    opening_fraction: float,
) -> float:
    """Calculate effective vent opening area.

    Args:
        vent_width: Vent width in m.
        vent_height: Vent height in m.
        opening_fraction: Vent opening fraction (0-1).

    Returns:
        Effective opening area in m².
    """
    return vent_width * vent_height * opening_fraction


# =============================================================================
# Mechanical Ventilation
# =============================================================================


def fan_flow_rate(
    fan_capacity: float,
    num_fans: int,
    speed_fraction: float = 1.0,
) -> float:
    """Calculate total fan flow rate.

    Args:
        fan_capacity: Single fan capacity in m³/s.
        num_fans: Number of fans.
        speed_fraction: Fan speed as fraction of full speed (0-1).

    Returns:
        Total volumetric flow rate in m³/s.
    """
    return fan_capacity * num_fans * speed_fraction


def fan_power(
    flow_rate: float,
    pressure_rise: float,
    efficiency: float = 0.6,
) -> float:
    """Calculate fan power consumption.

    P = Q * ΔP / η

    Args:
        flow_rate: Volumetric flow rate in m³/s.
        pressure_rise: Static pressure rise in Pa.
        efficiency: Fan efficiency (0-1).

    Returns:
        Fan power in W.
    """
    if efficiency <= 0:
        msg = f"Efficiency must be positive, got {efficiency}"
        raise ValueError(msg)
    return flow_rate * pressure_rise / efficiency


# =============================================================================
# Heat and Moisture Exchange
# =============================================================================


def sensible_heat_ventilation(
    flow_rate: float,
    t_supply: float,
    t_exhaust: float,
    rh_avg: float = 50.0,
) -> float:
    """Calculate sensible heat exchange from ventilation.

    Q_s = ṁ * c_p * ΔT

    Args:
        flow_rate: Volumetric air flow rate in m³/s.
        t_supply: Supply (incoming) air temperature in °C.
        t_exhaust: Exhaust (outgoing) air temperature in °C.
        rh_avg: Average relative humidity for density calculation.

    Returns:
        Sensible heat rate in W (positive = cooling, negative = heating).
    """
    # Air density at average temperature
    t_avg = (t_supply + t_exhaust) / 2.0
    w = humidity_ratio(t_avg, rh_avg)
    rho = air_density(t_avg, w)

    # Mass flow rate
    m_dot = rho * flow_rate

    # Sensible heat
    q_s = m_dot * C_P_DRY_AIR * (t_supply - t_exhaust)

    return q_s


def latent_heat_ventilation(
    flow_rate: float,
    t_supply: float,
    t_exhaust: float,
    rh_supply: float,
    rh_exhaust: float,
) -> float:
    """Calculate latent heat exchange from ventilation.

    Q_l = ṁ * h_fg * Δw

    Args:
        flow_rate: Volumetric air flow rate in m³/s.
        t_supply: Supply air temperature in °C.
        t_exhaust: Exhaust air temperature in °C.
        rh_supply: Supply air relative humidity (0-100).
        rh_exhaust: Exhaust air relative humidity (0-100).

    Returns:
        Latent heat rate in W (positive = dehumidification).
    """
    # Humidity ratios
    w_supply = humidity_ratio(t_supply, rh_supply)
    w_exhaust = humidity_ratio(t_exhaust, rh_exhaust)

    # Air density at average conditions
    t_avg = (t_supply + t_exhaust) / 2.0
    w_avg = (w_supply + w_exhaust) / 2.0
    rho = air_density(t_avg, w_avg)

    # Mass flow rate
    m_dot = rho * flow_rate

    # Latent heat of vaporization
    h_fg = latent_heat_of_vaporization(t_avg)

    # Latent heat
    q_l = m_dot * h_fg * (w_supply - w_exhaust)

    return q_l


def ventilation_latent_heat(
    flow_rate: float,
    w_supply: float,
    w_exhaust: float,
    t_avg: float = 20.0,
) -> float:
    """Calculate latent heat exchange from humidity ratio difference.

    Args:
        flow_rate: Volumetric air flow rate in m³/s.
        w_supply: Supply air humidity ratio kg/kg.
        w_exhaust: Exhaust air humidity ratio kg/kg.
        t_avg: Average air temperature in °C.

    Returns:
        Latent heat rate in W.
    """
    rho = air_density(t_avg, (w_supply + w_exhaust) / 2.0)
    m_dot = rho * flow_rate
    h_fg = latent_heat_of_vaporization(t_avg)

    return m_dot * h_fg * (w_supply - w_exhaust)


def total_heat_ventilation(
    flow_rate: float,
    t_supply: float,
    t_exhaust: float,
    rh_supply: float,
    rh_exhaust: float,
) -> float:
    """Calculate total (sensible + latent) heat exchange from ventilation.

    Args:
        flow_rate: Volumetric air flow rate in m³/s.
        t_supply: Supply air temperature in °C.
        t_exhaust: Exhaust air temperature in °C.
        rh_supply: Supply air relative humidity (0-100).
        rh_exhaust: Exhaust air relative humidity (0-100).

    Returns:
        Total heat rate in W.
    """
    q_s = sensible_heat_ventilation(flow_rate, t_supply, t_exhaust)
    q_l = latent_heat_ventilation(flow_rate, t_supply, t_exhaust, rh_supply, rh_exhaust)

    return q_s + q_l


def moisture_removal_rate(
    flow_rate: float,
    w_supply: float,
    w_exhaust: float,
    t_avg: float = 20.0,
) -> float:
    """Calculate moisture removal rate from ventilation.

    Args:
        flow_rate: Volumetric air flow rate in m³/s.
        w_supply: Supply air humidity ratio kg/kg.
        w_exhaust: Exhaust air humidity ratio kg/kg.
        t_avg: Average air temperature in °C.

    Returns:
        Moisture removal rate in kg/s (positive = dehumidification).
    """
    rho = air_density(t_avg, (w_supply + w_exhaust) / 2.0)
    m_dot = rho * flow_rate

    return m_dot * (w_exhaust - w_supply)


# =============================================================================
# Ventilation Requirements
# =============================================================================


def required_ventilation_cooling(
    heat_gain: float,
    t_inside: float,
    t_outside: float,
    rh_avg: float = 50.0,
) -> float:
    """Calculate required ventilation rate for sensible cooling.

    Args:
        heat_gain: Total heat gain to be removed in W.
        t_inside: Desired inside temperature in °C.
        t_outside: Outside air temperature in °C.
        rh_avg: Average relative humidity for density.

    Returns:
        Required volumetric flow rate in m³/s.

    Raises:
        ValueError: If outside temperature >= inside temperature.
    """
    delta_t = t_inside - t_outside

    if delta_t <= 0:
        msg = "Outside temperature must be lower than inside for cooling"
        raise ValueError(msg)

    # Air density
    t_avg = (t_inside + t_outside) / 2.0
    w = humidity_ratio(t_avg, rh_avg)
    rho = air_density(t_avg, w)

    # Required flow rate
    # Q = q / (ρ * c_p * ΔT)
    return heat_gain / (rho * C_P_DRY_AIR * delta_t)


def required_ach_humidity_control(
    moisture_generation: float,
    volume: float,
    w_inside: float,
    w_outside: float,
    t_avg: float = 20.0,
) -> float:
    """Calculate required air changes for humidity control.

    Args:
        moisture_generation: Interior moisture generation in kg/s.
        volume: Space volume in m³.
        w_inside: Desired inside humidity ratio kg/kg.
        w_outside: Outside humidity ratio kg/kg.
        t_avg: Average temperature in °C.

    Returns:
        Required air changes per hour.

    Raises:
        ValueError: If outside humidity >= inside humidity.
    """
    delta_w = w_inside - w_outside

    if delta_w <= 0:
        msg = "Outside humidity must be lower than inside for dehumidification"
        raise ValueError(msg)

    rho = air_density(t_avg, (w_inside + w_outside) / 2.0)

    # Required flow rate
    q = moisture_generation / (rho * delta_w)

    # Convert to ACH
    return q * 3600.0 / volume
