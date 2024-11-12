# Rolling Playwright-Python to the latest Playwright driver

* checkout repo: `git clone https://github.com/microsoft/playwright-python`
* make sure local python is 3.9
    * create virtual environment, if don't have one: `python -m venv env`
* activate venv: `source env/bin/activate`
* install all deps:
     - `python -m pip install --upgrade pip`
     - `pip install -r local-requirements.txt`
     - `pre-commit install`
     - `pip install -e .`
* change driver version in `setup.py`
* download new driver: `python -m build --wheel`
* generate API: `./scripts/update_api.sh`
* commit changes & send PR
* wait for bots to pass & merge the PR


## Fix typing issues with Playwright ToT

1. `cd playwright`
1. `API_JSON_MODE=1 node utils/doclint/generateApiJson.js > ../playwright-python/playwright/driver/package/api.json`
1. `./scripts/update_api.sh`
