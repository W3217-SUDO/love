from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_404_returns_html_for_html_accept(client):
    r = client.get("/this-route-does-not-exist", headers={"Accept": "text/html"})
    assert r.status_code == 404
    assert "text/html" in r.headers["content-type"]
    body = r.text
    assert "<html" in body.lower()
    assert "404" in body or "找不到" in body or "not found" in body.lower()


def test_404_returns_json_for_non_html_accept(client):
    r = client.get("/this-route-does-not-exist")
    assert r.status_code == 404
    # default Accept is */* — should be JSON
    assert "application/json" in r.headers["content-type"]


def test_403_returns_html_for_html_accept(client):
    """Hit any AppError(403) — easiest is to trigger via a Forbidden raise.
    We monkey-patch a temp route since no existing route raises Forbidden."""
    from app.errors import Forbidden
    from app.main import app

    @app.get("/_test_forbidden")
    def boom():
        raise Forbidden("nope")

    try:
        r = client.get("/_test_forbidden", headers={"Accept": "text/html"})
        assert r.status_code == 403
        assert "text/html" in r.headers["content-type"]
        body = r.text
        assert "<html" in body.lower()
        assert "403" in body or "禁止" in body or "forbidden" in body.lower()
    finally:
        app.router.routes = [r for r in app.router.routes if r.path != "/_test_forbidden"]


def test_500_renders_html_for_html_accept(client):
    from app.errors import AppError
    from app.main import app

    @app.get("/_test_500")
    def boom():
        raise AppError("kaboom", code="internal", http_status=500)

    try:
        r = client.get("/_test_500", headers={"Accept": "text/html"})
        assert r.status_code == 500
        assert "text/html" in r.headers["content-type"]
        body = r.text
        assert "<html" in body.lower()
        assert "500" in body or "出错" in body or "error" in body.lower()
    finally:
        app.router.routes = [r for r in app.router.routes if r.path != "/_test_500"]


def test_500_renders_json_for_json_accept(client):
    from app.errors import AppError
    from app.main import app

    @app.get("/_test_500_json")
    def boom():
        raise AppError("kaboom", code="internal", http_status=500)

    try:
        r = client.get("/_test_500_json")
        assert r.status_code == 500
        assert "application/json" in r.headers["content-type"]
    finally:
        app.router.routes = [r for r in app.router.routes if r.path != "/_test_500_json"]
