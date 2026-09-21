# Releasing

This page is for maintainers of the kit itself. The process mirrors [`prism-local`](https://github.com/senssei/prism-local) and
uses PyPI **trusted publishing** (OIDC), so no API tokens are stored anywhere. The workflow is `.github/workflows/publish.yml`
(manual: *Actions -> Publish -> Run workflow*); it runs the gate before it builds.

## One-time setup

1. On [test.pypi.org](https://test.pypi.org/manage/account/publishing/) (and later [pypi.org](https://pypi.org/manage/account/publishing/)),
   add a *pending publisher*: project `sdlc-kit`, owner `senssei`, repository `sdlc-kit`, workflow `publish.yml`,
   environment `testpypi` (respectively `pypi`).
2. In the GitHub repository, create the environments `testpypi` and `pypi` (*Settings -> Environments*). Add yourself as a
   required reviewer on `pypi` so a release needs an explicit approval.
3. For this documentation site: *Settings -> Pages -> Source: GitHub Actions*. `.github/workflows/docs.yml` then deploys it from
   `main`.

## Each release

1. Update `CHANGELOG.md` (move `[Unreleased]` items under a dated `[X.Y.Z] - YYYY-MM-DD` heading) and
   `sdlc_kit/__init__.py` (`__version__`), and merge to `main` with the gate green (`python3 sdlc_kit/sdlc_check.py`
   exits 0).
2. Run **Publish -> target `testpypi`**. It runs the gate, builds the sdist and wheel, runs `twine check --strict`, uploads to
   TestPyPI, then installs the uploaded version into a clean virtualenv and smoke-tests `sdlc-kit-install --help`.
3. Tag the release (`git tag -s vX.Y.Z && git push origin vX.Y.Z`) and run **Publish** on that tag with target `pypi`. The
   workflow refuses to publish to PyPI unless it runs from the tag `v<__version__>`.
4. Create a GitHub release for the tag.

!!! warning "Versions are permanent"
    Neither index lets you re-upload a version, and PyPI never lets you reuse one. Use a pre-release version such as `0.1.0rc1`
    while rehearsing on TestPyPI if you expect to iterate.
