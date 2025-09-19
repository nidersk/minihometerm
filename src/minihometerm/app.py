# flake8: noqa: E402
import os
from configparser import ConfigParser

# Ensure Kivy behaves in headless-friendly mode unless a window is explicitly desired.
os.environ.setdefault("KIVY_NO_ARGS", "1")

from kivy.app import App
from kivy.lang import Builder
from kivy.logger import Logger as logger
from kivy.uix.screenmanager import Screen

# flake8: enable=E402

KV = """
#:kivy 2.3.0

ScreenManager:
    id: sm
    HomeScreen:

<HomeScreen>:
    name: "home"
    BoxLayout:
        orientation: "vertical"
        padding: dp(16)
        spacing: dp(12)

        Label:
            id: title_lbl
            text: app.title
            font_size: "24sp"
            size_hint_y: None
            height: self.texture_size[1] + dp(8)

        Button:
            text: "Click me"
            size_hint_y: None
            height: dp(48)
            on_release: app.on_click_me()
"""


class HomeScreen(Screen):
    pass


class MiniHomeTerm(App):
    title = "MiniHomeTerm"

    def __init__(self, cfg: ConfigParser, **kwargs):
        super().__init__(**kwargs)

    def build(self):
        return Builder.load_string(KV)

    def on_click_me(self):
        # Placeholder for business logic
        logger.info("MiniHomeTerm: Button clicked!")
