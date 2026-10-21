# Contributing

## Choosing an Issue

To maintain project quality and focus, Playwright **requires a corresponding issue** for every contribution, with the exception of minor documentation fixes.

If you would like to address a bug or feature that isn't currently listed, **please file a new issue first**. This allows the community and maintainers to provide early feedback and facilitates a discussion before you invest time in developing a pull request.

When submitting an issue, please state clearly if you intend to work on it. Once triaged and approved, the maintainers will determine the best path forward—whether the task should be handled by the **core team**, an **automated agent**, or a **community contributor**. If the issue is assigned to you, you may then proceed with your changes and submit a PR.

### Submission Policy
To ensure the maintainability of the project, please note the following:

* **Unsolicited PRs:** Pull requests submitted without a linked issue or prior approval will be closed.
* **Low-Quality AI Contributions:** PRs that do not meet our quality standards or lack human oversight (including low-quality agentic submissions) will be closed without explanation.
* **Approval Required:** Only proceed with a PR once the issue has been officially assigned to you or approved for community contribution.

## How to Contribute

### Build and test

You need Python 3.10+, git, and Node.js with npm. The steps are the same on your
machine and in CI.

**1. Get the code and the Python dependencies.**

```sh
git clone https://github.com/microsoft/playwright-python
cd playwright-python
python3 -m venv env                      # on Ubuntu, you may need: sudo apt-get install python3-venv
source env/bin/activate
python -m pip install --upgrade pip
pip install -r local-requirements.txt
pip install -e .
```

**2. Get Playwright.** The driver and the generated API come from
`microsoft/playwright`, at the commit in `DRIVER_VERSION`. This clones it into
`.upstream/` (gitignored) and checks out that commit. Run it again when
`DRIVER_VERSION` changes, for example after a pull.

```sh
python scripts/upstream.py checkout
```

**3. Build.** This builds the driver from `.upstream/` (`npm ci`, `npm run build`,
plus the Node.js binary of `NODE_VERSION`) and the wheel in `dist/`. It also puts the
driver in `playwright/driver/`, for the editable install of step 1. The first build
takes a few minutes; later builds reuse the driver until `DRIVER_VERSION` changes.

```sh
python -m build --wheel
```

**4. Test.**

```sh
playwright install chromium
./test.sh                                # tests/sync and tests/async, in parallel, under xvfb
pytest tests/async --browser chromium -k <name>   # or a part of them
```

**5. Lint.** This is what the Lint job of CI runs, including mypy. The checks are
not a git hook.

```sh
pre-commit run --all-files
```

### Regenerating the API

`playwright/{async,sync}_api/_generated.py`, `playwright/_impl/_api_structures.py`,
the protocol files of `playwright/_impl` and `tests/upstream_registry.md` are
generated from `.upstream/`, and committed. Generate them again after you change
`scripts/codegen/`:

```sh
./scripts/update_api.sh
```

Python facts that the docs do not contain are in `scripts/codegen/python_rules.js`.
To move to a new Playwright commit, see [ROLLING.md](./ROLLING.md).

## Contributor License Agreement

This project welcomes contributions and suggestions. Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

## Code of Conduct

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
