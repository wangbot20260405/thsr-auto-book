import os
from dataclasses import dataclass, field
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


@dataclass
class QueryConfig:
    depart: str
    arrive: str
    date: str  # YYYY/MM/DD
    time: str  # HH:MM
    cabin: str = "standard"  # standard / business
    adult: int = 0
    child: int = 0
    senior: int = 0
    love: int = 0
    college: int = 0
    pid: str = ""
    phone: str = ""
    webhook_url: str = field(default_factory=lambda: os.getenv("DISCORD_WEBHOOK_URL", ""))
    use_membership: bool = False

    def validate(self) -> None:
        if self.depart == self.arrive:
            raise ValueError("起站與訖站不能相同")
        total = self.adult + self.child + self.senior + self.love + self.college
        if total <= 0:
            raise ValueError("總票數需大於 0")
        if not self.pid:
            raise ValueError("乘客身分證字號必填")
        if len(self.pid) not in (10,):
            raise ValueError(f"身分證字號格式錯誤: {self.pid}")
        # simple date format check
        parts = self.date.split("/")
        if len(parts) != 3:
            raise ValueError(f"日期格式錯誤，需為 YYYY/MM/DD: {self.date}")


@dataclass
class Train:
    number: str
    depart_time: str
    arrive_time: str
    duration: str
    cabin: str
    available: int
    price: int
    form_value: str = ""  # HTML form value for server submission

    @property
    def is_available(self) -> bool:
        return self.available > 0


@dataclass
class BookingResult:
    success: bool
    train_number: str = ""
    depart_time: str = ""
    arrive_time: str = ""
    cabin: str = ""
    ticket_code: str = ""
    price: int = 0
    error: str = ""

    @property
    def is_success(self) -> bool:
        return self.success
