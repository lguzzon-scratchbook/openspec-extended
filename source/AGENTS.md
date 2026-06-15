# Source - Python CLI

Python source for the `openspec-extended` binary.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | `__version__` only |
| `__main__.py` | Entry: `python -m source` |
| `cli.py` | Typer CLI (install/update/orchestrate) + `SCRIPT_VERSION` |
| `lib/osx.py` | Change-management tool (9 command domains) |
| `orchestrator/engine.py` | 7-phase autonomous workflow engine |

## Module Roles

- **`cli.py`** — User-facing CLI. Imports from `lib/osx.py` and `orchestrator/engine.py`. Owns `SCRIPT_VERSION` (canonical version).
- **`lib/osx.py`** — Stateless subcommands exposed as `openspec-extended osx <domain>`. JSON to stdout, errors to stderr.
- **`orchestrator/engine.py`** — Drives the PHASE0→PHASE6 state machine by spawning AI processes per phase.

## Conventions

- `SCRIPT_VERSION` in `cli.py` is the **single source of truth** for the tool version. See root AGENTS.md "Versioning" section.
- The `osx` subcommand namespace is a separate Typer app mounted under the main CLI; do not collapse them.

## See Also

- Root `AGENTS.md` — Code Style, Python Requirements, Versioning, Testing
- `source/lib/AGENTS.md` — `osx` subcommand domains
- `source/orchestrator/AGENTS.md` — 7-phase workflow
