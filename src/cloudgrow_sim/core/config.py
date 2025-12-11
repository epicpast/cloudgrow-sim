"""Pydantic configuration models for greenhouse simulation.

This module defines the configuration schema for greenhouse simulations
using Pydantic v2 models. Configuration can be loaded from YAML or JSON files.

The configuration hierarchy:
- SimulationConfig (top-level)
  - LocationConfig
  - GeometryConfig
  - CoveringConfig
  - ComponentsConfig
    - SensorConfig[]
    - ActuatorConfig[]
    - ControllerConfig[]
    - ModifierConfig[]
  - SetpointsConfig
  - WeatherConfig
  - OutputConfig
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Annotated, Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from cloudgrow_sim.core.state import (
    COVERING_MATERIALS,
    CoveringProperties,
    GeometryType,
    GreenhouseGeometry,
    Location,
)


class LocationConfig(BaseModel):
    """Geographic location configuration."""

    model_config = ConfigDict(frozen=True)

    latitude: Annotated[float, Field(ge=-90, le=90, description="Latitude in degrees")]
    longitude: Annotated[
        float, Field(ge=-180, le=180, description="Longitude in degrees")
    ]
    elevation: Annotated[
        float, Field(default=0.0, ge=-500, le=9000, description="Elevation in meters")
    ]
    timezone: str = Field(default="UTC", description="IANA timezone string")

    def to_location(self) -> Location:
        """Convert to Location state object."""
        return Location(
            latitude=self.latitude,
            longitude=self.longitude,
            elevation=self.elevation,
            timezone_str=self.timezone,
        )


class GeometryConfig(BaseModel):
    """Greenhouse geometry configuration."""

    model_config = ConfigDict(frozen=True)

    type: GeometryType = Field(default=GeometryType.GABLE)
    length: Annotated[float, Field(gt=0, description="Length in meters (N-S)")]
    width: Annotated[float, Field(gt=0, description="Width in meters (E-W)")]
    height_ridge: Annotated[float, Field(gt=0, description="Ridge height in meters")]
    height_eave: Annotated[float, Field(gt=0, description="Eave height in meters")]
    orientation: Annotated[
        float, Field(default=0.0, ge=0, lt=360, description="Orientation from North")
    ]

    @model_validator(mode="after")
    def validate_heights(self) -> GeometryConfig:
        """Ensure eave height doesn't exceed ridge height."""
        if self.height_eave > self.height_ridge:
            msg = f"Eave height ({self.height_eave}) cannot exceed ridge ({self.height_ridge})"
            raise ValueError(msg)
        return self

    def to_geometry(self) -> GreenhouseGeometry:
        """Convert to GreenhouseGeometry state object."""
        return GreenhouseGeometry(
            geometry_type=self.type,
            length=self.length,
            width=self.width,
            height_ridge=self.height_ridge,
            height_eave=self.height_eave,
            orientation=self.orientation,
        )


class CoveringConfig(BaseModel):
    """Greenhouse covering material configuration."""

    model_config = ConfigDict(frozen=True)

    material: str | None = Field(
        default="double_polyethylene",
        description="Pre-defined material name or None for custom",
    )
    transmittance_solar: Annotated[float, Field(default=0.77, ge=0, le=1)] = 0.77
    transmittance_par: Annotated[float, Field(default=0.75, ge=0, le=1)] = 0.75
    transmittance_thermal: Annotated[float, Field(default=0.05, ge=0, le=1)] = 0.05
    u_value: Annotated[float, Field(default=4.0, gt=0)] = 4.0
    reflectance_solar: Annotated[float, Field(default=0.13, ge=0, le=1)] = 0.13

    def to_covering(self) -> CoveringProperties:
        """Convert to CoveringProperties state object."""
        if self.material and self.material in COVERING_MATERIALS:
            return COVERING_MATERIALS[self.material]

        return CoveringProperties(
            material_name=self.material or "custom",
            transmittance_solar=self.transmittance_solar,
            transmittance_par=self.transmittance_par,
            transmittance_thermal=self.transmittance_thermal,
            u_value=self.u_value,
            reflectance_solar=self.reflectance_solar,
        )


class SensorConfig(BaseModel):
    """Sensor component configuration."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(description="Sensor type from registry")
    name: str = Field(description="Unique sensor name")
    location: Literal["interior", "exterior"] = Field(default="interior")
    position: tuple[float, float, float] | None = Field(
        default=None, description="(x, y, z) position in meters"
    )
    noise_std_dev: Annotated[float, Field(default=0.0, ge=0)] = 0.0
    enabled: bool = True


class ActuatorConfig(BaseModel):
    """Actuator component configuration."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(description="Actuator type from registry")
    name: str = Field(description="Unique actuator name")
    controller: str | None = Field(default=None, description="Controller name to bind")
    enabled: bool = True

    # Common actuator properties with defaults
    max_output: float = 1.0
    min_output: float = 0.0


class ControllerConfig(BaseModel):
    """Controller component configuration."""

    model_config = ConfigDict(extra="allow")

    type: str = Field(description="Controller type from registry")
    name: str = Field(description="Unique controller name")
    process_variable: str = Field(description="Sensor.measurement to control")
    output_target: str | None = Field(
        default=None, description="Actuator.property to control"
    )
    setpoint: float | None = Field(default=None, description="Fixed setpoint value")
    setpoint_source: Literal["fixed", "schedule"] = Field(default="fixed")
    enabled: bool = True

    # PID-specific (will be used if type is "pid")
    kp: float = 1.0
    ki: float = 0.0
    kd: float = 0.0
    output_limits: tuple[float, float] = (0.0, 1.0)
    anti_windup: bool = True


class ModifierConfig(BaseModel):
    """Modifier component configuration.

    Modifiers are passive elements that affect greenhouse climate
    without active control (e.g., covering materials, thermal mass).
    """

    model_config = ConfigDict(extra="allow")

    type: str = Field(description="Modifier type from registry")
    name: str = Field(description="Unique modifier name")
    enabled: bool = True


class ComponentsConfig(BaseModel):
    """Container for all component configurations."""

    sensors: list[SensorConfig] = Field(default_factory=list)
    actuators: list[ActuatorConfig] = Field(default_factory=list)
    controllers: list[ControllerConfig] = Field(default_factory=list)
    modifiers: list[ModifierConfig] = Field(default_factory=list)

    @field_validator("sensors", "actuators", "controllers", "modifiers", mode="after")
    @classmethod
    def validate_unique_names(
        cls, v: list[SensorConfig | ActuatorConfig | ControllerConfig | ModifierConfig]
    ) -> list[SensorConfig | ActuatorConfig | ControllerConfig | ModifierConfig]:
        """Ensure all component names are unique within their category."""
        names = [c.name for c in v]
        if len(names) != len(set(names)):
            duplicates = [n for n in names if names.count(n) > 1]
            msg = f"Duplicate component names: {set(duplicates)}"
            raise ValueError(msg)
        return v


class ScheduleEntry(BaseModel):
    """Single entry in a setpoint schedule."""

    time: str = Field(description="Time in HH:MM format")
    value: float

    @field_validator("time")
    @classmethod
    def validate_time_format(cls, v: str) -> str:
        """Validate time format."""
        try:
            parts = v.split(":")
            hour = int(parts[0])
            minute = int(parts[1])
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                msg = f"Invalid time: {v}"
                raise ValueError(msg)
        except (ValueError, IndexError) as e:
            msg = f"Invalid time format '{v}', expected HH:MM"
            raise ValueError(msg) from e
        return v


class SetpointsConfig(BaseModel):
    """Setpoint schedules configuration."""

    schedules: dict[str, list[ScheduleEntry]] = Field(default_factory=dict)
    defaults: dict[str, float] = Field(default_factory=dict)


class WeatherConfig(BaseModel):
    """Weather data source configuration."""

    source: Literal["file", "synthetic", "home_assistant", "api"] = Field(
        default="synthetic"
    )
    file: str | None = Field(default=None, description="Path to weather CSV file")

    # Synthetic weather parameters
    typical_summer: bool = False
    typical_winter: bool = False
    base_temperature: float = 20.0
    temperature_amplitude: float = 10.0

    # Home Assistant integration
    ha_url: str | None = Field(default=None, description="Home Assistant URL")
    ha_token: str | None = Field(default=None, description="HA long-lived access token")
    ha_sensors: dict[str, str] = Field(
        default_factory=dict,
        description="Mapping: property -> HA entity_id",
    )


class InfluxDBConfig(BaseModel):
    """InfluxDB output configuration."""

    enabled: bool = False
    url: str = "http://localhost:8086"
    org: str = ""
    bucket: str = ""
    token: str | None = Field(default=None, description="InfluxDB API token")


class CSVOutputConfig(BaseModel):
    """CSV output configuration."""

    enabled: bool = False
    path: str = "output/simulation_results.csv"


class PlotOutputConfig(BaseModel):
    """Plotting output configuration."""

    enabled: bool = False
    path: str = "output/plots/"
    formats: list[str] = Field(default_factory=lambda: ["png"])


class OutputConfig(BaseModel):
    """Output destinations configuration."""

    influxdb: InfluxDBConfig = Field(default_factory=InfluxDBConfig)
    csv: CSVOutputConfig = Field(default_factory=CSVOutputConfig)
    plots: PlotOutputConfig = Field(default_factory=PlotOutputConfig)


class SimulationConfig(BaseModel):
    """Top-level simulation configuration."""

    model_config = ConfigDict(extra="forbid")

    # Simulation parameters
    name: str = Field(default="Greenhouse Simulation")
    time_step: Annotated[float, Field(default=1.0, gt=0)] = 1.0  # seconds
    duration: Annotated[float, Field(default=86400.0, gt=0)] = 86400.0  # seconds
    start_time: datetime | None = None

    # Physical configuration
    location: LocationConfig
    geometry: GeometryConfig
    covering: CoveringConfig = Field(default_factory=CoveringConfig)

    # Components
    components: ComponentsConfig = Field(default_factory=ComponentsConfig)

    # Setpoints
    setpoints: SetpointsConfig = Field(default_factory=SetpointsConfig)

    # Weather
    weather: WeatherConfig = Field(default_factory=WeatherConfig)

    # Output
    output: OutputConfig = Field(default_factory=OutputConfig)

    @property
    def duration_timedelta(self) -> timedelta:
        """Get duration as timedelta."""
        return timedelta(seconds=self.duration)


def load_config(path: str | Path) -> SimulationConfig:
    """Load simulation configuration from YAML or JSON file.

    Args:
        path: Path to configuration file.

    Returns:
        Validated SimulationConfig object.

    Raises:
        FileNotFoundError: If file doesn't exist.
        ValueError: If configuration is invalid.
    """
    path = Path(path)

    if not path.exists():
        msg = f"Configuration file not found: {path}"
        raise FileNotFoundError(msg)

    with path.open() as f:
        if path.suffix in (".yaml", ".yml"):
            data = yaml.safe_load(f)
        else:
            import json

            data = json.load(f)

    return SimulationConfig.model_validate(data)


def save_config(config: SimulationConfig, path: str | Path) -> None:
    """Save simulation configuration to YAML or JSON file.

    Args:
        config: Configuration to save.
        path: Output file path.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = config.model_dump(mode="json", exclude_none=True)

    with path.open("w") as f:
        if path.suffix in (".yaml", ".yml"):
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        else:
            import json

            json.dump(data, f, indent=2)


def validate_config(data: dict[str, Any]) -> SimulationConfig:
    """Validate configuration data without loading from file.

    Args:
        data: Configuration dictionary.

    Returns:
        Validated SimulationConfig object.

    Raises:
        ValueError: If configuration is invalid.
    """
    return SimulationConfig.model_validate(data)
