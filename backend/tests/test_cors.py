from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def _options(client: TestClient, *, origin: str, method: str = "POST", req_headers: str = "authorization, content-type"):
    return client.options(
        "/api/v1/auth/token",
        headers={
            "origin": origin,
            "access-control-request-method": method,
            "access-control-request-headers": req_headers,
        },
    )


def test_preflight_returns_explicit_origin_not_wildcard() -> None:
    client = TestClient(app)
    r = _options(client, origin="http://localhost:5173")
    assert r.status_code in (200, 204), r.text
    acao = r.headers.get("access-control-allow-origin")
    assert acao == "http://localhost:5173"
    assert acao != "*"
    assert r.headers.get("access-control-allow-credentials") == "true"


def test_preflight_advertises_allowed_methods() -> None:
    client = TestClient(app)
    r = _options(client, origin="http://localhost:5173", method="DELETE")
    assert r.status_code in (200, 204), r.text
    acam = r.headers.get("access-control-allow-methods", "")
    advertised = {m.strip().upper() for m in acam.split(",") if m.strip()}
    for required in ("GET", "POST", "PUT", "PATCH", "DELETE"):
        assert required in advertised, f"{required} not in ACAM: {acam}"
    assert "TRACE" not in advertised
    assert "CONNECT" not in advertised


def test_preflight_advertises_allowed_headers() -> None:
    client = TestClient(app)
    r = _options(client, origin="http://localhost:5173")
    assert r.status_code in (200, 204), r.text
    acah = r.headers.get("access-control-allow-headers", "").lower()
    advertised = {h.strip() for h in acah.split(",") if h.strip()}
    assert "authorization" in advertised
    assert "content-type" in advertised


def test_unallowed_origin_gets_no_acao() -> None:
    client = TestClient(app)
    r = _options(client, origin="http://evil.com")
    # starlette returns 400 for disallowed origin preflight, or 200 with no ACAO
    acao = r.headers.get("access-control-allow-origin")
    assert acao != "http://evil.com"
    assert acao != "*"
