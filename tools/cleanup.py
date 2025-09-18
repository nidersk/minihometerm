#!/usr/bin/env python3
import pathlib
import shutil
import sys

CLEAN_DIRS = [
    "build",
    "dist",
    ".pytest_cache",
    ".mypy_cache",
    "htmlcov",
]
CLEAN_FILES = [
    ".coverage",
]

# Directories to ignore during recursive cleanup
SKIP_DIRS = {".venv", "venv", "ENV", "env", ".git"}


def rm(path: pathlib.Path):
    """Remove file or directory if it exists."""
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
        print(f"Removed dir: {path}")
    elif path.is_file():
        try:
            path.unlink()
            print(f"Removed file: {path}")
        except OSError:
            pass


def main():
    root = pathlib.Path(".").resolve()

    # Remove fixed dirs/files
    for d in CLEAN_DIRS:
        rm(root / d)
    for f in CLEAN_FILES:
        rm(root / f)

    # Remove all egg-info dirs (recursively)
    for p in root.rglob("*.egg-info"):
        if p.is_dir():
            rm(p)

    # Remove all __pycache__ dirs recursively, skipping SKIP_DIRS
    for p in root.rglob("__pycache__"):
        if any(skip in p.parts for skip in SKIP_DIRS):
            continue
        shutil.rmtree(p, ignore_errors=True)
        print(f"Removed cache: {p}")

    print("✅ Cleanup complete.")


if __name__ == "__main__":
    sys.exit(main())
