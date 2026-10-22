#!/bin/bash

# The checks of a change, and the last step of a roll (the playwright-roll skill):
# - .upstream/ is at the commit in DRIVER_VERSION, with no local changes;
# - the generated files are what .upstream/ generates (scripts/update_api.sh);
# - pre-commit: the formatters, flake8, mypy and pyright, on every file;
# - the tests match the upstream test registry (scripts/check_test_registry.py).
# It stops at the first check that fails. Fix the cause and run it again.
set -e
cd "$(dirname "$0")/.."

pin="$(cat DRIVER_VERSION)"
if [[ "$(git -C .upstream rev-parse HEAD 2>/dev/null)" != "$pin" ]]; then
    echo ".upstream/ is not at $pin, the commit in DRIVER_VERSION. Run: python scripts/upstream.py checkout" >&2
    exit 1
fi
if [[ -n "$(git -C .upstream status --porcelain)" ]]; then
    echo ".upstream/ has local changes; discard them (git -C .upstream status)." >&2
    exit 1
fi

before="$(mktemp)"
trap 'rm -f "$before"' EXIT
git diff > "$before"
./scripts/update_api.sh
if ! git diff | cmp -s - "$before"; then
    echo "update_api.sh changed the generated files: they were not what .upstream/ generates." >&2
    echo "Keep its output; make a change in scripts/codegen/ or python_rules.js, not in a generated file." >&2
    exit 1
fi

pre-commit run --show-diff-on-failure --all-files
python scripts/check_test_registry.py
echo "All checks passed."
