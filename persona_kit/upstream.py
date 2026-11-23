"""上游线路池。

一个 persona-kit 可以挂多条上游。某条 429 或者 5xx，自动换下一条。
顺序按 priority 排，同优先级按配置文件里的先后。
"""

from __future__ import annotations

import json
import os
import threading
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

RETRYABLE = (408, 409, 425, 429, 500, 502, 503, 504)


@dataclass
class Upstream:
    name: str
    base_url: str
    model: str
    api_key: str = ""
    priority: int = 100
    timeout: float = 120.0

    def url(self) -> str:
        base = self.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return base + "/chat/completions"

    def headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = "Bearer " + self.api_key
        return h


@dataclass
class Attempt:
    upstream: str = ""
    status: int = 0
    ms: int = 0
    error: str = ""


class UpstreamPool:
    def __init__(self, upstreams: list[Upstream]):
        self.upstreams = sorted(upstreams, key=lambda u: (u.priority,))
        self._lock = threading.Lock()
        self._state: dict[str, dict] = {
            u.name: {"ok": False, "status": 0, "ms": 0, "last": "", "error": ""} for u in self.upstreams
        }

    def order(self) -> list[Upstream]:
        return list(self.upstreams)

    def mark(self, name: str, ok: bool, status: int, ms: int, error: str = "") -> None:
        with self._lock:
            self._state[name] = {
                "ok": ok,
                "status": status,
                "ms": ms,
                "last": time.strftime("%Y-%m-%d %H:%M:%S"),
                "error": error,
            }

    def status(self) -> list[dict]:
        with self._lock:
            return [{"name": u.name, "model": u.model, "base_url": u.base_url, **self._state.get(u.name, {})}
                    for u in self.upstreams]

    def chat(self, up: Upstream, payload: dict, timeout: float | None = None) -> tuple[int, bytes, dict]:
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(up.url(), data=body, headers=up.headers())
        t0 = time.time()
        try:
            with urllib.request.urlopen(req, timeout=timeout or up.timeout) as r:
                data = r.read()
                self.mark(up.name, True, r.status, int((time.time() - t0) * 1000))
                return r.status, data, dict(r.headers)
        except urllib.error.HTTPError as e:
            data = e.read()
            self.mark(up.name, False, e.code, int((time.time() - t0) * 1000), data[:200].decode("utf-8", "ignore"))
            raise
        except Exception as e:
            self.mark(up.name, False, 0, int((time.time() - t0) * 1000), str(e)[:200])
            raise


def load_pool(path: str | Path) -> UpstreamPool:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError("找不到上游配置：" + str(p))
    data = json.loads(p.read_text(encoding="utf-8"))
    items = data.get("upstreams") if isinstance(data, dict) else data
    if not items:
        raise ValueError("上游配置里一条线路都没有")
    ups = []
    for i, it in enumerate(items):
        env_name = it.get("api_key_env") or ""
        key = it.get("api_key") or (os.environ.get(env_name, "") if env_name else "")
        ups.append(
            Upstream(
                name=str(it.get("name") or ("upstream-%d" % i)),
                base_url=str(it.get("base_url") or "").strip(),
                model=str(it.get("model") or ""),
                api_key=key,
                priority=int(it.get("priority", 100 + i)),
                timeout=float(it.get("timeout", 120)),
            )
        )
    return UpstreamPool(ups)