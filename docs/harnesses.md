# Harnesses

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
a harness that does not auto-discover skills still finds the workflow.

## Notes

- The docs describe symlinking an individual skill into `.claude/skills`; a symlink for the whole `.claude/skills` directory (what the
  installer creates) is not documented, but it works in practice (the maintainer's own projects use it). If it does not for you, make
  `.claude/skills` a real directory and re-run the installer: it then links each skill separately.
- `sdlc-release` is user-invoked only in Claude Code (`disable-model-invocation`): run `/sdlc-release` yourself.
- A project that git-ignores `.cursor/` will not commit the Cursor rule.
- Choose harnesses at install time with `--harness`, for example `local-sdlc-kit-install --harness claude,codex`.
