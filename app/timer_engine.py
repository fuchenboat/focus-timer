"""计时引擎：纯逻辑实现，支持倒计时与目标时刻（区间模拟）两种模式。

设计要点：
- 使用单调时钟 time.monotonic() 累计运行片段，避免系统时间被修改导致的误差；
- 暂停不会丢失已计时长，暂停时长单独记录；
- 目标时刻模式按「起始时刻 → 结束时刻」的区间长度倒数，
  同时可以换算出「模拟当前时刻」，用于传统时钟表盘的展示。
"""
from __future__ import annotations

import time
from datetime import datetime

from .utils import hm_to_minutes, now_datetime

STATE_IDLE = "idle"
STATE_RUNNING = "running"
STATE_PAUSED = "paused"
STATE_FINISHED = "finished"


class TimerEngine:
    def __init__(self) -> None:
        self.mode = "countdown"          # countdown | target
        self.clock_type = "digital"      # digital | analog
        self.total = 0.0                 # 计划总时长（秒）
        self.target_start = ""           # 目标时刻模式下 HH:MM
        self.target_end = ""             # 目标时刻模式下 HH:MM
        self.state = STATE_IDLE
        self.paused_count = 0
        self.paused_seconds = 0.0
        self.started_wall: datetime | None = None
        self.finished_wall: datetime | None = None

        self._accum = 0.0                # 已完成运行片段累计（秒）
        self._seg_start: float | None = None   # 当前片段起始 monotonic
        self._pause_start: float | None = None

    # ------------------------------------------------------------------ 配置
    def configure_countdown(self, seconds: float) -> None:
        self._reset_runtime()
        self.mode = "countdown"
        self.total = max(0.0, float(seconds))
        self.target_start = ""
        self.target_end = ""

    def configure_target(self, start_hm: str, end_hm: str) -> None:
        self._reset_runtime()
        self.mode = "target"
        self.target_start = start_hm
        self.target_end = end_hm
        span = hm_to_minutes(end_hm) - hm_to_minutes(start_hm)
        if span <= 0:
            span += 24 * 60
        self.total = float(span * 60)

    def configure_countup(self) -> None:
        """正向计时（停表）：从 0 开始累加，没有预设终点。"""
        self._reset_runtime()
        self.mode = "countup"
        self.total = 0.0
        self.target_start = ""
        self.target_end = ""

    def _reset_runtime(self) -> None:
        self.state = STATE_IDLE
        self._accum = 0.0
        self._seg_start = None
        self._pause_start = None
        self.paused_count = 0
        self.paused_seconds = 0.0
        self.started_wall = None
        self.finished_wall = None

    def reset(self) -> None:
        self._reset_runtime()
        self.total = 0.0
        self.mode = "countdown"
        self.target_start = ""
        self.target_end = ""

    # ------------------------------------------------------------------ 控制
    def start(self) -> None:
        """开始一次全新的计时（会重置累计数据）。"""
        if self.state == STATE_RUNNING:
            return
        self._accum = 0.0
        self.paused_count = 0
        self.paused_seconds = 0.0
        self.finished_wall = None
        self.started_wall = now_datetime()
        self._pause_start = None
        self._seg_start = time.monotonic()
        self.state = STATE_RUNNING

    def pause(self) -> None:
        if self.state != STATE_RUNNING:
            return
        if self._seg_start is not None:
            self._accum += time.monotonic() - self._seg_start
            self._seg_start = None
        self._pause_start = time.monotonic()
        self.paused_count += 1
        self.state = STATE_PAUSED

    def resume(self) -> None:
        if self.state != STATE_PAUSED:
            return
        if self._pause_start is not None:
            self.paused_seconds += time.monotonic() - self._pause_start
            self._pause_start = None
        self._seg_start = time.monotonic()
        self.state = STATE_RUNNING

    def toggle_pause(self) -> None:
        if self.state == STATE_RUNNING:
            self.pause()
        elif self.state == STATE_PAUSED:
            self.resume()

    def stop(self) -> None:
        """结束计时（无论是否已经到点）。"""
        if self.state == STATE_RUNNING and self._seg_start is not None:
            self._accum += time.monotonic() - self._seg_start
            self._seg_start = None
        elif self.state == STATE_PAUSED and self._pause_start is not None:
            self.paused_seconds += time.monotonic() - self._pause_start
            self._pause_start = None
        self.finished_wall = now_datetime()
        self.state = STATE_FINISHED

    # ------------------------------------------------------------------ 数值
    @property
    def elapsed(self) -> float:
        """已进行的有效时长（不含暂停）。"""
        total = self._accum
        if self.state == STATE_RUNNING and self._seg_start is not None:
            total += time.monotonic() - self._seg_start
        if self.total > 0:
            return min(total, self.total)
        return total

    @property
    def remaining(self) -> float:
        return max(0.0, self.total - self.elapsed)

    @property
    def display_seconds(self) -> float:
        """界面主显示值：正向计时显示已进行时长，其余模式显示剩余时长。"""
        if self.mode == "countup":
            return self.elapsed
        return self.remaining

    @property
    def progress(self) -> float:
        if self.mode == "countup":
            # 正向计时没有总时长，进度环改为「当前这一分钟」的走针进度
            return (self.elapsed % 60) / 60.0
        if self.total <= 0:
            return 0.0
        return max(0.0, min(1.0, self.elapsed / self.total))

    @property
    def is_running(self) -> bool:
        return self.state == STATE_RUNNING

    @property
    def is_paused(self) -> bool:
        return self.state == STATE_PAUSED

    @property
    def is_idle(self) -> bool:
        return self.state == STATE_IDLE

    @property
    def is_finished(self) -> bool:
        return self.state == STATE_FINISHED

    @property
    def expired(self) -> bool:
        """计划时间是否已经走完。"""
        return self.total > 0 and self.remaining <= 0 and self.state in (STATE_RUNNING, STATE_PAUSED)

    @property
    def simulated_datetime(self) -> datetime:
        """目标时刻模式下：起始时刻 + 已进行时长 = 模拟当前时刻。"""
        if self.mode == "target" and self.target_start:
            minutes = hm_to_minutes(self.target_start)
            base = now_datetime().replace(
                hour=minutes // 60, minute=minutes % 60, second=0, microsecond=0
            )
            return base + _seconds_delta(self.elapsed)
        return now_datetime()

    def clock_parts(self) -> tuple[int, int, int]:
        """返回传统时钟表盘要显示的时刻 (时, 分, 秒)。

        - 目标时刻模式：显示「模拟当前时刻」（起始时刻 + 已进行时长）；
        - 正向计时模式：显示已进行的时长（像秒表表盘一样）；
        - 倒计时模式：显示真实当前时刻。

        三种情况下数值都是递增的，因此指针始终顺时针走动。
        """
        if self.mode == "target":
            dt = self.simulated_datetime
            return dt.hour, dt.minute, dt.second
        if self.mode == "countup":
            seconds = int(self.elapsed)
            hours, rem = divmod(seconds, 3600)
            minutes, secs = divmod(rem, 60)
            return hours, minutes, secs
        dt = now_datetime()
        return dt.hour, dt.minute, dt.second


def _seconds_delta(seconds: float):
    from datetime import timedelta

    return timedelta(seconds=int(seconds))
