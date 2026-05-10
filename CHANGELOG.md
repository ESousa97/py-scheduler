# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Documentation set aligned with sibling templates (architecture, configuration, development).
- `scripts/smoke_validate.py` for fast config + registry validation.
- MIT `LICENSE`, community docs, Codecov config, pre-commit Ruff hooks, CodeQL workflow.
- CI: dependency review on pull requests; coverage upload on Python 3.12.

## [0.1.0] - 2026-05-10

### Added

- Initial release: YAML-driven APScheduler jobs, SQLite execution history, webhooks, Prometheus metrics, Tenacity retries.

[Unreleased]: https://github.com/esousa97/py-scheduler/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/esousa97/py-scheduler/releases/tag/v0.1.0
