---
name: playwright-roll
description: Roll Playwright Python to a new microsoft/playwright commit. Pins the commit, generates the API and builds the driver from it, and ports the upstream diff of the client and the tests.
---

# Rolling Playwright

Read `AGENTS.md` first. A roll moves `DRIVER_VERSION` to a new upstream commit and
ports everything that changed in between.

## 1. Pin

```sh
python scripts/upstream.py pin main      # or a branch, a tag, a commit
python scripts/update_node_version.py
old=$(git show HEAD:DRIVER_VERSION)
new=$(cat DRIVER_VERSION)
```

## 2. Generate

```sh
./scripts/update_api.sh
mypy playwright
```

The mypy errors are the to-do list: new members, options and protocol parameters that
`_impl/` does not have yet. Until they are ported, the client may not work with the new
driver. To see what changed in the public API:

```sh
git show HEAD:playwright/async_api/_generated.py > /tmp/old.py
python scripts/codegen/compare_api.py /tmp/old.py playwright/async_api/_generated.py --show all
```

## 3. Build

```sh
python -m build --wheel
playwright install chromium firefox webkit
```

## 4. Port

```sh
python scripts/upstream.py changes
```

It lists each changed upstream file with the Python file to port it to. For each one,
read `git -C .upstream diff $old $new -- <file>` and port it hunk by hunk:

- client code: into the module it names; `(no Python port yet)` is a new module;
- tests: into the async and the sync file it names. New test names come from
  `python scripts/check_test_registry.py --missing <id>`;
- test assets and snapshot images: copy them to the place it names;
- the "Generated" group: step 2 did it.

Changes in the server or in the injected scripts need nothing: they come with the new
driver. A test marked `xfail(reason="driver: ...")` may pass now; remove the mark then.

Run each changed test file on the three browsers. Then run `mypy playwright` until it
is clean.

## 5. Check

```sh
./test.sh
python scripts/update_versions.py        # the browser versions in README.md
./scripts/lint.sh                        # last: the roll is done when it passes
```

A failure in a file that the roll did not change may be a flake, or older than the
roll. Find out which, and say so in the PR.

Title the PR `chore: roll Playwright to <version> (<first 10 characters of $new>)`, with
the version from `.upstream/packages/playwright-core/package.json`. In the description,
list what you ported and what is left, and put the output of
`python scripts/upstream.py log` in a `<details>` block. The roll workflow adds that
list itself.

## When it breaks

- `missing ... argument`, or `Protocol violations` at the end of a test: a protocol change
  that the client does not follow yet. Port its hunk.
- `timeout: expected float, got undefined` at launch: `playwright/driver/` is older
  than the pin. Build again.
- `.upstream/ is not at ...`: `python scripts/upstream.py checkout`.
