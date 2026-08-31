import datetime
import zoneinfo
from typing import List, Set, Optional, Tuple

class CronValidationError(ValueError):
    pass

class CronEvaluator:
    """
    Pure Python, timezone-aware, deterministic 5-field Cron Evaluator.
    Supports standard wildcards (*), ranges (1-5), steps (*/15), lists (1,15,30),
    and IANA timezones with DST safety.
    """

    MIN_INTERVAL_SECONDS = 60  # Rate limit: max once per minute

    @staticmethod
    def validate_timezone(tz_name: str) -> zoneinfo.ZoneInfo:
        """Validates that tz_name is a recognized IANA timezone identifier."""
        if not tz_name or not isinstance(tz_name, str):
            raise CronValidationError("Timezone must be a non-empty string identifier (e.g. 'UTC', 'Asia/Kolkata').")
        try:
            return zoneinfo.ZoneInfo(tz_name.strip())
        except Exception as e:
            raise CronValidationError(f"Invalid IANA timezone '{tz_name}': {str(e)}")

    @staticmethod
    def _parse_field(field_str: str, min_val: int, max_val: int, field_name: str) -> Set[int]:
        """Parses a single cron field expression into a set of allowed integer values."""
        field_str = field_str.strip()
        if not field_str:
            raise CronValidationError(f"Empty cron field for '{field_name}'.")

        allowed: Set[int] = set()

        for part in field_str.split(","):
            part = part.strip()
            if not part:
                continue

            if "/" in part:
                sub_parts = part.split("/")
                if len(sub_parts) != 2:
                    raise CronValidationError(f"Invalid step syntax '{part}' in '{field_name}'.")
                base, step_str = sub_parts
                try:
                    step = int(step_str)
                    if step <= 0:
                        raise ValueError()
                except ValueError:
                    raise CronValidationError(f"Step value '{step_str}' in '{field_name}' must be a positive integer.")

                if base == "*":
                    start, end = min_val, max_val
                elif "-" in base:
                    range_parts = base.split("-")
                    if len(range_parts) != 2:
                        raise CronValidationError(f"Invalid range '{base}' in '{field_name}'.")
                    start, end = int(range_parts[0]), int(range_parts[1])
                else:
                    start, end = int(base), max_val

                if start < min_val or end > max_val or start > end:
                    raise CronValidationError(f"Range [{start}, {end}] out of bounds for '{field_name}' ({min_val}-{max_val}).")

                for val in range(start, end + 1, step):
                    allowed.add(val)

            elif "-" in part:
                range_parts = part.split("-")
                if len(range_parts) != 2:
                    raise CronValidationError(f"Invalid range syntax '{part}' in '{field_name}'.")
                try:
                    start, end = int(range_parts[0]), int(range_parts[1])
                except ValueError:
                    raise CronValidationError(f"Range values in '{part}' must be integers.")

                if start < min_val or end > max_val or start > end:
                    raise CronValidationError(f"Range [{start}, {end}] out of bounds for '{field_name}' ({min_val}-{max_val}).")

                for val in range(start, end + 1):
                    allowed.add(val)

            elif part == "*":
                for val in range(min_val, max_val + 1):
                    allowed.add(val)

            else:
                try:
                    val = int(part)
                except ValueError:
                    raise CronValidationError(f"Non-integer value '{part}' in '{field_name}'.")

                # Handle day_of_week 7 as 0 (Sunday)
                if field_name == "day_of_week" and val == 7:
                    val = 0

                if val < min_val or val > max_val:
                    raise CronValidationError(f"Value '{val}' out of bounds for '{field_name}' ({min_val}-{max_val}).")

                allowed.add(val)

        if not allowed:
            raise CronValidationError(f"Field '{field_name}' resulted in empty allowed values.")

        return allowed

    @classmethod
    def parse_cron(cls, expression: str) -> Tuple[Set[int], Set[int], Set[int], Set[int], Set[int]]:
        """
        Parses and validates a 5-field cron expression:
        minute (0-59) hour (0-23) day_of_month (1-31) month (1-12) day_of_week (0-6)
        """
        if not expression or not isinstance(expression, str):
            raise CronValidationError("Cron expression must be a non-empty string.")

        parts = expression.strip().split()
        if len(parts) != 5:
            raise CronValidationError(f"Cron expression must contain exactly 5 space-separated fields, got {len(parts)}: '{expression}'.")

        minutes = cls._parse_field(parts[0], 0, 59, "minute")
        hours = cls._parse_field(parts[1], 0, 23, "hour")
        days = cls._parse_field(parts[2], 1, 31, "day_of_month")
        months = cls._parse_field(parts[3], 1, 12, "month")
        dows = cls._parse_field(parts[4], 0, 6, "day_of_week")

        return minutes, hours, days, months, dows

    @classmethod
    def get_next_run(
        cls,
        expression: str,
        from_dt: Optional[datetime.datetime] = None,
        tz_name: str = "UTC",
        max_iterations: int = 525600  # Max 1 year of minutes
    ) -> datetime.datetime:
        """
        Calculates the next matching timestamp after `from_dt` in the specified timezone.
        Returns a UTC-aware datetime.
        """
        tz = cls.validate_timezone(tz_name)
        minutes, hours, days, months, dows = cls.parse_cron(expression)

        if from_dt is None:
            from_dt = datetime.datetime.now(datetime.timezone.utc)
        elif from_dt.tzinfo is None:
            from_dt = from_dt.replace(tzinfo=datetime.timezone.utc)

        # Convert to local target timezone
        local_dt = from_dt.astimezone(tz)
        # Advance by 1 minute to avoid matching current minute
        curr = (local_dt + datetime.timedelta(minutes=1)).replace(second=0, microsecond=0)

        for _ in range(max_iterations):
            # Month check
            if curr.month not in months:
                # Fast forward to next month
                if curr.month == 12:
                    curr = curr.replace(year=curr.year + 1, month=1, day=1, hour=0, minute=0)
                else:
                    curr = curr.replace(month=curr.month + 1, day=1, hour=0, minute=0)
                continue

            # Day of month & day of week check
            # Python weekday(): Monday is 0 and Sunday is 6
            # Cron standard: Sunday is 0, Monday is 1, ..., Saturday is 6
            cron_dow = (curr.weekday() + 1) % 7
            if curr.day not in days or cron_dow not in dows:
                curr = (curr + datetime.timedelta(days=1)).replace(hour=0, minute=0)
                continue

            # Hour check
            if curr.hour not in hours:
                curr = (curr + datetime.timedelta(hours=1)).replace(minute=0)
                continue

            # Minute check
            if curr.minute in minutes:
                # Found exact match! Convert to UTC
                return curr.astimezone(datetime.timezone.utc)

            curr += datetime.timedelta(minutes=1)

        raise CronValidationError(f"Could not find next matching execution for '{expression}' within 1 year.")
