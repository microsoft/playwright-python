# AGENTS.md

- Use 80% of the way to ASD-STE100 when talking to me and when generating docs.

Python bindings for Playwright. The client in `playwright/_impl/` talks to the Node.js
driver in `playwright/driver/` over a pipe.

## Upstream

Everything comes from `microsoft/playwright` at the commit in `DRIVER_VERSION`: the
driver, the generated API and the code that we port. `.upstream/` is a full clone of it
(gitignored). Read upstream code there. Do not edit, commit or switch branches in it.

```sh
python scripts/upstream.py checkout   # clone .upstream/, or move it to DRIVER_VERSION
python scripts/upstream.py changes    # what changed upstream since DRIVER_VERSION at HEAD
```

## Build and test

You need Python 3.10+, git, Node.js and npm.

```sh
python3 -m venv env && source env/bin/activate   # no python3-venv: uv venv env
pip install -r local-requirements.txt
pip install -e .
python scripts/upstream.py checkout
python -m build --wheel        # builds the driver from .upstream/ into playwright/driver/
python -m build --sdist        # the driver without Node.js; runs with PLAYWRIGHT_NODEJS_PATH
playwright install chromium    # not --with-deps: sudo is denied here
./test.sh [browser]            # tests/sync and tests/async, under xvfb
./scripts/lint.sh              # the Lint job of CI; run it before you commit
```

When `DRIVER_VERSION` changes, for example after a pull, run
`python scripts/upstream.py checkout` and build again. Run `tests/sync` and
`tests/async` in separate pytest runs: a sync test fails in a process where an async
test ran.

The install is editable: a change under `playwright/` needs no build, the next
`pytest` runs it. Run `mypy playwright` after it. Rebuild the wheel only when
`DRIVER_VERSION` or `NODE_VERSION` changes.

## The port

`playwright/_impl/` is a line-by-line port of the JS client,
`packages/playwright-core/src/client/*.ts`. `isomorphic/`, `protocol/` and `utils/` port
the parts of `packages/isomorphic`, `packages/protocol` and `packages/utils` that the
client uses. The rules are in `playwright/_impl/AGENTS.md`.

- One module per upstream file, in snake_case (`browserContext.ts` is
  `browser_context.py`), with the members in the JS order and the JS comments. The
  docstring names the file: `"""Port of packages/playwright-core/src/client/page.ts.`
  (`upstream.py changes` reads it).
- Each difference from the JS has a `# Python:` comment.
- Modules that start with `_` are Python only. `_api_classes.py` lists the
  implementation of each API class; the generated API imports it. `_greenlets.py` runs
  the sync API.
- A new `ChannelOwner` goes in `_object_factories()` in `connection.py`, and declares its
  channel: `_channel: "PageChannel"`. A plain wrapper class (like `Clock`) takes
  `_loop` and `_dispatcher_fiber` from its parent.
- Implementation methods take the snake_case arguments that the generated API passes.
  An option that can be absent is `Optional[X]` with no default, so that mypy finds
  each caller that misses a new option.
- Send messages with the generated channel methods, every parameter by its protocol
  name: `await self._channel.click(selector=selector, ..., timeout=self._timeout(timeout))`.
  `None` is not sent. Listen with `self._channel.on<Event>(handler)`. The tests check
  every sent message against the protocol spec.

## The API comes from the upstream docs

`./scripts/update_api.sh` generates these files from `.upstream/`, and they are
committed. Never edit them by hand.

- `playwright/{async,sync}_api/_generated.py` and `playwright/_impl/_api_structures.py`,
  from `docs/src/api`, by `scripts/codegen/generate_api.js`;
- the protocol files of `_impl/` (`protocol_channels.py`, `protocol_types.py`,
  `protocol/validator.py`, `_protocol.py`), from `packages/protocol/spec`;
- `tests/upstream_registry.md`, a copy of `tests/registry.md`.

After a docs change, `mypy playwright` shows what `_impl/` is missing.

- `* langs:` in the docs alone decides if a member is for Python. No `langs` means every
  language. Do not judge by the name of an API.
  `node .upstream/utils/doclint/generateApiJson.js` dumps the docs with `langs`.
- When Python ships a different API, the Python API wins: fix the upstream docs with a
  Python-only declaration (`* langs: python`).
- `scripts/codegen/python_rules.js` holds only what the docs can not say, each entry with
  a one-line comment that says why. The generator fails on an entry that matches
  nothing.
- An inline `[Object]` needs a Python name in the docs (`` "Name" <[Object]> `` or
  `* alias-python:`); the generator then writes its TypedDict. Export it from both
  `__init__.py` files.
- Other generator errors name the place: fix the docs, or add the type to `toPy` in
  `generate_api.js`. `scripts/codegen/compare_api.py` shows what changed between two
  generated files.

## Tests

`tests/{async,sync}/page/` and `library/` port upstream's `tests/page/` and
`tests/library/` test for test, once per flavor. `tests/AGENTS.md` has the rules.
`python scripts/check_test_registry.py` checks that each test of the registry is ported,
or listed in `tests/upstream_not_ported.txt` with the reason (`--missing` prints what is
left).

- Port with zero deviations. Never change a port to make it pass: fix the client, the
  driver or the environment. The only allowed mark is
  `xfail(reason="python: ...", strict=True)`, for a known bug of the client.
- The test timeout is 30 s, as upstream. `test.slow()` is `@pytest.mark.slow`.
- Python-only tests (the sync API, asyncio, regressions) go in `tests/{async,sync}/python/`.
  Keep them few: extend a test before you add one.

### Regression tests

- A regression test for a bug of the Python client goes in `tests/async/python/` or
  `tests/sync/python/`, in the file named after the upstream file of the feature
  (`test_page.py`), as one added case in an existing test. Write it once, in the
  flavor that the issue uses. When a port carries `xfail(reason="python: ...",
  strict=True)` for the bug, remove the mark instead: that port is the regression test.
- Tag the test with the issue in a comment on the first line of its body:
  `# Regression test for https://github.com/microsoft/playwright-python/issues/<n>.`
- The fixtures are `page`, `context`, `browser`, `browser_type`, `server`,
  `https_server`, `browser_name`, `assetdir` and, in sync, `sync_gather`;
  `tests/AGENTS.md` has the whole map. Use `server.set_route(path, handler)`,
  `server.PREFIX` and `server.EMPTY_PAGE`. A handler takes a Twisted request:
  `setHeader`, `setResponseCode`, `write`, `finish`.
- Annotate every parameter and the return value (`-> None`): mypy and pyright check
  the tests. A `Protocol violations` failure is a bug in the client, not in the test.
- Good models: `test_response_headers_should_work` in
  `tests/async/python/test_network.py`, and
  `test_sync_calls_should_raise_after_driver_exit` in `tests/sync/python/test_sync.py`.
- Run one file with one browser: `pytest tests/async/python/test_page.py --browser
  chromium`, then `--browser firefox` and `--browser webkit`. Without `--browser`,
  pytest runs all three. `-k <name>` selects one test, `--headed` runs the browser
  headed. The timeout of a test is 30 s; `@pytest.mark.slow` triples it. A change in
  `playwright/_impl/` serves both APIs: run the ported files of the feature in both
  flavors.

## Rolls

Use the `playwright-roll` skill.

## Commits and PRs

- Never push without "push", "upload", "create PR" or "ship it" in my message, also not
  to an open PR. Commit locally and tell me.
- Never post comments or reviews on GitHub as me. Write the text and wait for my OK.
- Commit message: `label(scope): description`, with `fix`, `feat`, `chore`, `docs`,
  `test` or `devops`. No Co-Authored-By, no "Generated with".
- Branch for an issue: `fix-<number>`. PR description: a few bullets, no test plan,
  `Fixes https://github.com/microsoft/playwright-python/issues/<number>`.
