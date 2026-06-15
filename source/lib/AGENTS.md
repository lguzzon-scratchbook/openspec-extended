# `source/lib/` - Change Management Tool

The `osx` subcommand namespace: `openspec-extended osx <domain> <action> [args]`.

## Contract

- **Output**: JSON to stdout
- **Errors**: stderr, non-zero exit on failure
- **No side effects** beyond the requested action; idempotent where possible

## Command Domains (10)

| Domain | Purpose |
|--------|---------|
| `baseline` | Baseline tracking (commit/branch) |
| `ctx` | Aggregate context for a change |
| `git` | Git status for change directory |
| `phase` | Phase advancement management |
| `state` | Phase and iteration state management |
| `iterations` | Iteration history tracking |
| `log` | Decision log management |
| `complete` | Completion status tracking |
| `validate` | Validation utilities |
| `instructions` | Get artifact instructions (proxies to `openspec` CLI) |

## Constants (top of `osx.py`)

| Constant | Value |
|----------|-------|
| `PHASES` | `["PHASE0" ... "PHASE6"]` |
| `VALID_TRANSITION_REASONS` | `implementation_incorrect`, `artifacts_modified`, `retry_requested` |
| `REQUIRED_SKILLS` | 5 `osx-*` skills installed for changes |
| `REQUIRED_CORE_SKILLS` | 4 `osc-*` core skills (apply, verify, sync, archive) |

## Conventions

- One Typer sub-app per domain, registered on the module-level `app`.
- Domain commands read/write state under `.openspec/` (created on demand).
- Never call AI processes directly — `osx` is a state/IO tool. AI invocation is the orchestrator's job.

## See Also

- Root `AGENTS.md` — Code Style, Versioning
- `source/AGENTS.md` — Module roles
- `source/orchestrator/AGENTS.md` — Consumer of `osx` state
