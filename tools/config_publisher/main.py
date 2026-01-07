from __future__ import annotations

from .config import load_config
from .publisher import publish_all, reports_to_json


def main() -> None:
    cfg = load_config()
    reports = publish_all(cfg)
    print("✅ Published configs:")
    print(reports_to_json(reports))


if __name__ == "__main__":
    main()
