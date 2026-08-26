from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).parents[1] / "app" / "streamlit_app.py"


def test_dashboard_renders_without_exceptions():
    app = AppTest.from_file(APP_PATH).run(timeout=60)

    assert not app.exception
    assert len(app.tabs) == 5
