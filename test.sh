#!/usr/bin/env bash
# Runs the tests of both implementations under xvfb, with one worker for every two
# cores: playwright/_impl (v1) on tests/sync and tests/async (the older tests), then
# playwright/_impl_v2 (PW_IMPL=v2) on tests/sync and tests/async (the older tests
# and the ports of the upstream tests). On a terminal, the progress is one status line
# (scripts/pytest_line_reporter.py), and the summary lists only failures and errors,
# without the warnings.
# Usage: ./test.sh [chromium|firefox|webkit] [extra pytest args]
set -u
cd "$(dirname "$0")"
browser=chromium
case "${1:-}" in chromium|firefox|webkit) browser=$1; shift ;; esac
workers=$(( $(nproc) / 2 ))
(( workers < 1 )) && workers=1
python=python
[ -x env/bin/python ] && python=env/bin/python
export PYTHONPATH="scripts${PYTHONPATH:+:$PYTHONPATH}"
# --maxschedchunk=1: a worker gets one test at a time, as soon as it is free, so
# that the slow tests at the end of the collection spread over all workers.
args=(--browser "$browser" -n "$workers" --maxschedchunk=1 --timeout 120 --timeout-method thread -p pytest_line_reporter -rfE --disable-warnings)
status=0
xvfb-run -a "$python" -m pytest tests/sync "${args[@]}" "$@" || status=$?
xvfb-run -a "$python" -m pytest tests/async "${args[@]}" "$@" || status=$?
PW_IMPL=v2 xvfb-run -a "$python" -m pytest tests/sync "${args[@]}" "$@" || status=$?
PW_IMPL=v2 xvfb-run -a "$python" -m pytest tests/async "${args[@]}" "$@" || status=$?
exit $status
