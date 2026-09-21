#!/usr/bin/env python3
"""Install the SDLC kit (skills, artifact templates, AGENTS.md, gate runner, harness adapters) into a project.

    python3 install.py                                   # into the current directory, every harness
    python3 install.py --target ../my-project --harness claude,codex
    python3 install.py --update                          # refresh kit-owned files, diff the project-owned ones
    python3 install.py --dry-run                         # say what would happen, write nothing

Kit-owned files (skills, runner, hook, Cursor rule) are refreshed by --update. Project-owned files (AGENTS.md, sdlc.toml, the four
artifacts, CLAUDE.md, GEMINI.md, the Copilot instructions) are created once and never overwritten; --update only shows a diff.
Nothing is ever deleted. Standard library only.
"""

import argparse
import difflib
import os
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Tuple

KIT = Path(__file__).resolve().parent
TEMPLATE = KIT / "template"
HARNESSES = ["claude", "codex", "gemini", "copilot", "cursor", "mcode"]
SKILLS = ["sdlc", "sdlc-plan", "sdlc-implement", "sdlc-review", "sdlc-release"]

# (source under template/, destination in the project, owner, harness that needs it or None for always, executable)
Entry = Tuple[str, str, str, Optional[str], bool]
ENTRIES: List[Entry] = (
    [(f"skills/{name}/SKILL.md", f".agents/skills/{name}/SKILL.md", "kit", None, False) for name in SKILLS]
    + [
        ("sdlc_check.py", "scripts/sdlc_check.py", "kit", None, False),
        ("githooks/pre-commit", ".githooks/pre-commit", "kit", None, True),
        ("AGENTS.md", "AGENTS.md", "project", None, False),
        ("sdlc.toml", "sdlc.toml", "project", None, False),
        ("intent.md", "intent.md", "project", None, False),
        ("spec.md", "spec.md", "project", None, False),
        ("plan.md", "plan.md", "project", None, False),
        ("REVIEW.md", "REVIEW.md", "project", None, False),
        ("adapters/CLAUDE.md", "CLAUDE.md", "project", "claude", False),
        ("adapters/GEMINI.md", "GEMINI.md", "project", "gemini", False),
        ("adapters/copilot-instructions.md", ".github/copilot-instructions.md", "project", "copilot", False),
        ("adapters/cursor-sdlc.mdc", ".cursor/rules/sdlc.mdc", "kit", "cursor", False),
        ("adapters/MCODE.md", "MCODE.md", "project", "mcode", False),
    ]
)
CLAUDE_LINK = (".claude/skills", "../.agents/skills")

Report = Tuple[str, str, str]  # (status, path, note)

# Project-owned files a skipped install leaves incomplete, and what the operator must do by hand. The skills rely on all of them.
MANUAL = {
    "AGENTS.md": ("AI-native SDLC", "merge the `Development process` and `Process rules` sections of the kit's template/AGENTS.md into it"),
    "CLAUDE.md": ("AGENTS.md", "add `@AGENTS.md` at the top so Claude Code reads the shared rules"),
    "GEMINI.md": ("AGENTS.md", "add `@AGENTS.md` at the top so Gemini CLI reads the shared rules"),
    ".github/copilot-instructions.md": ("AGENTS.md", "add a line telling Copilot to follow AGENTS.md"),
}


MAX_DIFF_LINES = 200


def _diff(current: Path, new: Path, rel: str) -> str:
    """A unified diff, or a one-line note for binary content, capped so it cannot flood an agent's context."""
    a_bytes, b_bytes = current.read_bytes(), new.read_bytes()
    try:
        if b"\0" in a_bytes or b"\0" in b_bytes:
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "binary")
        a = a_bytes.decode("utf-8").splitlines(keepends=True)
        b = b_bytes.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return f"{rel}: binary file differs ({len(a_bytes)} bytes yours, {len(b_bytes)} bytes in the kit template)\n"
    lines = list(difflib.unified_diff(a, b, f"{rel} (yours)", f"{rel} (kit template)"))
    if len(lines) > MAX_DIFF_LINES:
        lines = lines[:MAX_DIFF_LINES] + [f"... ({len(lines) - MAX_DIFF_LINES} more lines)\n"]
    return "".join(lines)


def _leaves_target(target: Path, dest: Path) -> bool:
    """True when writing `dest` would land outside `target` because a parent directory is a symlink."""
    parent = dest.parent
    while not parent.exists() and parent != parent.parent:
        parent = parent.parent
    try:
        parent.resolve().relative_to(target.resolve())
    except ValueError:
        return True
    return False


def _place(target: Path, source: Path, dest: Path, rel: str, owner: str, executable: bool, update: bool, dry_run: bool,
           diffs: List[str], manual: List[str]) -> Report:
    """Create, refresh or leave one file. May raise OSError; the caller reports it as `skipped`."""
    if _leaves_target(target, dest):
        return "skipped", rel, "a parent directory is a symlink that leaves the project: not touched"
    if dest.is_symlink() and (owner == "kit" or not dest.exists()):
        return "skipped", rel, "is a symlink (broken, or kit-owned): not touched"
    if not dest.exists():
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            if executable:
                dest.chmod(0o755)
        return "created", rel, owner
    if dest.is_dir():
        return "skipped", rel, "exists and is a directory"
    same = dest.read_bytes() == source.read_bytes()
    not_exec = executable and not os.access(dest, os.X_OK)
    if same and not not_exec:
        return "unchanged", rel, owner
    if owner == "kit":
        if not update:
            return "skipped", rel, "not executable (use --update)" if same else "kit-owned, differs from the template (use --update)"
        replaced = "" if same else _diff(dest, source, rel)
        if not dry_run:
            if not same:
                shutil.copyfile(source, dest)
            if executable:
                dest.chmod(0o755)
        if replaced:  # only after the write succeeded: an OSError above means nothing was replaced
            diffs.append(replaced)
        return "updated", rel, "made executable" if same else owner
    marker, todo = MANUAL.get(rel, (None, None))
    if marker and marker not in dest.read_text(encoding="utf-8", errors="replace"):
        manual.append(f"{rel}: {todo}")
    if update and not same:
        diffs.append(_diff(dest, source, rel))
    return "skipped", rel, "project-owned, never overwritten"


def _link_claude_skills(target: Path, dry_run: bool, manual: List[str]) -> List[Report]:
    """`.claude/skills` -> `../.agents/skills`, or per-skill links when `.claude/skills` is already a real directory."""
    rel, link_target = CLAUDE_LINK
    dest = target / rel
    try:
        if _leaves_target(target, dest):
            return [("skipped", rel, "a parent directory is a symlink that leaves the project: not touched")]
        if dest.is_symlink() and os.readlink(dest) == link_target:
            return [("unchanged", rel, "symlink")]
        if dest.is_dir() and not dest.is_symlink():
            reports = []
            for name in SKILLS:
                link, want = dest / name, f"../../.agents/skills/{name}"
                lrel = f"{rel}/{name}"
                if link.is_symlink() and os.readlink(link) == want:
                    reports.append(("unchanged", lrel, "symlink"))
                elif link.exists() or link.is_symlink():
                    reports.append(("skipped", lrel, f"exists and is not a link to {want}"))
                else:
                    if not dry_run:
                        link.symlink_to(want)
                    reports.append(("created", lrel, f"symlink -> {want}"))
            return reports
        if dest.exists() or dest.is_symlink():
            manual.append(f"{rel}: Claude Code will not find the kit skills there; link or copy the skill folders from .agents/skills into it")
            return [("skipped", rel, f"exists and is not a link to {link_target}")]
        if not dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.symlink_to(link_target)
        return [("created", rel, f"symlink -> {link_target}")]
    except OSError as exc:
        return [("skipped", rel, exc.strerror or str(exc))]


def install(target: Path, harnesses: List[str], update: bool, dry_run: bool) -> Tuple[List[Report], List[str], List[str]]:
    reports: List[Report] = []
    diffs: List[str] = []
    manual: List[str] = []
    for src, rel, owner, harness, executable in ENTRIES:
        if harness is not None and harness not in harnesses:
            continue
        try:
            reports.append(_place(target, TEMPLATE / src, target / rel, rel, owner, executable, update, dry_run, diffs, manual))
        except OSError as exc:  # a file where a directory is needed, read-only, permissions: report it and go on
            reports.append(("skipped", rel, exc.strerror or str(exc)))
    if "claude" in harnesses:
        reports.extend(_link_claude_skills(target, dry_run, manual))
    return reports, diffs, manual


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", type=Path, default=Path.cwd(), help="project directory (default: the current directory)")
    ap.add_argument("--harness", default=",".join(HARNESSES), help=f"comma-separated subset of: {', '.join(HARNESSES)} (default: all)")
    ap.add_argument("--update", action="store_true", help="refresh kit-owned files; show a diff for customised project-owned ones")
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    args = ap.parse_args(argv)

    harnesses = [h.strip() for h in args.harness.split(",") if h.strip()]
    if not harnesses:
        print(f"install: --harness needs at least one of {', '.join(HARNESSES)}", file=sys.stderr)
        return 2
    bad = [h for h in harnesses if h not in HARNESSES]
    if bad:
        print(f"install: unknown harness {', '.join(map(repr, bad))}; choose from {', '.join(HARNESSES)}", file=sys.stderr)
        return 2
    if not args.target.is_dir():
        print(f"install: target {str(args.target)!r} is not a directory", file=sys.stderr)
        return 2
    if args.target.resolve() == KIT:
        print("install: refusing to install into the kit itself; run it from, or point --target at, your project", file=sys.stderr)
        return 2

    reports, diffs, manual = install(args.target.resolve(), harnesses, args.update, args.dry_run)
    for status, rel, note in reports:
        print(f"{status:9} {rel}  ({note})")
    for diff in diffs:
        print("\n" + diff, end="")
    if manual:
        print("\nmanual step needed (these files already existed and were left alone; the skills rely on them):")
        for line in manual:
            print(f"  - {line}")
    if not args.dry_run and any(st == "created" and rel == "AGENTS.md" for st, rel, _ in reports):
        print("\nNext: fill in the <!-- TODO --> parts of AGENTS.md and the commands in sdlc.toml, then run: python3 scripts/sdlc_check.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
