#!/bin/bash
# Agent task runner for Skim redesign - creates worktree and runs agent task

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAN_FILE="${SCRIPT_DIR}/../.opencode/plans/redesign-architecture.md"

show_help() {
    echo "Usage: $0 <agent-name> <phase> <task-file>"
    echo ""
    echo "Agents:"
    echo "  ibkr-splitter     - Phase 1.1: Split IBKRClient into auth/connection/requests/facade"
    echo "  strategy-simplify - Phase 1.2: Simplify ORHBreakoutStrategy constructor"
    echo "  cli-extractor     - Phase 1.3: Extract CLI from bot.py"
    echo "  domain-builder    - Phase 2: Build domain layer (models, strategies, repositories)"
    echo "  infra-builder     - Phase 3: Build infrastructure layer (database, brokers, factory)"
    echo "  app-builder       - Phase 4: Build application layer (events, services, commands)"
    echo "  di-container      - Phase 5: Build DI container"
    echo "  migrator          - Phase 6: Migration and cleanup"
    echo ""
    echo "Examples:"
    echo "  $0 ibkr-splitter 1.1 agents/ibkr-splitter-task.md"
    echo "  $0 domain-builder 2 agents/domain-builder-task.md"
    exit 1
}

if [ $# -lt 2 ]; then
    show_help
fi

AGENT_NAME="$1"
PHASE="$2"
TASK_FILE="$3"

# Validate agent name
VALID_AGENTS="ibkr-splitter strategy-simplify cli-extractor domain-builder infra-builder app-builder di-container migrator"
if ! echo "$VALID_AGENTS" | grep -qw "$AGENT_NAME"; then
    echo "ERROR: Unknown agent: $AGENT_NAME"
    show_help
fi

# Create branch name
BRANCH_NAME="refactor/${AGENT_NAME}-${PHASE}"

echo "============================================"
echo "Agent: $AGENT_NAME"
echo "Phase: $PHASE"
echo "Branch: $BRANCH_NAME"
echo "============================================"

# Create worktree
bash "${SCRIPT_DIR}/create-worktree.sh" "$BRANCH_NAME"

WORKTREE_PATH="../skim-$BRANCH_NAME"

# Copy task file to worktree
if [ -n "$TASK_FILE" ] && [ -f "$TASK_FILE" ]; then
    cp "$TASK_FILE" "$WORKTREE_PATH/AGENT_TASK.md"
    echo "Task file copied to worktree"
fi

# Copy plan file
cp "$PLAN_FILE" "$WORKTREE_DIR/.opencode/plans/redesign-architecture.md" 2>/dev/null || true

echo ""
echo "Worktree created at: $WORKTREE_PATH"
echo ""
echo "To work on this task:"
echo "  cd $WORKTREE_PATH"
echo ""
echo "The agent should:"
echo "  1. Read AGENT_TASK.md for specific instructions"
echo "  2. Read the plan at .opencode/plans/redesign-architecture.md"
echo "  3. Implement the changes"
echo "  4. Run tests to verify"
echo "  5. Commit changes with message following conventional commits"
echo ""
echo "After completing:"
echo "  cd $(git rev-parse --show-toplevel) && git merge $BRANCH_NAME"
