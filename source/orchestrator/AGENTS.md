# `source/orchestrator/` - 7-Phase Workflow Engine

Drives a change through seven autonomous phases by spawning AI processes per phase and persisting state between iterations.

## 7-Phase State Machine

| Phase | Name | Command | Agent |
|-------|------|---------|-------|
| PHASE0 | ARTIFACT REVIEW | `osx-phase0` | `osx-analyzer` |
| PHASE1 | IMPLEMENTATION | `osx-phase1` | `osx-builder` |
| PHASE2 | REVIEW | `osx-phase2` | `osx-analyzer` |
| PHASE3 | MAINTAIN DOCS | `osx-phase3` | `osx-maintainer` |
| PHASE4 | SYNC | `osx-phase4` | `osx-maintainer` |
| PHASE5 | SELF-REFLECTION | `osx-phase5` | `osx-analyzer` |
| PHASE6 | ARCHIVE | `osx-phase6` | `osx-maintainer` |

## Constants

| Constant | Value | Meaning |
|----------|-------|---------|
| `DEFAULT_TIMEOUT` | `1800` | Per-phase AI subprocess timeout (seconds) |
| `DEFAULT_MAX_PHASE_ITERATIONS` | `10` | Retry budget per phase before giving up |

## Phase Transitions

A phase advances when the AI process exits 0 and reports completion via the `osx state` / `osx complete` subcommands. Failed phases transition backward using one of three reasons:

| Reason | Trigger |
|--------|---------|
| `implementation_incorrect` | Tests/build fail or code does not match proposal |
| `artifacts_modified` | Artifacts changed since the last iteration |
| `retry_requested` | Manual or self-reflection request |

Defined in `source/lib/osx.py:VALID_TRANSITION_REASONS`.

## Loop Shape

```
PHASE0 → PHASE1 → PHASE2 → PHASE3 → PHASE4 → PHASE5 → PHASE6
                ↖ (any phase can loop back on transition reason)
```

Each phase may iterate up to `DEFAULT_MAX_PHASE_ITERATIONS` times before the orchestrator halts and surfaces the failure.

## Conventions

- The orchestrator is a **driver**, not a decision-maker. It shells out to the AI CLI and reads JSON back from `osx` subcommands.
- State persists under the change directory (typically `.openspec/changes/<id>/state.json`); the orchestrator never mutates state directly — it calls `osx state` / `osx phase`.
- Cancellation is via SIGINT/SIGTERM: the orchestrator kills the AI child and records the partial state.

## Entry Point

- `run_orchestrator(...)` — async function in `engine.py`, exposed via `source.orchestrator.__init__`.
- Mounted under the main CLI as `openspec-extended orchestrate`.

## See Also

- Root `AGENTS.md` — Code Style, Versioning
- `source/AGENTS.md` — Module roles
- `source/lib/AGENTS.md` — `osx` subcommand contract (state I/O)
- `resources/opencode/commands/AGENTS.md` — Phase command definitions
- `resources/opencode/agents/AGENTS.md` — Phase agent definitions
