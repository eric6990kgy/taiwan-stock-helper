"""Regression test for a real bug: Vite silently picks the next free port
(5174, 5175, ...) when 5173 is taken, and a CORS allowlist hardcoded to
port 5173 turns that into a same-origin-looking failure with no useful
error in the browser (every request just fails). allow_origin_regex must
accept any localhost/127.0.0.1 port, not just the default.
"""


def test_cors_allows_default_vite_port(client):
    resp = client.options(
        "/api/portfolio",
        headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "GET"},
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


def test_cors_allows_alternate_port_when_default_is_taken(client):
    """The exact scenario that broke: Vite fell back to 5174."""
    resp = client.options(
        "/api/portfolio",
        headers={"Origin": "http://127.0.0.1:5174", "Access-Control-Request-Method": "GET"},
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"


def test_cors_allows_localhost_hostname_too(client):
    resp = client.options(
        "/api/portfolio",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_cors_rejects_non_local_origin(client):
    resp = client.options(
        "/api/portfolio",
        headers={"Origin": "http://evil.example.com", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in resp.headers
