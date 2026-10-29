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

"""Build the Playwright driver bundles from .upstream/.

The driver is the playwright-core package of microsoft/playwright, built from
``.upstream/`` at the commit in ``DRIVER_VERSION``, plus the official Node.js binary
of ``NODE_VERSION``. ``setup.py`` runs this when it builds a wheel. It:

1. builds ``.upstream/`` with ``npm ci`` and ``npm run build`` (once per commit);
2. packs ``packages/playwright-core`` with ``npm pack``;
3. adds the Node.js binary of each platform, and writes
   ``driver/playwright-<commit>-<suffix>.zip``::

       node | node.exe   - the Node.js binary
       LICENSE           - the Node.js license
       package/**        - the playwright-core npm package

The ``any`` bundle, for the source distribution, has only ``package/**``: it runs
with the Node.js of ``PLAYWRIGHT_NODEJS_PATH``.

A bundle that exists is not built again. ``.upstream/`` must be checked out at the
commit in ``DRIVER_VERSION`` (``python scripts/upstream.py checkout``), with no local
changes. npm uses the registry and the credentials of a root-level ``.npmrc`` when
there is one, for example the one that the release pipeline writes to point at
the internal Azure Artifacts feed. Apart from git and Node.js/npm this needs only
the Python standard library.

Usage::

    python scripts/build_driver.py            # build every platform bundle
    python scripts/build_driver.py <suffix>   # build one bundle, e.g. mac-arm64
"""

import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Iterable, List, NamedTuple, Set

import upstream

REPO_ROOT = Path(__file__).resolve().parent.parent
DRIVER_DIR = REPO_ROOT / "driver"

NODEJS_DIST = "https://nodejs.org/dist"


class Platform(NamedTuple):
    suffix: str  # bundle suffix; matches the "zip_name" values in setup.py
    node_dir: str  # the nodejs.org archive name infix: node-v<ver>-<node_dir>; "" for no Node.js
    windows: bool


# Keep in sync with the "zip_name" values in setup.py.
PLATFORMS: List[Platform] = [
    Platform("mac", "darwin-x64", False),
    Platform("mac-arm64", "darwin-arm64", False),
    Platform("linux", "linux-x64", False),
    Platform("linux-arm64", "linux-arm64", False),
    Platform("win32_x64", "win-x64", True),
    Platform("win32_arm64", "win-arm64", True),
    Platform("any", "", False),  # the source distribution: no Node.js
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


def run_npm(args: List[str], cwd: Path) -> None:
    npm = "npm.cmd" if sys.platform == "win32" else "npm"
    env = dict(os.environ)
    npmrc = REPO_ROOT / ".npmrc"
    if npmrc.is_file():
        # The release pipeline writes the registry and its credentials here.
        env["npm_config_userconfig"] = str(npmrc)
    print(f"Running npm {' '.join(args)} in {cwd}", flush=True)
    try:
        subprocess.check_call([npm, *args], cwd=cwd, env=env)
    except FileNotFoundError:
        raise SystemExit(
            "npm was not found on PATH; Node.js/npm are required to build the driver."
        )
    except subprocess.CalledProcessError as error:
        raise SystemExit(
            f"npm {' '.join(args)} failed with exit code {error.returncode}"
        )


def build_playwright_core(commit: str, work_dir: Path) -> Path:
    """Build .upstream/ and extract its playwright-core package into work_dir."""
    if upstream.local_changes():
        raise SystemExit(
            f"{upstream.UPSTREAM_DIR} has local changes. The driver bundles are named "
            "after the commit, so build them from a clean checkout."
        )
    core_dir = upstream.UPSTREAM_DIR / "packages" / "playwright-core"
    # npm ci removes node_modules, and the stamp with it.
    stamp = upstream.UPSTREAM_DIR / "node_modules" / ".playwright-python-build"
    built = (
        stamp.is_file()
        and stamp.read_text().strip() == commit
        and (core_dir / "lib").is_dir()
    )
    if not built:
        run_npm(["ci", "--no-audit", "--no-fund"], upstream.UPSTREAM_DIR)
        run_npm(["run", "build"], upstream.UPSTREAM_DIR)
        stamp.write_text(commit + "\n")
    run_npm(["pack", "--pack-destination", str(work_dir)], core_dir)
    tgzs = list(work_dir.glob("playwright-core-*.tgz"))
    if len(tgzs) != 1:
        raise SystemExit(
            f"npm pack did not produce one playwright-core-*.tgz in {work_dir}"
        )
    tgz = tgzs[0]
    with tarfile.open(tgz, "r:gz") as tar:
        # npm tarballs nest every file under a top-level "package/" directory,
        # which is exactly the bundle layout we want.
        members = [
            m
            for m in tar.getmembers()
            if m.name == "package" or m.name.startswith("package/")
        ]
        if not members:
            raise SystemExit(f"No package/ entries found in {tgz.name}")
        _extract_members(tar, work_dir, members)
    tgz.unlink()
    # Upstream copies these into the package before it publishes it
    # (LICENCE_FILES in utils/workspace.js).
    for name in ("NOTICE", "LICENSE"):
        shutil.copyfile(upstream.UPSTREAM_DIR / name, work_dir / "package" / name)
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
    commit: str,
    node_version: str,
    package_dir: Path,
    work_dir: Path,
) -> None:
    bundle_dir = work_dir / platform.suffix
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True)
    if platform.node_dir:
        fetch_node(platform, node_version, bundle_dir, work_dir)
    shutil.copytree(package_dir, bundle_dir / "package")
    destination = DRIVER_DIR / f"playwright-{commit}-{platform.suffix}.zip"
    zip_bundle(bundle_dir, destination)
    shutil.rmtree(bundle_dir)
    print(f"Created {destination}")


def build(suffixes: Set[str]) -> None:
    commit = upstream.read_pin()
    node_version = read_pin("NODE_VERSION")
    DRIVER_DIR.mkdir(exist_ok=True)

    todo = [
        p
        for p in PLATFORMS
        if p.suffix in suffixes
        and not (DRIVER_DIR / f"playwright-{commit}-{p.suffix}.zip").exists()
    ]
    if not todo:
        print(
            f"Driver bundles for {commit} already present in {DRIVER_DIR}; nothing to do."
        )
        return

    upstream.require_checkout()
    with tempfile.TemporaryDirectory(prefix="pw-driver-") as tmp_name:
        work_dir = Path(tmp_name)
        package_dir = build_playwright_core(commit, work_dir)
        for platform in todo:
            assemble(platform, commit, node_version, package_dir, work_dir)


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
