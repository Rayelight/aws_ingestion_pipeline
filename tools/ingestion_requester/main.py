from __future__ import annotations

from tools.ingestion_requester.requester import request_and_send, request_hourly


def main() -> None:
    # ---- Example 1: aggTrades (hourly runs) ----
    request_hourly(
        source="binance_api",
        entity="aggTrades",
        date="2025-01-06",
        endpoint="aggTrades",
        base_params={
            "symbol": "BTCUSDT",
            # limit/from_id sont optionnels; le tool peut set limit=1000 si placeholder
            "limit": 1000,
            "from_id": 0,
        },
        hours=[0],  # mets None pour 0..23
    )

    # ---- Example 2: klines (single run) ----
    # start_ms/end_ms sont required dans le contrat; si date/hour présents,
    # le tool les dérive automatiquement (fenêtre 60 min UTC) si absents.
    request_and_send(
        source="binance_api",
        entity="klines",
        params={
            "date": "2025-01-06",
            "hour": "00",
            "endpoint": "klines",
            "symbol": "BTCUSDT",
            "interval": "1m",
            "limit": 1000,
            # pas besoin de start_ms/end_ms : dérivés automatiquement
        },
    )


if __name__ == "__main__":
    main()
