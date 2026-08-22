# Contributing

Thank you for your interest in improving **py-scheduler**.

## Ground rules

- Open an issue first for large or behaviour-changing work so maintainers can align on scope.
- Keep pull requests focused: one concern per PR is easier to review and revert.
- Match existing style: **Ruff** formatting and lint rules are enforced in CI.

## Local setup

```bash
git clone https://github.com/enoquesousa/py-scheduler.git
cd py-scheduler
python -m venv .venv
source .venv/bin/activate  # Windows: .\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

## Checks before you push

```bash
ruff check .
ruff format --check .
pytest
```

Optional: install **pre-commit** and run `pre-commit install` so hooks mirror CI.

## Pull requests

- Describe **what** changed and **why** in the PR body.
- If behaviour changes, update **docs** (`README.md`, `docs/`) and **CHANGELOG.md** under `[Unreleased]`.

## Code of conduct

All contributors are expected to follow [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).
