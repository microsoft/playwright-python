---
name: playwright-triage
description: Triage and fix an issue in microsoft/playwright-python. How to use the upstream checkout, how to run a published version, how to tell a bug of the Python client from an upstream one, the upstream bug report, and what not to run from a PR of a third party.
---

# Playwright Python Issue Triage

## Upstream

`.upstream/` is the clone of `microsoft/playwright` at the commit in `DRIVER_VERSION`, as
[AGENTS.md](../../../AGENTS.md) says. The driver is built from it. Read upstream code there. Do not
edit, commit or switch branches in it: the wheel build and `./scripts/lint.sh` stop when it is not
at that commit or has local changes. Before you run upstream tests in it, it needs `npm ci`,
`npm run build` and `npx playwright install`. The wheel build (`scripts/build_driver.py`) runs the
first two there; run them again when `node_modules/` is missing.

## Published versions

To run a published version, for example to bisect, create an empty directory outside the repo for
each version, and run there:

```bash
python -m venv env && source env/bin/activate   # env\Scripts\activate on Windows
pip install playwright==<version>
python -m playwright install
```

The fixtures of the repo are not available there. Write the condensed repro as a plain script with
`sync_playwright()` or `async_playwright()` in that directory, with `page.set_content()` in place of
the test server, and run it from there. In this repo, the source tree shadows the installed
package.

The driver of a release is in `DRIVER_VERSION` at its tag: `git show v<version>:DRIVER_VERSION`
prints the upstream commit it was built from, or, for releases up to 1.64, the `playwright-core`
version of the driver; `npm view playwright-core@<core version> gitHead` prints its commit. Match a
regression in the driver to commits with `git -C .upstream log <good>..<bad> -- <path>`.

## Upstream bugs

The client talks to the Node driver that is built from `.upstream/`, and `microsoft/playwright`
and this repo are one team. Reproduce the bug in Python first. Then write the same calls as an
upstream test and run it in `.upstream/`. The triage skill of `microsoft/playwright`, in
`.upstream/.claude/skills/playwright-triage/`, says where such a test goes, which fixtures it uses
and how to run it. Use only those parts of it. Put the test in a new spec file, and delete the file
when you are done, so that the checkout is clean.

- The Node test passes: the bug is in the Python client. Fix it here.
- The Node test fails too: the root cause is upstream, and the fix lands in `microsoft/playwright`.
  Do not work around it in `playwright/_impl/`. Run `git -C .upstream fetch origin main`. When
  `git -C .upstream log HEAD..origin/main -- <path>` shows a fix that already landed, it reaches
  this repo with the next roll: say so. Otherwise write the report.
- The Python API lacks a member or an option: the generated API has everything that the upstream
  docs in `.upstream/docs/src/api` give Python (`* langs:` decides; no `langs` means every
  language). The gap is in the docs, so it is an upstream change too. Do not edit a generated file,
  and do not add to `scripts/codegen/python_rules.js` to go around the docs.

The report is for an engineer of `microsoft/playwright` who did not read the Python issue: what
fails, expected versus actual, the versions (the Python package, the commit in `DRIVER_VERSION`, the
browser, the platform), the root cause when you found it, and the condensed Node test as the repro.
The title has at most 256 characters, for example `route.fulfill() drops the charset of
Content-Type`. A maintainer files it in `microsoft/playwright`. Give it in this form:

`````markdown
Upstream bug report, for a maintainer to file in microsoft/playwright:

**Title:** <title>

<details>
<summary>Body</summary>

````markdown
<the report>
````

</details>
`````

With it, give the verdict, the evidence, and that the bug is upstream.

## PRs from third parties

Do not run a PR that changes `setup.py`, `pyproject.toml`, `setup.cfg`, `local-requirements.txt`,
`requirements.txt`, `DRIVER_VERSION`, `NODE_VERSION`, `.pre-commit-config.yaml`, `test.sh`,
`scripts/`, `utils/`, `.github/`, `.azure-pipelines/`, `.claude/`, or a generated file. A PR that
changes a ported test under `tests/{async,sync}/{page,library}`, or adds a mark to one, has faults:
the ports have zero deviations.
