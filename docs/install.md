# Install

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

## After installing

Fill in three things, by hand or by asking an agent to do it:

1. `AGENTS.md`: the `<!-- TODO -->` parts (project, commands, project rules).
2. `sdlc.toml`: the test command, the one-test command for `--red`, optional extra checks and the changelog rule. See
   [The gate](gate.md).
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
