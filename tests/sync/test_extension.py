# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional

import pytest

from playwright.sync_api import BrowserContext, BrowserType


@pytest.fixture()
def launch_persistent_context(
    browser_type: BrowserType,
    browser_channel: Optional[str],
    tmp_path: Path,
    launch_arguments: Dict[str, Any],
    is_headless_shell: bool,
) -> Generator[Callable[..., BrowserContext], None, None]:
    if browser_channel and browser_channel.startswith("chrome"):
        pytest.skip(
            "--load-extension is not supported in Chrome anymore. https://groups.google.com/a/chromium.org/g/chromium-extensions/c/1-g8EFx2BBY/m/S0ET5wPjCAAJ"
        )
    if is_headless_shell:
        pytest.skip("Headless Shell has no support for extensions")

    contexts: List[BrowserContext] = []

    def launch(extension_path: str, **kwargs: Any) -> BrowserContext:
        context = browser_type.launch_persistent_context(
            str(tmp_path),
            **launch_arguments,
            **kwargs,
            args=[
                f"--disable-extensions-except={extension_path}",
                f"--load-extension={extension_path}",
            ],
        )
        contexts.append(context)
        return context

    yield launch

    for context in contexts:
        context.close()


@pytest.mark.only_browser("chromium")
def test_should_give_access_to_the_service_worker(
    launch_persistent_context: Callable[..., BrowserContext],
    assetdir: Path,
) -> None:
    extension_path = str(assetdir / "extension-mv3-simple")
    context = launch_persistent_context(extension_path)
    service_workers = context.service_workers
    service_worker = (
        service_workers[0]
        if len(service_workers)
        else context.wait_for_event("serviceworker")
    )
    assert service_worker
    assert service_worker in context.service_workers
    while not service_worker.evaluate("globalThis.MAGIC") == 42:
        context.pages[0].wait_for_timeout(100)
    context.close()
    assert len(context.background_pages) == 0


@pytest.mark.only_browser("chromium")
def test_should_give_access_to_the_service_worker_when_recording_video(
    launch_persistent_context: Callable[..., BrowserContext],
    tmp_path: Path,
    assetdir: Path,
) -> None:
    extension_path = str(assetdir / "extension-mv3-simple")
    context = launch_persistent_context(
        extension_path, record_video_dir=(tmp_path / "videos")
    )
    service_workers = context.service_workers
    service_worker = (
        service_workers[0]
        if len(service_workers)
        else context.wait_for_event("serviceworker")
    )
    assert service_worker
    assert service_worker in context.service_workers
    while not service_worker.evaluate("globalThis.MAGIC") == 42:
        context.pages[0].wait_for_timeout(100)
    context.close()
    assert len(context.background_pages) == 0
