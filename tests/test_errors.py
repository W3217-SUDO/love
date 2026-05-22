from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import AppError, Forbidden, NotFound, register_exception_handlers


def make_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise AppError("kaboom", code="generic", http_status=500)

    @app.get("/missing")
    def missing() -> None:
        raise NotFound("nope")

    @app.get("/forbidden")
    def forbidden() -> None:
        raise Forbidden()

    return app


def test_app_error_returns_json_with_code():
    client = TestClient(make_app(), raise_server_exceptions=False)
    r = client.get("/boom")
    assert r.status_code == 500
    body = r.json()
    assert body["error"]["code"] == "generic"
    assert body["error"]["message"] == "kaboom"


def test_not_found_returns_404():
    client = TestClient(make_app())
    r = client.get("/missing")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"


def test_forbidden_returns_403():
    client = TestClient(make_app())
    r = client.get("/forbidden")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"
