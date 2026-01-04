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

# Check if worktree path already exists
if [ -d "$WORKTREE_PATH" ]; then
    echo "ERROR: Directory already exists: $WORKTREE_PATH"
    exit 1
fi

# Create the worktree with new branch
git worktree add "$WORKTREE_PATH" -b "$BRANCH_NAME"

cd "$WORKTREE_PATH"

# Copy necessary files and directories
cp "$PROJECT_ROOT/.env" . 2>/dev/null || true
cp -r "$PROJECT_ROOT/.vscode" . 2>/dev/null || true
if [ -d "$PROJECT_ROOT/oauth_keys" ]; then
    cp -r "$PROJECT_ROOT/oauth_keys" .
    # Ensure correct permissions on sensitive files
    chmod 600 oauth_keys/*.pem 2>/dev/null || true
fi

# Initialize Python environment with uv (separate venv per worktree)
uv venv
uv sync

echo "Worktree ready at: $WORKTREE_PATH"
echo ""
echo "To merge into main and clean up:"
echo "1. cd $PROJECT_ROOT && git merge $BRANCH_NAME"
echo "2. git worktree remove $WORKTREE_PATH"
echo "3. git branch -d $BRANCH_NAME"
echo ""

echo "Now cd into the worktree:"
echo "cd $WORKTREE_PATH"
