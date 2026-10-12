# Rolling Playwright-Python to the latest Playwright driver

* checkout repo: `git clone https://github.com/microsoft/playwright-python`
* make sure local python is 3.10 or newer
    * create virtual environment, if don't have one: `python -m venv env`
* activate venv: `source env/bin/activate`
* install all deps:
```
python -m pip install --upgrade pip
pip install -r local-requirements.txt
pre-commit install
pip install -e .
```
* change the driver pin in `DRIVER_VERSION` (the `playwright-core` npm version, e.g. `1.61.0`) and refresh `NODE_VERSION`: `python scripts/update_node_version.py`
* download the new driver: `python -m build --wheel` (fetches `playwright-core` via `npm pack` + the matching Node.js binary and assembles the bundle; no source build).
* generate API from the docs. This needs a separate `microsoft/playwright` checkout used only for rolls, on the exact release branch for the new version (e.g. `release-1.64`), clean and up to date with `origin`: `PW_SRC_DIR=../playwright-for-python ./scripts/update_api.sh`
* run `mypy playwright`: every error in `_generated.py` points at an implementation method in `playwright/_impl/` that lacks a new member or option. Implement it there, or record the difference in `scripts/codegen/python_rules.js`.
* commit changes & send PR
* wait for bots to pass & merge the PR
