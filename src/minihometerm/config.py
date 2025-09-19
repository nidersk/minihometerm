import os
from configparser import MissingSectionHeaderError
from pathlib import Path

from kivy.config import ConfigParser
from kivy.logger import Logger as logger

APP_NAME = "minihometerm"

# On Raspberry Pi, run as user “pi” or another; adjust path accordingly
USER_CONFIG_PATH = Path.home() / ".config" / APP_NAME / "config.ini"
GLOBAL_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config.ini"


def load_config() -> ConfigParser:
    config = ConfigParser()

    # default values
    config.setdefaults(
        "logging",
        {
            "level": "DEBUG",
        },
    )

    config.setdefaults(
        "connection",
        {
            "ws_url": "ws://homeassistant.local:8123/api/websocket",
            "token": "<YOUR_LONG_LIVED_TOKEN>",
        },
    )

    config.setdefaults(
        "ui",
        {
            "theme": "dark",
            "fullscreen": "1",
            "screen_dim_timeout": "60",
            "screen_off_timeout": "200",
            "show_date": "1",
            "show_clock": "1",
            "show_temperature": "1",
            "show_temperature_min_max": "1",
            "enable_animations": "1",
        },
    )

    config.setdefaults(
        "conditions",
        {
            "temperature_sensor": "sensor.smart_outdoor_module_temperature",
            "temperature_min_entity": "input_number.min_temp",
            "temperature_max_entity": "input_number.max_temp",
        },
    )

    config.setdefaults(
        "buttons",
        {
            "button_action_timeout": "300",
            "button1_label": "Button 1",
            "button1_icon": "lightbulb",
            "button1_state_entity": "input_boolean.test_toggle_1",
            "button1_action": "script.toggle_gate",
            "button2_label": "Button 2",
            "button2_icon": "garage",
            "button2_state_entity": "input_boolean.test_toggle_2",
            "button2_action": "script.toggle_garage_gate",
        },
    )

    # read global config (in repo root or installed path)
    if GLOBAL_CONFIG_PATH.exists():
        try:
            config.read(str(GLOBAL_CONFIG_PATH))
            logger.info(f"MiniHomeTerm: Global config found at {GLOBAL_CONFIG_PATH}")
        except MissingSectionHeaderError:
            logger.warning(
                f"MiniHomeTerm: Ignoring malformed global config at {GLOBAL_CONFIG_PATH}"
            )

    # read user config
    if USER_CONFIG_PATH.exists():
        try:
            config.read(str(USER_CONFIG_PATH))
            logger.info(f"MiniHomeTerm: User config found at {USER_CONFIG_PATH}")
        except MissingSectionHeaderError:
            logger.warning(f"MiniHomeTerm: Ignoring malformed user config at {USER_CONFIG_PATH}")

    # environment overrides
    ws_url_env = os.environ.get("MINIHOMETERM_WS_URL")
    token_env = os.environ.get("MINIHOMETERM_TOKEN")
    if ws_url_env:
        config.set("connection", "ws_url", ws_url_env)
    if token_env:
        config.set("connection", "token", token_env)

    return config
