"""Pre-built simulation scenarios for testing and demonstration.

Scenarios provide complete greenhouse configurations that can be
quickly loaded and run for testing various simulation aspects.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from cloudgrow_sim.components.actuators.cooling import EvaporativePad
from cloudgrow_sim.components.actuators.fans import CirculationFan, ExhaustFan
from cloudgrow_sim.components.actuators.heating import UnitHeater
from cloudgrow_sim.components.actuators.vents import RoofVent
from cloudgrow_sim.components.modifiers.covering import CoveringMaterial
from cloudgrow_sim.components.modifiers.thermal_mass import ThermalMass
from cloudgrow_sim.components.sensors.humidity import CombinedTempHumiditySensor
from cloudgrow_sim.components.sensors.radiation import PARSensor, SolarRadiationSensor
from cloudgrow_sim.components.sensors.temperature import TemperatureSensor
from cloudgrow_sim.controllers.hysteresis import HysteresisController
from cloudgrow_sim.controllers.pid import PIDController
from cloudgrow_sim.controllers.staged import StagedController
from cloudgrow_sim.core.state import (
    COVERING_MATERIALS,
    AirState,
    GeometryType,
    GreenhouseGeometry,
    GreenhouseState,
    Location,
)
from cloudgrow_sim.simulation.engine import SimulationConfig, SimulationEngine
from cloudgrow_sim.simulation.weather import (
    SyntheticWeatherConfig,
    SyntheticWeatherSource,
)


@dataclass
class ScenarioResult:
    """Result from running a scenario.

    Attributes:
        scenario_name: Name of the scenario.
        final_state: Final greenhouse state.
        steps_completed: Number of steps completed.
        peak_temperature: Maximum interior temperature reached.
        min_temperature: Minimum interior temperature reached.
        avg_temperature: Average interior temperature.
    """

    scenario_name: str
    final_state: GreenhouseState
    steps_completed: int
    peak_temperature: float
    min_temperature: float
    avg_temperature: float


def create_small_hobby_greenhouse(
    location: Location | None = None,
) -> GreenhouseState:
    """Create a small hobby greenhouse state.

    10m x 6m single-span structure typical of backyard greenhouses.

    Args:
        location: Site location (defaults to mid-Atlantic US).

    Returns:
        Configured GreenhouseState.
    """
    loc = location or Location(
        latitude=37.5,
        longitude=-77.4,
        elevation=50.0,
        timezone_str="America/New_York",
    )

    geometry = GreenhouseGeometry(
        geometry_type=GeometryType.GABLE,
        length=10.0,
        width=6.0,
        height_eave=2.4,
        height_ridge=3.5,
        orientation=0.0,
    )

    return GreenhouseState(
        interior=AirState(temperature=20.0, humidity=60.0, co2_ppm=400.0),
        exterior=AirState(temperature=15.0, humidity=50.0, co2_ppm=400.0),
        time=datetime.now(UTC).replace(hour=6, minute=0, second=0, microsecond=0),
        location=loc,
        geometry=geometry,
        covering=COVERING_MATERIALS["double_polyethylene"],
        solar_radiation=0.0,
        wind_speed=2.0,
        wind_direction=180.0,
    )


def create_commercial_greenhouse(
    location: Location | None = None,
) -> GreenhouseState:
    """Create a commercial greenhouse state.

    30m x 10m multi-span structure typical of production greenhouses.

    Args:
        location: Site location (defaults to California).

    Returns:
        Configured GreenhouseState.
    """
    loc = location or Location(
        latitude=36.8,
        longitude=-119.8,
        elevation=100.0,
        timezone_str="America/Los_Angeles",
    )

    geometry = GreenhouseGeometry(
        geometry_type=GeometryType.GABLE,
        length=30.0,
        width=10.0,
        height_eave=3.0,
        height_ridge=5.0,
        orientation=0.0,
    )

    return GreenhouseState(
        interior=AirState(temperature=22.0, humidity=65.0, co2_ppm=400.0),
        exterior=AirState(temperature=18.0, humidity=45.0, co2_ppm=400.0),
        time=datetime.now(UTC).replace(hour=6, minute=0, second=0, microsecond=0),
        location=loc,
        geometry=geometry,
        covering=COVERING_MATERIALS["single_glass"],
        solar_radiation=0.0,
        wind_speed=3.0,
        wind_direction=270.0,
    )


def create_basic_scenario(
    duration_hours: float = 24.0,
    time_step: float = 60.0,
) -> SimulationEngine:
    """Create a basic greenhouse scenario with minimal components.

    Simple hobby greenhouse with:
    - Interior temperature sensor
    - Exhaust fan with hysteresis control

    Good for testing basic simulation functionality.

    Args:
        duration_hours: Simulation duration in hours.
        time_step: Time step in seconds.

    Returns:
        Configured SimulationEngine ready to run.
    """
    state = create_small_hobby_greenhouse()
    start = state.time
    end = start + timedelta(hours=duration_hours)

    config = SimulationConfig(
        time_step=time_step,
        start_time=start,
        end_time=end,
        emit_events=True,
        emit_interval=10,  # Every 10 steps
    )

    weather = SyntheticWeatherSource(
        SyntheticWeatherConfig(
            latitude=state.location.latitude,
            temp_mean=18.0,
            temp_amplitude_daily=8.0,
        )
    )

    engine = SimulationEngine(state, weather, config)

    # Add sensor
    temp_sensor = TemperatureSensor("temp_int", location="interior")
    engine.add_sensor(temp_sensor)

    # Add actuator
    exhaust_fan = ExhaustFan(
        "exhaust_1",
        max_flow_rate=1.0,  # m³/s
        power_consumption=500.0,
    )
    engine.add_actuator(exhaust_fan)

    # Add controller
    vent_controller = HysteresisController(
        "vent_control",
        setpoint=28.0,
        hysteresis=2.0,
        reverse_acting=True,
    )
    engine.add_controller(vent_controller)

    return engine


def create_full_climate_scenario(
    duration_hours: float = 24.0,
    time_step: float = 60.0,
) -> SimulationEngine:
    """Create a full greenhouse climate control scenario.

    Commercial greenhouse with complete climate control:
    - Multiple sensors (temp, humidity, PAR, solar)
    - Staged exhaust fans with PID control
    - Evaporative cooling
    - Unit heater with hysteresis
    - Roof vents
    - Thermal mass (water barrels)

    Args:
        duration_hours: Simulation duration in hours.
        time_step: Time step in seconds.

    Returns:
        Configured SimulationEngine ready to run.
    """
    state = create_commercial_greenhouse()
    start = state.time
    end = start + timedelta(hours=duration_hours)

    config = SimulationConfig(
        time_step=time_step,
        start_time=start,
        end_time=end,
        emit_events=True,
        emit_interval=5,
    )

    weather = SyntheticWeatherSource(
        SyntheticWeatherConfig(
            latitude=state.location.latitude,
            temp_mean=20.0,
            temp_amplitude_daily=10.0,
            humidity_mean=50.0,
            solar_max=1000.0,
        )
    )

    engine = SimulationEngine(state, weather, config)

    # ===== SENSORS =====

    # Interior sensors
    engine.add_sensor(
        CombinedTempHumiditySensor(
            "dht_int",
            location="interior",
            temp_noise_std_dev=0.2,
            humidity_noise_std_dev=2.0,
        )
    )
    engine.add_sensor(PARSensor("par_int", location="interior"))
    engine.add_sensor(SolarRadiationSensor("pyranometer"))

    # Exterior sensors
    engine.add_sensor(TemperatureSensor("temp_ext", location="exterior"))

    # ===== ACTUATORS =====

    # Exhaust fans (3 stages)
    engine.add_actuator(
        ExhaustFan("exhaust_1", max_flow_rate=2.0, power_consumption=750.0)
    )
    engine.add_actuator(
        ExhaustFan("exhaust_2", max_flow_rate=2.0, power_consumption=750.0)
    )
    engine.add_actuator(
        ExhaustFan("exhaust_3", max_flow_rate=2.0, power_consumption=750.0)
    )

    # Circulation fan
    engine.add_actuator(CirculationFan("circ_fan", power_consumption=200.0))

    # Evaporative pad
    engine.add_actuator(
        EvaporativePad(
            "evap_pad",
            pad_area=6.0,
            saturation_efficiency=0.85,
        )
    )

    # Unit heater
    engine.add_actuator(
        UnitHeater(
            "heater_1",
            heating_capacity=15000.0,  # 15 kW
            efficiency=0.9,
        )
    )

    # Roof vents
    engine.add_actuator(
        RoofVent(
            "vent_roof_1",
            width=2.0,
            height=0.5,
            height_above_floor=4.5,
        )
    )
    engine.add_actuator(
        RoofVent(
            "vent_roof_2",
            width=2.0,
            height=0.5,
            height_above_floor=4.5,
        )
    )

    # ===== CONTROLLERS =====

    # Cooling: PID for temperature control
    engine.add_controller(
        PIDController(
            "cooling_pid",
            kp=0.5,
            ki=0.1,
            kd=0.05,
            setpoint=26.0,
            output_limits=(0.0, 1.0),
            reverse_acting=True,
        )
    )

    # Heating: Hysteresis controller
    engine.add_controller(
        HysteresisController(
            "heating_control",
            setpoint=18.0,
            hysteresis=2.0,
            reverse_acting=False,
        )
    )

    # Fan staging
    engine.add_controller(
        StagedController(
            "fan_staging",
            stages=[
                (26.0, 0.33),
                (28.0, 0.66),
                (30.0, 1.0),
            ],
            hysteresis=0.5,
        )
    )

    # ===== MODIFIERS =====

    # Covering material
    engine.add_modifier(CoveringMaterial("covering", material="single_glass"))

    # Thermal mass (water barrels)
    engine.add_modifier(
        ThermalMass(
            "water_barrels",
            mass=2000.0,  # 10x 200L barrels
            specific_heat=4186.0,
            surface_area=15.0,
            initial_temperature=20.0,
        )
    )

    return engine


def create_winter_heating_scenario(
    duration_hours: float = 48.0,
) -> SimulationEngine:
    """Create a winter heating stress test scenario.

    Cold weather conditions to test heating system:
    - Very cold exterior temperatures
    - Low solar radiation
    - High wind
    - Large heating demand

    Args:
        duration_hours: Simulation duration in hours.

    Returns:
        Configured SimulationEngine ready to run.
    """
    loc = Location(
        latitude=42.3,
        longitude=-71.1,
        elevation=10.0,
        timezone_str="America/New_York",
    )

    state = GreenhouseState(
        interior=AirState(temperature=18.0, humidity=50.0, co2_ppm=400.0),
        exterior=AirState(temperature=-5.0, humidity=70.0, co2_ppm=400.0),
        time=datetime(2025, 1, 15, 6, 0, tzinfo=UTC),
        location=loc,
        geometry=GreenhouseGeometry(
            geometry_type=GeometryType.GABLE,
            length=20.0,
            width=8.0,
            height_eave=2.5,
            height_ridge=4.0,
        ),
        covering=COVERING_MATERIALS["polycarbonate_twin"],
        solar_radiation=0.0,
        wind_speed=5.0,
        wind_direction=0.0,
    )

    weather = SyntheticWeatherSource(
        SyntheticWeatherConfig(
            latitude=loc.latitude,
            temp_mean=-2.0,
            temp_amplitude_daily=5.0,
            temp_amplitude_annual=0.0,  # Fixed winter
            solar_max=400.0,  # Low winter sun
            wind_mean=4.0,
            cloud_cover_mean=0.6,
        )
    )

    config = SimulationConfig(
        time_step=60.0,
        start_time=state.time,
        end_time=state.time + timedelta(hours=duration_hours),
    )

    engine = SimulationEngine(state, weather, config)

    # Sensors
    engine.add_sensor(TemperatureSensor("temp_int", location="interior"))
    engine.add_sensor(TemperatureSensor("temp_ext", location="exterior"))

    # Main heater
    engine.add_actuator(
        UnitHeater(
            "main_heater",
            heating_capacity=25000.0,  # 25 kW
            efficiency=0.92,
        )
    )

    # Backup heater
    engine.add_actuator(
        UnitHeater(
            "backup_heater",
            heating_capacity=15000.0,  # 15 kW
            efficiency=0.88,
        )
    )

    # Heating controller
    engine.add_controller(
        PIDController(
            "heating_pid",
            kp=0.8,
            ki=0.2,
            kd=0.1,
            setpoint=18.0,
            output_limits=(0.0, 1.0),
            reverse_acting=False,
        )
    )

    # Thermal curtain effect modeled as better U-value covering
    engine.add_modifier(CoveringMaterial("covering", material="polycarbonate_twin"))

    return engine


def create_summer_cooling_scenario(
    duration_hours: float = 48.0,
) -> SimulationEngine:
    """Create a summer cooling stress test scenario.

    Hot weather conditions to test cooling system:
    - High exterior temperatures
    - High solar radiation
    - Calm wind
    - Large cooling demand

    Args:
        duration_hours: Simulation duration in hours.

    Returns:
        Configured SimulationEngine ready to run.
    """
    loc = Location(
        latitude=33.4,
        longitude=-112.0,
        elevation=350.0,
        timezone_str="America/Phoenix",
    )

    state = GreenhouseState(
        interior=AirState(temperature=28.0, humidity=40.0, co2_ppm=400.0),
        exterior=AirState(temperature=35.0, humidity=20.0, co2_ppm=400.0),
        time=datetime(2025, 7, 15, 6, 0, tzinfo=UTC),
        location=loc,
        geometry=GreenhouseGeometry(
            geometry_type=GeometryType.QUONSET,
            length=25.0,
            width=9.0,
            height_eave=2.0,
            height_ridge=4.5,
        ),
        covering=COVERING_MATERIALS["double_polyethylene"],
        solar_radiation=0.0,
        wind_speed=1.0,
        wind_direction=180.0,
    )

    weather = SyntheticWeatherSource(
        SyntheticWeatherConfig(
            latitude=loc.latitude,
            temp_mean=38.0,
            temp_amplitude_daily=12.0,
            temp_amplitude_annual=0.0,  # Fixed summer
            humidity_mean=25.0,
            solar_max=1100.0,
            wind_mean=2.0,
            cloud_cover_mean=0.1,
        )
    )

    config = SimulationConfig(
        time_step=60.0,
        start_time=state.time,
        end_time=state.time + timedelta(hours=duration_hours),
    )

    engine = SimulationEngine(state, weather, config)

    # Sensors
    engine.add_sensor(CombinedTempHumiditySensor("dht_int", location="interior"))
    engine.add_sensor(SolarRadiationSensor("pyranometer"))

    # Exhaust fans
    for i in range(4):
        engine.add_actuator(
            ExhaustFan(
                f"exhaust_{i + 1}",
                max_flow_rate=3.0,
                power_consumption=1000.0,
            )
        )

    # Evaporative pad
    engine.add_actuator(
        EvaporativePad(
            "evap_pad",
            pad_area=12.0,
            saturation_efficiency=0.85,
        )
    )

    # Staged fan controller
    engine.add_controller(
        StagedController(
            "fan_staging",
            stages=[
                (28.0, 0.25),
                (30.0, 0.50),
                (32.0, 0.75),
                (34.0, 1.0),
            ],
            hysteresis=1.0,
        )
    )

    # Evap pad controller
    engine.add_controller(
        HysteresisController(
            "evap_control",
            setpoint=30.0,
            hysteresis=2.0,
            reverse_acting=True,
        )
    )

    return engine
