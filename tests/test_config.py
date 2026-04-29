"""
Tests for config.py — QueryConfig, Train, BookingResult validation.
"""
import pytest
from config import BookingResult, QueryConfig, Train


def test_query_config_validate_ok():
    cfg = QueryConfig(
        depart="台北",
        arrive="左營",
        date="2026/05/01",
        time="08:00",
        adult=1,
        pid="A123456789",
    )
    cfg.validate()  # should not raise


def test_query_config_same_station_raises():
    cfg = QueryConfig(
        depart="台北",
        arrive="台北",
        date="2026/05/01",
        time="08:00",
        adult=1,
        pid="A123456789",
    )
    with pytest.raises(ValueError, match="起站與訖站不能相同"):
        cfg.validate()


def test_query_config_no_tickets_raises():
    cfg = QueryConfig(
        depart="台北",
        arrive="左營",
        date="2026/05/01",
        time="08:00",
        adult=0,
        pid="A123456789",
    )
    with pytest.raises(ValueError, match="總票數需大於 0"):
        cfg.validate()


def test_query_config_missing_pid_raises():
    cfg = QueryConfig(
        depart="台北",
        arrive="左營",
        date="2026/05/01",
        time="08:00",
        adult=1,
        pid="",
    )
    with pytest.raises(ValueError, match="身分證字號必填"):
        cfg.validate()


def test_query_config_bad_date_format_raises():
    cfg = QueryConfig(
        depart="台北",
        arrive="左營",
        date="2026-05-01",
        time="08:00",
        adult=1,
        pid="A123456789",
    )
    with pytest.raises(ValueError, match="日期格式錯誤"):
        cfg.validate()


def test_train_is_available():
    t = Train(number="302", depart_time="07:30", arrive_time="09:00",
              duration="1h30m", cabin="standard", available=10, price=1490)
    assert t.is_available is True

    t0 = Train(number="302", depart_time="07:30", arrive_time="09:00",
               duration="1h30m", cabin="standard", available=0, price=1490)
    assert t0.is_available is False


def test_booking_result_success():
    r = BookingResult(success=True, ticket_code="ABC123")
    assert r.is_success is True
    assert r.ticket_code == "ABC123"


def test_booking_result_failure():
    r = BookingResult(success=False, error="No seats")
    assert r.is_success is False
    assert r.error == "No seats"
