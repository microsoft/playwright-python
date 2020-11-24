#!/bin/bash

function assert_script {
    newfile="$2"
    oldfile="playwright/$2"
    echo "Testing $newfile against $oldfile"

    if ! python $1 > $newfile; then
      exit 1
    fi

    pre-commit run --files $newfile

    cmp $oldfile $newfile
    exit_code=$?
    rm $newfile
}

assert_script "scripts/generate_sync_api.py" "sync_api.py"
assert_script "scripts/generate_async_api.py" "async_api.py"
