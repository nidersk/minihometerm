def test_app_title():
    from minihometerm.app import MiniHomeTerm

    app = MiniHomeTerm()
    assert app.title == "My Kivy App"


def test_build_returns_widget():
    from kivy.uix.screenmanager import ScreenManager

    from minihometerm.app import MiniHomeTerm

    app = MiniHomeTerm()
    root = app.build()
    # Root should be a Kivy widget (BoxLayout because KV defines one)
    assert isinstance(root, ScreenManager)
    assert "home" in root.current_screen.name


def test_on_click_me_prints(capsys):
    from minihometerm.app import MiniHomeTerm

    app = MiniHomeTerm()
    app.on_click_me()
    captured = capsys.readouterr()
    assert "Button clicked!" in captured.out
