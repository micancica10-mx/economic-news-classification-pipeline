from __future__ import annotations

from typing import Optional, Dict, Any
from playwright.async_api import Browser, BrowserContext, Page, Playwright


DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/123.0 Safari/537.36"
)


async def launch_context(
    play: Playwright,
    *,
    headless: bool = True,
    locale: str = "es-CO",
    user_agent: str = DEFAULT_UA,
    viewport: Optional[Dict[str, int]] = None,
) -> tuple[Browser, BrowserContext, Page]:
    browser = await play.chromium.launch(
        headless=headless,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
    )

    context = await browser.new_context(
        viewport=viewport or {"width": 1400, "height": 900},
        user_agent=user_agent,
        locale=locale,
    )

    # “ocultar webdriver”
    await context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    )

    page = await context.new_page()
    return browser, context, page
