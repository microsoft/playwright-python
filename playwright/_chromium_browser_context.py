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

from types import SimpleNamespace
from typing import Dict, List, Set

from playwright._browser_context import BrowserContext
from playwright._cdp_session import CDPSession
from playwright._connection import ChannelOwner, from_channel
from playwright._page import Page, Worker


class ChromiumBrowserContext(BrowserContext):

    Events = SimpleNamespace(
        BackgroundPage="backgroundpage",
        ServiceWorker="serviceworker",
    )

    def __init__(
        self, parent: ChannelOwner, type: str, guid: str, initializer: Dict
    ) -> None:
        super().__init__(parent, type, guid, initializer)

        self._background_pages: Set[Page] = set()
        self._service_workers: Set[Worker] = set()

        self._channel.on(
            "crBackgroundPage",
            lambda params: self._on_background_page(from_channel(params["page"])),
        )

        self._channel.on(
            "crServiceWorker",
            lambda params: self._on_service_worker(from_channel(params["worker"])),
        )

    def _on_background_page(self, page: Page) -> None:
        self._background_pages.add(page)
        self.emit(ChromiumBrowserContext.Events.BackgroundPage, page)

    def _on_service_worker(self, worker: Worker) -> None:
        worker._context = self
        self._service_workers.add(worker)
        self.emit(ChromiumBrowserContext.Events.ServiceWorker, worker)

    def backgroundPages(self) -> List[Page]:
        return list(self._background_pages)

    def serviceWorkers(self) -> List[Worker]:
        return list(self._service_workers)

    async def newCDPSession(self, page: Page) -> CDPSession:
        return from_channel(
            await self._channel.send("crNewCDPSession", {"page": page._channel})
        )
