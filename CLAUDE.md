# CLAUDE.md

Guidance for Claude when working in this repository.

## What this is

Python bindings for [Playwright](https://playwright.dev). The Python client talks JSON over a pipe to the Node-based driver bundled in `playwright/driver/`. The pipe protocol is defined upstream in `packages/protocol/src/protocol.yml`.

## Layout

- `playwright/_impl/` — hand-written client implementation (one module per object: `_browser.py`, `_page.py`, `_locator.py`, `_network.py`, etc.). Edit these to add or change behavior.
- `playwright/async_api/_generated.py`, `playwright/sync_api/_generated.py` — **auto-generated**. Never edit by hand; rerun `./scripts/update_api.sh` after changing `_impl/` or the driver.
- `scripts/generate_api.py`, `scripts/generate_async_api.py`, `scripts/generate_sync_api.py`, `scripts/documentation_provider.py` — codegen and validation. They diff the Python implementation against the driver's `playwright/driver/package/api.json` and abort if either side is out of sync.
- `scripts/expected_api_mismatch.txt` — explicit allowlist of "documented in JS, not in Python" or "named differently in Python" gaps. Lines that no longer apply must be removed.
- `tests/async/`, `tests/sync/` — pytest suites. Most new tests are added to the async file with a sync mirror.
- `setup.py` — `driver_version = "X.Y.Z"` is the source of truth for which driver build is downloaded from `cdn.playwright.dev`.
- `ROLLING.md`, `CONTRIBUTING.md` — human-facing setup and roll docs.

## Setup

`CONTRIBUTING.md` has the full sequence. The short version:

```sh
python3 -m venv env && source env/bin/activate
pip install --upgrade pip
pip install -r local-requirements.txt
pip install -e .
python -m build --wheel        # downloads the driver listed in setup.py
pre-commit install
```

If the system lacks `python3-venv`, `uv venv env` is an acceptable substitute (then `uv pip install --python env/bin/python --upgrade pip`).

## Common commands

- Regenerate `_generated.py`: `./scripts/update_api.sh` (runs codegen + pre-commit on the generated files).
- Lint everything: `pre-commit run --all-files`.
- Type-check: `mypy playwright`.
- Run tests: `pytest --browser chromium [-k name]`. Browsers are installed via `playwright install chromium` (do **not** use `--with-deps`, which requires sudo).

When changing public API, edit `_impl/`, then run `./scripts/update_api.sh`. The script regenerates `_generated.py` and validates against the driver's `api.json`. If validation fails, fix the mismatch in `_impl/`, in `expected_api_mismatch.txt`, or in `documentation_provider.py` — not by hand-editing `_generated.py`.

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
- Keep `expected_api_mismatch.txt` minimal — every entry needs a one-line rationale comment above it.
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
