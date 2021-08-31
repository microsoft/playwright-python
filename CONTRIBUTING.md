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

### APIs

#### Regenerating

```bash
./scripts/update_api.sh
pre-commit run --all-files
```

#### Differences between `_impl` and exposed API method signatures

- optional arguments are automatically converted to keyword arguments, unless the method has overloads. for example:
  ```py
  def wait_for_selector(self, selector: str, timeout: float = None, state: str = None): ...
  ```
  becomes
  ```py
  def wait_for_selector(self, selector: str, *, timeout: float = None, state: str = None): ...
  ```

- overloads must be defined using `@api_overload` in order for the generate scripts to be able to see them at runtime.
  ```py
  from playwright._impl._overload import api_overload
  
  @api_overload
  async def wait_for_selector(
      self,
      selector: str,
      *,
      timeout: float = None,
      state: Literal["attached", "visible"] = None,
      strict: bool = None,
  ) -> ElementHandle:
      pass

  @api_overload  # type: ignore[no-redef]
  async def wait_for_selector(
      self,
      selector: str,
      *,
      timeout: float = None,
      state: Literal["detached", "hidden"],
      strict: bool = None,
  ) -> None:
      pass

  async def wait_for_selector(  # type: ignore[no-redef]
      self,
      selector: str,
      *,
      timeout: float = None,
      state: Literal["attached", "detached", "hidden", "visible"] = None,
      strict: bool = None,
  ) -> Optional[ElementHandle]:
      ...
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
