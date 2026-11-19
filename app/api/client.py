"""Small standard-library client used by Streamlit to read the REST API."""
import json
import os
from urllib.error import URLError, HTTPError
from urllib.request import urlopen

def list_api_events(base_url: str | None = None, user_id: str = "local-user") -> list[dict]:
    base_url = base_url or os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    url = f"{base_url.rstrip('/')}/events?user_id={user_id}"
    try:
        with urlopen(url, timeout=3) as response:
            result = json.loads(response.read().decode("utf-8"))
    except (URLError, HTTPError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("FastAPI is unavailable. Start it with `python -m uvicorn app.api.main:app --reload`.") from exc
    if not isinstance(result, list):
        raise RuntimeError("FastAPI returned an unexpected event list.")
    return result
