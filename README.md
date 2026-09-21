# sdlc-kit

A small, harness-neutral AI-native SDLC you can drop into any git project. Every non-trivial change goes through
**intent -> spec -> plan -> test -> code -> review**, each stage ends in a committed file, and "done" is decided by a gate command,
not by opinion. It works with Claude Code, Codex, Gemini CLI, GitHub Copilot, Cursor and MiniMax Code because the process lives in
`AGENTS.md` and plain `SKILL.md` files, and every other harness file only points there.

Standard library only. POSIX only (Linux, macOS, WSL). The gate runner needs Python 3.11+; on an older `python3` it re-runs itself
under a `python3.11` or newer found on `PATH`.

## Install

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

## Per harness

Checked against each tool's documentation on 2026-09-21 (a reviewer read the pages; treat the details as likely to change).

| Harness | Picks up the process from | Skills | Start with |
|---|---|---|---|
| Claude Code | `CLAUDE.md` (its `@AGENTS.md` import is required: with both files present only `CLAUDE.md` is read) | `.claude/skills` (the installer links it to `.agents/skills`) | `/sdlc` |
| Codex | `AGENTS.md` | `.agents/skills` natively | "use the sdlc skill" |
| Gemini CLI | `GEMINI.md` (imports `AGENTS.md`), or `AGENTS.md` via `context.fileName` | `.agents/skills` natively | "use the sdlc skill" |
| GitHub Copilot | `.github/copilot-instructions.md` and `AGENTS.md` | `.agents/skills` in VS Code | "use the sdlc skill" |
| Cursor | `AGENTS.md` and `.cursor/rules/*.mdc` (`alwaysApply: true`) | `.agents/skills` | "use the sdlc skill" |
| MiniMax Code (mcode-tools) | `AGENTS.md` and `MCODE.md` | `.agents/skills` | "use the sdlc skill" |

Because several of these read `AGENTS.md` themselves, some adapters are redundant; they are harmless and they name the skill file, so
a harness that does not auto-discover skills still finds the workflow. Notes:

- The docs describe symlinking an individual skill into `.claude/skills`; a symlink for the whole `.claude/skills` directory (what the
  installer creates) is not documented, but it works in practice (the maintainer's own projects use it). If it does not for you, make
  `.claude/skills` a real directory and re-run the installer: it then links each skill separately.
- `sdlc-release` is user-invoked only in Claude Code (`disable-model-invocation`): run `/sdlc-release` yourself.
- A project that git-ignores `.cursor/` will not commit the Cursor rule.

## The gate (`sdlc.toml`)

```toml
base = "main"

[[check]]
name = "tests"
run = "<your test command>"          # exit 0 = pass; runs from the project root through the shell
# skip_if_missing = "<executable>"   # SKIP instead of FAIL when a tool is not installed

[changelog]                          # optional
file = "CHANGELOG.md"
runtime_paths = ["src/"]             # a change under these paths needs a change to `file`

[red]
run = "<command that runs exactly one test> {id}"   # {id} is already shell-quoted: do not quote it again
timeout = 60
not_found = ["<regex of output that means the test does not exist>"]
ignore = ["<regex of summary lines never to show as the failure reason>"]
```

```bash
python3 scripts/sdlc_check.py                    # every check; exit 0 only if none failed
python3 scripts/sdlc_check.py --only tests       # named checks
python3 scripts/sdlc_check.py --base origin/main
python3 scripts/sdlc_check.py --red <test-id>... # exit 0 only if every test FAILS now (and is not "not found")
```

`--red` is the test-first proof: a new test must be seen failing, and the printed reason line must be the missing behavior, not a
typo. It is `NOT RED` when the test passes, times out, is not found (`not_found`), or the command cannot run (exit 126, 127, a signal).
It works through subprocesses, so it cannot tell a skipped or expected-failure test from a real failure; read the reason line.
Keep `not_found` narrow: a pattern that also matches a genuine failure message hides a red test. `sdlc.toml` ships with commented
examples for several test tools.

A `[changelog]` check fails, rather than skips, when `base` does not exist in the repository (for example `master` instead of
`main`), and on any other git error such as an unreadable repository: set `base` in `sdlc.toml`. It skips only when git is missing, outside
a git checkout, or before the first commit. When you are on the base branch itself, only uncommitted changes are compared.

## Reviewing with fresh context

The `sdlc-review` skill tells the agent to hand only the artifacts and the diff to a fresh subagent or session and to treat its
report as data. Claude Code: the Agent tool. Others: a new session or their subagent feature.

## Develop the kit

```bash
python3 sdlc_kit/sdlc_check.py      # compile + tests
python3 -m build                    # sdist + wheel into dist/
python3 -m twine check --strict dist/*
```

See `AGENTS.md`, `intent.md`, `spec.md` and `plan.md` in this repository: the kit follows its own process.

## Releasing

The release process mirrors [`prism-local`](https://github.com/senssei/prism-local) and uses PyPI **trusted publishing**
(OIDC), so no API tokens are stored anywhere. The workflow is `.github/workflows/publish.yml`
(manual: *Actions → Publish → Run workflow*).

**One-time setup**

1. On [test.pypi.org](https://test.pypi.org/manage/account/publishing/) (and later [pypi.org](https://pypi.org/manage/account/publishing/)),
   add a *pending publisher*: project `sdlc-kit`, owner `senssei`, repository `sdlc-kit`, workflow `publish.yml`,
   environment `testpypi` (respectively `pypi`).
2. In the GitHub repository, create the environments `testpypi` and `pypi` (*Settings → Environments*). Add yourself as a
   required reviewer on `pypi` so a release needs an explicit approval.

**Each release**

1. Update `CHANGELOG.md` (move `[Unreleased]` items under a dated `[X.Y.Z] - YYYY-MM-DD` heading) and
   `sdlc_kit/__init__.py` (`__version__`), and merge to `main` with the gate green (`python3 sdlc_kit/sdlc_check.py`
   exits 0 and `python3 -m unittest discover -s tests` is green).
2. Run **Publish → target `testpypi`**. It builds the sdist and wheel, runs `twine check --strict`, uploads to TestPyPI,
   then installs the uploaded version into a clean virtualenv and smoke-tests `sdlc-kit-install --help`.
3. Tag the release (`git tag -s vX.Y.Z && git push origin vX.Y.Z`) and run **Publish** on that tag with target `pypi`. The
   workflow refuses to publish to PyPI unless it runs from the tag `v<__version__>`.
4. Create a GitHub release for the tag.

**Versions are permanent.** Neither index lets you re-upload a version, and PyPI never lets you reuse one. Use a
pre-release version such as `0.1.0rc1` while rehearsing on TestPyPI if you expect to iterate.
