"""视图基类：统一的画布元素创建、按比例布局与销毁。"""
from __future__ import annotations

import tkinter as tk

from ..canvas_kit import CanvasButton, UI_FONT, create_round_rect, redraw_round_rect


class BaseView:
    """所有页面视图的基类。

    布局约定：
    - text / widget：relx、rely 为锚点相对内容区的比例；
    - panel：relx、rely 为左上角比例，relw、relh 为相对宽高；
    - button：relx、rely 为按钮中心点比例。
    """

    name = "base"

    def __init__(self, app, canvas: tk.Canvas) -> None:
        self.app = app
        self.canvas = canvas
        self.theme = app.theme
        self.w = 0
        self.h = 0
        self.ox = 0
        self.oy = 0
        self._layout: list[dict] = []
        self._items: list[int] = []
        self._widgets: list[tk.Widget] = []
        self._buttons: list[CanvasButton] = []
        self.build()

    # ---------------------------------------------------------------- 创建元素
    def text(self, relx, rely, content, *, anchor="center", size=11, weight="normal",
             fill=None, family="Microsoft YaHei UI", dx=0, dy=0) -> int:
        item = self.canvas.create_text(
            0, 0, text=content, anchor=anchor,
            fill=fill or self.theme["text"], font=(family, size, weight),
        )
        self._items.append(item)
        self._layout.append({"type": "text", "id": item, "relx": relx, "rely": rely,
                             "anchor": anchor, "dx": dx, "dy": dy})
        return item

    def panel(self, relx, rely, relw, relh, *, radius=16, fill=None, outline="",
              width=1, stipple="", dx=0, dy=0) -> int:
        if fill is None:
            fill = self.app.panel_fill()
            if not stipple:
                stipple = self.app.panel_stipple()
        item = create_round_rect(self.canvas, 0, 0, 0, 0, radius, fill=fill,
                                 outline=outline, width=width, stipple=stipple)
        self._items.append(item)
        self._layout.append({"type": "panel", "id": item, "relx": relx, "rely": rely,
                             "relw": relw, "relh": relh, "radius": radius, "dx": dx, "dy": dy})
        return item

    def widget(self, wdg: tk.Widget, relx, rely, *, anchor="center", dx=0, dy=0,
               width=None, height=None) -> int:
        item = self.canvas.create_window(0, 0, window=wdg, anchor=anchor)
        if width:
            self.canvas.itemconfigure(item, width=width)
        if height:
            self.canvas.itemconfigure(item, height=height)
        self._widgets.append(wdg)
        self._layout.append({"type": "widget", "id": item, "relx": relx, "rely": rely,
                             "anchor": anchor, "dx": dx, "dy": dy})
        return item

    def button(self, relx, rely, content, command, *, width=120, height=42, radius=13,
               kind="primary", font=None, dx=0, dy=0) -> CanvasButton:
        btn = CanvasButton(self.canvas, self.theme, content, command, width=width,
                           height=height, radius=radius, kind=kind, font=font or UI_FONT)
        btn.set_visible(True)
        self._buttons.append(btn)
        self._layout.append({"type": "button", "obj": btn, "relx": relx, "rely": rely,
                             "dx": dx, "dy": dy})
        return btn

    # ---------------------------------------------------------------- 布局
    def relayout(self, width: int, height: int, ox: int = 0, oy: int = 0) -> None:
        self.w, self.h, self.ox, self.oy = width, height, ox, oy
        for entry in self._layout:
            x = ox + entry["relx"] * width + entry.get("dx", 0)
            y = oy + entry["rely"] * height + entry.get("dy", 0)
            kind = entry["type"]
            if kind in ("text", "widget"):
                self.canvas.coords(entry["id"], x, y)
            elif kind == "panel":
                redraw_round_rect(
                    self.canvas, entry["id"], x, y,
                    x + entry["relw"] * width, y + entry["relh"] * height,
                    entry["radius"],
                )
            elif kind == "button":
                entry["obj"].set_pos(x, y)
        self.on_layout(width, height, ox, oy)

    def on_layout(self, width: int, height: int, ox: int, oy: int) -> None:
        """子类可覆写，用于额外的自定义元素定位。"""

    def place_row(self, buttons, x: float, y: float, gap: float = 10) -> float:
        """把一组按钮从左到右排列，返回排列结束后的 x。"""
        cursor = x
        for button in buttons:
            button.set_pos(cursor + button.w / 2, y)
            cursor += button.w + gap
        return cursor

    def place_wrapped(self, buttons, x: float, y: float, limit_x: float,
                      gap: float = 8, row_h: float = 44) -> int:
        """从左到右排列并在超出右边界时自动换行，返回占用行数。"""
        cursor_x = x
        cursor_y = y
        rows = 1
        for button in buttons:
            if cursor_x + button.w > limit_x and cursor_x > x:
                cursor_x = x
                cursor_y += row_h
                rows += 1
            button.set_pos(cursor_x + button.w / 2, cursor_y)
            cursor_x += button.w + gap
        return rows

    # ---------------------------------------------------------------- 生命周期
    def build(self) -> None:
        """创建界面元素，由子类实现。"""

    def tick(self) -> None:
        """定时刷新，由子类按需实现。"""

    def on_show(self) -> None:
        """切换到该视图时调用。"""

    def on_hide(self) -> None:
        """离开该视图时调用。"""

    def destroy(self) -> None:
        self.on_hide()
        for widget in self._widgets:
            try:
                widget.destroy()
            except tk.TclError:
                pass
        for button in self._buttons:
            button.destroy()
        for item in self._items:
            self.canvas.delete(item)
        self._widgets = []
        self._buttons = []
        self._items = []
        self._layout = []
