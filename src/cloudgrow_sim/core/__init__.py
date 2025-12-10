"""Core module for greenhouse simulation framework.

This module provides the foundational classes and protocols for the simulation:
- Base protocols for components (sensors, actuators, controllers)
- State management for greenhouse environment
- Configuration loading and validation
- Component registry with plugin discovery
- Event system for state changes
"""

from cloudgrow_sim.core.base import (
    Actuator,
    Component,
    Controller,
    Sensor,
)
from cloudgrow_sim.core.events import Event, EventBus
from cloudgrow_sim.core.registry import get_registry, register_component
from cloudgrow_sim.core.state import (
    AirState,
    CoveringProperties,
    GreenhouseGeometry,
    GreenhouseState,
    Location,
)

__all__ = [
    # Protocols
    "Component",
    "Sensor",
    "Actuator",
    "Controller",
    # State
    "AirState",
    "GreenhouseState",
    "Location",
    "GreenhouseGeometry",
    "CoveringProperties",
    # Registry
    "register_component",
    "get_registry",
    # Events
    "Event",
    "EventBus",
]
