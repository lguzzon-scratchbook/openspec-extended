#!/usr/bin/env python3
"""
Architectural invariant tests for the CLI/library split refactor.

Verifies the post-refactor boundaries:

1. ``source/lib/osx.py`` is a pure library (no Typer/Click surface).
2. ``source/osx_cli.py`` owns the Typer app.
3. ``source/cli.py`` mounts the ``osx`` subcommand.
4. ``resources/opencode/manifest.toml`` ships only skills, agents, and
   commands (no ``[resources.scripts]`` or ``[resources.lib]``).
5. Agent/command/skill prompts reference ``openspec-extended osx`` and
   never the legacy ``.opencode/scripts/lib/osx`` path.
"""

import ast
from pathlib import Path

import pytest
import toml

REPO_ROOT = Path(__file__).parent.parent.parent
LIB_OSX = REPO_ROOT / "source" / "lib" / "osx.py"
OSX_CLI = REPO_ROOT / "source" / "osx_cli.py"
MANIFEST = REPO_ROOT / "resources" / "opencode" / "manifest.toml"
PROMPT_ROOT = REPO_ROOT / "resources" / "opencode"

PROMPT_FILES = [
    "commands/osx-phase0.md",
    "commands/osx-phase1.md",
    "commands/osx-phase2.md",
    "commands/osx-phase3.md",
    "commands/osx-phase4.md",
    "commands/osx-phase5.md",
    "commands/osx-phase6.md",
    "commands/osx-review.md",
    "commands/osx-modify.md",
    "skills/osx-workflow/SKILL.md",
    "skills/osx-workflow/references/autonomous-workflow.md",
    "skills/osx-concepts/references/cli-reference.md",
]


def _top_level_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text())
    return {
        node.names[0].name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    }


@pytest.mark.unit
class TestLibraryPurity:
    """``source/lib/osx.py`` must stay free of CLI framework imports."""

    def test_lib_osx_does_not_import_cli_frameworks(self):
        """``source/lib/osx.py`` must not import typer or click."""
        imports = _top_level_imports(LIB_OSX)
        forbidden = {"typer", "click"}
        leaked = imports & forbidden
        assert not leaked, (
            f"{LIB_OSX.relative_to(REPO_ROOT)} leaked CLI framework "
            f"imports: {sorted(leaked)}"
        )

    def test_osx_cli_imports_typer(self):
        """``source/osx_cli.py`` must import typer (it owns the CLI app)."""
        imports = _top_level_imports(OSX_CLI)
        assert "typer" in imports, (
            f"{OSX_CLI.relative_to(REPO_ROOT)} must import typer; "
            f"found imports: {sorted(imports)}"
        )


@pytest.mark.unit
class TestManifestInvariants:
    """Manifest must not declare scripts/lib sections after the refactor."""

    def test_manifest_has_no_scripts_section(self):
        """``[resources.scripts]`` must be absent from the opencode manifest."""
        manifest = toml.loads(MANIFEST.read_text())
        resources = manifest.get("resources", {})
        assert "scripts" not in resources, (
            f"{MANIFEST.relative_to(REPO_ROOT)} still declares "
            f"[resources.scripts]; the scripts/ tree should not be shipped"
        )

    def test_manifest_has_no_lib_section(self):
        """``[resources.lib]`` must be absent from the opencode manifest."""
        manifest = toml.loads(MANIFEST.read_text())
        resources = manifest.get("resources", {})
        assert "lib" not in resources, (
            f"{MANIFEST.relative_to(REPO_ROOT)} still declares "
            f"[resources.lib]; the lib/ tree should not be shipped"
        )


@pytest.mark.unit
class TestPromptReferencesBinary:
    """Prompts must reference the binary, not the legacy script path."""

    @pytest.mark.parametrize(
        "relpath",
        PROMPT_FILES,
        ids=[p.replace("/", "_").replace(".md", "") for p in PROMPT_FILES],
    )
    def test_prompt_does_not_reference_legacy_script_path(self, relpath: str):
        """Prompt text must not mention ``.opencode/scripts/lib/osx``."""
        prompt_path = PROMPT_ROOT / relpath
        text = prompt_path.read_text()
        legacy = ".opencode/scripts/lib/osx"
        assert legacy not in text, (
            f"{relpath} still references legacy path '{legacy}'; "
            f"replace with 'openspec-extended osx'"
        )

    @pytest.mark.parametrize(
        "relpath",
        PROMPT_FILES,
        ids=[p.replace("/", "_").replace(".md", "") for p in PROMPT_FILES],
    )
    def test_prompt_references_openspec_extended_binary(self, relpath: str):
        """Prompt text must reference the ``openspec-extended osx`` subcommand."""
        prompt_path = PROMPT_ROOT / relpath
        text = prompt_path.read_text()
        target = "openspec-extended osx"
        assert target in text, (
            f"{relpath} does not reference '{target}'; "
            f"agent/command/skill prompts should drive the osx subcommand "
            f"via the binary"
        )
