"""Serving the built frontend: assets, client-side routes, and no escaping the build folder."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.web_ui import mount_spa


def make(tmp_path):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>app</title>")
    (dist / "assets" / "app-1234.js").write_text("console.log(1)")
    (dist / "favicon.svg").write_text("<svg/>")
    (tmp_path / "secret.txt").write_text("nope")
    app = FastAPI()

    @app.get("/healthz")
    def healthz():
        return {"ok": True}

    assert mount_spa(app, dist)
    return TestClient(app)


def test_serves_assets_files_and_falls_back_to_index(tmp_path):
    c = make(tmp_path)
    assert c.get("/assets/app-1234.js").text == "console.log(1)"
    assert c.get("/favicon.svg").text == "<svg/>"
    for route in ("/", "/keys", "/admin/overview"):
        r = c.get(route)
        assert r.status_code == 200 and "<title>app</title>" in r.text
        assert r.headers["cache-control"] == "no-cache"
    assert c.get("/healthz").json() == {"ok": True}


def test_api_paths_are_not_swallowed_by_the_fallback(tmp_path):
    c = make(tmp_path)
    assert c.get("/api/nothing-here").status_code == 404
    assert c.get("/api").status_code == 404


def test_cannot_read_outside_the_build(tmp_path):
    c = make(tmp_path)
    r = c.get("/..%2Fsecret.txt")
    assert "nope" not in r.text


def test_nothing_mounted_without_a_build(tmp_path):
    assert mount_spa(FastAPI(), tmp_path / "missing") is False
