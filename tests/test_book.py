"""
Tests for book.py — THSRBooker passenger fill, captcha, submit, parse result.
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

from thsr_auto_book.book import THSRBooker
from thsr_auto_book.config import BookingResult


class TestTHSRBooker:
    def test_fill_passenger_sets_pid_and_phone(self):
        """fill_passenger is decorated with @catch_exception which returns a coroutine."""
        browser = MagicMock()
        page = MagicMock()
        page.fill = AsyncMock()
        browser._page = page

        booker = THSRBooker(browser)
        asyncio.run(booker.fill_passenger("A123456789", "0912345678"))

        calls = {call[0][0]: call[0][1] for call in page.fill.call_args_list}
        assert "#PersonId" in calls
        assert calls["#PersonId"] == "A123456789"
        assert "#Phone" in calls
        assert calls["#Phone"] == "0912345678"

    def test_check_captcha_returns_true_when_visible(self):
        browser = MagicMock()
        page = MagicMock()
        page.wait_for_selector = AsyncMock()
        browser._page = page

        booker = THSRBooker(browser)
        result = asyncio.run(booker.check_captcha())
        assert result is True

    def test_check_captcha_returns_false_when_not_found(self):
        browser = MagicMock()
        page = MagicMock()
        page.wait_for_selector = AsyncMock(side_effect=Exception("not found"))
        browser._page = page

        booker = THSRBooker(browser)
        result = asyncio.run(booker.check_captcha())
        assert result is False

    def test_submit_booking_clicks_confirm(self):
        browser = MagicMock()
        page = MagicMock()
        page.click = AsyncMock()
        page.wait_for_load_state = AsyncMock()
        browser._page = page

        booker = THSRBooker(browser)
        asyncio.run(booker.submit_booking(MagicMock()))
        page.click.assert_called()

    def test_parse_result_success(self):
        browser = MagicMock()
        page = MagicMock()
        # page.content() and code_elem.inner_text() are both async in Playwright
        page.content = AsyncMock(return_value="感謝您，完成訂票")
        code_elem = MagicMock()
        code_elem.inner_text = AsyncMock(return_value="005B 123456")
        page.locator = MagicMock(return_value=code_elem)
        browser._page = page

        booker = THSRBooker(browser)
        result = asyncio.run(booker.parse_result())
        assert result.is_success is True

    def test_parse_result_no_page(self):
        browser = MagicMock()
        browser._page = None

        booker = THSRBooker(browser)
        result = asyncio.run(booker.parse_result())
        assert result.is_success is False
        assert "No page available" in result.error
