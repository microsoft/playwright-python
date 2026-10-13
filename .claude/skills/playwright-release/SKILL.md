---
name: playwright-release
description: Prepare a Playwright Python release. Checks open bugs, writes the Python release notes in microsoft/playwright, opens the release PR, cuts the release branch, and saves a draft GitHub release. Never publishes the release.
---

# Preparing a Playwright Python release

In this skill, `1.xx` is the release (for example `1.64`), and `v1.xx.0` is its tag.
`$PW_SRC_DIR` is the roll checkout of `microsoft/playwright` (see the
`playwright-roll` skill, step 2).

Remotes: find the remote for `microsoft/playwright-python` with `git remote -v`.
The commands below call it `upstream`.

What you may push:
- The user's request to prepare the release is the instruction to open the two PRs
  in steps 2 and 3.
- Cut the release branch (step 4) only when the user tells you to.
- Never publish the release.

## 1. Preconditions

Check that the bugs are closed. The bug and regression issue templates give
these title prefixes:

```sh
gh issue list --repo microsoft/playwright-python --state open \
  --search 'in:title "[Bug]" OR in:title "[Regression]"'
```

If any are open, list them for the user and ask whether to continue. Do not
close or comment on issues.

Check that the driver is rolled. `DRIVER_VERSION` must be the driver for the
release: a `1.xx.y` build, or a `1.xx.0-beta-…` build from `release-1.xx`, as the
user says. If it is not, roll with the `playwright-roll` skill. This is often
already done. The roll commit goes into the release commit PR (step 3). When the
API roll for 1.xx is already on `main`, that PR only moves `DRIVER_VERSION`.

## 2. Release notes (microsoft/playwright)

Write the notes in the roll checkout, on a branch from `origin/main`:

```sh
git -C "$PW_SRC_DIR" fetch origin main
git -C "$PW_SRC_DIR" checkout -b release-notes-1.xx-python origin/main
```

In `docs/src/release-notes-python.md`, add a `## Version 1.xx` section above the
previous version. Translate it from the `## Version 1.xx` section of
`docs/src/release-notes-js.md`. Compare the `Version 1.63` sections of the two
files to see what a past translation dropped and changed.

- Keep the structure: highlights with emoji headings, `### New APIs` with
  `####` groups, `### Announcements`, `### Browser Versions`.
- Remove what Python does not have: the test runner (`@playwright/test`,
  `test.*`, config, fixtures, projects, reporters), UI mode, the HTML report,
  component testing, the VS Code extension, and `npx playwright test` options.
  Remove every API whose `langs` excludes Python. To check an API, look for it in
  `playwright/async_api/_generated.py`, or check `langs` in `api.json` (see
  "Verifying classifications" in the `playwright-roll` skill).
- Rewrite code samples in Python, with the sync API:
  `page.get_by_role("button").click()`. Use snake_case names and Python values
  (`True`, `None`).
- Keep API links as docs link macros: `` [`method: Page.frameLocator`] ``,
  `` [`option: Tracing.start.ariaSnapshots`] ``,
  `` [`event: Page.dialogClosed`] ``. The docs site shows them with Python names.
  In plain text, use Python names.
- Commands: write `playwright install`, not `npx playwright install`.
- Lean towards Python. List the playwright-python commits since the previous
  release branch:

  ```sh
  gh api repos/microsoft/playwright-python/compare/release-1.<xx-1>...main \
    --jq '.commits[].commit.message | split("\n")[0]'
  ```

  If some of them change what users see (for example, a different exception
  type), list them for the user and ask whether to add them to the notes.

Commit, push to the user's fork of `microsoft/playwright`, and open the PR. If
the checkout has no remote for the fork, add one. `gh api user --jq .login`
gives the user's login.

```sh
git -C "$PW_SRC_DIR" commit -am "docs: release notes for v1.xx Python"
git -C "$PW_SRC_DIR" push <fork-remote> release-notes-1.xx-python
gh pr create --repo microsoft/playwright --head <login>:release-notes-1.xx-python \
  --title "docs: release notes for v1.xx Python" \
  --body "- Add \`Version 1.xx\` to the Python release notes, translated from the Node.js notes"
```

Then put the roll checkout back on the release branch. `./scripts/update_api.sh`
reads the docs from it. Run the checkout checks from step 2 of the
`playwright-roll` skill.

```sh
git -C "$PW_SRC_DIR" checkout release-1.xx
```

## 3. Release commit (playwright-python)

Open a PR from the branch with the roll commit:

- Title: `chore: roll Playwright to v1.xx.y`, where `v1.xx.y` is the Python
  release version, even when `DRIVER_VERSION` is a beta build.
- Description: the release notes from step 2, in GitHub markdown (see below).
  The user copies this description into the GitHub release, so for this PR it
  replaces the "keep PR descriptions short" rule in `CLAUDE.md`.

Convert the notes to GitHub markdown yourself:

- Leave out the `## Version 1.xx` heading. Move every other heading up one level
  (`###` becomes `##`, `####` becomes `###`).
- Replace each link macro with a full playwright.dev link. Use the Python name as
  the link text:

  | Macro | GitHub markdown |
  |---|---|
  | `` [`method: Page.frameLocator`] `` | `[page.frame_locator()](https://playwright.dev/python/docs/api/class-page#page-frame-locator)` |
  | `` [`method: Locator.visible`] `` (a property in Python) | `[locator.visible](https://playwright.dev/python/docs/api/class-locator#locator-visible)` |
  | `` [`option: Browser.newContext.httpCredentials`] `` | ``[`http_credentials`](https://playwright.dev/python/docs/api/class-browser#browser-new-context-option-http-credentials)`` |
  | `` [`event: BrowserContext.dialogClosed`] `` | `[browser_context.on("dialogclosed")](https://playwright.dev/python/docs/api/class-browsercontext#browser-context-event-dialog-closed)` |

  The page is `class-` and the class name in lower case. The anchor is the class
  and member names in kebab-case. Options add `-option-<name>`, and events add
  `-event-<name>`. A member is a property in Python if `_generated.py` declares
  it with `@property`.

Wait for the user to review and merge the PR. Do not merge it yourself.

## 4. Release (only when the user tells you to)

Cut `release-1.xx` from `main` and push it to `upstream`:

```sh
git fetch upstream main
git show FETCH_HEAD:DRIVER_VERSION       # the release driver
git log -1 --oneline FETCH_HEAD          # the release commit from step 3
git ls-remote --exit-code upstream refs/heads/release-1.xx   # must fail: the branch must not exist yet
git push upstream FETCH_HEAD:refs/heads/release-1.xx
```

Save the release notes as a draft release that targets the branch. Take the
notes from the merged PR description, so that edits from the review are
included:

```sh
gh pr view <release-pr> --repo microsoft/playwright-python --json body --jq .body > <notes-file>
gh release create v1.xx.0 --repo microsoft/playwright-python --draft \
  --target release-1.xx --title v1.xx.0 --notes-file <notes-file>
gh release list --repo microsoft/playwright-python --limit 3   # v1.xx.0 shows as Draft
```

Give the user the URL of the draft. Your work ends here. Do not publish the
release: never run `gh release create` without `--draft`, and never run
`gh release edit --draft=false`. Publishing creates the tag and starts
`.github/workflows/publish.yml`, which builds the wheels and uploads them to PyPI
after a reviewer approves the `pypi` environment. Never run that workflow, and
never approve the environment.
