"""
Monitoring loop — poll THSR for seat availability and trigger booking.
"""
from __future__ import annotations

import asyncio
import logging

from .browser import BrowserManager
from .config import QueryConfig, Train
from .discord_client import send_status
from .search import THSRSearcher

logger = logging.getLogger("thsr_auto_book.monitor")


async def monitor_loop(
    config: QueryConfig,
    target_train: Train,
    searcher: THSRSearcher,
    interval: int = 30,
) -> Train | None:
    """
    Poll every `interval` seconds.
    Return the target train if it becomes available, else None on interrupt.
    """
    logger.info("Monitor started for train %s (interval=%ds)", target_train.number, interval)
    send_status(
        f"開始監控車次 {target_train.number}，每 {interval} 秒查詢一次",
        config.webhook_url,
    )

    count = 0
    while True:
        count += 1
        try:
            # Re-fill form and submit (fresh page load each time)
            await searcher.browser.navigate_to_thsr()
            await searcher.fill_form(config)
            await searcher.submit()
            trains = searcher.parse_results()

            found = next((t for t in trains if t.number == target_train.number), None)
            if found and found.is_available:
                logger.info("Train %s has seats available!", found.number)
                send_status(
                    f"✅ 車次 {found.number} 有位！正在訂票...",
                    config.webhook_url,
                )
                return found

            logger.info("[%d] Train %s still no seats", count, target_train.number)
            send_status(
                f"[{count}] 車次 {target_train.number} 無位，{interval} 秒後重試...",
                config.webhook_url,
            )
        except Exception as e:
            logger.warning("Monitor query error: %s", e)
            send_status(f"監控查詢錯誤：{e}，{interval} 秒後重試...", config.webhook_url)

        await asyncio.sleep(interval)
