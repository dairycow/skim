#!/bin/bash
# Merge a git worktree branch into main and clean up the worktree

set -e

# Check for branch name argument
if [ $# -eq 0 ]; then
    echo "Usage: $0 <branch-name>"
    echo "Example: $0 feature/new-strategy"
    echo ""
    echo "This will:"
    echo "1. Check for uncommitted changes in the worktree"
    echo "2. Switch to main in the main repo"
    echo "3. Merge the branch into main"
    echo "4. Remove the worktree"
    echo "5. Delete the branch"
    exit 1
fi

BRANCH_NAME="$1"
PROJECT_ROOT="$(git rev-parse --show-toplevel)"
PROJECT_NAME="$(basename "$PROJECT_ROOT")"
PARENT_DIR="$(dirname "$PROJECT_ROOT")"

# Sanitize branch name for directory (replace / with -)
SAFE_BRANCH_NAME="${BRANCH_NAME//\//-}"
WORKTREE_PATH="$PARENT_DIR/$PROJECT_NAME-$SAFE_BRANCH_NAME"

# Check if worktree exists
if [ ! -d "$WORKTREE_PATH" ]; then
    echo "ERROR: Worktree directory does not exist: $WORKTREE_PATH"
    exit 1
fi

# Check for uncommitted changes in the worktree
echo "Checking for uncommitted changes in worktree..."
cd "$WORKTREE_PATH"
if [ -n "$(git status --porcelain)" ]; then
    echo "ERROR: Uncommitted changes found in worktree:"
    git status --short
    echo ""
    echo "Please commit or stash your changes before merging."
    exit 1
fi
cd "$PROJECT_ROOT"

# Switch to main
echo "Switching to main branch..."
git checkout main

# Pull latest changes from main
echo "Pulling latest changes from main..."
git pull origin main

# Merge the branch
echo "Merging $BRANCH_NAME into main..."
git merge "$BRANCH_NAME"

# Remove the worktree
echo "Removing worktree at: $WORKTREE_PATH"
git worktree remove "$WORKTREE_PATH"

# Delete the branch
echo "Deleting branch: $BRANCH_NAME"
git branch -d "$BRANCH_NAME"

echo ""
echo "Successfully merged $BRANCH_NAME into main and cleaned up worktree."
