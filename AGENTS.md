# AGENTS.md (sdlc-kit itself)

This repository is the kit, not a project that uses it. To install the process into a project, see `README.md`.

## Project

Reusable AI-native SDLC: `sdlc_kit/` is the installable package (`sdlc_kit/install.py` scaffolds, `sdlc_kit/sdlc_check.py` is
the gate runner, `sdlc_kit/template/` is the rest). The top-level `install.py` is a shim that re-exports
`sdlc_kit.install.main` for git clones; `pip install sdlc-kit` exposes the same installer as the `sdlc-kit-install` console
script. Python 3.11+, standard library only at runtime. Read `intent.md` (why), `spec.md` (invariants K1 to K5, installer,
runner and packaging contracts) and `plan.md` (state) first.

## Commands

```bash
python3 sdlc_kit/sdlc_check.py                                   # the gate (sdlc.toml here): compile + tests
python3 sdlc_kit/sdlc_check.py --red tests.test_x.TestY.test_z   # red-first
python3 -m unittest discover -s tests                            # tests only
python3 -m build && python3 -m twine check --strict dist/*      # sdist + wheel + twine check (maintainer)
```

## Rules

- The kit's own process is the one it ships: intent -> spec -> plan -> test -> code -> review (`sdlc_kit/template/AGENTS.md`).
  Change the behavior in `spec.md` first, prove the new test red, then change `sdlc_kit/template/` or `sdlc_kit/install.py`.
- K1: nothing in `sdlc_kit/template/` except `sdlc_kit/template/sdlc.toml` may name a project, language tool or test framework
  (`tests/test_kit.py`, `tests/test_packaging.py::TestInvariantsStillHold`). Build tooling at the repo root (`pyproject.toml`,
  `MANIFEST.in`, the top-level `install.py` shim) is exempt: it names tools in the role of building the kit.
- K2: process rules live only in `sdlc_kit/template/AGENTS.md`; adapters point to it.
- K3: the installer never overwrites a project-owned file and never deletes.
- K4: runtime is standard library only. Build-time dependencies (`setuptools`, `build`, `twine`) are not runtime.
- Tests never touch the user's git config: use `GIT_CONFIG_GLOBAL=/dev/null` (a globally signed commit waits for a passphrase and
  hangs the suite), and set `sys.dont_write_bytecode` before loading files from `sdlc_kit/`.
- Commit and push only when the operator asks. PyPI publishes are operator-gated; the trusted-publishing workflow at
  `.github/workflows/publish.yml` requires a matching tag `v<__version__>` for `target: pypi`.
