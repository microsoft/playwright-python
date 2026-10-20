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

"""A test server route that keeps the files of a multipart/form-data upload, in both flavors.

It replaces the formidable routes of the upstream upload tests:

    server.setRoute('/upload', async (req, res) => {
      const form = new formidable.IncomingForm();
      form.parse(req, function(err, fields, f) {
        files = f;
        res.end();
      });
    });
"""

from typing import Dict

from tests.helpers.multipart import MultipartPart, parse_multipart
from tests.server import Server, TestServerRequest


def route_form_files(server: Server, path: str) -> Dict[str, MultipartPart]:
    """Routes path and returns the uploaded files of the form, by field name.

    Like formidable, it keeps only the parts that have a filename. The dict is empty
    until the route has parsed the request. The route sends the response after it has
    filled the dict, so a test that waits for the response can read the files.
    """
    files: Dict[str, MultipartPart] = {}

    def handle(request: TestServerRequest) -> None:
        content_type = request.getHeader("content-type") or ""
        for part in parse_multipart(content_type, request.post_body or b""):
            if part.filename is not None:
                files[part.name] = part
        request.finish()

    server.set_route(path, handle)
    return files
