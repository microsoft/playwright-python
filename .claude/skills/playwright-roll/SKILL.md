---
name: playwright-roll
description: Roll Playwright Python to a new version
---

Help the user roll to a new version of Playwright.
../../../ROLLING.md contains general instructions and scripts.

Start with updating the version and generating the API to see the state of things.

Afterwards, work through the list of changes that need to be backported.
You can find a list of pull requests that might need to be taking into account in the issue titled "Backport changes".
Work through them one-by-one and check off the items that you have handled.
Not all of them will be relevant, some might have partially been reverted, etc. - so feel free to check with the upstream release branch.

Rolling includes:
- updating client implementation to match changes in the upstream JS implementation (see ../playwright/packages/playwright-core/src/client)
- adding a couple of new tests to verify new/changed functionality

## Tips & Tricks
- Project checkouts are in the parent directory (`../`).
- when updating checkboxes, store the issue content into /tmp and edit it there, then update the issue based on the file
