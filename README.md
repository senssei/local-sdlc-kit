# sdlc-kit

**A small, harness-neutral AI-native SDLC you can drop into any git project.**

[![CI](https://github.com/senssei/sdlc-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/senssei/sdlc-kit/actions/workflows/ci.yml)
[![Docs](https://github.com/senssei/sdlc-kit/actions/workflows/docs.yml/badge.svg)](https://senssei.github.io/sdlc-kit/)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](https://github.com/senssei/sdlc-kit/blob/main/LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://senssei.github.io/sdlc-kit/install/)
[![Platform: Linux, macOS, WSL](https://img.shields.io/badge/platform-linux%20%7C%20macos%20%7C%20wsl-lightgrey.svg)](https://senssei.github.io/sdlc-kit/install/)
[![Dependencies: none](https://img.shields.io/badge/runtime%20dependencies-none-brightgreen.svg)](https://github.com/senssei/sdlc-kit/blob/main/pyproject.toml)

Every non-trivial change goes through six stages. Each stage ends in a committed file, and "done" is decided by a gate command,
not by opinion.

```text
intent  ->  spec  ->  plan  ->  test  ->  code  ->  review
   |          |         |        (red)                 |
intent.md  spec.md  plan.md   seen failing        REVIEW.md      gate: python3 scripts/sdlc_check.py
```

Works with **Claude Code, Codex, Gemini CLI, GitHub Copilot, Cursor and MiniMax Code**: the process lives in `AGENTS.md` and plain
`SKILL.md` files, and every other harness file only points there.

## Why

- **State survives the chat.** Intent, spec and plan are files in git, so the work outlives `/clear`, context compaction and a
  switch of agent.
- **Tests come first, and it is proven.** `sdlc_check.py --red` exits 0 only when the new test fails now, for the right reason.
- **Gates decide, not opinion.** A plan box is ticked only after the gate exited 0 in the same session; review is done by a fresh
  agent that sees only the artifacts and the diff.
- **Nothing to learn per tool.** One `AGENTS.md`, one skill directory, thin adapters. Standard library only, POSIX only.

## Quick start

```bash
pip install sdlc-kit
cd my-project
sdlc-kit-install          # then start with /sdlc (Claude Code) or "use the sdlc skill" (others)
```

The installer never overwrites a file your project owns and never deletes anything. Not on PyPI yet? Use the git-clone form
under [Install in detail](#install-in-detail). Full documentation:
<https://senssei.github.io/sdlc-kit/>

## Install in detail

The gate runner needs Python 3.11+; on an older `python3` it re-runs itself under a `python3.11` or newer found on `PATH`.

```bash
pip install sdlc-kit                     # or from a git clone: python3 ~/sdlc-kit/install.py
cd my-project
sdlc-kit-install                         # all harnesses; same flags as the git-clone shim
sdlc-kit-install --harness claude,codex  # a subset
sdlc-kit-install --dry-run               # see what it would do (it cannot predict OS errors)
```

Git-clone form (works without a PyPI release):

```bash
git clone <this repo> ~/sdlc-kit
cd my-project
python3 ~/sdlc-kit/install.py                       # the top-level shim re-exports sdlc_kit.install.main
python3 ~/sdlc-kit/install.py --harness claude,codex
python3 ~/sdlc-kit/install.py --dry-run
```

The git-clone shim and the PyPI wheel expose the same installer with the same flags. Both produce the same files in the target
project.

Then fill in three things, by hand or by asking an agent to do it:

1. `AGENTS.md`: the `<!-- TODO -->` parts (project, commands, project rules).
2. `sdlc.toml`: the test command, the one-test command for `--red`, optional extra checks and the changelog rule.
3. `intent.md` and `spec.md`: the problem, constraints, non-goals, invariants. The operator approves `intent.md`.

Optional: `git config core.hooksPath .githooks` runs the gate before every commit.

## What you get

| Path | Owner | Role |
|---|---|---|
| `AGENTS.md` | project | The process table, the process rules, and your project rules. The single source of truth |
| `sdlc.toml` | project | Your gate: commands for the checks and for running one test |
| `intent.md`, `spec.md`, `plan.md`, `REVIEW.md` | project | The stage artifacts (blank templates) |
| `.agents/skills/sdlc*/SKILL.md` | kit | Five skills: `sdlc` (find the stage), `sdlc-plan`, `sdlc-implement`, `sdlc-review`, `sdlc-release` |
| `scripts/sdlc_check.py` | kit | The gate runner and `--red` |
| `.githooks/pre-commit` | kit | Opt-in hook calling the runner |
| `CLAUDE.md`, `GEMINI.md`, `MCODE.md`, `.github/copilot-instructions.md` | project | Adapters, a few lines that point to `AGENTS.md` |
| `.cursor/rules/sdlc.mdc`, `.claude/skills` (symlink) | kit | Cursor rule, Claude Code skill discovery |

**Kit-owned** files are refreshed by `install.py --update`, which prints a diff of what it replaced, so put your customisations in
`AGENTS.md` (project-owned), not in the skills. **Project-owned** files are created once and never overwritten; `--update` only
prints a diff against the current template. The installer never deletes anything.

If your project already has an `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` or Copilot instructions, they are left alone and the installer
ends with a `manual step needed` list: merge the process section into your `AGENTS.md`, and make the adapters point to it.

## Documentation

Full documentation: <https://senssei.github.io/sdlc-kit/>

- [Process](https://senssei.github.io/sdlc-kit/process/): the six stages and the five skills.
- [Harnesses](https://senssei.github.io/sdlc-kit/harnesses/): how Claude Code, Codex, Gemini CLI, GitHub Copilot, Cursor and
  MiniMax Code pick the process up.
- [The gate](https://senssei.github.io/sdlc-kit/gate/): `sdlc.toml`, `sdlc_check.py` and the red-first `--red` proof.

## Develop the kit

```bash
python3 sdlc_kit/sdlc_check.py      # compile + tests
python3 -m build                    # sdist + wheel into dist/
python3 -m twine check --strict dist/*
pip install -e ".[docs]" && mkdocs serve   # preview the documentation site
```

See `AGENTS.md`, `intent.md`, `spec.md` and `plan.md` in this repository: the kit follows its own process.

## Releasing

Releases use PyPI trusted publishing (no tokens), TestPyPI first, then PyPI from a `v<__version__>` tag. The procedure is in
[Releasing](https://senssei.github.io/sdlc-kit/releasing/).

## License

[Apache-2.0](https://github.com/senssei/sdlc-kit/blob/main/LICENSE)
