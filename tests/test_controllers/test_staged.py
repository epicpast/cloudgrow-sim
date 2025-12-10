"""Tests for staged controller."""

from __future__ import annotations

from cloudgrow_sim.controllers import StagedController


class TestStagedController:
    """Tests for StagedController."""

    def test_no_stages(self) -> None:
        """No stages returns zero output."""
        ctrl = StagedController("staged")
        output = ctrl.compute(30.0, 0.1)
        assert output == 0.0

    def test_single_stage(self) -> None:
        """Single stage activation."""
        ctrl = StagedController(
            "staged",
            stages=[(25.0, 1.0)],
        )

        # Below threshold
        output = ctrl.compute(20.0, 0.1)
        assert output == 0.0
        assert ctrl.current_stage == -1

        # At or above threshold
        output = ctrl.compute(25.0, 0.1)
        assert output == 1.0
        assert ctrl.current_stage == 0

    def test_multiple_stages(self) -> None:
        """Multiple stage progression."""
        ctrl = StagedController(
            "staged",
            stages=[
                (25.0, 0.33),
                (27.0, 0.66),
                (29.0, 1.0),
            ],
        )

        # Below all stages
        assert ctrl.compute(20.0, 0.1) == 0.0
        assert ctrl.current_stage == -1

        # Stage 1
        assert ctrl.compute(25.0, 0.1) == 0.33
        assert ctrl.current_stage == 0

        # Stage 2
        assert ctrl.compute(27.5, 0.1) == 0.66
        assert ctrl.current_stage == 1

        # Stage 3
        assert ctrl.compute(30.0, 0.1) == 1.0
        assert ctrl.current_stage == 2

    def test_hysteresis(self) -> None:
        """Hysteresis prevents rapid cycling."""
        ctrl = StagedController(
            "staged",
            stages=[(25.0, 1.0)],
            hysteresis=1.0,
        )

        # Turn on at 25
        ctrl.compute(25.0, 0.1)
        assert ctrl.current_stage == 0

        # Stays on at 24.5 (within hysteresis)
        ctrl.compute(24.5, 0.1)
        assert ctrl.current_stage == 0

        # Turns off below hysteresis
        ctrl.compute(23.5, 0.1)
        assert ctrl.current_stage == -1

    def test_add_stage(self) -> None:
        """Dynamically add stage."""
        ctrl = StagedController("staged")

        ctrl.add_stage(25.0, 0.5)
        ctrl.add_stage(30.0, 1.0)

        assert len(ctrl.stages) == 2
        # Stages should be sorted
        assert ctrl.stages[0].threshold == 25.0
        assert ctrl.stages[1].threshold == 30.0

    def test_clear_stages(self) -> None:
        """Clear all stages."""
        ctrl = StagedController(
            "staged",
            stages=[(25.0, 0.5), (30.0, 1.0)],
        )

        ctrl.clear_stages()
        assert len(ctrl.stages) == 0

    def test_reset(self) -> None:
        """Reset clears current stage."""
        ctrl = StagedController(
            "staged",
            stages=[(25.0, 1.0)],
        )

        ctrl.compute(30.0, 0.1)
        assert ctrl.current_stage == 0

        ctrl.reset()
        assert ctrl.current_stage == -1


class TestStagedControllerFanApplication:
    """Tests simulating staged fan control."""

    def test_three_stage_fan(self) -> None:
        """Three-stage exhaust fan control."""
        ctrl = StagedController(
            "fan_stages",
            stages=[
                (26.0, 0.33),  # 1/3 fans at 26°C
                (28.0, 0.66),  # 2/3 fans at 28°C
                (30.0, 1.0),  # All fans at 30°C
            ],
            hysteresis=0.5,
        )

        # Morning: cool
        assert ctrl.compute(22.0, 0.1) == 0.0

        # Warming up
        assert ctrl.compute(26.0, 0.1) == 0.33

        # Hot midday
        assert ctrl.compute(31.0, 0.1) == 1.0

        # Cooling down - drops to lower stage when below threshold
        # Hysteresis is applied per-stage on the falling edge
        assert ctrl.compute(30.0, 0.1) == 1.0
        assert ctrl.compute(29.3, 0.1) == 0.66  # Below stage 3 (30.0), go to stage 2
        assert ctrl.compute(27.3, 0.1) == 0.33  # Below stage 2 (28.0), go to stage 1
