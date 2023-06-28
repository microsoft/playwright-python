

# Playwright Akasa Fork

Akasa maintains a small fork of the [Playwright Python](https://github.com/microsoft/playwright-python) project to enable various features specific to Aksasa use cases.


## Changes

* **1.35.1-akasa1**: Expose `BrowserContext.enableRecorder` so that we can initiate recordings programmatically. (masoncj, June 2023)

## Release process

* In [playwright repo](https://github.com/alpha-health-ai/playwright/blob/akasa-expose-enable-recorder/README.AKASA.md):
  * Change version in package.json with akasa extension: "1.35.1-akasa1"
  * Update README.AKASA.md with description of changes.
  * `./utils/build/build-playwright-driver.sh`
* In this repo:
  * `cp ../playwright/utils/build/output/*.zip driver/`
  * Change driver_version in `setup.py` to match above version.
  * Comment out `use_scm_version` in setup.py and add `version` to match above version.
  * Build: `python setup.py bdist_wheel --all`
  * Copy these files to dev server: `scp dist/playwright-*.whl cmason-capsule-u22:`
  * Release:
    ```
    aws codeartifact login --tool twine --repository akasa --domain akasa --domain-owner 025412125743
    twine upload --verbose --repository codeartifact playwright-1.36.0+akasa1-py3-none-*
    ```
