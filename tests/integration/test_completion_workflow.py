#!/usr/bin/env python3
"""
Integration tests for completion workflow.
"""

import json
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration


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


def run_osx(domain, action, change, *args, cwd=None):
    """Run osx command and return result."""
    cmd = [str(OSX_LIB), domain, action, change] + list(args)
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


class TestCompletionWorkflow:
    """Tests for completion workflow."""

    def test_complete_set_creates_complete_json(self, test_env):
        """osc-complete set creates complete.json."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE6","iteration":1,"phase_complete":true}',
        )

        result = run_osx("complete", "set", "test-change", cwd=test_env)
        assert result.returncode == 0
        assert json.loads(result.stdout)["status"] == "COMPLETE"

        complete_file = (
            test_env / "openspec" / "changes" / "test-change" / "complete.json"
        )
        assert complete_file.is_file()

    def test_complete_check_returns_correct_status(self, test_env):
        """osc-complete check returns correct status."""
        setup_change(test_env, "test-change")

        result = run_osx("complete", "check", "test-change", cwd=test_env)
        assert result.returncode == 1
        assert json.loads(result.stdout)["exists"] == False

        run_osx("complete", "set", "test-change", cwd=test_env)

        result = run_osx("complete", "check", "test-change", cwd=test_env)
        assert result.returncode == 0
        assert json.loads(result.stdout)["exists"] == True

    def test_state_marked_complete_via_osc_state(self, test_env):
        """State is marked complete via osc-state."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE6","iteration":1,"phase_complete":false}',
        )

        result = run_osx("state", "complete", "test-change", cwd=test_env)
        assert result.returncode == 0
        assert json.loads(result.stdout)["phase_complete"] == True

        result = run_osx("state", "get", "test-change", cwd=test_env)
        assert json.loads(result.stdout)["phase_complete"] == True

    def test_iterations_json_persists_after_completion(self, test_env):
        """iterations.json persists after completion."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE6","iteration":1,"phase_complete":true}',
        )

        subprocess.run(
            [
                str(OSX_LIB),
                "iterations",
                "append",
                "test-change",
                "--phase",
                "PHASE0",
                "--iteration",
                "1",
                "--extra",
                '{"action":"start"}',
            ],
            cwd=test_env,
            check=True,
        )

        subprocess.run(
            [
                str(OSX_LIB),
                "iterations",
                "append",
                "test-change",
                "--phase",
                "PHASE1",
                "--iteration",
                "1",
                "--extra",
                '{"action":"implement"}',
            ],
            cwd=test_env,
            check=True,
        )

        run_osx("complete", "set", "test-change", cwd=test_env)

        iterations_file = (
            test_env / "openspec" / "changes" / "test-change" / "iterations.json"
        )
        assert iterations_file.is_file()

        result = run_osx("iterations", "get", "test-change", cwd=test_env)
        assert result.returncode == 0
        assert json.loads(result.stdout)["count"] == 2

    def test_full_completion_flow_with_all_artifacts(self, test_env):
        """Full completion flow with all artifacts."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE6","iteration":1,"phase_complete":true}',
        )

        result = run_osx("state", "complete", "test-change", cwd=test_env)
        assert result.returncode == 0

        result = run_osx("complete", "set", "test-change", "COMPLETE", cwd=test_env)
        assert result.returncode == 0

        result = run_osx("complete", "get", "test-change", cwd=test_env)
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["status"] == "COMPLETE"
        assert output["with_blocker"] == False

    def test_completion_with_blocker_records_reason(self, test_env):
        """Completion with blocker records reason."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE6","iteration":1,"phase_complete":true}',
        )

        result = run_osx(
            "complete",
            "set",
            "test-change",
            "BLOCKED",
            "--blocker-reason",
            "Tests failed in CI",
            cwd=test_env,
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["with_blocker"] == True
        assert output["blocker_reason"] == "Tests failed in CI"

        result = run_osx("complete", "get", "test-change", cwd=test_env)
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["with_blocker"] == True
        assert output["blocker_reason"] == "Tests failed in CI"
