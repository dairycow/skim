# Hooks Configuration Guide (Python Projects)

This guide explains how to configure and customize the hooks system for Python projects.

## Quick Start Configuration

### 1. Register Hooks in .claude/settings.json

Create or update `.claude/settings.json` in your project root:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/skill-activation-prompt.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|MultiEdit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post-tool-use-tracker.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/stop-python-check.sh"
          }
        ]
      }
    ]
  }
}
```

### 2. Set Execute Permissions

```bash
chmod +x .claude/hooks/*.sh
chmod +x .claude/hooks/*.py
```

### 3. Verify Python Environment

```bash
python3 --version  # Should be 3.6+
```

No additional Python packages are required - the hooks use only the standard library.

## Customization Options

### Project Structure Detection

By default, hooks detect these directory patterns:

**Python Source:** `src/`, `lib/`, `app/`, `api/`, `services/`
**Tests:** `tests/`, `test/`, `pytest/`
**Documentation:** `docs/`, `documentation/`
**Scripts:** `scripts/`, `bin/`, `tools/`
**Monorepo:** `packages/*`

#### Adding Custom Directory Patterns

Edit `.claude/hooks/post-tool-use-tracker.py`, function `detect_repo()`:

```python
# Add your custom directories
python_src_patterns = ['src', 'lib', 'app', 'api', 'services', 'my_module']
```

### Lint Command Detection

The hooks auto-detect linting commands based on:
1. Presence of `pyproject.toml` with `[tool.ruff]`, `[tool.flake8]`, or `[tool.pylint]`
2. Presence of `.flake8`, `setup.cfg`, or `tox.ini`
3. Defaults to `ruff check .` if no config found

#### Supported Linters
- **ruff** (default and recommended)
- **flake8**
- **pylint**

#### Customizing Lint Commands

Edit `.claude/hooks/post-tool-use-tracker.py`, function `get_lint_command()`:

```python
# Add custom lint logic
if repo == 'my-service':
    return f"cd {repo_path} && mypy ."
```

### Format Command Detection

The hooks auto-detect formatting commands based on:
1. Presence of `pyproject.toml` with `[tool.ruff.format]` or `[tool.black]`
2. Defaults to `ruff format .` if no config found

#### Supported Formatters
- **ruff format** (default and recommended)
- **black**

#### Customizing Format Commands

Edit `.claude/hooks/post-tool-use-tracker.py`, function `get_format_command()`:

```python
# Add custom format logic
if repo == 'my-service':
    return f"cd {repo_path} && autopep8 --in-place --recursive ."
```

### Test Command Detection

Hooks automatically detect:
- `pytest` (if `pytest.ini` exists or `tests/` directory found)
- `unittest` (fallback for `tests/` directory)
- `pyproject.toml` with `[tool.pytest]` configuration

#### Custom Test Configs

Edit `.claude/hooks/post-tool-use-tracker.py`, function `get_test_command()`:

```python
# Add custom test logic
if repo == 'my-service':
    return f"cd {repo_path} && nose2"
```

### Python-Specific File Detection

The hook only tracks Python files (`.py`) and skips:
- Markdown files (`.md`, `.markdown`, `.rst`)
- Text files (`.txt`)

To modify file detection, edit the `main()` function in `post-tool-use-tracker.py`:

```python
# Skip if not a Python file
if not re.search(r'\.py$', file_path):
    sys.exit(0)
```

### Stop Hook Customization

The `stop-python-check.sh` hook automatically runs when you stop working. You can customize its behavior:

#### Disable Auto-Fix

Edit `.claude/hooks/stop-python-check.sh` to skip the auto-fix step:

```bash
# Comment out or remove the auto-fix section (lines ~70-90)
# if [ "$HAS_ERRORS" -eq 1 ]; then
#     echo "🔧 Attempting auto-fix with ruff --fix..."
#     ...
# fi
```

#### Change Error Display Limit

By default, the hook shows the first 20 lines of errors. To change this:

```bash
# Find this line in stop-python-check.sh
echo "$OUTPUT" | head -20  # Change 20 to your preferred limit
```

#### Run Additional Checks

Add custom checks after the linting step:

```bash
# Add at the end of stop-python-check.sh before the summary
echo "🔬 Running type checks with mypy..."
if command -v mypy &> /dev/null; then
    cd "$CLAUDE_PROJECT_DIR" && mypy .
fi
```

#### Skip Formatting

To only run linting without formatting, comment out the formatting section:

```bash
# Comment out lines ~35-50 in stop-python-check.sh
# echo "🎨 Auto-formatting with ruff..."
# FORMAT_COMMANDS=$(grep ":format:" "$CACHE_DIR/commands.txt" | cut -d: -f3- | sort -u)
# ...
```

## Environment Variables

### Global Environment Variables

Set in your shell profile (`.bashrc`, `.zshrc`, etc.):

```bash
# Custom project directory (if not using default)
export CLAUDE_PROJECT_DIR=/path/to/your/project
```

### Per-Session Environment Variables

Set before starting Claude Code:

```bash
CLAUDE_PROJECT_DIR=/custom/path claude-code
```

## Hook Execution Order

Hooks run in the order specified in `settings.json`:

```json
"UserPromptSubmit": [
  {
    "hooks": [
      { "command": "...skill-activation-prompt.sh" }  // Runs when prompt submitted
    ]
  }
],
"PostToolUse": [
  {
    "hooks": [
      { "command": "...post-tool-use-tracker.sh" }  // Runs after Edit/Write/MultiEdit
    ]
  }
]
```

## Selective Hook Enabling

You don't need all hooks. Choose what works for your project:

### Minimal Setup (Skill Activation Only)

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/skill-activation-prompt.sh"
          }
        ]
      }
    ]
  }
}
```

### With File Tracking

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/skill-activation-prompt.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|MultiEdit|Write",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/post-tool-use-tracker.sh"
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/stop-python-check.sh"
          }
        ]
      }
    ]
  }
}
```

## Cache Management

### Cache Location

```
$CLAUDE_PROJECT_DIR/.claude/python-cache/[session_id]/
```

Files stored in cache:
- `edited-files.log` - Timestamped log of all edited files
- `affected-repos.txt` - List of affected repositories/directories
- `commands.txt` - Detected lint, format, and test commands

### Manual Cache Cleanup

```bash
# Remove all cached data
rm -rf $CLAUDE_PROJECT_DIR/.claude/python-cache/*

# Remove specific session
rm -rf $CLAUDE_PROJECT_DIR/.claude/python-cache/[session-id]
```

## Troubleshooting Configuration

### Hook Not Executing

1. **Check registration:** Verify hook is in `.claude/settings.json`
2. **Check permissions:** Run `chmod +x .claude/hooks/*.sh .claude/hooks/*.py`
3. **Check path:** Ensure `$CLAUDE_PROJECT_DIR` is set correctly
4. **Check Python:** Run `python3 --version` to verify Python 3.6+

### False Positive Detections

**Issue:** Hook triggers for files it shouldn't

**Solution:** Add skip conditions in `post-tool-use-tracker.py`:

```python
# Skip generated files
if '/generated/' in file_path or '/__pycache__/' in file_path:
    sys.exit(0)
```

### Performance Issues

**Issue:** Hooks are slow

**Solutions:**
1. Skip large files:
```python
# In main() function
file_size = os.path.getsize(file_path)
if file_size > 100000:  # Skip files > 100KB
    sys.exit(0)
```

2. Limit scope of linting/formatting to specific directories
3. Add more skip conditions for non-critical files

### Debugging Hooks

Add debug output to any hook:

```bash
# In shell script (.sh files)
set -x  # Enable debug mode
```

```python
# In Python script (.py files)
import sys
print(f"DEBUG: file_path={file_path}", file=sys.stderr)
print(f"DEBUG: repo={repo}", file=sys.stderr)
```

View hook execution in Claude Code's logs.

## Advanced Configuration

### Custom Hook Event Handlers

You can create your own hooks for other events:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/my-custom-bash-guard.sh"
          }
        ]
      }
    ]
  }
}
```

### Monorepo Configuration

For monorepos with multiple Python packages:

```python
# In detect_repo() function
if repo == 'packages':
    if len(parts) >= 2:
        return f"packages/{parts[1]}"
    return repo
```

### Virtual Environment Support

If your build commands need to run in a virtualenv:

```python
# In get_lint_command() or get_format_command()
venv_path = repo_path / 'venv'
if venv_path.exists():
    return f"cd {repo_path} && source venv/bin/activate && ruff check ."
```

### Docker/Container Projects

If your commands need to run in containers:

```python
# In get_lint_command()
if repo == 'api':
    return "docker-compose exec api ruff check ."
```

## Python Tool Integration

### Ruff (Recommended)

Ruff is fast and combines linting + formatting:

```toml
# pyproject.toml
[tool.ruff]
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "W", "UP", "B", "C4", "SIM"]

[tool.ruff.format]
quote-style = "double"
```

### Black

Traditional Python formatter:

```toml
# pyproject.toml
[tool.black]
line-length = 88
target-version = ['py311']
```

### Pytest

Modern Python testing framework:

```toml
# pyproject.toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

### Mypy

Static type checking:

```toml
# pyproject.toml
[tool.mypy]
python_version = "3.11"
strict = true
```

## Best Practices

1. **Start minimal** - Enable hooks one at a time
2. **Test thoroughly** - Make changes and verify hooks work
3. **Use pyproject.toml** - Centralize all tool configuration
4. **Document customizations** - Add comments to explain custom logic
5. **Version control** - Commit `.claude/` directory to git
6. **Team consistency** - Share configuration across team

## Python-Specific Notes

- Hooks use only Python standard library (no pip install needed)
- Compatible with pyproject.toml, setup.py, and setup.cfg
- Auto-detects common Python tools (ruff, black, flake8, pylint, pytest)
- Cache directory is `.claude/python-cache/` (not `tsc-cache`)
- Only tracks `.py` files (ignores other file types)

## See Also

- [README.md](./README.md) - Hooks overview
