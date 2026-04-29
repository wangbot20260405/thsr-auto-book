#!/usr/bin/env python3
"""
THSR Auto-Book — CLI entry point for automated high-speed rail booking.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

# Setup paths
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, "/home/w/.openclaw/workspace")

from dotenv import load_dotenv
load_dotenv()

from thsr_auto_book.browser import BrowserManager
from thsr_auto_book.book import THSRBooker
from thsr_auto_book.config import QueryConfig, Train
from thsr_auto_book.discord_client import send_booking_result, send_captcha_request, send_message, send_train_list, send_status
from thsr_auto_book.exceptions import BookingStepError, CaptchaError, CaptchaTimeoutError, THSRBookingError
from thsr_auto_book.monitor import monitor_loop
from thsr_auto_book.search import THSRSearcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("thsr_auto_book")


def ask(prompt: str, default: str = "", required: bool = False) -> str:
    while True:
        val = input(f"{prompt} [{default}]: ").strip()
        if val:
            return val
        if default or not required:
            return default
        print("此欄位必填")


def collect_config() -> QueryConfig:
    print("\n=== THSR 訂票查詢 ===")
    depart = ask("出發站", "台北")
    arrive = ask("到達站", "左營")
    date = ask("出發日期 (YYYY/MM/DD)", required=True)
    time = ask("出發時段", "00:00")
    cabin = ask("車廂種類 (standard/business)", "standard")
    adult = int(ask("全票張數", "1") or 1)
    pid = ask("乘客身分證字號", required=True)
    phone = ask("手機號碼", "")
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "")

    config = QueryConfig(
        depart=depart,
        arrive=arrive,
        date=date,
        time=time,
        cabin=cabin,
        adult=adult,
        pid=pid,
        phone=phone,
        webhook_url=webhook,
    )
    config.validate()
    return config


async def run() -> None:
    config = collect_config()
    bot_token = os.getenv("DISCORD_BOT_TOKEN", "")

    browser_mgr = BrowserManager(headless=True)
    try:
        await browser_mgr.launch()
        await browser_mgr.new_page()

        searcher = THSRSearcher(browser_mgr)
        booker = THSRBooker(browser_mgr)

        # Step 1: navigate and search
        await searcher.navigate_to_search()
        await searcher.fill_form(config)
        await searcher.submit()

        trains = searcher.parse_results()
        send_train_list(trains, config.webhook_url)

        # Step 2: user selects a train
        choice = input("選班次編號（或輸入「監控」自動監控）: ").strip()
        if choice.lower() == "監控":
            selected = trains[0] if trains else None
            if not selected:
                print("沒有可選班次")
                return
            available_train = await monitor_loop(config, selected, searcher)
            if not available_train:
                send_status("監控中斷", config.webhook_url)
                return
            selected = available_train

        else:
            idx = int(choice or 1) - 1
            if idx < 0 or idx >= len(trains):
                print("無效的編號")
                return
            selected = trains[idx]

        # Step 3: select train and go to passenger form
        await searcher.select_train(selected)
        await browser_mgr.navigate_to_thsr()

        # Step 4: fill passenger + captcha
        await booker.fill_passenger(config.pid, config.phone)
        has_captcha = await booker.check_captcha()

        if has_captcha:
            send_captcha_request(None, config.webhook_url)
            captcha = booker.solve_captcha_auto()
            if not captcha:
                logger.warning("CNN captcha failed, waiting for Discord input")
                if bot_token and config.webhook_url:
                    channel_id = os.getenv("DISCORD_CHANNEL_ID", "")
                    try:
                        captcha = await booker.wait_for_captcha_discord(channel_id, bot_token)
                    except CaptchaTimeoutError:
                        logger.error("Captcha timeout")
                        return
            await booker.submit_booking(config)

        # Step 5: confirm ticket
        result = booker.parse_result()
        send_booking_result(result, config.webhook_url)

        print("\n訂票完成")
        print(result.ticket_code if result.is_success else f"失敗: {result.error}")

    except THSRBookingError as e:
        logger.exception("Booking error")
        send_message(f"❌ 訂票錯誤：{e}", config.webhook_url)
    finally:
        await browser_mgr.close()


def main() -> int:
    try:
        asyncio.run(run())
        return 0
    except KeyboardInterrupt:
        print("\n已中止")
        return 130
    except Exception as e:
        logger.exception("Unexpected error")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
