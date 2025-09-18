# minihometerm

A structured Kivy application with Test-Driven Development and setuptools packaging.

## Features
- Kivy-based UI (`src/minihometerm`)
- TDD with `pytest`
- Structured modules: `ui/`, `core/`, `helpers/`, `ext/`, and `assets/`
- Packaged with `setuptools` using `pyproject.toml`
- CI via GitHub Actions (lint + tests)

## Dev Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -U pip
pip install -e ".[dev]"
```

## Run

```bash
python -m minihometerm.main
```

## Tests

```bash
pytest -q
```

> CI runs tests headlessly by setting `KIVY_WINDOW=mock`.
