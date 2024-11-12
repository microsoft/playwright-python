#!/bin/bash
set -e
set +x

if [[ ($1 == '--help') || ($1 == '-h') || ($1 == '') || ($2 == '') ]]; then
  echo "usage: $(basename $0) {--arm64,--amd64} {jammy,noble} playwright:localbuild-noble"
  echo
  echo "Build Playwright docker image and tag it as 'playwright:localbuild-noble'."
  echo "Once image is built, you can run it with"
  echo ""
  echo "  docker run --rm -it playwright:localbuild-noble /bin/bash"
  echo ""
  echo "NOTE: this requires on Playwright PIP dependencies to be installed"
  echo ""
  exit 0
fi

function cleanup() {
  rm -rf "dist/"
}

trap "cleanup; cd $(pwd -P)" EXIT
cd "$(dirname "$0")"

pushd ../../
for wheel in $(python setup.py --list-wheels); do
  PLAYWRIGHT_TARGET_WHEEL=$wheel python -m build --wheel
done
popd
mkdir dist/
cp ../../dist/*-manylinux*.whl dist/

PLATFORM=""
if [[ "$1" == "--arm64" ]]; then
  PLATFORM="linux/arm64";
elif [[ "$1" == "--amd64" ]]; then
  PLATFORM="linux/amd64"
else
  echo "ERROR: unknown platform specifier - $1. Only --arm64 or --amd64 is supported"
  exit 1
fi

docker build --platform "${PLATFORM}" -t "$3" -f "Dockerfile.$2" .
