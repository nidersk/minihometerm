import sys
import textwrap

from minihometerm.ui import loader


def make_pkg(tmp_path, pkg_name="fakepkg"):
    """Helper: create a fake Python package under tmp_path."""
    package_dir = tmp_path / pkg_name
    package_dir.mkdir()
    (package_dir / "__init__.py").write_text("")
    sys.path.insert(0, str(tmp_path))
    return package_dir


# -------------------------
# load_kv_files tests
# -------------------------


def test_load_single_kv_file(tmp_path):
    kv_content = textwrap.dedent(
        """
        <DummyWidget@Widget>:
            size_hint: None, None
        """
    )
    kv_file = tmp_path / "dummy.kv"
    kv_file.write_text(kv_content)

    loader.load_kv_files(str(tmp_path))  # should not raise


def test_load_recursive_kv_files(tmp_path):
    subdir = tmp_path / "sub"
    subdir.mkdir()

    kv_content = textwrap.dedent(
        """
        <DummyWidget@Widget>:
            size_hint: None, None
        """
    )
    kv_file = subdir / "dummy.kv"
    kv_file.write_text(kv_content)

    loader.load_kv_files(str(tmp_path))  # should not raise


def test_non_kv_files_ignored(tmp_path):
    (tmp_path / "not_kv.txt").write_text("this should be ignored")
    loader.load_kv_files(str(tmp_path))  # should not raise


# -------------------------
# discover_screens tests
# -------------------------


def test_discover_single_screen(tmp_path, monkeypatch):
    make_pkg(tmp_path, "pkg1")
    (tmp_path / "pkg1" / "myscreen.py").write_text(
        textwrap.dedent(
            """
            from kivy.uix.screenmanager import Screen
            class MyScreen(Screen): pass
            """
        )
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    screens = loader.discover_screens("pkg1")
    assert {cls.__name__ for cls in screens} == {"MyScreen"}


def test_discover_multiple_screens(tmp_path, monkeypatch):
    make_pkg(tmp_path, "pkg2")
    (tmp_path / "pkg2" / "s1.py").write_text(
        "from kivy.uix.screenmanager import Screen\nclass S1(Screen): pass\n"
    )
    (tmp_path / "pkg2" / "s2.py").write_text(
        "from kivy.uix.screenmanager import Screen\nclass S2(Screen): pass\n"
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    screens = loader.discover_screens("pkg2")
    assert {cls.__name__ for cls in screens} == {"S1", "S2"}


def test_ignore_non_screen_classes(tmp_path, monkeypatch):
    make_pkg(tmp_path, "pkg3")
    (tmp_path / "pkg3" / "mixed.py").write_text(
        textwrap.dedent(
            """
            class NotAScreen: pass
            from kivy.uix.screenmanager import Screen
            class Good(Screen): pass
            """
        )
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    screens = loader.discover_screens("pkg3")
    assert {cls.__name__ for cls in screens} == {"Good"}


def test_empty_package_returns_no_screens(tmp_path, monkeypatch):
    make_pkg(tmp_path, "pkg4")
    monkeypatch.syspath_prepend(str(tmp_path))

    screens = loader.discover_screens("pkg4")
    assert screens == []
