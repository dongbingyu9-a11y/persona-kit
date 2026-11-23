#!/usr/bin/env python3
"""persona-kit 服务端：把档案挂到任何 OpenAI 兼容接口前面。

    python3 -m persona_kit.cli serve --persona personas/zora.json --upstreams upstreams.json

客户端把 base_url 指到 http://127.0.0.1:8080/v1 就行。
"""

from __future__ import annotations

import json
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .profile import Persona
from .prompt import build_system_prompt, inject_messages
from .upstream import RETRYABLE, UpstreamPool


class Handler(BaseHTTPRequestHandler):
    server_version = "persona-kit"
    protocol_version = "HTTP/1.1"

    persona: Persona
    pool: UpstreamPool
    verbose: bool = False

    def log_message(self, fmt, *args):
        if getattr(self.server, "verbose", False):
            print("[persona-kit] " + fmt % args)

    def _json(self, code: int, obj) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0].rstrip("/")
        if path in ("", "/health"):
            self._json(200, {"ok": True, "persona": self.persona.name, "upstreams": self.pool.status()})
        elif path == "/profile":
            self._json(200, self.persona.data)
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")
        if path not in ("/v1/chat/completions", "/chat/completions"):
            return self._json(404, {"error": "not found"})

        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            return self._json(400, {"error": "请求体不是合法 JSON"})
        if not isinstance(payload, dict):
            return self._json(400, {"error": "请求体必须是对象"})

        msgs = payload.get("messages")
        if not isinstance(msgs, list) or not msgs:
            return self._json(400, {"error": "messages 不能为空"})

        payload["messages"] = inject_messages(
            msgs, build_system_prompt(self.persona), self.persona.marker
        )
        payload.pop("stream_options", None)

        attempts = []
        for up in self.pool.order():
            try:
                status, data, headers = self.pool.chat(up, payload)
            except urllib.error.HTTPError as e:
                attempts.append({"upstream": up.name, "status": e.code})
                if e.code in RETRYABLE:
                    continue
                return self._json(e.code, {"error": {"message": "上游返回错误", "upstream": up.name,
                                                      "detail": e.read()[:500].decode("utf-8", "ignore")}})
            except Exception as e:
                attempts.append({"upstream": up.name, "error": str(e)[:160]})
                continue
            ctype = headers.get("Content-Type", "application/json; charset=utf-8")
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return

        self._json(502, {
            "error": {"message": "所有上游都没通", "attempts": attempts},
            "hint": "跑一次 GET /health 看每条线的状态",
        })


def serve(persona: Persona, pool: UpstreamPool, host: str = "127.0.0.1", port: int = 8080,
          verbose: bool = False) -> None:
    handler = type("BoundHandler", (Handler,), {"persona": persona, "pool": pool, "verbose": verbose})
    srv = ThreadingHTTPServer((host, port), handler)
    srv.daemon_threads = True
    srv.verbose = verbose
    print("persona-kit 起来了：persona=%s  port=%d  上游 %d 条" % (persona.name, port, len(pool.upstreams)))
    for u in pool.order():
        print("  - %s  %s  %s" % (u.name, u.model, u.base_url))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n停了。")
    finally:
        srv.server_close()