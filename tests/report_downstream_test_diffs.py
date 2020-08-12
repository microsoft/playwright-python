import argparse
import json
import os
import re
import subprocess
import tempfile
from collections import namedtuple

TestCase = namedtuple("TestCase", ["api", "file", "test"])


def pytest_test_cases():
    p = subprocess.run(
        ["pytest", "--browser", "chromium", "--collect-only", "-q"],
        stdout=subprocess.PIPE,
    )
    regex = (
        r"tests/(?P<api>a?sync)/test_(?P<file>.*)\.py::test_(?P<test>.*)\[chromium\]"
    )
    matches = re.finditer(regex, p.stdout.decode(), re.MULTILINE)
    for match in matches:
        yield TestCase(
            match.group("api"), match.group("file"), match.group("test"),
        )


def jest_test_cases(playwright_js_path):
    env = os.environ.copy()
    env["REPORT_ONLY"] = "true"
    with tempfile.NamedTemporaryFile() as results:
        subprocess.run(
            ["npx", "jest", "--json", "--outputFile", results.name],
            env=env,
            cwd=playwright_js_path,
            stderr=subprocess.DEVNULL,
        )

        for test_suite in json.load(results)["testResults"]:
            regex = r"(.*/)?(?P<file>[^/]+)\.spec\.[jt]s$"
            file = re.match(regex, test_suite["name"]).group("file")
            for assertion in test_suite["assertionResults"]:
                yield TestCase("sync", normalized(file), normalized(assertion["title"]))
                yield TestCase(
                    "async", normalized(file), normalized(assertion["title"])
                )


def normalized(original):
    return re.sub(r"[^a-z_]", "_", original, flags=re.IGNORECASE)


def main():
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
        javascript_tests = set([x for x in javascript_tests if x[0] == args.api])

    missing = javascript_tests.difference(python_tests)
    found = javascript_tests.intersection(python_tests)

    print("MISSING, MISPELLED, OR MISNAMED:")
    for (api, file, test) in sorted(missing):
        print(f"{api}/test_{file}.py::test_{test}")

    print(f"\nMissing: {len(missing)}, Found: {len(found)}")


if __name__ == "__main__":
    main()
