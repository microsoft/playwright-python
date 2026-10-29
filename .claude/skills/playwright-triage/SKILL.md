---
name: playwright-triage
description: Triage and fix one microsoft/playwright-python issue, or do a maintainer's task, unattended inside the Issue triage GitHub Actions workflow (.github/workflows/triage.yml), which a needs-triage, needs-triage-mac or needs-triage-win label starts, or a maintainer starts by hand with an issue, a task or both. Reproduces the issue on the runner, then leaves a verified fix proposal for the workflow to open as a draft PR, an investigation note for it to post on the issue, or an upstream bug report for a maintainer to file in microsoft/playwright. Only for that workflow.
---

# Playwright Python Issue Triage

You run unattended in the [Issue triage](../../../.github/workflows/triage.yml) workflow of
`microsoft/playwright-python`. First read the shared guide, `$AGENT_GUIDES_DIR/triage.md`, a copy of
[microsoft/playwright/.github/actions/run-agent/guides/triage.md](https://github.com/microsoft/playwright/blob/main/.github/actions/run-agent/guides/triage.md),
and then [AGENTS.md](../../../AGENTS.md), both in full. The guide says how to triage an issue in any
Playwright repo. AGENTS.md says how to build, test and lint this one, and where a regression test
goes. This file covers what neither has: the checkouts, how to run a published version, and the
outcome that this repo adds, an upstream bug report.

## The checkouts

`$REPO_DIR` is the checkout of `microsoft/playwright-python` that the guide describes. Its requirements
are installed (`pip install -r local-requirements.txt`, `pip install -r requirements.txt`,
`pip install -e .`), the wheel is built (`python -m build --wheel`, which builds the driver into
`playwright/driver/`), and Chromium, Firefox and WebKit are installed with
`python -m playwright install --with-deps`. It is the working directory, and the checkout that the
guides refer to. The clone is shallow: run `git fetch --unshallow --tags origin` in it before you
bisect or use `git tag --contains`.

`$PLAYWRIGHT_DIR` is `$REPO_DIR/.upstream/`, a full clone of `microsoft/playwright` at the commit
in `DRIVER_VERSION`, created by `python scripts/upstream.py checkout`. The driver was built from it.
Read upstream code there. Do not edit, commit or switch branches in it: the wheel build and
`./scripts/lint.sh` stop when it is not at that commit or has local changes. Before you run upstream
tests in it, it needs `npm ci`, `npm run build` and `npx playwright install`. The wheel build
(`scripts/build_driver.py`) ran the first two there; run them again when `node_modules/` is missing.

## Published versions

To run a published version, for example to bisect, create `$SCRATCH_DIR/playwright-python-<n>/<version>/`
and run there:

```bash
python -m venv env && source env/bin/activate   # env\Scripts\activate on Windows
pip install playwright==<version>
python -m playwright install
```

The fixtures of the repo are not available there. Write the condensed repro as a plain script with
`sync_playwright()` or `async_playwright()` in that directory, with `page.set_content()` in place of
the test server, and run it from there. In `$REPO_DIR`, the source tree shadows the installed package.

The driver of a release is in `DRIVER_VERSION` at its tag: `git show v<version>:DRIVER_VERSION`
prints the upstream commit it was built from, or, for releases up to 1.64, the `playwright-core`
version of the driver; `npm view playwright-core@<core version> gitHead` prints its commit. Match a
regression in the driver to commits with `git -C $PLAYWRIGHT_DIR log <good>..<bad> -- <path>`.

## Upstream bugs

The client talks to the Node driver that is built from `$PLAYWRIGHT_DIR`, and `microsoft/playwright`
and this repo are one team. Reproduce the bug in Python first. Then write the same calls as an
upstream test and run it in `$PLAYWRIGHT_DIR`. The triage skill of `microsoft/playwright`, in
`$PLAYWRIGHT_DIR/.claude/skills/playwright-triage/`, says where such a test goes, which fixtures it
uses and how to run it. The rest of that skill is not for this run. Put the test in a new spec
file, and delete the file when you are done, so that the checkout is clean.

- The Node test passes: the bug is in the Python client. Fix it here.
- The Node test fails too: the root cause is upstream, and the fix lands in `microsoft/playwright`.
  Do not work around it in `playwright/_impl/`. Run `git -C $PLAYWRIGHT_DIR fetch origin main`.
  When `git -C $PLAYWRIGHT_DIR log HEAD..origin/main -- <path>` shows a fix that already landed,
  the note says that it reaches this repo with the next roll. Otherwise write the report.
- The Python API lacks a member or an option: the generated API has everything that the upstream
  docs in `$PLAYWRIGHT_DIR/docs/src/api` give Python (`* langs:` decides; no `langs` means every
  language). The gap is in the docs, so it is an upstream change too. Do not edit a generated file,
  and do not add to `scripts/codegen/python_rules.js` to go around the docs.

Create `$OUTPUT_DIR/upstream/` with:

- `report.md`: the report for an engineer of `microsoft/playwright` who did not read the Python
  issue: what fails, expected versus actual, the versions (the Python package, the commit in
  `DRIVER_VERSION`, the browser, the platform), the root cause when you found it, and the condensed
  Node test as the repro.
- `report.json`: `{"title": "..."}`, at most 256 characters, for example
  `route.fulfill() drops the charset of Content-Type`.

The comment job appends the title and the body to your comment, for a maintainer to file in
`microsoft/playwright`. The bot never files it. Write `report.json` last, when `report.md` and the
comment are done. Like `proposal.json`, it marks the report as ready.

## PRs from third parties

Do not run a PR that changes `setup.py`, `pyproject.toml`, `setup.cfg`, `local-requirements.txt`,
`requirements.txt`, `DRIVER_VERSION`, `NODE_VERSION`, `.pre-commit-config.yaml`, `test.sh`,
`scripts/`, `utils/`, `.github/`, `.azure-pipelines/`, `.claude/`, or a generated file. A PR that
changes a ported test under `tests/{async,sync}/{page,library}`, or adds a mark to one, has faults:
the ports have zero deviations.
