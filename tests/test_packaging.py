"""Packaging (Phase 3): pyproject, sdist+wheel, twine check, venv smoke test, K1/K4 still hold.

These tests are red-first: every assertion fails until the corresponding item in plan.md Phase 3 is implemented.
"""

import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.dont_write_bytecode = True


class TestPackageLayout(unittest.TestCase):
    """Items 1 and 2: sdlc_kit/ package + top-level install.py shim."""

    def test_sdlc_kit_package_exists(self):
        self.assertTrue((ROOT / "sdlc_kit" / "__init__.py").is_file(), "sdlc_kit/__init__.py")

    def test_sdlc_kit_has_version(self):
        spec = importlib.util.spec_from_file_location("sdlc_kit", ROOT / "sdlc_kit" / "__init__.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue(hasattr(mod, "__version__"), "sdlc_kit.__version__")
        self.assertRegex(mod.__version__, r"^\d+\.\d+\.\d+(?:rc\d+)?$")

    def test_install_module_inside_package(self):
        self.assertTrue((ROOT / "sdlc_kit" / "install.py").is_file())
        # it must still expose main() (callable returning int)
        spec = importlib.util.spec_from_file_location("sdlc_kit_install_inner", ROOT / "sdlc_kit" / "install.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue(callable(getattr(mod, "main", None)))

    def test_runner_inside_package(self):
        self.assertTrue((ROOT / "sdlc_kit" / "sdlc_check.py").is_file())

    def test_template_directory_inside_package(self):
        self.assertTrue((ROOT / "sdlc_kit" / "template").is_dir())
        for rel in ("AGENTS.md", "sdlc.toml", "intent.md", "spec.md", "plan.md", "REVIEW.md",
                    "skills/sdlc/SKILL.md", "skills/sdlc-plan/SKILL.md",
                    "adapters/CLAUDE.md", "adapters/MCODE.md", "adapters/cursor-sdlc.mdc",
                    "githooks/pre-commit"):
            self.assertTrue((ROOT / "sdlc_kit" / "template" / rel).is_file(), rel)

    def test_top_level_install_shim(self):
        shim = ROOT / "install.py"
        self.assertTrue(shim.is_file(), "top-level install.py shim")
        text = shim.read_text(encoding="utf-8")
        self.assertIn("sdlc_kit.install", text)
        self.assertIn("main", text)
        # must NOT be the real installer (that moved into the package)
        self.assertNotIn("ENTRIES", text, "shim must not redefine installer internals")


class TestPyproject(unittest.TestCase):
    """Item 3: pyproject.toml with setuptools backend, dynamic version, no runtime deps, entry point."""

    def setUp(self):
        self.path = ROOT / "pyproject.toml"
        self.assertTrue(self.path.is_file(), "pyproject.toml")
        with self.path.open("rb") as f:
            self.data = tomllib.load(f)

    def test_build_backend_is_setuptools(self):
        self.assertEqual(self.data["build-system"]["build-backend"], "setuptools.build_meta")

    def test_project_name(self):
        self.assertEqual(self.data["project"]["name"], "sdlc-kit")

    def test_dynamic_version(self):
        self.assertIn("version", self.data["project"].get("dynamic", []))

    def test_runtime_dependencies_are_empty(self):
        self.assertEqual(self.data["project"].get("dependencies", []), [])

    def test_requires_python(self):
        self.assertGreaterEqual(self.data["project"]["requires-python"], ">=3.11")

    def test_entry_point_exposes_installer(self):
        scripts = self.data["project"].get("scripts", {})
        self.assertIn("sdlc-kit-install", scripts)
        self.assertEqual(scripts["sdlc-kit-install"], "sdlc_kit.install:main")

    def test_urls_include_github_repo(self):
        urls = self.data["project"].get("urls", {})
        self.assertIn("Homepage", urls)
        self.assertIn("Issues", urls)
        self.assertIn("Changelog", urls)
        for name, url in urls.items():
            if name == "Documentation":  # the MkDocs site on GitHub Pages
                self.assertIn("github.io", url.lower(), url)
            else:
                self.assertIn("github.com", url.lower(), url)

    def test_license_is_apache(self):
        self.assertIn("Apache", str(self.data["project"].get("license", "")))

    def test_packages_lists_sdlc_kit(self):
        self.assertIn("sdlc_kit", self.data["tool"]["setuptools"]["packages"])

    def test_setuptools_knows_about_template_data(self):
        # package-data must include the template files so the wheel ships them
        pkg_data = self.data["tool"]["setuptools"].get("package-data", {})
        sdlc_kit_data = pkg_data.get("sdlc_kit", [])
        joined = " ".join(sdlc_kit_data)
        self.assertIn("template", joined)

    def test_dev_extra_includes_build_and_twine(self):
        dev = self.data["project"]["optional-dependencies"]["dev"]
        joined = " ".join(dev)
        self.assertIn("build", joined)
        self.assertIn("twine", joined)


class TestManifest(unittest.TestCase):
    """Item 4: MANIFEST.in."""

    def test_manifest_in_exists(self):
        self.assertTrue((ROOT / "MANIFEST.in").is_file())

    def test_manifest_includes_license_readme_changelog(self):
        text = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
        for needle in ("LICENSE", "README.md", "CHANGELOG.md"):
            self.assertIn(needle, text, needle)

    def test_manifest_prunes_tests(self):
        text = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
        self.assertRegex(text, r"\bprune\s+tests\b")

    def test_manifest_includes_template_recursively(self):
        text = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")
        self.assertRegex(text, r"recursive-include\s+sdlc_kit[/\\.]template\b")


class TestDistFiles(unittest.TestCase):
    """Items 5: LICENSE, CHANGELOG.md, CONTRIBUTING.md, SECURITY.md."""

    def test_license_present_and_apache(self):
        text = (ROOT / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("Apache License", text)
        self.assertIn("Version 2.0", text)

    def test_changelog_present_and_keep_a_changelog(self):
        text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("Keep a Changelog", text)
        self.assertIn("SemVer", text)
        self.assertIn("[Unreleased]", text)

    def test_contributing_present(self):
        self.assertTrue((ROOT / "CONTRIBUTING.md").is_file())
        text = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        # at minimum: setup, tests, PR section
        for needle in ("Setup", "Tests", "Pull requests"):
            self.assertIn(needle, text, needle)

    def test_security_present(self):
        self.assertTrue((ROOT / "SECURITY.md").is_file())
        text = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
        for needle in ("Reporting", "Supported versions"):
            self.assertIn(needle, text, needle)


class TestInvariantsStillHold(unittest.TestCase):
    """K1 still forbids project names in installed content; K4 still forbids runtime deps."""

    FORBIDDEN = re.compile(r"\b(prism|foundry|ollama|unittest|pytest|jest|cargo|npm|mkdocs|pip|pyproject|sql|ruff|gradle|maven)\b", re.IGNORECASE)

    def _template_files(self):
        tpl = ROOT / "sdlc_kit" / "template"
        return [p for p in sorted(tpl.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]

    def test_k1_no_project_names_in_template(self):
        offenders = []
        for path in self._template_files():
            if path.name == "sdlc.toml":
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                m = self.FORBIDDEN.search(line)
                if m:
                    offenders.append(f"{path.relative_to(ROOT / 'sdlc_kit')}:{n}: {m.group(0)}")
        self.assertEqual(offenders, [], offenders)

    def test_k4_no_third_party_imports_in_runtime(self):
        # Every .py file in sdlc_kit/ except __init__.py and the runner must stdlib-only.
        # The runner imports tomllib (stdlib) and that is the same library it already used.
        # We re-check: nothing outside the standard library.
        stdlib = set(sys.stdlib_module_names) if hasattr(sys, "stdlib_module_names") else None
        offenders = []
        for path in sorted((ROOT / "sdlc_kit").rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            tree = importlib.util.spec_from_file_location("_anon_" + path.stem, path)
            # Cheap static scan instead, because loading may run side effects.
            text = path.read_text(encoding="utf-8")
            for m in re.finditer(r"^\s*(?:from|import)\s+([A-Za-z_][\w]*)", text, re.MULTILINE):
                mod = m.group(1)
                if mod in ("__future__",):
                    continue
                if stdlib is not None and mod in stdlib:
                    continue
                # not in stdlib -> could be third-party. For maintainer tooling (pyproject not in sdlc_kit), this is fine; but sdlc_kit/* is runtime.
                offenders.append(f"{path.relative_to(ROOT)}: {mod}")
        self.assertEqual(offenders, [], offenders)


class TestBuildWheelAndSdist(unittest.TestCase):
    """Items 3 and 4 verified end-to-end: build, twine check, wheel contents."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.dist = Path(cls._tmp.name) / "dist"
        cls.dist.mkdir()
        # Build with the maintainer toolchain. We assume `build` is importable in the test env.
        # If it is not, skip — the rest of the suite still runs.
        try:
            import build  # noqa: F401
        except ImportError:
            cls._skip = True
            return
        cls._skip = False
        env = os.environ.copy()
        env.setdefault("GIT_CONFIG_GLOBAL", "/dev/null")
        proc = subprocess.run([sys.executable, "-m", "build", "--outdir", str(cls.dist), str(ROOT)],
                              env=env, capture_output=True, text=True)
        if proc.returncode != 0:
            raise AssertionError(f"`python -m build` failed:\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def setUp(self):
        if self._skip:
            self.skipTest("`build` module not installed")

    def test_sdist_and_wheel_exist(self):
        files = sorted(p.name for p in self.dist.iterdir())
        self.assertTrue(any(f.endswith(".whl") for f in files), files)
        self.assertTrue(any(f.endswith(".tar.gz") for f in files), files)

    def test_wheel_name(self):
        wheels = [p for p in self.dist.iterdir() if p.name.endswith(".whl")]
        self.assertEqual(len(wheels), 1)
        # PEP 427: sdlc_kit-<version>-py3-none-any.whl
        self.assertRegex(wheels[0].name, r"^sdlc_kit-[\d.]+(?:rc\d+)?-py3-none-any\.whl$")

    def test_wheel_contains_template_and_runner(self):
        wheels = [p for p in self.dist.iterdir() if p.name.endswith(".whl")]
        with zipfile.ZipFile(wheels[0]) as z:
            names = z.namelist()
        for needle in ("sdlc_kit/sdlc_check.py", "sdlc_kit/install.py",
                       "sdlc_kit/template/AGENTS.md", "sdlc_kit/template/sdlc.toml",
                       "sdlc_kit/template/skills/sdlc/SKILL.md",
                       "sdlc_kit/template/adapters/CLAUDE.md",
                       "sdlc_kit/template/adapters/MCODE.md"):
            self.assertIn(needle, names, needle)

    def test_wheel_metadata_has_no_runtime_deps(self):
        wheels = [p for p in self.dist.iterdir() if p.name.endswith(".whl")]
        with zipfile.ZipFile(wheels[0]) as z:
            metadata = z.read([n for n in z.namelist() if n.endswith("METADATA")][0]).decode("utf-8")
        # Requires-Dist without `; extra == "..."` is a runtime dep and must be absent.
        # Optional extras (declared via [project.optional-dependencies]) are emitted as
        # `Requires-Dist: foo ; extra == "extra-name"`; they are not runtime deps.
        runtime_deps = [
            line for line in metadata.splitlines()
            if line.startswith("Requires-Dist: ") and "extra ==" not in line
        ]
        self.assertEqual(runtime_deps, [], runtime_deps)

    def test_wheel_metadata_has_console_scripts(self):
        wheels = [p for p in self.dist.iterdir() if p.name.endswith(".whl")]
        with zipfile.ZipFile(wheels[0]) as z:
            entry = z.read([n for n in z.namelist() if n.endswith("entry_points.txt")][0]).decode("utf-8")
        self.assertIn("sdlc-kit-install", entry)
        self.assertIn("sdlc_kit.install:main", entry)

    def test_twine_check_strict_passes(self):
        try:
            import twine  # noqa: F401
        except ImportError:
            self.skipTest("`twine` module not installed")
        proc = subprocess.run([sys.executable, "-m", "twine", "check", "--strict", *map(str, self.dist.iterdir())],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_venv_install_smoke_test(self):
        wheels = [p for p in self.dist.iterdir() if p.name.endswith(".whl")]
        with tempfile.TemporaryDirectory() as venv_dir:
            cmd = [sys.executable, "-m", "venv", venv_dir]
            subprocess.run(cmd, check=True, capture_output=True)
            pip = Path(venv_dir) / "bin" / "pip"
            cli = Path(venv_dir) / "bin" / "sdlc-kit-install"
            # Install the wheel + nothing else (no internet); if the install pulls deps, fail.
            proc = subprocess.run([str(pip), "install", "--no-index", "--no-deps", str(wheels[0])],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertTrue(cli.is_file(), "sdlc-kit-install console script must exist")
            help_proc = subprocess.run([str(cli), "--help"], capture_output=True, text=True)
            self.assertEqual(help_proc.returncode, 0, help_proc.stdout + help_proc.stderr)
            # The CLI must list the same harness set as the in-repo installer.
            for needle in ("claude", "codex", "gemini", "copilot", "cursor", "mcode"):
                self.assertIn(needle, help_proc.stdout, needle)


class TestPublishWorkflow(unittest.TestCase):
    """Item 6: .github/workflows/publish.yml is a valid trusted-publishing workflow."""

    def test_publish_workflow_exists(self):
        self.assertTrue((ROOT / ".github" / "workflows" / "publish.yml").is_file())

    def test_publish_workflow_is_valid_yaml(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML not installed")
        with (ROOT / ".github" / "workflows" / "publish.yml").open() as f:
            data = yaml.safe_load(f)
        # PyYAML turns `on:` into the boolean True; accept either key.
        on_key = True if True in data else "on"
        on = data.get(on_key, {})
        self.assertIn("workflow_dispatch", on)
        self.assertIn("inputs", on["workflow_dispatch"])
        self.assertIn("target", on["workflow_dispatch"]["inputs"])

    def test_publish_workflow_uses_trusted_publishing(self):
        text = (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
        self.assertIn("pypa/gh-action-pypi-publish", text)
        self.assertIn("id-token: write", text)

    def test_publish_workflow_does_not_reference_pypi_token_secret(self):
        text = (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
        for needle in ("TWINE_TOKEN", "PYPI_TOKEN", "pypi-token", "twine-token"):
            self.assertNotIn(needle, text, needle)

    def test_publish_workflow_refuses_pypi_outside_tag(self):
        text = (ROOT / ".github" / "workflows" / "publish.yml").read_text(encoding="utf-8")
        # Gating: must check GITHUB_REF_TYPE == tag and name == v<version>
        self.assertIn("GITHUB_REF_TYPE", text)
        self.assertIn("GITHUB_REF_NAME", text)
        self.assertIn('v$VERSION', text)


class TestCiWorkflow(unittest.TestCase):
    """Phase 4: ci.yml runs the gate on a Python matrix and a build; publish.yml runs the gate before building."""

    CI = ROOT / ".github" / "workflows" / "ci.yml"
    PUBLISH = ROOT / ".github" / "workflows" / "publish.yml"

    def _ci(self):
        self.assertTrue(self.CI.is_file(), "ci.yml missing")
        return self.CI.read_text(encoding="utf-8")

    def test_ci_triggers_on_push_and_pull_request(self):
        text = self._ci()
        self.assertRegex(text, r"(?m)^  push:")
        self.assertRegex(text, r"(?m)^  pull_request:")

    def test_ci_runs_the_gate_on_every_supported_python(self):
        text = self._ci()
        self.assertIn("sdlc_kit/sdlc_check.py", text)
        for minor in ("3.11", "3.12", "3.13"):
            self.assertIn(f'"{minor}"', text, minor)

    def test_ci_builds_and_checks_the_distribution(self):
        text = self._ci()
        self.assertIn("python -m build", text)
        self.assertIn("twine check --strict", text)

    def test_ci_is_read_only_and_holds_no_token(self):
        text = self._ci()
        self.assertIn("contents: read", text)
        self.assertNotIn("id-token", text)
        for needle in ("TWINE_TOKEN", "PYPI_TOKEN", "pypi-token", "twine-token"):
            self.assertNotIn(needle, text, needle)

    def test_publish_runs_the_gate_before_building(self):
        text = self.PUBLISH.read_text(encoding="utf-8")
        self.assertIn("sdlc_kit/sdlc_check.py", text)
        self.assertLess(text.index("sdlc_kit/sdlc_check.py"), text.index("python -m build"))

    def test_workflows_use_no_outdated_artifact_actions(self):
        for path in (self.CI, self.PUBLISH):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                self.assertNotRegex(text, r"actions/(up|down)load-artifact@v4", path.name)


if __name__ == "__main__":
    unittest.main()