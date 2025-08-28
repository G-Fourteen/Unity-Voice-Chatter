import logging
import random
import time
from typing import Any, Dict, List

import asyncio
import requests

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, config):
        self.config = config
        self.retry_attempts = 6
        self.retry_delay = 2

    def _request_json(self, method: str, url: str, **kwargs) -> Dict[str, Any] | str:
        """Perform an HTTP request and return the parsed JSON or an error string."""
        headers = kwargs.pop("headers", None)
        for attempt in range(self.retry_attempts):
            try:
                resp = requests.request(method, url, headers=headers, **kwargs)
                if resp.status_code == 200:
                    return resp.json()
                if resp.status_code in {429, 500, 502, 503, 504}:
                    delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 0.1)
                    logger.warning(
                        f"Retry {attempt + 1}/{self.retry_attempts} status {resp.status_code} wait {delay:.2f}s"
                    )
                    time.sleep(delay)
                    continue
                return f"Error: API returned status {resp.status_code} {resp.text}"
            except (requests.ConnectionError, requests.Timeout) as e:
                delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 0.1)
                logger.warning(
                    f"Retry {attempt + 1}/{self.retry_attempts} due to {e} wait {delay:.2f}s"
                )
                time.sleep(delay)
                continue
            except RuntimeError as e:
                if "Event loop is closed" in str(e):
                    logger.warning("Event loop closed, recreating loop and retrying")
                    asyncio.set_event_loop(asyncio.new_event_loop())
                    delay = self.retry_delay * (2 ** attempt) + random.uniform(0, 0.1)
                    time.sleep(delay)
                    continue
                logger.error(f"Unexpected runtime error {e}")
                return f"Error: Unexpected runtime error {e}"
            except Exception as e:
                logger.error(f"Unexpected exception {e}")
                return f"Error: Unexpected exception {e}"
        logger.error("API unreachable after retries")
        return "Error: Upstream API unreachable after retries"

    def fetch_models(self) -> List[Dict[str, str]]:
        headers = {"Authorization": f"Bearer {self.config.pollinations_token}"}
        result = self._request_json("GET", self.config.models_url, headers=headers, timeout=15)
        if isinstance(result, list):
            if all(isinstance(m, str) for m in result):
                return [{"name": m.strip()} for m in result]
            if all(isinstance(m, dict) and "name" in m for m in result):
                return [
                    {"name": m["name"].strip(), "description": m.get("description", "")}
                    for m in result
                ]
        return [{"name": "unity", "description": "Default unity model"}]

    def send_message(self, messages: list, model: str | None):
        if not model or not isinstance(model, str) or model.strip() == "":
            model = self.config.default_model
        logger.info(f"Using model: {model}")
        payload = {"messages": messages, "model": model}
        headers = {"Authorization": f"Bearer {self.config.pollinations_token}"}
        result = self._request_json(
            "POST", self.config.api_url, json=payload, headers=headers, timeout=30
        )
        if isinstance(result, str):
            return result
        try:
            return result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            return f"Error: Invalid response format {e}"
