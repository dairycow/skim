# AGENTS.md

## Project Type
This is a Python project using modern Python packaging with `pyproject.toml`.

## Code Formatting & Linting
- **Ruff**: Fast Python linter and formatter configured for 80 character line length
- Run `ruff format .` to format code
- Run `ruff check .` to lint code
- Run `ruff check --fix .` to auto-fix linting issues

## Deployment
Commits to the main branch are automatically applied to the deployed container via webhook.

## Debugging
For deep debugging, use SSH to access the container directly.