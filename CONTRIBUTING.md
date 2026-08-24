# Contributing to FKT

## Getting Started

1. Clone the repo and create a virtual environment:
   ```
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

2. Copy `.env.example` to `.env` and fill in your API keys.

3. Run migrations and seed data:
   ```
   python -m tracker_app.db.migrations
   python -m tracker_app.tools.populate
   ```

4. Start the app:
   ```
   python -m tracker_app.web.app       # dashboard only
   python -m tracker_app.main          # tracker only
   ```

## Development Workflow

- **Linting:** `ruff check tracker_app/` and `ruff format tracker_app/`
- **Tests:** `pytest tracker_app/tests/ -v`
- **Coverage:** `pytest --cov=tracker_app --cov-report=term-missing`
- **CI checks:** Run `ruff check` + `ruff format --check` + `pytest` before pushing.

## Code Style

- Python 3.11+, type hints on public functions.
- Constants live in `tracker_app/constants.py` — import from there, never hardcode.
- SQLAlchemy models in `tracker_app/db/models.py`. Migrations in `tracker_app/db/migrations.py`.
- Tests in `tracker_app/tests/`, named `test_<feature>.py`.

## Commit Convention

Use conventional commits: `fix:`, `feat:`, `refactor:`, `docs:`, `style:`, `test:`, `build:`.