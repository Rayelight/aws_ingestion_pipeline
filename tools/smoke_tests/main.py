from __future__ import annotations

from tools.ingestion_requester.requester import build_request_from_contract  # reuse run_id logic
from .config import load_config
from .runner import print_system_snapshot, wait_for_run


def main() -> None:
    cfg = load_config()

    # ✅ Définis ici les runs à tester (pas d’args)
    # Le run_id sera dérivé de la même manière que le requester.
    test_cases = [
        {
            "source": "binance_api",
            "entity": "aggTrades",
            "params": {"date": "2025-05-03", "hour": "00", "endpoint": "aggTrades", "symbol": "BTCUSDT"},
        },
        {
            "source": "binance_api",
            "entity": "klines",
            "params": {"date": "2025-05-03", "hour": "00", "endpoint": "klines", "symbol": "BTCUSDT", "interval": "1m"},
        },
    ]

    print_system_snapshot(cfg)

    all_ok = True
    for tc in test_cases:
        req = build_request_from_contract(source=tc["source"], entity=tc["entity"], params=tc["params"], run_id=None)
        print("\n=== Smoke test ===")
        print(f"dataset={req.source}/{req.entity} run_id={req.run_id}")

        res = wait_for_run(cfg, req.source, req.entity, req.run_id)

        print(f"DDB status: {res.ddb_status}")
        print(f"bronze_ok={res.bronze_ok} silver_ok={res.silver_ok}")
        if res.bronze_success_key:
            print(f"bronze_success: s3://{cfg.datalake_bucket}/{res.bronze_success_key}")
        if res.silver_success_key:
            print(f"silver_success: s3://{cfg.datalake_bucket}/{res.silver_success_key}")

        ok = (res.ddb_status == "SILVER_WRITTEN") or res.silver_ok
        if not ok:
            all_ok = False
            print("❌ Smoke test FAILED for this run (see status / missing artifacts).")
        else:
            print("✅ Smoke test OK.")

    print("\n=== Summary ===")
    print("✅ ALL OK" if all_ok else "❌ SOME FAILURES")


if __name__ == "__main__":
    main()
