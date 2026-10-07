"""数据模型：计时记录。"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime

STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_INTERRUPTED = "interrupted"

STATUS_LABELS = {
    STATUS_RUNNING: "进行中",
    STATUS_COMPLETED: "已完成",
    STATUS_INTERRUPTED: "已中断",
}

MODE_LABELS = {"countdown": "倒计时", "target": "目标时刻", "countup": "正向计时"}
CLOCK_LABELS = {"digital": "电子时钟", "analog": "传统时钟"}


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class Record:
    """一次计时任务的完整数据。"""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    mode: str = "countdown"
    clock_type: str = "digital"
    planned_seconds: int = 0
    actual_seconds: int = 0
    start_time: str = ""
    end_time: str = ""
    status: str = STATUS_RUNNING
    note_before: str = ""
    note_after: str = ""
    target_start: str = ""
    target_end: str = ""
    paused_count: int = 0
    paused_seconds: int = 0
    created_at: str = field(default_factory=now_str)

    # ---- 序列化 ----
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Record":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})

    # ---- 展示辅助 ----
    @property
    def mode_label(self) -> str:
        return MODE_LABELS.get(self.mode, self.mode)

    @property
    def status_label(self) -> str:
        return STATUS_LABELS.get(self.status, self.status)

    @property
    def clock_label(self) -> str:
        return CLOCK_LABELS.get(self.clock_type, self.clock_type)

    @property
    def span_label(self) -> str:
        """目标时刻模式下的区间文本。"""
        if self.mode == "target" and self.target_start and self.target_end:
            return f"{self.target_start} → {self.target_end}"
        return ""
