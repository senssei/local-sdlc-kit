# The gate

The gate is `scripts/sdlc_check.py` reading your `sdlc.toml`. "Done" means it exited 0 in this session.

## `sdlc.toml`

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

## Running it

```bash
python3 scripts/sdlc_check.py                    # every check; exit 0 only if none failed
python3 scripts/sdlc_check.py --only tests       # named checks
python3 scripts/sdlc_check.py --base origin/main
python3 scripts/sdlc_check.py --red <test-id>... # exit 0 only if every test FAILS now (and is not "not found")
```

## `--red`

`--red` is the test-first proof: a new test must be seen failing, and the printed reason line must be the missing behavior, not a
typo. It is `NOT RED` when the test passes, times out, is not found (`not_found`), or the command cannot run (exit 126, 127, a signal).
It works through subprocesses, so it cannot tell a skipped or expected-failure test from a real failure; read the reason line.
Keep `not_found` narrow: a pattern that also matches a genuine failure message hides a red test. `sdlc.toml` ships with commented
examples for several test tools.

## The changelog check

A `[changelog]` check fails, rather than skips, when `base` does not exist in the repository (for example `master` instead of
`main`), and on any other git error such as an unreadable repository: set `base` in `sdlc.toml`. It skips only when git is missing,
outside a git checkout, or before the first commit. When you are on the base branch itself, only uncommitted changes are compared.
