# Security Policy

## Reporting a vulnerability

Please report security issues privately through GitHub's
[private vulnerability reporting](https://github.com/senssei/sdlc-kit/security/advisories/new) rather than a public
issue. Include the version, how you run `sdlc-kit-install` (target directory, flags), and steps to reproduce. This is
a small alpha project, so expect a best-effort response, but reports are taken seriously.

## Threat model

`sdlc-kit` is a **file scaffolder** for a development process.

- The installer copies template files into a target directory and never overwrites files the project already owns
  (K3 in `spec.md`). It does not read, transmit or transform user code.
- The kit is **standard library only at runtime**. The only network access during `pip install` is fetching the wheel
  and its dependencies (the wheel has none).
- The pre-commit hook (`.githooks/pre-commit`) runs the gate locally; it does not contact any network service.
- The PyPI release uses GitHub Actions trusted publishing (OIDC) — no API tokens are stored in the repository.
- Setting `--target` to a directory outside the project is refused when the parent path is a symlink leading
  outside the target (`tests/test_install.py::TestSafety::test_symlinked_parent_directory_never_sends_writes_outside_the_target`).

Supported versions: the latest release only. Older releases are not patched.