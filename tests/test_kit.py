"""Invariants of the kit content: K1 (no project/tool names), K2 (process rules only in AGENTS.md), skill format."""

import re
import unittest
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "sdlc_kit" / "template"
# sdlc.toml is where examples of other tools belong (K1 exempts it); everything else must stay neutral.
FORBIDDEN = re.compile(r"\b(prism|foundry|ollama|unittest|pytest|jest|cargo|npm|mkdocs|pip|pyproject|sql|ruff|gradle|maven)\b", re.IGNORECASE)


def template_files():
    return [p for p in sorted(TEMPLATE.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]


class TestNoProjectNames(unittest.TestCase):
    def test_template_names_no_project_or_test_tool(self):
        offenders = []
        for path in template_files():
            if path.name == "sdlc.toml":
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                m = FORBIDDEN.search(line)
                if m:
                    offenders.append(f"{path.relative_to(TEMPLATE)}:{n}: {m.group(0)}")
        self.assertEqual(offenders, [])

    def test_template_exists(self):
        self.assertTrue((TEMPLATE / "AGENTS.md").is_file())
        self.assertTrue((TEMPLATE / "sdlc_check.py").is_file())


class TestAdapters(unittest.TestCase):
    ADAPTERS = ["CLAUDE.md", "GEMINI.md", "copilot-instructions.md", "cursor-sdlc.mdc", "MCODE.md"]

    def test_every_adapter_points_to_agents_md(self):
        for name in self.ADAPTERS:
            text = (TEMPLATE / "adapters" / name).read_text(encoding="utf-8")
            self.assertIn("AGENTS.md", text, name)

    def test_adapters_do_not_redefine_the_process(self):
        for name in self.ADAPTERS:
            text = (TEMPLATE / "adapters" / name).read_text(encoding="utf-8")
            self.assertNotIn("### Process rules", text, name)
            self.assertNotIn("| Intent |", text, name)

    def test_only_agents_md_defines_the_process_table(self):
        holders = [p.name for p in template_files() if "| 1 | Intent |" in p.read_text(encoding="utf-8")]
        self.assertEqual(holders, ["AGENTS.md"])


class TestSingleSourceOfRules(unittest.TestCase):
    """K2: the operator gates and the independent-review rule are stated once, in AGENTS.md; everything else points there."""

    def read(self, rel):
        return (TEMPLATE / rel).read_text(encoding="utf-8")

    def test_adapters_and_review_policy_do_not_restate_the_rules(self):
        for rel in ("adapters/CLAUDE.md", "adapters/GEMINI.md", "adapters/copilot-instructions.md", "adapters/cursor-sdlc.mdc", "adapters/MCODE.md", "REVIEW.md"):
            text = self.read(rel)
            for phrase in ("explicit ask", "fresh subagent", "never the one that wrote", "Stop and ask"):
                self.assertNotIn(phrase, text, f"{rel}: {phrase}")

    def test_nothing_points_at_a_removed_review_section(self):
        for path in template_files():
            self.assertNotIn("section 4", path.read_text(encoding="utf-8"), str(path.relative_to(TEMPLATE)))

    def test_agents_md_holds_the_push_and_force_push_rules(self):
        text = self.read("AGENTS.md")
        self.assertIn("force-push", text)
        self.assertNotIn("force-push", self.read("skills/sdlc-release/SKILL.md"))


class TestRunnerStaysToolNeutral(unittest.TestCase):
    """K5: the runner knows no test tool's output format; those live in sdlc.toml (`not_found`, `ignore`)."""

    def test_runner_source_has_no_tool_output_formats(self):
        src = (TEMPLATE / "sdlc_check.py").read_text(encoding="utf-8")
        for needle in ("panic", "not ok", "Ran \\d", "FAILED (", "failed in", "short test summary", "_FailedTest", "Traceback", "--- FAIL"):
            self.assertNotIn(needle, src, needle)


class TestSkillsMatchTheRunner(unittest.TestCase):
    def test_no_skill_names_a_check_that_may_not_exist(self):
        for path in (TEMPLATE / "skills").rglob("SKILL.md"):
            self.assertNotIn("--only tests", path.read_text(encoding="utf-8"), str(path))

    def test_the_router_does_not_tell_the_agent_to_invoke_the_user_only_release_skill(self):
        text = (TEMPLATE / "skills" / "sdlc" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("ask the user to run", text)

    def test_skills_use_the_configured_base_branch_not_a_hardcoded_main(self):
        for name in ("sdlc", "sdlc-review", "sdlc-release"):
            text = (TEMPLATE / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            self.assertNotIn("merge-base main", text, name)
            self.assertNotIn("--base main", text, name)

    def test_plan_skill_records_intent_approval(self):
        text = (TEMPLATE / "skills" / "sdlc-plan" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("approved by the operator", text)
        self.assertIn("intent.md", text.split("approved by the operator", 1)[0][-400:])


class TestGuidanceFromTheDryRun(unittest.TestCase):
    """Gaps a fresh agent hit when it followed the skills in a project that was not this one."""

    def read(self, rel):
        return (TEMPLATE / rel).read_text(encoding="utf-8")

    def test_agents_md_tells_where_the_commands_are_defined(self):
        text = self.read("AGENTS.md")
        self.assertIn("sdlc.toml", text.split("## Development process", 1)[0])

    def test_plan_skill_says_what_to_do_when_intent_is_still_the_template(self):
        text = self.read("skills/sdlc-plan/SKILL.md")
        self.assertIn("untouched template", text)
        self.assertIn("do not invent", text.lower())

    def test_plan_skill_puts_open_questions_into_the_approval_request(self):
        self.assertIn("approval request", self.read("skills/sdlc-plan/SKILL.md"))

    def test_plan_skill_shows_new_artifacts_that_git_diff_does_not_list(self):
        self.assertIn("git status", self.read("skills/sdlc-plan/SKILL.md"))

    def test_implement_skill_says_to_import_the_missing_code_inside_the_test(self):
        text = self.read("skills/sdlc-implement/SKILL.md")
        self.assertIn("inside the test", text)

    def test_implement_skill_says_what_to_do_with_a_test_that_passes_at_once(self):
        self.assertIn("passes at once", self.read("skills/sdlc-implement/SKILL.md"))

    def test_implement_skill_lists_command_could_not_run_as_not_red(self):
        self.assertIn("could not run", self.read("skills/sdlc-implement/SKILL.md"))

    def test_router_explains_an_empty_range_on_the_base_branch(self):
        self.assertIn("on the base branch", self.read("skills/sdlc/SKILL.md"))

    def test_agents_md_allows_configuring_the_gate_but_not_weakening_it(self):
        text = self.read("AGENTS.md")
        self.assertIn("first-time set-up", text)


class TestSkills(unittest.TestCase):
    NAMES = ["sdlc", "sdlc-plan", "sdlc-implement", "sdlc-review", "sdlc-release"]

    def test_each_skill_has_matching_frontmatter(self):
        for name in self.NAMES:
            text = (TEMPLATE / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
            m = re.match(r"---\nname: (.+)\ndescription: (.+)\n(?:.*\n)*?---\n", text)
            self.assertIsNotNone(m, name)
            self.assertEqual(m.group(1), name)
            self.assertGreater(len(m.group(2)), 40, name)

    def test_no_unexpected_skill_directories(self):
        found = sorted(p.name for p in (TEMPLATE / "skills").iterdir())
        self.assertEqual(found, sorted(self.NAMES))


if __name__ == "__main__":
    unittest.main()
