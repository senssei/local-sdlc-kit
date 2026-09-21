"""The generic gate runner: config-driven checks, changelog rule, and red-first (`--red`)."""

import contextlib
import importlib.util
import io
import os
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest import mock

sys.dont_write_bytecode = True  # do not leave __pycache__ inside template/
SCRIPT = Path(__file__).resolve().parent.parent / "sdlc_kit" / "sdlc_check.py"
spec = importlib.util.spec_from_file_location("sdlc_check", SCRIPT)
sdlc_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdlc_check)

PY = sys.executable

FAKE_TOOL = textwrap.dedent(
    """
    import sys, time
    tid = sys.argv[1]
    if tid == "fails":
        print("noise"); print("AssertionError: 1 != 2"); print("trailing noise"); sys.exit(1)
    if tid == "passes":
        sys.exit(0)
    if tid == "typo":
        print("Ran 0 tests"); sys.exit(1)
    if tid == "slow":
        time.sleep(30)
    if tid == "unittest style":
        print("Traceback (most recent call last):"); print('  File "t.py", line 3, in test_x')
        print("AttributeError: module 'app' has no attribute 'new_feature'"); print()
        print("-" * 70); print("Ran 1 test in 0.001s"); print(); print("FAILED (errors=1)"); sys.exit(1)
    if tid == "pytest style":
        print("E   assert 1 == 2"); print("=========== short test summary info ===========")
        print("FAILED tests/test_x.py::test_y - assert 1 == 2"); print("============ 1 failed in 0.05s ============"); sys.exit(1)
    if tid == "anchored":
        print("header"); print("No tests found"); sys.exit(1)
    if tid == "indented":
        print("AssertionError: real reason"); print('  File "x.py", line 3, in fail_helper'); sys.exit(1)
    if tid == "spaced id":
        print("ValueError: got a spaced id"); sys.exit(1)
    """
)


def write_config(root: Path, body: str) -> None:
    (root / "sdlc.toml").write_text(textwrap.dedent(body))


def run_main(root: Path, *args: str):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = sdlc_check.main(["--root", str(root), *args])
        except SystemExit as exc:  # argparse errors
            code = exc.code
    return code, out.getvalue(), err.getvalue()


def git(root: Path, *args: str) -> str:
    # Hermetic: ignore the user's global config (signing would wait for a passphrase, hooks, templates).
    env = dict(
        os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1",
        GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
    )
    return subprocess.run(["git", *args], cwd=root, env=env, check=True, capture_output=True, text=True, timeout=30).stdout


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)


class TestConfig(Base):
    def test_missing_config_exits_2(self):
        code, _out, err = run_main(self.root)
        self.assertEqual(code, 2)
        self.assertIn("sdlc.toml", err)

    def test_invalid_toml_exits_2(self):
        (self.root / "sdlc.toml").write_text("this is [not toml")
        code, _out, err = run_main(self.root)
        self.assertEqual(code, 2)
        self.assertIn("sdlc.toml", err)

    def test_check_without_run_exits_2(self):
        write_config(self.root, '[[check]]\nname = "x"\n')
        code, _out, err = run_main(self.root)
        self.assertEqual(code, 2)
        self.assertIn("run", err)

    def test_red_run_needs_id_placeholder(self):
        write_config(self.root, '[[check]]\nname = "x"\nrun = "true"\n[red]\nrun = "true"\n')
        code, _out, err = run_main(self.root, "--red", "a")
        self.assertEqual(code, 2)
        self.assertIn("{id}", err)

    def test_red_timeout_must_be_a_positive_number(self):
        for bad in ('"soon"', "0", "-5"):
            write_config(self.root, f'[[check]]\nname = "x"\nrun = "true"\n[red]\nrun = "true {{id}}"\ntimeout = {bad}\n')
            code, _out, err = run_main(self.root, "--red", "a")
            self.assertEqual(code, 2, bad)
            self.assertIn("timeout", err)

    def test_changelog_runtime_paths_must_be_strings(self):
        write_config(self.root, '[changelog]\nfile = "C.md"\nruntime_paths = [1, 2]\n')
        code, _out, err = run_main(self.root)
        self.assertEqual(code, 2)
        self.assertIn("runtime_paths", err)

    def test_not_found_must_be_a_list_of_strings(self):
        write_config(self.root, '[[check]]\nname = "x"\nrun = "true"\n[red]\nrun = "true {id}"\nnot_found = "Ran 0 tests"\n')
        code, _out, err = run_main(self.root, "--red", "a")
        self.assertEqual(code, 2)
        self.assertIn("not_found", err)

    def test_wrongly_typed_keys_exit_2_not_a_traceback(self):
        bad = {
            "check as a table": '[check]\nname = "x"\nrun = "true"\n',
            "changelog not a table": 'changelog = 1\n[[check]]\nname = "x"\nrun = "true"\n',
            "red not a table": 'red = 3\n[[check]]\nname = "x"\nrun = "true"\n',
            "base not a string": 'base = 5\n[[check]]\nname = "x"\nrun = "true"\n',
            "skip_if_missing not a string": '[[check]]\nname = "x"\nrun = "true"\nskip_if_missing = 5\n',
            "check timeout not a number": '[[check]]\nname = "x"\nrun = "true"\ntimeout = "a"\n',
        }
        for label, body in bad.items():
            write_config(self.root, body)
            code, _out, err = run_main(self.root)
            self.assertEqual(code, 2, label)
            self.assertIn("sdlc.toml", err, label)

    def test_a_gate_with_no_checks_exits_2(self):
        write_config(self.root, 'base = "main"\n')
        code, _out, err = run_main(self.root)
        self.assertEqual(code, 2)
        self.assertIn("no checks", err)

    def test_unknown_only_name_exits_2(self):
        write_config(self.root, '[[check]]\nname = "x"\nrun = "true"\n')
        code, _out, err = run_main(self.root, "--only", "nope")
        self.assertEqual(code, 2)
        self.assertIn("nope", err)

    def test_duplicate_check_names_exit_2(self):
        write_config(self.root, '[[check]]\nname = "x"\nrun = "true"\n[[check]]\nname = "x"\nrun = "true"\n')
        code, _out, err = run_main(self.root)
        self.assertEqual(code, 2)
        self.assertIn("duplicate", err)


class TestConfigWarnings(Base):
    def test_unknown_keys_and_sections_warn_but_do_not_stop_the_gate(self):
        write_config(self.root, '[[check]]\nname = "x"\nrun = "true"\n[chagelog]\nfile = "C.md"\n[red]\nrun = "true {id}"\nnot_foud = ["a"]\n')
        code, out, err = run_main(self.root)
        self.assertEqual(code, 0)
        self.assertIn("unknown", err)
        self.assertIn("chagelog", err)
        self.assertIn("not_foud", err)

    def test_empty_runtime_path_entry_exits_2(self):
        write_config(self.root, '[changelog]\nfile = "C.md"\nruntime_paths = [""]\n')
        code, _out, err = run_main(self.root)
        self.assertEqual(code, 2)
        self.assertIn("runtime_paths", err)


class TestGate(Base):
    def test_all_pass_exits_0(self):
        write_config(self.root, '[[check]]\nname = "a"\nrun = "true"\n[[check]]\nname = "b"\nrun = "true"\n')
        code, out, _err = run_main(self.root)
        self.assertEqual(code, 0)
        self.assertIn("[PASS] a", out)
        self.assertIn("[PASS] b", out)

    def test_failing_check_exits_1_and_shows_output(self):
        write_config(self.root, '[[check]]\nname = "a"\nrun = "echo boom-detail; exit 3"\n')
        code, out, _err = run_main(self.root)
        self.assertEqual(code, 1)
        self.assertIn("[FAIL] a", out)
        self.assertIn("boom-detail", out)

    def test_later_checks_still_run_after_a_failure(self):
        write_config(self.root, '[[check]]\nname = "a"\nrun = "false"\n[[check]]\nname = "b"\nrun = "true"\n')
        code, out, _err = run_main(self.root)
        self.assertEqual(code, 1)
        self.assertIn("[PASS] b", out)

    def test_only_runs_the_named_checks(self):
        write_config(self.root, '[[check]]\nname = "a"\nrun = "false"\n[[check]]\nname = "b"\nrun = "true"\n')
        code, out, _err = run_main(self.root, "--only", "b")
        self.assertEqual(code, 0)
        self.assertNotIn("] a", out)

    def test_skip_if_missing_tool(self):
        write_config(self.root, '[[check]]\nname = "docs"\nrun = "no-such-tool-xyz build"\nskip_if_missing = "no-such-tool-xyz"\n')
        code, out, _err = run_main(self.root)
        self.assertEqual(code, 0)
        self.assertIn("[SKIP] docs", out)

    def test_a_background_child_does_not_hang_the_gate(self):
        write_config(self.root, '[[check]]\nname = "daemon"\nrun = "sleep 20 & echo started"\n')
        began = time.monotonic()
        code, out, _err = run_main(self.root)
        self.assertLess(time.monotonic() - began, 10)
        self.assertEqual(code, 0)
        self.assertIn("started", out)

    def test_per_check_timeout_fails_the_check(self):
        write_config(self.root, '[[check]]\nname = "slow"\nrun = "sleep 20"\ntimeout = 1\n')
        began = time.monotonic()
        code, out, _err = run_main(self.root)
        self.assertLess(time.monotonic() - began, 10)
        self.assertEqual(code, 1)
        self.assertIn("timed out", out)

    def test_pass_detail_is_the_last_line_and_is_truncated(self):
        write_config(self.root, f'[[check]]\nname = "a"\nrun = "echo first; echo last-line"\n[[check]]\nname = "b"\nrun = "{PY} -c \\"print(\'a\' * 5000)\\""\n')
        code, out, _err = run_main(self.root)
        self.assertEqual(code, 0)
        self.assertIn("last-line", out)
        self.assertNotIn("first", out)
        self.assertLess(max(len(line) for line in out.splitlines()), 400)

    def test_commands_left_in_the_background_are_killed_when_the_check_ends(self):
        write_config(self.root, '[[check]]\nname = "d"\nrun = "sleep 30 & echo $! > pidfile"\n')
        code, _out, _err = run_main(self.root)
        self.assertEqual(code, 0)
        self.assertProcessGone(int((self.root / "pidfile").read_text()))

    def test_timeout_kills_the_whole_process_group_not_just_the_shell(self):
        write_config(self.root, '[[check]]\nname = "d"\nrun = "sh -c \'sleep 30 & echo $! > pidfile; wait\'"\ntimeout = 1\n')
        run_main(self.root)
        self.assertProcessGone(int((self.root / "pidfile").read_text()))

    def test_sigterm_to_the_runner_kills_the_running_check(self):
        write_config(self.root, '[[check]]\nname = "d"\nrun = "sleep 30 & echo $! > pidfile; wait"\n')
        proc = subprocess.Popen([PY, str(SCRIPT), "--root", str(self.root)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.addCleanup(proc.kill)
        pidfile = self.root / "pidfile"
        for _ in range(100):
            if pidfile.exists() and pidfile.read_text().strip():
                break
            time.sleep(0.05)
        child = int(pidfile.read_text())
        proc.terminate()
        proc.wait(timeout=10)
        self.assertProcessGone(child)

    def test_output_is_capped_to_its_tail(self):
        with mock.patch.object(sdlc_check, "MAX_OUTPUT_BYTES", 2000):
            code, out = sdlc_check._run_shell("seq 1 20000", self.root)
        self.assertEqual(code, 0)
        self.assertLessEqual(len(out), 2000)
        self.assertTrue(out.rstrip().endswith("20000"))

    def assertProcessGone(self, pid: int) -> None:
        for _ in range(60):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.05)
        os.kill(pid, 9)
        self.fail(f"process {pid} is still running")

    def test_warns_when_no_check_actually_ran(self):
        write_config(self.root, '[[check]]\nname = "docs"\nrun = "x"\nskip_if_missing = "no-such-tool-xyz"\n')
        code, out, _err = run_main(self.root)
        self.assertEqual(code, 0)
        self.assertIn("warning", out.lower())

    def test_commands_run_from_the_project_root(self):
        (self.root / "marker.txt").write_text("x")
        write_config(self.root, '[[check]]\nname = "cwd"\nrun = "test -f marker.txt"\n')
        code, _out, _err = run_main(self.root)
        self.assertEqual(code, 0)


class TestChangelog(Base):
    def setUp(self):
        super().setUp()
        git(self.root, "init", "-q", "-b", "main")
        (self.root / "src").mkdir()
        (self.root / "src" / "a.py").write_text("1\n")
        (self.root / "CHANGELOG.md").write_text("# Changelog\n")
        write_config(
            self.root,
            """
            [[check]]
            name = "noop"
            run = "true"
            [changelog]
            file = "CHANGELOG.md"
            runtime_paths = ["src/"]
            """,
        )
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "base")

    def changelog(self, *extra: str):
        return run_main(self.root, "--only", "changelog", *extra)

    def test_no_runtime_change_passes(self):
        (self.root / "README.md").write_text("docs\n")
        code, out, _err = self.changelog()
        self.assertEqual(code, 0)
        self.assertIn("[PASS] changelog", out)

    def test_runtime_change_without_changelog_fails(self):
        (self.root / "src" / "a.py").write_text("2\n")
        code, out, _err = self.changelog()
        self.assertEqual(code, 1)
        self.assertIn("src/a.py", out)

    def test_runtime_change_with_changelog_passes(self):
        (self.root / "src" / "a.py").write_text("2\n")
        (self.root / "CHANGELOG.md").write_text("# Changelog\n- entry\n")
        code, _out, _err = self.changelog()
        self.assertEqual(code, 0)

    def test_untracked_runtime_file_counts(self):
        (self.root / "src" / "new.py").write_text("x\n")
        code, out, _err = self.changelog()
        self.assertEqual(code, 1)
        self.assertIn("src/new.py", out)

    def test_path_with_spaces_and_non_ascii_is_reported_verbatim(self):
        (self.root / "src" / "zażółć gęślą.py").write_text("x\n")
        code, out, _err = self.changelog()
        self.assertEqual(code, 1)
        self.assertIn("src/zażółć gęślą.py", out)

    def test_committed_change_is_seen_against_the_base(self):
        git(self.root, "checkout", "-q", "-b", "feature")
        (self.root / "src" / "a.py").write_text("3\n")
        git(self.root, "commit", "-q", "-am", "change")
        code, out, _err = self.changelog()
        self.assertEqual(code, 1)
        self.assertIn("src/a.py", out)

    def test_unresolvable_base_in_a_git_checkout_fails_loudly(self):
        code, out, _err = self.changelog("--base", "no-such-ref")
        self.assertEqual(code, 1)
        self.assertIn("[FAIL] changelog", out)
        self.assertIn("no-such-ref", out)
        self.assertIn("base", out)

    def test_repository_without_commits_is_skipped(self):
        other = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(other, ignore_errors=True))
        git(other, "init", "-q", "-b", "main")
        (other / "sdlc.toml").write_text((self.root / "sdlc.toml").read_text())
        code, out, _err = run_main(other, "--only", "changelog")
        self.assertEqual(code, 0)
        self.assertIn("[SKIP] changelog", out)

    def test_project_in_a_subdirectory_of_the_repository(self):
        mono = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(mono, ignore_errors=True))
        git(mono, "init", "-q", "-b", "main")
        proj = mono / "proj"
        (proj / "src").mkdir(parents=True)
        (mono / "other").mkdir()
        (proj / "src" / "a.py").write_text("1\n")
        (proj / "CHANGELOG.md").write_text("# c\n")
        (mono / "other" / "x.py").write_text("1\n")
        (proj / "sdlc.toml").write_text((self.root / "sdlc.toml").read_text())
        git(mono, "add", "-A")
        git(mono, "commit", "-q", "-m", "base")
        git(mono, "checkout", "-q", "-b", "feature")
        (mono / "other" / "x.py").write_text("2\n")
        git(mono, "commit", "-qam", "outside the project")
        code, out, _err = run_main(proj, "--only", "changelog")
        self.assertEqual(code, 0, out)
        (proj / "src" / "a.py").write_text("2\n")
        git(mono, "commit", "-qam", "inside the project")
        code, out, _err = run_main(proj, "--only", "changelog")
        self.assertEqual(code, 1, out)
        self.assertIn("src/a.py", out)

    def test_not_a_git_checkout_is_skipped(self):
        other = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(other, ignore_errors=True))
        (other / "sdlc.toml").write_text((self.root / "sdlc.toml").read_text())
        code, out, _err = run_main(other, "--only", "changelog")
        self.assertEqual(code, 0)
        self.assertIn("[SKIP] changelog", out)

    def test_no_changelog_section_means_no_such_check(self):
        write_config(self.root, '[[check]]\nname = "noop"\nrun = "true"\n')
        code, _out, err = run_main(self.root, "--only", "changelog")
        self.assertEqual(code, 2)
        self.assertIn("changelog", err)


class TestChangelogEdgeCases(Base):
    def setUp(self):
        super().setUp()
        git(self.root, "init", "-q", "-b", "main")
        for d in ("src", "src_old", "docs"):
            (self.root / d).mkdir()
        (self.root / "src" / "a.py").write_text("1\n")
        (self.root / "src_old" / "b.py").write_text("1\n")
        (self.root / "CHANGELOG.md").write_text("# c\n")
        self.config('"src/"', "CHANGELOG.md")
        git(self.root, "add", "-A")
        git(self.root, "commit", "-q", "-m", "base")
        git(self.root, "checkout", "-q", "-b", "feature")

    def config(self, paths: str, file: str) -> None:
        write_config(self.root, f'[[check]]\nname = "noop"\nrun = "true"\n[changelog]\nfile = "{file}"\nruntime_paths = [{paths}]\n')

    def changelog(self):
        return run_main(self.root, "--only", "changelog")

    def test_a_rename_out_of_a_runtime_path_is_a_runtime_change(self):
        git(self.root, "mv", "src/a.py", "docs/a.py")
        git(self.root, "commit", "-q", "-m", "move")
        code, out, _err = self.changelog()
        self.assertEqual(code, 1)
        self.assertIn("src/a.py", out)

    def test_head_at_the_base_says_that_committed_changes_are_not_compared(self):
        git(self.root, "checkout", "-q", "main")
        (self.root / "src" / "a.py").write_text("2\n")
        git(self.root, "commit", "-qam", "committed on the base branch")
        code, out, _err = self.changelog()
        self.assertEqual(code, 0)
        self.assertIn("HEAD is the base", out)

    def test_changelog_file_is_matched_after_normalising_the_path(self):
        self.config('"src/"', "./CHANGELOG.md")
        (self.root / "src" / "a.py").write_text("2\n")
        (self.root / "CHANGELOG.md").write_text("# c\n- entry\n")
        code, out, _err = self.changelog()
        self.assertEqual(code, 0, out)

    def test_runtime_path_without_trailing_slash_respects_directory_boundaries(self):
        self.config('"src"', "CHANGELOG.md")
        (self.root / "src_old" / "b.py").write_text("2\\n".replace("\\n", "\n"))
        code, out, _err = self.changelog()
        self.assertEqual(code, 0, out)
        (self.root / "src" / "a.py").write_text("2\n")
        code, out, _err = self.changelog()
        self.assertEqual(code, 1)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root can read any file")
    def test_a_git_failure_is_a_failure_not_a_silent_skip(self):
        sha = git(self.root, "rev-parse", "HEAD").strip()
        obj = self.root / ".git" / "objects" / sha[:2] / sha[2:]
        obj.chmod(0)
        self.addCleanup(lambda: obj.chmod(0o644))
        code, out, _err = self.changelog()
        self.assertEqual(code, 1)
        self.assertIn("[FAIL] changelog", out)

    def test_missing_git_executable_is_reported_not_a_traceback(self):
        with mock.patch.dict(os.environ, {"PATH": "/nonexistent"}):
            code, out, _err = self.changelog()
        self.assertEqual(code, 0)
        self.assertIn("[SKIP] changelog", out)
        self.assertIn("git", out)


class TestRed(Base):
    def setUp(self):
        super().setUp()
        (self.root / "fake_tool.py").write_text(FAKE_TOOL)
        write_config(
            self.root,
            f"""
            [[check]]
            name = "noop"
            run = "true"
            [red]
            run = "{PY} fake_tool.py {{id}}"
            timeout = 1
            not_found = ["Ran 0 tests"]
            ignore = ["^FAILED\\\\b", "^Ran \\\\d+ tests?", "^\\\\d+ failed", "^=+ "]
            """,
        )

    def test_failing_test_is_red_and_reason_is_the_error_line(self):
        code, out, _err = run_main(self.root, "--red", "fails")
        self.assertEqual(code, 0)
        self.assertIn("RED", out)
        self.assertIn("AssertionError: 1 != 2", out)
        self.assertNotIn("trailing noise", out)

    def test_reason_skips_unittest_summary_lines(self):
        code, out, _err = run_main(self.root, "--red", "unittest style")
        self.assertEqual(code, 0)
        self.assertIn("AttributeError: module 'app' has no attribute 'new_feature'", out)
        self.assertNotIn("FAILED (errors=1)", out)

    def test_reason_skips_pytest_summary_lines(self):
        code, out, _err = run_main(self.root, "--red", "pytest style")
        self.assertEqual(code, 0)
        self.assertIn("E   assert 1 == 2", out)
        self.assertNotIn("1 failed in", out)

    def test_tool_that_cannot_run_is_not_red(self):
        write_config(self.root, '[[check]]\nname = "noop"\nrun = "true"\n[red]\nrun = "no-such-tool-xyz {id}"\n')
        code, out, _err = run_main(self.root, "--red", "foo")
        self.assertEqual(code, 1)
        self.assertIn("NOT RED", out)
        self.assertIn("could not run", out)

    def test_test_killed_by_a_signal_is_not_red_even_when_the_shell_survives(self):
        write_config(
            self.root,
            f'[[check]]\nname = "noop"\nrun = "true"\n[red]\nrun = "cd . && {PY} -c \'import os, signal; os.kill(os.getpid(), signal.SIGKILL)\' {{id}}"\n',
        )
        code, out, _err = run_main(self.root, "--red", "x")
        self.assertEqual(code, 1)
        self.assertIn("could not run", out)

    def test_anchored_not_found_pattern_matches_a_later_line(self):
        write_config(self.root, f'[[check]]\nname = "noop"\nrun = "true"\n[red]\nrun = "{PY} fake_tool.py {{id}}"\nnot_found = ["^No tests found"]\n')
        code, out, _err = run_main(self.root, "--red", "anchored")
        self.assertEqual(code, 1)
        self.assertIn("not found", out)

    def test_ignore_patterns_see_the_indentation_of_the_line(self):
        write_config(self.root, f'[[check]]\nname = "noop"\nrun = "true"\n[red]\nrun = "{PY} fake_tool.py {{id}}"\nignore = ["^\\\\s+File"]\n')
        code, out, _err = run_main(self.root, "--red", "indented")
        self.assertEqual(code, 0)
        self.assertIn("AssertionError: real reason", out)

    def test_shipped_template_red_default_is_not_red(self):
        (self.root / "sdlc.toml").write_text((SCRIPT.parent.parent / "sdlc.toml").read_text())
        code, out, _err = run_main(self.root, "--red", "anything")
        self.assertEqual(code, 1)
        self.assertIn("NOT RED", out)

    def test_child_that_escapes_the_process_group_does_not_defeat_the_timeout(self):
        write_config(self.root, '[[check]]\nname = "noop"\nrun = "true"\n[red]\nrun = "sh -c \'setsid sleep 15 & sleep 30\' {id}"\ntimeout = 1\n')
        began = time.monotonic()
        code, out, _err = run_main(self.root, "--red", "x")
        self.assertLess(time.monotonic() - began, 10)
        self.assertEqual(code, 1)
        self.assertIn("timed out", out)

    def test_passing_test_is_not_red(self):
        code, out, _err = run_main(self.root, "--red", "passes")
        self.assertEqual(code, 1)
        self.assertIn("NOT RED", out)
        self.assertIn("passes already", out)

    def test_not_found_pattern_is_not_red(self):
        code, out, _err = run_main(self.root, "--red", "typo")
        self.assertEqual(code, 1)
        self.assertIn("NOT RED", out)
        self.assertIn("not found", out)

    def test_timeout_is_not_red(self):
        code, out, _err = run_main(self.root, "--red", "slow")
        self.assertEqual(code, 1)
        self.assertIn("timed out", out)

    def test_all_ids_must_be_red(self):
        code, out, _err = run_main(self.root, "--red", "fails", "passes")
        self.assertEqual(code, 1)
        self.assertIn("RED      fails", out)
        self.assertIn("NOT RED  passes", out)

    def test_id_is_shell_quoted(self):
        code, out, _err = run_main(self.root, "--red", "spaced id")
        self.assertEqual(code, 0)
        self.assertIn("got a spaced id", out)

    def test_id_cannot_inject_shell(self):
        code, out, _err = run_main(self.root, "--red", "fails; touch injected")
        self.assertFalse((self.root / "injected").exists())

    def test_red_cannot_be_combined_with_only_or_base(self):
        for extra in (["--only", "noop"], ["--base", "main"]):
            code, _out, err = run_main(self.root, "--red", "fails", *extra)
            self.assertEqual(code, 2)
            self.assertIn("--red", err)

    def test_missing_red_section_exits_2(self):
        write_config(self.root, '[[check]]\nname = "noop"\nrun = "true"\n')
        code, _out, err = run_main(self.root, "--red", "fails")
        self.assertEqual(code, 2)
        self.assertIn("[red]", err)

    def test_non_python_tool_works(self):
        write_config(self.root, '[[check]]\nname = "noop"\nrun = "true"\n[red]\nrun = "sh -c \'exit 1\' {id}"\n')
        code, out, _err = run_main(self.root, "--red", "anything")
        self.assertEqual(code, 0)
        self.assertIn("RED", out)


class TestPythonVersion(Base):
    def test_reexecs_under_a_newer_interpreter_when_tomllib_is_missing(self):
        write_config(self.root, '[[check]]\nname = "x"\nrun = "true"\n')
        with mock.patch.object(sdlc_check, "tomllib", None), \
                mock.patch.object(sdlc_check.shutil, "which", side_effect=lambda n: "/fake/python3.12" if n == "python3.12" else None), \
                mock.patch.object(sdlc_check.os, "execv") as execv:
            run_main(self.root, "--only", "x")
        execv.assert_called_once()
        path, argv = execv.call_args[0]
        self.assertEqual(path, "/fake/python3.12")
        self.assertEqual(argv[0], "/fake/python3.12")
        self.assertIn("--only", argv)

    def test_a_python_newer_than_the_ones_known_at_release_time_is_found(self):
        write_config(self.root, '[[check]]\nname = "x"\nrun = "true"\n')
        with mock.patch.object(sdlc_check, "tomllib", None), \
                mock.patch.object(sdlc_check.shutil, "which", side_effect=lambda n: "/fake/python3.17" if n == "python3.17" else None), \
                mock.patch.object(sdlc_check.os, "execv") as execv:
            run_main(self.root)
        self.assertEqual(execv.call_args[0][0], "/fake/python3.17")

    def test_clear_error_when_no_newer_interpreter_exists(self):
        with mock.patch.object(sdlc_check, "tomllib", None), mock.patch.object(sdlc_check.shutil, "which", return_value=None):
            code, _out, err = run_main(self.root)
        self.assertEqual(code, 2)
        self.assertIn("3.11", err)


if __name__ == "__main__":
    unittest.main()
