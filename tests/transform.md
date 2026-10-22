# How to port the upstream tests to Python

These rules say how to write `tests/async/{page,library}` and `tests/sync/{page,library}`
from `tests/page` and `tests/library` in `microsoft/playwright`, at the commit in
`DRIVER_VERSION`. Use them at each roll, for every new or changed upstream test. The
upstream tests are in `.upstream/`, the checkout at that commit. The steps of a roll are
in the `playwright-roll` skill.

The port is line by line, with **zero deviations**. A reviewer reads the `.spec.ts` file
and the two `.py` files side by side. Each upstream statement maps to one Python
statement, or to one of the fixed patterns in this document. The test does what the
upstream test does, in the same order, with the same values, and checks the same things.

**Never change a port to make it pass.** No skip, condition, mark, wait or assertion
that upstream does not have, for any reason: not a browser channel, not a CI image, not an
operating system, not flakiness. A port that fails shows a bug in the client, the driver
or the environment: fix that, or report it with the evidence. The one allowed mark is
`@pytest.mark.xfail(reason="python: ...", strict=True)`, for a bug in the Python client
that is not fixed yet.

The rules of the client itself are in `playwright/_impl/transform.md`.

## 1. Files and names

- The upstream file decides the Python files: `tests/page/page-check.spec.ts` is
  `tests/async/page/test_page_check.py` and `tests/sync/page/test_page_check.py`;
  `tests/library/chromium/oopif.spec.ts` is `tests/async/library/chromium/test_oopif.py`
  and the same under `tests/sync`. The tests keep the upstream order.
- Every upstream test has an identifier, the first token of its title
  (`it('CH-001 should check the box', ...)`). `tests/upstream_registry.md` is a copy of
  upstream's `tests/registry.md` and lists them all. The name of the port is `test_`, the
  identifier with `_`, the `describe` titles and the title, all in snake_case:
  `test('EX-181 toHaveCount pass')` in `test.describe('toHaveCount')` is
  `test_EX_181_to_have_count_to_have_count_pass`.
- A test that a loop declares several times (`for (const kind of kinds) it(...)`) is one
  function with `@pytest.mark.parametrize`, with the loop values as the ids.
- `beforeEach`, `afterEach` and the fixtures that a file defines (`test.extend({...})`)
  are pytest fixtures at the top of the file, with the same names in snake_case. Helpers
  of the file stay helpers of the file.
- A test that can not exist in Python (a JavaScript-only API, Node.js client internals,
  tools that run in the driver, `@playwright/test` features) is not ported: it goes in
  `tests/upstream_not_ported.txt`, with the reason. Nothing else is left out.
- `python scripts/check_test_registry.py` checks that every test in the registry is
  ported twice or listed as not ported, under the expected name. `--missing <code or
  file glob>` prints the names still to port.

## 2. The two flavors

The async port is the port. The sync port is the same test again, statement for statement,
with the sync API:

- `await page.click()` is `await page.click()` in `tests/async` and `page.click()` in
  `tests/sync`.
- `const [a, b] = await Promise.all([p1, p2])` is `a, b = await asyncio.gather(p1, p2)`
  in async. In sync it is `a, b = sync_gather(lambda: ..., lambda: ...)`: the `sync_gather`
  fixture runs each callable in a greenlet of its own and returns their results in order.
- `const [event] = await Promise.all([page.waitForEvent('x'), action()])` is
  `async with page.expect_event("x") as info: await action()` then `await info.value`.
  In sync: `with page.expect_event("x") as info: action()` then `info.value`.
- `const promise = page.waitForX(); ...; await promise` (a wait that starts before the
  action and is awaited later) is `task = asyncio.create_task(page.wait_for_x())` in
  async. In sync, where the port needs a bare future, `wait_for_future(page._loop,
  page._dispatcher_fiber, future)` from `playwright._impl._greenlets` runs the event loop
  until it settles; the file keeps a small helper for it when it needs several.
- A handler that upstream writes as `async route => { await route.fulfill() }` is
  `async def handler(route): await route.fulfill()` in async and
  `def handler(route): route.fulfill()` in sync. The sync API runs it in a greenlet of
  its own, so it may block.

## 3. Fixtures

The upstream fixtures map to the pytest fixtures of `tests/conftest.py`,
`tests/async/conftest.py` and `tests/sync/conftest.py`:

| Upstream | Python |
|---|---|
| `page`, `context`, `browser`, `browserType` | `page`, `context`, `browser`, `browser_type` |
| `server`, `httpsServer` | `server`, `https_server` (`tests/server.py`, Twisted) |
| `browserName`, `channel` | `browser_name`, `browser_channel` |
| `isWindows`, `isMac`, `isLinux`, `platform` | `is_win`, `is_mac`, `is_linux`, `platform` |
| `headless`, `isHeadlessShell` | `headless`, `is_headless_shell` |
| `browserVersion`, `browserMajorVersion` | `browser_version`, `browser_major_version` |
| `launchPersistent`, `contextFactory`, `browserFactory` | `launch_persistent`, `context_factory`, `browser_factory` |
| `createUserDataDir` | `create_user_data_dir` |
| `asset('file')` | `assetdir / "file"` |
| `expect(buffer).toMatchSnapshot('x.png')` | `assert_to_be_golden(buffer, "x.png")` |
| `kTargetClosedErrorMessage` | `TARGET_CLOSED_ERROR_MESSAGE` (`tests/utils.py`) |
| `startRemoteServer`, `connect`, `twoPages` and the other fixtures of a file | fixtures of the same name in the file, or in `tests/helpers/` when several files share them |

The server has the methods of upstream's `TestServer` in snake_case: `set_route`,
`set_redirect`, `set_auth`, `set_csp`, `enable_gzip`, `wait_for_request`,
`expect_request`, `wait_for_web_socket`. A route handler takes a `TestServerRequest`
(Twisted's `Request`): `setHeader`, `setResponseCode`, `write`, `finish`, `getHeader`,
`post_body`.

## 4. Statements

- `expect(a).toBe(b)`, `toEqual`, `toContain`, `toBeTruthy`, `toBeGreaterThan` are
  `assert a == b`, `assert a == b`, `assert b in a`, `assert a`, `assert a > b`. A matcher
  on a locator or a page (`await expect(locator).toHaveText(...)`) is the same matcher of
  the Python API: `await expect(locator).to_have_text(...)`, and `expect(locator)...` in
  sync.
- `await expect(promise).rejects.toThrow('text')` and `const error = await
  promise.catch(e => e); expect(error.message).toContain('text')` are
  `with pytest.raises(Error) as exc_info: await promise` and
  `assert "text" in exc_info.value.message`. The class is the one upstream expects:
  `Error`, `TimeoutError`, `TargetClosedError` from the public API.
- `it.skip(condition, reason)` and `test.skip(...)` are `if condition: pytest.skip(reason)`
  at the top of the test, with the same condition. `it.fixme(condition, reason)` is the
  same with `pytest.skip("fixme")`, or the reason when there is one: a fixme is a skip
  that upstream has, so the port has it too. A skip at the top of a file or a `describe`
  is a condition in each test of it, or `pytestmark`.
- `test.slow()` and `test.setTimeout(test.info().timeout * 3)` are
  `@pytest.mark.slow`; at the top of a file, `pytestmark = pytest.mark.slow`. The
  timeout of a test is 30 seconds, as upstream (`pyproject.toml`); `slow` triples it.
- `it('...', { annotation: ... }, ...)`: the annotation is not ported.
- `page.evaluate(() => ...)`: the function stays JavaScript, in a string. A function
  with arguments takes one argument: `page.evaluate("([a, b]) => a + b", [a, b])`. A
  Node.js value that goes to the page is the Python value: `undefined` and `null` are
  `None`, an object is a dict with the same keys, an array is a list, a `Buffer` is
  `bytes`, a `RegExp` is `re.compile(...)`, a `Date` is a `datetime`.
- The options of an API call are keyword arguments in snake_case: `{ waitUntil: 'load' }`
  is `wait_until="load"`. The keys of the data that the page or the driver returns stay
  as they are (`request.headers["content-type"]`, `entry["response"]["headers"]`).
- `new Promise(resolve => ...)` that the test settles itself is an `asyncio.Future` that
  the test settles; `new Promise(f => setTimeout(f, 100))` is `asyncio.sleep(0.1)` in
  async and `page.wait_for_timeout(100)` or `time.sleep(0.1)` in sync, as the test needs.
- `console.log` and comments stay, as comments. A comment that explains an upstream
  workaround stays with the code it explains.

## 5. Marks

The port has one mark of its own, `# Python:`, on the line before a statement whose form
the rules above change in a way that is not obvious: a value that Python can not express
as upstream does, a helper that stands for a JavaScript construct. Do not mark a plain
rename or a plain `await`. A mark is not a deviation: the test still does what upstream
does.

## 6. Python-only tests

A behavior that no upstream test covers (the sync API, asyncio, Python types, `__repr__`,
a regression of this repository) gets a test in `tests/async/python/` or
`tests/sync/python/`, in the file named after the upstream file of the feature. These
are not ports: see the second rule of tests in `AGENTS.md`, and keep them few.
