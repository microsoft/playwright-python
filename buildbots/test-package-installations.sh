#!/bin/bash

tmpdir=$(mktemp -d)
base_dir=$(pwd)
set -e

# Cleanup to ensure we start fresh
echo "Deleting driver and browsers from base installation"
rm -rf driver
rm -rf playwright
rm -rf ~/.cache/ms-playwright

cp buildbots/assets/stub.py "$tmpdir/main.py"

cd $tmpdir
echo "Creating virtual environment"
virtualenv env
source env/bin/activate
echo "Installing Playwright Python via Wheel"
pip install "$(echo $base_dir/dist/playwright*manylinux1*.whl)"
echo "Installing browsers"
python -m playwright install
echo "Running basic tests"
python "main.py"
cd -

test -f "$tmpdir/chromium.png"
test -f "$tmpdir/firefox.png"
test -f "$tmpdir/webkit.png"
echo "Passed package installation tests successfully"
