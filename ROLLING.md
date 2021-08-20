# Rolling Playwright-Python to the latest Playwright driver

* checkout repo: `git clone https://github.com/microsoft/playwright-python`
* make sure local python is 3.9
    * create virtual environment, if don't have one: `python3 -m venv env`
* activate venv: `source env/bin/activate`
* install all deps:
     - `python -m pip install --upgrade pip`
     - `pip install -r local-requirements.txt`
     - `pip install -e .`
* checkout `release-1.14` branch
* change driver version in `setup.py`
* download new driver: `rm -rf build/ dist/ driver/ && python setup.py bdist_wheel`
* update API wrt new driver: `./scripts/update_api.sh`
* run commit hooks (twice!): `pre-commit run --all-files`
* commit changes & send PR
* wait for bots to pass & merge the PR

