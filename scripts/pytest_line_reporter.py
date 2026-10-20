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

"""A pytest reporter that redraws one status line, like Playwright's line reporter.

Load it with `-p pytest_line_reporter` (scripts/ on PYTHONPATH). The progress of the
tests is one status line. Each failure prints in full as soon as it happens, and the
status line continues below it; the end summary lists the failures again, one line each.
It does nothing when the output is not a terminal.
"""

from typing import Optional, Tuple

import pytest
from _pytest.terminal import TerminalReporter

_CLEAR_LINE = "\r\x1b[2K"

Location = Tuple[str, Optional[int], str]


class LineStatus:
    """Takes over the per-test output of the terminal reporter."""

    def __init__(self, reporter: TerminalReporter) -> None:
        self._reporter = reporter
        self._done = 0

    def pytest_runtest_logstart(self, nodeid: str, location: Location) -> None:
        pass

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        reporter = self._reporter
        reporter._tests_ran = True
        category, _, _ = reporter.config.hook.pytest_report_teststatus(
            report=report, config=reporter.config
        )
        reporter._add_stats(category, [report])
        if not report.failed:
            return
        # Replace the status line with the failure, as summary_errors() and
        # summary_failures() print it, then draw the status line again below it.
        reporter._tw.write(_CLEAR_LINE)
        reporter.currentfspath = None
        headline = reporter._getfailureheadline(report)
        if report.when != "call":
            headline = f"ERROR at {report.when} of {headline}"
        reporter.write_sep("_", headline, red=True, bold=True)
        reporter._outrep_summary(report)
        self._draw(report.nodeid)

    def pytest_runtest_logfinish(self, nodeid: str, location: Location) -> None:
        self._done += 1
        self._draw(nodeid)

    def summary_failures(self) -> None:
        # The failures were printed as they happened.
        pass

    def summary_errors(self) -> None:
        pass

    def _draw(self, nodeid: str) -> None:
        reporter = self._reporter
        session = reporter._session
        total = session.testscollected if session else 0

        def count(*categories: str) -> int:
            return sum(len(reporter.stats.get(c, [])) for c in categories)

        failed = count("failed", "error")
        status = (
            f"[{self._done}/{total}] passed {count('passed')}"
            + (f", failed {failed}" if failed else "")
            + f", skipped {count('skipped', 'xfailed')}"
        )
        line = status if self._done == total else f"{status}  {nodeid}"
        reporter._tw.write(_CLEAR_LINE + line[: reporter._tw.fullwidth - 1])
        reporter._tw.flush()
        # Start the next output of the reporter on a new line.
        reporter.currentfspath = -2


@pytest.hookimpl(trylast=True)
def pytest_configure(config: pytest.Config) -> None:
    reporter = config.pluginmanager.getplugin("terminalreporter")
    if (
        not isinstance(reporter, TerminalReporter)
        or hasattr(config, "workerinput")
        or not reporter.isatty()
    ):
        return
    # Keep the reporter object, which xdist already holds. Replace its per-test hooks
    # and its failure sections with LineStatus, then register it again so that pluggy
    # calls the replacements.
    status = LineStatus(reporter)
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
