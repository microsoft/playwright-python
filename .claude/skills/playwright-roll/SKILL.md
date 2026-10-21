---
name: playwright-roll
description: Roll Playwright Python to a new microsoft/playwright commit. Pins the commit in DRIVER_VERSION, builds the driver and generates the API from .upstream/, and ports the upstream diff of the client and the tests line by line.
---

# Rolling Playwright Python

`DRIVER_VERSION` holds one `microsoft/playwright` commit. `.upstream/` (gitignored) is
a full clone of `microsoft/playwright` at that commit. Everything comes from it:

- the driver: `python -m build --wheel` builds it from `.upstream/`;
- the generated files: `./scripts/update_api.sh` writes the API and the protocol files,
  and copies the test registry;
- the hand-written port: `playwright/_impl/` ports the client
  (`packages/playwright-core/src/client` and the parts of `packages/isomorphic`,
  `packages/protocol/src` and `packages/utils` that it uses), and `tests/async/`,
  `tests/sync/` port `tests/page/` and `tests/library/`.

A roll moves `DRIVER_VERSION` from the old commit to the new one, and ports the diff
between the two. Do not commit, branch or edit in `.upstream/`.

## 0. Set up

Follow steps 1 and 2 of `CONTRIBUTING.md`: the venv, the dependencies, and
`python scripts/upstream.py checkout`. Activate the venv before every `pip`, `pytest`
or `pre-commit`. In the agent harness, `sudo` is denied: if `python3-venv` is
missing, use `uv venv env`, and install browsers without `--with-deps`.

## 1. Pin

```sh
python scripts/upstream.py pin <ref>     # a branch (main, release-1.66), a tag (v1.66.0) or a commit
python scripts/update_node_version.py    # NODE_VERSION: the current Node.js LTS
old=$(git show HEAD:DRIVER_VERSION)
new=$(cat DRIVER_VERSION)
```

`pin` writes the commit to `DRIVER_VERSION` and checks it out in `.upstream/`. The
driver reports the version of `packages/playwright-core/package.json` at that commit:
`1.66.0` on a release tag, `1.67.0-next` on `main`.

## 2. Build

```sh
python -m build --wheel                  # the driver from .upstream/, and the wheel
playwright install chromium
```

## 3. Generate

```sh
./scripts/update_api.sh
mypy playwright
```

The API generator (`scripts/codegen/generate_api.js`) reads the docs in
`.upstream/docs/src/api`, keeps what is for Python, applies
`scripts/codegen/python_rules.js`, and writes every member with its call into
`_impl/`. It never reads `_impl/`. So a new member or option in the docs is a mypy
error in `_generated.py`, and a new parameter in the protocol spec is a mypy error at
the channel call in `_impl/`: each `ChannelOwner` subclass declares its channel type
(`_channel: "PageChannel"`), so mypy checks every call. Step 4 fixes them. Until then,
the client may fail to talk to the new driver.

To see what changed in the public API:

```sh
git show HEAD:playwright/async_api/_generated.py > /tmp/old.py
python scripts/codegen/compare_api.py /tmp/old.py playwright/async_api/_generated.py --show all
```

## 4. Port

```sh
python scripts/upstream.py changes
```

`changes` lists each upstream file that changed between `$old` and `$new`, in groups,
with the Python file to port it to. The files that upstream generates from the
protocol spec (`channels.d.ts`, `validator.ts`) are in the "Generated" group with the
docs and the spec: step 3 regenerated their Python counterparts. A spec file that
`tests/upstream_not_ported.txt` lists shows its reason instead of a Python file. For
each other file, read the diff and port each hunk, in order:

```sh
git -C .upstream diff "$old" "$new" -- <upstream file>
```

**Client.** Port each hunk line by line into the Python module, with the rules of
[`playwright/_impl/transform.md`](../../../playwright/_impl/transform.md). Change the
lines that the hunk changes, so that a reviewer can read the two diffs side by side.
Mark each difference from the JS with `# Python:`, and remove a mark whose reason is
gone.

- A new client file (`(no Python port yet)`): a new module, named in snake_case
  (`browserContext.ts` is `browser_context.py`), with the docstring
  `"""Port of <upstream path>.` and the members in the JS order. A new `ChannelOwner`
  goes in `_object_factories()` in `connection.py`. A new class of the public API goes
  in `_api_classes.py`. A plain wrapper class (like `Clock`) sets `self._loop` and
  `self._dispatcher_fiber` from its parent.
- A deleted or renamed file: delete or rename the module.
- Shared code that Python does not port: port it only when the client starts to use it.

**Tests.** Port each hunk line by line into the async test and the sync test that
`changes` names, with the rules of [`tests/transform.md`](../../../tests/transform.md):
zero deviations, and never change a port to make it pass.
`python scripts/check_test_registry.py --missing <code or file>` prints the name of a
new test. A test that can not exist in Python goes in `tests/upstream_not_ported.txt`,
with the reason. Run each ported file on the three browsers, the async and the sync
files in separate runs (a sync test can not run in a process where an async test has
run: `Runner.run() cannot be called from a running event loop`):

```sh
xvfb-run -a pytest tests/async/page/test_page_click.py --browser firefox
xvfb-run -a pytest tests/sync/page/test_page_click.py --browser firefox
```

A failure is a bug in the client, the driver or the environment, not in the test.

**Test assets.** Copy each changed file from `.upstream/tests/assets/` to
`tests/assets/`; delete the deleted ones. Only these files: a few files in
`tests/assets/` are Python only.

**Snapshot images.** Upstream keeps the image of `toMatchSnapshot()` next to the spec
(`page-screenshot.spec.ts-snapshots/<name>-<browser>.png`); the port keeps it in
`tests/golden-<browser>/<name>.png`. `changes` names the golden file of each changed
image: copy it there. The BiDi and the Firefox Nightly images are not used.

Then run `mypy playwright` until it is clean.

## 5. Check

```sh
pre-commit run --all-files
python scripts/check_test_registry.py
./test.sh
./scripts/update_api.sh && git status    # no new changes: the generated files come from .upstream/
playwright install chromium firefox webkit
python scripts/update_versions.py        # the browser versions in README.md
```

`./test.sh` runs every test, on many workers. For a failure in a file that the roll did
not change:

1. Run the test alone. A test that passes alone failed from the load of the full run.
2. Run it against the old driver. Its bundle stays in `driver/`
   (`playwright-<old>-<suffix>.zip`): extract it into `playwright/driver/`, keeping the
   file modes, run the test, then `python -m build --wheel` puts the new driver back.
   A test that fails with the old driver too is not a regression of the roll: list it
   in the PR.

Title the PR `chore: roll Playwright to <version> (<first 10 characters of $new>)`,
with the version from step 1. List what you ported and what you could not finish, and
put `git -C .upstream log --oneline --reverse "$old..$new"` of the changed paths in a
`<details>` block.

## Reference: the docs decide the public API

A new member or option comes from the docs into `_generated.py`; the client hunk
implements it.

- **For Python**: no `langs` filter, or `langs` includes `python`. Port it.
- **Not for Python**: `* langs: js` (or another filter without Python). The generator
  leaves it out. Mark the client member `# Not ported: <member> langs: js`.
- **Different in Python**: the shipped Python API wins. Fix the upstream docs with a
  Python-only declaration (`* langs: python`). Put in `python_rules.js` only what the
  docs can not say, with a one-line `//` comment above the entry that says why.

**`langs` is the only filter.** Do not decide by the name of an API: the 1.59 roll left
out Screencast, Debugger and `pickLocator` because they sounded like tooling, and they
were Python APIs. An empty `langs` means every language. To check it:

```sh
node .upstream/utils/doclint/generateApiJson.js > /tmp/api.json
python -c "import json; c = {x['name']: x for x in json.load(open('/tmp/api.json'))}['Page']; print([(m['name'], m.get('langs', {})) for m in c['members']])"
```

Other docs changes:

- A new inline `[Object]` needs a Python name in the docs (`` "Name" <[Object]> `` or
  `* alias-python:`). The generator writes its TypedDict into `_api_structures.py`;
  re-export it from `playwright/async_api/__init__.py` and `playwright/sync_api/__init__.py`.
- A renamed positional parameter: rename it in `_impl/`.
- A member now in the docs that `python_rules.js` lists: remove the entry. The
  generator fails on entries that match nothing.

`python_rules.js` tables (keys use docs names, `Class.member.arg`; `*` matches one segment):

| Table | Use |
|---|---|
| `handWrittenClasses` | Classes written by hand (`Error`, `TimeoutError`, `FormData`). |
| `contextManagerClasses`, `tracebackHideClasses` | Base-class and `__tracebackhide__` choices. |
| `extraMembers`, `extraOptions` | Python-only members and hidden options. |
| `positionalOptions` | Option names that are positional everywhere (`predicate`). |
| `structTotal` | `total=` of a TypedDict, where it differs from the default. |

## Reference: failure modes

| Symptom | Fix |
|---|---|
| `.upstream/ is not at <commit>` | `python scripts/upstream.py checkout`. |
| `.upstream has local changes` | `git -C .upstream status`; discard the changes. |
| mypy: `"XImpl" has no attribute "y"` in `_generated.py` | A new member in the docs: port the client hunk. |
| mypy: `Unexpected keyword argument "z"` for an impl method | A new option: port the client hunk (`Optional[X]`, no default, passed to the channel call), or fix the docs if Python must not have it. |
| mypy: `Missing named argument "z"` for a channel method | A new protocol parameter: port the client hunk that passes it. |
| generator: `No Python name for the struct at X.y.z` | Name the `[Object]` in the docs. |
| generator: `The struct X has different fields at A and B` | Give one place its own name in the docs. |
| generator: `Unknown docs type "T"` | Add it to `toPy` in `generate_api.js`. |
| generator: `required parameter z follows an optional one` | Fix the docs with a Python-only `### param:` or `### option:`. |
| generator: `the entry "…" no longer matches anything` | Delete or re-key the `python_rules.js` entry. |
| `AttributeError: … '_loop'` on a new wrapper class | Set `self._loop` and `self._dispatcher_fiber` in its `__init__`. |
| `Protocol violations: X.y: params.z: …` at test teardown | The client sends what the spec does not allow: port the hunk that renamed or removed it. |
| A `binary` field arrives as `str` | Decode it with `base64.b64decode()`. |
| `timeout: expected float, got undefined` at launch | `playwright/driver/` is older than the pin: `python -m build --wheel`. |
