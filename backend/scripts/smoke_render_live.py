"""Live Render smoke test for deployed Week 2 backend.

Run from the repository root:

    python backend/scripts/smoke_render_live.py

This checks the deployed service without changing the frontend contract:
- GET /health
- GET /version
- OPTIONS /generate from the Week 2 Vercel preview origin
- POST /generate with a free-text product name
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "https://beautyagent-ai.onrender.com"
DEFAULT_ORIGIN = "https://beautyagent-ai-git-week2-jillk83s-projects.vercel.app"


@dataclass(frozen=True)
class SmokeResult:
    name: str
    passed: bool
    detail: str


def _request(
    method: str,
    url: str,
    *,
    origin: str | None = None,
    payload: dict[str, object] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, str], str]:
    headers = dict(extra_headers or {})
    body: bytes | None = None
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if origin:
        headers["Origin"] = origin

    request = Request(url, data=body, method=method, headers=headers)
    try:
        with urlopen(request, timeout=30) as response:
            return (
                response.status,
                dict(response.headers.items()),
                response.read().decode("utf-8"),
            )
    except HTTPError as exc:
        return (
            exc.code,
            dict(exc.headers.items()),
            exc.read().decode("utf-8"),
        )
    except URLError as exc:
        return 0, {}, str(exc)


def check_health(base_url: str) -> SmokeResult:
    status, _headers, body = _request("GET", f"{base_url}/health")
    passed = status == 200 and '"status":"ok"' in body.replace(" ", "")
    return SmokeResult("health", passed, f"HTTP {status} {body}")


def check_version(base_url: str) -> SmokeResult:
    status, _headers, body = _request("GET", f"{base_url}/version")
    if status != 200:
        return SmokeResult("version", False, f"HTTP {status} {body}")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return SmokeResult("version", False, f"Invalid JSON: {body}")

    passed = (
        payload.get("status") == "ok"
        and payload.get("app") == "beautyagent-ai-backend"
        and payload.get("expected_branch") == "week-2"
    )
    return SmokeResult("version", passed, json.dumps(payload, ensure_ascii=True))


def check_cors(base_url: str, origin: str) -> SmokeResult:
    status, headers, body = _request(
        "OPTIONS",
        f"{base_url}/generate",
        origin=origin,
        extra_headers={
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type",
        },
    )
    allowed_origin = headers.get("access-control-allow-origin") or headers.get(
        "Access-Control-Allow-Origin"
    )
    passed = status == 200 and allowed_origin == origin
    return SmokeResult(
        "cors_preflight",
        passed,
        f"HTTP {status} allow-origin={allowed_origin} body={body}",
    )


def check_generate(base_url: str, origin: str) -> SmokeResult:
    status, _headers, body = _request(
        "POST",
        f"{base_url}/generate",
        origin=origin,
        payload={
            "brandId": "tower_28",
            "productName": "SOS spray",
            "brief": "Draft a launch post.",
            "channels": ["tiktok"],
        },
    )
    if status != 200:
        return SmokeResult("generate_free_text_product", False, f"HTTP {status} {body}")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return SmokeResult("generate_free_text_product", False, f"Invalid JSON: {body}")

    results = payload.get("results") or []
    passed = payload.get("error") is None and len(results) == 1
    return SmokeResult(
        "generate_free_text_product",
        passed,
        json.dumps(payload, ensure_ascii=True)[:800],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test live Render backend.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--origin", default=DEFAULT_ORIGIN)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    results = [
        check_health(base_url),
        check_version(base_url),
        check_cors(base_url, args.origin),
        check_generate(base_url, args.origin),
    ]

    failures = 0
    for result in results:
        marker = "PASS" if result.passed else "FAIL"
        print(f"{marker} {result.name}: {result.detail}")
        if not result.passed:
            failures += 1

    if failures:
        print(f"Render live smoke failed: {failures}/{len(results)} checks failed.")
        return 1

    print(f"Render live smoke passed: {len(results)}/{len(results)} checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
