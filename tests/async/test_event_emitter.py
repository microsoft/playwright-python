import asyncio

from playwright._impl.event_emitter import EventEmitter


async def test_ignore_errors_should_not_suppress_errors_from_other_events() -> None:
    emitter = EventEmitter()
    release = asyncio.Event()
    reported = []

    loop = asyncio.get_running_loop()
    previous_handler = loop.get_exception_handler()
    loop.set_exception_handler(
        lambda loop, context: reported.append(context.get("exception"))
    )
    try:
        async def listener_a() -> None:
            await release.wait()
            raise RuntimeError("Error in event A")

        async def listener_b() -> None:
            await release.wait()
            raise RuntimeError("Error in event B")

        emitter.on("a", listener_a)
        emitter.on("b", listener_b)

        emitter.emit("a")
        emitter.emit("b")

        await emitter.remove_all_listeners("a", "ignoreErrors")
        release.set()

        await asyncio.sleep(0)
        await asyncio.sleep(0)

        assert [str(error) for error in reported] == ["Error in event B"]
    finally:
        loop.set_exception_handler(previous_handler)


async def test_ignore_errors_should_not_affect_listeners_added_after_removal() -> None:
    emitter = EventEmitter()
    reported = []

    loop = asyncio.get_running_loop()
    previous_handler = loop.get_exception_handler()
    loop.set_exception_handler(
        lambda loop, context: reported.append(context.get("exception"))
    )
    try:
        await emitter.remove_all_listeners("a", "ignoreErrors")

        async def listener_b() -> None:
            raise RuntimeError("Error in a later event B listener")

        emitter.on("b", listener_b)
        emitter.emit("b")

        await asyncio.sleep(0)
        await asyncio.sleep(0)

        assert [str(error) for error in reported] == [
            "Error in a later event B listener"
        ]
    finally:
        loop.set_exception_handler(previous_handler)
