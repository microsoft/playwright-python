#!/bin/bash

python scripts/update_versions.py

function update_api {
    echo "Generating $1"
    file_name="$1"
    generate_script="$2"
    git checkout HEAD -- "$file_name"

    if python "$generate_script" > .x; then
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
