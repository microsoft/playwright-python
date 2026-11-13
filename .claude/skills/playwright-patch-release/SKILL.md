---
name: playwright-patch-release
description: Prepare a patch release of Playwright Python (v1.xx.1 and later) from a release branch. Picks the next version, writes the release notes as the list of fixes in microsoft/playwright between the driver of the previous release of the branch and the driver of its tip, and saves them as a draft GitHub release, in place of an old draft. Never publishes the release.
---

# Preparing a patch release of Playwright Python

In this skill, `release-1.xx` is the release branch (for example `release-1.65`),
`v1.xx.p` is the previous release of the branch, and `v1.xx.n` is the patch release
that you prepare. For the first release of a branch, `v1.xx.0`, use the
`playwright-release` skill: its notes are the full release notes.

A patch release has no release commit. The fixes are on the branch already: a roll
moved its driver to a newer commit of `release-1.xx` of `microsoft/playwright`. The
version of the package comes from the tag, and GitHub makes the tag when a maintainer
publishes the draft. So the result of this skill is only the draft release.

Remotes: find the remote for `microsoft/playwright-python` with `git remote -v`. The
commands below call it `upstream`. In a clone of `microsoft/playwright-python`, it
is `origin`.

Never publish the release: see step 5.

## 1. The version

Fetch the branch and the tags. The previous release is the highest `v1.xx.*` tag:

```sh
git fetch upstream release-1.xx --tags
git tag --list 'v1.xx.*' --sort=-v:refname | head -1      # v1.xx.p
git merge-base --is-ancestor v1.xx.p FETCH_HEAD && echo "on release-1.xx"
git log --first-parent --format='%h %s' v1.xx.p..FETCH_HEAD   # the commits of this repository
```

- The next version is `v1.xx.n`, with `n = p + 1`. A draft release has no tag, so an
  old draft of `v1.xx.n` does not change the result.
- No `v1.xx.*` tag: `v1.xx.0` is not released. Stop and say so.
- The tag is not on the branch: stop and say so.
- The log is empty: there is nothing to release. Stop and say so.

## 2. The changes

The changes of the release are the commits of `microsoft/playwright` between the two
drivers: the driver of `v1.xx.p` and the driver of the tip of the branch.
`DRIVER_VERSION` names the commit of each one:

```sh
git show v1.xx.p:DRIVER_VERSION      # A, the driver of the previous release
git show FETCH_HEAD:DRIVER_VERSION   # B, the driver of this release
```

For a release up to 1.64, `DRIVER_VERSION` is a version of `playwright-core`, not a
commit. Its commit is the tag `v<version>` of `microsoft/playwright`.

Move `.upstream/` to B and list the commits between A and B. Both are on
`release-1.xx` of `microsoft/playwright`:

```sh
git checkout --detach FETCH_HEAD && python scripts/upstream.py checkout
git -C .upstream merge-base --is-ancestor <A> <B> && echo "A is before B"
git -C .upstream log --reverse --format='%h %s' <A>..<B>
```

A commit of an upstream release branch has the title `cherry-pick(#<pr>): <title>`,
where `#<pr>` is the pull request on `main` of `microsoft/playwright`. For each
commit, read the pull request and the issue that it fixes:

```sh
gh pr view <pr> --repo microsoft/playwright --json title,body,closingIssuesReferences
```

The patch releases of `microsoft/playwright` between A and B name the same issues
(`gh release view v1.xx.y --repo microsoft/playwright`). Use them as a check, not as
the source: the list comes from the commits.

Keep a fix only when it changes something for a user of Playwright Python: the
browsers, the driver, the protocol, the API. Leave out the fixes of the test runner,
of the Node.js tools and of the other languages, and the commits that a user cannot
see: version bumps, CI, tests, docs of other languages.

When A and B are the same commit, the release has no upstream changes. Then the
commits of step 1 are the only changes: list those that a user can see, such as a new
bundled Node.js or a change of the Docker images.

## 3. The notes

Write the notes to a file, in GitHub markdown, in this shape. It is the shape of the
earlier patch releases, for example
[v1.65.1](https://github.com/microsoft/playwright-python/releases/tag/v1.65.1):

```markdown
### Highlights

https://github.com/microsoft/playwright/issues/<n> - <title of the issue>
https://github.com/microsoft/playwright/pull/<n> - <title of the pull request>

<One short paragraph for each change that needs an explanation.>

## Browser Versions

- Chromium <new version>
```

- One line for each fix, and nothing more: no new APIs, no code samples, no
  sections of the full release notes. A patch release has only fixes.
- Link the issue that the fix closes, with the title of the issue as it is. The
  issue can be in `microsoft/playwright` or in `microsoft/playwright-python`. When
  there is no issue, link the pull request on `main`, not the cherry-pick, with its
  title without `cherry-pick(#<pr>):`.
- Order the lines by how much they matter to a user: regressions first.
- Add a paragraph only when the title does not tell a user what changed, for
  example why a new Node.js matters. Write what the user gets, in one or two
  sentences.
- No title line, no version, no date: GitHub shows them.

Browser Versions: list only the browsers whose version changed since `v1.xx.p`,
each with its new version. Compare the table in `README.md` at the two commits. A
roll generates the table from the driver.

```sh
git show v1.xx.p:README.md | grep 'GEN:.*-version'
git show FETCH_HEAD:README.md | grep 'GEN:.*-version'
```

The names are `Chromium`, `Mozilla Firefox` and `WebKit`. When no version changed,
leave out the `## Browser Versions` section.

## 4. Check the notes

- Each line of the list has a commit between A and B in step 2. Each of those
  commits that changes something for a user of Playwright Python has a line.
- Each link opens, and its title is the title of that issue or pull request.
- The notes name a browser only when its version changed since `v1.xx.p`, with the
  version of `README.md` at the tip of the branch.

## 5. The draft release

Save the notes as a draft release with the tag `v1.xx.n`, the title `v1.xx.n` and
the target `release-1.xx`. A draft of `v1.xx.n` from an earlier run has old notes:
the new draft replaces it. Never delete or change a published release.

**As the Playwright bot**, on CI. You have no token and no `gh`: you cannot save the
release yourself. Leave one `release` call in `calls.json`, and the Post step of the
bot saves the draft:

```json
{ "call": "release", "repo": "microsoft/playwright-python", "tag": "v1.xx.n", "target": "release-1.xx", "bodyFile": "release-notes.md" }
```

The call deletes the old draft of `v1.xx.n` and saves the new one. It fails when the
tag exists or when the release is published. The notes have no footer.

**As a person at a computer**, with `gh` logged in. First check that the old release
is a draft:

```sh
gh release view v1.xx.n --repo microsoft/playwright-python --json isDraft --jq .isDraft
gh release delete v1.xx.n --repo microsoft/playwright-python --yes    # only when the line above prints true
gh release create v1.xx.n --repo microsoft/playwright-python --draft \
  --target release-1.xx --title v1.xx.n --notes-file <notes-file>
gh release list --repo microsoft/playwright-python --limit 3          # v1.xx.n shows as Draft
```

Give the user the URL of the draft, the previous release, and the list of the
changes that you left out with the reason for each. Your work ends here. Do not
publish the release: never run `gh release create` without `--draft`, and never run
`gh release edit --draft=false`. Publishing creates the tag and starts
`.github/workflows/publish.yml`, which builds the wheels and uploads them to PyPI
after a reviewer approves the `pypi` environment. Never run that workflow, and never
approve the environment.
