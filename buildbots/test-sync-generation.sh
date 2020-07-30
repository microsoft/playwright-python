#!/bin/bash

function assert_script {
    newfile="$2"
    oldfile="playwright/$2"
    echo "Testing $newfile against $oldfile"

    python $1 > $newfile

    pre-commit run --files $newfile

    cmp $oldfile $newfile
    exit_code=$?
    rm $newfile
    return $exit_code
}

assert_script "scripts/generate_sync_api.py" "sync_api.py"
assert_script "scripts/generate_async_api.py" "async_api.py"
