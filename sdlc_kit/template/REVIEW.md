# Review policy (`REVIEW.md`)

## 1. Who decides

Agents propose; the **operator decides** what merges and what ships (the operator gates are in `AGENTS.md`). A change that passes every gate is not done until it has been
reviewed, and the review is never done by the session that wrote the change.

```text
Plan approved -> test red -> code green -> gate exit 0 -> independent review -> operator decision -> commit / release
```

## 2. Independent review

Review with fresh context: a separate subagent or a new session that is given only `intent.md`, `spec.md`, the `plan.md` items
under review, this file, and the diff (`git diff $(git merge-base <base> HEAD)` plus untracked files, `<base>` being `base` in
`sdlc.toml`). It reports findings ranked by
severity, each with `file:line` and a concrete failing input, and no praise. The author fixes findings test-first; the reviewer
does not edit code.

## 3. Checklist

### A. Evidence
- [ ] `python3 scripts/sdlc_check.py` exited `0` in this session.
- [ ] Every new or changed behavior has a test that was seen failing first (`sdlc_check.py --red`).
- [ ] No test was weakened, skipped or deleted to get green.

### B. Spec
- [ ] The behavior is written in `spec.md` (or the normative doc it points to) and the code matches it.
- [ ] No invariant is broken. Touching one needs operator approval.

### C. Patch
- [ ] The diff contains only what the plan item covers; no drive-by refactors.
- [ ] No dependency the project rules forbid.

### D. Security and cleanliness
- [ ] No injection into shell commands, queries or paths; no path traversal; no secrets in code or logs.
- [ ] Input is validated at the boundary; errors keep their documented shape.

### E. Project checks
- [ ] <!-- Add the review rows that are specific to this project (docs updated, changelog entry, hardware or data safety, ...). -->

## 4. Commands

```bash
python3 scripts/sdlc_check.py                        # the gate
python3 scripts/sdlc_check.py --red <test-id>        # red-first
git diff $(git merge-base <base> HEAD)               # what the reviewer sees (<base> from sdlc.toml)
git config core.hooksPath .githooks                  # opt in to the pre-commit gate
```
