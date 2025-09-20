import os
from contextlib import suppress

# Must be set before importing kivy
os.environ["KIVY_WINDOW"] = "mock"
os.environ["KIVY_GL_BACKEND"] = "mock"


def test_app_title(mock_cfg):
    from minihometerm.app import MiniHomeTerm

    app = MiniHomeTerm(cfg=mock_cfg)
    assert app.title == "MiniHomeTerm"


# def test_build_returns_widget():
#     from kivy.uix.screenmanager import ScreenManager

#     from minihometerm.app import MiniHomeTerm

#     app = MiniHomeTerm()

#     root = app.build()
#     Root should be a Kivy widget (BoxLayout because KV defines one)
#     assert isinstance(root, ScreenManager)
#     assert "home" in root.current_screen.name


def test_on_click_me_prints(caplog, mock_cfg):
    from minihometerm.app import MiniHomeTerm

    app = MiniHomeTerm(cfg=mock_cfg)
    with caplog.at_level("INFO"):
        with suppress(ConnectionError):
            app.on_click_me()

    assert any("Button clicked!" in message for message in caplog.messages)

    assert any("Button clicked!" in message for message in caplog.messages)
