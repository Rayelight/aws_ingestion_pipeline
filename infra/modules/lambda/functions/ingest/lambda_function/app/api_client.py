from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

import requests


@dataclass(frozen=True)
class ApiClient:
    timeout_sec: float
    max_retries: int

    def request_json(
        self,
        method: str,
        base_url: str,
        endpoint: str,
        headers: Dict[str, str],
        params: Dict[str, Any],
    ) -> Union[Dict[str, Any], list]:
        url = f"{base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        last_err: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                resp = requests.request(method=method, url=url, headers=headers, params=params, timeout=self.timeout_sec)
                if resp.status_code >= 400:
                    raise RuntimeError(f"API error {resp.status_code}: {resp.text[:200]}")
                return resp.json()
            except Exception as e:
                last_err = e
                if attempt >= self.max_retries:
                    break
                time.sleep(min(2 ** attempt, 8))

        raise RuntimeError(f"API request failed after retries: {last_err}")
