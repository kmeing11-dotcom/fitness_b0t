import re
from datetime import datetime, timedelta
from typing import Optional, Tuple


def parse_time(time_str: str) -> Optional[Tuple[int, int]]:
    """Parse time string to hours and minutes"""
    try:
        if ':' in time_str:
            parts = time_str.split(':')
            hours = int(parts[0])
            minutes = int(parts[1])
        else:
            # Try to parse as hours
            hours = int(time_str)
            minutes = 0

        if 0 <= hours < 24 and 0 <= minutes < 60:
            return hours, minutes
        return None
    except ValueError:
        return None


def format_measurement(value: float, unit: str) -> str:
    """Format measurement value with unit"""
    if value is None:
        return "N/A"
    return f"{value:.1f} {unit}"


def calculate_change(current: float, previous: float) -> Tuple[float, bool]:
    """Calculate change and direction"""
    if current is None or previous is None:
        return 0, False

    change = current - previous
    improved = change < 0  # For weight/waist measurements, decrease is improvement
    return change, improved


def get_date_range(days: int = 30) -> Tuple[datetime, datetime]:
    """Get date range for last N days"""
    end = datetime.now()
    start = end - timedelta(days=days)
    return start, end


def sanitize_username(username: str) -> str:
    """Sanitize username (remove @ and special chars)"""
    return re.sub(r'[^a-zA-Z0-9_]', '', username.lstrip('@'))


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."