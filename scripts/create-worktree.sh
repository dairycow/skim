#!/bin/bash
# Create a git worktree in sibling directory with project setup for Skim Trading Bot

set -e

# Check for branch name argument
if [ $# -eq 0 ]; then
    echo "Usage: $0 <branch-name>"
    echo "Example: $0 feature/new-strategy"
    echo ""
    echo "This will create a worktree at: ../skim-<branch-name>/"
    exit 1
fi

BRANCH_NAME="$1"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"
PARENT_DIR="$(dirname "$PROJECT_ROOT")"

# Sanitize branch name for directory (replace / with -)
SAFE_BRANCH_NAME="${BRANCH_NAME//\//-}"
WORKTREE_PATH="$PARENT_DIR/$PROJECT_NAME-$SAFE_BRANCH_NAME"

echo "Creating worktree for branch: $BRANCH_NAME"
echo "Location: $WORKTREE_PATH"

# Check if worktree path already exists
if [ -d "$WORKTREE_PATH" ]; then
    echo "ERROR: Directory already exists: $WORKTREE_PATH"
    exit 1
fi

# Create the worktree with new branch
echo "Creating git worktree..."
git worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME"

cd "$WORKTREE_PATH"

# Copy necessary files and directories
echo "Copying project data and configuration..."

if [ -f "$PROJECT_ROOT/.env" ]; then
    echo "  ✓ Copying .env"
    cp "$PROJECT_ROOT/.env" .
else
    echo "  ⚠ WARNING: .env not found in main directory"
fi

if [ -d "$PROJECT_ROOT/data" ]; then
    echo "  ✓ Copying data/"
    cp -r "$PROJECT_ROOT/data" .
else
    echo "  ⚠ WARNING: data/ not found in main directory"
fi

if [ -d "$PROJECT_ROOT/oauth_keys" ]; then
    echo "  ✓ Copying oauth_keys/"
    cp -r "$PROJECT_ROOT/oauth_keys" .
    # Ensure correct permissions on sensitive files
    chmod 600 oauth_keys/*.pem 2>/dev/null || true
else
    echo "  ⚠ WARNING: oauth_keys/ not found in main directory"
fi

# Initialize Python environment with uv (separate venv per worktree)
echo ""
echo "Setting up Python environment with uv..."
uv venv
echo "Installing dependencies..."
uv sync

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Worktree ready at: $WORKTREE_PATH"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "To start working:"
echo "  cd $WORKTREE_PATH"
echo "  source .venv/bin/activate"
echo ""
echo "When done, remove the worktree with:"
echo "  git worktree remove $WORKTREE_PATH"
echo "  # or: rm -rf $WORKTREE_PATH && git worktree prune"
