---
name: playwright-roll
description: Roll Playwright Python to a new driver version. Walks the upstream `docs/src/api/` commit range, regenerates the public API from the docs, ports each change into `_impl/`, records justified differences in `scripts/codegen/python_rules.js`, and adds tests.
---

# Rolling Playwright Python

The goal of a roll is to move the driver pin in `DRIVER_VERSION` to a new release, port every public API change introduced upstream during that interval, and suppress the rest, so that `./scripts/update_api.sh` and `mypy playwright` run clean and the test suite still passes.

The previous human-facing summary lives in `../../../ROLLING.md`. This skill is the operational playbook — read it end to end before starting.

## Mental model

The Python port is hand-written code in `playwright/_impl/`, plus a generator (`scripts/codegen/generate_api.js`) that:

1. parses the upstream docs (`$PW_SRC_DIR/docs/src/api`) with the upstream parser and filters them for Python,
2. applies the Python facts that the docs do not contain, from `scripts/codegen/python_rules.js`, and
3. emits the whole public API into `playwright/{async,sync}_api/_generated.py`: signatures, types, docstrings, event overloads, and the call into `_impl/` for every member.

The generator never reads `_impl/`. A new member or option in the docs therefore shows up in `_generated.py` right away, as a call into `_impl/` that does not exist yet. Each generated class types its `_impl_obj`, so **`mypy playwright` lists every such gap** as an error in `_generated.py`. Three resolutions:

- **PORT** — the new API is intended for Python (no `langs.only` filter, or `langs.only` includes `"python"`). Implement it in `_impl/` until mypy is clean.
- **MISMATCH** — the shipped Python API differs from the docs (a callback signature uses unions, a kwarg uses a legacy name, etc.). The shipped implementation wins. Add an entry to `scripts/codegen/python_rules.js` with a comment explaining *why*, and propose the upstream docs change that would make the entry unnecessary.
- **N/A** — the commit only touches docs, has `* langs: js` (or any other filter that excludes Python), is server-side, Electron-only, or was reverted later in the same release. No action; the generator already leaves it out.

The upstream documentation source of truth is `docs/src/api/*.md` in the playwright repo. Every `## method:` / `## property:` / `## event:` / `### option:` / `### param:` block has an optional `* langs: js` (or `js, python`, etc.) filter. The Python doclint resolves these into `langs` fields on each member of `api.json`. **An empty `langs: {}` means "all languages including Python" — *implement it*, don't suppress it.**

> **The mistake the 1.59 roll made twice over:** classifying things as "internal tooling, N/A for Python" based on the *name* of the API (Screencast, Debugger, pickLocator, clearConsoleMessages, artifactsDir, …). Almost all of those had empty `langs: {}` in `api.json` and were real Python APIs. Sounding tooling-y is not a `langs` filter. **The `langs` field on the member in `api.json` is the only authoritative signal.** When in doubt, dump it (see "Verifying classifications" below).

## Process

### 1. Set up the env

`CONTRIBUTING.md` covers this. Notes from past rolls:

- The repo requires Python 3.10+. If `python3.10` isn't available, use `python3` (3.12 is fine).
- If `python3-venv` is missing system-wide, use `uv venv env` instead, then `uv pip install --python env/bin/python --upgrade pip`. Don't try to `apt install` — sudo is denied in the harness.
- Always activate the venv before any `pip`, `pytest`, `mypy`, or `pre-commit` invocation.

### 2. Bump the driver pin, download it, and generate api.json

The docs walk and codegen read the upstream docs from a `microsoft/playwright`
checkout at `$PW_SRC_DIR`. **Use a separate checkout that exists only for
rolls, on the exact release branch you roll to**: `release-<new>`, the
`major.minor` of the new `DRIVER_VERSION` (the branch has the release's docs
plus any cherry-picks). Never point `PW_SRC_DIR` at a checkout that someone
works in: on `main` or a feature branch the docs differ, and the generator
silently emits that API instead of the release's.

```sh
export PW_SRC_DIR=../playwright-for-python      # the roll checkout, nothing else
# First roll on this machine: clone it (no npm install needed).
git clone https://github.com/microsoft/playwright.git "$PW_SRC_DIR"
# Every roll: move it to the release branch.
git -C "$PW_SRC_DIR" fetch origin
git -C "$PW_SRC_DIR" checkout release-<new>     # e.g. release-1.62
git -C "$PW_SRC_DIR" merge --ff-only origin/release-<new>
```

Check the checkout before you generate, and again before you commit:

```sh
git -C "$PW_SRC_DIR" rev-parse --abbrev-ref HEAD                  # must print release-<new>
git -C "$PW_SRC_DIR" status --porcelain                           # must print nothing
git -C "$PW_SRC_DIR" rev-parse HEAD origin/release-<new>          # both lines must be equal
```

Then bump the pins and assemble the driver:

```sh
# Edit DRIVER_VERSION (repo root): the playwright-core npm version for the new
# release, no "v" prefix, e.g.  1.62.0
python scripts/update_node_version.py     # refresh NODE_VERSION to the current LTS

source env/bin/activate
python -m build --wheel       # downloads playwright-core @ DRIVER_VERSION + Node.js, assembles the driver
playwright install chromium   # NOT --with-deps; sudo is denied

# The walk below inspects `langs` from api.json. Codegen does not need it.
node "$PW_SRC_DIR/utils/doclint/generateApiJson.js" > /tmp/api.json
```

The wheel build just downloads the `playwright-core` npm package at
`DRIVER_VERSION` and the matching Node.js binary (no source build, no Node/npm/git
toolchain), and unpacks the driver under `playwright/driver/`. The docs are the
one piece not shipped in the bundle — `./scripts/update_api.sh` reads them from
`$PW_SRC_DIR`. `/tmp/api.json` is only a convenient dump of the same docs for
the walk.

### 3. Identify the commit range

Use the roll checkout at `$PW_SRC_DIR` (from step 2).
Bring it up to date and ensure release branches/tags are present before walking
the range:

```sh
git -C "$PW_SRC_DIR" fetch --tags
git -C "$PW_SRC_DIR" fetch origin 'release-*:release-*'
```

There is sometimes no `vX.Y.0` tag for the latest release (the bots cut release branches first and tag later). Anchor on commits, not tags.

The diff range is "every commit on the new release branch since the previous release was cut". Anchor commits:

- **Previous release end**: the `chore: bump version to vX.Y.0-next` commit on `main`. That commit is the first commit *after* the previous release (X.Y-1) was cut. Use its parent (`<sha>~1`) as the lower bound.
  ```sh
  git -C "$PW_SRC_DIR" log --all --grep="bump version to v" --oneline | head
  ```
- **New release end**: the tip of `release-<new>` (or the matching tag if it exists).

Save the commit list, oldest first, scoped to `docs/src/api/`:

```sh
git -C "$PW_SRC_DIR" log <prev-anchor>~1..release-<new> --oneline --reverse -- docs/src/api > /tmp/roll-<new>-commits.md
```

A normal roll yields 50–100 commits. If you see 0 or thousands, the range is wrong.

Format the file as a markdown checklist and add the standard preamble (status legend, where to look up `api.json` etc.) — see the file from the 1.58→1.59 roll for the template.

### 4. Walk the commit list

For each commit, in chronological order:

```sh
git -C "$PW_SRC_DIR" show <sha> -- docs/src/api/
```

Look for:
- `## (async )?method:` / `## property:` / `## event:` additions or removals;
- `* langs: ...` lines on those blocks;
- `### param:` / `### option:` additions or removals;
- new `class-X.md` files (whole new classes — usually `langs: js`);
- type changes in `- returns:` lines.

Classify and act.

#### Verifying classifications (do this before suppressing anything)

Before tagging anything as MISMATCH or N/A based on appearance, dump the actual `langs` from `api.json`:

```python
import json
data = json.load(open("/tmp/api.json"))
classes = {c["name"]: c for c in data}
for cls_name in ["Page", "BrowserContext", "Screencast", "Debugger"]:
    cls = classes.get(cls_name)
    if not cls:
        continue
    print(f"\n{cls_name}: cls_langs={cls.get('langs', {})}")
    for m in cls["members"]:
        print(f"  {m['name']} kind={m.get('kind')} langs={m.get('langs', {})}")
```

For options/params nested inside an `Object`-typed arg, walk one level deeper:

```python
for a in member.get("args", []):
    if a["name"] == "options":
        for prop in a.get("type", {}).get("properties", []):
            print(prop["name"], prop.get("langs", {}))
```

A few rules of thumb that catch most "actually a PORT" cases:
- If the *containing class* has empty `langs: {}` and the *member* has empty `langs: {}`, it's for Python — implement it.
- If the member is empty but a single *option* has `langs: js`, the method is for Python and you only skip that option (e.g. `Screencast.start.size` is `langs: js` while `Screencast.start` itself isn't).
- If you're about to add three or more `Method not implemented:` entries for the same class, stop — you almost certainly need to implement the class.

#### PORT

Implement the change in `playwright/_impl/<module>.py`. Use the upstream JS implementation as a reference: `$PW_SRC_DIR/packages/playwright-core/src/client/<module>.ts`. Translate idioms:

| Upstream JS | Python |
|---|---|
| `async foo(): Promise<X>` | `async def foo(self) -> X:` |
| `foo(): X` (sync getter, no args, no body) | `@property def foo(self) -> X:` (the generator makes argument-less sync members properties — see `isPythonProperty` in `scripts/codegen/generate_api.js` — and reads `self._impl_obj.foo` without calling it. mypy does not catch a plain method here; the test does.) |
| `await this._channel.foo({ a, b })` | `await self._channel.send("foo", None, locals_to_params(locals()))` |
| `(await this._channel.foo()).value` | `await self._channel.send("foo", None)` (Python's `send()` auto-unwraps single-key responses; only call `send_return_as_dict` when the protocol returns multiple keys.) |
| `(await this._channel.foo()).artifact` (multi-key, may be empty) | `result = await self._channel.send_return_as_dict("foo", None); (result or {}).get("artifact")` — `send_return_as_dict` returns **`None`** (not `{}`) when the protocol response carries no fields. |
| `try { ... } catch (e) { if (isTargetClosedError(e)) return; throw e; }` | `try: ...; except Exception as e: if is_target_closed_error(e): return; raise` (import from `playwright._impl._errors`) |
| Inline `[Object]` return like `{endpoint: string}` | A `TypedDict` in `playwright/_impl/_api_structures.py`, which the generator writes. It names the struct from the docs: `` "Name" <[Object]> ``, or an `* alias-python:` line under it. See `RemoteAddr`, `BrowserBindResult`, `DebuggerPausedDetails`. |
| `binary` event/return field | The Python channel layer hands you a base64 string. Decode with `base64.b64decode(value)` before exposing as `bytes`. See `Screencast._dispatch_frame`. |

When implementing a new ChannelOwner subclass (one constructed by the protocol with `(parent, type, guid, initializer)`):
1. Register it in `playwright/_impl/_object_factory.py:create_remote_object` — otherwise the guid resolves to `DummyObject` and downstream code breaks mysteriously.
2. Add it to `playwright/_impl/_api_classes.py` (the import and `__all__`). The generator emits every Python class in the docs, and the generated API imports each implementation from that file. If the class is missing there, `_generated.py` fails to import.

When implementing a non-ChannelOwner wrapper class (a plain class that holds a Page/Context reference, like `Screencast`, `Clock`):
- Add it to `playwright/_impl/_api_classes.py`, as for a ChannelOwner subclass.
- Set `self._loop = parent._loop` and `self._dispatcher_fiber = parent._dispatcher_fiber` in `__init__`. The generated `AsyncBase`/`SyncBase` wrappers read these; missing them gives `AttributeError: 'X' object has no attribute '_loop'` at first use.

When the docs add a new struct (an inline `[Object]` with named fields):
- The generator writes its TypedDict into `_api_structures.py`. Never edit that file by hand; internal types go in `_internal_structures.py`.
- It needs a Python name in the docs: a name before the type (`` - `size` "ScreenSize" <[Object]> ``), or an `* alias-python:` line under the type. The generator fails with "No Python name for the struct at …" until one exists. Nested structs need names too.
- Re-export it from both `playwright/async_api/__init__.py` and `playwright/sync_api/__init__.py`: assignment line plus an entry in `__all__`. Same pattern as `ViewportSize`, `RemoteAddr`.

If the new API was previously recorded in `python_rules.js` (for example in `extraMembers`), **remove that entry** when implementing it. The generator fails on entries that no longer match anything, so stale entries cannot pile up.

If a doc rename involves a *positional* parameter (no default, before any `*`), users almost certainly call it positionally — you can rename freely. The 1.59 `BrowserType.connect.wsEndpoint` → `endpoint` is the canonical example. Don't suppress this kind of rename; just rename in `_impl/`. **Important corollary:** when docs rename a param, the wire-protocol field usually also changed in `packages/protocol/spec/*.yml` and the server-side dispatcher in `packages/playwright-core/src/server/dispatchers/*Dispatcher.ts`. If so, you must also update the channel-send dict key (e.g. `{"wsEndpoint": …}` → `{"endpoint": …}`). Keeping the old name in Python for a renamed param hides a wire-protocol bug.

#### MISMATCH

A MISMATCH is a divergence between the docs and the shipped Python surface. The shipped implementation wins. Use it sparingly — most apparent mismatches turn out to be PORTs you skipped. Fix a type, a name or a position in the upstream docs: declare the param or option for Python only, with `* langs: python`, and limit the shared declaration to the other languages. Example from `class-page.md`, where Python accepts a callback with one or two arguments:

```md
### param: Page.route.handler
* since: v1.8
* langs: python
- `handler` <[function]\([Route]\)|[function]\([Route], [Request]\)>
```

`scripts/codegen/python_rules.js` only holds what the docs cannot say, for example hidden internal kwargs (`extraOptions`: `Browser.new_context(default_browser_type=)`). Add an entry to the right table, with a one-line `//` comment above it explaining *why*. Keys use docs names (`Class.member.arg`, camelCase).

The generator fails with "the entry … no longer matches anything; remove it" when an upstream change makes an entry unnecessary. Delete that entry.

**Do not suppress** these — they're PORTs in disguise:

- "Internal tooling" classes/methods whose `langs` field is empty (`Screencast.*`, `Debugger.*`, `Page.pick_locator`, `BrowserContext.debugger`, `Browser.bind/unbind`, `Page.{clear,console}_*`). The 1.59 roll suppressed all of these initially, then had to walk every one back. Verify `langs` first.
- A renamed positional parameter (mypy: unexpected keyword argument `newName` for the impl method). Just rename in `_impl/` and update the channel-send dict key.
- A struct return the generator cannot name ("No Python name for the struct at …"). Name it, so that the generator writes a TypedDict — don't type it `Dict`.

#### N/A

Common N/A flavors:
- Whole new class with `langs: js` (Inspector/Screencast, Debugger, Overlay).
- Members with `langs: js` (most "tooling" / MCP / agentic features).
- Doc-only edits (typo fixes, "Improve `not` property sections", etc.).
- Reverts that cancel an earlier add in the same range (always check the rest of the range before porting something that gets reverted).
- Java/C# `langs:` blocks.
- Electron-only changes (`docs/src/api/class-electron.md`).

Tick the box in `/tmp/roll-<new>-commits.md` with one line: `[x] <sha> <subject> — <classification>: <one-liner>`.

### 5. Regenerate

```sh
./scripts/update_api.sh   # uses PW_SRC_DIR from step 2; run the checkout checks there first
```

The script, for `sync` and then `async`:
1. runs `node scripts/codegen/generate_api.js --flavor <flavor>` (reads the docs from `$PW_SRC_DIR`) straight into `playwright/<flavor>_api/_generated.py`,
2. invokes `pre-commit run --files` on the generated file.

Then run `mypy playwright` and work through the errors in `_generated.py` — each one is a call into `_impl/` that the implementation does not support yet.

To see exactly what a regeneration changed in the public API, compare against the committed file:

```sh
git show HEAD:playwright/async_api/_generated.py > /tmp/old.py
python scripts/codegen/compare_api.py /tmp/old.py playwright/async_api/_generated.py --show all
```

**CI no longer verifies that `_generated.py` is in sync** (the Lint job dropped the
"Verify generated API is up to date" step so it needn't check out upstream). So
regenerating here and committing the result is on you — don't skip it.

Failure modes and fixes:

| Symptom | Cause | Fix |
|---|---|---|
| mypy: `"XImpl" has no attribute "y"` in `_generated.py` | The docs have a new member `X.y`; `_impl/` does not. | PORT it. |
| mypy: `Unexpected keyword argument "z" for "y" of "XImpl"` | New parameter or option on an existing method. | Add the kwarg (docs camelCase name) in `_impl/`. If Python must not have it, fix the docs: `* langs:` on the option. |
| mypy: incompatible argument type in `_generated.py` | The docs type changed, or `_impl/` declares a narrower type. | Match the type in `_impl/`, or fix the docs with a Python-only declaration (`* langs: python`). |
| generator: `No Python name for the struct at X.y.z` | A new inline `[Object]` with no name in the docs. | Name it in the docs: `` "Name" <[Object]> ``. |
| generator: `The struct X has different fields at A and B` | Two places in the docs share one struct name, but their fields differ. | Give one place its own name in the docs. |
| `_generated.py` gains or loses members that the commit walk never mentioned | `PW_SRC_DIR` is not on `release-<new>` (for example on `main` or a feature branch), or is behind `origin/release-<new>`. | Run the checkout checks from step 2, fix the checkout, regenerate. |
| generator: `Unknown docs type "T" at X.y` | A docs type the type table in `generate_api.js` (`toPy`) does not know. | Add it to `toPy`. |
| generator: `required parameter z follows an optional one` | The docs order params so that Python would need a default before a non-default. | Fix the docs, for example with a Python-only `### param:` or `### option:`, as `select_option(value)` has. |
| generator: `the entry "…" no longer matches anything; remove it` | An upstream change made a rules entry unnecessary (or renamed what it points at). | Delete it, or re-key it to the new docs name. |
| `pyright … reportInconsistentOverload` (single-event class) | A class gained its first event, so there is one `Literal[…]` overload + impl, which pyright wants ≥2 of. | The generator already handles this — `emitEvents` adds a second `@typing.overload` with `event: str` when a class has exactly one event. |
| `pre-commit` keeps reformatting `_generated.py` on each run | First run after regen always reformats once; rerun until idle. | `pre-commit run --all-files` to settle. |
| A kwarg in `_impl/` that the docs don't mention (e.g. legacy name from a doc rename) | Nothing fails: the generator simply never passes it. | If the param is positional with no default, just rename it in `_impl/`. Check `packages/protocol/spec/*.yml` and the server dispatcher — if the wire field renamed too, also update the channel-send dict key. Only use `extraOptions` for genuinely hidden internal kwargs (`default_browser_type`). |
| `AttributeError: 'X' object has no attribute '_loop'` (or `_dispatcher_fiber`) at first use of a new wrapper class | The non-ChannelOwner wrapper isn't initializing the fields the generated `AsyncBase`/`SyncBase` reads. | In the wrapper's `__init__`, set `self._loop = parent._loop` and `self._dispatcher_fiber = parent._dispatcher_fiber`. |
| `'NoneType' object has no attribute 'get'` after `send_return_as_dict` | Method's protocol response carries no fields and `send_return_as_dict` returned `None`. | `(result or {}).get(...)`. |
| Frame/buffer payload arrives as a `str` instead of `bytes` | Protocol `binary` fields cross the wire as base64. | `base64.b64decode(value)` in the impl before exposing. |

After the script settles, run `pre-commit run --all-files` once more to confirm everything is idle.

### 6. Add tests

For each PORT, add one async test and a matching sync test. Conventions:

- Tests go in the existing topic file (`test_page_network_request.py`, `test_browsercontext.py`, `test_dialog.py`, …) — don't create new files unless there's no obvious home.
- Use `from playwright.async_api import …`, **not** `from playwright._impl._page import Page` (the impl class doesn't have the public wrappers like `expect_console_message`).
- For event-info objects, `await message_info.value` (it's an `async` property).
- Don't write tests that hang the page (e.g. `page.evaluate(... fetch slow ...)` followed by `page.close()` from a fixture) — the request task gets a `TargetClosedError`. Use `page.on("event", handler)` to capture state at event time instead.
- `playwright install chromium` (no `--with-deps`) is sufficient for the test suite under sandbox.

### 7. Update existing high-touch artifacts

- `DRIVER_VERSION` and `NODE_VERSION`: already done in step 2.
- `README.md`: gets the chromium/firefox/webkit version table updated automatically by `scripts/update_versions.py` (called from `update_api.sh`). Don't edit by hand.
- The "Backport changes" tracking issue on GitHub (filed by `microsoft-playwright-automation`) is the *intent* tracker, but it's frequently out of sync with what's actually been ported. Treat it as a starting point, not the source of truth — the `docs/src/api/` commit walk is authoritative.

### 8. Final verification

Repeat the checkout checks from step 2: the committed `_generated.py` must come from `release-<new>`.

```sh
pre-commit run --all-files
mypy playwright                 # 2 pre-existing errors in _json_pipe.py and _artifact.py are unrelated
pytest --browser chromium tests/async/<files-you-touched> tests/sync/<files-you-touched>
```

Then a smoke regression on a few neighboring suites (`tests/async/test_browser*.py`, `test_cdp_session.py`, `test_tracing.py`, `test_dialog.py`, `test_page_*.py`) to make sure nothing inherent to the port shifted.

## Reference: `python_rules.js` tables

All keys use docs names: `Class.member` or `Class.member.arg`, with the upstream PascalCase class and camelCase member/arg names. `*` matches one name segment.

| Table | Use |
|---|---|
| `handWrittenClasses` | Classes in the Python docs that are written by hand (`Error`, `TimeoutError`, `FormData`). |
| `contextManagerClasses`, `tracebackHideClasses` | Base-class and `__tracebackhide__` choices. |
| `extraMembers`, `extraOptions` | Python-only members and hidden options; generated without docstrings. |
| `positionalOptions` | Option names that are positional everywhere (`predicate`). |
| `structTotal` | `total=` of a TypedDict, where it differs from "total=False if any field is optional". |

## Tips & gotchas

- **`langs.only` is your filter — and the only filter.** Don't classify by name (`Screencast`, `Debugger`, `pickLocator`) or by intuition ("looks like internal tooling"). Always check `langs` in `api.json`. The 1.59 roll cost two extra audit passes by trusting names over `langs`.
- **Audit your own classifications a second time.** After the first walk through the commit range, before opening the PR, re-read every entry in `python_rules.js` you added during this roll and ask "is this divergence justified, or did I skip a port?" Run the `langs`-dump snippet on each suspicious entry. The 1.59 roll's first PR had ~20 wrong suppressions; the second pass cut them to 0.
- **A cluster of rules on the same class is a smell.** If you're about to add five entries for `Foo.*`, you're almost certainly looking at a class that needs to be implemented. Implement the whole thing once and the entries disappear.
- **Watch for revert pairs in the same range.** 1.59 added and reverted `Browser.isRemote` (#39613 / #39620) inside the same release. Walking chronologically lets you skip the add when you see the revert later.
- **Watch for rename-revert pairs.** 1.59 had `Locator.normalize` → `Locator.toCode` (#39648) → `Locator.normalize` (#39754). Final state wins; only port the last.
- **Doc renames almost always include a wire-protocol rename.** Whenever you see `### param: X.y.oldName` → `### param: X.y.newName` in a doc commit, also `git -C "$PW_SRC_DIR" show <sha> -- packages/protocol/spec/` and the corresponding `*Dispatcher.ts` file. If the wire field changed too, the channel-send dict key in `_impl/` must change. Suppressing the doc-side mismatch is hiding a real bug — the previous Python code is silently sending an unknown field that the new server ignores.
- **TypedDicts beat `Dict[str, X]` for any structured return.** When the docs describe a return as `[Object]` with named fields, name the struct for the generator, which writes its `TypedDict` into `_api_structures.py`, and re-export it from both public `__init__.py` files. Zero runtime cost (it's still a `dict`), and the docstrings expand its fields from the docs.
- **Positional renames are free.** A param with no default before any `*` separator is positional-or-keyword in Python, but realistic call sites pass it positionally. Renaming such a param doesn't break callers.
- **The "Backport changes" GitHub issue can be misleading.** In the 1.59 roll its checkboxes were all marked `[x]` with annotations like "✅ IMPLEMENTED", but several of those features had not actually been merged into the Python port. Trust the `docs/src/api/` walk over the issue.
- **The docs parser has quirks.** In a type expression, everything after a function's `:` is its return type, so `[function]([A]):[any]|[B]` is one function returning `any|B`. Put a function with a return type last in a union. And when a `### param:` header name differs from the backticked name on its type line, the header name is the docs name and the type-line name becomes the alias.
- **Don't edit `_generated.py` to fix lint or typing.** Fix `_impl/`, `scripts/codegen/generate_api.js`, or `python_rules.js` instead. Hand-editing the generated file is reverted on the next regen.
- **`/tmp/roll-<new>-commits.md` is a working artifact, not a deliverable.** Don't commit it. The commit message and PR description are where the audit summary belongs.
