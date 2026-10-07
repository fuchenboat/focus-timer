"""通用工具函数：时间格式化与解析。"""
from __future__ import annotations

from datetime import datetime, timedelta


def format_hms(seconds: float, always_hours: bool = True) -> str:
    """秒 -> HH:MM:SS（或 MM:SS）。"""
    seconds = max(0, int(round(seconds)))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    if always_hours or hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_duration(seconds: float) -> str:
    """秒 -> 人类可读时长，例如「1 小时 23 分钟」。"""
    seconds = max(0, int(round(seconds)))
    hours, rem = divmod(seconds, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if hours:
        parts.append(f"{hours} 小时")
    if minutes:
        parts.append(f"{minutes} 分钟")
    if secs and not hours:
        parts.append(f"{secs} 秒")
    return " ".join(parts) if parts else "0 秒"


def parse_hm(text: str):
    """解析 HH:MM 文本，返回 (hour, minute)，非法返回 None。"""
    if not text:
        return None
    normalized = str(text).strip().replace("：", ":").replace(".", ":").replace(" ", "")
    if ":" not in normalized:
        return None
    parts = normalized.split(":")
    if len(parts) != 2:
        return None
    try:
        hour = int(parts[0])
        minute = int(parts[1])
    except ValueError:
        return None
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        return None
    return hour, minute


def normalize_hm(text: str, default: str = "09:00") -> str:
    """标准化时间文本为 HH:MM。"""
    parsed = parse_hm(text)
    if not parsed:
        return default
    return f"{parsed[0]:02d}:{parsed[1]:02d}"


def current_hm() -> str:
    now = datetime.now()
    return f"{now.hour:02d}:{now.minute:02d}"


def minutes_to_hm(total_minutes: int) -> str:
    total_minutes %= 24 * 60
    return f"{total_minutes // 60:02d}:{total_minutes % 60:02d}"


def hm_to_minutes(hm: str) -> int:
    parsed = parse_hm(hm)
    if not parsed:
        return 0
    return parsed[0] * 60 + parsed[1]


def now_datetime() -> datetime:
    return datetime.now()


def short_datetime(text: str) -> str:
    """把 "2026-10-07 09:00:00" 显示为 "10-07 09:00"。"""
    try:
        dt = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return text
    return dt.strftime("%m-%d %H:%M")


def end_of_span(start: str, end: str) -> str:
    """返回目标区间结束时刻的展示文本，支持跨天。"""
    return end


def span_minutes(start_hm: str, end_hm: str) -> int:
    """计算两个时刻之间的分钟数（跨天取正）。"""
    start = hm_to_minutes(start_hm)
    end = hm_to_minutes(end_hm)
    diff = end - start
    if diff <= 0:
        diff += 24 * 60
    return diff


def combine_date(time_text: str) -> datetime:
    """把 HH:MM 与今天日期组合成 datetime。"""
    parsed = parse_hm(time_text) or (0, 0)
    today = datetime.now()
    return today.replace(hour=parsed[0], minute=parsed[1], second=0, microsecond=0)


def shift_hm(hm: str, minutes: int) -> str:
    return minutes_to_hm(hm_to_minutes(hm) + minutes)


def add_seconds(base: datetime, seconds: float) -> datetime:
    return base + timedelta(seconds=seconds)
