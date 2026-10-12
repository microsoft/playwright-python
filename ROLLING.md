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
* generate API from the docs (needs a nearby `microsoft/playwright` checkout at the release branch for the new version, e.g. `release-1.64`): `PW_SRC_DIR=../playwright ./scripts/update_api.sh`
* run `mypy playwright`: every error in `_generated.py` points at an implementation method in `playwright/_impl/` that lacks a new member or option. Implement it there, or record the difference in `scripts/codegen/python_rules.js`. (Temporary: while `scripts/codegen/legacy_order.json` exists, mypy does not check this yet; rely on the tests.)
* commit changes & send PR
* wait for bots to pass & merge the PR
