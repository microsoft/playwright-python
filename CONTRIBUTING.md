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

### Configuring python environment

The project development requires Python version 3.10+. To set it as default in the environment run the following commands:

```sh
# You may need to install python 3.10 venv if it's missing, on Ubuntu just run `sudo apt-get install python3.10-venv`
python3.10 -m venv env
source ./env/bin/activate
```

Install required dependencies:

```sh
python -m pip install --upgrade pip
pip install -r local-requirements.txt
```

Build and install drivers:

The driver is assembled from published artifacts — the `playwright-core` npm
package (version pinned in `DRIVER_VERSION`) and the official Node.js binary
(pinned in `NODE_VERSION`). Building a wheel downloads them with `npm pack` and
plain HTTP, so Node.js/npm must be installed; no git or source build is needed.

```sh
pip install -e .
python -m build --wheel
```

Install the browsers to test against:

```sh
playwright install chromium
```

Run tests:

```sh
pytest --browser chromium
```

Checking for typing errors

```sh
mypy playwright
```

Format the code

```sh
pre-commit install
pre-commit run --all-files
```

For more details look at the [CI configuration](./.github/workflows/ci.yml).

### Regenerating APIs

`update_api.sh` generates `api.json` from a nearby `microsoft/playwright`
checkout (at the tag matching `DRIVER_VERSION`); point `PW_SRC_DIR` at it.

```bash
PW_SRC_DIR=../playwright ./scripts/update_api.sh
pre-commit run --all-files
```

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
