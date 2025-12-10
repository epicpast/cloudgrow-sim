"""ASHRAE physical constants for greenhouse calculations.

Reference: ASHRAE Handbook—Fundamentals (2021)

All values use SI units.
"""

from typing import Final

# =============================================================================
# Universal Constants
# =============================================================================

#: Stefan-Boltzmann constant (W/(m²·K⁴))
#: ASHRAE Handbook—Fundamentals, Chapter 4
STEFAN_BOLTZMANN: Final[float] = 5.670374419e-8

#: Universal gas constant (J/(mol·K))
UNIVERSAL_GAS_CONSTANT: Final[float] = 8.314462618

# =============================================================================
# Solar Constants
# =============================================================================

#: Solar constant - extraterrestrial radiation (W/m²)
#: ASHRAE Handbook—Fundamentals, Chapter 14
SOLAR_CONSTANT: Final[float] = 1367.0

#: Earth's orbital eccentricity
EARTH_ECCENTRICITY: Final[float] = 0.01671

#: Earth's axial tilt (degrees)
EARTH_AXIAL_TILT: Final[float] = 23.45

# =============================================================================
# Air Properties
# =============================================================================

#: Specific heat of dry air at constant pressure (J/(kg·K))
#: ASHRAE Handbook—Fundamentals, Chapter 1
C_P_DRY_AIR: Final[float] = 1006.0

#: Specific heat of water vapor at constant pressure (J/(kg·K))
#: ASHRAE Handbook—Fundamentals, Chapter 1
C_P_WATER_VAPOR: Final[float] = 1860.0

#: Gas constant for dry air (J/(kg·K))
#: R_air = R_universal / M_air = 8314.462 / 28.966
GAS_CONSTANT_DRY_AIR: Final[float] = 287.055

#: Gas constant for water vapor (J/(kg·K))
#: R_water = R_universal / M_water = 8314.462 / 18.015
GAS_CONSTANT_WATER_VAPOR: Final[float] = 461.5

#: Molecular weight of dry air (kg/kmol)
MOLECULAR_WEIGHT_DRY_AIR: Final[float] = 28.966

#: Molecular weight of water (kg/kmol)
MOLECULAR_WEIGHT_WATER: Final[float] = 18.015

#: Ratio of molecular weights (dimensionless)
#: Used in humidity calculations
EPSILON: Final[float] = MOLECULAR_WEIGHT_WATER / MOLECULAR_WEIGHT_DRY_AIR  # ≈ 0.62198

# =============================================================================
# Water Properties
# =============================================================================

#: Latent heat of vaporization at 0°C (J/kg)
#: ASHRAE Handbook—Fundamentals, Chapter 1
LATENT_HEAT_VAPORIZATION_0C: Final[float] = 2501000.0

#: Latent heat of vaporization at 20°C (J/kg)
#: More commonly used reference temperature
LATENT_HEAT_VAPORIZATION: Final[float] = 2454000.0

#: Latent heat of sublimation (ice to vapor) at 0°C (J/kg)
LATENT_HEAT_SUBLIMATION: Final[float] = 2834000.0

#: Latent heat of fusion (ice to water) at 0°C (J/kg)
LATENT_HEAT_FUSION: Final[float] = 333000.0

#: Specific heat of liquid water (J/(kg·K))
C_P_WATER: Final[float] = 4186.0

#: Density of water at 20°C (kg/m³)
DENSITY_WATER_20C: Final[float] = 998.2

# =============================================================================
# Standard Conditions
# =============================================================================

#: Standard atmospheric pressure (Pa)
STANDARD_PRESSURE: Final[float] = 101325.0

#: Standard temperature (K) - 15°C
STANDARD_TEMPERATURE_K: Final[float] = 288.15

#: Standard temperature (°C)
STANDARD_TEMPERATURE_C: Final[float] = 15.0

#: Standard air density at 15°C, 101325 Pa (kg/m³)
STANDARD_AIR_DENSITY: Final[float] = 1.225

# =============================================================================
# Saturation Pressure Coefficients (ASHRAE)
# =============================================================================
# Hyland-Wexler correlation coefficients for saturation pressure
# ASHRAE Handbook—Fundamentals, Chapter 1

#: Coefficients for saturation pressure over water (T in K, result in Pa)
#: Valid for 0°C to 200°C
SAT_PRESSURE_WATER_C1: Final[float] = -5.8002206e3
SAT_PRESSURE_WATER_C2: Final[float] = 1.3914993
SAT_PRESSURE_WATER_C3: Final[float] = -4.8640239e-2
SAT_PRESSURE_WATER_C4: Final[float] = 4.1764768e-5
SAT_PRESSURE_WATER_C5: Final[float] = -1.4452093e-8
SAT_PRESSURE_WATER_C6: Final[float] = 6.5459673

#: Coefficients for saturation pressure over ice (T in K, result in Pa)
#: Valid for -100°C to 0°C
SAT_PRESSURE_ICE_C1: Final[float] = -5.6745359e3
SAT_PRESSURE_ICE_C2: Final[float] = 6.3925247
SAT_PRESSURE_ICE_C3: Final[float] = -9.6778430e-3
SAT_PRESSURE_ICE_C4: Final[float] = 6.2215701e-7
SAT_PRESSURE_ICE_C5: Final[float] = 2.0747825e-9
SAT_PRESSURE_ICE_C6: Final[float] = -9.4840240e-13
SAT_PRESSURE_ICE_C7: Final[float] = 4.1635019

# =============================================================================
# Heat Transfer Constants
# =============================================================================

#: Gravitational acceleration (m/s²)
GRAVITY: Final[float] = 9.80665

#: Thermal conductivity of air at 20°C (W/(m·K))
THERMAL_CONDUCTIVITY_AIR: Final[float] = 0.0257

#: Dynamic viscosity of air at 20°C (Pa·s)
DYNAMIC_VISCOSITY_AIR: Final[float] = 1.81e-5

#: Kinematic viscosity of air at 20°C (m²/s)
KINEMATIC_VISCOSITY_AIR: Final[float] = 1.5e-5

#: Prandtl number for air at 20°C (dimensionless)
PRANDTL_AIR: Final[float] = 0.71

#: Thermal diffusivity of air at 20°C (m²/s)
THERMAL_DIFFUSIVITY_AIR: Final[float] = 2.1e-5

# =============================================================================
# Greenhouse-Specific Constants
# =============================================================================

#: Typical ground reflectance (albedo) for various surfaces
ALBEDO_GRASS: Final[float] = 0.25
ALBEDO_SOIL_DRY: Final[float] = 0.20
ALBEDO_SOIL_WET: Final[float] = 0.10
ALBEDO_CONCRETE: Final[float] = 0.30
ALBEDO_SNOW: Final[float] = 0.80

#: PAR fraction of solar radiation (dimensionless)
#: Approximately 45% of solar radiation is photosynthetically active
PAR_FRACTION: Final[float] = 0.45

#: Conversion from W/m² to µmol/(m²·s) for PAR
#: Approximately 4.57 µmol/J for sunlight
PAR_CONVERSION_FACTOR: Final[float] = 4.57

#: Typical CO2 concentration in ambient air (ppm)
AMBIENT_CO2_PPM: Final[float] = 420.0

# =============================================================================
# Temperature Conversions
# =============================================================================


def celsius_to_kelvin(t_celsius: float) -> float:
    """Convert temperature from Celsius to Kelvin.

    Args:
        t_celsius: Temperature in degrees Celsius.

    Returns:
        Temperature in Kelvin.
    """
    return t_celsius + 273.15


def kelvin_to_celsius(t_kelvin: float) -> float:
    """Convert temperature from Kelvin to Celsius.

    Args:
        t_kelvin: Temperature in Kelvin.

    Returns:
        Temperature in degrees Celsius.
    """
    return t_kelvin - 273.15
