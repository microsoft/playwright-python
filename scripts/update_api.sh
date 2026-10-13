#!/bin/bash

# Generates the public API (playwright/{async,sync}_api/_generated.py) and its
# TypedDicts (playwright/_impl/_api_structures.py) from the Playwright API docs
# (docs/src/api) in a microsoft/playwright checkout, pointed to by PW_SRC_DIR.
# Use a separate checkout on the exact release branch for the version in
# DRIVER_VERSION (for example release-1.64). The generator is
# scripts/codegen/generate_api.js; Python facts that the docs do not contain
# are in scripts/codegen/python_rules.js.
driver_version="$(cat DRIVER_VERSION)"
if [[ -z "$PW_SRC_DIR" ]]; then
    echo "Set PW_SRC_DIR to a separate microsoft/playwright checkout on the release branch for v${driver_version}, e.g.:" >&2
    echo "    PW_SRC_DIR=../playwright-for-python ./scripts/update_api.sh" >&2
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

playwright install

python scripts/update_versions.py
