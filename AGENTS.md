# AGENTS

- Skim: automated ASX ORH breakout bot using IBKR OAuth1; phases driven by cron—see `crontab` for timings.
- Tooling: modern Python (pyproject, 3.13+); uv for all python/pytest/ruff/pre-commit; use Australian english; no emojis; delegate to subagents when possible.
- Quality: pre-commit hooks mandatory; fix or document issues immediately; avoid destructive commands without approval.
- TDD: RED→GREEN→REFACTOR; write tests first, see them fail, commit tests separately, implement to green, refactor safely, do not change tests while implementing.
- Commands: `uv run pytest`; `uv run pre-commit run --all-files`; `uv run ruff check src tests`; `uv run ruff format src tests`.
- Bot runs: `uv run python -m skim.core.bot scan|track_ranges|trade|manage`.
- Data/config: SQLite at ./data/skim.db; env vars in .env; OAuth keys in oauth_keys/; persistent data/logs/oauth_keys.
- States: Candidates watching→entered→closed; Positions open→closed; phases are independent—core modules do not call each other.
- Testing markers: unit (mocked), integration (real IBKR), manual (skip CI); mock IBKR via responses; fixtures in tests/fixtures; shared setup in tests/conftest.py.
- Modules: core orchestrator src/skim/core/bot.py; scanner.py finds gaps; range_tracker samples ORH/ORL; trader executes entries; monitor handles stops; brokers/* handle IBKR client/market data/orders/scanner; data/database.py and data/models.py manage persistence.
- Deployment: GitOps to prod via main; logs in ./logs dev and /opt/skim/logs prod.
