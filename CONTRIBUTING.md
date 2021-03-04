# Contributing

## How to Contribute

### Configuring python environment

The project development requires Python version 3.9+. To set it as default in the environment run the following commands:

```sh
# You may need to install python 3.9 venv if it's missing, on Ubuntu just run `sudo apt-get install python3.9-venv`
python3.9 -m venv env
source ./env/bin/activate
```

Install required dependencies:

```sh
python -m pip install --upgrade pip wheel
pip install -r local-requirements.txt
```

Build and install drivers:

```sh
pip install -e.
python setup.py bdist_wheel
# For all platforms
python setup.py bdist_wheel --all
```

Run tests:

```sh
pytest
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

For more details look at the [CI configuration](./blob/master/.github/workflows/ci.yml).

### Regenerating APIs

```bash
./scripts/update_api.sh
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
