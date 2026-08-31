import pytest
import datetime
import zoneinfo

from app.services.workflow_cron import CronEvaluator, CronValidationError

def test_cron_parsing_valid_expressions():
    # 1. Standard daily 9am
    mins, hours, days, months, dows = CronEvaluator.parse_cron("0 9 * * *")
    assert mins == {0}
    assert hours == {9}
    assert len(days) == 31
    assert len(months) == 12
    assert len(dows) == 7

    # 2. Weekdays at 15:30
    mins, hours, days, months, dows = CronEvaluator.parse_cron("30 15 * * 1-5")
    assert mins == {30}
    assert hours == {15}
    assert dows == {1, 2, 3, 4, 5}

    # 3. Every 15 minutes during morning hours
    mins, hours, days, months, dows = CronEvaluator.parse_cron("*/15 8-11 * * *")
    assert mins == {0, 15, 30, 45}
    assert hours == {8, 9, 10, 11}

def test_cron_parsing_invalid_expressions():
    with pytest.raises(CronValidationError):
        CronEvaluator.parse_cron("* * * *")  # only 4 fields

    with pytest.raises(CronValidationError):
        CronEvaluator.parse_cron("60 * * * *")  # minute 60 out of bounds

    with pytest.raises(CronValidationError):
        CronEvaluator.parse_cron("0 24 * * *")  # hour 24 out of bounds

    with pytest.raises(CronValidationError):
        CronEvaluator.parse_cron("0 9 32 * *")  # day 32 out of bounds

    with pytest.raises(CronValidationError):
        CronEvaluator.parse_cron("0 9 * 13 *")  # month 13 out of bounds

def test_timezone_validation():
    tz = CronEvaluator.validate_timezone("Asia/Kolkata")
    assert tz.key == "Asia/Kolkata"

    tz_utc = CronEvaluator.validate_timezone("UTC")
    assert tz_utc.key == "UTC"

    with pytest.raises(CronValidationError):
        CronEvaluator.validate_timezone("Invalid/Fake_Timezone")

def test_cron_next_run_calculation():
    # Base: 2026-09-01 08:30:00 UTC
    base_dt = datetime.datetime(2026, 9, 1, 8, 30, 0, tzinfo=datetime.timezone.utc)

    # Next daily 9:00 AM UTC
    next_run = CronEvaluator.get_next_run("0 9 * * *", from_dt=base_dt, tz_name="UTC")
    assert next_run.year == 2026
    assert next_run.month == 9
    assert next_run.day == 1
    assert next_run.hour == 9
    assert next_run.minute == 0

    # Hourly top-of-hour
    next_run_hourly = CronEvaluator.get_next_run("0 * * * *", from_dt=base_dt, tz_name="UTC")
    assert next_run_hourly.hour == 9
    assert next_run_hourly.minute == 0
