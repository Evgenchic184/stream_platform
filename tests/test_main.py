import pytest

import main


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
