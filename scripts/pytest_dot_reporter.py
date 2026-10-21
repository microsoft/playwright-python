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

"""A pytest reporter that prints one character per test, like Playwright's dot reporter.

Load it with `-p pytest_dot_reporter` (scripts/ on PYTHONPATH); CI runs the suites
with it. Each test is one character: `·` passed, `F` failed, `E` failed in a fixture,
`°` skipped, `x` failed as expected, `X` passed unexpectedly, `×` failed and to be run
again. Each failure prints in full as soon as it happens, between the dots, so that
the log of a run that is cut short still has it; the end summary lists the failures
again, one line each. Unlike the line reporter, it does not need a terminal.
"""

from typing import Dict, Optional, Tuple

import pytest
from _pytest.terminal import TerminalReporter

Location = Tuple[str, Optional[int], str]

_LINE_WIDTH = 80

# The character of each test outcome, and its colors.
_MARKS: Dict[str, Tuple[str, Dict[str, bool]]] = {
    "passed": ("·", {"green": True}),
    "failed": ("F", {"red": True, "bold": True}),
    "error": ("E", {"red": True, "bold": True}),
    "skipped": ("°", {"yellow": True}),
    "xfailed": ("x", {"yellow": True}),
    "xpassed": ("X", {"yellow": True}),
    "rerun": ("×", {"light": True}),
}


class DotStatus:
    """Takes over the per-test output of the terminal reporter."""

    def __init__(self, reporter: TerminalReporter) -> None:
        self._reporter = reporter
        self._column = 0

    def pytest_runtest_logstart(self, nodeid: str, location: Location) -> None:
        pass

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        reporter = self._reporter
        reporter._tests_ran = True
        category, letter, _ = reporter.config.hook.pytest_report_teststatus(
            report=report, config=reporter.config
        )
        reporter._add_stats(category, [report])
        if report.failed or category == "rerun":
            self._print_failure(report, category)
        if not letter:
            # A fixture that ran: the test gets its character from its call.
            return
        if self._column == _LINE_WIDTH:
            reporter._tw.line()
            self._column = 0
        mark, markup = _MARKS.get(category, (letter[:1], {}))
        reporter._tw.write(mark, **markup)
        reporter._tw.flush()
        self._column += 1
        # Start the next output of the reporter on a new line.
        reporter.currentfspath = -2

    def pytest_runtest_logfinish(self, nodeid: str, location: Location) -> None:
        pass

    def summary_failures(self) -> None:
        # The failures were printed as they happened.
        pass

    def summary_errors(self) -> None:
        pass

    def _print_failure(self, report: pytest.TestReport, category: str) -> None:
        # As summary_errors() and summary_failures() print it, on a line of its own.
        reporter = self._reporter
        headline = reporter._getfailureheadline(report)
        if category == "rerun":
            headline = f"RERUN {headline}"
        elif report.when != "call":
            headline = f"ERROR at {report.when} of {headline}"
        reporter.write_sep("_", headline, red=True, bold=True)
        reporter._outrep_summary(report)
        reporter._tw.flush()
        self._column = 0


@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config) -> None:
    reporter = config.pluginmanager.getplugin("terminalreporter")
    if not isinstance(reporter, TerminalReporter) or hasattr(config, "workerinput"):
        return
    # Keep the reporter object, which xdist already holds. Replace its per-test hooks
    # and its failure sections with DotStatus, then register it again so that pluggy
    # calls the replacements.
    status = DotStatus(reporter)
    config.pluginmanager.unregister(reporter)
    for name in (
        "pytest_runtest_logstart",
        "pytest_runtest_logreport",
        "pytest_runtest_logfinish",
        "summary_failures",
        "summary_errors",
    ):
        setattr(reporter, name, getattr(status, name))
    config.pluginmanager.register(reporter, "terminalreporter")
