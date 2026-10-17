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

"""Checks the ported tests against the upstream test registry.

tests/upstream_registry.md is a copy of tests/registry.md in microsoft/playwright.
It lists every upstream test in tests/page and tests/library with its identifier
(for example CH-001). Each of those tests must be either:

- ported, once in tests/async and once in tests/sync (under page/ or library/), as a
  function named test_<ID>_<title>, for example test_CH_001_should_check_the_box; or
- listed in tests/upstream_not_ported.txt, with the reason.

The name is made from the identifier and the title, with the describe titles first:
the "{a, b}" variants of a test that a loop declares are dropped, camelCase becomes
snake_case, and each run of other characters becomes one underscore.

Usage:
    python scripts/check_test_registry.py             # fails on any problem
    python scripts/check_test_registry.py --report    # prints the coverage per subsystem
    python scripts/check_test_registry.py --missing CH page/page-check
                                                      # lists the tests to port
"""

import argparse
import ast
import fnmatch
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "tests" / "upstream_registry.md"
NOT_PORTED = ROOT / "tests" / "upstream_not_ported.txt"
FLAVORS = ("async", "sync")
SUITE_DIRS = ("page", "library")

_ROW = re.compile(
    r"^\| `(?P<id>[A-Z]{2}-(?:[A-Z]{2,3}-)?\d{3})` \| `(?P<file>[^`]+)` \| "
    r"(?P<title>.*?)(?: \*\((?P<copies>\d+) copies\)\*)? \|$"
)
_SUBSYSTEM = re.compile(r"^\| `(?P<code>[A-Z]{2})` \| (?P<name>[^|]+?) \|")
_TEST_ID = re.compile(r"^test_(?P<id>[A-Z]{2}(?:_[A-Z]{2,3})?_\d{3})(?:_|$)")


@dataclass
class Entry:
    id: str
    file: str  # upstream path relative to tests/, without .spec.ts
    title: str  # describe titles and the title, joined with " › "
    copies: int

    @property
    def code(self) -> str:
        return self.id[:2]

    @property
    def expected_name(self) -> str:
        title = self.title
        if self.copies > 1:
            title = re.sub(r"\{[^{}]*\}", " ", title)
        name = f"test_{self.id.replace('-', '_')}"
        suffix = slug(title)
        return f"{name}_{suffix}" if suffix else name


def slug(text: str) -> str:
    text = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", text)
    text = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", text)
    text = re.sub(r"[^A-Za-z0-9]+", "_", text)
    return text.strip("_").lower()


def unescape_markdown(text: str) -> str:
    return re.sub(r"\\([\\`*_\[\]<>|])", r"\1", text)


def read_registry() -> Tuple[Dict[str, Entry], Dict[str, str]]:
    entries: Dict[str, Entry] = {}
    subsystems: Dict[str, str] = {}
    for line in REGISTRY.read_text(encoding="utf-8").splitlines():
        row = _ROW.match(line)
        if row:
            file = row["file"]
            if file.endswith(".spec.ts"):
                file = file[: -len(".spec.ts")]
            entries[row["id"]] = Entry(
                row["id"],
                file,
                unescape_markdown(row["title"]),
                int(row["copies"] or 1),
            )
            continue
        subsystem = _SUBSYSTEM.match(line)
        if subsystem:
            subsystems[subsystem["code"]] = subsystem["name"]
    return entries, subsystems


@dataclass
class Rule:
    line: int
    selector: str
    reason: str

    def matches(self, entry: Entry) -> bool:
        if re.fullmatch(r"[A-Z]{2}-(?:[A-Z]{2,3}-)?\d{3}", self.selector):
            return entry.id == self.selector
        if re.fullmatch(r"[A-Z]{2}", self.selector):
            return entry.code == self.selector
        return fnmatch.fnmatchcase(entry.file, self.selector)


def read_rules(problems: List[str]) -> List[Rule]:
    rules = []
    for number, line in enumerate(
        NOT_PORTED.read_text(encoding="utf-8").splitlines(), 1
    ):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(None, 1)
        if len(parts) < 2:
            problems.append(f"{NOT_PORTED.name}:{number}: the rule has no reason")
            continue
        rules.append(Rule(number, parts[0], parts[1]))
    return rules


@dataclass
class PortedTest:
    flavor: str
    path: Path
    line: int
    name: str


def read_ported_tests(problems: List[str]) -> Dict[str, Dict[str, List[PortedTest]]]:
    """Returns {flavor: {id: [tests]}}."""
    ported: Dict[str, Dict[str, List[PortedTest]]] = {
        f: defaultdict(list) for f in FLAVORS
    }
    for flavor in FLAVORS:
        for suite_dir in SUITE_DIRS:
            for path in sorted(
                (ROOT / "tests" / flavor / suite_dir).rglob("test_*.py")
            ):
                try:
                    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
                except SyntaxError as error:
                    problems.append(
                        f"{path.relative_to(ROOT)}:{error.lineno}: {error.msg}"
                    )
                    continue
                for node in tree.body:
                    if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        continue
                    if not node.name.startswith("test_"):
                        continue
                    test = PortedTest(
                        flavor, path.relative_to(ROOT), node.lineno, node.name
                    )
                    match = _TEST_ID.match(node.name)
                    if not match:
                        problems.append(
                            f"{test.path}:{test.line}: {node.name} does not start with a "
                            "registry identifier, for example test_CH_001_"
                        )
                        continue
                    ported[flavor][match["id"].replace("_", "-")].append(test)
    return ported


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--report", action="store_true", help="print the coverage per subsystem"
    )
    parser.add_argument(
        "--missing",
        nargs="*",
        metavar="FILTER",
        help="list the tests to port; a filter is a subsystem code or an upstream file glob",
    )
    args = parser.parse_args()

    problems: List[str] = []
    entries, subsystems = read_registry()
    rules = read_rules(problems)
    ported = read_ported_tests(problems)

    not_ported: Dict[str, Rule] = {}
    used_rules: Set[int] = set()
    for entry in entries.values():
        for rule in rules:
            if rule.matches(entry):
                not_ported.setdefault(entry.id, rule)
                used_rules.add(rule.line)
    for rule in rules:
        if rule.line not in used_rules:
            problems.append(
                f"{NOT_PORTED.name}:{rule.line}: {rule.selector} matches no registry test"
            )

    missing: Dict[str, List[Entry]] = {flavor: [] for flavor in FLAVORS}
    for flavor in FLAVORS:
        for test_id, tests in sorted(ported[flavor].items()):
            registered = entries.get(test_id)
            for test in tests:
                where = f"{test.path}:{test.line}"
                if not registered:
                    problems.append(f"{where}: {test_id} is not in {REGISTRY.name}")
                elif test.name != registered.expected_name:
                    problems.append(
                        f"{where}: {test.name} should be named {registered.expected_name}"
                    )
            if registered and test_id in not_ported:
                problems.append(
                    f"{tests[0].path}:{tests[0].line}: {test_id} is ported, but "
                    f"{NOT_PORTED.name}:{not_ported[test_id].line} lists it as not ported"
                )
            if len(tests) > 1:
                others = ", ".join(f"{t.path}:{t.line}" for t in tests[1:])
                problems.append(
                    f"{tests[0].path}:{tests[0].line}: {test_id} is also defined at {others}"
                )
        for entry in entries.values():
            if entry.id not in ported[flavor] and entry.id not in not_ported:
                missing[flavor].append(entry)

    if args.missing is not None:
        filters = args.missing

        def selected(entry: Entry) -> bool:
            return not filters or any(
                entry.code == f or fnmatch.fnmatchcase(entry.file, f) for f in filters
            )

        for flavor in FLAVORS:
            for entry in missing[flavor]:
                if selected(entry):
                    print(
                        f"{flavor:5} {entry.id:10} {entry.file}.spec.ts  {entry.expected_name}"
                    )
        return 0

    if args.report:
        print(
            f"{'code':4} {'subsystem':34} {'tests':>5} {'n/a':>5} {'async':>5} {'sync':>5} {'todo':>5}"
        )
        totals = [0, 0, 0, 0, 0]
        by_code: Dict[str, List[Entry]] = defaultdict(list)
        for entry in entries.values():
            by_code[entry.code].append(entry)
        for code, name in subsystems.items():
            group = by_code.get(code, [])
            excluded = sum(1 for e in group if e.id in not_ported)
            done = [
                sum(1 for e in group if e.id in ported[flavor]) for flavor in FLAVORS
            ]
            todo = len(group) - excluded - min(done)
            row = [len(group), excluded, *done, todo]
            totals = [a + b for a, b in zip(totals, row)]
            print(f"{code:4} {name[:34]:34} " + " ".join(f"{value:5}" for value in row))
        print(f"{'':4} {'total':34} " + " ".join(f"{value:5}" for value in totals))

    for flavor in FLAVORS:
        if missing[flavor]:
            problems.append(
                f"{len(missing[flavor])} registry tests are neither in tests/{flavor} nor in "
                f"{NOT_PORTED.name}; list them with --missing"
            )
    for problem in problems:
        print(problem, file=sys.stderr)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
