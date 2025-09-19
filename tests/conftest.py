import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def headless_kivy():
    # Ensure tests don't try to open a real window.
    os.environ.setdefault("KIVY_WINDOW", "mock")
    os.environ.setdefault("KIVY_GL_BACKEND", "mock")
    os.environ.setdefault("KIVY_NO_ARGS", "1")
    yield


@pytest.fixture
def mock_cfg(monkeypatch, tmp_path):
    from minihometerm import config

    monkeypatch.setattr(config, "USER_CONFIG_PATH", tmp_path / "doesnotexist.ini")
    monkeypatch.setattr(config, "GLOBAL_CONFIG_PATH", tmp_path / "alsodoesnotexist.ini")

    cfg = config.load_config()

    return cfg
