# Contributing to Aurynk

Welcome, and thank you for helping move Aurynk forward. This guide keeps contributors aligned on tooling, workflow, and release practices.

## Contents

- [Quick start](#quick-start)
- [What to change here](#what-to-change-here)
- [Backporting](#backporting)
- [Tests & checks](#tests--checks)
- [PR guidance](#pr-guidance)
- [Contact](#contact)

## Additional Guides

For more detailed information, see:
- **[BUILDING.md](docs/BUILDING.md)** - Comprehensive build instructions for all platforms
- **[TESTING.md](docs/TESTING.md)** - Testing strategies, running tests, and debugging

## Quick Start

1. Clone and enter the repository:
   ```bash
   git clone https://github.com/IshuSinghSE/aurynk.git
   cd aurynk
   ```
2. Create a development branch for your change:
   ```bash
   git checkout -b feature/my-improvement
   ```
3. Prepare a virtual environment (recommended) and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
   ```
# Contributing to Aurynk (short)

Thanks for helping improve Aurynk. This file is a short guide — full build and testing instructions live in `docs/BUILDING.md` and `docs/TESTING.md`.

## Quick start

- Clone the repo and create a branch:

  ```bash
  git clone https://github.com/IshuSinghSE/aurynk.git
  cd aurynk
  git checkout -b feature/my-change
  ```

- Dev install and run:

  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install -e ".[dev]"
  python -m aurynk
  ```

## What to change here

- Small bug fixes, tests, docs, or UI tweaks: open a branch from `main` and target `main` with your PR.
- For urgent fixes to a release branch, merge into `main` first, then open a backport branch from the release (see below).

## Backporting

- Workflow we recommend:
  1. Merge the fix to `main` and ensure CI passes.
  2. Create a backport branch from the target release branch, cherry-pick the commit(s), and open a PR.

Example:

```bash
git fetch origin
git checkout -b backport/myfix origin/release/v1.2.2
git cherry-pick <commit>
git push origin backport/myfix
# Open PR: backport/myfix -> release/v1.2.2
```

## Tests & checks

- Run tests locally: `pytest` (see `docs/TESTING.md` for details).
- Lint & format: `ruff check .` and `ruff format .`
- Keep commits small and include a test when fixing bugs where practical.

## PR guidance

- Title: short, use conventional prefix (e.g. `fix(tray): …`).
- Body: What, why, how, and test steps. Link any related issues.
- Add screenshots for UI changes and mark any manual verification steps.

## Contact

- Report issues: https://github.com/IshuSinghSE/aurynk/issues
- Discuss: https://github.com/IshuSinghSE/aurynk/discussions

Thanks — contributions are appreciated! If you want, I can open a minimal backport PR draft for you.