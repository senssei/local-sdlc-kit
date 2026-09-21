# Intent: sdlc-kit

> **Status: approved by the operator, 2026-09-21.** The operator approves any change to this file.

## 1. Problem

AI coding agents (Claude Code, Codex, Gemini CLI, GitHub Copilot, Cursor, MiniMax Code, ...) lose work between sessions and drift
from the request when the process lives in chat. `prism-local` solved this with an AI-native SDLC (intent, spec, plan, test, code,
review) whose state is committed files and whose "done" is decided by a deterministic gate. That process is welded to one project,
so it cannot be reused.

## 2. Outcome

One small repository. Running `install.py` in any git project adds the process (skills, artifact templates, `AGENTS.md`), a
config-driven gate runner, and thin adapters for the chosen harnesses. The project only fills in its own commands and rules. The
same kit is also installable from PyPI as `sdlc-kit`; both surfaces expose the same files and the same `sdlc-kit-install` command.

## 3. Constraints

1. Standard library only, POSIX only (Linux, macOS, WSL). The runner needs Python 3.11+ (`tomllib`) and re-runs itself under a newer one.
   Build-time packaging dependencies (`setuptools`, `build`, `twine` for the maintainer) are not a runtime concern.
2. Harness-neutral: `AGENTS.md` is the single source of truth, adapters only point to it.
3. Never overwrites a file the project owns.
4. No knowledge of any language, framework or test tool inside the kit; that lives in the project's `sdlc.toml`.

## 4. Non-goals

1. Running the agents. The kit only tells them what to do and checks the result.
2. Enforcing the process on humans. Everything is opt-in.
3. A plugin marketplace entry or a hosted service. PyPI is in scope; marketplaces are not.

## 5. Success criteria

| Criterion | Evidence |
|---|---|
| A fresh project gets a working process from one command | `tests/test_install.py`, dry run with a fresh agent |
| The kit names no project, language or test tool in installed content | K1 grep test |
| Existing project files are never overwritten | K3 test |
| The gate works for a non-Python project | `tests/test_sdlc_check.py` with a shell-command fixture |
| `pip install sdlc-kit` lands an installable distribution with the same files as a git clone | `tests/test_packaging.py`: sdist + wheel build, `twine check --strict`, venv smoke test |
| The PyPI-published version matches the in-repo behaviour | The wheel installs and `sdlc-kit-install --help` lists the same harnesses as `python3 install.py --help` |
