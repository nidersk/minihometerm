import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def headless_kivy():
    # Ensure tests don't try to open a real window.
    os.environ.setdefault("KIVY_WINDOW", "mock")
    os.environ.setdefault("KIVY_GL_BACKEND", "mock")
    os.environ.setdefault("KIVY_NO_ARGS", "1")
    yield
