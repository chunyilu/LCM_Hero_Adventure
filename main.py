#!/usr/bin/env python3
"""
LCM Hero Adventure — Main Entry Point.

A 2D Educational Math JRPG teaching Least Common Multiples (LCM) through:
- Mathematical Shield turn-based battles
- 4 pedagogical zones (Prime Pair, Overlapping Factors, Contained Multiples, Three-Number Rush)
- Short Division (短除法) & Multiples Listing Tutorial Fairy
- Adaptive Edge AI offline performance model
- Village Equipment Shop (Multiplier Sword, Prime Number Shield) & Princess Rescue Progression.
"""

from __future__ import annotations

import argparse

from mvc.controller import GameController


def main() -> None:
    parser = argparse.ArgumentParser(description="LCM Hero Adventure — 2D Educational JRPG")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run with a hidden window (for automated testing).",
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=None,
        help="Optional max frames to run before exiting cleanly.",
    )
    args = parser.parse_args()

    controller = GameController(headless=args.headless)
    controller.run(max_frames=args.frames)


if __name__ == "__main__":
    main()
