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

from contextlib import closing

import os
import socket

def find_free_port():
  with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
    s.bind(('', 0))
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    return s.getsockname()[1]

class Server:
  def __init__(self):
    self.PORT = find_free_port()
    self.EMPTY_PAGE = f'http://localhost:{self.PORT}/empty.html'
    self.PREFIX = f'http://localhost:{self.PORT}'
    self.CROSS_PROCESS_PREFIX = f'http://127.0.0.1:{self.PORT}'

server = Server()
