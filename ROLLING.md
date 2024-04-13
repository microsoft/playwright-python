# Rolling Playwright-Python to the latest Playwright driver

* Checkout repo: `git clone https://github.com/microsoft/playwright-python`
* Make sure local Python is 3.9
* Create a virtual environment, if don't have one: `python -m venv env`
* Activate venv: `source env/bin/activate`
* Install all deps:
     - `python -m pip install --upgrade pip`
     - `pip install -r local-requirements.txt`
     - `pre-commit install`
     - `pip install -e .`
* Change driver version in `setup.py`
* Download new driver: `python setup.py bdist_wheel`
* Generate API: `./scripts/update_api.sh`
* Commit changes & send PR
* Wait for bots to pass & merge the PR
