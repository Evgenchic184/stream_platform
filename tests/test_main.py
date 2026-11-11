import importlib.util
import sys
from pathlib import Path

import pytest

import main


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("/stream", "/stream"),
        ("stream", "/stream"),
        ("/stream/", "/stream"),
        ("stream/", "/stream"),
        ("", ""),
        ("/", ""),
    ],
)
def test_normalize_prefix(value, expected):
    assert main.normalize_prefix(value) == expected


def call_middleware(prefix, path_info, script_name=""):
    """Run ``PrefixMiddleware`` around a dummy WSGI app and capture environ."""
    captured = {}

    def dummy_app(environ, start_response):
        captured["PATH_INFO"] = environ.get("PATH_INFO")
        captured["SCRIPT_NAME"] = environ.get("SCRIPT_NAME")
        start_response("200 OK", [("Content-Type", "text/plain")])
        return [b"ok"]

    environ = {
        "PATH_INFO": path_info,
        "SCRIPT_NAME": script_name,
        "REQUEST_METHOD": "GET",
    }
    responses = []

    def start_response(status, headers):
        responses.append((status, headers))

    body = b"".join(main.PrefixMiddleware(dummy_app, prefix)(environ, start_response))
    assert responses == [("200 OK", [("Content-Type", "text/plain")])]
    return captured, body


@pytest.mark.parametrize(
    ("path_info", "expected_path"),
    [
        ("/stream", "/"),
        ("/stream/", "/"),
        ("/stream/static/x.js", "/static/x.js"),
    ],
)
def test_prefix_middleware_strips_matching_prefix(path_info, expected_path):
    captured, body = call_middleware("/stream", path_info)

    assert captured == {"PATH_INFO": expected_path, "SCRIPT_NAME": "/stream"}
    assert body == b"ok"


def test_prefix_middleware_keeps_path_already_stripped_by_proxy():
    captured, body = call_middleware("/stream", "/static/x.js")

    assert captured == {"PATH_INFO": "/static/x.js", "SCRIPT_NAME": "/stream"}
    assert body == b"ok"


def test_prefix_middleware_does_not_strip_partial_segment():
    captured, _ = call_middleware("/stream", "/streaming/x.js")

    assert captured == {"PATH_INFO": "/streaming/x.js", "SCRIPT_NAME": "/stream"}


@pytest.mark.parametrize("path_info", ["/stream/static/x.js", "/"])
def test_prefix_middleware_without_prefix_is_noop(path_info):
    captured, body = call_middleware("", path_info)

    assert captured == {"PATH_INFO": path_info, "SCRIPT_NAME": ""}
    assert body == b"ok"


def test_app_with_url_prefix_renders_prefixed_static_urls(tmp_path, monkeypatch):
    """Import main.py in isolation with URL_PREFIX set, then clean up."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "history").write_text(
        f"{tmp_path / 'episode1.mkv'}:0:123.5\n", encoding="utf-8"
    )
    monkeypatch.setenv("URL_PREFIX", "/stream")

    module_name = "main_with_url_prefix"
    spec = importlib.util.spec_from_file_location(module_name, Path(main.__file__))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)

        assert module.URL_PREFIX == "/stream"
        assert module.app.config["APPLICATION_ROOT"] == "/stream"
        module.app.config["TESTING"] = True

        with module.app.test_client() as prefixed_client:
            response = prefixed_client.get("/stream/")

        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "/stream/static/hls.js" in body
        assert "/stream/static/output.m3u8" in body
    finally:
        sys.modules.pop(module_name, None)


@pytest.fixture
def client(monkeypatch, tmp_path):
    """Flask test client with a valid ``history`` file in the temp cwd."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "history").write_text(
        f"{tmp_path / 'episode1.mkv'}:0:123.5\n", encoding="utf-8"
    )
    main.app.config["TESTING"] = True
    with main.app.test_client() as test_client:
        yield test_client


def test_shutdown_route_is_removed(client):
    response = client.get("/shutdown")
    assert response.status_code == 404


def test_index_renders_static_urls(client):
    response = client.get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "/static/hls.js" in body
    assert "/static/output.m3u8" in body
    # No proxy prefix was sent, so nothing should be prefixed.
    assert "/stream/static" not in body


def test_index_honours_x_forwarded_prefix(client):
    response = client.get("/", headers={"X-Forwarded-Prefix": "/stream"})

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "/stream/static/hls.js" in body
    assert "/stream/static/output.m3u8" in body
