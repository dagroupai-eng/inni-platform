from __future__ import annotations

from typing import Any, Dict, Optional

import requests


class NanoBananaClient:
    def __init__(self, token: str, base_url: str = "https://api.acedata.cloud"):
        self.token = token
        self.base_url = base_url.rstrip("/")

    def generate(
        self,
        prompt: str,
        count: int = 1,
        model: Optional[str] = None,
        aspect_ratio: Optional[str] = None,
        resolution: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"action": "generate", "prompt": prompt, "count": count}
        if model:
            payload["model"] = model
        if aspect_ratio:
            payload["aspect_ratio"] = aspect_ratio
        if resolution:
            payload["resolution"] = resolution
        return self._post(payload)

    def edit(
        self,
        prompt: str,
        image_urls: list[str],
        count: int = 1,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"action": "edit", "prompt": prompt, "image_urls": image_urls, "count": count}
        if model:
            payload["model"] = model
        return self._post(payload)

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.base_url}/nano-banana/images"
        headers = {
            "authorization": f"Bearer {self.token}",
            "accept": "application/json",
            "content-type": "application/json",
        }
        r = requests.post(url, json=payload, headers=headers, timeout=60)
        try:
            return r.json()
        except Exception:
            return {"success": False, "error": {"code": "invalid_json", "message": r.text}, "status_code": r.status_code}

