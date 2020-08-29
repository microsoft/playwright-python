#!/bin/bash

base_dir=$(pwd)
set -e

# Cleanup to ensure we start fresh
echo "Deleting driver and browsers from base installation"
rm -rf playwright/driver
mv playwright playwright-gone
rm -rf ~/.cache/ms-playwright

function test_installation() {
    tmpdir=$(mktemp -d)
    echo "Testing package $1"
    cp buildbots/assets/stub.py "$tmpdir/main.py"

    cd $tmpdir
    echo "Creating virtual environment"
    virtualenv env
    source env/bin/activate
    echo "Installing Playwright Python via Wheel"
    pip install "$1"
    echo "Installing browsers"
    python -m playwright install
    echo "Running basic tests"
    python "main.py"
    cd -

    test -f "$tmpdir/chromium.png"
    test -f "$tmpdir/firefox.png"
    test -f "$tmpdir/webkit.png"
    rm -rf $tmpdir
    cd $base_dir
}

test_installation "$(echo $base_dir/dist/playwright*whl)"
test_installation "$(echo $base_dir/dist/playwright*\.tar\.gz)"

echo "Passed package installation tests successfully"
