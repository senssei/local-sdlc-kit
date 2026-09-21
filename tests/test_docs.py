"""Docs site (Phase 5): mkdocs.yml + docs/, built with MkDocs in CI and deployed to GitHub Pages.

Structure tests run with the standard library only; the real build runs when `mkdocs` is installed.
"""

import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True
DOCS = ROOT / "docs"
MKDOCS = ROOT / "mkdocs.yml"
SITE_URL = "https://senssei.github.io/sdlc-kit/"


def read(path):
    return path.read_text(encoding="utf-8")


def nav_files():
    return re.findall(r"(?m)^\s*-\s+(?:[^:\n]+:\s+)?([\w./-]+\.md)\s*$", read(MKDOCS))


class TestMkdocsConfig(unittest.TestCase):
    def test_config_exists_with_site_name_and_strict(self):
        self.assertTrue(MKDOCS.is_file(), "mkdocs.yml missing")
        text = read(MKDOCS)
        self.assertRegex(text, r"(?m)^site_name:\s*\S")
        self.assertRegex(text, r"(?m)^strict:\s*true\s*$")

    def test_nav_lists_the_pages_and_every_file_exists(self):
        files = nav_files()
        for page in ("index.md", "install.md", "process.md", "harnesses.md", "gate.md", "releasing.md"):
            self.assertIn(page, files, page)
        for page in files:
            self.assertTrue((DOCS / page).is_file(), f"nav points at missing docs/{page}")

    def test_every_docs_page_is_in_the_nav(self):
        files = set(nav_files())
        for page in DOCS.glob("*.md"):
            self.assertIn(page.name, files, f"{page.name} is not in the nav")

    def test_relative_links_resolve(self):
        for page in DOCS.glob("*.md"):
            for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", read(page)):
                if re.match(r"[a-z]+:", target):
                    continue
                self.assertTrue((page.parent / target).resolve().exists(), f"{page.name}: broken link {target}")


class TestDocsDependencies(unittest.TestCase):
    def setUp(self):
        self.project = tomllib.loads(read(ROOT / "pyproject.toml"))["project"]

    def test_docs_extra_pins_mkdocs_below_2(self):
        docs = self.project.get("optional-dependencies", {}).get("docs", [])
        self.assertTrue(any(d.startswith("mkdocs") and "<2" in d for d in docs), docs)

    def test_runtime_dependencies_stay_empty(self):
        self.assertEqual(self.project["dependencies"], [])

    def test_docs_are_not_shipped(self):
        self.assertIn("prune docs", read(ROOT / "MANIFEST.in"))

    def test_site_output_is_ignored(self):
        self.assertRegex(read(ROOT / ".gitignore"), r"(?m)^site/$")


class TestDocsWorkflows(unittest.TestCase):
    def test_ci_builds_the_docs_strictly(self):
        self.assertIn("mkdocs build --strict", read(ROOT / ".github" / "workflows" / "ci.yml"))

    def test_docs_workflow_deploys_from_main_with_scoped_permissions(self):
        path = ROOT / ".github" / "workflows" / "docs.yml"
        self.assertTrue(path.is_file(), "docs.yml missing")
        text = read(path)
        self.assertRegex(text, r"(?m)^  push:")
        self.assertIn("branches: [main]", text)
        self.assertIn("mkdocs build --strict", text)
        self.assertIn("actions/deploy-pages", text)
        self.assertIn("pages: write", text)
        self.assertRegex(text, r"(?m)^permissions:\n  contents: read\n")  # write scopes only on the deploy job
        self.assertNotRegex(text, r"(?m)^permissions:\n(?:  .*\n)*?  (pages|id-token): write")
        for needle in ("TWINE_TOKEN", "PYPI_TOKEN", "pypi-token", "secrets."):
            self.assertNotIn(needle, text, needle)


class TestDocsLinkedFromRepo(unittest.TestCase):
    def test_readme_links_to_the_site_and_does_not_repeat_the_reference(self):
        text = read(ROOT / "README.md")
        self.assertIn(SITE_URL, text)
        self.assertIn("pip install sdlc-kit", text)
        self.assertIn("sdlc-kit-install", text)
        self.assertNotIn("Trusted publishing setup", text)
        self.assertNotIn("[[check]]", text)  # the sdlc.toml reference lives in docs/gate.md

    def test_contributing_knows_about_the_docs_site(self):
        text = read(ROOT / "CONTRIBUTING.md")
        self.assertNotIn("does not publish a separate docs site", text)
        self.assertIn("mkdocs", text)
        self.assertIn("docs/releasing.md", text)

    def test_process_page_points_to_the_single_source(self):
        self.assertIn("sdlc_kit/template/AGENTS.md", read(DOCS / "process.md"))


@unittest.skipUnless(shutil.which("mkdocs"), "mkdocs not installed")
class TestMkdocsBuild(unittest.TestCase):
    def test_strict_build_succeeds(self):
        with tempfile.TemporaryDirectory() as out:
            proc = subprocess.run(
                ["mkdocs", "build", "--strict", "-f", str(MKDOCS), "-d", out],
                cwd=ROOT, capture_output=True, text=True, timeout=120,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertTrue((Path(out) / "index.html").is_file())


if __name__ == "__main__":
    unittest.main()
