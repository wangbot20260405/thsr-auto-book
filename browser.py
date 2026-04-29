"""
Browser Manager — Playwright-based Chrome management with Cloudflare challenge support.
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Browser, Page

from thsr_auto_book.exceptions import BrowserError, CloudflareChallengeError

logger = logging.getLogger("thsr_auto_book.browser")

THSR_URL = "https://irs.thsrc.com.tw/IMINT/?locale=tw"
CHROME_OPTIONS = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--window-size=1280,900",
]


def _ensure_display() -> None:
    """Set DISPLAY for headful Chrome when Xvfb is running."""
    if "DISPLAY" not in os.environ:
        shutil.which("xvfb-run") or shutil.which("Xvfb")
        # default Xvfb display
        os.environ.setdefault("DISPLAY", ":99")


def catch_exception(func):
    """Decorator: on exception, take screenshot and re-raise as BookingStepError."""
    async def wrapper(self, *args, **kwargs):
        try:
            return await func(self, *args, **kwargs)
        except Exception as exc:
            import traceback
            logger.exception("Exception in %s.%s", func.__module__, func.__name__)
            path = await self.take_screenshot()
            from thsr_auto_book.exceptions import BookingStepError
            raise BookingStepError(
                step=func.__name__,
                message=f"{type(exc).__name__}: {exc}",
                screenshot_path=path,
            ) from exc
    return wrapper


class BrowserManager:
    def __init__(self, headless: bool = True):
        self.headless = headless
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None
        self._screenshot_dir = Path(tempfile.mkdtemp(prefix="thsr-screenshot-"))

    async def launch(self) -> Browser:
        _ensure_display()
        try:
            pw = await async_playwright().start()
            self._browser = await pw.chromium.launch(
                headless=self.headless,
                args=CHROME_OPTIONS,
            )
            logger.info("Browser launched (headless=%s)", self.headless)
            return self._browser
        except Exception as e:
            raise BrowserError(f"Failed to launch browser: {e}") from e

    async def new_page(self) -> Page:
        if self._browser is None:
            raise BrowserError("Browser not launched. Call launch() first.")
        self._page = await self._browser.new_page(
            viewport={"width": 1280, "height": 900}
        )
        await self._page.set_viewport_size({"width": 1280, "height": 900})
        logger.info("New page opened")
        return self._page

    @catch_exception
    async def navigate_to_thsr(self, wait_selector: str = "select[name='selectStartStation']", timeout: int = 60000) -> Page:
        """Navigate to THSR booking page, wait for form to be ready."""
        if self._page is None:
            raise BrowserError("No page. Call new_page() first.")
        logger.info("Navigating to THSR booking page...")
        await self._page.goto(THSR_URL, wait_until="networkidle", timeout=timeout)
        # Give Cloudflare challenge time to resolve
        await asyncio.sleep(5)
        try:
            await self._page.wait_for_selector(wait_selector, timeout=30000)
            logger.info("THSR form loaded successfully")
        except Exception:
            raise CloudflareChallengeError("Cloudflare challenge did not resolve; form not found.")
        return self._page

    async def take_screenshot(self) -> str:
        path = str(self._screenshot_dir / f"screenshot_{asyncio.get_event_loop().time():.0f}.png")
        if self._page:
            await self._page.screenshot(path=path)
            logger.info("Screenshot saved: %s", path)
        return path

    async def close(self) -> None:
        if self._page:
            await self._page.close()
            self._page = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        logger.info("Browser closed")
