#!/bin/bash

python scripts/update_versions.py

function update_api {
    echo "Generating $1"
    file_name="$1"
    generate_script="$2"
    git checkout HEAD -- "$file_name"

    python "$generate_script" > .x

    mv .x "$file_name"
    pre-commit run --files $file_name
}

update_api "playwright/sync_api.py" "scripts/generate_sync_api.py"
update_api "playwright/async_api.py" "scripts/generate_async_api.py"

echo "Regenerated APIs"
