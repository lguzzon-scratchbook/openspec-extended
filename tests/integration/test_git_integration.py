#!/usr/bin/env python3
"""
Integration tests for git operations with state.
"""

import json
import subprocess
from pathlib import Path

import pytest


OSX_LIB = (
    Path(__file__).parent.parent.parent
    / "resources"
    / "opencode"
    / "scripts"
    / "lib"
    / "osx"
)


@pytest.fixture
def test_env(tmp_path):
    """Create a test environment with git repo."""
    env_dir = tmp_path / "test_env"
    env_dir.mkdir()

    subprocess.run(["git", "init", "-q"], cwd=env_dir, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=env_dir, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=env_dir, check=True)

    readme = env_dir / "README.md"
    readme.write_text("# Test repo")
    subprocess.run(["git", "add", "README.md"], cwd=env_dir, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "Initial commit"], cwd=env_dir, check=True
    )

    (env_dir / "openspec" / "changes").mkdir(parents=True)
    (env_dir / ".opencode" / "skills").mkdir(parents=True)
    (env_dir / ".opencode" / "commands").mkdir(parents=True)

    for skill in ["osx-concepts", "osx-review-artifacts", "osx-modify-artifacts"]:
        skill_dir = env_dir / ".opencode" / "skills" / skill
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"# {skill}")

    for phase in range(7):
        cmd_file = env_dir / ".opencode" / "commands" / f"osx-phase{phase}.md"
        cmd_file.write_text(f"# osx-phase{phase}")

    return env_dir


def run_osx(domain, action, *args, cwd=None):
    """Run osx command and return result."""
    cmd = [str(OSX_LIB), domain, action] + list(args)
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result


def setup_change(env_dir, change_name, state_data=None):
    """Setup a change directory with required files."""
    change_dir = env_dir / "openspec" / "changes" / change_name
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "specs").mkdir(exist_ok=True)

    (change_dir / "proposal.md").write_text("# Proposal")
    (change_dir / "design.md").write_text("# Design")
    (change_dir / "tasks.md").write_text("# Tasks")
    (change_dir / "specs" / "spec.md").write_text("# Spec")

    if state_data:
        (change_dir / "state.json").write_text(state_data)

    return change_dir


class TestGitIntegration:
    """Tests for git operations with state."""

    def test_baseline_recorded_with_commit_hash(self, test_env):
        """Baseline is recorded with commit hash."""
        result = run_osx("baseline", "record", cwd=test_env)
        assert result.returncode == 0

        baseline_file = test_env / ".openspec-baseline.json"
        assert baseline_file.is_file()

        baseline = json.loads(baseline_file.read_text())
        assert baseline["commit"] is not None
        assert baseline["commit"] != "null"
        assert len(baseline["commit"]) == 40
        assert all(c in "0123456789abcdef" for c in baseline["commit"])

    def test_baseline_persists_across_state_operations(self, test_env):
        """Baseline persists across state operations."""
        result = run_osx("baseline", "record", cwd=test_env)
        assert result.returncode == 0

        baseline_file = test_env / ".openspec-baseline.json"
        recorded_commit = json.loads(baseline_file.read_text())["commit"]

        setup_change(test_env, "test-change", '{"phase":"PHASE0","iteration":1}')

        result = run_osx("phase", "advance", "test-change", cwd=test_env)
        assert result.returncode == 0

        result = run_osx("baseline", "get", cwd=test_env)
        assert result.returncode == 0
        assert json.loads(result.stdout)["commit"] == recorded_commit

    def test_git_status_integrates_with_context(self, test_env):
        """Git status integrates with context."""
        setup_change(test_env, "test-change", '{"phase":"PHASE1","iteration":1}')

        test_file = test_env / "openspec" / "changes" / "test-change" / "test-file.txt"
        test_file.write_text("test content")

        subprocess.run(
            ["git", "add", "openspec/changes/test-change/test-file.txt"],
            cwd=test_env,
            check=True,
        )

        result = run_osx("git", "get", "test-change", cwd=test_env)
        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert len(output.get("added", [])) >= 1

    def test_branch_name_captured_correctly(self, test_env):
        """Branch name is captured correctly."""
        result = run_osx("baseline", "record", cwd=test_env)
        assert result.returncode == 0

        baseline_file = test_env / ".openspec-baseline.json"
        baseline = json.loads(baseline_file.read_text())
        assert baseline["branch"] is not None
        assert baseline["branch"] != "null"

    def test_git_status_detects_untracked_files(self, test_env):
        """Git status detects untracked files in change directory."""
        setup_change(test_env, "test-change", '{"phase":"PHASE1","iteration":1}')

        subprocess.run(
            ["git", "add", "openspec/changes/test-change/proposal.md"],
            cwd=test_env,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-q", "-m", "Track change files"],
            cwd=test_env,
            check=True,
        )

        new_dir = test_env / "openspec" / "changes" / "test-change" / "newdir"
        new_dir.mkdir()
        untracked = new_dir / "untracked.md"
        untracked.write_text("new file")

        result = run_osx("git", "get", "test-change", cwd=test_env)
        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert len(output.get("untracked", [])) >= 1

    def test_git_status_reflects_change_directory_modifications(self, test_env):
        """Git status reflects change directory modifications."""
        setup_change(test_env, "test-change", '{"phase":"PHASE1","iteration":1}')

        subprocess.run(
            ["git", "add", "openspec/changes/test-change/"], cwd=test_env, check=True
        )
        subprocess.run(
            ["git", "commit", "-q", "-m", "Track change files"],
            cwd=test_env,
            check=True,
        )

        proposal = test_env / "openspec" / "changes" / "test-change" / "proposal.md"
        proposal.write_text(proposal.read_text() + "\nmodified content")

        result = run_osx("git", "get", "test-change", cwd=test_env)
        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert len(output.get("modified", [])) >= 1
