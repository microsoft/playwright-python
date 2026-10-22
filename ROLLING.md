# Rolling to a new Playwright commit

`DRIVER_VERSION` holds the `microsoft/playwright` commit that the driver, the
generated API and the ported code come from. A roll moves it to a new commit and
ports what changed in between. Set up the repo first ([CONTRIBUTING.md](./CONTRIBUTING.md),
steps 1 and 2). The full process, for people and agents, is in
[.claude/skills/playwright-roll/SKILL.md](./.claude/skills/playwright-roll/SKILL.md).

1. **Pin** the new commit, a branch or a tag. This writes the commit to
   `DRIVER_VERSION` and checks it out in `.upstream/`.

   ```sh
   python scripts/upstream.py pin main
   python scripts/update_node_version.py
   ```

2. **Build** the driver and install the browsers.

   ```sh
   python -m build --wheel
   playwright install chromium firefox webkit
   ```

3. **Generate** the API, the protocol files and the test registry.

   ```sh
   ./scripts/update_api.sh
   ```

4. **Port** what changed upstream, line by line: the client into `playwright/_impl/`
   ([transform.md](./playwright/_impl/transform.md)), the tests into `tests/async/` and
   `tests/sync/` ([tests/transform.md](./tests/transform.md)).

   ```sh
   python scripts/upstream.py changes      # each changed upstream file, with its Python file
   ```

5. **Check**, then commit and open the PR.

   ```sh
   pre-commit run --all-files
   python scripts/check_test_registry.py
   ./test.sh
   python scripts/update_versions.py        # the browser versions in README.md
   ```
