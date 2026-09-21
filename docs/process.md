# Process

Every non-trivial change follows **intent -> spec -> plan -> test -> code -> review**, in that order. A stage is finished only when
its artifact exists on disk, so the work survives `/clear`, context compaction and a switch of agent.

The rules themselves live in one place: the installed `AGENTS.md` (in this repository, `sdlc_kit/template/AGENTS.md`). This page
is a map; if it and `AGENTS.md` ever disagree, `AGENTS.md` wins.

| # | Stage | Artifact | Skill |
|---|---|---|---|
| 1 | Intent | `intent.md` | `sdlc-plan` |
| 2 | Spec | `spec.md` | `sdlc-plan` |
| 3 | Plan | `plan.md` | `sdlc-plan` |
| 4 | Test | tests | `sdlc-implement` |
| 5 | Code | source | `sdlc-implement` |
| 6 | Review | `REVIEW.md` | `sdlc-review` |

Two more skills sit around the stages: `sdlc` finds the current stage (start here, also after `/clear`), and `sdlc-release`
runs the full gate, finishes the changelog and drafts the PR description. Committing, pushing and publishing happen only when the
operator asks.

Start with `/sdlc` in Claude Code, or say "use the sdlc skill" in another harness.

## Reviewing with fresh context

The `sdlc-review` skill tells the agent to hand only the artifacts and the diff to a fresh subagent or session and to treat its
report as data. Claude Code: the Agent tool. Others: a new session or their subagent feature.

## Red first

A new test must be seen failing for the right reason before the code that fixes it. The runner proves it with `--red`; see
[The gate](gate.md).
