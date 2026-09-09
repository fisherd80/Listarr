"""Route tests for application-wide template context processors."""

import pytest
from flask import render_template_string

from listarr import db
from listarr.models.app_config_model import get_app_config
from listarr.utils.time_utils import invalidate_app_timezone_memo

pytestmark = pytest.mark.routes


@pytest.fixture(autouse=True)
def reset_app_timezone_state():
    invalidate_app_timezone_memo()
    yield
    invalidate_app_timezone_memo()


def _set_app_timezone(value):
    cfg = get_app_config()
    cfg.timezone = value
    db.session.commit()
    invalidate_app_timezone_memo()


def _window_app_timezone_assignment(body):
    start = body.index("window.APP_TZ")
    end = body.index("</script>", start)
    return body[start:end]


def test_inject_app_timezone_returns_resolved_name_default(app, monkeypatch):
    monkeypatch.delenv("TZ", raising=False)

    with app.test_request_context():
        rendered = render_template_string("{{ app_timezone }}")

    assert rendered == "UTC"


def test_inject_app_timezone_reflects_stored_value(app):
    _set_app_timezone("America/New_York")

    with app.test_request_context():
        rendered = render_template_string("{{ app_timezone }}")

    assert rendered == "America/New_York"


def test_rendered_page_emits_window_app_timezone(client):
    _set_app_timezone("America/New_York")

    response = client.get("/settings")

    assert response.status_code == 200
    assert 'window.APP_TZ = "America/New_York";' in response.get_data(as_text=True)


def test_window_app_timezone_script_precedes_utils_js(client):
    response = client.get("/settings")
    body = response.get_data(as_text=True)

    assert response.status_code == 200
    assert body.index("window.APP_TZ") < body.index("js/utils.js")


def test_app_timezone_is_json_escaped(client):
    # The invalid stored zone resolves to UTC; this still pins that the inline
    # assignment cannot contain a raw script-breakout sequence.
    _set_app_timezone("</script><script>alert(1)</script>")

    response = client.get("/settings")
    assignment = _window_app_timezone_assignment(response.get_data(as_text=True))

    assert response.status_code == 200
    assert "window.APP_TZ" in assignment
    assert "</script><script>" not in assignment
