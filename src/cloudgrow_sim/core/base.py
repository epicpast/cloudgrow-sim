"""Base protocols and abstract classes for greenhouse simulation components.

This module defines the core protocols that all components must implement:
- Component: Base protocol for all simulation components
- Sensor: Protocol for measurement devices
- Actuator: Protocol for controllable devices
- Controller: Protocol for control algorithms

All protocols use typing.Protocol for structural subtyping compatibility
with mypy strict mode.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

import numpy as np

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from numpy.random import Generator

    from cloudgrow_sim.core.state import GreenhouseState


class Component(ABC):
    """Base class for all simulation components.

    Components are the building blocks of the greenhouse simulation.
    Each component has a unique name and participates in the simulation
    loop via the update() method.

    Attributes:
        name: Unique identifier for this component.
        enabled: Whether this component is active in the simulation.
    """

    def __init__(self, name: str, *, enabled: bool = True) -> None:
        """Initialize component.

        Args:
            name: Unique identifier for this component.
            enabled: Whether this component is active. Defaults to True.
        """
        self._name = name
        self._enabled = enabled

    @property
    def name(self) -> str:
        """Unique identifier for this component."""
        return self._name

    @property
    def enabled(self) -> bool:
        """Whether this component is active in the simulation."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set component enabled state."""
        self._enabled = value

    @abstractmethod
    def update(self, dt: float, state: GreenhouseState) -> None:
        """Update component state for one simulation time step.

        Args:
            dt: Time step duration in seconds.
            state: Current greenhouse state (may be modified in-place).
        """

    def reset(self) -> None:  # noqa: B027
        """Reset component to initial state.

        Override in subclasses that maintain internal state.
        """


class Sensor(Component):
    """Base class for sensor components that measure environmental variables.

    Sensors read values from the greenhouse state and optionally add
    measurement noise to simulate real sensor behavior.

    Attributes:
        location: Where the sensor is placed ('interior', 'exterior', etc.).
        noise_std_dev: Standard deviation of Gaussian measurement noise.
        rng: Random number generator for reproducible noise.
    """

    def __init__(
        self,
        name: str,
        location: str = "interior",
        *,
        noise_std_dev: float = 0.0,
        enabled: bool = True,
        rng: Generator | None = None,
        seed: int | None = None,
    ) -> None:
        """Initialize sensor.

        Args:
            name: Unique identifier for this sensor.
            location: Sensor placement location.
            noise_std_dev: Measurement noise standard deviation.
            enabled: Whether this sensor is active.
            rng: NumPy random generator for reproducible simulations.
                If None and seed is provided, creates a new generator.
                If both None, creates a default generator (non-deterministic).
            seed: Seed for creating a new random generator if rng is None.
        """
        super().__init__(name, enabled=enabled)
        self._location = location
        self._noise_std_dev = noise_std_dev
        self._last_reading: dict[str, float] = {}

        # Initialize random generator for reproducible noise
        if rng is not None:
            self._rng = rng
        elif seed is not None:
            self._rng = np.random.default_rng(seed)
        else:
            self._rng = np.random.default_rng()
            if noise_std_dev > 0:
                logger.debug(
                    "Sensor '%s' using non-deterministic RNG (no seed provided). "
                    "Set seed parameter for reproducible results.",
                    name,
                )

    @property
    def location(self) -> str:
        """Sensor placement location."""
        return self._location

    @property
    def noise_std_dev(self) -> float:
        """Measurement noise standard deviation."""
        return self._noise_std_dev

    @property
    def last_reading(self) -> dict[str, float]:
        """Most recent sensor reading."""
        return self._last_reading.copy()

    @property
    def rng(self) -> Generator:
        """Random number generator for noise generation."""
        return self._rng

    def _add_noise(self, value: float, std_dev: float | None = None) -> float:
        """Add Gaussian noise to a value.

        Args:
            value: The true value to add noise to.
            std_dev: Standard deviation override. Uses noise_std_dev if None.

        Returns:
            Value with added noise.
        """
        sigma = std_dev if std_dev is not None else self._noise_std_dev
        if sigma > 0:
            return float(value + self._rng.normal(0, sigma))
        return value

    @abstractmethod
    def read(self, state: GreenhouseState) -> dict[str, float]:
        """Take a measurement from the current state.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary of measured values (e.g., {"temperature": 25.0}).
        """

    def update(self, dt: float, state: GreenhouseState) -> None:
        """Update sensor by taking a new reading.

        Args:
            dt: Time step duration in seconds (unused for sensors).
            state: Current greenhouse state.
        """
        del dt  # Unused
        if self.enabled:
            self._last_reading = self.read(state)


class Actuator(Component):
    """Base class for actuator components that modify the environment.

    Actuators receive control signals and affect the greenhouse state
    (e.g., fans change ventilation rate, heaters add heat).

    Attributes:
        output_limits: Tuple of (min, max) output values.
    """

    def __init__(
        self,
        name: str,
        *,
        output_limits: tuple[float, float] = (0.0, 1.0),
        enabled: bool = True,
    ) -> None:
        """Initialize actuator.

        Args:
            name: Unique identifier for this actuator.
            output_limits: Tuple of (min, max) output values.
            enabled: Whether this actuator is active.
        """
        super().__init__(name, enabled=enabled)
        self._output_limits = output_limits
        self._output: float = output_limits[0]

    @property
    def output_limits(self) -> tuple[float, float]:
        """Tuple of (min, max) output values."""
        return self._output_limits

    @property
    def output(self) -> float:
        """Current actuator output level."""
        return self._output

    def set_output(self, value: float) -> None:
        """Set actuator output, clamping to limits.

        Args:
            value: Desired output value.
        """
        min_val, max_val = self._output_limits
        self._output = max(min_val, min(max_val, value))

    @abstractmethod
    def get_effect(self, state: GreenhouseState) -> dict[str, float]:
        """Calculate the physical effect of this actuator.

        Args:
            state: Current greenhouse state.

        Returns:
            Dictionary of effects (e.g., {"heat_rate": 1000.0} for W).
        """

    def update(self, dt: float, state: GreenhouseState) -> None:
        """Apply actuator effects to the state.

        Args:
            dt: Time step duration in seconds.
            state: Current greenhouse state (modified in-place).
        """
        if self.enabled:
            self._apply_effect(dt, state)

    @abstractmethod
    def _apply_effect(self, dt: float, state: GreenhouseState) -> None:
        """Apply physical effect to greenhouse state.

        Args:
            dt: Time step duration in seconds.
            state: Current greenhouse state (modified in-place).
        """

    def reset(self) -> None:
        """Reset actuator to minimum output."""
        self._output = self._output_limits[0]


class Controller(Component):
    """Base class for control algorithm components.

    Controllers read process variables (from sensors) and compute
    output signals to drive actuators toward setpoints.

    Attributes:
        setpoint: Target value for the controlled variable.
    """

    def __init__(
        self,
        name: str,
        *,
        setpoint: float = 0.0,
        enabled: bool = True,
    ) -> None:
        """Initialize controller.

        Args:
            name: Unique identifier for this controller.
            setpoint: Initial target value.
            enabled: Whether this controller is active.
        """
        super().__init__(name, enabled=enabled)
        self._setpoint = setpoint
        self._output: float = 0.0
        self._connected_actuators: list[Actuator] = []

    @property
    def setpoint(self) -> float:
        """Target value for the controlled variable."""
        return self._setpoint

    @setpoint.setter
    def setpoint(self, value: float) -> None:
        """Set new setpoint value."""
        self._setpoint = value

    @property
    def output(self) -> float:
        """Current controller output."""
        return self._output

    def connect_actuator(self, actuator: Actuator) -> None:
        """Connect an actuator to receive this controller's output.

        Args:
            actuator: Actuator to control.
        """
        if actuator not in self._connected_actuators:
            self._connected_actuators.append(actuator)

    def disconnect_actuator(self, actuator: Actuator) -> None:
        """Disconnect an actuator.

        Args:
            actuator: Actuator to disconnect.
        """
        if actuator in self._connected_actuators:
            self._connected_actuators.remove(actuator)

    @abstractmethod
    def compute(
        self,
        process_value: float,
        dt: float,
    ) -> float:
        """Compute control output based on process value.

        Args:
            process_value: Current measured value of controlled variable.
            dt: Time step duration in seconds.

        Returns:
            Control output value.
        """

    def update(self, dt: float, state: GreenhouseState) -> None:
        """Update controller and connected actuators.

        Args:
            dt: Time step duration in seconds.
            state: Current greenhouse state.
        """
        if not self.enabled:
            return

        # Get process value (subclasses should override _get_process_value)
        pv = self._get_process_value(state)

        # Compute new output
        self._output = self.compute(pv, dt)

        # Apply to connected actuators
        for actuator in self._connected_actuators:
            actuator.set_output(self._output)

    def _get_process_value(self, state: GreenhouseState) -> float:
        """Get the process value from state.

        Override in subclasses to specify which state variable to control.

        Args:
            state: Current greenhouse state.

        Returns:
            Current value of the controlled variable.
        """
        # Default: use interior temperature
        return state.interior.temperature

    def reset(self) -> None:
        """Reset controller internal state."""
        self._output = 0.0


class ClimateModifier(Component):
    """Base class for passive elements affecting climate.

    Climate modifiers represent physical elements that affect heat transfer
    or light transmission without active control (e.g., covering materials,
    thermal mass).
    """

    @abstractmethod
    def get_properties(self) -> dict[str, Any]:
        """Get physical properties of this modifier.

        Returns:
            Dictionary of properties (e.g., {"u_value": 4.0, "transmittance": 0.8}).
        """

    def update(self, dt: float, state: GreenhouseState) -> None:
        """Update modifier state.

        Most modifiers are passive and don't need updates. Override if needed.

        Args:
            dt: Time step duration in seconds.
            state: Current greenhouse state.
        """
