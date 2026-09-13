"""HTTP+JSON client for the CUMCM 2026 B-problem local simulator."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_BASE_URL = "http://127.0.0.1:2026"


class SimError(RuntimeError):
    def __init__(self, message: str, *, status: int | None = None, body: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status = status
        self.body = body or {}


def _decode(raw: bytes) -> dict[str, Any]:
    if not raw:
        return {}
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise SimError("simulator response is not a JSON object")
    return payload


class SimClient:
    def __init__(
        self,
        *,
        robot_id: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout_s: float = 5.0,
        opener=None,
    ) -> None:
        if not robot_id or not str(robot_id).strip():
            raise ValueError("robot_id (contest team id) is required")
        self.robot_id = str(robot_id).strip()
        self.base_url = base_url.rstrip("/")
        self.timeout_s = float(timeout_s)
        self._opener = opener or urlopen

    def _base(self, request_id: str) -> dict[str, Any]:
        return {"arena_id": "default", "robot_id": self.robot_id, "request_id": str(request_id)}

    def post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if path not in {"/enter", "/measure", "/clear", "/exit"}:
            raise ValueError(f"unknown path {path}")
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._opener(request, timeout=self.timeout_s) as response:
                body = _decode(response.read())
                status = getattr(response, "status", 200)
        except HTTPError as exc:
            raw = exc.read() if exc.fp is not None else b""
            try:
                body = _decode(raw)
            except Exception:
                body = {}
            raise SimError(f"HTTP {exc.code} {path}", status=exc.code, body=body) from exc
        except URLError as exc:
            raise SimError(f"simulator unreachable at {self.base_url}: {exc.reason}") from exc
        if status != 200:
            raise SimError(f"HTTP {status} {path}", status=status, body=body)
        return body

    def enter(self, request_id: str = "enter-1") -> dict[str, Any]:
        return self.post("/enter", self._base(request_id))

    def exit(self, request_id: str = "exit-1") -> dict[str, Any]:
        return self.post("/exit", self._base(request_id))

    def measure(self, request_id: str, x: float, y: float, channel: int) -> dict[str, Any]:
        payload = self._base(request_id)
        payload["position"] = {"x": float(x), "y": float(y)}
        payload["channel"] = int(channel)
        return self.post("/measure", payload)

    def clear(self, request_id: str, x: float, y: float, channel: int) -> dict[str, Any]:
        payload = self._base(request_id)
        payload["position"] = {"x": float(x), "y": float(y)}
        payload["channel"] = int(channel)
        return self.post("/clear", payload)
