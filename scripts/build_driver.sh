#!/usr/bin/env bash
# Copyright (c) Microsoft Corporation.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Build the Playwright driver bundles from upstream source.
#
# This script checks out microsoft/playwright at the commit pinned in the
# DRIVER_SHA file (repo root) and runs upstream's
# utils/build/build-playwright-driver.sh. That script cross-builds the
# per-platform bundles, which this script stages into driver/ as
# playwright-<sha>-<suffix>.zip for setup.py to embed into the platform wheels.
#
# The pin is an immutable commit SHA (tags can be moved upstream) and lives in
# the neutral DRIVER_SHA file so setup.py and CI can read it without parsing
# this script. The SHA is baked into the staged bundle filenames, so the
# filename doubles as the build cache key: a roll changes DRIVER_SHA, which
# changes the filenames and invalidates the cache.
#
# A single host builds all platform bundles at once: the upstream script
# downloads the matching Node.js binary for each target, so the host platform
# does not constrain which bundles can be produced.
#
# This is intentionally a shell script (rather than language-specific code) so
# the same build step can be shared across the Playwright language forks.
#
# Usage: scripts/build_driver.sh   (reads the pin from DRIVER_SHA; no arguments)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DRIVER_DIR="$REPO_ROOT/driver"
SOURCE_DIR="$DRIVER_DIR/playwright-src"
PLAYWRIGHT_REPO="https://github.com/microsoft/playwright"

# The driver pin: an immutable commit in microsoft/playwright.
# microsoft/playwright @ main
EXPECTED_SHA="$(tr -d '[:space:]' < "$REPO_ROOT/DRIVER_SHA")"
if [[ -z "$EXPECTED_SHA" ]]; then
  echo "DRIVER_SHA is empty or missing at $REPO_ROOT/DRIVER_SHA" >&2
  exit 2
fi

# Bundle suffixes produced by utils/build/build-playwright-driver.sh. Keep in
# sync with the "zip_name" values in setup.py.
SUFFIXES=(mac mac-arm64 linux linux-arm64 win32_x64 win32_arm64)

bundles_present() {
  local suffix
  for suffix in "${SUFFIXES[@]}"; do
    [[ -f "$DRIVER_DIR/playwright-$EXPECTED_SHA-$suffix.zip" ]] || return 1
  done
  return 0
}

require_tools() {
  local missing=()
  local tool
  for tool in git node npm bash; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      missing+=("$tool")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "Building the Playwright driver from source requires the following tools," >&2
    echo "which were not found on PATH: ${missing[*]}." >&2
    echo "Install Node.js (with npm), git and bash, then retry. On Windows, run the" >&2
    echo "build from a bash shell (e.g. Git Bash)." >&2
    exit 1
  fi
}

checked_out_sha() {
  if [[ -d "$SOURCE_DIR/.git" ]]; then
    git -C "$SOURCE_DIR" rev-parse HEAD 2>/dev/null || true
  fi
}

clone_source() {
  # Reuse an existing checkout's git object store across rolls: only initialize
  # a fresh repo when one isn't already present, then fetch and check out the
  # pinned commit. This avoids re-cloning the repo (and re-running npm ci from
  # scratch) every time the pin changes.
  if [[ ! -d "$SOURCE_DIR/.git" ]]; then
    rm -rf "$SOURCE_DIR"
    mkdir -p "$SOURCE_DIR"
    git -C "$SOURCE_DIR" init -q
    git -C "$SOURCE_DIR" remote add origin "$PLAYWRIGHT_REPO"
  fi
  if [[ "$(checked_out_sha)" != "$EXPECTED_SHA" ]]; then
    echo "Fetching $PLAYWRIGHT_REPO at $EXPECTED_SHA"
    # Shallow-fetch a single commit. GitHub allows fetching an arbitrary commit
    # by SHA, so a full clone is unnecessary.
    git -C "$SOURCE_DIR" fetch --depth 1 origin "$EXPECTED_SHA"
    git -C "$SOURCE_DIR" checkout -q --detach FETCH_HEAD
  fi
  # Make sure we landed on exactly the pinned commit.
  if [[ "$(checked_out_sha)" != "$EXPECTED_SHA" ]]; then
    echo "Checked out commit '$(checked_out_sha)' but '$EXPECTED_SHA' was requested." >&2
    exit 1
  fi
}

build_source() {
  echo "Installing Playwright dependencies (npm ci)"
  (cd "$SOURCE_DIR" && npm ci)
  # Drop build outputs left over from a previously checked-out commit when the
  # checkout is reused across rolls (lib/ dirs are gitignored, so switching
  # commits doesn't clear them).
  echo "Cleaning previous build outputs (npm run clean)"
  (cd "$SOURCE_DIR" && npm run clean)
  echo "Building Playwright (npm run build)"
  (cd "$SOURCE_DIR" && npm run build)
  echo "Building driver bundles"
  (cd "$SOURCE_DIR" && bash utils/build/build-playwright-driver.sh)
}

copy_bundles() {
  local output_dir="$SOURCE_DIR/utils/build/output"
  # The output dir also holds build intermediates (downloaded Node.js binaries,
  # tgz archives, extracted package dirs), so copy only the bundles. Upstream
  # names them playwright-<version>-<suffix>.zip; restage each one with the pin
  # SHA in the name so the filename doubles as the build cache key.
  local suffix matches
  for suffix in "${SUFFIXES[@]}"; do
    matches=("$output_dir"/playwright-*-"$suffix".zip)
    if [[ ! -f "${matches[0]}" ]]; then
      echo "Expected driver bundle for '$suffix' was not produced in $output_dir" >&2
      exit 1
    fi
    cp "${matches[0]}" "$DRIVER_DIR/playwright-$EXPECTED_SHA-$suffix.zip"
  done
}

# Fast path: the bundles for this exact pin are already staged, so there is
# nothing to (re)build. This keeps repeat invocations cheap and lets consumers
# that only downloaded the prebuilt bundles skip the build entirely (no Node).
if bundles_present; then
  echo "Driver bundles for $EXPECTED_SHA already present in $DRIVER_DIR; skipping build."
  exit 0
fi

require_tools
clone_source
build_source
copy_bundles
