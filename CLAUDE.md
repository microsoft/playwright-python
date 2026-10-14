# CLAUDE.md

Guidance for Claude when working in this repository.

## What this is

Python bindings for [Playwright](https://playwright.dev). The Python client talks JSON over a pipe to the Node-based driver bundled in `playwright/driver/`. The pipe protocol is defined upstream in `packages/protocol/spec/*.yml`.

## Layout

- `playwright/_impl/` — hand-written client implementation (one module per object: `_browser.py`, `_page.py`, `_locator.py`, `_network.py`, etc.). Edit these to add or change behavior. Internal types are in `_internal_structures.py`.
- `playwright/async_api/_generated.py`, `playwright/sync_api/_generated.py`, and the public TypedDicts in `playwright/_impl/_api_structures.py` — **auto-generated** from the upstream API docs. Never edit by hand; rerun `./scripts/update_api.sh` after a roll or after changing `scripts/codegen/`.
- `scripts/codegen/generate_api.js` — the generator. A Node.js script that loads the upstream doc parser (`utils/doclint/api_parser.js`) from `$PW_SRC_DIR`, filters the docs for Python, and writes the whole public API: signatures, types, docstrings, event overloads, the calls into `_impl/`, and the TypedDicts. It does not read `_impl/`.
- `scripts/codegen/python_rules.js` — the Python facts that the docs do not contain (positional options, struct `total=`, hidden members and options). Policy: the shipped Python API wins; each entry is a candidate for an upstream docs fix, and the generator fails on entries that no longer match anything. Every entry needs a one-line rationale comment above it.
- `scripts/codegen/compare_api.py` — compares two generated files (signatures, annotations, call bodies, docstrings) and lists every difference. Use it to check that a generator change does not change the API.
- `tests/async/`, `tests/sync/` — pytest suites. Most new tests are added to the async file with a sync mirror.
- `DRIVER_VERSION` — the single source of truth for which Playwright release the driver is assembled from (one line, the `playwright-core` npm version, e.g. `1.61.0`, no `v` prefix). Read by `setup.py`, `scripts/build_driver.py`, and CI. The wheel build downloads `playwright-core` at this version from npm plus the matching Node.js binary and assembles the per-platform bundles — no source build. The version is baked into the staged bundle filenames (`driver/playwright-<version>-<suffix>.zip`), so it doubles as the build cache key.
- `NODE_VERSION` — the Node.js version bundled with the driver (one line, e.g. `24.16.0`). Maintained at roll time by `scripts/update_node_version.py` (latest LTS, mirroring upstream's `utils/build/update-playwright-node.mjs`).
- `scripts/build_driver.py` — assembles the per-platform driver bundles into `driver/` by downloading the `playwright-core` npm package (`DRIVER_VERSION`) and the official Node.js binaries (`NODE_VERSION`). Fetches `playwright-core` with `npm pack` (needs Node.js/npm on PATH; honours a root `.npmrc`) and the Node.js binaries over plain HTTP; invoked from `setup.py`'s `bdist_wheel` with the target platform's suffix (no arg builds all six).
- The API docs are **not** shipped in the bundle. `scripts/update_api.sh` reads them from a separate `microsoft/playwright` checkout (`$PW_SRC_DIR`) on the exact release branch for `DRIVER_VERSION`, never from a checkout on `main` or a feature branch. Needed only when regenerating the API, never at runtime.
- `ROLLING.md`, `CONTRIBUTING.md` — human-facing setup and roll docs.

## Setup

`CONTRIBUTING.md` has the full sequence. The short version (needs Node.js and npm for the driver build):

```sh
python3 -m venv env && source env/bin/activate
pip install --upgrade pip
pip install -r local-requirements.txt
pip install -e .
python -m build --wheel        # downloads playwright-core @ DRIVER_VERSION + Node.js and assembles the driver
pre-commit install
```

If the system lacks `python3-venv`, `uv venv env` is an acceptable substitute (then `uv pip install --python env/bin/python --upgrade pip`).

## Common commands

- Regenerate `_generated.py`: `./scripts/update_api.sh` (runs codegen + pre-commit on the generated files).
- Lint everything: `pre-commit run --all-files`.
- Type-check: `mypy playwright`.
- Run tests: `pytest --browser chromium [-k name]`. Browsers are installed via `playwright install chromium` (do **not** use `--with-deps`, which requires sudo).

The public API comes from the upstream docs. After `./scripts/update_api.sh`, run `mypy playwright`: the generated classes type their `_impl_obj`, so every new member or option that `_impl/` does not implement yet is a mypy error in `_generated.py`. Fix it in `_impl/`, or record a justified difference in `scripts/codegen/python_rules.js` — not by hand-editing `_generated.py`.

## Rolling Playwright to a new version

This is the recurring high-stakes task. Use the dedicated skill:

→ **[`.claude/skills/playwright-roll/SKILL.md`](.claude/skills/playwright-roll/SKILL.md)**

It documents the full process: the upstream commit-range diff over `docs/src/api/`, how to classify each commit (PORT / MISMATCH / N/A), how to handle the `langs:` filter, the recurring failure modes, and the tests/sync-mirroring conventions.

## Working on PRs

- Never post comments, replies, or reviews on GitHub PRs/issues under my account without my explicit approval. Draft the proposed text and wait for me to approve before sending.

## House style

- Don't hand-edit generated files.
- Don't add `# type: ignore` or modify `_generated.py` to silence pyright; fix the source of the mismatch.
- New public methods on impl classes need a sync test mirror under `tests/sync/`.
- Keep `scripts/codegen/python_rules.js` minimal — every entry needs a one-line rationale comment above it. Prefer fixing the upstream docs.
- Prefer `locals_to_params(locals())` for forwarding optional kwargs to channel sends, matching the rest of the codebase.

## Commit Convention

Before committing, run `mypy playwright` and fix errors.

Semantic commit messages: `label(scope): description`

Labels: `fix`, `feat`, `chore`, `docs`, `test`, `devops`

```bash
git checkout -b fix-12345
# ... make changes ...
git add <changed-files>
git commit -m "$(cat <<'EOF'
fix(asyncio): do not deadlock in atexit handler

Fixes: https://github.com/microsoft/playwright-python/issues/12345
EOF
)"
git push origin fix-12345
gh pr create --repo microsoft/playwright-python --head username:fix-12345 \
  --title "fix(asyncio): do not deadlock in atexit handler" \
  --body "$(cat <<'EOF'
## Summary
- <describe the change very! briefly>

Fixes https://github.com/microsoft/playwright-python/issues/12345
EOF
)"
```

Never add Co-Authored-By agents in commit message.
Never add "Generated with" in commit message.
Never add test plan to PR description. Keep PR description short — a few bullet points at most.
Branch naming for issue fixes: `fix-<issue-number>`

**Never `git push` without an explicit instruction to push.** Applies even when a PR is already open for the branch — additional commits are immediately visible to reviewers. Commit locally, report what was committed, and wait. Only push when the user's message contains "push", "upload", "create PR", "ship it", or equivalent.
