import os
import re
from datetime import datetime

def format_date(dt: datetime) -> str:
    return dt.strftime("%d.%m.%Y %H:%M")

def safe_float(value: str) -> float:
    try:
        return float(value.replace(',', '.'))
    except:
        return None

def is_valid_time(time_str: str) -> bool:
    return bool(re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time_str))