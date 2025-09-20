import importlib
import inspect
import os
import pkgutil
from typing import List, Type

from kivy.lang import Builder
from kivy.uix.screenmanager import Screen


def load_kv_files(base_path: str) -> None:
    """
    Recursively load all .kv files under the given base path.
    """
    for root, _, files in os.walk(base_path):
        for filename in files:
            if filename.endswith(".kv"):
                filepath = os.path.join(root, filename)
                Builder.load_file(filepath)


def discover_screens(package_name: str) -> List[Type[Screen]]:
    """
    Import all modules in a package and return subclasses of Screen.
    """
    screens: List[Type[Screen]] = []
    package = importlib.import_module(package_name)

    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        module = importlib.import_module(f"{package_name}.{module_name}")

        for _, obj in inspect.getmembers(module, inspect.isclass):
            if issubclass(obj, Screen) and obj is not Screen:
                screens.append(obj)

    return screens
