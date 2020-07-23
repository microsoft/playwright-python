#!/bin/bash

newfile="sync.py"
oldfile="playwright/sync.py"

python scripts/generate_sync_api.py > $newfile

pre-commit run --files $newfile

cmp $oldfile $newfile
exit_code=$?

rm $newfile

exit $exit_code
