class THSRBookingError(Exception):
    """Base exception for THSR booking errors."""
    pass


class BrowserError(THSRBookingError):
    """Browser launch/operation failed."""
    pass


class CloudflareChallengeError(THSRBookingError):
    """Cloudflare JS challenge did not complete."""
    pass


class CaptchaError(THSRBookingError):
    """CAPTCHA recognition failed."""
    pass


class CaptchaTimeoutError(THSRBookingError):
    """User did not provide CAPTCHA input in time."""
    pass


class NetworkError(THSRBookingError):
    """Network request failed after retries."""
    pass


class BookingStepError(THSRBookingError):
    """A booking step (form submit, train select, etc.) failed."""

    def __init__(self, step: str, message: str, screenshot_path: str | None = None):
        self.step = step
        self.screenshot_path = screenshot_path
        super().__init__(f"[{step}] {message}")
