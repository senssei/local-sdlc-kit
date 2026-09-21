# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [SemVer](https://semver.org/) (pre-1.0: minor
versions may include breaking changes).

## [Unreleased]

### Added
- **AI-native SDLC kit** (intent, spec, plan, test, code, review). `install.py` scaffolds any git project with
  `AGENTS.md`, five stage skills (`sdlc`, `sdlc-plan`, `sdlc-implement`, `sdlc-review`, `sdlc-release`), a config-driven
  gate runner (`scripts/sdlc_check.py`) with a `--red` red-first mode, an opt-in pre-commit hook, and thin adapters for
  Claude Code, Gemini CLI, GitHub Copilot, Cursor, MiniMax Code (mcode-tools). Standard library only at runtime.
- **mcode-tools harness** (`MCODE.md` adapter, `--harness mcode`). MiniMax Code reads `AGENTS.md` natively; the adapter
  names the skill directory so a fresh session finds the workflow without guessing. No `.claude/skills`-style symlink is
  created — Codex and mcode-tools do not need one.
- **PyPI publication.** `pip install sdlc-kit` lands an installable wheel that ships the same `sdlc_kit/install.py`,
  `sdlc_kit/sdlc_check.py`, and `sdlc_kit/template/` as a git clone. The installer is exposed as the
  `sdlc-kit-install` console script. A top-level `install.py` shim keeps `python3 install.py` working from a clone.
- **GitHub Actions trusted publishing** (`.github/workflows/publish.yml`): `workflow_dispatch` with `target: testpypi |
  pypi`, no API tokens in the repo. PyPI is gated on the workflow running from a tag `v<__version__>`, mirroring the
  `prism-local` release process.
- **CI** (`.github/workflows/ci.yml`): the kit's gate on Python 3.11 to 3.13 and a sdist/wheel build with `twine check --strict`
  on every push to `main` and every pull request. `publish.yml` now runs the gate before building.
- **Documentation site** (MkDocs, `docs/` + `mkdocs.yml`): install, process, harnesses, the gate and releasing. Built with
  `mkdocs build --strict` in CI and deployed to GitHub Pages from `main` (`.github/workflows/docs.yml`). The harness, gate and
  releasing detail moved out of `README.md` into `docs/`; the README keeps install and links. New `docs` extra
  (`pip install sdlc-kit[docs]` is for maintainers; not a runtime dependency).
- **Apache-2.0** license, **Keep a Changelog** + SemVer conventions.

## [0.1.0] - 2026-09-21

First numbered release. Equivalent to the in-repo state before PyPI packaging; the version number matches
`sdlc_kit.__version__`.

### Notes
- The kit ships as a wheel and an sdist; `pip install sdlc-kit` gives the user the same `sdlc-kit-install` CLI as a
  git clone's `python3 install.py`.
- The release process is `Actions -> Publish -> target testpypi`, then a tag `v0.1.0`, then `Actions -> Publish ->
  target pypi` from that tag.