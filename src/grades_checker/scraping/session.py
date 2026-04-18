from contextlib import contextmanager
from typing import Iterator

from playwright.sync_api import Browser, BrowserContext, Page, Playwright, sync_playwright


@contextmanager
def managed_page(headless: bool = False) -> Iterator[Page]:
    playwright: Playwright = sync_playwright().start()
    browser: Browser = playwright.chromium.launch(headless=headless)
    context: BrowserContext = browser.new_context()
    page: Page = context.new_page()
    try:
        yield page
    finally:
        context.close()
        browser.close()
        playwright.stop()
