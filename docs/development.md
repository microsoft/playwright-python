# Development

## Build driver:

```sh
pip install -e .
python setup.py bdist_wheel
```

## Run tests:

```sh
pytest
```

## Run tests with coverage:

```sh
pytest --cov=playwright --cov-report html
open htmlcov/index.html
```

## Deploy:

```sh
python setup.py bdist_wheel
python setup.py upload
```

## Checking for typing errors

```sh
mypy playwright
```

## Format the code

```sh
black .
```

## Installing the Git hooks (auto format etc. on commit)

```sh
pre-commit install
```
