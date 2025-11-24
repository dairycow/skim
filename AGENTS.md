# AGENTS.md

- This is a modern Python project defined by `pyproject.toml`.
- uv is used as the unified toolchain.
- ALWAYS USE uv WHEN RUNNING ANY PYTHON COMMANDS OR PYTEST.
- Pre-commit hooks are configured for automated quality assurance. IF YOU IDENTIFY ANY ISSUES, ADDRESS OR DOCUMENT THEM IMMEDIATELY.
- Use Australian english.
- Don't use emojis.
- ALWAYS DELEGATE ITEMS SUBAGENTS WHEN APPLICABLE.
- YOU MUST follow the Test-Driven Development RED -> GREEN -> REFACTOR cycle.

## Test-Driven Development
- Write tests BEFORE implementation
- Confirm tests fail (avoid mock implementations)
- Commit tests separately
- Implement until tests pass
- Do NOT modify tests during implementation