"""
THSR Booking Flow — passenger data, captcha, ticket submission.
"""
from __future__ import annotations

import asyncio
import logging
import re
import sys
import time
from typing import Optional

from playwright.async_api import Page

from thsr_auto_book.browser import BrowserManager, catch_exception
from thsr_auto_book.config import BookingResult, QueryConfig
from thsr_auto_book.exceptions import BookingStepError, CaptchaTimeoutError

logger = logging.getLogger("thsr_auto_book.book")

# Path to CNN captcha solver from thsr_tools
CAPTCHA_SOLVER_PATH = "/home/w/.openclaw/workspace/thsr_tools"


class THSRBooker:
    def __init__(self, browser: BrowserManager):
        self.browser = browser

    @catch_exception
    async def fill_passenger(self, pid: str, phone: str = "") -> None:
        page = self.browser._page
        if page is None:
            raise BookingStepError("fill_passenger", "No page available")
        await page.fill("#PersonId", pid)
        if phone:
            await page.fill("#Phone", phone)
        logger.info("Passenger data filled (PID: %s)", pid[:4] + "****")

    async def check_captcha(self) -> bool:
        """Return True if a captcha element is visible on the page."""
        page = self.browser._page
        if page is None:
            return False
        try:
            await page.wait_for_selector("#SecurityCode", timeout=3000)
            return True
        except Exception:
            return False

    async def solve_captcha_auto(self) -> str:
        """Solve captcha using CNN model from thsr_tools."""
        page = self.browser._page
        if page is None:
            raise BookingStepError("solve_captcha_auto", "No page available")

        # Save captcha image
        img = page.locator("#SecurityCode")
        path = f"/tmp/captcha_{time.time():.0f}.png"
        await img.screenshot(path=path)

        # Call CNN solver
        sys.path.insert(0, CAPTCHA_SOLVER_PATH)
        from captcha import solve_captcha
        result = solve_captcha(path)
        logger.info("CNN captcha result: %s", result or "(empty)")
        return result or ""

    async def wait_for_captcha_discord(
        self,
        channel_id: str,
        bot_token: str,
        timeout: int = 300,
    ) -> str:
        """Poll Discord channel history for captcha response."""
        import requests
        headers = {"Authorization": f"Bot {bot_token}"}
        url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        start = time.time()
        seen_ids = set()

        while time.time() - start < timeout:
            try:
                resp = requests.get(url, headers=headers, params={"limit": 5}, timeout=10)
                if resp.status_code != 200:
                    await asyncio.sleep(1)
                    continue
                messages = resp.json()
                for msg in messages:
                    content = msg.get("content", "").strip()
                    msg_id = msg["id"]
                    if msg_id in seen_ids:
                        continue
                    seen_ids.add(msg_id)
                    if re.fullmatch(r"[A-Z0-9]{4,6}", content.upper()):
                        logger.info("Captcha received from Discord: %s", content)
                        return content.upper()
            except Exception as e:
                logger.warning("Discord polling error: %s", e)
            await asyncio.sleep(1)

        raise CaptchaTimeoutError("No valid captcha received within timeout")

    @catch_exception
    async def submit_booking(self, config: QueryConfig) -> Page:
        page = self.browser._page
        if page is None:
            raise BookingStepError("submit_booking", "No page available")
        await page.click("input[value='確認']")
        await page.wait_for_load_state("networkidle2")
        logger.info("Booking submitted")
        return page

    async def parse_result(self) -> BookingResult:
        page = self.browser._page
        if page is None:
            return BookingResult(success=False, error="No page available")

        try:
            # Try to find ticket code
            code_elem = page.locator(".ticket-no, .ticket-number, td.ticket-number")
            ticket_code = (await code_elem.inner_text()).strip() if code_elem else ""
            # Parse success indicators
            content = await page.content()
            if "感謝" in content or "成功" in content or ticket_code:
                return BookingResult(
                    success=True,
                    ticket_code=ticket_code,
                )
        except Exception as e:
            logger.warning("Failed to parse result: %s", e)

        return BookingResult(success=False, error="Could not parse booking result")
