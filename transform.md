# How to port the JavaScript client to Python

These rules say how to write `playwright/_impl_v2` from `packages/playwright-core/src/client`
in `microsoft/playwright`. Use them at each roll, for every new or changed line of the
client.

The port is line by line. **The structure of the Python follows the JavaScript. The timing
of the Python follows asyncio.** A reviewer reads the `.ts` file and the `.py` file side by
side. Each JavaScript statement maps to one Python statement, or to one of the fixed
patterns in this document.

Each rule shows the JavaScript form, then the Python form. When a rule changes the behavior,
the rule says why. "Mark it" means: add a `# Python:` comment at that line (see section 11).

The low-level helpers that these rules use are in `playwright/_impl_v2/utils/tasks.py`:
`fire_and_forget()`, `race()`, `completed()`, `failed()`, `wait_for_next_task()` and
`call_in_next_task()`.

## 1. Promises and asyncio

### 1.1 The two timing rules of the JavaScript client

The client code relies on two rules of the JavaScript runtime:

1. An `async` function runs its body at the call, up to the first `await`. The caller
   continues after that.
2. The driver's messages are dispatched one per macrotask. All promise reactions run
   before the next message.

asyncio does not have these rules:

1. A coroutine does not run until a task runs it. `asyncio.ensure_future(coro)` runs the
   first step at the next turn of the event loop, not at the call.
2. A task resumes one step per turn of the event loop. Several callbacks can run between
   two steps.

Rule 1 is not imitated. The rules below make the start of a function explicit where it
matters (1.4) and leave it to asyncio where it does not.

Rule 2 is imitated by one helper, `wait_for_next_task()` (see 1.17). JavaScript calls a
macrotask a "task"; the helper waits until the next task would start: until every
reaction to the current task has run. The transport awaits it before it dispatches the
next message (1.13), and `setTimeout(callback, 0)` is `call_in_next_task(callback)`
(1.11). Use them where upstream relies on a task boundary; nowhere else.

### 1.2 `await` is `await`

```ts
const response = await this._channel.goto(params);
```
```python
response = await self._channel.goto(url=url, waitUntil=wait_until, referer=referer)
```

Both suspend here. This is most of the lines. No mark.

### 1.3 A promise that is awaited later is a task

```ts
const promise = this._doSomething();
await this._somethingElse();
await promise;
```
```python
task = asyncio.ensure_future(self._do_something())
await self._something_else()
await task
```

Use `asyncio.ensure_future()`. It takes a coroutine or a future. `self._do_something()`
starts one turn later than in JavaScript. See 1.4 when that matters. No mark.

An async IIFE, `(async () => { ... })()`, becomes a named `async def` method and
`asyncio.ensure_future(self._name())`. Mark it.

### 1.4 Split a function at its first `await` when the caller needs the start now

Some callers depend on timing rule 1: the body of the called function must run before the
caller continues. The known cases in the client are:

- `waitForEvent()`, `waitForNavigation()` and the Python `expect_*()` context managers:
  the listener must be registered before the action that fires the event.
- A channel call: the message must go out before the caller continues (see 1.5).
- `_wrapApiCall()`: the stack and the zone are captured at the call.
- A function that sets a flag before its first `await`, when the caller starts several
  of them and awaits them together (`RouteHandler.stop()` sets `_ignoreException`).
- An event listener that changes state before its first `await` (see 1.12).

For these cases, write the function as a **plain `def` that runs the prefix and returns
the awaitable of the rest**. The `@api_call()` decorator calls the method at once, so the
prefix runs at the call, inside the API zone, and the decorator returns the awaitable.

```ts
@apiCall()
async waitForEvent(event, predicate) {
  const waiter = Waiter.createForEvent(this, event);   // runs at the call
  waiter.rejectOnTimeout(...);
  const result = await waiter.waitForEvent(this, event, predicate);
  waiter.dispose();
  return result;
}
```
```python
@api_call()
def wait_for_event(self, event, predicate, timeout) -> Awaitable[Any]:
    # Python: a plain def. The waiter and its listeners are set up at the call, as the
    # JS async function sets them up before its first await; the result is the wait.
    waiter = Waiter.create_for_event(self, event)
    waiter.reject_on_timeout(...)
    wait = waiter.wait_for_event(self, event, predicate)

    async def result() -> Any:
        r = await wait
        waiter.dispose()
        return r

    return result()

def expect_event(self, event, predicate, timeout) -> EventContextManagerImpl:
    # Python only: waitForEvent() as a context manager. wait_for_event() is a plain
    # def, so its listeners are registered here, before the with block runs; the
    # wait runs in a task.
    return EventContextManagerImpl(
        asyncio.ensure_future(self.wait_for_event(event=event, predicate=predicate, timeout=timeout))
    )
```

`await page.wait_for_event(...)` works as before: the decorator returns an awaitable.
`Waiter.wait_for_event()` is a plain `def` for the same reason: it registers the listener
and returns the wait.

Do not split a function when no caller depends on the prefix. Mark each split.

### 1.5 A channel call sends now and returns an awaitable

The generated channel methods are plain `def`. The message goes out at the call. The
method returns an awaitable of the result. `Channel._call()` never raises at the call; a
failure is raised when the awaitable is awaited, as a rejected promise is.

```ts
await this._channel.click(params);
const { value } = await this._channel.getAttribute(params);
this._channel.screencastFrameAck(params).catch(() => {});
```
```python
await self._channel.click(selector=selector, ...)
value = (await self._channel.getAttribute(selector=selector, name=name))["value"]
fire_and_forget(self._channel.screencastFrameAck(frameId=frame_id))
```

Every parameter of the protocol is passed, by its protocol name. An absent option is
`None`. `timeout` is `self._timeout(timeout)`, or `NO_TIMEOUT` where the JS has
`kNoTimeout`. A result has every top-level field; a field the driver left out is `None`.

### 1.6 Fire and forget: `.catch(() => {})`

```ts
this._disableInterception().catch(() => {});
void this._channel.updateSubscription(params);
```
```python
fire_and_forget(self._disable_interception())
fire_and_forget(self._channel.updateSubscription(event=event, enabled=enabled))
```

`fire_and_forget()` runs a coroutine as a task and keeps a reference to it. It marks the
exception of the awaitable as handled. It never raises. Use it for every awaitable that
nobody awaits. Never drop an awaitable; never call `asyncio.ensure_future()` and discard
the task.

### 1.7 `.catch(handler)` that is awaited is `try` / `except`

```ts
const error = await this._doStopChunk(path).catch(e => e);
await route._innerContinue(true).catch(() => {});
```
```python
try:
    await self._do_stop_chunk(path)
    error = None
except Exception as e:
    error = e

try:
    await route._inner_continue(is_fallback=True)
except Exception:
    pass
```

Catch `Exception`, not `BaseException`. `asyncio.CancelledError` must pass through (see
1.14). Keep the JS comment that says why the error is ignored.

### 1.8 `Promise.all()` is `asyncio.gather()`

```ts
await Promise.all(promises);
const [handled] = await Promise.all([route._startHandling(), handler(route, request)]);
```
```python
await asyncio.gather(*promises)
handled, _ = await asyncio.gather(route._start_handling(), handler(route, route.request))
```

Both raise the first error and let the other awaitables run on. `gather()` accepts
coroutines and futures. A JavaScript value in the list is not awaitable in Python; keep it
out of the list and use it directly.

### 1.9 `Promise.race()` is `race()`

```ts
return await Promise.race([promise, ...this._failures]);
```
```python
return await race([promise, *self._failures])
```

`race()` returns the result, or raises the error, of the first awaitable that settles.
When several have settled, the first in the list wins. The coroutines that `race()`
started for the call are cancelled when the race ends; a future or a task that was given
to `race()` runs on, as in JavaScript. The errors of the losers are marked as handled, as
`Promise.race()` handles them.

### 1.10 Promises that are created by hand

| JavaScript | Python |
|---|---|
| `new ManualPromise<T>()` | `ManualPromise[T]()` (a future that may be awaited by several tasks) |
| `new Promise<T>(resolve => { ... })` | `future = loop.create_future()`, then `future.set_result(value)` |
| `Promise.resolve(value)` | `completed(value)` |
| `Promise.reject(error)` | `failed(error)` |
| `promise.then(f)` | `async def` that awaits the promise and calls `f` |

Do not write `then()` and `catch()` helpers. Write the `async def`.

One exception. `promise.then(() => { throw e })` is one microtask in JavaScript. A task
is one turn later than a done callback. Where a reaction is only a throw (the failures of
a `Waiter`), write it as a done callback (`future.add_done_callback(...)`), or raise in
the listener itself, so that the failure settles at the event. Mark it.

### 1.11 Timers

```ts
const timer = setTimeout(callback, timeout);
clearTimeout(timer);
```
```python
timer = asyncio.get_running_loop().call_later(timeout / 1000, callback)
timer.cancel()
```

JavaScript timeouts are in milliseconds; asyncio timers are in seconds. The callback runs
at the next turn after the delay. It does not wait for other tasks.

`setTimeout(callback, 0)` is different. Upstream uses it to run the callback in the next
task, after the reactions to the events that the current code emits (a timer is a
macrotask; the reactions are microtasks). That is `call_in_next_task(callback)`, which
awaits `wait_for_next_task()` (1.17) and then calls the callback. Do not use
`call_soon()` for it: one turn is not the end of the reactions.

```ts
setTimeout(() => browser._didClose(), 0);
```
```python
call_in_next_task(lambda: browser._did_close())
```

### 1.12 Async event listeners

```ts
this._channel.on('route', async ({ route }) => { ... });
```
```python
self._channel.onRoute(lambda event: self._on_route(network.Route.from_(event["route"])))
```

`emit()` calls the listener. When the listener returns an awaitable, `EventEmitter`
runs it as a task and keeps it in `_pending_handlers`. An error of the task goes to the
rejection handler of the emitter, or is reported as an unhandled error. The body of an
`async def` listener runs one turn after the event (timing rule 1 does not hold). When the
state that the listener changes before its first `await` matters, apply 1.4: register a
plain `def` that changes the state and returns the awaitable of the rest.

### 1.13 The transport dispatches each message in its own task

Upstream `pipeTransport.ts` hands each message to `setImmediate()`: each message is a
task of its own, so all the reactions to a message run before the next one. The Python
transport does `await wait_for_next_task()` after each message (1.17).

### 1.14 Cancellation is Python only

JavaScript cannot cancel a promise. Python can cancel a task. The rules of the port:

- When the task that awaits an API call is cancelled, the call is aborted. The connection
  sends `__abort__` for its message.
- A future that several tasks may await is never cancelled by one of them. `ManualPromise`
  shields itself in `__await__`. A shared future that is not a `ManualPromise` is awaited
  with `asyncio.shield()`. Mark it.
- Catch `asyncio.CancelledError` only to clean up, and raise it again.
- `race()` and `gather()` follow these rules. See 1.9.

`AbortSignal` and the `signal` options are not ported. Cancellation is their counterpart.
Write `# Not ported: the signal option` at the member.

### 1.15 Every task has an owner

A task that nobody holds can be collected while it runs, and its error is lost. Each task
is one of:

- awaited by the code that created it (`await task`);
- kept by `fire_and_forget()`;
- kept by `EventEmitter` in `_pending_handlers`;
- kept by an object that cancels it on dispose (for example the failure tasks of a
  `Waiter`).

### 1.16 Errors of a task that nobody awaits

In Node.js an unhandled rejection crashes the process. In Python the port reports the
error of an event listener, and the next API call raises it. The error of a
`fire_and_forget()` awaitable is dropped, as the `.catch(() => {})` dropped it.

### 1.17 `wait_for_next_task()`: the task boundary

In JavaScript, a task (macrotask) is a message from the driver, a timer, or an I/O
callback. The reactions of promises (microtasks) all run before the next task starts.
asyncio has no such boundary: the callback of a future, and then each task that the
callback wakes up, is a turn of the event loop of its own, in one queue with everything
else. So the reactions to a message are a chain of turns of unknown depth: a wait is two
turns, an `expect_*()` is three, a `gather()` adds one more.

`wait_for_next_task()` waits until that chain is done: it yields until the event loop
has no callback ready to run. Then the next message, or the callback of a 0 ms timer,
runs as the next task would in JavaScript. Without it, a listener that user code
registers after one event misses the next message when both messages were read from the
pipe together.

The ready queue is not public API (`loop._ready`); on a loop that does not have it, the
helper yields twice, the depth of a wait. It stops after 100 turns.

Use it only where upstream relies on the task boundary: the transport (1.13) and
`setTimeout(…, 0)` (1.11). Do not use it to order the client's own code; make that
order explicit at the site (1.4, 1.10).

## 2. Files, classes and members

- One Python module per JavaScript file, in snake_case: `browserContext.ts` is
  `browser_context.py`. The parts of `packages/isomorphic`, `packages/protocol` and
  `packages/utils` that the client uses are under `isomorphic/`, `protocol/` and `utils/`.
- Keep the members in the JavaScript order. Keep the JavaScript comments.
- `constructor()` is `__init__()`. Initialize the fields in the JavaScript order. A field
  declared with `!` and set later is annotated and set to `None` with `cast()`.
- `static from(channel)` is `from_(channel)`, a `@staticmethod`. `static fromNullable()`
  is `from_nullable()`.
- A getter, or a method without parameters that the generated API reads as a property,
  is a `@property`. The generated API decides; check `_generated.py`. Mark it in the
  module docstring.
- `toJSON()` is `__repr__()`. `[util.inspect.custom]()` is `__str__()`.
- `[Symbol.asyncDispose]()` is not ported; the Python API has `close()` or the generated
  context manager.
- `private` and `_name` members keep the underscore. Public members have no underscore.
- A JavaScript module function is a Python module function, at the same position.

## 3. Names and options

- camelCase is snake_case: `waitForLoadState` is `wait_for_load_state`.
- An options object is keyword arguments. The implementation method takes the arguments
  that the generated API passes, in that order, with the Python names. An option that can
  be absent is `Optional[X]` with no default. So mypy reports a call that does not pass a
  new option.
- The channel call takes the protocol names, in camelCase: `waitUntil=wait_until`.
- `options?.x` is `x`. `{ ...options, y }` is `{**options, "y": y}`.
- A JavaScript parameter that the Python API does not have (for example `noWaitAfter`
  on `hover()`) is accepted by the implementation method and not sent. Say so in the
  module docstring.
- A user-facing message that names an option or a method names the Python one:
  `'Pass { acceptDownloads: true }'` is `"Pass 'accept_downloads=True'"`. Mark it.

## 4. `undefined`, `null` and `None`

- `None` is `undefined`. A `None` option is not sent; the validator drops the key. A
  `None` value in a result from the driver is a field that the driver left out.
- A JSON `null` inside the data of an array (for example an IndexedDB record in a storage
  state) is `None` too, and the validator keeps it, as it is data and not an option.
- `x !== undefined` is `x is not None`. `x ?? y` is `x if x is not None else y`.
- `if (x)` on an object or an array is `if x is not None`: `{}` and `[]` are true in
  JavaScript and false in Python. Mark it. `if (x)` on a string or a number is `if x`.
- `x || y` on an object is `x if x is not None else y`. On a string or a number it is
  `x or y`.
- A value that goes to the page (an evaluate argument) and is `None` is `undefined`, as in
  `playwright/_impl`.

## 5. Errors

- `throw new Error(message)` is `raise Error(message)`. The classes are the public ones
  of `playwright/_impl/_errors.py`: `Error`, `TimeoutError`, `TargetClosedError`. Import
  them from `playwright/_impl_v2/errors.py`.
- `assert(condition, message)` from `@isomorphic/assert` is
  `if not condition: raise Error(message)`. Never use the `assert` statement: it is
  removed by `python -O`, and it raises the wrong class.
- `e.message` is `e.message`. `e.name` is `e.name`. `e.stack` is `e._stack`.
- `rewriteErrorMessage(e, message)` is `rewrite_error_message(e, message)`. The Python
  version returns a copy, because one error object can fail several calls. Mark the call.
- `isTargetClosedError(e)` is `is_target_closed_error(e)`:

  ```ts
  try { ... } catch (e) { if (isTargetClosedError(e)) return; throw e; }
  ```
  ```python
  try: ...
  except Exception as e:
      if is_target_closed_error(e):
          return
      raise
  ```
- Keep the text of a message. Change only the names of options and methods (see 3).
- An error that comes from the driver is parsed by `parse_error()`; a client error is
  serialized by `serialize_error()`. Both keep `name`, `message` and `stack`.

## 6. Events

- `this._channel.on('x', handler)` is `self._channel.onX(handler)`. The generated
  `onX()` passes the event payload as a dict with every top-level field; an absent field
  is `None`.
- `this.emit(Events.Page.Close, this)` is `self.emit(Events.Page.Close, self)`. `emit()`
  returns `True` when a listener ran.
- `on()`, `once()`, `addListener()`, `removeListener()`, `off()` keep their Node.js
  semantics in `event_emitter.py`. A listener is a plain function; see 1.12 for `async`.
- The constants of `events.ts` are in `events.py`, with the same strings.

## 7. Types

| JavaScript | Python |
|---|---|
| `interface X { a: string; b?: number }` | `class X(TypedDict)` with `b: NotRequired[...]`, or a `total=False` TypedDict |
| `T \| undefined`, `T?` | `Optional[T]` |
| `Array<T>` as input | `Sequence[T]` |
| `Array<T>` as output or a field | `List[T]` |
| `Record<string, T>` | `Dict[str, T]` |
| `Map<K, V>` | `Dict[K, V]`; `utils/map.py` when the keys are objects compared by identity |
| `Set<T>` | `Dict[T, None]` when the order matters, else `Set[T]` |
| `Buffer` | `bytes`; base64 at the channel boundary |
| `number` | `float`, or `int` where the protocol says `integer` |
| `string \| RegExp` | `Union[str, Pattern[str]]` |
| `Function`, `(a: A) => B` | `Callable[[A], B]` |
| `Promise<T>` | `Awaitable[T]` as a return type; `asyncio.Future[T]` for a future |

The protocol types are generated into `protocol_types.py`; never write them by hand. The
public TypedDicts of the API are generated into `playwright/_impl/_api_structures.py`.

## 8. Strings, numbers, regular expressions and JSON

- `String(n)` is `js_string(n)`: `30000.0` prints as `30000`. Use it in messages.
- A template literal is an f-string.
- `JSON.stringify(x)` is `json.dumps(x, separators=(",", ":"), ensure_ascii=False)`.
- `JSON.parse(s)` is `json.loads(s)`. `json.loads()` accepts `NaN`; mark it where it
  matters.
- A `RegExp` is a `re.Pattern`. The flags go to the driver as JavaScript letters through
  `escape_regex_flags()`; a flag that JavaScript does not have raises.
- `s.startsWith(x)` is `s.startswith(x)`. `xs.includes(x)` is `x in xs`.
- `encodeURIComponent(s)` is `urllib.parse.quote(s, safe="")`.
- `Buffer.from(s, 'base64')` is `base64.b64decode(s)`. `buffer.toString('base64')` is
  `base64.b64encode(buffer).decode()`.
- `Number.MAX_SAFE_INTEGER` is the constant `MAX_SAFE_INTEGER` in the module that uses it.

## 9. Files, paths and the process

- `await fs.promises.readFile(p)` is `await asyncio.to_thread(Path(p).read_bytes)`. Never
  read or write a file on the event loop.
- `fs.promises.mkdir(p, { recursive: true })` is `os.makedirs(p, exist_ok=True)`, in a
  thread.
- `path.resolve(p)` is `os.path.abspath(p)`. `path.basename(p)` is `os.path.basename(p)`.
  `path.join()` is `os.path.join()`. A `Path` argument is accepted everywhere a string is.
- `process.env.X` is `os.environ.get("X")`. `process.platform` is `sys.platform`.
  `process.cwd()` is `os.getcwd()`.

## 10. Loops and collections

- `for (const x of xs)` is `for x in xs`.
- `xs.map(f)` is a list comprehension. `xs.filter(f)` is a list comprehension with `if`.
- `xs.find(f)` is `next((x for x in xs if f(x)), None)`.
- `xs.some(f)` is `any(f(x) for x in xs)`. `xs.every(f)` is `all(...)`.
- `xs.indexOf(x)` compares by identity: `next((i for i, y in enumerate(xs) if y is x), -1)`.
  Mark it.
- `xs.splice(i, 1)` is `del xs[i]`. `xs.push(x)` is `xs.append(x)`.
- `Object.entries(o)` is `o.items()`. `Object.keys(o)` is `o.keys()`. `delete o.x` is
  `o.pop("x", None)`.
- JavaScript iterates a `Map` or a `Set` that changes during the loop. Python does not.
  Iterate a copy: `for x in list(xs)`. Mark it.

## 11. Marks

Three marks, each a comment on the line before the code:

- `# Python: <reason>` — the Python does something different from the JavaScript. Say
  what and why, in one or two lines. Use it for every rule above that says "mark it".
- `# Python only: <what>` — code with no JavaScript counterpart: a helper, the
  `expect_*()` methods, `__repr__()`.
- `# Not ported: <member> <reason>` — a JavaScript member that is left out. Give the
  reason: `langs: js` in the docs, a test hook, a Node.js internal.

Do not mark a plain rename or a plain `await`. Do not repeat the code in the comment. When
a whole module deviates in the same way, say it once in the module docstring.

## 12. What is not ported

- A member with `* langs: js` in `docs/src/api/*.md`. Check the docs, not the name.
- The `signal` options and `AbortSignal` (see 1.14).
- The `exposeFunctions` options and `addInitScript(script, arg)`.
- The `__testHook*` options: a JavaScript function that the server calls.
- `android.ts`, `electron.ts`, `coverage.ts`: `langs: js`.
- `channels.d.ts`: the generator writes `protocol_channels.py` and `protocol_types.py`.

## 13. At each roll

1. List the upstream commits of the range for `packages/playwright-core/src/client`,
   `packages/isomorphic`, `packages/protocol` and the parts of `packages/utils` that are
   ported.
2. For each hunk, find the Python line and apply the rules. Keep the order.
3. Regenerate the protocol files with `./scripts/update_api.sh`.
4. Run `mypy playwright` and `./test-v2.sh`.
5. Read every `# Python:` mark in the changed members again. Remove a mark whose reason
   is gone. Add one for each new deviation.
