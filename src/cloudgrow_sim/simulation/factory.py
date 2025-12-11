"""Factory functions for creating simulation components from configuration.

This module provides the bridge between YAML/JSON configuration files and
actual simulation component instantiation. The main entry point is
`create_engine_from_config()` which creates a fully configured
SimulationEngine ready to run.
"""

from __future__ import annotations

import importlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

# Import component modules to populate the registry at import time
# These modules register components via @register_component decorator
import cloudgrow_sim.components.actuators.cooling
import cloudgrow_sim.components.actuators.curtains
import cloudgrow_sim.components.actuators.fans
import cloudgrow_sim.components.actuators.heating
import cloudgrow_sim.components.actuators.vents
import cloudgrow_sim.components.modifiers.covering
import cloudgrow_sim.components.modifiers.thermal_mass
import cloudgrow_sim.components.sensors.co2
import cloudgrow_sim.components.sensors.humidity
import cloudgrow_sim.components.sensors.radiation
import cloudgrow_sim.components.sensors.temperature
import cloudgrow_sim.components.sensors.wind
import cloudgrow_sim.controllers.hysteresis
import cloudgrow_sim.controllers.pid
import cloudgrow_sim.controllers.schedule
import cloudgrow_sim.controllers.staged
from cloudgrow_sim.core.base import Actuator, Controller, Sensor
from cloudgrow_sim.core.config import (
    ActuatorConfig,
    ControllerConfig,
    ModifierConfig,
    SensorConfig,
    SimulationConfig,
)
from cloudgrow_sim.core.registry import get_registry
from cloudgrow_sim.core.state import (
    AirState,
    GreenhouseState,
)
from cloudgrow_sim.simulation.engine import SimulationConfig as EngineConfig
from cloudgrow_sim.simulation.engine import SimulationEngine
from cloudgrow_sim.simulation.weather import (
    CSVWeatherSource,
    SyntheticWeatherConfig,
    SyntheticWeatherSource,
    WeatherSource,
)

if TYPE_CHECKING:
    from cloudgrow_sim.components.modifiers.covering import CoveringMaterial
    from cloudgrow_sim.components.modifiers.thermal_mass import ThermalMass

# List of component modules for re-registration after registry reset
_COMPONENT_MODULES = [
    cloudgrow_sim.components.actuators.cooling,
    cloudgrow_sim.components.actuators.curtains,
    cloudgrow_sim.components.actuators.fans,
    cloudgrow_sim.components.actuators.heating,
    cloudgrow_sim.components.actuators.vents,
    cloudgrow_sim.components.modifiers.covering,
    cloudgrow_sim.components.modifiers.thermal_mass,
    cloudgrow_sim.components.sensors.co2,
    cloudgrow_sim.components.sensors.humidity,
    cloudgrow_sim.components.sensors.radiation,
    cloudgrow_sim.components.sensors.temperature,
    cloudgrow_sim.components.sensors.wind,
    cloudgrow_sim.controllers.hysteresis,
    cloudgrow_sim.controllers.pid,
    cloudgrow_sim.controllers.schedule,
    cloudgrow_sim.controllers.staged,
]


def ensure_components_registered() -> None:
    """Ensure all component modules are registered in the registry.

    This is useful after reset_registry() to re-register components.
    Call this in test setup methods after reset_registry().
    """
    for module in _COMPONENT_MODULES:
        importlib.reload(module)


def create_engine_from_config(
    config: SimulationConfig,
    *,
    clear_registry_instances: bool = True,
) -> SimulationEngine:
    """Create a fully configured SimulationEngine from a SimulationConfig.

    This is the main factory function that bridges configuration files
    to runnable simulations. It:
    1. Creates the initial GreenhouseState from config
    2. Creates the weather source from config
    3. Instantiates all components via the registry
    4. Wires controller-actuator bindings

    Args:
        config: Validated SimulationConfig object (from load_config or direct).
        clear_registry_instances: If True, clear existing registry instances
            before creating new ones. Set to False for testing.

    Returns:
        SimulationEngine ready to run.

    Raises:
        KeyError: If a component type is not found in registry.
        ValueError: If configuration is invalid.
    """
    registry = get_registry()

    # Clear previous instances to avoid name conflicts
    if clear_registry_instances:
        registry.clear_instances()

    # 1. Create initial state
    state = _create_initial_state(config)

    # 2. Create weather source
    weather = _create_weather_source(config)

    # 3. Create engine config
    start_time = config.start_time or datetime.now(UTC).replace(
        hour=6, minute=0, second=0, microsecond=0
    )
    engine_config = EngineConfig(
        time_step=config.time_step,
        start_time=start_time,
        end_time=start_time + timedelta(seconds=config.duration),
        emit_events=True,
    )

    # 4. Create engine
    engine = SimulationEngine(state, weather, engine_config)

    # 5. Create and add components
    # Track actuators and controllers for binding
    actuator_map: dict[str, Actuator] = {}
    controller_map: dict[str, Controller] = {}

    # Sensors
    for sensor_cfg in config.components.sensors:
        if not sensor_cfg.enabled:
            continue
        sensor = _create_sensor(registry, sensor_cfg)
        engine.add_sensor(sensor)

    # Actuators
    for actuator_cfg in config.components.actuators:
        if not actuator_cfg.enabled:
            continue
        actuator = _create_actuator(registry, actuator_cfg)
        engine.add_actuator(actuator)
        actuator_map[actuator_cfg.name] = actuator

    # Controllers
    for controller_cfg in config.components.controllers:
        if not controller_cfg.enabled:
            continue
        controller = _create_controller(registry, controller_cfg)
        engine.add_controller(controller)
        controller_map[controller_cfg.name] = controller

    # Modifiers
    for modifier_cfg in config.components.modifiers:
        if not modifier_cfg.enabled:
            continue
        modifier = _create_modifier(registry, modifier_cfg)
        engine.add_modifier(modifier)

    # Note: Controller-actuator binding is tracked in config but
    # the actual binding happens via the engine's control loop

    return engine


def _create_initial_state(config: SimulationConfig) -> GreenhouseState:
    """Create initial GreenhouseState from config.

    Args:
        config: The simulation configuration.

    Returns:
        Initialized GreenhouseState.
    """
    # Use config's start_time or default to today at 6 AM
    start_time = config.start_time or datetime.now(UTC).replace(
        hour=6, minute=0, second=0, microsecond=0
    )

    return GreenhouseState(
        interior=AirState(temperature=20.0, humidity=60.0, co2_ppm=400.0),
        exterior=AirState(temperature=15.0, humidity=50.0, co2_ppm=400.0),
        time=start_time,
        location=config.location.to_location(),
        geometry=config.geometry.to_geometry(),
        covering=config.covering.to_covering(),
        solar_radiation=0.0,
        wind_speed=2.0,
        wind_direction=180.0,
    )


def _create_weather_source(config: SimulationConfig) -> WeatherSource:
    """Create weather source from config.

    Args:
        config: The simulation configuration.

    Returns:
        Configured WeatherSource instance.
    """
    wc = config.weather

    if wc.source == "synthetic":
        return SyntheticWeatherSource(
            SyntheticWeatherConfig(
                latitude=config.location.latitude,
                temp_mean=wc.base_temperature,
                temp_amplitude_daily=wc.temperature_amplitude,
            )
        )

    if wc.source == "file" and wc.file:
        return CSVWeatherSource(wc.file)

    # Default fallback
    return SyntheticWeatherSource(
        SyntheticWeatherConfig(latitude=config.location.latitude)
    )


def _create_sensor(
    registry: Any,
    sensor_cfg: SensorConfig,
) -> Sensor:
    """Create sensor from config.

    Args:
        registry: The component registry.
        sensor_cfg: Sensor configuration.

    Returns:
        Instantiated sensor.
    """
    # Build kwargs from config
    kwargs: dict[str, Any] = {
        "location": sensor_cfg.location,
    }

    # Add noise if specified
    if sensor_cfg.noise_std_dev > 0:
        kwargs["noise_std_dev"] = sensor_cfg.noise_std_dev

    # Add type-specific kwargs from extra fields
    if sensor_cfg.model_extra:
        kwargs.update(sensor_cfg.model_extra)

    return cast(
        Sensor, registry.create("sensor", sensor_cfg.type, sensor_cfg.name, **kwargs)
    )


def _create_actuator(
    registry: Any,
    actuator_cfg: ActuatorConfig,
) -> Actuator:
    """Create actuator from config.

    Args:
        registry: The component registry.
        actuator_cfg: Actuator configuration.

    Returns:
        Instantiated actuator.
    """
    # Build kwargs from extra fields (type-specific params like max_flow_rate)
    kwargs: dict[str, Any] = {}
    if actuator_cfg.model_extra:
        kwargs.update(actuator_cfg.model_extra)

    return cast(
        Actuator,
        registry.create("actuator", actuator_cfg.type, actuator_cfg.name, **kwargs),
    )


def _create_controller(
    registry: Any,
    controller_cfg: ControllerConfig,
) -> Controller:
    """Create controller from config.

    Args:
        registry: The component registry.
        controller_cfg: Controller configuration.

    Returns:
        Instantiated controller.
    """
    kwargs: dict[str, Any] = {}

    # Add setpoint if specified
    if controller_cfg.setpoint is not None:
        kwargs["setpoint"] = controller_cfg.setpoint

    # PID-specific parameters
    if controller_cfg.type == "pid":
        kwargs["kp"] = controller_cfg.kp
        kwargs["ki"] = controller_cfg.ki
        kwargs["kd"] = controller_cfg.kd
        kwargs["output_limits"] = controller_cfg.output_limits
        kwargs["anti_windup"] = controller_cfg.anti_windup

    # Add extra fields (type-specific params like hysteresis, stages)
    if controller_cfg.model_extra:
        kwargs.update(controller_cfg.model_extra)

    return cast(
        Controller,
        registry.create(
            "controller", controller_cfg.type, controller_cfg.name, **kwargs
        ),
    )


def _create_modifier(
    registry: Any,
    modifier_cfg: ModifierConfig,
) -> CoveringMaterial | ThermalMass:
    """Create modifier from config.

    Args:
        registry: The component registry.
        modifier_cfg: Modifier configuration.

    Returns:
        Instantiated modifier.
    """
    # Build kwargs from extra fields
    kwargs: dict[str, Any] = {}
    if modifier_cfg.model_extra:
        kwargs.update(modifier_cfg.model_extra)

    # Note: cast uses string type annotation to avoid runtime import
    return cast(
        "CoveringMaterial | ThermalMass",
        registry.create("modifier", modifier_cfg.type, modifier_cfg.name, **kwargs),
    )
