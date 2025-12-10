"""Allow running as `python -m cloudgrow_sim`."""

from cloudgrow_sim.main import main

if __name__ == "__main__":
    raise SystemExit(main())
