# What is this?

⚠️ **EXPERIMENTAL** ⚠️

This is a Python 3 version of the [https://github.com/microsoft/playwright](https://github.com/microsoft/playwright) project. In only contains initial stub implementation with **NO** tests. It can not be used in production yet.

# Install

```sh
pip3 install playwright_web
```

# Run

```py
import asyncio
from playwright_web import webkit

async def run():
    browser = await webkit.launch(headless=False)
    context = await browser.newContext(viewport=0) # 0 stands for no viewport
    page = await context.newPage()

    page.on('framenavigated', lambda frame: print(f'Frame navigated to {frame.url}'))
    page.on('request', lambda request: print(f'Request {request.url}'))

    await page.goto('https://example.com')
    print(await page.title())

    body = await page.querySelector('body')
    print(await body.textContent())

    await page.click('text=More information...')
    print(await page.title())

    await browser.close()

asyncio.get_event_loop().run_until_complete(run())
```

# Development

Build driver:
```sh
python ./build_driver.py
```

Run tests:
```sh
python -m unittest
```

Run tests with coverage:
```
pip install coverage
coverage run -m unittest
coverage html
open htmlcov/index.html
```

Deploy:
```sh
python ./build_package.py
... check
python ./upload_package.py
```

# Contributing

This project welcomes contributions and suggestions.  Most contributions require you to agree to a
Contributor License Agreement (CLA) declaring that you have the right to, and actually do, grant us
the rights to use your contribution. For details, visit https://cla.opensource.microsoft.com.

When you submit a pull request, a CLA bot will automatically determine whether you need to provide
a CLA and decorate the PR appropriately (e.g., status check, comment). Simply follow the instructions
provided by the bot. You will only need to do this once across all repos using our CLA.

This project has adopted the [Microsoft Open Source Code of Conduct](https://opensource.microsoft.com/codeofconduct/).
For more information see the [Code of Conduct FAQ](https://opensource.microsoft.com/codeofconduct/faq/) or
contact [opencode@microsoft.com](mailto:opencode@microsoft.com) with any additional questions or comments.
