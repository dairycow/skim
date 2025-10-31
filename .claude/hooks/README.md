# Hooks

Claude Code hooks that enable skill auto-activation and file tracking for Python projects.

---

## What Are Hooks?

Hooks are scripts that run at specific points in Claude's workflow:
- **UserPromptSubmit**: When user submits a prompt
- **PreToolUse**: Before a tool executes
- **PostToolUse**: After a tool completes
- **Stop**: When user requests to stop

**Key insight:** Hooks can modify prompts, block actions, and track state - enabling features Claude can't do alone.

---

## Essential Hooks (Start Here)

### skill-activation-prompt (UserPromptSubmit)

**Purpose:** Automatically suggests relevant skills based on user prompts and file context

**How it works:**
1. Reads `skill-rules.json`
2. Matches user prompt against trigger patterns
3. Checks which files user is working with
4. Injects skill suggestions into Claude's context

**Why it's essential:** This is THE hook that makes skills auto-activate.

**Integration:**
```bash
# Copy both files
cp skill-activation-prompt.sh your-project/.claude/hooks/
cp skill-activation-prompt.py your-project/.claude/hooks/

# Make executable
chmod +x your-project/.claude/hooks/skill-activation-prompt.sh
chmod +x your-project/.claude/hooks/skill-activation-prompt.py

# Requires Python 3.6+ (no additional dependencies needed)
```

**Add to settings.json:**
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

**Customization:** ✅ None needed - reads skill-rules.json automatically

---

### post-tool-use-tracker (PostToolUse)

**Purpose:** Tracks file changes to maintain context across sessions (Python-specific)

**How it works:**
1. Monitors Edit/Write/MultiEdit tool calls
2. Records which Python files were modified
3. Creates cache for context management
4. Auto-detects project structure and Python tooling (ruff, pytest, etc.)

**Why it's essential:** Helps Claude understand what parts of your Python codebase are active.

**Integration:**
```bash
# Copy both files
cp post-tool-use-tracker.sh your-project/.claude/hooks/
cp post-tool-use-tracker.py your-project/.claude/hooks/

# Make executable
chmod +x your-project/.claude/hooks/post-tool-use-tracker.sh
chmod +x your-project/.claude/hooks/post-tool-use-tracker.py

# Requires Python 3.6+ (no additional dependencies needed)
```

**Add to settings.json:**
```json
{
  "hooks": {
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
    ]
  }
}
```

**Python-specific features:**
- Detects `pyproject.toml` configuration
- Auto-discovers ruff, flake8, pylint, black
- Identifies pytest, unittest test suites
- Supports Python monorepo structures

**Customization:** ✅ None needed - auto-detects Python tooling

---

## Optional Hooks

### stop-python-check (Stop)

**Purpose:** Automatically lint and format Python code when you stop working

**How it works:**
1. Reads the cache created by `post-tool-use-tracker.py`
2. Runs `ruff format` to auto-format modified files
3. Runs `ruff check` to find linting issues
4. Attempts auto-fix with `ruff check --fix`
5. Reports any remaining issues that need manual fixing

**Why it's useful:** Ensures code quality and consistent formatting without manual intervention.

**Integration:**
```bash
# Copy the file
cp stop-python-check.sh your-project/.claude/hooks/

# Make executable
chmod +x your-project/.claude/hooks/stop-python-check.sh
```

**Add to settings.json:**
```json
{
  "hooks": {
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

**Features:**
- ✅ Auto-formats code with ruff
- ✅ Auto-fixes many linting issues
- ✅ Type checks with mypy
- ✅ Auto-installs missing type stubs (e.g., types-requests)
- ✅ Reports remaining issues clearly
- ✅ Non-blocking (won't prevent stopping)
- ✅ Only runs if Python files were edited

**Requirements:**
- `ruff` must be installed and available in PATH
- `mypy` must be installed for type checking (optional)
- Run `pip install ruff mypy` if not already installed

**Customization:** See CONFIG.md for advanced configuration options.

---

## For Claude Code

**When setting up hooks for a Python project:**

1. **Start with the two essential hooks** (skill-activation-prompt and post-tool-use-tracker)
2. **Verify Python environment:**
   ```bash
   python3 --version  # Should be 3.6+
   which ruff        # Check if ruff is available
   ```
3. **Test hooks manually** before relying on them
4. **Verify after setup:**
   ```bash
   ls -la .claude/hooks/*.sh | grep rwx
   ```

**Python-specific notes:**
- The hooks use only Python standard library (no pip dependencies)
- Compatible with pyproject.toml, setup.py, and setup.cfg projects
- Auto-detects common Python tools (ruff, black, flake8, pylint, pytest)
- Cache directory is `.claude/python-cache/` (not `tsc-cache`)

**Questions?** See CONFIG.md for detailed configuration options.
