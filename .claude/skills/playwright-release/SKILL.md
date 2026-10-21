---
name: playwright-release
description: Prepare a Playwright Python release. Checks open bugs, adds Python-specific changes to the Python release notes in microsoft/playwright, opens the release PR, cuts the release branch, and saves a draft GitHub release. Never publishes the release.
---

# Preparing a Playwright Python release

In this skill, `1.xx` is the release (for example `1.64`), and `v1.xx.0` is its tag.
`.upstream/` is the checkout of `microsoft/playwright` at the commit in
`DRIVER_VERSION` (`python scripts/upstream.py checkout`). Only read from it: do not
commit or switch branches there.

Remotes: find the remote for `microsoft/playwright-python` with `git remote -v`.
The commands below call it `upstream`.

What you may push:
- The user's request to prepare the release is the instruction to open the PRs
  in steps 2 and 3. Step 2 has a PR only when it adds Python changes.
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

Check that the driver is rolled. `DRIVER_VERSION` must be a commit of
`release-1.xx`: the tag `v1.xx.y`, or the tip of the branch, as the user says. The
driver reports the version of `playwright-core` at that commit, so it must be
`1.xx.y`:

```sh
python scripts/upstream.py checkout
git -C .upstream fetch origin release-1.xx
git -C .upstream merge-base --is-ancestor "$(cat DRIVER_VERSION)" FETCH_HEAD && echo "on release-1.xx"
git -C .upstream show "$(cat DRIVER_VERSION)":packages/playwright-core/package.json | grep '"version"'
```

If it is not, roll with the `playwright-roll` skill (`python scripts/upstream.py pin v1.xx.y`,
or `pin release-1.xx`). This is often already done. The roll commit goes into the
release commit PR (step 3). When the API roll for 1.xx is already on `main`, that PR
only moves `DRIVER_VERSION`.

## 2. Release notes (microsoft/playwright)

The Python notes in `docs/src/release-notes-python.md` are written in
`microsoft/playwright` together with the Node.js notes. The
`playwright-release-notes` skill there
(`.claude/skills/playwright-release-notes/SKILL.md` on `main`) covers that,
including the Python code style. Check that the `## Version 1.xx` section is on the
release branch:

```sh
git -C .upstream fetch origin release-1.xx
git -C .upstream show FETCH_HEAD:docs/src/release-notes-python.md | grep -n '^## Version 1.xx$'
```

If it is missing, tell the user: it should have landed with the Node.js notes.

Then lean towards Python. List the playwright-python commits since the previous
release branch:

```sh
gh api repos/microsoft/playwright-python/compare/release-1.<xx-1>...main \
  --jq '.commits[].commit.message | split("\n")[0]'
```

Pick only significant changes that only the Python port has, for example a
different exception type. Leave out minor bug fixes, internal changes, and anything
the notes already cover. If nothing is significant, go to step 3. Otherwise list
the changes for the user and ask whether to add them to the notes.

To add them, write them in a worktree of `.upstream/` next to this repository, on a
branch from `origin/main`. `.upstream/` itself stays at the pin.

```sh
notes="$(dirname "$PWD")/playwright-release-notes-1.xx"
git -C .upstream fetch origin main
git -C .upstream worktree add -b release-notes-1.xx-python "$notes" origin/main
```

Commit, push to the user's fork of `microsoft/playwright`, and open the PR. If
the checkout has no remote for the fork, add one. `gh api user --jq .login`
gives the user's login.

```sh
git -C "$notes" commit -am "docs: release notes for v1.xx Python"
git -C "$notes" push <fork-remote> release-notes-1.xx-python
gh pr create --repo microsoft/playwright --head <login>:release-notes-1.xx-python \
  --title "docs: release notes for v1.xx Python" \
  --body "- Update the \`Version 1.xx\` Python release notes with upstream and Python-specific changes"
```

After the PR merges, it needs a cherry-pick to `release-1.xx` (the
`playwright-cherry-pick` skill in `microsoft/playwright`).

Then remove the worktree:

```sh
git -C .upstream worktree remove "$notes"
```

## 3. Release commit (playwright-python)

Open a PR from the branch with the roll commit:

- Title: `chore: roll Playwright to v1.xx.y`, where `v1.xx.y` is the Python
  release version, even when `DRIVER_VERSION` is the tip of `release-1.xx` and not
  a tag.
- Description: the Python release notes, in GitHub markdown (see below).
  The user copies this description into the GitHub release, so for this PR it
  replaces the "keep PR descriptions short" rule in `AGENTS.md`.

Convert the `## Version 1.xx` section of `release-notes-python.md` on
`release-1.xx` to GitHub markdown with Python link text. Follow step 3 of the
`playwright-release-notes` skill in `microsoft/playwright`, including its link
check and the Python scan.

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
