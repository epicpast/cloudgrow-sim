"""Greenhouse simulation engine.

The engine orchestrates the simulation loop:
1. Update exterior conditions from weather source
2. Read all sensors
3. Execute all controllers
4. Apply actuator commands
5. Calculate physics (solar gain, conduction, ventilation)
6. Update interior state
7. Emit telemetry events
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import TYPE_CHECKING, Any, NamedTuple

from cloudgrow_sim.core.events import (
    Event,
    EventType,
    get_event_bus,
)
from cloudgrow_sim.core.state import (
    AirState,
    GreenhouseState,
)
from cloudgrow_sim.physics.constants import (
    C_P_DRY_AIR,
    STANDARD_AIR_DENSITY,
    STEFAN_BOLTZMANN,
)
from cloudgrow_sim.physics.heat_transfer import (
    conduction_heat_transfer,
    sky_temperature,
)
from cloudgrow_sim.physics.psychrometrics import (
    humidity_ratio,
    relative_humidity,
)
from cloudgrow_sim.simulation.weather import SyntheticWeatherSource, WeatherSource

if TYPE_CHECKING:
    from cloudgrow_sim.components.modifiers.covering import CoveringMaterial
    from cloudgrow_sim.components.modifiers.thermal_mass import ThermalMass
    from cloudgrow_sim.core.base import Actuator, Controller, Sensor


class SimulationStatus(str, Enum):
    """Simulation status states."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


# Maximum temperature change rate (C/s)
# This physical limit prevents unrealistic temperature jumps during simulation.
# Derivation: A well-insulated greenhouse with typical thermal mass (soil, plants,
# structure) has a thermal time constant of 15-30 minutes. Even under extreme
# conditions (full heating/cooling capacity), temperature changes rarely exceed
# 0.1 C/s. This value acts as a safety bound for numerical stability.
# Reference: ASHRAE Handbook - HVAC Applications (2019), Chapter 24
_MAX_TEMP_CHANGE_RATE: float = 0.1  # C/s


@dataclass
class SimulationConfig:
    """Configuration for simulation engine.

    Attributes:
        time_step: Simulation time step in seconds.
        start_time: Simulation start datetime.
        end_time: Simulation end datetime (None for indefinite).
        real_time_factor: Speed multiplier (1.0 = real-time, 0 = fast as possible).
        emit_events: Whether to emit events to event bus.
        emit_interval: Minimum interval between event emissions in steps.
    """

    time_step: float = 60.0  # seconds
    start_time: datetime = field(
        default_factory=lambda: datetime.now(UTC).replace(
            hour=6, minute=0, second=0, microsecond=0
        )
    )
    end_time: datetime | None = None
    real_time_factor: float = 0.0  # 0 = fast as possible
    emit_events: bool = True
    emit_interval: int = 1  # Emit every N steps


@dataclass
class SimulationStats:
    """Statistics from simulation run.

    Attributes:
        steps_completed: Number of time steps completed.
        simulation_time: Total simulated time.
        wall_time: Actual elapsed time.
        avg_step_time: Average wall time per step.
    """

    steps_completed: int = 0
    simulation_time: timedelta = field(default_factory=timedelta)
    wall_time: timedelta = field(default_factory=timedelta)

    @property
    def avg_step_time(self) -> float:
        """Average wall time per step in milliseconds."""
        if self.steps_completed == 0:
            return 0.0
        return self.wall_time.total_seconds() * 1000 / self.steps_completed


# Effective emissivity of greenhouse system for longwave radiation
# This represents the combined effect of:
# - Covering material emissivity (polyethylene ~0.8, glass ~0.9)
# - Interior surface emissivity
# - View factor to sky (typically 0.1-0.3 for gabled structures)
# The low value (0.1) accounts for the covering reducing radiative heat loss.
# Reference: ASHRAE Handbook-Fundamentals (2021), Chapter 4
_GREENHOUSE_EFFECTIVE_EMISSIVITY: float = 0.1


class ActuatorTotals(NamedTuple):
    """Aggregated totals from all actuator effects.

    Attributes:
        ventilation_rate: Total ventilation rate in m^3/s.
        heating: Total heating power in W.
        cooling: Total evaporative cooling in W.
        humidity_addition: Total humidity addition rate in kg/s.
        co2_injection: Total CO2 injection rate in m^3/s of pure CO2.
    """

    ventilation_rate: float
    heating: float
    cooling: float
    humidity_addition: float
    co2_injection: float


class SimulationEngine:
    """Main greenhouse simulation engine.

    Orchestrates the simulation loop, managing sensors, controllers,
    actuators, and physics calculations.
    """

    def __init__(
        self,
        state: GreenhouseState,
        weather: WeatherSource | None = None,
        config: SimulationConfig | None = None,
    ) -> None:
        """Initialize simulation engine.

        Args:
            state: Initial greenhouse state.
            weather: Weather data source.
            config: Simulation configuration.
        """
        self._state = state
        self._weather = weather or SyntheticWeatherSource()
        self._config = config or SimulationConfig()

        self._sensors: list[Sensor] = []
        self._actuators: list[Actuator] = []
        self._controllers: list[Controller] = []
        self._modifiers: list[CoveringMaterial | ThermalMass] = []

        self._status = SimulationStatus.IDLE
        self._current_time = self._config.start_time
        self._stats = SimulationStats()
        self._step_count = 0

        self._event_bus = get_event_bus()

    @property
    def state(self) -> GreenhouseState:
        """Current greenhouse state."""
        return self._state

    @property
    def status(self) -> SimulationStatus:
        """Current simulation status."""
        return self._status

    @property
    def current_time(self) -> datetime:
        """Current simulation time."""
        return self._current_time

    @property
    def stats(self) -> SimulationStats:
        """Simulation statistics."""
        return self._stats

    def add_sensor(self, sensor: Sensor) -> None:
        """Add a sensor to the simulation."""
        self._sensors.append(sensor)

    def add_actuator(self, actuator: Actuator) -> None:
        """Add an actuator to the simulation."""
        self._actuators.append(actuator)

    def add_controller(self, controller: Controller) -> None:
        """Add a controller to the simulation."""
        self._controllers.append(controller)

    def add_modifier(self, modifier: CoveringMaterial | ThermalMass) -> None:
        """Add a climate modifier to the simulation."""
        self._modifiers.append(modifier)

    def _update_exterior_conditions(self) -> None:
        """Update exterior conditions from weather source."""
        conditions = self._weather.get_conditions(self._current_time)

        self._state = GreenhouseState(
            interior=self._state.interior,
            exterior=AirState(
                temperature=conditions.temperature,
                humidity=conditions.humidity,
                pressure=conditions.pressure,
                co2_ppm=self._state.exterior.co2_ppm,
            ),
            time=self._current_time,
            location=self._state.location,
            geometry=self._state.geometry,
            covering=self._state.covering,
            solar_radiation=conditions.solar_radiation,
            wind_speed=conditions.wind_speed,
            wind_direction=conditions.wind_direction,
        )

    def _read_sensors(self) -> dict[str, dict[str, float]]:
        """Read all sensors and return readings."""
        readings: dict[str, dict[str, float]] = {}

        for sensor in self._sensors:
            if sensor.enabled:
                sensor.update(self._config.time_step, self._state)
                readings[sensor.name] = sensor.last_reading

        return readings

    def _execute_controllers(
        self, sensor_readings: dict[str, dict[str, float]]
    ) -> dict[str, float]:
        """Execute all controllers and return outputs.

        Args:
            sensor_readings: Dictionary of sensor readings (reserved for future use).
                Currently unused but will enable sensor-to-controller linkage
                for closed-loop control in a future version.
                See: https://github.com/cloudgrow-sim/cloudgrow-sim/issues/42

        Returns:
            Dictionary mapping controller names to their output values.
        """
        # M1 Fix: Document the parameter's future purpose instead of just deleting.
        # The sensor_readings parameter is intentionally accepted but unused,
        # reserved for planned sensor-controller binding feature.
        del sensor_readings  # Reserved for future sensor-controller linkage (issue #42)

        outputs: dict[str, float] = {}

        for controller in self._controllers:
            if controller.enabled:
                controller.update(self._config.time_step, self._state)
                outputs[controller.name] = controller.output

        return outputs

    def _apply_actuator_outputs(
        self, controller_outputs: dict[str, float]
    ) -> dict[str, dict[str, Any]]:
        """Apply controller outputs to actuators and get effects."""
        del controller_outputs  # Reserved for future controller-actuator linkage
        effects: dict[str, dict[str, Any]] = {}

        for actuator in self._actuators:
            if actuator.enabled:
                actuator.update(self._config.time_step, self._state)
                effects[actuator.name] = actuator.get_effect(self._state)

        return effects

    # =========================================================================
    # Physics calculation methods (ARCH-3 refactoring)
    # =========================================================================

    def _aggregate_actuator_effects(
        self, actuator_effects: dict[str, dict[str, Any]]
    ) -> ActuatorTotals:
        """Aggregate all actuator effects into totals.

        Args:
            actuator_effects: Dictionary of actuator effects keyed by actuator name.

        Returns:
            ActuatorTotals with summed values for each effect type.
        """
        total_ventilation = 0.0
        total_heating = 0.0
        total_cooling = 0.0
        total_humidity = 0.0
        total_co2 = 0.0

        for effect in actuator_effects.values():
            if "ventilation_rate" in effect:
                total_ventilation += effect["ventilation_rate"]
            if "heat_output" in effect:
                total_heating += effect["heat_output"]
            if "evaporative_cooling" in effect:
                total_cooling += effect["evaporative_cooling"]
            if "humidity_addition_rate" in effect:
                total_humidity += effect["humidity_addition_rate"]
            if "co2_injection_rate" in effect:
                total_co2 += effect["co2_injection_rate"]

        return ActuatorTotals(
            ventilation_rate=total_ventilation,
            heating=total_heating,
            cooling=total_cooling,
            humidity_addition=total_humidity,
            co2_injection=total_co2,
        )

    def _calculate_heat_balance(self, totals: ActuatorTotals) -> float:
        """Calculate net heat flux from all sources and sinks.

        Includes solar gain, conduction loss, ventilation exchange,
        sky radiation loss, and actuator heating/cooling.

        Args:
            totals: Aggregated actuator effect totals.

        Returns:
            Net heat flux in Watts (positive = heating).
        """
        geom = self._state.geometry
        covering = self._state.covering
        t_int = self._state.interior.temperature
        t_ext = self._state.exterior.temperature
        rh_ext = self._state.exterior.humidity

        # 1. Solar heat gain
        solar_transmitted = (
            self._state.solar_radiation * covering.transmittance_solar * geom.floor_area
        )

        # 2. Conduction heat loss through covering
        q_conduction = conduction_heat_transfer(
            covering.u_value,
            geom.wall_area + geom.roof_area,
            t_int,
            t_ext,
        )

        # 3. Ventilation heat exchange
        # Sensible heat from ventilation (Q = m_dot * cp * dT)
        # Reference: ASHRAE Handbook-Fundamentals (2021), Chapter 18, Eq. 15
        # Q_sensible = rho * V_dot * c_p * (T_in - T_out)
        # where:
        #   rho = air density (kg/m^3)
        #   V_dot = volumetric flow rate (m^3/s)
        #   c_p = specific heat of dry air (J/(kg*K))
        #   T_in, T_out = inlet/outlet temperatures (C)
        q_ventilation = (
            totals.ventilation_rate
            * STANDARD_AIR_DENSITY  # kg/m^3
            * C_P_DRY_AIR  # J/(kg*K)
            * (t_int - t_ext)  # temperature difference (C)
        )

        # 4. Sky radiation loss (Stefan-Boltzmann law)
        # Reference: ASHRAE Handbook-Fundamentals (2021), Chapter 4
        # Q_rad = epsilon * sigma * A * (T_surface^4 - T_sky^4)
        # The effective sky temperature is calculated using the Berdahl-Fromberg
        # correlation (see heat_transfer.sky_temperature)
        t_sky = sky_temperature(t_ext, rh_ext, cloud_cover=0.3)
        q_radiation = (
            _GREENHOUSE_EFFECTIVE_EMISSIVITY
            * STEFAN_BOLTZMANN
            * geom.roof_area
            * ((t_int + 273.15) ** 4 - (t_sky + 273.15) ** 4)
        )

        # Net heat flux
        q_net = (
            solar_transmitted
            + totals.heating
            - q_conduction
            - q_ventilation
            - q_radiation
            - totals.cooling
        )

        return q_net

    def _apply_temperature_change(self, q_net: float) -> float:
        """Apply temperature change based on net heat flux.

        Calculates temperature change using thermal mass and applies
        rate limiting and clamping for physical realism.

        Args:
            q_net: Net heat flux in Watts.

        Returns:
            New interior temperature in degrees Celsius.
        """
        dt = self._config.time_step
        geom = self._state.geometry
        t_int = self._state.interior.temperature

        # Temperature change: dT = Q * dt / (m * cp)
        air_mass = geom.volume * STANDARD_AIR_DENSITY  # kg
        dt_temp = q_net * dt / (air_mass * C_P_DRY_AIR)

        # M4 Fix: Scale temperature change limit by time step
        # Maximum change is proportional to dt, ensuring physically realistic
        # behavior regardless of simulation time step size.
        # At dt=60s: max change = 6.0 C (was fixed at 5.0 C)
        # At dt=1s: max change = 0.1 C (physically realistic)
        max_temp_change = _MAX_TEMP_CHANGE_RATE * dt
        dt_temp = max(-max_temp_change, min(max_temp_change, dt_temp))
        new_temp = t_int + dt_temp
        new_temp = max(-50.0, min(60.0, new_temp))  # AirState valid range

        return new_temp

    def _calculate_moisture_balance(
        self, totals: ActuatorTotals, new_temp: float
    ) -> float:
        """Calculate new relative humidity from moisture balance.

        Accounts for ventilation moisture exchange and humidification.

        Args:
            totals: Aggregated actuator effect totals.
            new_temp: New interior temperature for RH calculation.

        Returns:
            New relative humidity percentage (10-100%).
        """
        dt = self._config.time_step
        geom = self._state.geometry
        t_int = self._state.interior.temperature
        rh_int = self._state.interior.humidity
        t_ext = self._state.exterior.temperature
        rh_ext = self._state.exterior.humidity

        # Current absolute humidity
        w_int = humidity_ratio(t_int, rh_int)
        w_ext = humidity_ratio(t_ext, rh_ext)

        # Moisture from ventilation
        moisture_ventilation = (
            totals.ventilation_rate * STANDARD_AIR_DENSITY * (w_ext - w_int)
        )

        # New humidity ratio
        air_mass = geom.volume * STANDARD_AIR_DENSITY
        dw = (moisture_ventilation + totals.humidity_addition) * dt / air_mass
        new_w = max(0.001, w_int + dw)

        # Convert back to RH
        new_rh = relative_humidity(new_temp, new_w)
        new_rh = max(10.0, min(100.0, new_rh))

        return new_rh

    def _calculate_co2_balance(self, totals: ActuatorTotals) -> float:
        """Calculate new CO2 concentration from balance equation.

        Accounts for ventilation exchange and CO2 injection.

        Args:
            totals: Aggregated actuator effect totals.

        Returns:
            New CO2 concentration in ppm (200-5000).
        """
        dt = self._config.time_step
        geom = self._state.geometry
        co2_int = self._state.interior.co2_ppm
        co2_ext = self._state.exterior.co2_ppm

        # CO2 is in ppm (parts per million by volume)
        # For well-mixed gases, volume exchange rate equals mass exchange rate
        # d(CO2_ppm)/dt = (ventilation_rate / volume) * (CO2_ext - CO2_int)
        #                 + injection_rate
        #
        # CO2 ventilation exchange: volume flow rate * concentration difference
        # Result is in ppm * m^3/s, normalized by volume gives ppm/s
        co2_ventilation_rate = (
            totals.ventilation_rate * (co2_ext - co2_int) / geom.volume
        )

        # CO2 injection from actuators (in ppm/s contribution to the volume)
        # Actuators report injection_rate in appropriate units (e.g., mL/s of pure CO2)
        # Convert to ppm contribution: (injection_rate_m3_per_s / volume_m3) * 1e6
        # Assuming co2_injection is in m^3/s of pure CO2
        # ppm contribution = (m^3/s / volume_m^3) * 1e6
        co2_injection_rate = totals.co2_injection * 1e6 / geom.volume

        d_co2 = (co2_ventilation_rate + co2_injection_rate) * dt
        new_co2 = max(200.0, min(5000.0, co2_int + d_co2))

        return new_co2

    def _update_modifiers(self) -> None:
        """Update all climate modifiers (e.g., thermal mass)."""
        dt = self._config.time_step
        for modifier in self._modifiers:
            modifier.update(dt, self._state)

    def _update_interior_state(
        self, new_temp: float, new_rh: float, new_co2: float
    ) -> None:
        """Reconstruct greenhouse state with new interior values.

        Args:
            new_temp: New interior temperature in degrees Celsius.
            new_rh: New interior relative humidity percentage.
            new_co2: New interior CO2 concentration in ppm.
        """
        self._state = GreenhouseState(
            interior=AirState(
                temperature=new_temp,
                humidity=new_rh,
                pressure=self._state.interior.pressure,
                co2_ppm=new_co2,
            ),
            exterior=self._state.exterior,
            time=self._current_time,
            location=self._state.location,
            geometry=self._state.geometry,
            covering=self._state.covering,
            solar_radiation=self._state.solar_radiation,
            wind_speed=self._state.wind_speed,
            wind_direction=self._state.wind_direction,
        )

    def _calculate_physics(self, actuator_effects: dict[str, dict[str, Any]]) -> None:
        """Calculate physics and update interior state.

        Orchestrates the physics calculations by:
        1. Aggregating actuator effects
        2. Computing heat balance
        3. Applying temperature change
        4. Computing moisture balance
        5. Computing CO2 balance
        6. Updating climate modifiers
        7. Updating interior state

        Args:
            actuator_effects: Dictionary of actuator effects keyed by actuator name.
        """
        # Aggregate all actuator effects
        totals = self._aggregate_actuator_effects(actuator_effects)

        # Calculate heat balance and new temperature
        q_net = self._calculate_heat_balance(totals)
        new_temp = self._apply_temperature_change(q_net)

        # Calculate moisture balance (depends on new temperature for RH)
        new_rh = self._calculate_moisture_balance(totals, new_temp)

        # Calculate CO2 balance
        new_co2 = self._calculate_co2_balance(totals)

        # Update modifiers (thermal mass, etc.)
        self._update_modifiers()

        # Update state with new values
        self._update_interior_state(new_temp, new_rh, new_co2)

    # =========================================================================
    # Event emission methods
    # =========================================================================

    def _emit_telemetry(self) -> None:
        """Emit simulation telemetry events."""
        if not self._config.emit_events:
            return

        if self._step_count % self._config.emit_interval != 0:
            return

        self._event_bus.emit(
            Event(
                event_type=EventType.STATE_UPDATE,
                timestamp=self._current_time,
                source="engine",
                data={
                    "interior_temperature": self._state.interior.temperature,
                    "interior_humidity": self._state.interior.humidity,
                    "interior_co2": self._state.interior.co2_ppm,
                    "exterior_temperature": self._state.exterior.temperature,
                    "solar_radiation": self._state.solar_radiation,
                    "wind_speed": self._state.wind_speed,
                },
                message="State update",
            )
        )

    def step(self) -> bool:
        """Execute a single simulation step.

        Returns:
            True if simulation should continue, False if finished.
        """
        if self._status == SimulationStatus.STOPPED:
            return False

        if self._config.end_time and self._current_time >= self._config.end_time:
            self._status = SimulationStatus.STOPPED
            return False

        # 1. Update exterior from weather
        self._update_exterior_conditions()

        # 2. Read sensors
        sensor_readings = self._read_sensors()

        # 3. Execute controllers
        controller_outputs = self._execute_controllers(sensor_readings)

        # 4. Apply actuators
        actuator_effects = self._apply_actuator_outputs(controller_outputs)

        # 5. Calculate physics
        self._calculate_physics(actuator_effects)

        # 6. Emit telemetry
        self._emit_telemetry()

        # Advance time
        self._current_time += timedelta(seconds=self._config.time_step)
        self._step_count += 1
        self._stats.steps_completed += 1
        self._stats.simulation_time += timedelta(seconds=self._config.time_step)

        return True

    def run(self, steps: int | None = None) -> SimulationStats:
        """Run simulation for a number of steps or until end time.

        Args:
            steps: Number of steps to run (None = until end time).

        Returns:
            Simulation statistics.
        """
        import time

        self._status = SimulationStatus.RUNNING
        self._emit_start_event()

        start_wall = time.perf_counter()
        step_counter = 0

        try:
            while True:
                if steps is not None and step_counter >= steps:
                    break

                if not self.step():
                    break

                step_counter += 1

        except Exception as e:
            self._status = SimulationStatus.ERROR
            self._emit_error_event(str(e))
            raise

        finally:
            end_wall = time.perf_counter()
            self._stats.wall_time = timedelta(seconds=end_wall - start_wall)
            self._emit_stop_event()

        self._status = SimulationStatus.STOPPED
        return self._stats

    def _emit_start_event(self) -> None:
        """Emit simulation start event."""
        self._event_bus.emit(
            Event(
                event_type=EventType.SIMULATION_START,
                timestamp=self._current_time,
                source="engine",
                message=f"Simulation started at {self._current_time.isoformat()}",
            )
        )

    def _emit_stop_event(self) -> None:
        """Emit simulation stop event."""
        self._event_bus.emit(
            Event(
                event_type=EventType.SIMULATION_STOP,
                timestamp=self._current_time,
                source="engine",
                data={"stats": self._stats.__dict__},
                message=f"Simulation stopped after {self._stats.steps_completed} steps",
            )
        )

    def _emit_error_event(self, error: str) -> None:
        """Emit simulation error event."""
        self._event_bus.emit(
            Event(
                event_type=EventType.SIMULATION_ERROR,
                timestamp=self._current_time,
                source="engine",
                data={"error": error},
                message=f"Simulation error: {error}",
            )
        )

    def reset(self, initial_state: GreenhouseState | None = None) -> None:
        """Reset simulation to initial state.

        Args:
            initial_state: New initial state (or reuse current).
        """
        if initial_state:
            self._state = initial_state

        self._current_time = self._config.start_time
        self._step_count = 0
        self._stats = SimulationStats()
        self._status = SimulationStatus.IDLE

        # Reset all components
        for sensor in self._sensors:
            sensor.reset()
        for actuator in self._actuators:
            actuator.reset()
        for controller in self._controllers:
            controller.reset()
        for modifier in self._modifiers:
            modifier.reset()
