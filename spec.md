# Specification: local-sdlc-kit

## 1. Components

- `sdlc_kit/` is the installable Python package. `sdlc_kit/install.py` scaffolds and updates, `sdlc_kit/sdlc_check.py` is the gate
  runner installed as `scripts/sdlc_check.py`, and `sdlc_kit/template/` is the rest of what gets installed (skills, adapters,
  `AGENTS.md`, `sdlc.toml`, the four artifact templates, hook). Kit-owned files (skills, adapters, runner, hook, Cursor rule) are
  refreshed by `--update`; project-owned files (`AGENTS.md`, `sdlc.toml`, `intent.md`, `spec.md`, `plan.md`, `REVIEW.md`,
  `CLAUDE.md`, `GEMINI.md`, `MCODE.md`, `.github/copilot-instructions.md`) are created once.
- A top-level `install.py` shim re-exports `sdlc_kit.install.main` so that `python3 install.py` from a git clone still works after
  the restructure. It is **not** part of the PyPI wheel.
- `pyproject.toml` and `MANIFEST.in` describe the wheel and the sdist; they are build-only and do not run on the user's machine.

## 2. Invariants

| # | Invariant |
|---|---|
| K1 | The kit names no specific project, language or test tool in installed content (`sdlc_kit/template/`, except `sdlc_kit/template/sdlc.toml` which is project configuration and carries examples for several tools). Build tooling at the repository root (`pyproject.toml`, `MANIFEST.in`, the top-level `install.py` shim) is exempt: it names tools in the role of building the kit, not as content the user sees. |
| K2 | `sdlc_kit/template/AGENTS.md` is the authority for the process rules, the operator gates and the independent-review rule. Adapters do not restate them. `REVIEW.md`, the skills and the hook may echo a rule in a sentence for the reader of that file, but never add, relax or contradict one. |
| K3 | The installer never overwrites a project-owned file, and never deletes anything. |
| K4 | Runtime is standard library only. Build-time dependencies (`setuptools`, `build`, `twine` for the maintainer) are not runtime and are exempt. |
| K5 | The runner knows no language or tool and no test tool's output format; commands and patterns (`run`, `not_found`, `ignore`) come from `sdlc.toml`. |

## 3. Installer contract

`python3 install.py [--target DIR] [--harness claude,codex,gemini,copilot,cursor,mcode] [--update] [--dry-run]`

- Default target is the current directory, default harness set is `claude,codex,gemini,copilot,cursor,mcode`. POSIX only (symlinks, `sh` hook).
- Every file is reported as `created`, `skipped` (with the reason), `updated` or `unchanged`.
- Exit 0 on success, 2 for a bad argument, a target that is not a directory, or a target that is the kit itself.
- An OS error on one file (a file where a directory is needed, read-only, permissions) is reported as `skipped` with the reason and the
  rest still installs. Nothing is written through a symlink: not one at a kit-owned path, not a broken one at a project-owned path,
  and not a parent directory that is a symlink leading outside the target.
- `--dry-run` reports what a real run would try; it cannot predict an OS error, so a real run may report `skipped` where it said `created`.
- `.claude/skills` is a relative symlink to `../.agents/skills`. If `.claude/skills` is already a real directory, each kit skill is
  linked into it individually. Anything else at that path is reported and left alone.
- `--update` rewrites kit-owned files and prints a unified diff of what it replaced, only after the write succeeded (customise
  `AGENTS.md`, not the skills). It also restores the hook's exec bit. For a project-owned file that differs from the template it prints
  a diff and applies nothing. A diff is capped at 200 lines, and a binary file is reported as "binary file differs" without a diff.
- When an existing project-owned `AGENTS.md` lacks the process, or an existing `CLAUDE.md`, `GEMINI.md` or Copilot file does not
  point to `AGENTS.md`, or `.claude/skills` is something other than the kit link or a directory, the installer prints a `manual step
  needed` list saying what to do. It never edits those files. An empty `--harness` is an error (exit 2).

## 4. Runner contract

`python3 scripts/sdlc_check.py [--only NAME ...] [--base REF] [--root DIR]` and `--red ID ...`. POSIX only. It needs Python 3.11+
(`tomllib`) and re-runs itself under the first `python3.14` to `python3.11` on `PATH` when started on an older interpreter.

- Config `sdlc.toml` in the project root (`--root`, default the parent of the directory holding the script). Missing or invalid
  config, a wrongly typed key, no checks at all, or an unknown `--only` name: exit 2 with the reason, never a traceback.
- Each `[[check]]` has `name` and `run` (shell command, run from the project root; stdin is closed). Exit 0 is pass, else fail.
  `skip_if_missing` (a command name) turns a missing tool into `skip`; `timeout` (seconds, optional) makes a hung check fail. The
  command's whole process group is killed when it times out, when the command ends (a background child never outlives it and never
  delays the verdict), and when the runner receives SIGTERM or SIGINT. Pass detail is the last output line, cut to 200 characters.
  Output beyond the last 1 MB is dropped.
- Keys the runner does not read (a typo such as `[chagelog]` or `not_foud`) produce a warning on stderr and are ignored.
- `[changelog]` adds a built-in `changelog` check: fail when a file under `runtime_paths` changed against the merge-base with
  `--base` (default `base` in the config, else `main`) and `file` did not. Paths are normalised and matched on directory boundaries
  (`src` does not cover `src_old/`; an empty entry is a configuration error). They are relative to `--root` even when it is a
  subdirectory of the repository; untracked files count; a rename is a deletion plus an addition, so moving a file out of a runtime
  path counts. When HEAD is the merge-base itself the result says that only uncommitted changes were compared.
  It skips only when there is genuinely nothing to compare: git is not installed, not a git checkout, or no commits yet. Every other
  git failure (an unreadable object, "dubious ownership") and a `base` that cannot be resolved **fail**, quoting git, because a silent
  skip would switch the gate off.
- `--red`: for each id run `[red].run` with `{id}` replaced by the shell-quoted id (do not quote it again), timeout `[red].timeout`
  (default 60 s). Red means the command ran, exited nonzero, and its output matches none of `[red].not_found` (regexes, matched per
  line). Exit 126, 127, death by a signal (negative, or 129 to 159 when a shell reports it), a timeout, exit 0, and a `not_found` match
  are all `NOT RED`. The reason line is the last output line that looks like an error (`error`, `exception`, `assert`, `fail`),
  skipping lines that match `[red].ignore` (matched with their indentation intact). Exit 0 only if every id is red. It cannot be
  combined with `--only` or `--base`, and an id that starts with `-` cannot be passed.
- If every selected check was skipped the runner prints a warning. Overall exit 0 unless a check failed.

## 5. Packaging contract

`pyproject.toml` (setuptools backend, dynamic version read from `sdlc_kit.__version__`), `MANIFEST.in` (include `LICENSE`,
`README.md`, `CHANGELOG.md`; prune everything else not shipped), `LICENSE` (Apache-2.0), `CHANGELOG.md` (Keep a Changelog, SemVer,
under `[Unreleased]` until released), `CONTRIBUTING.md`, `SECURITY.md`.

- `[project] dependencies = []`. The kit installs nothing extra at runtime. Optional extras (`dev` for tests) cover maintainer
  workflows and are not installed by users.
- `[project.scripts] local-sdlc-kit-install = "sdlc_kit.install:main"` exposes the installer as a console script so `pip install local-sdlc-kit`
  gives users `local-sdlc-kit-install --help` without cloning the repo.
- `python -m build` must produce a wheel and an sdist; `twine check --strict dist/*` must exit 0. A fresh virtualenv must be able to
  `pip install dist/*.whl` and run `local-sdlc-kit-install --help`, producing the same harness list as `python3 install.py --help` from a
  git clone.
- `[project.urls]` points at the GitHub repository (`Homepage`, `Issues`, `Changelog`, `Documentation` when a docs site exists).
- GitHub Actions trusted publishing (OIDC) is the supported release path; no PyPI token is committed. The manual workflow
  `.github/workflows/publish.yml` is `workflow_dispatch` with `target: testpypi | pypi`; PyPI is gated on the workflow running
  from a tag `v<__version__>`, mirroring `prism-local`'s release process.
- CI: `.github/workflows/ci.yml` runs on `push` to `main` and on `pull_request`. It runs the kit's own gate
  (`python3 sdlc_kit/sdlc_check.py`) on a Python matrix that covers every supported minor (3.11, 3.12, 3.13), and a build job
  (`python -m build`, `twine check --strict dist/*`). `publish.yml` runs the same gate in its `build` job, so nothing is published
  from a red tree. Workflows hold `contents: read` unless a job needs more, and reference no PyPI token.
- Docs: `docs/` (Markdown) and `mkdocs.yml` build a static site with MkDocs (`mkdocs build --strict` must exit 0; every file in
  `nav` exists; relative links between pages resolve). `docs/` holds the detailed reference (install, harnesses, the gate, the
  process, releasing); `README.md` stays a self-contained PyPI landing page that links to it, and does not repeat the reference.
  `mkdocs` is a build-time dependency in the `docs` extra (K4: not runtime, not in `dependencies`). `docs/` is not shipped
  (`MANIFEST.in` prunes it). CI builds the site with `--strict` on every change; `.github/workflows/docs.yml` deploys it to
  GitHub Pages from `main` only, with `pages: write` and `id-token: write` scoped to the deploy job and no token stored.
  The process docs point to `sdlc_kit/template/AGENTS.md` and do not restate its rules (K2).
