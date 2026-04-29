"""
Discord integration — send messages via webhook, poll for captcha responses.
"""
from __future__ import annotations

import logging
import re
import time
from typing import List

import requests

from thsr_auto_book.config import BookingResult, Train

logger = logging.getLogger("thsr_auto_book.discord")


def send_message(content: str, webhook_url: str) -> bool:
    """Send a message to Discord via webhook."""
    if not webhook_url:
        logger.warning("No webhook URL configured, skipping Discord message")
        return False
    try:
        resp = requests.post(
            webhook_url,
            json={"content": content},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Discord message sent: %s", content[:80])
        return True
    except Exception as e:
        logger.error("Failed to send Discord message: %s", e)
        return False


def send_train_list(trains: List[Train], webhook_url: str) -> None:
    """Send formatted train list to Discord."""
    if not trains:
        send_message("🚄 目前沒有可選班次", webhook_url)
        return

    lines = ["**🚄 可用班次**\n"]
    for i, t in enumerate(trains, 1):
        avail_icon = "✅" if t.is_available else "❌"
        lines.append(
            f"`{i}.` [{t.depart_time}] {t.number} | "
            f"標準車廂 剩餘：{t.available} {avail_icon}"
        )
    lines.append("\n請回覆數字選擇車次，或輸入「監控」啟動自動監控")
    send_message("\n".join(lines), webhook_url)


def send_captcha_request(image_path: str | None, webhook_url: str) -> None:
    """Send captcha request to Discord (text-only, image via bot upload if path given)."""
    content = "🔐 **請輸入驗證碼**（請回覆在同一頻道）"
    if image_path:
        content += f"\n驗證碼圖片：{image_path}"
    send_message(content, webhook_url)


def send_booking_result(result: BookingResult, webhook_url: str) -> None:
    if result.is_success:
        content = (
            f"✅ **訂票成功！**\n"
            f"車次：{result.train_number}\n"
            f"取票代碼：`{result.ticket_code}`\n"
            f"金額：NT${result.price}\n"
            f"請於取票期限前完成付款取票"
        )
    else:
        content = f"❌ **訂票失敗**\n原因：{result.error}\n請自行至高鐵網站處理"
    send_message(content, webhook_url)


def send_status(message: str, webhook_url: str) -> None:
    """Send a monitoring status update."""
    send_message(f"🔄 {message}", webhook_url)
