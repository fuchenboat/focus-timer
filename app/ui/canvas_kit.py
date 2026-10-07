"""画布 UI 工具库：圆角矩形、画布按钮、以及各主题下的原生控件样式。"""
from __future__ import annotations

import itertools
import tkinter as tk
from tkinter import ttk

_FONT_FAMILY = "Microsoft YaHei UI"
_counter = itertools.count(1)

UI_FONT = (_FONT_FAMILY, 11)
UI_FONT_SMALL = (_FONT_FAMILY, 10)
UI_FONT_BOLD = (_FONT_FAMILY, 12, "bold")
TITLE_FONT = (_FONT_FAMILY, 17, "bold")
CLOCK_FONT = ("Consolas", 52, "bold")
CLOCK_FONT_SMALL = ("Consolas", 22, "bold")
MONO_FONT = ("Consolas", 12)


def round_rect_points(x1: float, y1: float, x2: float, y2: float, r: float) -> list[float]:
    """生成圆角矩形的多边形顶点（配合 smooth=True 使用）。"""
    r = max(0, min(r, (x2 - x1) / 2, (y2 - y1) / 2))
    return [
        x1 + r, y1,
        x2 - r, y1,
        x2, y1,
        x2, y1 + r,
        x2, y2 - r,
        x2, y2,
        x2 - r, y2,
        x1 + r, y2,
        x1, y2,
        x1, y2 - r,
        x1, y1 + r,
        x1, y1,
    ]


def create_round_rect(canvas: tk.Canvas, x1, y1, x2, y2, r=12, **kwargs) -> int:
    return canvas.create_polygon(
        round_rect_points(x1, y1, x2, y2, r), smooth=True, splinesteps=16, **kwargs
    )


def redraw_round_rect(canvas: tk.Canvas, item: int, x1, y1, x2, y2, r=12) -> None:
    canvas.coords(item, *round_rect_points(x1, y1, x2, y2, r))


def button_palette(theme, kind: str, selected: bool = False) -> dict:
    palette = {
        "primary": dict(bg=theme["accent"], fg=theme["accent_text"], hover=theme["accent_hover"], outline=""),
        "success": dict(bg=theme["success"], fg="#ffffff", hover=theme["success_hover"], outline=""),
        "danger": dict(bg=theme["danger"], fg="#ffffff", hover=theme["danger_hover"], outline=""),
        "secondary": dict(bg=theme["surface2"], fg=theme["text"], hover=theme["surface3"], outline=theme["border"]),
        "ghost": dict(bg="", fg=theme["text_muted"], hover=theme["surface2"], outline=""),
        "chip": dict(bg=theme["surface2"], fg=theme["text"], hover=theme["surface3"], outline=theme["border"]),
    }.get(kind, {})
    if selected:
        palette = dict(palette)
        palette["bg"] = theme["accent"]
        palette["fg"] = theme["accent_text"]
        palette["hover"] = theme["accent_hover"]
        palette["outline"] = ""
    return palette


class CanvasButton:
    """绘制在画布上的圆角按钮，支持悬停、选中、禁用状态。"""

    def __init__(
        self,
        canvas: tk.Canvas,
        theme,
        text: str,
        command=None,
        width: int = 120,
        height: int = 42,
        radius: int = 13,
        kind: str = "primary",
        font=None,
        outline_width: int = 1,
    ) -> None:
        self.canvas = canvas
        self.theme = theme
        self.text = text
        self.command = command
        self.w = width
        self.h = height
        self.radius = radius
        self.kind = kind
        self.font = font or UI_FONT
        self.outline_width = outline_width

        self.x = 0
        self.y = 0
        self._enabled = True
        self._selected = False
        self._hover = False
        self._visible = False

        self.tag = f"cbtn{next(_counter)}"
        self.body = create_round_rect(canvas, 0, 0, 0, 0, radius, fill=theme["surface2"], outline="")
        self.label = canvas.create_text(0, 0, text=text, font=self.font)
        canvas.itemconfigure(self.body, tags=(self.tag,))
        canvas.itemconfigure(self.label, tags=(self.tag,))
        canvas.tag_bind(self.tag, "<Button-1>", self._on_click)
        canvas.tag_bind(self.tag, "<Enter>", self._on_enter)
        canvas.tag_bind(self.tag, "<Leave>", self._on_leave)
        self._draw()

    # ------------------------------------------------------------------ 状态
    def _palette(self) -> dict:
        return button_palette(self.theme, self.kind, self._selected)

    def _draw(self) -> None:
        palette = self._palette()
        fill = palette["bg"]
        fg = palette["fg"]
        outline = palette["outline"]
        width = self.outline_width
        if not self._enabled:
            fill = self.theme["surface2"]
            fg = self.theme["text_faint"]
            outline = ""
        elif self._hover and fill:
            fill = palette["hover"]
        if not fill:
            fill = ""
            outline = outline or self.theme["border"]
        redraw_round_rect(self.canvas, self.body, self.x - self.w / 2, self.y - self.h / 2,
                          self.x + self.w / 2, self.y + self.h / 2, self.radius)
        self.canvas.itemconfigure(self.body, fill=fill, outline=outline, width=width)
        self.canvas.itemconfigure(self.label, fill=fg, text=self.text, font=self.font)
        self.canvas.coords(self.label, self.x, self.y)

    # ------------------------------------------------------------------ 事件
    def _on_click(self, _event=None) -> None:
        if self._enabled and self.command:
            self.command()

    def _on_enter(self, _event=None) -> None:
        if not self._enabled:
            return
        self._hover = True
        self.canvas.configure(cursor="hand2")
        self._draw()

    def _on_leave(self, _event=None) -> None:
        self._hover = False
        self.canvas.configure(cursor="")
        self._draw()

    # ------------------------------------------------------------------ 接口
    def set_pos(self, x: float, y: float) -> None:
        self.x, self.y = x, y
        self._draw()

    def set_text(self, text: str) -> None:
        self.text = text
        self._draw()

    def set_kind(self, kind: str) -> None:
        self.kind = kind
        self._draw()

    def set_selected(self, selected: bool) -> None:
        self._selected = bool(selected)
        self._draw()

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = bool(enabled)
        self._draw()

    def set_visible(self, visible: bool) -> None:
        self._visible = bool(visible)
        state = "normal" if visible else "hidden"
        self.canvas.itemconfigure(self.body, state=state)
        self.canvas.itemconfigure(self.label, state=state)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def destroy(self) -> None:
        self.canvas.delete(self.tag)


# ---------------------------------------------------------------- 原生控件样式
def themed_entry(parent, theme, width=10, font=None, justify="center", textvariable=None) -> tk.Entry:
    return tk.Entry(
        parent,
        width=width,
        font=font or UI_FONT,
        justify=justify,
        textvariable=textvariable,
        bg=theme["surface2"],
        fg=theme["text"],
        insertbackground=theme["text"],
        disabledbackground=theme["surface3"],
        disabledforeground=theme["text_faint"],
        relief="flat",
        highlightthickness=1,
        highlightbackground=theme["border"],
        highlightcolor=theme["accent"],
        bd=0,
    )


def themed_text(parent, theme, height=3, font=None, width=30) -> tk.Text:
    return tk.Text(
        parent,
        height=height,
        width=width,
        font=font or UI_FONT,
        bg=theme["surface2"],
        fg=theme["text"],
        insertbackground=theme["text"],
        relief="flat",
        highlightthickness=1,
        highlightbackground=theme["border"],
        highlightcolor=theme["accent"],
        bd=0,
        wrap="word",
    )


def configure_ttk_styles(theme, root) -> None:
    """统一配置 Treeview / Scale 等 ttk 控件样式。"""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(
        "App.Treeview",
        background=theme["surface"],
        fieldbackground=theme["surface"],
        foreground=theme["text"],
        rowheight=32,
        borderwidth=0,
        relief="flat",
        font=UI_FONT,
    )
    style.map(
        "App.Treeview",
        background=[("selected", theme["accent"])],
        foreground=[("selected", theme["accent_text"])],
    )
    style.configure(
        "App.Treeview.Heading",
        background=theme["surface2"],
        foreground=theme["text_muted"],
        relief="flat",
        borderwidth=0,
        font=UI_FONT_SMALL,
        padding=(6, 6),
    )
    style.map("App.Treeview.Heading", background=[("active", theme["surface3"])])
    style.configure(
        "App.Vertical.TScrollbar",
        background=theme["surface2"],
        troughcolor=theme["surface"],
        bordercolor=theme["surface"],
        arrowcolor=theme["text_muted"],
        relief="flat",
    )
    style.configure(
        "App.Horizontal.TScale",
        background=theme["surface2"],
        troughcolor=theme["track"],
        bordercolor=theme["surface"],
        lightcolor=theme["accent"],
        darkcolor=theme["accent"],
    )
