---
name: playwright-roll
description: Roll Playwright Python to a new driver version. Walks the upstream `docs/src/api/` commit range, ports each public-API change, suppresses the rest in `expected_api_mismatch.txt`, regenerates the typed surface, and adds tests.
---

# Rolling Playwright Python

The goal of a roll is to move `driver_version` in `setup.py` to a new release, port every public API change introduced upstream during that interval, and suppress the rest, so that `./scripts/update_api.sh` runs clean and the test suite still passes.

The previous human-facing summary lives in `../../../ROLLING.md`. This skill is the operational playbook — read it end to end before starting.

## Mental model

The Python port is hand-written code in `playwright/_impl/`, plus a generator (`scripts/generate_*.py`, `scripts/documentation_provider.py`) that:

1. introspects the Python `_impl` classes via `inspect`,
2. emits typed wrapper classes into `playwright/{async,sync}_api/_generated.py`, and
3. diffs the introspected surface against `playwright/driver/package/api.json` (downloaded inside the new driver wheel).

Anything in `api.json` that is missing or differently typed in `_impl/` causes generation to fail. Three resolutions:

- **PORT** — the new API is intended for Python (no `langs.only` filter, or `langs.only` includes `"python"`). Implement it in `_impl/`.
- **MISMATCH** — the API genuinely exists for Python but is shaped differently (a callback signature uses unions, a kwarg uses a legacy name, etc.) and there's a justified reason to keep the divergence. Add a precise line to `scripts/expected_api_mismatch.txt` with a comment explaining *why*.
- **N/A** — the commit only touches docs, has `* langs: js` (or any other filter that excludes Python), is server-side, Electron-only, or was reverted later in the same release. No action.

The upstream documentation source of truth is `docs/src/api/*.md` in the playwright repo. Every `## method:` / `## property:` / `## event:` / `### option:` / `### param:` block has an optional `* langs: js` (or `js, python`, etc.) filter. The Python doclint resolves these into `langs` fields on each member of `api.json`. **An empty `langs: {}` means "all languages including Python" — *implement it*, don't suppress it.**

> **The mistake the 1.59 roll made twice over:** classifying things as "internal tooling, N/A for Python" based on the *name* of the API (Screencast, Debugger, pickLocator, clearConsoleMessages, artifactsDir, …). Almost all of those had empty `langs: {}` in `api.json` and were real Python APIs. Sounding tooling-y is not a `langs` filter. **The `langs` field on the member in `api.json` is the only authoritative signal.** When in doubt, dump it (see "Verifying classifications" below).

## Pre-flight

You will need two checkouts in the parent directory:
- `~/code/playwright-python` — this repo.
- `~/code/playwright` — the upstream playwright monorepo (used read-only for diffing).

Bring upstream up to date and ensure release branches/tags are present:

```sh
git -C ~/code/playwright fetch --tags
git -C ~/code/playwright fetch origin 'release-*:release-*'
```

There is sometimes no `vX.Y.0` tag for the latest release (the bots cut release branches first and tag later). Anchor on commits, not tags — see "Identify the commit range" below.

## Process

### 1. Set up the env

`CONTRIBUTING.md` covers this. Notes from past rolls:

- The repo says Python 3.9 is required, but 3.9+ works. If `python3.9` isn't available, use `python3` (3.12 is fine).
- If `python3-venv` is missing system-wide, use `uv venv env` instead, then `uv pip install --python env/bin/python --upgrade pip`. Don't try to `apt install` — sudo is denied in the harness.
- Always activate the venv before any `pip`, `pytest`, `mypy`, or `pre-commit` invocation.

### 2. Bump the driver and download it

```sh
# Edit setup.py
driver_version = "<new>"     # e.g. "1.59.1"

source env/bin/activate
python -m build --wheel       # downloads the new driver from cdn.playwright.dev
playwright install chromium   # NOT --with-deps; sudo is denied
```

The wheel build prints `Fetching https://cdn.playwright.dev/builds/driver/playwright-<new>-linux.zip` and unpacks the driver under `playwright/driver/package/`. From this point, `playwright/driver/package/api.json` reflects the new release.

### 3. Identify the commit range

The diff range is "every commit on the new release branch since the previous release was cut". Anchor commits:

- **Previous release end**: the `chore: bump version to vX.Y.0-next` commit on `main`. That commit is the first commit *after* the previous release (X.Y-1) was cut. Use its parent (`<sha>~1`) as the lower bound.
  ```sh
  git -C ~/code/playwright log --all --grep="bump version to v" --oneline | head
  ```
- **New release end**: the tip of `release-<new>` (or the matching tag if it exists).

Save the commit list, oldest first, scoped to `docs/src/api/`:

```sh
git -C ~/code/playwright log <prev-anchor>~1..release-<new> --oneline --reverse -- docs/src/api > /tmp/roll-<new>-commits.md
```

A normal roll yields 50–100 commits. If you see 0 or thousands, the range is wrong.

Format the file as a markdown checklist and add the standard preamble (status legend, where to look up `api.json` etc.) — see the file from the 1.58→1.59 roll for the template.

### 4. Walk the commit list

For each commit, in chronological order:

```sh
git -C ~/code/playwright show <sha> -- docs/src/api/
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
data = json.load(open("playwright/driver/package/api.json"))
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

Implement the change in `playwright/_impl/<module>.py`. Use the upstream JS implementation as a reference: `~/code/playwright/packages/playwright-core/src/client/<module>.ts`. Translate idioms:

| Upstream JS | Python |
|---|---|
| `async foo(): Promise<X>` | `async def foo(self) -> X:` |
| `foo(): X` (sync getter, no args, no body) | `@property def foo(self) -> X:` (the doc generator treats argument-less sync getters as properties — see `documentation_provider.py:133`. If you make it a method instead, you'll get a "Method vs property mismatch" error.) |
| `await this._channel.foo({ a, b })` | `await self._channel.send("foo", None, locals_to_params(locals()))` |
| `(await this._channel.foo()).value` | `await self._channel.send("foo", None)` (Python's `send()` auto-unwraps single-key responses; only call `send_return_as_dict` when the protocol returns multiple keys.) |
| `(await this._channel.foo()).artifact` (multi-key, may be empty) | `result = await self._channel.send_return_as_dict("foo", None); (result or {}).get("artifact")` — `send_return_as_dict` returns **`None`** (not `{}`) when the protocol response carries no fields. |
| `try { ... } catch (e) { if (isTargetClosedError(e)) return; throw e; }` | `try: ...; except Exception as e: if is_target_closed_error(e): return; raise` (import from `playwright._impl._errors`) |
| Inline `[Object]` return like `{endpoint: string}` | A `TypedDict` in `playwright/_impl/_api_structures.py` — *not* `Dict[str, str]`. The doc generator serializes TypedDicts as `{field: type, ...}` via `get_type_hints` and that matches the inline-object form exactly. See `RemoteAddr`, `BrowserBindResult`, `DebuggerPausedDetails`. |
| `binary` event/return field | The Python channel layer hands you a base64 string. Decode with `base64.b64decode(value)` before exposing as `bytes`. See `Screencast._dispatch_frame`. |

When implementing a new ChannelOwner subclass (one constructed by the protocol with `(parent, type, guid, initializer)`):
1. Register it in `playwright/_impl/_object_factory.py:create_remote_object` — otherwise the guid resolves to `DummyObject` and downstream code breaks mysteriously.
2. Import it and add it to `generated_types` in `scripts/generate_api.py`, plus add a `XxxImpl` import in the `header` string.

When implementing a non-ChannelOwner wrapper class (a plain class that holds a Page/Context reference, like `Screencast`, `Clock`):
- Set `self._loop = parent._loop` and `self._dispatcher_fiber = parent._dispatcher_fiber` in `__init__`. The generated `AsyncBase`/`SyncBase` wrappers read these; missing them gives `AttributeError: 'X' object has no attribute '_loop'` at first use.

When adding a new TypedDict in `_api_structures.py`:
- Add it to the `from playwright._impl._api_structures import …` line in `scripts/generate_api.py` so the generator can resolve it as a forward reference in type hints.
- Re-export it from both `playwright/async_api/__init__.py` and `playwright/sync_api/__init__.py`: assignment line plus an entry in `__all__`. Same pattern as `ViewportSize`, `RemoteAddr`.

If the new API was previously suppressed in `expected_api_mismatch.txt`, **remove that line** when implementing it.

If a doc rename involves a *positional* parameter (no default, before any `*`), users almost certainly call it positionally — you can rename freely. The 1.59 `BrowserType.connect.wsEndpoint` → `endpoint` is the canonical example. Don't suppress this kind of rename; just rename in `_impl/`. **Important corollary:** when docs rename a param, the wire-protocol field usually also changed in `packages/protocol/src/protocol.yml` and the server-side dispatcher in `packages/playwright-core/src/server/dispatchers/*Dispatcher.ts`. If so, you must also update the channel-send dict key (e.g. `{"wsEndpoint": …}` → `{"endpoint": …}`). A "Parameter not documented" suppression for a renamed param is a code smell hiding a wire-protocol bug.

#### MISMATCH

A MISMATCH is a *justified, durable* divergence between the docs and the Python surface. Use it sparingly — most apparent mismatches turn out to be PORTs you skipped. Legitimate examples in the current `expected_api_mismatch.txt`:

- Hidden internal kwargs (`Browser.new_context(default_browser_type=)`).
- Callback signatures where Python explicitly unions one-arg and two-arg variants but the docs document only the canonical form (`Page.route(handler=)`, `WebSocketRoute.on_close(handler=)`).

Add a precise line to `scripts/expected_api_mismatch.txt` with a `# comment` group header explaining *why* the divergence is intentional. The exact wording comes from the generator's error message. Examples:

```
# One vs two arguments in the callback, Python explicitly unions.
Parameter type mismatch in Page.route(handler=): documented as Callable[[Route, Request], Union[Any, Any]], code has Union[Callable[[Route, Request], Any], Callable[[Route], Any]]
```

The generator removes lines from `expected_api_mismatch.txt` that no longer match an error. If you see "No longer there: …" in the script's stderr, delete that line.

**Do not suppress** these — they're PORTs in disguise:

- "Internal tooling" classes/methods whose `langs` field is empty (`Screencast.*`, `Debugger.*`, `Page.pick_locator`, `BrowserContext.debugger`, `Browser.bind/unbind`, `Page.{clear,console}_*`). The 1.59 roll suppressed all of these initially, then had to walk every one back. Verify `langs` first.
- A renamed positional parameter (`Parameter not documented: X.y(old_name=)` + `Parameter not implemented: X.y(new_name=)`). Just rename in `_impl/` and update the channel-send dict key.
- A `Parameter type mismatch in X.y(return=): documented as {field: T}, code has Dict[str, T]`. Use a TypedDict.

#### N/A

Common N/A flavors:
- Whole new class with `langs: js` (Disposable, Inspector/Screencast, Debugger, Overlay).
- Members with `langs: js` (most "tooling" / MCP / agentic features).
- Doc-only edits (typo fixes, "Improve `not` property sections", etc.).
- Reverts that cancel an earlier add in the same range (always check the rest of the range before porting something that gets reverted).
- Java/C# `langs:` blocks.
- Electron-only changes (`docs/src/api/class-electron.md`).

Tick the box in `/tmp/roll-<new>-commits.md` with one line: `[x] <sha> <subject> — <classification>: <one-liner>`.

### 5. Regenerate

```sh
./scripts/update_api.sh
```

The script does, in order:
1. `git checkout HEAD -- playwright/{async,sync}_api/_generated.py` (resets to last committed),
2. runs `scripts/generate_{sync,async}_api.py` which dumps to `.x` then renames into place,
3. invokes `pre-commit run --files` on the generated files.

Failure modes and fixes:

| Symptom | Cause | Fix |
|---|---|---|
| `Method not implemented: X.y` | `api.json` documents `X.y`, no Python impl exists. | PORT it, or add a MISMATCH line. |
| `Parameter not implemented: X.y(z=)` | New parameter on existing method. | Add the kwarg in `_impl/`, or MISMATCH. |
| `Method vs property mismatch: X.y` | You implemented as a method but the doc treats it as a property (sync, no args, has return type). | Add `@property` in `_impl/`. |
| `Method not documented: X.y` | Python has it but `api.json` doesn't. | The upstream removed the API; remove from `_impl/` and from `_generated.py` callers. |
| `Parameter type mismatch in X.y(z=): documented as ..., code has ...` | Type signature doesn't line up. | Match the type in `_impl/`, or MISMATCH it for known historical divergences. |
| `pyright … reportInconsistentOverload` (single-event class) | A class gained its first event in `api.json`, so the generator emits one `Literal[…]` overload + impl, which pyright wants ≥2 of. | The generator already handles this — `documentation_provider.print_events` emits a second `@typing.overload` with `event: str` plus a generic impl. If you regress this, see how 1.59 handled `CDPSession` getting a `close` event. |
| `pre-commit` keeps reformatting `_generated.py` on each run | First run after regen always reformats once; rerun until idle. | `pre-commit run --all-files` to settle. |
| `Parameter not documented: X.y(z=)` | Python has a kwarg the docs don't mention (e.g. legacy name from a doc rename). | If the param is positional with no default, just rename it in `_impl/`. Check `protocol.yml` and the server dispatcher — if the wire field renamed too, also update the channel-send dict key. Only MISMATCH for genuinely hidden internal kwargs (`default_browser_type`). |
| `KeyError: 'templates'` deep in `inner_serialize_doc_type` | A `Promise<X>\|X` union upstream collapsed to a bare `Promise` with no templates in `api.json`. | `documentation_provider.inner_serialize_doc_type` should treat that as `Any` (`if "templates" not in type: return "Any"`). |
| `"void" is not defined (reportUndefinedVariable)` in generated event handlers | `api.json` has a `void`-typed event payload that the serializer left as the literal string `"void"`. | `documentation_provider.inner_serialize_doc_type` should map `"void"` to `"None"` alongside `"null"`. |
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

- `setup.py`: already done in step 2.
- `README.md`: gets the chromium/firefox/webkit version table updated automatically by `scripts/update_versions.py` (called from `update_api.sh`). Don't edit by hand.
- The "Backport changes" tracking issue on GitHub (filed by `microsoft-playwright-automation`) is the *intent* tracker, but it's frequently out of sync with what's actually been ported. Treat it as a starting point, not the source of truth — the `docs/src/api/` commit walk is authoritative.

### 8. Final verification

```sh
pre-commit run --all-files
mypy playwright                 # 2 pre-existing errors in _json_pipe.py and _artifact.py are unrelated
pytest --browser chromium tests/async/<files-you-touched> tests/sync/<files-you-touched>
```

Then a smoke regression on a few neighboring suites (`tests/async/test_browser*.py`, `test_cdp_session.py`, `test_tracing.py`, `test_dialog.py`, `test_page_*.py`) to make sure nothing inherent to the port shifted.

## Reference: `expected_api_mismatch.txt` line forms

Exact strings the generator emits (and that this file must contain to suppress):

```
Method not implemented: <Class>.<snake_method>
Parameter not implemented: <Class>.<snake_method>(<snake_param>=)
Parameter not documented: <Class>.<snake_method>(<snake_param>=)
Method vs property mismatch: <Class>.<snake_method>
Method not documented: <Class>.<snake_method>
Parameter type mismatch in <Class>.<snake_method>(<arg>=): documented as <T1>, code has <T2>
```

Class names use the upstream PascalCase (`BrowserContext`, `BrowserType`); method/param names are converted to `snake_case` matching the Python surface.

## Tips & gotchas

- **`langs.only` is your filter — and the only filter.** Don't classify by name (`Screencast`, `Debugger`, `pickLocator`) or by intuition ("looks like internal tooling"). Always check `langs` in `api.json`. The 1.59 roll cost two extra audit passes by trusting names over `langs`.
- **Audit your own classifications a second time.** After the first walk through the commit range, before opening the PR, re-read every line in `expected_api_mismatch.txt` you added during this roll and ask "is this divergence justified, or did I skip a port?" Run the `langs`-dump snippet on each suspicious entry. The 1.59 roll's first PR had ~20 wrong suppressions; the second pass cut them to 0.
- **A cluster of suppressions on the same class is a smell.** If you're about to add five `Method not implemented: Foo.*` lines, you're almost certainly looking at a class that needs to be implemented. Implement the whole thing once and the suppressions disappear.
- **Watch for revert pairs in the same range.** 1.59 added and reverted `Browser.isRemote` (#39613 / #39620) inside the same release. Walking chronologically lets you skip the add when you see the revert later.
- **Watch for rename-revert pairs.** 1.59 had `Locator.normalize` → `Locator.toCode` (#39648) → `Locator.normalize` (#39754). Final state wins; only port the last.
- **Doc renames almost always include a wire-protocol rename.** Whenever you see `### param: X.y.oldName` → `### param: X.y.newName` in a doc commit, also `git -C ~/code/playwright show <sha> -- packages/protocol/src/protocol.yml` and the corresponding `*Dispatcher.ts` file. If the wire field changed too, the channel-send dict key in `_impl/` must change. Suppressing the doc-side mismatch is hiding a real bug — the previous Python code is silently sending an unknown field that the new server ignores.
- **TypedDicts beat `Dict[str, X]` for any structured return.** When the docs describe a return as `[Object]` with named fields (or even `[Object=Foo]`), define a `TypedDict` in `_api_structures.py`, re-export from both public `__init__.py` files, and use it. Zero runtime cost (it's still a `dict`), and the doc generator's type comparator matches by structure via `get_type_hints`.
- **Positional renames are free.** A param with no default before any `*` separator is positional-or-keyword in Python, but realistic call sites pass it positionally. Renaming such a param doesn't break callers.
- **The "Backport changes" GitHub issue can be misleading.** In the 1.59 roll its checkboxes were all marked `[x]` with annotations like "✅ IMPLEMENTED", but several of those features had not actually been merged into the Python port. Trust the `docs/src/api/` walk over the issue.
- **`api.json` may carry doclint quirks.** 1.59 hit two: `Promise<X>|X` collapsed to a bare `Promise` with no `templates`, and `void`-typed events serialized as the literal string `"void"`. Both are upstream artifacts; patch `inner_serialize_doc_type` to handle them rather than fighting the api.json side.
- **Don't edit `_generated.py` to fix lint or typing.** Fix `_impl/`, `documentation_provider.py`, or `expected_api_mismatch.txt` instead. Hand-editing the generated file is reverted on the next regen.
- **`/tmp/roll-<new>-commits.md` is a working artifact, not a deliverable.** Don't commit it. The commit message and PR description are where the audit summary belongs.
