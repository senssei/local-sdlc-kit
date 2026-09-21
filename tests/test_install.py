"""install.py: scaffolds a project, never overwrites project-owned files, never deletes (K3)."""

import contextlib
import importlib.util
import io
import os
import tempfile
import sys
import unittest
from pathlib import Path

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().parent.parent / "sdlc_kit" / "install.py"
spec = importlib.util.spec_from_file_location("install", SCRIPT)
install = importlib.util.module_from_spec(spec)
spec.loader.exec_module(install)

ALWAYS = [
    "AGENTS.md", "sdlc.toml", "intent.md", "spec.md", "plan.md", "REVIEW.md",
    "scripts/sdlc_check.py", ".githooks/pre-commit",
    ".agents/skills/sdlc/SKILL.md", ".agents/skills/sdlc-plan/SKILL.md", ".agents/skills/sdlc-implement/SKILL.md",
    ".agents/skills/sdlc-review/SKILL.md", ".agents/skills/sdlc-release/SKILL.md",
]
CLAUDE = ["CLAUDE.md"]
GEMINI = ["GEMINI.md"]
COPILOT = [".github/copilot-instructions.md"]
CURSOR = [".cursor/rules/sdlc.mdc"]
MCODE = ["MCODE.md"]


def run_install(*args: str):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = install.main(list(args))
        except SystemExit as exc:
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def tree(root: Path):
    return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file() or p.is_symlink())


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.target = Path(self._tmp.name)

    def install(self, *args: str):
        return run_install("--target", str(self.target), *args)


class TestFreshInstall(Base):
    def test_all_harnesses_by_default(self):
        code, out, _err = self.install()
        self.assertEqual(code, 0)
        for rel in ALWAYS + CLAUDE + GEMINI + COPILOT + CURSOR + MCODE:
            self.assertTrue((self.target / rel).is_file(), rel)
        self.assertIn("created", out)

    def test_hook_is_executable(self):
        self.install()
        self.assertTrue(os.access(self.target / ".githooks" / "pre-commit", os.X_OK))

    def test_claude_skills_is_a_relative_symlink(self):
        self.install()
        link = self.target / ".claude" / "skills"
        self.assertTrue(link.is_symlink())
        self.assertEqual(os.readlink(link), "../.agents/skills")
        self.assertTrue((link / "sdlc" / "SKILL.md").is_file())

    def test_only_selected_harnesses_get_adapters(self):
        self.install("--harness", "claude")
        files = tree(self.target)
        self.assertIn("CLAUDE.md", files)
        for rel in GEMINI + COPILOT + CURSOR + MCODE:
            self.assertNotIn(rel, files)

    def test_codex_needs_no_adapter(self):
        self.install("--harness", "codex")
        files = tree(self.target)
        for rel in ALWAYS:
            self.assertIn(rel, files)
        for rel in CLAUDE + GEMINI + COPILOT + CURSOR + MCODE + [".claude/skills"]:
            self.assertNotIn(rel, files)

    def test_mcode_only_creates_mcode_md_and_no_claude_skills_link(self):
        self.install("--harness", "mcode")
        files = tree(self.target)
        for rel in ALWAYS + MCODE:
            self.assertIn(rel, files)
        for rel in CLAUDE + GEMINI + COPILOT + CURSOR + [".claude/skills"]:
            self.assertNotIn(rel, files)

    def test_unknown_harness_exits_2(self):
        code, _out, err = self.install("--harness", "vim")
        self.assertEqual(code, 2)
        self.assertIn("vim", err)
        self.assertEqual(tree(self.target), [])

    def test_target_must_be_a_directory(self):
        code, _out, err = run_install("--target", str(self.target / "nope"))
        self.assertEqual(code, 2)
        self.assertIn("nope", err)

    def test_dry_run_writes_nothing(self):
        code, out, _err = self.install("--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(tree(self.target), [])
        self.assertIn("created", out)


class TestNeverOverwrites(Base):
    def test_second_run_changes_nothing(self):
        self.install()
        before = {rel: (self.target / rel).read_bytes() for rel in tree(self.target) if not (self.target / rel).is_symlink()}
        code, out, _err = self.install()
        self.assertEqual(code, 0)
        self.assertNotIn("created", out)
        after = {rel: (self.target / rel).read_bytes() for rel in before}
        self.assertEqual(before, after)

    def test_customised_project_files_survive_with_and_without_update(self):
        self.install()
        for rel in ("AGENTS.md", "sdlc.toml", "intent.md", "CLAUDE.md", "MCODE.md"):
            (self.target / rel).write_text("MINE\n")
        self.install()
        self.install("--update")
        for rel in ("AGENTS.md", "sdlc.toml", "intent.md", "CLAUDE.md", "MCODE.md"):
            self.assertEqual((self.target / rel).read_text(), "MINE\n", rel)

    def test_update_shows_a_diff_for_a_customised_project_file_without_applying_it(self):
        self.install()
        (self.target / "AGENTS.md").write_text("MINE\n")
        _code, out, _err = self.install("--update")
        self.assertIn("--- ", out)
        self.assertIn("+++ ", out)
        self.assertEqual((self.target / "AGENTS.md").read_text(), "MINE\n")

    def test_nothing_is_deleted(self):
        self.install()
        extra = self.target / "notes.txt"
        extra.write_text("keep")
        self.install("--update")
        self.assertEqual(extra.read_text(), "keep")

    def test_real_claude_skills_directory_keeps_its_own_content(self):
        (self.target / ".claude" / "skills").mkdir(parents=True)
        (self.target / ".claude" / "skills" / "mine.md").write_text("x")
        code, out, _err = self.install()
        self.assertEqual(code, 0)
        self.assertFalse((self.target / ".claude" / "skills").is_symlink())
        self.assertTrue((self.target / ".claude" / "skills" / "mine.md").exists())
        self.assertTrue((self.target / ".claude" / "skills" / "sdlc").is_symlink())


class TestUpdate(Base):
    def test_update_refreshes_kit_owned_files(self):
        self.install()
        skill = self.target / ".agents" / "skills" / "sdlc" / "SKILL.md"
        original = skill.read_text()
        skill.write_text("stale\n")
        self.install()  # without --update it stays stale
        self.assertEqual(skill.read_text(), "stale\n")
        _code, out, _err = self.install("--update")
        self.assertEqual(skill.read_text(), original)
        self.assertIn("updated", out)

    def test_update_refreshes_the_runner_and_the_cursor_rule(self):
        self.install()
        for rel in ("scripts/sdlc_check.py", ".cursor/rules/sdlc.mdc"):
            (self.target / rel).write_text("stale\n")
        self.install("--update")
        for rel in ("scripts/sdlc_check.py", ".cursor/rules/sdlc.mdc"):
            self.assertNotEqual((self.target / rel).read_text(), "stale\n", rel)


class TestRobustness(Base):
    def test_broken_symlink_at_a_project_owned_path_is_skipped_not_a_crash(self):
        missing = self.target.parent / (self.target.name + "-missing.md")
        self.addCleanup(lambda: missing.unlink() if missing.exists() else None)
        (self.target / "AGENTS.md").symlink_to(missing)
        code, out, _err = self.install()
        self.assertEqual(code, 0)
        self.assertIn("skipped", out)
        self.assertFalse(missing.exists(), "the installer wrote through a broken symlink")
        self.assertTrue((self.target / "sdlc.toml").is_file())

    def test_a_file_where_a_directory_is_needed_is_reported_and_the_rest_installs(self):
        (self.target / "scripts").write_text("i am a file")
        code, out, _err = self.install()
        self.assertEqual(code, 0)
        self.assertRegex(out, r"skipped\s+scripts/sdlc_check.py")
        self.assertTrue((self.target / "AGENTS.md").is_file())
        self.assertEqual((self.target / "scripts").read_text(), "i am a file")

    def test_update_does_not_write_through_a_symlink_at_a_kit_owned_path(self):
        outside = self.target.parent / (self.target.name + "-outside.py")
        outside.write_text("shared\n")
        self.addCleanup(lambda: outside.unlink())
        (self.target / "scripts").mkdir()
        (self.target / "scripts" / "sdlc_check.py").symlink_to(outside)
        code, out, _err = self.install("--update")
        self.assertEqual(code, 0)
        self.assertEqual(outside.read_text(), "shared\n")
        self.assertRegex(out, r"skipped\s+scripts/sdlc_check.py")

    def test_target_equal_to_the_kit_is_refused(self):
        code, _out, err = run_install("--target", str(install.KIT), "--dry-run")  # dry run: a regression must not litter the kit
        self.assertEqual(code, 2)
        self.assertIn("kit", err)
        self.assertFalse((install.KIT / "CLAUDE.md").exists())

    def test_missing_exec_bit_on_the_hook_is_repaired_only_by_update(self):
        self.install()
        hook = self.target / ".githooks" / "pre-commit"
        hook.chmod(0o644)
        _code, out, _err = self.install()
        self.assertFalse(os.access(hook, os.X_OK))
        self.assertIn("not executable", out)
        self.install("--update")
        self.assertTrue(os.access(hook, os.X_OK))

    def test_update_prints_what_it_replaces_in_a_kit_owned_file(self):
        self.install()
        skill = self.target / ".agents" / "skills" / "sdlc" / "SKILL.md"
        skill.write_text("my local tweak\n")
        _code, out, _err = self.install("--update")
        self.assertIn("my local tweak", out)
        self.assertIn("-my local tweak", out)


class TestSafety(Base):
    def test_symlinked_parent_directory_never_sends_writes_outside_the_target(self):
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(outside, ignore_errors=True))
        (self.target / ".agents").symlink_to(outside)
        (self.target / "scripts").symlink_to(outside)
        code, out, _err = self.install()
        self.assertEqual(code, 0)
        self.assertEqual(sorted(p.name for p in outside.iterdir()), [])
        self.assertRegex(out, r"skipped\s+scripts/sdlc_check.py")
        self.install("--update")
        self.assertEqual(sorted(p.name for p in outside.iterdir()), [])

    def test_a_binary_file_at_a_kit_owned_path_does_not_flood_the_output(self):
        self.install()
        (self.target / ".agents" / "skills" / "sdlc" / "SKILL.md").write_bytes(b"\x00\xff" * 200_000)
        _code, out, _err = self.install("--update")
        self.assertLess(len(out), 5000)
        self.assertIn("binary", out)

    def test_a_huge_text_diff_is_capped(self):
        self.install()
        (self.target / ".agents" / "skills" / "sdlc" / "SKILL.md").write_text("line\n" * 20_000)
        _code, out, _err = self.install("--update")
        self.assertLess(len(out.splitlines()), 400)
        self.assertIn("more lines", out)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root can write read-only files")
    def test_no_diff_is_claimed_written_when_the_write_failed(self):
        self.install()
        skill = self.target / ".agents" / "skills" / "sdlc" / "SKILL.md"
        skill.write_text("stale\n")
        skill.chmod(0o444)
        _code, out, _err = self.install("--update")
        self.assertRegex(out, r"skipped\s+.agents/skills/sdlc/SKILL.md")
        self.assertNotIn("now written", out)

    def test_dry_run_with_update_writes_nothing(self):
        self.install()
        skill = self.target / ".agents" / "skills" / "sdlc" / "SKILL.md"
        skill.write_text("stale\n")
        self.install("--update", "--dry-run")
        self.assertEqual(skill.read_text(), "stale\n")

    def test_empty_harness_list_is_refused(self):
        code, _out, err = self.install("--harness", "")
        self.assertEqual(code, 2)
        self.assertIn("harness", err)


class TestHook(Base):
    def test_hook_finds_the_project_from_its_own_location_not_from_the_repository_root(self):
        self.install()
        (self.target / "sdlc.toml").write_text('[[check]]\nname = "marker"\nrun = "touch ran-here"\n')
        elsewhere = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(elsewhere, ignore_errors=True))
        import subprocess
        proc = subprocess.run(["sh", str(self.target / ".githooks" / "pre-commit")], cwd=elsewhere, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue((self.target / "ran-here").exists())


class TestIncompleteInstall(Base):
    def test_skipped_agents_md_and_adapters_need_a_manual_step_and_say_so(self):
        (self.target / "AGENTS.md").write_text("existing\n")
        (self.target / "CLAUDE.md").write_text("existing\n")
        _code, out, _err = self.install()
        manual = out.split("manual step", 1)[1]
        self.assertIn("AGENTS.md: merge", manual)
        self.assertIn("CLAUDE.md: add `@AGENTS.md`", manual)

    def test_gemini_and_copilot_files_that_do_not_point_to_agents_md_are_listed(self):
        (self.target / "GEMINI.md").write_text("mine\n")
        (self.target / ".github").mkdir()
        (self.target / ".github" / "copilot-instructions.md").write_text("mine\n")
        _code, out, _err = self.install()
        manual = out.split("manual step", 1)[1]
        self.assertIn("GEMINI.md:", manual)
        self.assertIn("copilot-instructions.md:", manual)

    def test_an_existing_agents_md_that_already_has_the_process_is_not_listed(self):
        (self.target / "AGENTS.md").write_text("# Mine\n\n## Development process (AI-native SDLC)\n")
        _code, out, _err = self.install()
        self.assertNotIn("manual step", out)

    def test_claude_skills_symlink_to_another_directory_is_listed(self):
        (self.target / ".claude").mkdir()
        (self.target / ".claude" / "skills").symlink_to(self.target)
        _code, out, _err = self.install()
        self.assertIn("manual step", out)
        self.assertIn(".claude/skills", out.split("manual step", 1)[1])

    def test_clean_install_has_no_manual_step(self):
        _code, out, _err = self.install()
        self.assertNotIn("manual step", out)

    def test_real_claude_skills_directory_gets_per_skill_symlinks(self):
        (self.target / ".claude" / "skills").mkdir(parents=True)
        (self.target / ".claude" / "skills" / "mine").mkdir()
        _code, _out, _err = self.install()
        for name in ("sdlc", "sdlc-plan", "sdlc-implement", "sdlc-review", "sdlc-release"):
            link = self.target / ".claude" / "skills" / name
            self.assertTrue(link.is_symlink(), name)
            self.assertTrue((link / "SKILL.md").is_file(), name)
        self.assertTrue((self.target / ".claude" / "skills" / "mine").is_dir())


if __name__ == "__main__":
    unittest.main()
