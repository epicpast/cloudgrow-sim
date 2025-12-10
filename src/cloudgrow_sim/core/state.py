"""State management for greenhouse simulation.

This module defines the data structures that represent the complete state
of the greenhouse environment at any point in time:

- AirState: Temperature, humidity, pressure, CO2 for air masses
- Location: Geographic coordinates and timezone
- GreenhouseGeometry: Physical dimensions and shape
- CoveringProperties: Optical and thermal properties of covering material
- GreenhouseState: Complete simulation state
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum


class GeometryType(str, Enum):
    """Supported greenhouse geometry types."""

    GABLE = "gable"
    QUONSET = "quonset"
    GOTHIC = "gothic"
    VENLO = "venlo"
    HIGH_TUNNEL = "high_tunnel"
    CUSTOM = "custom"


@dataclass
class AirState:
    """Thermodynamic state of an air mass.

    Represents the psychrometric properties of air at a specific location.
    All units follow SI conventions.

    Attributes:
        temperature: Dry-bulb temperature in °C.
        humidity: Relative humidity as percentage (0-100).
        pressure: Atmospheric pressure in Pa.
        co2_ppm: CO2 concentration in parts per million.
    """

    temperature: float = 20.0
    humidity: float = 50.0
    pressure: float = 101325.0
    co2_ppm: float = 400.0

    def __post_init__(self) -> None:
        """Validate air state values."""
        if not -50 <= self.temperature <= 60:
            msg = f"Temperature {self.temperature}°C outside valid range [-50, 60]"
            raise ValueError(msg)
        if not 0 <= self.humidity <= 100:
            msg = f"Humidity {self.humidity}% outside valid range [0, 100]"
            raise ValueError(msg)
        if not 80000 <= self.pressure <= 120000:
            msg = f"Pressure {self.pressure} Pa outside valid range [80000, 120000]"
            raise ValueError(msg)
        if not 0 <= self.co2_ppm <= 5000:
            msg = f"CO2 {self.co2_ppm} ppm outside valid range [0, 5000]"
            raise ValueError(msg)

    def copy(self) -> AirState:
        """Create a copy of this air state."""
        return AirState(
            temperature=self.temperature,
            humidity=self.humidity,
            pressure=self.pressure,
            co2_ppm=self.co2_ppm,
        )


@dataclass
class Location:
    """Geographic location for solar calculations.

    Attributes:
        latitude: Latitude in degrees (-90 to 90, positive = North).
        longitude: Longitude in degrees (-180 to 180, positive = East).
        elevation: Elevation above sea level in meters.
        timezone_str: IANA timezone string (e.g., "America/New_York").
    """

    latitude: float
    longitude: float
    elevation: float = 0.0
    timezone_str: str = "UTC"

    def __post_init__(self) -> None:
        """Validate location values."""
        if not -90 <= self.latitude <= 90:
            msg = f"Latitude {self.latitude}° outside valid range [-90, 90]"
            raise ValueError(msg)
        if not -180 <= self.longitude <= 180:
            msg = f"Longitude {self.longitude}° outside valid range [-180, 180]"
            raise ValueError(msg)
        if not -500 <= self.elevation <= 9000:
            msg = f"Elevation {self.elevation}m outside valid range [-500, 9000]"
            raise ValueError(msg)


@dataclass
class GreenhouseGeometry:
    """Physical dimensions and shape of the greenhouse.

    Attributes:
        geometry_type: Type of greenhouse structure.
        length: Length in meters (typically N-S orientation).
        width: Width in meters (typically E-W orientation).
        height_ridge: Height at ridge/peak in meters.
        height_eave: Height at eave/sidewall in meters.
        orientation: Orientation angle in degrees from North (0-360).
    """

    geometry_type: GeometryType = GeometryType.GABLE
    length: float = 30.0
    width: float = 10.0
    height_ridge: float = 5.0
    height_eave: float = 3.0
    orientation: float = 0.0

    def __post_init__(self) -> None:
        """Validate geometry values."""
        if self.length <= 0:
            msg = f"Length must be positive, got {self.length}"
            raise ValueError(msg)
        if self.width <= 0:
            msg = f"Width must be positive, got {self.width}"
            raise ValueError(msg)
        if self.height_ridge <= 0:
            msg = f"Ridge height must be positive, got {self.height_ridge}"
            raise ValueError(msg)
        if self.height_eave <= 0:
            msg = f"Eave height must be positive, got {self.height_eave}"
            raise ValueError(msg)
        if self.height_eave > self.height_ridge:
            msg = f"Eave height {self.height_eave} cannot exceed ridge {self.height_ridge}"
            raise ValueError(msg)

    @property
    def floor_area(self) -> float:
        """Floor area in m²."""
        return self.length * self.width

    @property
    def volume(self) -> float:
        """Approximate interior volume in m³.

        Uses trapezoidal approximation for gable roofs.
        """
        avg_height = (self.height_eave + self.height_ridge) / 2
        return self.length * self.width * avg_height

    @property
    def wall_area(self) -> float:
        """Total exterior wall area in m² (excluding floor and roof).

        Includes end walls and sidewalls.
        """
        # Sidewalls (rectangular)
        sidewall_area = 2 * self.length * self.height_eave

        # End walls (trapezoidal for gable)
        end_wall_rect = self.width * self.height_eave
        end_wall_triangle = 0.5 * self.width * (self.height_ridge - self.height_eave)
        end_wall_area = 2 * (end_wall_rect + end_wall_triangle)

        return sidewall_area + end_wall_area

    @property
    def roof_area(self) -> float:
        """Total roof area in m².

        Accounts for roof slope.
        """
        # Calculate roof slope length
        half_width = self.width / 2
        roof_rise = self.height_ridge - self.height_eave
        slope_length = float((half_width**2 + roof_rise**2) ** 0.5)

        # Two roof surfaces
        return 2 * self.length * slope_length

    @property
    def total_surface_area(self) -> float:
        """Total exterior surface area in m² (walls + roof, excluding floor)."""
        return self.wall_area + self.roof_area


@dataclass
class CoveringProperties:
    """Optical and thermal properties of greenhouse covering material.

    Attributes:
        material_name: Descriptive name of the material.
        transmittance_solar: Solar radiation transmittance (0-1).
        transmittance_par: PAR transmittance (0-1).
        transmittance_thermal: Long-wave (thermal) transmittance (0-1).
        u_value: Overall heat transfer coefficient in W/(m²·K).
        reflectance_solar: Solar reflectance (0-1).
    """

    material_name: str = "double_polyethylene"
    transmittance_solar: float = 0.77
    transmittance_par: float = 0.75
    transmittance_thermal: float = 0.05
    u_value: float = 4.0
    reflectance_solar: float = 0.13

    def __post_init__(self) -> None:
        """Validate covering properties."""
        for attr in [
            "transmittance_solar",
            "transmittance_par",
            "transmittance_thermal",
            "reflectance_solar",
        ]:
            val = getattr(self, attr)
            if not 0 <= val <= 1:
                msg = f"{attr} must be in [0, 1], got {val}"
                raise ValueError(msg)
        if self.u_value <= 0:
            msg = f"U-value must be positive, got {self.u_value}"
            raise ValueError(msg)

    @property
    def absorptance_solar(self) -> float:
        """Solar absorptance (1 - transmittance - reflectance)."""
        return 1.0 - self.transmittance_solar - self.reflectance_solar


# Pre-defined covering materials
COVERING_MATERIALS: dict[str, CoveringProperties] = {
    "single_glass": CoveringProperties(
        material_name="single_glass",
        transmittance_solar=0.85,
        transmittance_par=0.83,
        transmittance_thermal=0.02,
        u_value=5.8,
        reflectance_solar=0.08,
    ),
    "double_glass": CoveringProperties(
        material_name="double_glass",
        transmittance_solar=0.75,
        transmittance_par=0.73,
        transmittance_thermal=0.02,
        u_value=3.0,
        reflectance_solar=0.12,
    ),
    "single_polyethylene": CoveringProperties(
        material_name="single_polyethylene",
        transmittance_solar=0.87,
        transmittance_par=0.85,
        transmittance_thermal=0.70,
        u_value=6.0,
        reflectance_solar=0.08,
    ),
    "double_polyethylene": CoveringProperties(
        material_name="double_polyethylene",
        transmittance_solar=0.77,
        transmittance_par=0.75,
        transmittance_thermal=0.05,
        u_value=4.0,
        reflectance_solar=0.13,
    ),
    "polycarbonate_twin": CoveringProperties(
        material_name="polycarbonate_twin",
        transmittance_solar=0.80,
        transmittance_par=0.78,
        transmittance_thermal=0.03,
        u_value=3.5,
        reflectance_solar=0.10,
    ),
    "polycarbonate_triple": CoveringProperties(
        material_name="polycarbonate_triple",
        transmittance_solar=0.72,
        transmittance_par=0.70,
        transmittance_thermal=0.02,
        u_value=2.5,
        reflectance_solar=0.12,
    ),
}


@dataclass
class GreenhouseState:
    """Complete state of the greenhouse simulation.

    This is the central data structure passed through the simulation loop.
    It contains all information needed to compute the next state.

    Attributes:
        time: Current simulation time.
        interior: Interior air state.
        exterior: Exterior (ambient) air state.
        solar_radiation: Global horizontal irradiance in W/m².
        wind_speed: Wind speed in m/s.
        wind_direction: Wind direction in degrees from North.
        location: Geographic location.
        geometry: Greenhouse physical dimensions.
        covering: Covering material properties.
    """

    time: datetime = field(default_factory=lambda: datetime.now(UTC))
    interior: AirState = field(default_factory=AirState)
    exterior: AirState = field(default_factory=AirState)
    solar_radiation: float = 0.0
    wind_speed: float = 0.0
    wind_direction: float = 0.0
    location: Location = field(
        default_factory=lambda: Location(latitude=37.3, longitude=-78.4)
    )
    geometry: GreenhouseGeometry = field(default_factory=GreenhouseGeometry)
    covering: CoveringProperties = field(default_factory=CoveringProperties)

    def __post_init__(self) -> None:
        """Validate state values."""
        if self.solar_radiation < 0:
            msg = f"Solar radiation cannot be negative, got {self.solar_radiation}"
            raise ValueError(msg)
        if self.wind_speed < 0:
            msg = f"Wind speed cannot be negative, got {self.wind_speed}"
            raise ValueError(msg)

    def copy(self) -> GreenhouseState:
        """Create a deep copy of this state."""
        return GreenhouseState(
            time=self.time,
            interior=self.interior.copy(),
            exterior=self.exterior.copy(),
            solar_radiation=self.solar_radiation,
            wind_speed=self.wind_speed,
            wind_direction=self.wind_direction,
            location=Location(
                latitude=self.location.latitude,
                longitude=self.location.longitude,
                elevation=self.location.elevation,
                timezone_str=self.location.timezone_str,
            ),
            geometry=GreenhouseGeometry(
                geometry_type=self.geometry.geometry_type,
                length=self.geometry.length,
                width=self.geometry.width,
                height_ridge=self.geometry.height_ridge,
                height_eave=self.geometry.height_eave,
                orientation=self.geometry.orientation,
            ),
            covering=CoveringProperties(
                material_name=self.covering.material_name,
                transmittance_solar=self.covering.transmittance_solar,
                transmittance_par=self.covering.transmittance_par,
                transmittance_thermal=self.covering.transmittance_thermal,
                u_value=self.covering.u_value,
                reflectance_solar=self.covering.reflectance_solar,
            ),
        )

    @property
    def interior_exterior_delta_t(self) -> float:
        """Temperature difference between interior and exterior in °C."""
        return self.interior.temperature - self.exterior.temperature
