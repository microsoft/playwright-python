import argparse
import json
import os
import re
import subprocess
import typing
from collections import namedtuple

from playwright._path_utils import get_file_dirname

_dirname = get_file_dirname()

TestCase = namedtuple("TestCase", ["api", "file", "test"])


def pytest_test_cases() -> typing.Generator[TestCase, None, None]:
    p = subprocess.run(
        ["pytest", "--browser", "chromium", "--collect-only", "-q"],
        cwd=_dirname / ".." / "tests",
        stdout=subprocess.PIPE,
        check=True,
    )
    regex = (
        r"tests/(?P<api>a?sync)/test_(?P<file>.*)\.py::test_(?P<test>.*)\[chromium\]"
    )
    matches = re.finditer(regex, p.stdout.decode(), re.MULTILINE)
    for match in matches:
        yield TestCase(
            match.group("api"),
            match.group("file"),
            match.group("test"),
        )


def jest_test_cases(playwright_js_path: str) -> typing.Generator[TestCase, None, None]:
    p = subprocess.run(
        [
            "node",
            os.path.join("test", "runner"),
            "test",
            "--trial-run",
            "--reporter",
            "json",
        ],
        cwd=playwright_js_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=True,
    )

    tests = json.loads(p.stdout.decode())
    for test in [*tests["pending"], *tests["passes"], *tests["failures"]]:
        regex = r"(.*/)?(?P<file>[^/]+)\.spec\.[jt]s$"

        match = re.match(regex, test["file"])
        if not match:
            continue

        file = match.group("file")

        yield TestCase("sync", normalized(file), normalized(test["title"]))
        yield TestCase("async", normalized(file), normalized(test["title"]))


def normalized(original: str) -> str:
    cleaned = re.sub(r"[^a-z0-9_]", "_", original, flags=re.IGNORECASE)
    cleaned = re.sub(r"[_]+", "_", cleaned)
    cleaned = cleaned.strip("_")
    return cleaned


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--playwright-js-path",
        type=str,
        help="path to playwright JavaScript directory",
        required=True,
    )
    parser.add_argument(
        "--api",
        type=str,
        help="filter test cases based on API",
        choices=["sync", "async"],
    )
    args = parser.parse_args()

    python_tests = set(pytest_test_cases())
    javascript_tests = set(jest_test_cases(args.playwright_js_path))

    if args.api:
        javascript_tests = set([x for x in javascript_tests if x.api == args.api])

    missing = javascript_tests.difference(python_tests)
    found = javascript_tests.intersection(python_tests)

    print("MISSING, MISPELLED, OR MISNAMED:")
    print("=" * 80)
    for (api, file, test) in sorted(missing):
        print(f"{api}/test_{file}.py::test_{test}")

    print(f"\nMissing: {len(missing)}, Found: {len(found)}")


if __name__ == "__main__":
    main()
