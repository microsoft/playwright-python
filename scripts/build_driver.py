#!/usr/bin/env python3
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

"""Assemble the Playwright driver bundles from published artifacts.

Instead of building the driver from upstream source, this downloads the
already-published ``playwright-core`` npm package (pinned in ``DRIVER_VERSION``)
and the official Node.js binaries (pinned in ``NODE_VERSION``) and assembles
per-platform bundles into ``driver/playwright-<version>-<suffix>.zip``. The
layout mirrors what upstream's ``utils/build/build-playwright-driver.sh``
produces, which is what ``setup.py`` extracts into ``playwright/driver/`` when
building a wheel::

    node | node.exe   - the Node.js binary
    LICENSE           - the Node.js license
    package/**        - the playwright-core npm package

Unlike the old source build this needs no Node.js, npm, git or bash — only the
Python standard library.

Usage::

    scripts/build_driver.py            # assemble every platform bundle
    scripts/build_driver.py <suffix>   # assemble a single bundle, e.g. mac-arm64

``setup.py`` invokes the single-suffix form so a wheel build only downloads the
one Node.js binary it needs.
"""

import os
import shutil
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterable, List, NamedTuple, Set

REPO_ROOT = Path(__file__).resolve().parent.parent
DRIVER_DIR = REPO_ROOT / "driver"

NPM_REGISTRY = "https://registry.npmjs.org"
NODEJS_DIST = "https://nodejs.org/dist"


class Platform(NamedTuple):
    suffix: str  # bundle suffix; matches the "zip_name" values in setup.py
    node_dir: str  # the nodejs.org archive name infix: node-v<ver>-<node_dir>
    windows: bool


# Keep in sync with the "zip_name" values in setup.py.
PLATFORMS: List[Platform] = [
    Platform("mac", "darwin-x64", False),
    Platform("mac-arm64", "darwin-arm64", False),
    Platform("linux", "linux-x64", False),
    Platform("linux-arm64", "linux-arm64", False),
    Platform("win32_x64", "win-x64", True),
    Platform("win32_arm64", "win-arm64", True),
]


def read_pin(name: str) -> str:
    value = (REPO_ROOT / name).read_text().strip()
    if not value:
        raise SystemExit(f"{name} is empty or missing at {REPO_ROOT / name}")
    return value


def download(url: str, destination: Path) -> None:
    last_error: Exception = RuntimeError("no attempt made")
    for attempt in range(1, 6):
        try:
            print(f"Downloading {url}")
            with urllib.request.urlopen(url) as response:  # noqa: S310
                with open(destination, "wb") as out:
                    shutil.copyfileobj(response, out)
            return
        except Exception as error:  # noqa: BLE001
            last_error = error
            print(f"  attempt {attempt} failed: {error}")
            time.sleep(attempt)
    raise SystemExit(f"Failed to download {url}: {last_error}")


def _extract_members(
    tar: tarfile.TarFile, path: Path, members: List[tarfile.TarInfo]
) -> None:
    # filter="data" sanitizes paths (rejects "..", absolute names) while keeping
    # the read/write/execute bits we rely on. It is only available on 3.12+.
    if sys.version_info >= (3, 12):
        tar.extractall(path, members=members, filter="data")
    else:
        tar.extractall(path, members=members)  # noqa: S202


def _extract_tar_file(tar: tarfile.TarFile, name: str, destination: Path) -> None:
    member = tar.getmember(name)
    source = tar.extractfile(member)
    if source is None:
        raise SystemExit(f"{name} is not a regular file in the archive")
    with source, open(destination, "wb") as out:
        shutil.copyfileobj(source, out)
    # Preserve the executable bit so the Node.js binary stays runnable end to end:
    # setup.py's extractall() re-applies the mode it reads back from our zip.
    os.chmod(destination, member.mode & 0o777)


def _extract_zip_file(archive: zipfile.ZipFile, name: str, destination: Path) -> None:
    try:
        info = archive.getinfo(name)
    except KeyError:
        raise SystemExit(f"{name} not found in the archive")
    with archive.open(info) as source, open(destination, "wb") as out:
        shutil.copyfileobj(source, out)


def fetch_playwright_core(version: str, work_dir: Path) -> Path:
    """Download playwright-core@<version> and extract its package/ tree once."""
    url = f"{NPM_REGISTRY}/playwright-core/-/playwright-core-{version}.tgz"
    tgz = work_dir / f"playwright-core-{version}.tgz"
    download(url, tgz)
    with tarfile.open(tgz, "r:gz") as tar:
        # npm tarballs nest every file under a top-level "package/" directory,
        # which is exactly the bundle layout we want.
        members = [
            m
            for m in tar.getmembers()
            if m.name == "package" or m.name.startswith("package/")
        ]
        if not members:
            raise SystemExit(f"No package/ entries found in {url}")
        _extract_members(tar, work_dir, members)
    tgz.unlink()
    return work_dir / "package"


def fetch_node(
    platform: Platform, node_version: str, bundle_dir: Path, work_dir: Path
) -> None:
    """Download the Node.js build for a platform and place node + LICENSE in the bundle."""
    node_dir = f"node-v{node_version}-{platform.node_dir}"
    ext = "zip" if platform.windows else "tar.gz"
    url = f"{NODEJS_DIST}/v{node_version}/{node_dir}.{ext}"
    archive = work_dir / f"{node_dir}.{ext}"
    download(url, archive)
    if platform.windows:
        with zipfile.ZipFile(archive) as zf:
            _extract_zip_file(zf, f"{node_dir}/node.exe", bundle_dir / "node.exe")
            _extract_zip_file(zf, f"{node_dir}/LICENSE", bundle_dir / "LICENSE")
    else:
        with tarfile.open(archive, "r:gz") as tar:
            _extract_tar_file(tar, f"{node_dir}/bin/node", bundle_dir / "node")
            _extract_tar_file(tar, f"{node_dir}/LICENSE", bundle_dir / "LICENSE")
    archive.unlink()


def zip_bundle(bundle_dir: Path, destination: Path) -> None:
    files = sorted(p for p in bundle_dir.rglob("*") if p.is_file())
    tmp = destination.with_name(destination.name + ".tmp")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file in files:
            # ZipFile.write records the on-disk st_mode in external_attr, so the
            # node binary's executable bit survives into the bundle.
            zf.write(file, file.relative_to(bundle_dir).as_posix())
    os.replace(tmp, destination)


def assemble(
    platform: Platform,
    version: str,
    node_version: str,
    package_dir: Path,
    work_dir: Path,
) -> None:
    bundle_dir = work_dir / platform.suffix
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)
    fetch_node(platform, node_version, bundle_dir, work_dir)
    shutil.copytree(package_dir, bundle_dir / "package")
    destination = DRIVER_DIR / f"playwright-{version}-{platform.suffix}.zip"
    zip_bundle(bundle_dir, destination)
    shutil.rmtree(bundle_dir)
    print(f"Created {destination}")


def build(suffixes: Set[str]) -> None:
    version = read_pin("DRIVER_VERSION")
    node_version = read_pin("NODE_VERSION")
    DRIVER_DIR.mkdir(exist_ok=True)

    todo = [
        p
        for p in PLATFORMS
        if p.suffix in suffixes
        and not (DRIVER_DIR / f"playwright-{version}-{p.suffix}.zip").exists()
    ]
    if not todo:
        print(
            f"Driver bundles for {version} already present in {DRIVER_DIR}; nothing to do."
        )
        return

    with tempfile.TemporaryDirectory(prefix="pw-driver-") as tmp_name:
        work_dir = Path(tmp_name)
        package_dir = fetch_playwright_core(version, work_dir)
        for platform in todo:
            assemble(platform, version, node_version, package_dir, work_dir)


def main(argv: Iterable[str]) -> None:
    valid = {p.suffix for p in PLATFORMS}
    requested = set(argv)
    if requested:
        unknown = requested - valid
        if unknown:
            raise SystemExit(
                f"Unknown bundle suffix(es): {', '.join(sorted(unknown))}. "
                f"Valid suffixes: {', '.join(p.suffix for p in PLATFORMS)}"
            )
    else:
        requested = valid
    build(requested)


if __name__ == "__main__":
    main(sys.argv[1:])
