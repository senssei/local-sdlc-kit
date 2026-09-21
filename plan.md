# Plan: sdlc-kit

An item is ticked only after `python3 sdlc_kit/sdlc_check.py` exited 0 for it. The runner re-runs itself under a newer Python
when the current interpreter is older than 3.11.

## Phase 3: Publish to PyPI

Status: approved by the operator, not started.

Mirror the release pattern of `prism-local` (the `03-foundy-local` project): the kit becomes an installable Python package
(`sdlc_kit/`) shipped as a wheel and an sdist, with Apache-2.0, Keep-a-Changelog, and GitHub Actions trusted publishing.
K1 and K4 are re-scoped to **installed content** and **runtime** respectively; build tooling at the repo root and build-time
dependencies are exempt. The intent non-goal "A package on PyPI" is removed and the spec gains a Packaging contract.

- [x] 1. Move the kit into a `sdlc_kit/` package: `install.py` -> `sdlc_kit/install.py`, `template/` ->
  `sdlc_kit/template/`, `template/sdlc_check.py` -> `sdlc_kit/sdlc_check.py`. Add `sdlc_kit/__init__.py` with `__version__ = "0.1.0"`.
  Update the existing tests (`tests/test_install.py` resolves the script from the new location; `tests/test_kit.py` resolves
  `TEMPLATE` from `sdlc_kit/template/`). Tests: `python3 -m unittest discover -s tests` still passes.
- [x] 2. Top-level `install.py` shim: `from sdlc_kit.install import main` and `sys.exit(main())`, so `python3 install.py` still
  works from a git clone. Test: `python3 install.py --help` exits 0 and prints the harness list.
- [x] 3. Add `pyproject.toml` (setuptools backend, dynamic version from `sdlc_kit.__version__`, `dependencies = []`,
  `[project.scripts] sdlc-kit-install = "sdlc_kit.install:main"`, `[project.optional-dependencies] dev = ["build", "twine"]`,
  `[project.urls]` with `Homepage`, `Issues`, `Changelog`, Apache-2.0 license expression). Test: `python3 -c "import tomllib;
  tomllib.loads(open('pyproject.toml').read())"` parses; `python3 -m build` produces `dist/*.whl` and `dist/*.tar.gz`.
- [x] 4. Add `MANIFEST.in` (`include LICENSE README.md CHANGELOG.md`, `prune tests docs scripts .github`, plus the standard
  `recursive-include sdlc_kit/template *`). Test: `twine check --strict dist/*` exits 0 and the wheel contains
  `sdlc_kit/template/AGENTS.md`, `sdlc_kit/template/skills/sdlc/SKILL.md`, and `sdlc_kit/sdlc_check.py`.
- [x] 5. Add `LICENSE` (Apache-2.0), `CHANGELOG.md` (Keep a Changelog, `[Unreleased]` entry that lists Phase 2 and Phase 3),
  `CONTRIBUTING.md` (setup, tests, docs, style, PRs — the kit has no `docs/`, so the doc section is "this kit does not
  publish a separate docs site"), `SECURITY.md` (reporting channel, supported versions = latest only). Tests: the
  `MANIFEST.in` include list matches.
- [x] 6. Add `.github/workflows/publish.yml`: `workflow_dispatch` with `target: testpypi | pypi`, mirrors `prism-local` (build
  with `python -m build`, `twine check --strict`, upload via `pypa/gh-action-pypi-publish` with OIDC, smoke-test the wheel
  on TestPyPI by installing it in a fresh venv and running `sdlc-kit-install --help`; PyPI gated on a tag `v<__version__>`).
  No API tokens in the repo. Test: a syntax check (`python3 -c "import yaml; yaml.safe_load(open('.github/workflows/publish.yml'))"`)
  and a grep that no `TWINE_TOKEN` / `PYPI_TOKEN` secret is referenced.
- [x] 7. Update `README.md` and the kit's own `AGENTS.md`: add `pip install sdlc-kit` and `sdlc-kit-install` to the commands,
  and a "Releasing" section that mirrors `prism-local`'s procedure (TestPyPI first, then PyPI from a tag, with a reviewer on
  the `pypi` environment). Test: a grep test that `README.md` mentions both `pip install sdlc-kit` and the `sdlc-kit-install`
  command.
- [x] 8. Independent review of the change by a fresh subagent: the wheel builds, `twine check` is clean, the venv smoke test
  succeeds, K1 still forbids project names in `sdlc_kit/template/`, K4 still forbids runtime dependencies, and the in-repo
  `python3 install.py` shim still works. Verifier reported `FIXES NEEDED`; three findings (`.gitignore` missing
  `dist/` / `*.egg-info/` / `build/`, broken `docs/releasing.md` link in `CONTRIBUTING.md`, missing `## Releasing`
  section in `README.md`) were fixed in the same change.

Risks and open questions:

- **Trusted publishing setup is operator-only.** The first release requires the operator to add a pending publisher on
  test.pypi.org and pypi.org and to create the `testpypi` and `pypi` GitHub environments. The workflow is ready; the credentials
  are not.
- **A re-upload to PyPI is impossible.** Use a pre-release (`0.1.0rc1`) on TestPyPI if iteration is expected. The kit's
  `__version__` and the wheel name must agree.
- **The shim `install.py` adds a name collision.** `pip install sdlc-kit` produces a wheel that does not contain a top-level
  `install.py`; the shim only exists in the git checkout. AGENTS.md and README must keep both invocations working.

## Phase 2: Add mcode-tools as a supported harness

Status: approved by the operator, not started.

The MiniMax Code terminal (mcode-tools, agent name "Mavis") reads `AGENTS.md` natively, like Codex, but it also benefits from a
project-root adapter file that names the skill directory so a fresh session finds the workflow without guessing. The change adds
`mcode` to `HARNESSES`, a project-owned adapter (`template/adapters/MCODE.md` -> `MCODE.md`), a README row and the corresponding
tests. K1-K5 do not change: the adapter only points to `AGENTS.md`, the harness name stays inside `install.py` and the adapter file.

- [x] 1. Add `mcode` to `HARNESSES` in `install.py` and an `ENTRIES` row for `adapters/MCODE.md` -> `MCODE.md` (test: a fresh
  install with `--harness mcode` creates `MCODE.md` and nothing else, and `install.HARNESSES` contains `"mcode"`).
- [x] 2. Add `template/adapters/MCODE.md` that points to `AGENTS.md` and names the five skills in `.agents/skills/`
  (tests: `tests/test_kit.py::TestAdapters` confirms it like the others; `tests/test_kit.py::TestSingleSourceOfRules` confirms it
  does not restate process rules).
- [x] 3. Add a row for mcode-tools to the harness table in `README.md`, and mention mcode in `template/AGENTS.md` and
  `template/skills/sdlc/SKILL.md` where the harness list appears (test: a grep test added to `tests/test_kit.py::TestAdapters`
  that every adapter file lists `AGENTS.md`).
- [x] 4. Independent review of the change by a fresh subagent: the new harness is listed in the README, the default harness set,
  and the spec; the adapter points to `AGENTS.md` and does not restate rules; the test proves the file is created and never
  overwritten. Verifier reported `READY TO SHIP`; one low-severity finding (`MCODE.md` missing from the K3 explicit list in
  `test_customised_project_files_survive_with_and_without_update`) was fixed in the same change.

Risks and open questions:

- Whether mcode-tools reads a project-root `MCODE.md` is not documented externally; the file is harmless if it does not (the
  README treats redundant adapters as a feature, not a bug). A future revision can drop the file if evidence accumulates that
  no harness reads it.
- mcode-tools reads `AGENTS.md` directly, so unlike Claude Code it does not need a `.claude/skills`-style symlink. The
  installer must not create one unless evidence appears.

## Phase 1: Extract

Status: items 1 to 5 built. Review 1 (20 findings) and review 2 (18 findings, plus a fresh-agent dry run of `/sdlc` in a scaffolded
project that surfaced 6 guidance gaps) were all triaged; each defect was reproduced test-first and fixed (gate: compile + 123 tests,
2026-09-21). Deliberately not done: a configurable `[red].reason` (finding 16: the English error vocabulary is a language-neutral
heuristic, `ignore` covers the tool-specific part) and further wording dedup of skills (K2 was reworded instead). Not yet done: a third
look at the second round of fixes, migration of prism-local (item 6). `intent.md` is still a draft: the operator has not approved it.

- [x] 1. Generic skills and artifact templates under `template/` (tests: `tests/test_kit.py::TestNoProjectNames`, `TestSkills`).
- [x] 2. `template/AGENTS.md` and adapters for Claude, Gemini, Copilot, Cursor (tests: `tests/test_kit.py::TestAdapters`).
- [x] 3. Runner `template/sdlc_check.py` ported from prism-local, config-driven (tests: `tests/test_sdlc_check.py`, 31 tests).
- [x] 4. `install.py` (tests: `tests/test_install.py`).
- [x] 5. `README.md`, this repo's own `sdlc.toml` and `AGENTS.md` (dogfood).
- [ ] 6. Migrate prism-local onto the kit (separate repo; changes its `AGENTS.md`, so it needs the operator's approval).
- [x] 7. Independent review of the kit (fresh subagent). 20 findings fixed test-first; fixes verified by tests only, not re-reviewed.
- [x] 8. Second independent review of the fixes and a dry run of `/sdlc` by a fresh agent: done; findings fixed, fixes verified by tests only.

Risks and open questions:

- `--red` is subprocess-based: it cannot tell a skipped or `expectedFailure` test from a real failure, it relies on `not_found`
  patterns for typos. The printed reason line must still be read.
- Skill discovery differs per harness and changes quickly. The reviewer confirmed from documentation (through a summarising fetcher, so
  not read raw by the maintainer) that all five harnesses read `AGENTS.md` or an adapter and find `.agents/skills`; a whole-directory
  `.claude/skills` symlink is undocumented but works in practice.
- The runner needs Python 3.11+ (`tomllib`); on an older `python3` it re-runs itself under `python3.11` or newer, and exits 2 with a
  clear message when there is none.
- Windows (native) is out of scope: the runner and installer use POSIX process groups and symlinks.
