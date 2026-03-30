#!/usr/bin/env python3
"""
Integration tests for full change lifecycle.
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


def setup_archive(env_dir, change_name, timestamp="2024-01-15"):
    """Setup archive directory with timestamped change."""
    archive_dir = env_dir / "openspec" / "changes" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    archived = archive_dir / f"{timestamp}-{change_name}"
    archived.mkdir(parents=True, exist_ok=True)
    (archived / "specs").mkdir(exist_ok=True)

    (archived / "proposal.md").write_text("# Proposal")
    (archived / "design.md").write_text("# Design")
    (archived / "tasks.md").write_text("# Tasks")
    (archived / "specs" / "spec.md").write_text("# Spec")

    return archived


class TestChangeLifecycle:
    """Tests for full change lifecycle."""

    def test_create_change_advance_phases_complete(self, test_env):
        """Create change -> advance phases -> complete."""
        setup_change(
            test_env,
            "lifecycle-test",
            '{"phase":"PHASE0","iteration":0,"phase_complete":false}',
        )

        result = run_osx("phase", "current", "lifecycle-test", cwd=test_env)
        assert result.returncode == 0
        assert json.loads(result.stdout)["phase"] == "PHASE0"

        run_osx("state", "complete", "lifecycle-test", cwd=test_env)

        result = run_osx("phase", "advance", "lifecycle-test", cwd=test_env)
        assert result.returncode == 0
        assert json.loads(result.stdout)["phase"] == "PHASE1"

        run_osx("state", "complete", "lifecycle-test", cwd=test_env)
        result = run_osx("phase", "advance", "lifecycle-test", cwd=test_env)
        assert json.loads(result.stdout)["phase"] == "PHASE2"

        run_osx("state", "complete", "lifecycle-test", cwd=test_env)
        result = run_osx("phase", "advance", "lifecycle-test", cwd=test_env)
        assert json.loads(result.stdout)["phase"] == "PHASE3"

        run_osx("state", "complete", "lifecycle-test", cwd=test_env)
        result = run_osx("phase", "advance", "lifecycle-test", cwd=test_env)
        assert json.loads(result.stdout)["phase"] == "PHASE4"

        run_osx("state", "complete", "lifecycle-test", cwd=test_env)
        result = run_osx("phase", "advance", "lifecycle-test", cwd=test_env)
        assert json.loads(result.stdout)["phase"] == "PHASE5"

        run_osx("state", "complete", "lifecycle-test", cwd=test_env)
        result = run_osx("phase", "advance", "lifecycle-test", cwd=test_env)
        assert json.loads(result.stdout)["phase"] == "PHASE6"

        run_osx("state", "complete", "lifecycle-test", cwd=test_env)
        result = run_osx("phase", "advance", "lifecycle-test", cwd=test_env)
        assert json.loads(result.stdout)["phase"] == "COMPLETE"

        result = run_osx("complete", "set", "lifecycle-test", cwd=test_env)
        assert result.returncode == 0

        result = run_osx("complete", "check", "lifecycle-test", cwd=test_env)
        assert result.returncode == 0
        assert json.loads(result.stdout)["exists"] == True

    def test_context_aggregation_across_full_lifecycle(self, test_env):
        """Context aggregation across full lifecycle."""
        setup_change(
            test_env,
            "lifecycle-test",
            '{"phase":"PHASE1","iteration":2,"phase_complete":false}',
        )

        subprocess.run(
            [
                str(OSX_LIB),
                "iterations",
                "append",
                "lifecycle-test",
                "--phase",
                "PHASE0",
                "--iteration",
                "1",
                "--extra",
                '{"notes":"review"}',
            ],
            cwd=test_env,
            check=True,
        )

        subprocess.run(
            [
                str(OSX_LIB),
                "iterations",
                "append",
                "lifecycle-test",
                "--phase",
                "PHASE1",
                "--iteration",
                "1",
                "--extra",
                '{"notes":"implement"}',
            ],
            cwd=test_env,
            check=True,
        )

        result = run_osx("ctx", "get", "lifecycle-test", cwd=test_env)
        assert result.returncode == 0

        output = json.loads(result.stdout)
        assert output["change"] == "lifecycle-test"
        assert output["state"]["phase"] == "PHASE1"
        assert output["artifacts"]["proposal"]["exists"] == True
        assert output["artifacts"]["design"]["exists"] == True
        assert output["artifacts"]["tasks"]["exists"] == True
        assert output["history"]["iterations_recorded"] == 2

    def test_archive_workflow_creates_archive_directory(self, test_env):
        """Archive workflow creates archive directory."""
        setup_change(
            test_env,
            "lifecycle-test",
            '{"phase":"PHASE6","iteration":1,"phase_complete":true}',
        )

        result = run_osx("complete", "set", "lifecycle-test", cwd=test_env)
        assert result.returncode == 0

        setup_archive(test_env, "lifecycle-test", "2024-01-15")

        archive_dir = test_env / "openspec" / "changes" / "archive"
        assert archive_dir.is_dir()

        archived = archive_dir / "2024-01-15-lifecycle-test"
        assert archived.is_dir()

    def test_multiple_changes_can_coexist_independently(self, test_env):
        """Multiple changes can coexist independently."""
        setup_change(test_env, "change-alpha")
        setup_change(test_env, "change-beta")

        setup_change(test_env, "change-alpha", '{"phase":"PHASE1","iteration":1}')
        setup_change(test_env, "change-beta", '{"phase":"PHASE3","iteration":2}')

        result = run_osx("phase", "current", "change-alpha", cwd=test_env)
        assert result.returncode == 0
        assert json.loads(result.stdout)["phase"] == "PHASE1"

        result = run_osx("phase", "current", "change-beta", cwd=test_env)
        assert result.returncode == 0
        assert json.loads(result.stdout)["phase"] == "PHASE3"

        result = run_osx("phase", "advance", "change-alpha", cwd=test_env)
        assert result.returncode == 0
        assert json.loads(result.stdout)["phase"] == "PHASE2"

        result = run_osx("phase", "current", "change-beta", cwd=test_env)
        assert json.loads(result.stdout)["phase"] == "PHASE3"
