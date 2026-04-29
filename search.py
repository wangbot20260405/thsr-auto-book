"""
THSR Train Search — fill search form and parse results via Playwright DOM.
"""
from __future__ import annotations

import logging
import re
from typing import List

from playwright.async_api import Page

from .browser import BrowserManager, catch_exception
from .config import QueryConfig, Train
from .exceptions import BookingStepError, NetworkError

logger = logging.getLogger("thsr_auto_book.search")

STATION_MAP = {
    "台北": "Taipei",
    "板橋": "Banqiao",
    "桃園": "Taoyuan",
    "新竹": "Hsinchu",
    "苗栗": "Miaoli",
    "台中": "Taichung",
    "彰化": "Changhua",
    "雲林": "Yunlin",
    "嘉義": "Chiayi",
    "台南": "Tainan",
    "左營": "Zuoying",
}


class THSRSearcher:
    def __init__(self, browser: BrowserManager):
        self.browser = browser

    @catch_exception
    async def navigate_to_search(self) -> Page:
        return await self.browser.navigate_to_thsr()

    @catch_exception
    async def fill_form(self, config: QueryConfig) -> None:
        page = self.browser._page
        if page is None:
            raise BookingStepError("fill_form", "No page available")

        # Select stations
        from_val = STATION_MAP.get(config.depart, config.depart)
        to_val = STATION_MAP.get(config.arrive, config.arrive)
        await page.select_option("select[name='selectStartStation']", from_val)
        await page.select_option("select[name='selectDestinationStation']", to_val)

        # Date — the input field is id-based
        date_input = page.locator("#BookingS1Form_tripDate")
        await date_input.fill(config.date)

        # Time selector
        time_select = page.locator("#DepartTime")
        await time_select.select_option(config.time)

        # Cabin type
        cabin_code = "0" if config.cabin == "standard" else "1"
        await page.check(f"#CarType{ cabin_code }")
        # or use radio style: input[name='trainCon:trainRadioGroup']
        await page.select_option("select[name='trainCon:trainRadioGroup']", cabin_code)

        # Ticket amounts
        adult_selector = page.locator("#TicketNormal")
        await adult_selector.fill(str(config.adult or 1))

        logger.info("Search form filled: %s -> %s on %s", config.depart, config.arrive, config.date)

    @catch_exception
    async def submit(self) -> Page:
        page = self.browser._page
        if page is None:
            raise BookingStepError("submit", "No page available")
        logger.info("Submitting search form...")
        await page.click("input[value='確認']")
        await page.wait_for_load_state("networkidle2")
        return page

    async def parse_results(self) -> List[Train]:
        """Parse the train list table from the current page HTML."""
        page = self.browser._page
        if page is None:
            raise BookingStepError("parse_results", "No page available")

        html = page.content()
        trains: List[Train] = []

        # Simple HTML parsing — table rows inside #table-result or similar
        # <tr data-value="302">...</tr>
        # We look for rows with radio inputs inside tbody
        rows = page.locator("#tbody tr").all()
        for i, row in enumerate(rows):
            cols = row.locator("td").all()
            if len(cols) < 6:
                continue
            try:
                depart_time = await cols[1].inner_text()
                arrive_time = await cols[2].inner_text()
                duration = await cols[3].inner_text()
                price_text = await cols[5].inner_text()
                # extract number from radio button value
                radio = row.locator("input[type='radio']")
                form_value = await radio.get_attribute("value") or ""
                # last column: available seats
                available_text = await cols[4].inner_text()
                available = int(re.sub(r"\D", "", available_text)) if available_text.strip() not in ("", "X") else 0
                train_number = form_value.strip()
                price = int(re.sub(r"\D", "", price_text)) if price_text.strip() else 0
                trains.append(Train(
                    number=train_number,
                    depart_time=depart_time.strip(),
                    arrive_time=arrive_time.strip(),
                    duration=duration.strip(),
                    cabin=config.cabin if hasattr(self, "config") else "standard",
                    available=available,
                    price=price,
                    form_value=form_value,
                ))
            except Exception as e:
                logger.warning("Failed to parse row %d: %s", i, e)
                continue

        logger.info("Parsed %d trains", len(trains))
        return trains

    @catch_exception
    async def select_train(self, train: Train) -> None:
        page = self.browser._page
        if page is None:
            raise BookingStepError("select_train", "No page available")
        # Click the radio button with the matching form value
        selector = f"#tbody tr input[value='{train.form_value}']"
        await page.click(selector)
        logger.info("Selected train: %s", train.number)
