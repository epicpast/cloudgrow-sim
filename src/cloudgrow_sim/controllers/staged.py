"""Staged (multi-stage) controller implementation."""

from __future__ import annotations

from dataclasses import dataclass

from cloudgrow_sim.core.base import Controller
from cloudgrow_sim.core.registry import register_component


@dataclass
class Stage:
    """A single stage in a staged controller.

    Attributes:
        threshold: Process value threshold for this stage.
        output: Output value when this stage is active.
    """

    threshold: float
    output: float


@register_component("controller", "staged")
class StagedController(Controller):
    """Multi-stage on/off controller.

    Staged controllers activate different output levels based on
    process value thresholds. Common for fan staging, shade control, etc.

    Example: A 3-stage exhaust fan system might have:
    - Stage 1 (25%): Activate at 26°C
    - Stage 2 (50%): Activate at 28°C
    - Stage 3 (100%): Activate at 30°C

    Attributes:
        stages: List of Stage objects (threshold, output pairs).
        hysteresis: Temperature hysteresis to prevent rapid cycling.
    """

    def __init__(
        self,
        name: str,
        *,
        stages: list[tuple[float, float]] | None = None,
        hysteresis: float = 0.5,
        setpoint: float = 0.0,
        enabled: bool = True,
    ) -> None:
        """Initialize staged controller.

        Args:
            name: Unique identifier.
            stages: List of (threshold, output) tuples, sorted by threshold.
            hysteresis: Deadband for stage transitions.
            setpoint: Base setpoint (stages are relative to this).
            enabled: Whether controller is active.
        """
        super().__init__(name, setpoint=setpoint, enabled=enabled)
        self._hysteresis = hysteresis
        self._current_stage: int = -1  # -1 = no stage active

        # Convert tuples to Stage objects
        if stages:
            self._stages = [Stage(threshold=t, output=o) for t, o in stages]
            # Sort by threshold
            self._stages.sort(key=lambda s: s.threshold)
        else:
            self._stages = []

    @property
    def stages(self) -> list[Stage]:
        """List of stages."""
        return self._stages

    @property
    def current_stage(self) -> int:
        """Current active stage index (-1 = none)."""
        return self._current_stage

    @property
    def hysteresis(self) -> float:
        """Hysteresis value for stage transitions."""
        return self._hysteresis

    def add_stage(self, threshold: float, output: float) -> None:
        """Add a stage to the controller.

        Args:
            threshold: Process value threshold for activation.
            output: Output value when stage is active.
        """
        self._stages.append(Stage(threshold=threshold, output=output))
        self._stages.sort(key=lambda s: s.threshold)

    def clear_stages(self) -> None:
        """Remove all stages."""
        self._stages.clear()
        self._current_stage = -1

    def compute(
        self,
        process_value: float,
        dt: float,
    ) -> float:
        """Compute staged output based on process value.

        Args:
            process_value: Current measured value.
            dt: Time step duration (unused for staged control).

        Returns:
            Output value for the current stage.
        """
        del dt  # Unused

        if not self._stages:
            return 0.0

        # Determine which stages should be active
        # Use hysteresis to prevent rapid cycling
        new_stage = -1

        for i, stage in enumerate(self._stages):
            if self._current_stage >= i:
                # Already at or above this stage - use lower threshold
                effective_threshold = stage.threshold - self._hysteresis
            else:
                # Below this stage - use normal threshold
                effective_threshold = stage.threshold

            if process_value >= effective_threshold:
                new_stage = i

        self._current_stage = new_stage

        if self._current_stage >= 0:
            self._output = self._stages[self._current_stage].output
        else:
            self._output = 0.0

        return self._output

    def reset(self) -> None:
        """Reset controller to initial state."""
        super().reset()
        self._current_stage = -1
