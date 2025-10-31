#!/bin/bash
set -e

# Get the session ID from environment or use default
SESSION_ID="${CLAUDE_SESSION_ID:-default}"
CACHE_DIR="$CLAUDE_PROJECT_DIR/.claude/python-cache/$SESSION_ID"

# Exit if no cache directory exists (no Python files were edited)
if [ ! -d "$CACHE_DIR" ]; then
    exit 0
fi

# Exit if no commands were recorded
if [ ! -f "$CACHE_DIR/commands.txt" ]; then
    exit 0
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐍 PYTHON CODE QUALITY CHECK"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Track if any errors occurred
HAS_ERRORS=0
HAS_FORMAT_CHANGES=0
HAS_TYPE_ERRORS=0

# Extract unique repos that were modified
REPOS=$(grep -E "^[^:]+:lint:" "$CACHE_DIR/commands.txt" | cut -d: -f1 | sort -u)

if [ -z "$REPOS" ]; then
    echo "✅ No Python files to check"
    exit 0
fi

echo "📁 Checking repositories: $REPOS"
echo ""

# Run formatting first (ruff format)
echo "🎨 Auto-formatting with ruff..."
FORMAT_COMMANDS=$(grep ":format:" "$CACHE_DIR/commands.txt" | cut -d: -f3- | sort -u)

if [ -n "$FORMAT_COMMANDS" ]; then
    while IFS= read -r cmd; do
        if [ -n "$cmd" ]; then
            echo "   Running: $cmd"
            if eval "$cmd" > /dev/null 2>&1; then
                echo "   ✅ Formatted successfully"
                HAS_FORMAT_CHANGES=1
            else
                echo "   ⚠️  Formatting skipped (no changes or not available)"
            fi
        fi
    done <<< "$FORMAT_COMMANDS"
    echo ""
fi

# Run linting (ruff check)
echo "🔍 Linting with ruff..."
LINT_COMMANDS=$(grep ":lint:" "$CACHE_DIR/commands.txt" | cut -d: -f3- | sort -u)

if [ -n "$LINT_COMMANDS" ]; then
    while IFS= read -r cmd; do
        if [ -n "$cmd" ]; then
            echo "   Running: $cmd"

            # Run the command and capture output
            if OUTPUT=$(eval "$cmd" 2>&1); then
                echo "   ✅ No linting issues"
            else
                EXIT_CODE=$?
                echo "   ❌ Linting issues found:"
                echo "$OUTPUT" | head -20  # Show first 20 lines

                # Check if there are more lines
                LINE_COUNT=$(echo "$OUTPUT" | wc -l)
                if [ "$LINE_COUNT" -gt 20 ]; then
                    echo "   ... and $((LINE_COUNT - 20)) more issues"
                fi

                HAS_ERRORS=1
            fi
        fi
    done <<< "$LINT_COMMANDS"
    echo ""
fi

# Try auto-fixing linting issues with ruff --fix
if [ "$HAS_ERRORS" -eq 1 ]; then
    echo "🔧 Attempting auto-fix with ruff --fix..."
    FIX_COMMANDS=$(grep ":lint:" "$CACHE_DIR/commands.txt" | cut -d: -f3- | sed 's/ruff check/ruff check --fix/' | sort -u)

    if [ -n "$FIX_COMMANDS" ]; then
        while IFS= read -r cmd; do
            if [ -n "$cmd" ]; then
                echo "   Running: $cmd"
                if eval "$cmd" > /dev/null 2>&1; then
                    echo "   ✅ Auto-fixed some issues"
                else
                    echo "   ⚠️  Some issues require manual fixing"
                fi
            fi
        done <<< "$FIX_COMMANDS"
        echo ""
    fi

    # Re-run linting to check if issues remain
    echo "🔍 Re-checking after auto-fix..."
    REMAINING_ERRORS=0

    while IFS= read -r cmd; do
        if [ -n "$cmd" ]; then
            if ! eval "$cmd" > /dev/null 2>&1; then
                REMAINING_ERRORS=1
            fi
        fi
    done <<< "$LINT_COMMANDS"

    if [ "$REMAINING_ERRORS" -eq 0 ]; then
        echo "   ✅ All issues resolved!"
        HAS_ERRORS=0
    else
        echo "   ⚠️  Some issues remain - please review above"
    fi
    echo ""
fi

# Run type checking with mypy (if available)
if command -v mypy &> /dev/null; then
    echo "🔬 Type checking with mypy..."

    # Run mypy on the project root
    if OUTPUT=$(cd "$CLAUDE_PROJECT_DIR" && mypy . 2>&1); then
        echo "   ✅ No type errors"
    else
        echo "   ❌ Type errors found:"
        echo "$OUTPUT" | head -20  # Show first 20 lines

        # Check if there are more lines
        LINE_COUNT=$(echo "$OUTPUT" | wc -l)
        if [ "$LINE_COUNT" -gt 20 ]; then
            echo "   ... and $((LINE_COUNT - 20)) more issues"
        fi

        HAS_TYPE_ERRORS=1

        # Try to auto-install missing type stub packages
        MISSING_STUBS=$(echo "$OUTPUT" | grep -oP 'pip install \K[a-zA-Z0-9_-]+' | sort -u)

        if [ -n "$MISSING_STUBS" ]; then
            echo ""
            echo "🔧 Attempting to install missing type stubs..."

            INSTALLED_ANY=0
            while IFS= read -r package; do
                if [ -n "$package" ]; then
                    echo "   Installing: $package"
                    if pip install "$package" > /dev/null 2>&1; then
                        echo "   ✅ Installed $package"
                        INSTALLED_ANY=1
                    else
                        echo "   ⚠️  Failed to install $package"
                    fi
                fi
            done <<< "$MISSING_STUBS"

            # Re-run mypy if we installed anything
            if [ "$INSTALLED_ANY" -eq 1 ]; then
                echo ""
                echo "🔬 Re-checking types after installing stubs..."

                # Clear mypy cache to pick up new stubs
                rm -rf "$CLAUDE_PROJECT_DIR/.mypy_cache" > /dev/null 2>&1 || true

                if OUTPUT=$(cd "$CLAUDE_PROJECT_DIR" && mypy . 2>&1); then
                    echo "   ✅ All type errors resolved!"
                    HAS_TYPE_ERRORS=0
                else
                    echo "   ⚠️  Some type errors remain:"
                    echo "$OUTPUT" | head -10  # Show fewer lines on recheck

                    REMAINING_COUNT=$(echo "$OUTPUT" | wc -l)
                    if [ "$REMAINING_COUNT" -gt 10 ]; then
                        echo "   ... and $((REMAINING_COUNT - 10)) more issues"
                    fi
                fi
            fi
        fi
    fi
    echo ""
else
    echo "💡 Tip: Install mypy for type checking (pip install mypy)"
    echo ""
fi

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ "$HAS_ERRORS" -eq 0 ] && [ "$HAS_TYPE_ERRORS" -eq 0 ]; then
    if [ "$HAS_FORMAT_CHANGES" -eq 1 ]; then
        echo "✅ Code formatted and all checks passed"
        echo "💡 Formatted files were auto-fixed"
    else
        echo "✅ All checks passed"
    fi
elif [ "$HAS_TYPE_ERRORS" -eq 1 ] && [ "$HAS_ERRORS" -eq 0 ]; then
    echo "⚠️  Type errors found (linting passed)"
    echo "💡 Review type errors above and fix manually"
elif [ "$HAS_ERRORS" -eq 1 ] && [ "$HAS_TYPE_ERRORS" -eq 0 ]; then
    echo "⚠️  Linting issues remain (type checking passed)"
    echo "💡 Review linting issues above and fix manually"
else
    echo "⚠️  Both linting and type errors found"
    echo "💡 Review the issues above and fix manually"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Don't fail the hook - just report
exit 0
