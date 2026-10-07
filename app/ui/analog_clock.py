"""传统时钟（表盘）绘制组件。"""
from __future__ import annotations

import math
import tkinter as tk

from .canvas_kit import UI_FONT_SMALL


class AnalogClock:
    """绘制在画布上的传统时钟，支持进度环与中心文字。"""

    def __init__(self, canvas: tk.Canvas, theme) -> None:
        self.canvas = canvas
        self.theme = theme
        self.items: list[int] = []
        self.cx = 0.0
        self.cy = 0.0
        self.r = 100.0
        self._built = False
        self.arc_track = None
        self.arc_progress = None
        self.hand_hour = None
        self.hand_minute = None
        self.hand_second = None
        self.center_dot = None
        self.sub_text = None

    # ------------------------------------------------------------------ 构建
    def build(self, cx: float, cy: float, r: float) -> None:
        self.cx, self.cy, self.r = cx, cy, r
        self.destroy()
        theme = self.theme
        r = self.r

        self.items.append(
            self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r,
                                    fill=theme["surface"], outline=theme["border"], width=2)
        )
        # 刻度
        for i in range(60):
            angle = math.radians(i * 6)
            major = i % 5 == 0
            outer = r * 0.96
            inner = r * (0.86 if major else 0.92)
            x1 = cx + inner * math.sin(angle)
            y1 = cy - inner * math.cos(angle)
            x2 = cx + outer * math.sin(angle)
            y2 = cy - outer * math.cos(angle)
            self.items.append(
                self.canvas.create_line(
                    x1, y1, x2, y2,
                    fill=theme["text_muted"] if major else theme["text_faint"],
                    width=2 if major else 1,
                )
            )
        # 小时数字
        for hour in range(1, 13):
            angle = math.radians(hour * 30)
            x = cx + r * 0.70 * math.sin(angle)
            y = cy - r * 0.70 * math.cos(angle)
            self.items.append(
                self.canvas.create_text(x, y, text=str(hour), fill=theme["text_muted"],
                                        font=(UI_FONT_SMALL[0], max(9, int(r * 0.11))))
            )

        # 进度环
        ring_r = r + 12
        self.arc_track = self.canvas.create_arc(
            cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r,
            start=90, extent=-359.9, style="arc", outline=theme["track"], width=9,
        )
        self.arc_progress = self.canvas.create_arc(
            cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r,
            start=90, extent=0, style="arc", outline=theme["accent"], width=9,
        )
        self.items.extend([self.arc_track, self.arc_progress])

        # 指针
        self.hand_hour = self.canvas.create_line(cx, cy, cx, cy, fill=theme["text"],
                                                 width=max(4, int(r * 0.055)), capstyle="round")
        self.hand_minute = self.canvas.create_line(cx, cy, cx, cy, fill=theme["text"],
                                                   width=max(3, int(r * 0.035)), capstyle="round")
        self.hand_second = self.canvas.create_line(cx, cy, cx, cy, fill=theme["accent"],
                                                   width=max(1, int(r * 0.018)), capstyle="round")
        self.center_dot = self.canvas.create_oval(cx - 5, cy - 5, cx + 5, cy + 5,
                                                  fill=theme["accent"], outline="")
        self.sub_text = self.canvas.create_text(cx, cy + r * 0.42, text="", fill=theme["text_muted"],
                                                font=(UI_FONT_SMALL[0], max(9, int(r * 0.12)), "bold"))
        self.items.extend([self.hand_hour, self.hand_minute, self.hand_second, self.center_dot, self.sub_text])
        self._built = True

    # ------------------------------------------------------------------ 更新
    def update(self, hour: int, minute: int, second: int, progress: float,
               sub_text: str = "", running: bool = True) -> None:
        if not self._built:
            return
        cx, cy, r = self.cx, self.cy, self.r

        hour_angle = math.radians(((hour % 12) + minute / 60 + second / 3600) * 30)
        minute_angle = math.radians((minute + second / 60) * 6)
        second_angle = math.radians(second * 6)

        self._line(self.hand_hour, hour_angle, r * 0.50)
        self._line(self.hand_minute, minute_angle, r * 0.72)
        self._line(self.hand_second, second_angle, r * 0.80)

        extent = -359.9 * max(0.0, min(1.0, progress))
        self.canvas.itemconfigure(self.arc_progress, extent=extent)
        self.canvas.itemconfigure(self.arc_progress, outline=self.theme["accent"])
        self.canvas.itemconfigure(self.arc_track, outline=self.theme["track"])
        self.canvas.itemconfigure(self.hand_second, fill=self.theme["accent"] if running else self.theme["text_faint"])
        self.canvas.itemconfigure(self.sub_text, text=sub_text, fill=self.theme["text_muted"])
        self.canvas.coords(self.sub_text, cx, cy + r * 0.42)

    def _line(self, item: int, angle: float, length: float) -> None:
        x = self.cx + length * math.sin(angle)
        y = self.cy - length * math.cos(angle)
        self.canvas.coords(item, self.cx, self.cy, x, y)

    # ------------------------------------------------------------------ 其它
    def hide(self) -> None:
        for item in self.items:
            self.canvas.itemconfigure(item, state="hidden")

    def show(self) -> None:
        for item in self.items:
            self.canvas.itemconfigure(item, state="normal")

    def destroy(self) -> None:
        for item in self.items:
            self.canvas.delete(item)
        self.items = []
        self._built = False
