#!/usr/bin/env python
"""
Seed dispatcher for Tulia v2.

This script doesn't own any hard-coded curriculum data anymore. Instead, it
provides a small CLI that lets you run dedicated seed scripts (for example
`seed_moduleA_sample.py`) or any other seeds you register in the table below.

Usage examples:
    python seed_data.py --list                 # show available targets
    python seed_data.py module_a_sample        # run one target
    python seed_data.py --all                  # run everything in order

Add new seeds by dropping a file alongside this one and registering it in
`SEED_REGISTRY`. Each seed entry points to `<module>:<callable>` that will be
imported and executed.
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Iterable, List

BASE_DIR = Path(__file__).resolve().parent

# Ensure our project modules are importable before Django initialises.
sys.path.insert(0, str(BASE_DIR))

# Default to the local settings module unless the caller overrides it.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myProject.settings")

import django  # noqa: E402  (Django needs to load after we set DJANGO_SETTINGS_MODULE)

django.setup()


@dataclass(frozen=True)
class SeedTarget:
    """Represents a runnable seed target discovered by the dispatcher."""

    key: str
    import_path: str
    callable_name: str
    description: str = ""

    def load(self) -> Callable[[], None]:
        module = importlib.import_module(self.import_path)
        try:
            seed_callable = getattr(module, self.callable_name)
        except AttributeError as exc:  # pragma: no cover - safety net
            raise RuntimeError(
                f"Seed target '{self.key}' expects callable "
                f"'{self.callable_name}' in '{self.import_path}', "
                "but it was not found."
            ) from exc
        if not callable(seed_callable):
            raise RuntimeError(
                f"Seed target '{self.key}' resolved '{self.callable_name}' "
                f"in '{self.import_path}', but it is not callable."
            )
        return seed_callable  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Register available seed targets here. The key becomes the CLI argument.
# ---------------------------------------------------------------------------
SEED_REGISTRY: Dict[str, SeedTarget] = {
    "module_a_sample": SeedTarget(
        key="module_a_sample",
        import_path="seed_moduleA_sample",
        callable_name="main",
        description="Seeds Module A scaffolding (levels, lessons, sample superuser).",
    ),
    # Add additional entries like:
    # "module_b_sample": SeedTarget(
    #     key="module_b_sample",
    #     import_path="seed_moduleB_sample",
    #     callable_name="main",
    #     description="Seeds Module B curriculum and related fixtures.",
    # ),
}


def list_targets() -> None:
    if not SEED_REGISTRY:
        print("No seed targets registered. Add entries to SEED_REGISTRY to enable seeding.")
        return
    print("Available seed targets:\n")
    width = max(len(key) for key in SEED_REGISTRY) + 2
    for key, target in SEED_REGISTRY.items():
        description = target.description or "(no description provided)"
        print(f"  {key.ljust(width)}{description}")
    print("\nRun `python seed_data.py <target>` to execute an individual seed.")


def run_targets(target_keys: Iterable[str]) -> None:
    for key in target_keys:
        target = SEED_REGISTRY.get(key)
        if not target:
            raise SystemExit(f"Unknown seed target '{key}'. Run with --list to see options.")
        print(f"\n🌱 Running seed: {key}")
        seed_callable = target.load()
        seed_callable()
        print(f"✅ Finished: {key}")


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed dispatcher for Tulia v2.")
    parser.add_argument(
        "targets",
        nargs="*",
        help="One or more seed target keys to execute. Use --list to view options.",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List registered seed targets and exit.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run every registered seed target in registration order.",
    )
    return parser.parse_args(argv)


def main(argv: List[str] | None = None) -> None:
    args = parse_args(argv or sys.argv[1:])

    if args.list:
        list_targets()
        return

    if args.all:
        run_targets(SEED_REGISTRY.keys())
        return

    if not args.targets:
        list_targets()
        return

    run_targets(args.targets)


if __name__ == "__main__":
    main()

