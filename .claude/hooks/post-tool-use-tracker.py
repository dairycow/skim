#!/usr/bin/env python3
"""
Post-tool-use hook that tracks edited files and their repos.
This runs after Edit, MultiEdit, or Write tools complete successfully.

Adapted for Python projects using pyproject.toml, ruff, pytest, etc.
"""

import json
import sys
import os
import re
from pathlib import Path
from typing import Optional
from datetime import datetime


def detect_repo(file_path: str, project_root: str) -> Optional[str]:
    """Detect repo from file path."""
    # Remove project root from path
    relative_path = file_path.replace(f"{project_root}/", "", 1)

    # Extract first directory component
    parts = relative_path.split('/')
    if not parts:
        return None

    repo = parts[0]

    # Common Python project directory patterns
    python_src_patterns = ['src', 'lib', 'app', 'api', 'services']
    test_patterns = ['tests', 'test', 'pytest']
    docs_patterns = ['docs', 'documentation']
    script_patterns = ['scripts', 'bin', 'tools']

    if repo in python_src_patterns or repo in test_patterns or repo in docs_patterns or repo in script_patterns:
        return repo

    # Package/monorepo structure
    if repo == 'packages':
        if len(parts) >= 2:
            return f"packages/{parts[1]}"
        return repo

    # Check if it's a source file in root
    if len(parts) == 1:
        return 'root'

    return 'unknown'


def get_lint_command(repo: str, project_root: str) -> Optional[str]:
    """Get linting command for Python repo."""
    repo_path = Path(project_root) / repo if repo != 'root' else Path(project_root)
    pyproject_toml = repo_path / 'pyproject.toml' if repo != 'root' else Path(project_root) / 'pyproject.toml'

    # Check if pyproject.toml exists
    if pyproject_toml.exists():
        try:
            with open(pyproject_toml, 'r') as f:
                content = f.read()

                # Check for ruff configuration
                if '[tool.ruff' in content:
                    if repo == 'root':
                        return f"cd {project_root} && ruff check ."
                    else:
                        return f"cd {repo_path} && ruff check ."

                # Check for flake8
                if '[tool.flake8' in content or 'flake8' in content:
                    if repo == 'root':
                        return f"cd {project_root} && flake8 ."
                    else:
                        return f"cd {repo_path} && flake8 ."

                # Check for pylint
                if '[tool.pylint' in content or 'pylint' in content:
                    if repo == 'root':
                        return f"cd {project_root} && pylint ."
                    else:
                        return f"cd {repo_path} && pylint ."
        except (IOError, Exception):
            pass

    # Check for .flake8 or setup.cfg
    for config_file in ['.flake8', 'setup.cfg', 'tox.ini']:
        if (repo_path / config_file).exists():
            if repo == 'root':
                return f"cd {project_root} && flake8 ."
            else:
                return f"cd {repo_path} && flake8 ."

    # Default to ruff if no config found but it's a Python file
    if repo == 'root':
        return f"cd {project_root} && ruff check ."
    else:
        return f"cd {repo_path} && ruff check ."


def get_format_command(repo: str, project_root: str) -> Optional[str]:
    """Get formatting command for Python repo."""
    repo_path = Path(project_root) / repo if repo != 'root' else Path(project_root)
    pyproject_toml = repo_path / 'pyproject.toml' if repo != 'root' else Path(project_root) / 'pyproject.toml'

    # Check if pyproject.toml exists
    if pyproject_toml.exists():
        try:
            with open(pyproject_toml, 'r') as f:
                content = f.read()

                # Check for ruff formatter
                if '[tool.ruff.format' in content or '[tool.ruff' in content:
                    if repo == 'root':
                        return f"cd {project_root} && ruff format ."
                    else:
                        return f"cd {repo_path} && ruff format ."

                # Check for black
                if '[tool.black' in content or 'black' in content:
                    if repo == 'root':
                        return f"cd {project_root} && black ."
                    else:
                        return f"cd {repo_path} && black ."
        except (IOError, Exception):
            pass

    # Default to ruff format if no config found
    if repo == 'root':
        return f"cd {project_root} && ruff format ."
    else:
        return f"cd {repo_path} && ruff format ."


def get_test_command(repo: str, project_root: str) -> Optional[str]:
    """Get test command for Python repo."""
    repo_path = Path(project_root) / repo if repo != 'root' else Path(project_root)

    # Check for pytest
    if (repo_path / 'pytest.ini').exists() or (repo_path / 'tests').exists():
        if repo == 'root':
            return f"cd {project_root} && pytest"
        else:
            return f"cd {repo_path} && pytest"

    # Check for pyproject.toml with pytest config
    pyproject_toml = repo_path / 'pyproject.toml' if repo != 'root' else Path(project_root) / 'pyproject.toml'
    if pyproject_toml.exists():
        try:
            with open(pyproject_toml, 'r') as f:
                content = f.read()
                if '[tool.pytest' in content:
                    if repo == 'root':
                        return f"cd {project_root} && pytest"
                    else:
                        return f"cd {repo_path} && pytest"
        except (IOError, Exception):
            pass

    # Check for unittest
    if (repo_path / 'tests').exists():
        if repo == 'root':
            return f"cd {project_root} && python -m unittest discover"
        else:
            return f"cd {repo_path} && python -m unittest discover"

    return None


def main():
    try:
        # Read tool information from stdin
        tool_info_json = sys.stdin.read()
        tool_info = json.loads(tool_info_json)

        # Extract relevant data
        tool_name = tool_info.get('tool_name', '')
        file_path = tool_info.get('tool_input', {}).get('file_path', '')
        session_id = tool_info.get('session_id', 'default')

        # Skip if not an edit tool or no file path
        if tool_name not in ['Edit', 'MultiEdit', 'Write'] or not file_path:
            sys.exit(0)

        # Skip markdown files
        if re.search(r'\.(md|markdown|rst|txt)$', file_path):
            sys.exit(0)

        # Skip if not a Python file
        if not re.search(r'\.py$', file_path):
            sys.exit(0)

        # Get project directory
        project_dir = os.environ.get('CLAUDE_PROJECT_DIR', '')
        if not project_dir:
            sys.exit(0)

        # Create cache directory in project
        cache_dir = Path(project_dir) / '.claude' / 'python-cache' / session_id
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Detect repo
        repo = detect_repo(file_path, project_dir)

        # Skip if unknown repo
        if not repo or repo == 'unknown':
            sys.exit(0)

        # Log edited file
        timestamp = int(datetime.now().timestamp())
        edited_files_log = cache_dir / 'edited-files.log'
        with open(edited_files_log, 'a') as f:
            f.write(f"{timestamp}:{file_path}:{repo}\n")

        # Update affected repos list
        affected_repos_file = cache_dir / 'affected-repos.txt'
        existing_repos = set()
        if affected_repos_file.exists():
            existing_repos = set(affected_repos_file.read_text().strip().split('\n'))

        if repo not in existing_repos:
            with open(affected_repos_file, 'a') as f:
                f.write(f"{repo}\n")

        # Store commands
        commands_tmp = cache_dir / 'commands.txt.tmp'
        lint_cmd = get_lint_command(repo, project_dir)
        format_cmd = get_format_command(repo, project_dir)
        test_cmd = get_test_command(repo, project_dir)

        with open(commands_tmp, 'a') as f:
            if lint_cmd:
                f.write(f"{repo}:lint:{lint_cmd}\n")
            if format_cmd:
                f.write(f"{repo}:format:{format_cmd}\n")
            if test_cmd:
                f.write(f"{repo}:test:{test_cmd}\n")

        # Remove duplicates from commands
        if commands_tmp.exists():
            commands = set(commands_tmp.read_text().strip().split('\n'))
            commands_file = cache_dir / 'commands.txt'
            commands_file.write_text('\n'.join(sorted(commands)) + '\n')
            commands_tmp.unlink()

        # Exit cleanly
        sys.exit(0)

    except Exception as err:
        # Silent failure - don't interrupt the workflow
        sys.exit(0)


if __name__ == '__main__':
    main()
