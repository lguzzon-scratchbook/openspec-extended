#!/usr/bin/env python3
"""
Unit tests for osx-orchestrate state machine and signal handling.
"""

import json
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import patch, MagicMock

import pytest

scripts_path = Path(__file__).parent.parent.parent / "resources/opencode/scripts"
sys.path.insert(0, str(scripts_path))

osx_orchestrate_module = ModuleType("osx_orchestrate")
osx_orchestrate_module.__file__ = str(scripts_path / "osx-orchestrate.py")

osx_code = (scripts_path / "osx-orchestrate.py").read_text()
exec(
    compile(osx_code, scripts_path / "osx-orchestrate.py", "exec"),
    osx_orchestrate_module.__dict__,
)

orch = osx_orchestrate_module


@pytest.fixture
def temp_change_dir(tmp_path):
    """Create temporary change directory structure."""
    change_dir = tmp_path / "openspec" / "changes" / "test-change"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text("# Tasks")
    (change_dir / "proposal.md").write_text("# Proposal")
    (change_dir / "design.md").write_text("# Design")
    specs_dir = change_dir / "specs"
    specs_dir.mkdir()
    (specs_dir / "spec.md").write_text("# Spec")
    return change_dir


@pytest.fixture
def archived_change_dir(tmp_path):
    """Create archived change directory."""
    archive_dir = tmp_path / "openspec" / "changes" / "archive"
    archived = archive_dir / "2024-01-15-test-change"
    archived.mkdir(parents=True)
    return archived


@pytest.fixture(autouse=True)
def reset_state():
    """Reset orch.state before each test."""
    orch.state = orch.State()
    yield
    orch.state = orch.State()


class TestStateMachine:
    """Tests for state machine phase transitions."""

    def test_phase_transition_normal_advance(self, temp_change_dir, monkeypatch):
        """Normal advance when no explicit transition set."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)

        state_file = temp_change_dir / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "phase": "PHASE0",
                    "iteration": 1,
                    "phase_complete": True,
                    "phase_iterations": {"PHASE0": 1},
                }
            )
        )

        orch.state.change_dir = temp_change_dir
        has_transition, target = orch.check_transition()

        assert has_transition is False
        assert target == ""

    def test_phase_transition_explicit(self, temp_change_dir, monkeypatch):
        """Explicit transition when set in state."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)

        state_file = temp_change_dir / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "phase": "PHASE2",
                    "iteration": 1,
                    "phase_complete": True,
                    "transition": {
                        "target": "PHASE1",
                        "reason": "implementation_incorrect",
                    },
                }
            )
        )

        orch.state.change_dir = temp_change_dir
        has_transition, target = orch.check_transition()

        assert has_transition is True
        assert target == "PHASE1"

    def test_phase_transition_missing_state(self, temp_change_dir, monkeypatch):
        """Handles missing state.json gracefully."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)
        orch.state.change_dir = temp_change_dir

        has_transition, target = orch.check_transition()

        assert has_transition is False
        assert target == ""

    def test_phase_iterations_tracking(self, temp_change_dir, monkeypatch):
        """Iteration counts per phase are tracked correctly."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)

        state_file = temp_change_dir / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "phase": "PHASE4",
                    "iteration": 1,
                    "phase_complete": False,
                    "phase_iterations": {
                        "PHASE0": 1,
                        "PHASE1": 2,
                        "PHASE2": 1,
                        "PHASE3": 1,
                        "PHASE4": 1,
                    },
                }
            )
        )

        orch.state.change_dir = temp_change_dir
        data = orch.read_state()

        assert data["phase_iterations"]["PHASE0"] == 1
        assert data["phase_iterations"]["PHASE1"] == 2
        assert data["phase_iterations"]["PHASE2"] == 1

    def test_check_complete_detection(self, temp_change_dir, monkeypatch):
        """COMPLETE signal detection via complete.json."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)
        orch.state.change_dir = temp_change_dir
        orch.state.change_id = "test-change"

        with patch.object(orch, "run_osx_command") as mock_cmd:
            mock_cmd.return_value = (json.dumps({"valid": True}), 0)
            result = orch.check_complete()
            assert result is True


class TestPhaseLookup:
    """Tests for phase name/command/agent lookups."""

    def test_get_phase_name(self):
        """Correct phase names returned."""
        assert orch.PHASE_NAMES["PHASE0"] == "ARTIFACT REVIEW"
        assert orch.PHASE_NAMES["PHASE1"] == "IMPLEMENTATION"
        assert orch.PHASE_NAMES["PHASE2"] == "REVIEW"
        assert orch.PHASE_NAMES["PHASE3"] == "MAINTAIN DOCS"
        assert orch.PHASE_NAMES["PHASE4"] == "SYNC"
        assert orch.PHASE_NAMES["PHASE5"] == "SELF-REFLECTION"
        assert orch.PHASE_NAMES["PHASE6"] == "ARCHIVE"

    def test_get_phase_command(self):
        """Correct phase commands returned."""
        assert orch.PHASE_COMMANDS["PHASE0"] == "osx-phase0"
        assert orch.PHASE_COMMANDS["PHASE1"] == "osx-phase1"
        assert orch.PHASE_COMMANDS["PHASE2"] == "osx-phase2"
        assert orch.PHASE_COMMANDS["PHASE3"] == "osx-phase3"
        assert orch.PHASE_COMMANDS["PHASE4"] == "osx-phase4"
        assert orch.PHASE_COMMANDS["PHASE5"] == "osx-phase5"
        assert orch.PHASE_COMMANDS["PHASE6"] == "osx-phase6"

    def test_get_phase_agent(self):
        """Correct phase agents returned."""
        assert orch.PHASE_AGENTS["PHASE0"] == "osx-analyzer"
        assert orch.PHASE_AGENTS["PHASE1"] == "osx-builder"
        assert orch.PHASE_AGENTS["PHASE2"] == "osx-analyzer"
        assert orch.PHASE_AGENTS["PHASE3"] == "osx-maintainer"
        assert orch.PHASE_AGENTS["PHASE4"] == "osx-maintainer"
        assert orch.PHASE_AGENTS["PHASE5"] == "osx-analyzer"
        assert orch.PHASE_AGENTS["PHASE6"] == "osx-maintainer"

    def test_valid_transition_reasons(self):
        """All valid transition reasons are accepted."""
        assert "implementation_incorrect" in orch.VALID_TRANSITION_REASONS
        assert "artifacts_modified" in orch.VALID_TRANSITION_REASONS
        assert "retry_requested" in orch.VALID_TRANSITION_REASONS


class TestChangeDirectory:
    """Tests for change directory resolution."""

    def test_find_change_dir_primary(self, temp_change_dir, monkeypatch):
        """Finds change in primary openspec/changes location."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)

        result = orch.find_change_dir("test-change")

        assert result is not None
        assert result.name == "test-change"
        assert result.parent.name == "changes"

    def test_find_change_dir_archived(self, tmp_path, monkeypatch):
        """Finds change in archive directory."""
        archive_dir = tmp_path / "openspec/changes/archive"
        archive_dir.mkdir(parents=True)
        archived = archive_dir / "2024-01-15-test-change"
        archived.mkdir()

        monkeypatch.chdir(tmp_path)

        result = orch.find_change_dir("test-change")

        assert result is not None
        assert "archive" in str(result)
        assert result.name.endswith("-test-change")

    def test_find_change_dir_not_found(self, tmp_path, monkeypatch):
        """Returns None if change not found."""
        monkeypatch.chdir(tmp_path)

        result = orch.find_change_dir("nonexistent")

        assert result is None


class TestLogging:
    """Tests for logging behavior."""

    def test_verbose_flag_controls_output(self, capsys):
        """Verbose flag enables VERBOSE output to terminal."""
        orch.state.verbose = True
        orch.state.no_color = True

        orch.log_verbose("Test verbose message")

        captured = capsys.readouterr()
        assert "[VERBOSE]" in captured.out
        assert "Test verbose message" in captured.out

    def test_no_color_flag_strips_ansi(self, capsys):
        """no_color flag removes ANSI codes."""
        orch.state.verbose = True
        orch.state.no_color = True

        orch.log_verbose("Test message")

        captured = capsys.readouterr()
        assert "\x1b[" not in captured.out

    def test_log_file_receives_all_output(self, temp_change_dir, capsys):
        """Log file contains verbose messages even without -v flag."""
        log_file = temp_change_dir / "test.log"
        log_file.touch()
        orch.state.verbose = False
        orch.state.no_color = True
        orch.state.log_file = log_file

        orch.log_verbose("Verbose to log file")

        log_content = log_file.read_text()
        assert "Verbose to log file" in log_content


class TestArchive:
    """Tests for log file archiving."""

    def test_archive_log_file_early_return(self, temp_change_dir):
        """Early return when no log file exists."""
        orch.state.log_file = None

        result = orch.archive_log_file()

        assert result is True

    def test_archive_log_file_user_specified(self, temp_change_dir):
        """User-specified log file is not archived."""
        log_file = temp_change_dir / "user-specified.log"
        log_file.write_text("user log content")
        orch.state.log_file = log_file
        orch.state.log_user_specified = True

        result = orch.archive_log_file()

        assert result is True
        assert log_file.exists()

    def test_archive_validation(self, temp_change_dir, monkeypatch):
        """Validates archive path from osx output."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)
        orch.state.change_dir = temp_change_dir
        orch.state.change_id = "test-change"
        orch.state.log_file = temp_change_dir / "test.log"
        orch.state.log_file.touch()

        archive_dir = temp_change_dir.parent / "archive" / "2024-01-15-test-change"
        archive_dir.mkdir(parents=True)

        with patch.object(orch, "run_osx_command") as mock_cmd:
            mock_cmd.return_value = (
                json.dumps({"valid": True, "archive": str(archive_dir)}),
                0,
            )
            with patch("shutil.move") as mock_move:
                mock_move.return_value = None
                with patch("subprocess.run") as mock_git:
                    mock_git.return_value = MagicMock(returncode=0)
                    result = orch.archive_log_file()

            assert result is True


class TestAdvancePhase:
    """Tests for phase advancement logic."""

    def test_advance_phase_normal_sequence(self):
        """Phases advance in correct order."""
        assert orch.advance_phase("PHASE0") == "PHASE1"
        assert orch.advance_phase("PHASE1") == "PHASE2"
        assert orch.advance_phase("PHASE2") == "PHASE3"
        assert orch.advance_phase("PHASE3") == "PHASE4"
        assert orch.advance_phase("PHASE4") == "PHASE5"
        assert orch.advance_phase("PHASE5") == "PHASE6"
        assert orch.advance_phase("PHASE6") == "COMPLETE"

    def test_advance_phase_complete_stays_complete(self):
        """COMPLETE remains COMPLETE."""
        assert orch.advance_phase("COMPLETE") == "COMPLETE"


class TestGetTransitionReason:
    """Tests for transition reason retrieval."""

    def test_get_transition_reason_valid(self, temp_change_dir, monkeypatch):
        """Returns reason when transition is set."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)

        state_file = temp_change_dir / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "phase": "PHASE2",
                    "iteration": 1,
                    "transition": {
                        "reason": "artifacts_modified",
                        "details": "Spec updated",
                    },
                }
            )
        )

        orch.state.change_dir = temp_change_dir
        reason = orch.get_transition_reason()
        details = orch.get_transition_details()

        assert reason == "artifacts_modified"
        assert details == "Spec updated"

    def test_get_transition_reason_missing(self, temp_change_dir, monkeypatch):
        """Returns 'unknown' when no transition set."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)

        state_file = temp_change_dir / "state.json"
        state_file.write_text(json.dumps({"phase": "PHASE0"}))

        orch.state.change_dir = temp_change_dir
        reason = orch.get_transition_reason()

        assert reason == "unknown"


class TestReadWriteState:
    """Tests for state file read/write operations."""

    def test_write_state_creates_file(self, temp_change_dir, monkeypatch):
        """write_state creates state.json file."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)
        orch.state.change_dir = temp_change_dir
        orch.state.total_invocations = 0

        orch.write_state("PHASE0", 1)

        state_file = temp_change_dir / "state.json"
        assert state_file.exists()

        data = json.loads(state_file.read_text())
        assert data["phase"] == "PHASE0"
        assert data["iteration"] == 1

    def test_write_state_increments_phase_iterations(
        self, temp_change_dir, monkeypatch
    ):
        """write_state increments phase iteration count."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)
        orch.state.change_dir = temp_change_dir
        orch.state.total_invocations = 0

        state_file = temp_change_dir / "state.json"
        state_file.write_text(
            json.dumps({"phase": "PHASE0", "phase_iterations": {"PHASE0": 1}})
        )

        orch.write_state("PHASE0", 2)

        data = json.loads(state_file.read_text())
        assert data["phase_iterations"]["PHASE0"] == 2

    def test_read_state_missing_file(self, temp_change_dir, monkeypatch):
        """read_state returns None when file missing."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)
        orch.state.change_dir = temp_change_dir

        result = orch.read_state()

        assert result is None

    def test_read_state_invalid_json(self, temp_change_dir, monkeypatch):
        """read_state returns None for corrupted state."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)
        orch.state.change_dir = temp_change_dir

        state_file = temp_change_dir / "state.json"
        state_file.write_text("not valid json")

        result = orch.read_state()

        assert result is None


class TestCheckPhaseComplete:
    """Tests for phase completion detection."""

    def test_check_phase_complete_true(self, temp_change_dir, monkeypatch):
        """Returns True when phase_complete is true."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)

        state_file = temp_change_dir / "state.json"
        state_file.write_text(
            json.dumps({"phase": "PHASE0", "iteration": 1, "phase_complete": True})
        )

        orch.state.change_dir = temp_change_dir
        result = orch.check_phase_complete()

        assert result is True

    def test_check_phase_complete_false(self, temp_change_dir, monkeypatch):
        """Returns False when phase_complete is false."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)

        state_file = temp_change_dir / "state.json"
        state_file.write_text(json.dumps({"phase": "PHASE0", "phase_complete": False}))

        orch.state.change_dir = temp_change_dir
        result = orch.check_phase_complete()

        assert result is False
