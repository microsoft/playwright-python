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

from scripts.documentation_provider import DocumentationProvider


def test_transform_documentation_entry() -> None:
    provider = DocumentationProvider()
    assert provider._transform_doc_entry("<[Promise]<?[Error]>>") == "<Optional[Error]>"
    assert provider._transform_doc_entry("<[Frame]>") == "<Frame>"
    assert (
        provider._transform_doc_entry("<[function]|[string]|[Object]>")
        == "<[function]|[str]|[Dict]>"
    )
    assert provider._transform_doc_entry("<?[Object]>") == "<Optional[Dict]>"
