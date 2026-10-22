#!/bin/bash

# Generates the files that come from microsoft/playwright, from .upstream/ at the
# commit in DRIVER_VERSION (python scripts/upstream.py checkout):
# - playwright/{async,sync}_api/_generated.py and playwright/_impl/_api_structures.py,
#   from the API docs (docs/src/api), by scripts/codegen/generate_api.js;
# - playwright/_impl/_protocol.py, protocol_types.py, protocol_channels.py and
#   protocol/validator.py, from the protocol spec (packages/protocol/spec), by
#   scripts/codegen/generate_protocol.py;
# - tests/upstream_registry.md, a copy of tests/registry.md.
# The generated files are committed. The Lint job of CI runs this script and fails
# when they differ.
cd "$(dirname "$0")/.." || exit 1

pin="$(cat DRIVER_VERSION)"
if [[ "$(git -C .upstream rev-parse HEAD 2>/dev/null)" != "$pin" ]]; then
    echo ".upstream/ is not at $pin, the commit in DRIVER_VERSION. Run: python scripts/upstream.py checkout" >&2
    exit 1
fi

function update_api {
    flavor="$1"
    file_name="${2:-playwright/${flavor}_api/_generated.py}"
    echo "Generating $file_name"
    if node scripts/codegen/generate_api.js --flavor "$flavor" --out "$file_name"; then
        pre-commit run --files "$file_name"
    else
        echo "Exited due to errors"
        exit 1
    fi
}

update_api structs playwright/_impl/_api_structures.py
update_api sync
update_api async

protocol_files="playwright/_impl/_protocol.py playwright/_impl/protocol_types.py playwright/_impl/protocol_channels.py playwright/_impl/protocol/validator.py"
echo "Generating $protocol_files"
if python scripts/codegen/generate_protocol.py --out playwright/_impl/_protocol.py --types-out playwright/_impl/protocol_types.py --channels-out playwright/_impl/protocol_channels.py --validator-out playwright/_impl/protocol/validator.py; then
    pre-commit run --files $protocol_files
else
    echo "Exited due to errors"
    exit 1
fi

echo "Copying tests/upstream_registry.md"
cp .upstream/tests/registry.md tests/upstream_registry.md
