#!/bin/bash
# Delegation script for Skim redesign agents
# Creates worktrees and prepares agent tasks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLAN_FILE="${SCRIPT_DIR}/../.opencode/plans/redesign-architecture.md"
TASKS_DIR="${SCRIPT_DIR}/tasks"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[+]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[-]${NC} $1"
}

show_help() {
    echo "Skim Redesign Agent Delegation"
    echo ""
    echo "Usage: $0 <command> [agent]"
    echo ""
    echo "Commands:"
    echo "  list              - List all available agents"
    echo "  launch <agent>    - Create worktree and prepare agent task"
    echo "  all               - Launch all agents in parallel"
    echo "  status <agent>    - Check status of agent worktree"
    echo "  merge <agent>     - Merge agent worktree back to main"
    echo ""
    echo "Agents:"
    echo "  ibkr-splitter     - Phase 1.1: Split IBKRClient"
    echo "  strategy-simplify - Phase 1.2: Simplify strategy constructor"
    echo "  cli-extractor     - Phase 1.3: Extract CLI"
    echo "  domain-builder    - Phase 2: Build domain layer"
    echo "  infra-builder     - Phase 3: Build infrastructure"
    echo "  app-builder       - Phase 4: Build application layer"
    echo "  di-container      - Phase 5: Build DI container"
    echo "  migrator          - Phase 6: Migration and cleanup"
    echo ""
    echo "Examples:"
    echo "  $0 list"
    echo "  $0 launch ibkr-splitter"
    echo "  $0 merge strategy-simplify"
}

list_agents() {
    echo "Available Agents:"
    echo ""
    echo "Phase 1 (Week 1-2) - Break Down Large Classes:"
    echo "  1. ibkr-splitter     - Split IBKRClient into 4 classes"
    echo "  2. strategy-simplify - Reduce strategy params to 1 context"
    echo "  3. cli-extractor     - Extract CLI into separate module"
    echo ""
    echo "Phase 2 (Week 3-4) - Build Domain Core:"
    echo "  4. domain-builder    - Create domain models and protocols"
    echo ""
    echo "Phase 3 (Week 5-6) - Build Infrastructure:"
    echo "  5. infra-builder     - Unified database, broker factory"
    echo ""
    echo "Phase 4 (Week 7-8) - Build Application Layer:"
    echo "  6. app-builder       - Event bus, trading service"
    echo ""
    echo "Phase 5 (Week 9) - DI Container:"
    echo "  7. di-container      - Dependency injection container"
    echo ""
    echo "Phase 6 (Week 10) - Migration:"
    echo "  8. migrator          - Migrate ORH, update tests, cleanup"
}

launch_agent() {
    local AGENT_NAME="$1"
    local PHASE="$2"
    local TASK_FILE="${TASKS_DIR}/${AGENT_NAME}-task.md"
    
    if [ ! -f "$TASK_FILE" ]; then
        print_error "Task file not found: $TASK_FILE"
        exit 1
    fi
    
    local BRANCH_NAME="refactor/${AGENT_NAME}-${PHASE}"
    local WORKTREE_PATH="../skim-${BRANCH_NAME}"
    
    print_status "Launching agent: $AGENT_NAME"
    print_status "Branch: $BRANCH_NAME"
    print_status "Phase: $PHASE"
    echo ""
    
    # Check if worktree already exists
    if [ -d "$WORKTREE_PATH" ]; then
        print_warning "Worktree already exists: $WORKTREE_PATH"
        echo "To continue working:"
        echo "  cd $WORKTREE_PATH"
        echo "  cat AGENT_TASK.md"
        return
    fi
    
    # Create worktree
    print_status "Creating worktree..."
    bash "${SCRIPT_DIR}/../create-worktree.sh" "$BRANCH_NAME"
    
    # Copy task file
    print_status "Copying task file..."
    cp "$TASK_FILE" "$WORKTREE_PATH/AGENT_TASK.md"
    
    # Copy plan
    mkdir -p "$WORKTREE_PATH/.opencode/plans"
    cp "$PLAN_FILE" "$WORKTREE_PATH/.opencode/plans/redesign-architecture.md"
    
    echo ""
    print_status "Worktree ready at: $WORKTREE_PATH"
    echo ""
    echo "Next steps:"
    echo "  1. cd $WORKTREE_PATH"
    echo "  2. Read AGENT_TASK.md for instructions"
    echo "  3. Read .opencode/plans/redesign-architecture.md for context"
    echo "  4. Implement the changes"
    echo "  5. Run tests: uv run pytest"
    echo "  6. Commit changes"
    echo ""
    echo "When done, merge with:"
    echo "  cd $(git rev-parse --show-toplevel) && $0 merge $AGENT_NAME"
}

merge_agent() {
    local AGENT_NAME="$1"
    local PHASE="$2"
    local BRANCH_NAME="refactor/${AGENT_NAME}-${PHASE}"
    
    print_status "Merging agent: $AGENT_NAME"
    print_status "Branch: $BRANCH_NAME"
    echo ""
    
    # Check if branch exists
    if ! git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
        print_error "Branch not found: $BRANCH_NAME"
        exit 1
    fi
    
    # Check for uncommitted changes
    if git diff --quiet && git diff --cached --quiet; then
        print_status "No uncommitted changes"
    else
        print_warning "Uncommitted changes detected"
        echo "Stash or commit before merging"
        exit 1
    fi
    
    # Merge
    print_status "Merging into main..."
    git checkout main
    git merge --no-ff "$BRANCH_NAME" -m "Merge pull request for ${AGENT_NAME}"
    
    # Remove worktree
    local WORKTREE_PATH="../skim-${BRANCH_NAME}"
    if [ -d "$WORKTREE_PATH" ]; then
        print_status "Removing worktree..."
        git worktree remove "$WORKTREE_PATH"
    fi
    
    # Remove branch
    print_status "Removing branch..."
    git branch -d "$BRANCH_NAME"
    
    print_status "Done! Merged ${AGENT_NAME} into main"
}

launch_all() {
    echo "Launching all agents in parallel..."
    echo ""
    
    # Phase 1 agents can run in parallel
    launch_agent "ibkr-splitter" "1.1" &
    launch_agent "strategy-simplify" "1.2" &
    launch_agent "cli-extractor" "1.3" &
    wait
    
    echo ""
    echo "Phase 1 worktrees created. Continuing with next phases..."
    echo ""
    
    # Phase 2 can run
    launch_agent "domain-builder" "2" &
    wait
    
    # Phase 3 can run
    launch_agent "infra-builder" "3" &
    wait
    
    # Phase 4 can run
    launch_agent "app-builder" "4" &
    wait
    
    # Phase 5 can run
    launch_agent "di-container" "5" &
    wait
    
    # Phase 6 depends on 1-5
    launch_agent "migrator" "6" &
    wait
    
    echo ""
    print_status "All agents launched!"
}

# Main
case "$1" in
    list)
        list_agents
        ;;
    launch)
        if [ -z "$2" ]; then
            print_error "Agent name required"
            show_help
            exit 1
        fi
        # Map agent name to phase
        case "$2" in
            ibkr-splitter) PHASE="1.1" ;;
            strategy-simplify) PHASE="1.2" ;;
            cli-extractor) PHASE="1.3" ;;
            domain-builder) PHASE="2" ;;
            infra-builder) PHASE="3" ;;
            app-builder) PHASE="4" ;;
            di-container) PHASE="5" ;;
            migrator) PHASE="6" ;;
            *)
                print_error "Unknown agent: $2"
                show_help
                exit 1
                ;;
        esac
        launch_agent "$2" "$PHASE"
        ;;
    merge)
        if [ -z "$2" ]; then
            print_error "Agent name required"
            show_help
            exit 1
        fi
        case "$2" in
            ibkr-splitter) PHASE="1.1" ;;
            strategy-simplify) PHASE="1.2" ;;
            cli-extractor) PHASE="1.3" ;;
            domain-builder) PHASE="2" ;;
            infra-builder) PHASE="3" ;;
            app-builder) PHASE="4" ;;
            di-container) PHASE="5" ;;
            migrator) PHASE="6" ;;
            *)
                print_error "Unknown agent: $2"
                show_help
                exit 1
                ;;
        esac
        merge_agent "$2" "$PHASE"
        ;;
    all)
        launch_all
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
