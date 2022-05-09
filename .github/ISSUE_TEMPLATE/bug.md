---
name: Bug Report
about: Something doesn't work like it should? Tell us!
title: "[BUG]"
labels: ''
assignees: ''

---

**Context:**
- Playwright Version: [what Playwright version do you use?]
- Operating System: [e.g. Windows, Linux or Mac]
- Python version: [e.g. 3.7, 3.9]
- Browser: [e.g. All, Chromium, Firefox, WebKit]
- Extra: [any specific details about your environment]

**Code Snippet**

Help us help you! Put down a short code snippet that illustrates your bug and
that we can run and debug locally.

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
