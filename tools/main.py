from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Literal, Optional

# Import tool entrypoints
from tools.config_publisher.main import main as publish_configs_main
from tools.ingestion_requester.main import main as request_ingestion_main
from tools.smoke_tests.main import main as smoke_tests_main


ActionName = Literal[
    "publish_configs",
    "request_ingestion",
    "smoke_tests",
]


@dataclass(frozen=True)
class Step:
    name: ActionName
    enabled: bool = True


def _actions() -> Dict[ActionName, Callable[[], None]]:
    return {
        "publish_configs": publish_configs_main,
        "request_ingestion": request_ingestion_main,
        "smoke_tests": smoke_tests_main,
    }


def run_plan(plan: List[Step]) -> None:
    actions = _actions()

    for step in plan:
        if not step.enabled:
            print(f"⏭️  Skipping: {step.name}")
            continue

        if step.name not in actions:
            raise ValueError(f"Unknown action: {step.name}")

        print("\n" + "=" * 80)
        print(f"▶️  Running: {step.name}")
        print("=" * 80)

        actions[step.name]()

        print(f"✅ Done: {step.name}")


def main() -> None:
    """
    ✅ Pas d’args CLI.
    Pour “manipuler” le comportement, modifie le PLAN ci-dessous.
    """
    PLAN: List[Step] = [
        Step(name="publish_configs", enabled=True),
        Step(name="request_ingestion", enabled=True),
        Step(name="smoke_tests", enabled=False),
    ]

    run_plan(PLAN)


if __name__ == "__main__":
    main()
