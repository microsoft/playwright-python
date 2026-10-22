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

"""Manage .upstream/, the microsoft/playwright checkout that this repository is built from.

DRIVER_VERSION holds one microsoft/playwright commit. .upstream/ (gitignored) is a
full clone of microsoft/playwright, checked out at that commit. The wheel build
builds the driver from it (setup.py runs scripts/build_driver.py), and
scripts/update_api.sh generates the API from it. Both stop when .upstream/ is not
at the commit in DRIVER_VERSION; run `checkout` then.

Usage::

    python scripts/upstream.py checkout          # clone .upstream/ the first time; check out DRIVER_VERSION
    python scripts/upstream.py pin <ref>         # move DRIVER_VERSION to a branch, a tag or a commit,
                                                 # and check it out
    python scripts/upstream.py changes [<from>]  # list what changed upstream since <from> (default:
                                                 # DRIVER_VERSION at HEAD), with the Python files to port it to
    python scripts/upstream.py resolve <ref>     # print the commit of a branch, a tag or a commit

Apart from git, this needs only the Python standard library.
"""

import ast
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from check_test_registry import Entry, Rule, read_rules

REPO_ROOT = Path(__file__).resolve().parent.parent
UPSTREAM_DIR = REPO_ROOT / ".upstream"
UPSTREAM_URL = "https://github.com/microsoft/playwright.git"
DRIVER_VERSION = REPO_ROOT / "DRIVER_VERSION"

_COMMIT = re.compile(r"^[0-9a-f]{40}$")

# The upstream code that playwright/_impl ports, line by line.
CLIENT_PATHS = [
    "packages/playwright-core/src/client",
    "packages/playwright-core/src/outofprocess.ts",
]
SHARED_PATHS = ["packages/isomorphic", "packages/protocol/src", "packages/utils"]
# The upstream files that scripts/update_api.sh generates the Python files from, and
# the files that upstream generates from the protocol spec (utils/generate_channels.js),
# as update_api.sh generates their Python counterparts.
GENERATED_FROM_PATHS = ["docs/src/api", "packages/protocol/spec", "tests/registry.md"]
UPSTREAM_GENERATED = [
    "packages/isomorphic/protocolMetainfo.ts",
    "packages/playwright-core/src/client/channels.d.ts",
    "packages/protocol/src/structs.d.ts",
    "packages/protocol/src/validator.ts",
]
TEST_PATHS = ["tests/page", "tests/library"]
ASSET_PATHS = ["tests/assets"]


def _git(*args: str, cwd: Path = UPSTREAM_DIR, capture: bool = True) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE if capture else None,
        )
    except FileNotFoundError:
        raise SystemExit("git was not found on PATH.")
    except subprocess.CalledProcessError as error:
        raise SystemExit(
            f"git {' '.join(args)} failed with exit code {error.returncode}"
        )
    return result.stdout.strip() if capture else ""


def _has_commit(commit: str) -> bool:
    return (
        subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=UPSTREAM_DIR,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def read_pin() -> str:
    pin = DRIVER_VERSION.read_text().strip()
    if not _COMMIT.match(pin):
        raise SystemExit(
            f"{DRIVER_VERSION} must hold one microsoft/playwright commit (40 hex digits), got {pin!r}"
        )
    return pin


def head() -> str:
    return _git("rev-parse", "HEAD")


def local_changes() -> bool:
    return bool(_git("status", "--porcelain"))


def fetch(commit: str) -> None:
    if _has_commit(commit):
        return
    _git("fetch", "--quiet", "--tags", "origin", capture=False)
    if not _has_commit(commit):
        # A commit that no branch or tag reaches any more, for example on a deleted branch.
        _git("fetch", "--quiet", "origin", commit, capture=False)


def checkout(commit: Optional[str] = None) -> str:
    """Check out commit (default: DRIVER_VERSION) in .upstream/, after cloning it the first time."""
    commit = commit or read_pin()
    cloned = False
    if not (UPSTREAM_DIR / ".git").exists():
        print(f"Cloning {UPSTREAM_URL} into {UPSTREAM_DIR}", flush=True)
        _git(
            "clone",
            "--no-checkout",
            UPSTREAM_URL,
            str(UPSTREAM_DIR),
            cwd=REPO_ROOT,
            capture=False,
        )
        cloned = True
    if not cloned and head() == commit:
        print(f"{UPSTREAM_DIR} is at {commit}", flush=True)
        return commit
    if not cloned and local_changes():
        raise SystemExit(
            f"{UPSTREAM_DIR} has local changes. Commit or discard them before checking out {commit}."
        )
    fetch(commit)
    _git("checkout", "--quiet", "--detach", commit, capture=False)
    print(f"{UPSTREAM_DIR} is at {commit}", flush=True)
    return commit


def require_checkout() -> str:
    """Return the commit in DRIVER_VERSION; stop unless .upstream/ is checked out at it."""
    commit = read_pin()
    if not (UPSTREAM_DIR / ".git").exists() or head() != commit:
        raise SystemExit(
            f"{UPSTREAM_DIR} is not at {commit}, the commit in DRIVER_VERSION. "
            "Run: python scripts/upstream.py checkout"
        )
    return commit


def resolve(ref: str) -> str:
    """Return the commit of a branch, a tag or a commit of microsoft/playwright."""
    if _COMMIT.match(ref):
        return ref
    # "^{}" is the commit that an annotated tag points to.
    names = [f"refs/tags/{ref}^{{}}", f"refs/tags/{ref}", f"refs/heads/{ref}"]
    refs: Dict[str, str] = {}
    for line in _git("ls-remote", UPSTREAM_URL, *names, cwd=REPO_ROOT).splitlines():
        commit, name = line.split("\t")
        refs[name] = commit
    for name in names:
        if name in refs:
            return refs[name]
    raise SystemExit(f"{ref} is not a branch, a tag or a full commit of {UPSTREAM_URL}")


def pin(ref: str) -> None:
    old = read_pin()
    new = resolve(ref)
    checkout(new)
    DRIVER_VERSION.write_text(new + "\n")
    print(f"DRIVER_VERSION: {old} -> {new}")


def _python_ports() -> Dict[str, List[str]]:
    """Map each upstream file to the Python modules whose docstring says that they port it."""
    ports: Dict[str, List[str]] = defaultdict(list)
    for module in sorted((REPO_ROOT / "playwright" / "_impl").rglob("*.py")):
        docstring = ast.get_docstring(ast.parse(module.read_text(encoding="utf-8")))
        for path in re.findall(r"packages/[\w./-]+\.ts", docstring or ""):
            ports[path].append(module.relative_to(REPO_ROOT).as_posix())
    return ports


def _python_test_file(path: str, rules: List[Rule]) -> Optional[str]:
    # tests/page/page-check.spec.ts -> tests/{async,sync}/page/test_page_check.py
    if not path.endswith(".spec.ts"):
        return None
    file = path.split("/", 1)[1].removesuffix(".spec.ts")
    # A rule of tests/upstream_not_ported.txt that covers the whole file.
    rule = next((r for r in rules if r.matches(Entry("", file, "", 1))), None)
    if rule:
        return f"not ported: {rule.reason}"
    directory, name = file.rsplit("/", 1)
    return f"tests/{{async,sync}}/{directory}/test_{re.sub(r'[^A-Za-z0-9]+', '_', name)}.py"


def _golden_file(path: str) -> Optional[str]:
    # tests/page/page-screenshot.spec.ts-snapshots/screenshot-chromium.png
    #   -> tests/golden-chromium/screenshot.png
    match = re.fullmatch(
        r"tests/.+\.spec\.ts-snapshots/(.+)-(chromium|firefox|webkit)(\.\w+)", path
    )
    if not match or match[1].endswith("-bidi"):
        return None  # The BiDi and the Firefox Nightly images are not used.
    return f"tests/golden-{match[2]}/{match[1]}{match[3]}"


def changes(since: Optional[str]) -> None:
    new = require_checkout()
    old = (
        resolve(since) if since else _git("show", "HEAD:DRIVER_VERSION", cwd=REPO_ROOT)
    )
    if old == new:
        print(f"DRIVER_VERSION is {new} at HEAD too; pass the commit to compare with.")
        return
    fetch(old)
    count = _git("rev-list", "--count", f"{old}..{new}")
    print(f"microsoft/playwright {old[:10]}..{new[:10]}: {count} commits")

    def diff(paths: Sequence[str]) -> List[str]:
        # One row per file: "M path", "A path", "D path" or "R old -> new".
        output = _git("diff", "--name-status", "--find-renames", old, new, "--", *paths)
        rows: List[str] = []
        for line in output.splitlines():
            status, *names = line.split("\t")
            rows.append(f"{status[0]} {' -> '.join(names)}")
        return rows

    def section(title: str, rows: List[str]) -> None:
        if rows:
            print(f"\n{title}")
            for row in rows:
                print(f"  {row}")

    ports = _python_ports()
    client: List[str] = []
    shared: List[str] = []
    for row in diff(CLIENT_PATHS + SHARED_PATHS):
        names = row[2:].split(" -> ")
        if names[-1] in UPSTREAM_GENERATED:
            continue
        target = ", ".join(ports.get(names[-1]) or ports.get(names[0]) or [])
        if target:
            client.append(f"{row}  =>  {target}")
        elif any(names[-1].startswith(path) for path in CLIENT_PATHS):
            client.append(f"{row}  =>  (no Python port yet)")
        else:
            shared.append(row)
    rules = read_rules([])
    tests: List[str] = []
    for row in diff(TEST_PATHS):
        path = row[2:].split(" -> ")[-1]
        test_file = _python_test_file(path, rules) or _golden_file(path)
        tests.append(f"{row}  =>  {test_file}" if test_file else row)

    section(
        "Client: port each hunk line by line (playwright/_impl/transform.md)", client
    )
    section(
        "Shared code that Python does not port: port it if the client starts to use it",
        shared,
    )
    section(
        "Tests: port each hunk line by line, async and sync (tests/transform.md);"
        " copy each snapshot image to its golden file",
        tests,
    )
    section("Test assets: copy to tests/assets", diff(ASSET_PATHS))
    section(
        "Generated: scripts/update_api.sh generates the Python files",
        diff(GENERATED_FROM_PATHS + UPSTREAM_GENERATED),
    )


def main(argv: List[str]) -> None:
    command, args = (argv[0], argv[1:]) if argv else ("", [])
    if command == "checkout" and not args:
        checkout()
    elif command == "pin" and len(args) == 1:
        pin(args[0])
    elif command == "changes" and len(args) <= 1:
        changes(args[0] if args else None)
    elif command == "resolve" and len(args) == 1:
        print(resolve(args[0]))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
