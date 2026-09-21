# sdlc-kit

A small, harness-neutral AI-native SDLC you can drop into any git project. Every non-trivial change goes through
**intent -> spec -> plan -> test -> code -> review**, each stage ends in a committed file, and "done" is decided by a gate command,
not by opinion.

It works with Claude Code, Codex, Gemini CLI, GitHub Copilot, Cursor and MiniMax Code, because the process lives in `AGENTS.md`
and plain `SKILL.md` files, and every other harness file only points there.

Standard library only. POSIX only (Linux, macOS, WSL). The gate runner needs Python 3.11+; on an older `python3` it re-runs itself
under a `python3.11` or newer found on `PATH`.

## Where to go

| If you want to | Read |
|---|---|
| Add the process to a project | [Install](install.md) |
| Understand the six stages and the five skills | [Process](process.md) |
| See how each harness picks the process up | [Harnesses](harnesses.md) |
| Configure `sdlc.toml` or use `--red` | [The gate](gate.md) |
| Cut a release of the kit itself | [Releasing](releasing.md) |
