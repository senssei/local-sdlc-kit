# Contributing

Thanks for helping out. local-sdlc-kit is a small alpha project: issues and pull requests are welcome.

## Setup

```bash
git clone https://github.com/senssei/local-sdlc-kit
cd local-sdlc-kit
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"               # adds `build` and `twine` for the maintainer workflow
```

The kit has no runtime dependencies. The `dev` extra is only for maintainers who build wheels and upload to PyPI.

## Tests

```bash
python3 -m unittest discover -s tests -v    # ~150 tests, ~7 s, no network or GPU
```

`tests/test_packaging.py` builds a wheel + sdist into a temp directory, runs `twine check --strict`, and installs the
wheel into a fresh `venv` to smoke-test `local-sdlc-kit-install --help`. It needs `build` and `twine` (the `[dev]` extra).
`tests/test_install.py`, `tests/test_kit.py` and `tests/test_sdlc_check.py` need nothing but the standard library.

## The gate

```bash
python3 sdlc_kit/sdlc_check.py                 # the deterministic gate: compile + tests
python3 sdlc_kit/sdlc_check.py --red <id>      # red-first: prove a new test fails for the right reason
```

A change is only "done" when the gate exits 0 in this session. Tick a plan box only after that.

## Process

The kit ships its own process. Every non-trivial change follows **intent -> spec -> plan -> test -> code -> review**.
The artifacts are committed files; the state survives `/clear`, a context compaction and a switch of agent.

- **`intent.md`** — problem, outcome, constraints, non-goals, success criteria. Operator-approved.
- **`spec.md`** — invariants (K1–K5), installer contract, runner contract, packaging contract. No code against
  undefined behavior.
- **`plan.md`** — unchecked `- [ ]` items under a phase, each naming its files and its test. Operator-approved.
- **`REVIEW.md`** — independent review (fresh subagent or session) with no open finding.
- **`CHANGELOG.md`** — every user-visible change gets a `[Unreleased]` entry.

## Style

- **Standard library only at runtime.** Build-time dependencies (`setuptools`, `build`, `twine`) are exempt.
- **No project / language / test-tool names in installed content.** K1 in `spec.md`; grep-tested by
  `tests/test_packaging.py::TestInvariantsStillHold::test_k1_no_project_names_in_template`.
- **Process rules live only in `sdlc_kit/template/AGENTS.md`.** Adapters point to it (K2).
- **The installer never overwrites a project-owned file and never deletes.** K3.
- **One logical change per commit**, message `type: description` (`feat:`, `bugfix:`, `docs:`, `chore:`, `packaging:`).

## Docs

The documentation site is MkDocs: `docs/` (Markdown) and `mkdocs.yml`. Preview it with `pip install -e ".[docs]" && mkdocs serve`;
`mkdocs build --strict` must pass (CI runs it). It is deployed to GitHub Pages from `main` by `.github/workflows/docs.yml`.
`README.md` is the PyPI landing page: keep it short and put reference material in `docs/`. The process rules stay in
`sdlc_kit/template/AGENTS.md`; `docs/process.md` only points to it.

## Pull requests

Describe what changed and why, and note how you tested it. CI must pass (the gate on Python 3.11 to 3.13, the wheel build, the
strict docs build). For a release, see [`docs/releasing.md`](docs/releasing.md). It is implemented by
`.github/workflows/publish.yml`.
