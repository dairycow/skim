# AGENTS.md

## Project Type
This is a Python project using modern Python packaging with `pyproject.toml`.

## Code Formatting & Linting
- **Black**: Code formatter configured for 80 character line length
- **Ruff**: Fast Python linter configured for 80 character line length
- Run `black .` to format code
- Run `ruff check .` to lint code
- Run `ruff check --fix .` to auto-fix issues

## Deployment
Commits to the main branch are automatically applied to the deployed container via webhook.

## Debugging
For deep debugging, use SSH to access the container directly.