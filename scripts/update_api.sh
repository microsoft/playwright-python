#!/bin/bash

# Codegen needs Playwright's api.json (the documented API surface), which the
# assembled driver bundle does not ship — it is generated from the upstream docs
# and is only needed here, when regenerating the API. Generate it into a temp file
# and hand it to the generators via PW_API_JSON (documentation_provider.py reads it
# from there); nothing is written into the driver. If PW_API_JSON is already set,
# use that pre-generated api.json as-is; otherwise generate it from a nearby
# microsoft/playwright checkout pointed to by PW_SRC_DIR (at the tag in
# DRIVER_VERSION).
driver_version="$(cat DRIVER_VERSION)"
if [[ -z "$PW_API_JSON" ]]; then
    if [[ -z "$PW_SRC_DIR" ]]; then
        echo "Set PW_SRC_DIR to a microsoft/playwright checkout at v${driver_version}" >&2
        echo "(or PW_API_JSON to a pre-generated api.json), e.g.:" >&2
        echo "    PW_SRC_DIR=../playwright ./scripts/update_api.sh" >&2
        exit 1
    fi
    PW_API_JSON="$(mktemp "${TMPDIR:-/tmp}/playwright-api-json.XXXXXX")"
    trap 'rm -f "$PW_API_JSON"' EXIT
    echo "Generating api.json from $PW_SRC_DIR"
    if ! API_JSON_MODE=1 node "$PW_SRC_DIR/utils/doclint/generateApiJson.js" > "$PW_API_JSON"; then
        echo "Failed to generate api.json from $PW_SRC_DIR (a microsoft/playwright checkout at v${driver_version}?)" >&2
        exit 1
    fi
fi
export PW_API_JSON

function update_api {
    echo "Generating $1"
    file_name="$1"
    generate_script="$2"
    git checkout HEAD -- "$file_name"

    if PYTHONIOENCODING=utf-8 python "$generate_script" > .x; then
        mv .x "$file_name"
        pre-commit run --files $file_name
        echo "Regenerated APIs"
    else
        echo "Exited due to errors"
        exit 1
    fi
}

update_api "playwright/sync_api/_generated.py" "scripts/generate_sync_api.py"
update_api "playwright/async_api/_generated.py" "scripts/generate_async_api.py"

playwright install

python scripts/update_versions.py
