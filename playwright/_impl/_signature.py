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

import inspect
import sys
from typing import Any, Callable

if sys.version_info < (3, 14):

    def signature(fn: Callable[..., Any]) -> inspect.Signature:
        return inspect.signature(fn)

else:
    # PEP 649 made annotations lazily evaluated, and inspect.signature()
    # evaluates them eagerly by default. Handlers annotated with names that
    # only exist under `if TYPE_CHECKING:` would raise NameError while all we
    # need is the parameter list, so ask for unresolved forward references.
    from annotationlib import Format

    def signature(fn: Callable[..., Any]) -> inspect.Signature:
        return inspect.signature(fn, annotation_format=Format.FORWARDREF)
