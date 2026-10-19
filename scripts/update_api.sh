#!/bin/bash

# Generates the public API (playwright/{async,sync}_api/_generated.py) and its
# TypedDicts (playwright/_impl/_api_structures.py) from the Playwright API docs
# (docs/src/api) in a microsoft/playwright checkout, pointed to by PW_SRC_DIR,
# and the protocol tables (playwright/_impl/_protocol.py) from its protocol spec
# (packages/protocol/spec).
# Use a separate checkout at the exact commit in DRIVER_VERSION (rev=), the commit
# that the playwright-core package (npm=) is built from. The generator is
# scripts/codegen/generate_api.js; Python facts that the docs do not contain
# are in scripts/codegen/python_rules.js.
driver_version="$(sed -n 's/^npm=//p' DRIVER_VERSION)"
driver_rev="$(sed -n 's/^rev=//p' DRIVER_VERSION)"
if [[ -z "$PW_SRC_DIR" ]]; then
    echo "Set PW_SRC_DIR to a separate microsoft/playwright checkout at ${driver_rev} (playwright-core ${driver_version}), e.g.:" >&2
    echo "    PW_SRC_DIR=../playwright-for-python ./scripts/update_api.sh" >&2
    exit 1
fi
if [[ "$(git -C "$PW_SRC_DIR" rev-parse HEAD)" != "$driver_rev" ]]; then
    echo "$PW_SRC_DIR is not at ${driver_rev}, the commit of playwright-core ${driver_version} in DRIVER_VERSION:" >&2
    echo "    git -C \"$PW_SRC_DIR\" fetch origin && git -C \"$PW_SRC_DIR\" checkout --detach ${driver_rev}" >&2
    exit 1
fi
if [[ -n "$(git -C "$PW_SRC_DIR" status --porcelain)" ]]; then
    echo "$PW_SRC_DIR has local changes; generate from a clean checkout." >&2
    exit 1
fi
export PW_SRC_DIR

function update_api {
    flavor="$1"
    file_name="${2:-playwright/${flavor}_api/_generated.py}"
    echo "Generating $file_name"
    if node scripts/codegen/generate_api.js --flavor "$flavor" --out "$file_name"; then
        pre-commit run --files "$file_name"
        echo "Regenerated APIs"
    else
        echo "Exited due to errors"
        exit 1
    fi
}

update_api structs playwright/_impl/_api_structures.py
update_api sync
update_api async

echo "Generating playwright/_impl/_protocol.py, _protocol_types.py and _protocol_channels.py"
if python scripts/codegen/generate_protocol.py --out playwright/_impl/_protocol.py --types-out playwright/_impl/_protocol_types.py --channels-out playwright/_impl/_protocol_channels.py; then
    pre-commit run --files playwright/_impl/_protocol.py playwright/_impl/_protocol_types.py playwright/_impl/_protocol_channels.py
else
    echo "Exited due to errors"
    exit 1
fi

playwright install

python scripts/update_versions.py
