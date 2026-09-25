"""Small HTTP helpers; requests is optional at runtime."""

from __future__ import annotations

import json
from urllib.request import Request, urlopen


def get_json(url: str, user_agent: str, timeout: int = 30):
    try:
        import requests
    except ImportError:
        request = Request(url, headers={"User-Agent": user_agent})
        with urlopen(request, timeout=timeout) as response:  # nosec: supplied constants
            return json.loads(response.read().decode("utf-8"))
    response = requests.get(url, headers={"User-Agent": user_agent}, timeout=timeout)
    response.raise_for_status()
    return response.json()


def get_text(url: str, user_agent: str, timeout: int = 30) -> str:
    try:
        import requests
    except ImportError:
        request = Request(url, headers={"User-Agent": user_agent})
        with urlopen(request, timeout=timeout) as response:  # nosec: supplied constants
            return response.read().decode("utf-8")
    response = requests.get(url, headers={"User-Agent": user_agent}, timeout=timeout)
    response.raise_for_status()
    return response.text
