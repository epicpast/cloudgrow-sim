"""Tests for configuration models."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import SecretStr, ValidationError

from cloudgrow_sim.core.config import (
    ActuatorConfig,
    ComponentsConfig,
    ControllerConfig,
    CoveringConfig,
    GeometryConfig,
    InfluxDBConfig,
    LocationConfig,
    ModifierConfig,
    SensorConfig,
    SimulationConfig,
    WeatherConfig,
    load_config,
    save_config,
)
from cloudgrow_sim.core.state import GeometryType


class TestLocationConfig:
    """Tests for LocationConfig."""

    def test_basic_creation(self) -> None:
        """Create basic location config."""
        config = LocationConfig(latitude=37.0, longitude=-78.0)
        assert config.latitude == 37.0
        assert config.longitude == -78.0
        assert config.elevation == 0.0  # default
        assert config.timezone == "UTC"  # default

    def test_full_creation(self) -> None:
        """Create location config with all fields."""
        config = LocationConfig(
            latitude=37.3,
            longitude=-78.4,
            elevation=200.0,
            timezone="America/New_York",
        )
        assert config.latitude == 37.3
        assert config.longitude == -78.4
        assert config.elevation == 200.0
        assert config.timezone == "America/New_York"

    def test_to_location(self) -> None:
        """Convert to Location state object."""
        config = LocationConfig(
            latitude=37.3,
            longitude=-78.4,
            elevation=150.0,
            timezone="America/New_York",
        )
        loc = config.to_location()
        assert loc.latitude == 37.3
        assert loc.longitude == -78.4
        assert loc.elevation == 150.0
        assert loc.timezone_str == "America/New_York"

    def test_invalid_latitude(self) -> None:
        """Error on invalid latitude."""
        with pytest.raises(ValueError):
            LocationConfig(latitude=100.0, longitude=0.0)

    def test_invalid_longitude(self) -> None:
        """Error on invalid longitude."""
        with pytest.raises(ValueError):
            LocationConfig(latitude=0.0, longitude=200.0)


class TestGeometryConfig:
    """Tests for GeometryConfig."""

    def test_basic_creation(self) -> None:
        """Create basic geometry config."""
        config = GeometryConfig(
            length=30.0,
            width=10.0,
            height_ridge=5.0,
            height_eave=3.0,
        )
        assert config.length == 30.0
        assert config.width == 10.0
        assert config.height_ridge == 5.0
        assert config.height_eave == 3.0
        assert config.type == GeometryType.GABLE  # default

    def test_quonset_type(self) -> None:
        """Create quonset geometry."""
        config = GeometryConfig(
            type=GeometryType.QUONSET,
            length=20.0,
            width=8.0,
            height_ridge=4.0,
            height_eave=2.0,
        )
        assert config.type == GeometryType.QUONSET

    def test_to_geometry(self) -> None:
        """Convert to GreenhouseGeometry state object."""
        config = GeometryConfig(
            type=GeometryType.GABLE,
            length=30.0,
            width=10.0,
            height_ridge=5.0,
            height_eave=3.0,
            orientation=45.0,
        )
        geom = config.to_geometry()
        assert geom.geometry_type == GeometryType.GABLE
        assert geom.length == 30.0
        assert geom.width == 10.0
        assert geom.height_ridge == 5.0
        assert geom.height_eave == 3.0
        assert geom.orientation == 45.0

    def test_eave_exceeds_ridge_error(self) -> None:
        """Error when eave exceeds ridge height."""
        with pytest.raises(ValueError, match="cannot exceed"):
            GeometryConfig(
                length=30.0,
                width=10.0,
                height_ridge=3.0,
                height_eave=5.0,  # Higher than ridge
            )

    def test_zero_dimensions_error(self) -> None:
        """Error on zero dimensions."""
        with pytest.raises(ValueError):
            GeometryConfig(
                length=0.0,  # Invalid
                width=10.0,
                height_ridge=5.0,
                height_eave=3.0,
            )


class TestCoveringConfig:
    """Tests for CoveringConfig."""

    def test_predefined_material(self) -> None:
        """Use predefined material."""
        config = CoveringConfig(material="double_polyethylene")
        assert config.material == "double_polyethylene"
        props = config.to_covering()
        assert props.material_name == "double_polyethylene"

    def test_single_glass_material(self) -> None:
        """Use single glass material."""
        config = CoveringConfig(material="single_glass")
        props = config.to_covering()
        assert props.material_name == "single_glass"

    def test_custom_material(self) -> None:
        """Use custom material properties."""
        config = CoveringConfig(
            material=None,  # Custom
            transmittance_solar=0.90,
            transmittance_par=0.92,
            transmittance_thermal=0.05,
            u_value=6.0,
            reflectance_solar=0.05,
        )
        props = config.to_covering()
        assert props.transmittance_solar == 0.90
        assert props.u_value == 6.0
        assert props.material_name == "custom"

    def test_default_values(self) -> None:
        """Check default covering config values."""
        config = CoveringConfig()
        assert config.material == "double_polyethylene"
        assert config.transmittance_solar == 0.77
        assert config.u_value == 4.0


class TestModifierConfig:
    """Tests for ModifierConfig."""

    def test_modifier_config_valid(self) -> None:
        """Create valid modifier config."""
        config = ModifierConfig(type="covering", name="main_covering")
        assert config.type == "covering"
        assert config.name == "main_covering"
        assert config.enabled is True  # default

    def test_modifier_config_extra_fields_allowed(self) -> None:
        """Extra fields pass through for component-specific params."""
        config = ModifierConfig(
            type="thermal_mass",
            name="water_barrels",
            mass=2000.0,
            specific_heat=4186.0,
            surface_area=10.0,
            initial_temperature=20.0,
        )
        assert config.type == "thermal_mass"
        assert config.name == "water_barrels"
        # Extra fields accessible via model_dump
        data = config.model_dump()
        assert data["mass"] == 2000.0
        assert data["specific_heat"] == 4186.0
        assert data["surface_area"] == 10.0
        assert data["initial_temperature"] == 20.0

    def test_modifier_config_type_required(self) -> None:
        """Error when type is missing."""
        with pytest.raises(ValueError):
            ModifierConfig(name="no_type")  # type: ignore[call-arg]

    def test_modifier_config_name_required(self) -> None:
        """Error when name is missing."""
        with pytest.raises(ValueError):
            ModifierConfig(type="covering")  # type: ignore[call-arg]

    def test_modifier_config_disabled(self) -> None:
        """Create disabled modifier."""
        config = ModifierConfig(type="covering", name="disabled_cover", enabled=False)
        assert config.enabled is False


class TestComponentsConfigWithModifiers:
    """Tests for ComponentsConfig including modifiers."""

    def test_components_config_includes_modifiers(self) -> None:
        """ComponentsConfig includes modifiers list."""
        config = ComponentsConfig(
            sensors=[SensorConfig(type="temperature", name="temp_1")],
            actuators=[
                ActuatorConfig(
                    type="exhaust_fan",
                    name="fan_1",
                    max_flow_rate=1.0,
                    power_consumption=500.0,
                )
            ],
            controllers=[
                ControllerConfig(
                    type="hysteresis",
                    name="ctrl_1",
                    process_variable="temp_1.temperature",
                    setpoint=25.0,
                )
            ],
            modifiers=[
                ModifierConfig(type="covering", name="cover_1", material="single_glass")
            ],
        )
        assert len(config.sensors) == 1
        assert len(config.actuators) == 1
        assert len(config.controllers) == 1
        assert len(config.modifiers) == 1
        assert config.modifiers[0].type == "covering"

    def test_components_config_empty_modifiers_default(self) -> None:
        """ComponentsConfig defaults to empty modifiers list."""
        config = ComponentsConfig()
        assert config.modifiers == []

    def test_components_config_multiple_modifiers(self) -> None:
        """ComponentsConfig can have multiple modifiers."""
        config = ComponentsConfig(
            modifiers=[
                ModifierConfig(type="covering", name="cover_1"),
                ModifierConfig(
                    type="thermal_mass",
                    name="mass_1",
                    mass=1000.0,
                    specific_heat=4186.0,
                    surface_area=5.0,
                    initial_temperature=20.0,
                ),
            ]
        )
        assert len(config.modifiers) == 2
        assert config.modifiers[0].type == "covering"
        assert config.modifiers[1].type == "thermal_mass"


class TestSecretStrTokens:
    """Tests for SEC-2: SecretStr token handling."""

    def test_weather_config_ha_token_is_secret(self) -> None:
        """SEC-2: WeatherConfig.ha_token uses SecretStr."""
        config = WeatherConfig(
            source="home_assistant",
            ha_url="http://homeassistant.local:8123",
            ha_token="super_secret_token_12345",
        )
        # Token should be wrapped in SecretStr
        assert isinstance(config.ha_token, SecretStr)
        # Getting the value requires explicit call to get_secret_value()
        assert config.ha_token.get_secret_value() == "super_secret_token_12345"

    def test_weather_config_ha_token_not_in_repr(self) -> None:
        """SEC-2: ha_token should not appear in string representation."""
        config = WeatherConfig(
            source="home_assistant",
            ha_url="http://homeassistant.local:8123",
            ha_token="super_secret_token_12345",
        )
        config_str = str(config)
        config_repr = repr(config)
        # The actual token value should NOT appear in string representations
        assert "super_secret_token_12345" not in config_str
        assert "super_secret_token_12345" not in config_repr

    def test_weather_config_ha_token_masked_in_model_dump(self) -> None:
        """SEC-2: ha_token is masked in default model_dump."""
        config = WeatherConfig(
            source="home_assistant",
            ha_url="http://homeassistant.local:8123",
            ha_token="super_secret_token_12345",
        )
        # Default dump masks secret
        dumped = config.model_dump()
        assert dumped["ha_token"] != "super_secret_token_12345"
        # The dump contains a SecretStr object, not the raw value
        assert isinstance(dumped["ha_token"], SecretStr)

    def test_influxdb_config_token_is_secret(self) -> None:
        """SEC-2: InfluxDBConfig.token uses SecretStr."""
        config = InfluxDBConfig(
            enabled=True,
            url="http://localhost:8086",
            org="my-org",
            bucket="greenhouse",
            token="influx_api_token_xyz789",
        )
        # Token should be wrapped in SecretStr
        assert isinstance(config.token, SecretStr)
        # Getting the value requires explicit call
        assert config.token.get_secret_value() == "influx_api_token_xyz789"

    def test_influxdb_config_token_not_in_repr(self) -> None:
        """SEC-2: InfluxDB token should not appear in string representation."""
        config = InfluxDBConfig(
            enabled=True,
            url="http://localhost:8086",
            org="my-org",
            bucket="greenhouse",
            token="influx_api_token_xyz789",
        )
        config_str = str(config)
        config_repr = repr(config)
        # The actual token value should NOT appear in string representations
        assert "influx_api_token_xyz789" not in config_str
        assert "influx_api_token_xyz789" not in config_repr

    def test_tokens_none_by_default(self) -> None:
        """Tokens default to None."""
        weather_config = WeatherConfig()
        assert weather_config.ha_token is None

        influxdb_config = InfluxDBConfig()
        assert influxdb_config.token is None

    def test_token_from_yaml_string(self, tmp_path: Path) -> None:
        """Tokens can be loaded from YAML as plain strings."""
        yaml_content = """
name: Token Test
location:
  latitude: 37.0
  longitude: -78.0
geometry:
  length: 10.0
  width: 5.0
  height_ridge: 4.0
  height_eave: 2.5
weather:
  source: home_assistant
  ha_url: http://homeassistant.local:8123
  ha_token: my_secret_ha_token
output:
  influxdb:
    enabled: true
    url: http://localhost:8086
    org: test-org
    bucket: test-bucket
    token: my_influxdb_token
"""
        yaml_file = tmp_path / "config_with_tokens.yaml"
        yaml_file.write_text(yaml_content)

        config = load_config(yaml_file)

        # Tokens should be loaded and wrapped in SecretStr
        assert config.weather.ha_token is not None
        assert isinstance(config.weather.ha_token, SecretStr)
        assert config.weather.ha_token.get_secret_value() == "my_secret_ha_token"

        assert config.output.influxdb.token is not None
        assert isinstance(config.output.influxdb.token, SecretStr)
        assert config.output.influxdb.token.get_secret_value() == "my_influxdb_token"


class TestConfigIO:
    """Tests for configuration file I/O."""

    def test_load_config_yaml(self, tmp_path: Path) -> None:
        """Test loading YAML configuration file."""
        yaml_content = """
name: Test Simulation
location:
  latitude: 37.0
  longitude: -78.0
  elevation: 100.0
  timezone: America/New_York
geometry:
  length: 10.0
  width: 5.0
  height_ridge: 4.0
  height_eave: 2.5
"""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content)

        config = load_config(yaml_file)
        assert config.name == "Test Simulation"
        assert config.location.latitude == 37.0
        assert config.location.longitude == -78.0
        assert config.location.elevation == 100.0
        assert config.location.timezone == "America/New_York"
        assert config.geometry.length == 10.0
        assert config.geometry.width == 5.0
        assert config.geometry.height_ridge == 4.0
        assert config.geometry.height_eave == 2.5

    def test_load_config_yml_extension(self, tmp_path: Path) -> None:
        """Test loading YAML configuration file with .yml extension."""
        yaml_content = """
name: YML Test
location:
  latitude: 40.0
  longitude: -75.0
geometry:
  length: 20.0
  width: 10.0
  height_ridge: 5.0
  height_eave: 3.0
"""
        yml_file = tmp_path / "config.yml"
        yml_file.write_text(yaml_content)

        config = load_config(yml_file)
        assert config.name == "YML Test"
        assert config.location.latitude == 40.0

    def test_load_config_json(self, tmp_path: Path) -> None:
        """Test loading JSON configuration file."""
        json_content = {
            "name": "JSON Test Simulation",
            "location": {"latitude": 38.0, "longitude": -77.0, "elevation": 50.0},
            "geometry": {
                "length": 15.0,
                "width": 8.0,
                "height_ridge": 5.0,
                "height_eave": 3.0,
            },
        }
        json_file = tmp_path / "config.json"
        json_file.write_text(json.dumps(json_content))

        config = load_config(json_file)
        assert config.name == "JSON Test Simulation"
        assert config.location.latitude == 38.0
        assert config.location.longitude == -77.0
        assert config.location.elevation == 50.0
        assert config.geometry.length == 15.0

    def test_save_config_yaml(self, tmp_path: Path) -> None:
        """Test saving configuration to YAML."""
        config = SimulationConfig(
            name="Save Test",
            location=LocationConfig(latitude=35.0, longitude=-80.0, elevation=200.0),
            geometry=GeometryConfig(
                length=25.0, width=12.0, height_ridge=6.0, height_eave=4.0
            ),
        )

        yaml_file = tmp_path / "output.yaml"
        save_config(config, yaml_file)

        # Reload and verify
        loaded_config = load_config(yaml_file)
        assert loaded_config.name == "Save Test"
        assert loaded_config.location.latitude == 35.0
        assert loaded_config.location.longitude == -80.0
        assert loaded_config.geometry.length == 25.0

    def test_save_config_json(self, tmp_path: Path) -> None:
        """Test saving configuration to JSON."""
        config = SimulationConfig(
            name="JSON Save Test",
            location=LocationConfig(latitude=36.0, longitude=-79.0),
            geometry=GeometryConfig(
                length=30.0, width=15.0, height_ridge=7.0, height_eave=4.5
            ),
        )

        json_file = tmp_path / "output.json"
        save_config(config, json_file)

        # Reload and verify
        loaded_config = load_config(json_file)
        assert loaded_config.name == "JSON Save Test"
        assert loaded_config.location.latitude == 36.0
        assert loaded_config.geometry.length == 30.0

    def test_save_config_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that save_config creates parent directories if they don't exist."""
        config = SimulationConfig(
            name="Nested Path Test",
            location=LocationConfig(latitude=37.0, longitude=-78.0),
            geometry=GeometryConfig(
                length=10.0, width=5.0, height_ridge=4.0, height_eave=2.5
            ),
        )

        nested_path = tmp_path / "nested" / "path" / "config.yaml"
        save_config(config, nested_path)

        assert nested_path.exists()
        loaded_config = load_config(nested_path)
        assert loaded_config.name == "Nested Path Test"

    def test_load_config_file_not_found(self) -> None:
        """Test FileNotFoundError for missing config."""
        with pytest.raises(FileNotFoundError, match="Configuration file not found"):
            load_config(Path("/nonexistent/path/config.yaml"))

    def test_load_config_invalid_yaml(self, tmp_path: Path) -> None:
        """Test validation error for invalid config content."""
        # Write YAML that parses but fails validation (missing required fields)
        invalid_yaml = """
name: Invalid Config
# Missing required location and geometry
"""
        yaml_file = tmp_path / "invalid.yaml"
        yaml_file.write_text(invalid_yaml)

        with pytest.raises(ValidationError):
            load_config(yaml_file)

    def test_load_config_invalid_values(self, tmp_path: Path) -> None:
        """Test validation error for invalid field values."""
        invalid_yaml = """
name: Bad Values
location:
  latitude: 100.0  # Invalid: must be [-90, 90]
  longitude: -78.0
geometry:
  length: 10.0
  width: 5.0
  height_ridge: 4.0
  height_eave: 2.5
"""
        yaml_file = tmp_path / "invalid_values.yaml"
        yaml_file.write_text(invalid_yaml)

        with pytest.raises(ValidationError):
            load_config(yaml_file)

    def test_load_config_with_components(self, tmp_path: Path) -> None:
        """Test loading config with components section."""
        yaml_content = """
name: Full Config Test
location:
  latitude: 37.0
  longitude: -78.0
geometry:
  length: 10.0
  width: 5.0
  height_ridge: 4.0
  height_eave: 2.5
components:
  sensors:
    - type: temperature
      name: temp_interior
      location: interior
  actuators:
    - type: exhaust_fan
      name: fan_1
      max_output: 1.0
"""
        yaml_file = tmp_path / "full_config.yaml"
        yaml_file.write_text(yaml_content)

        config = load_config(yaml_file)
        assert len(config.components.sensors) == 1
        assert config.components.sensors[0].name == "temp_interior"
        assert len(config.components.actuators) == 1
        assert config.components.actuators[0].name == "fan_1"

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Test that save and load produce equivalent configs."""
        original_config = SimulationConfig(
            name="Roundtrip Test",
            time_step=30.0,
            duration=3600.0,
            location=LocationConfig(
                latitude=40.0, longitude=-75.0, elevation=150.0, timezone="UTC"
            ),
            geometry=GeometryConfig(
                length=20.0, width=10.0, height_ridge=5.0, height_eave=3.0
            ),
            covering=CoveringConfig(material="single_glass"),
        )

        yaml_file = tmp_path / "roundtrip.yaml"
        save_config(original_config, yaml_file)
        loaded_config = load_config(yaml_file)

        assert loaded_config.name == original_config.name
        assert loaded_config.time_step == original_config.time_step
        assert loaded_config.duration == original_config.duration
        assert loaded_config.location.latitude == original_config.location.latitude
        assert loaded_config.location.longitude == original_config.location.longitude
        assert loaded_config.geometry.length == original_config.geometry.length
        assert loaded_config.covering.material == original_config.covering.material
