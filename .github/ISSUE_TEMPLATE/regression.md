---
name: Report regression
about: Functionality that used to work and does not any more
title: "[REGRESSION]: "
labels: ''
assignees: ''

---

**Context:**
- GOOD Playwright Version: [what Playwright version worked nicely?]
- BAD Playwright Version: [what Playwright version doesn't work any more?]
- Operating System: [e.g. Windows, Linux or Mac]
- Extra: [any specific details about your environment]

**Code Snippet**

Help us help you! Put down a short code snippet that illustrates your bug and
that we can run and debug locally. For example:

```python
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    # ...
    browser.close()
```

**Describe the bug**

Add any other details about the problem here.
