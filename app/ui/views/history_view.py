"""历史视图：查看、修改备注与删除历史计时记录。"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from ...models import STATUS_COMPLETED, STATUS_INTERRUPTED
from ...utils import format_duration, format_hms, short_datetime
from ..canvas_kit import UI_FONT, themed_text
from .base import BaseView


COLUMNS = (
    ("time", "开始时间", 118),
    ("mode", "模式", 76),
    ("planned", "计划", 84),
    ("actual", "实际", 84),
    ("status", "状态", 70),
    ("note", "备注", 150),
)


class HistoryView(BaseView):
    name = "history"

    def __init__(self, app, canvas):
        self.selected_id: str | None = None
        self.tree: ttk.Treeview | None = None
        self._tree_frame: tk.Frame | None = None
        self._tree_item_id: int | None = None
        self._note_widgets: dict[str, tk.Text] = {}
        self._note_item_ids: dict[str, int] = {}
        self._note_label_items: dict[str, int] = {}
        self._detail_items: dict[str, int] = {}
        self._detail_rows: list[tuple[str, int, int]] = []
        self._detail_title = None
        self._save_button = None
        self._delete_button = None
        self._empty_item = None
        super().__init__(app, canvas)

    # ================================================================= 构建
    def build(self) -> None:
        theme = self.theme
        records = self.app.storage.sorted_records()

        self.text(0.03, 0.065, "历史记录", anchor="w", size=16, weight="bold")
        total_seconds = self.app.storage.total_focus_seconds()
        stats = (f"共 {len(records)} 条 · 累计专注 {format_duration(total_seconds)} · "
                 f"完成 {self.app.storage.completed_count()} 次")
        self.text(0.03, 0.125, stats, anchor="w", size=10, fill=theme["text_muted"])

        # 左侧列表
        self._tree_frame = tk.Frame(self.canvas, bg=theme["surface"])
        self.tree = ttk.Treeview(self._tree_frame, columns=[c[0] for c in COLUMNS],
                                 show="headings", style="App.Treeview", selectmode="browse")
        for key, label, width in COLUMNS:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor="center", stretch=True)
        self.tree.tag_configure("completed", foreground=theme["text"])
        self.tree.tag_configure("interrupted", foreground=theme["warning"])
        scrollbar = ttk.Scrollbar(self._tree_frame, orient="vertical", command=self.tree.yview,
                                  style="App.Vertical.TScrollbar")
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree_item_id = self.widget(self._tree_frame, 0.03, 0.19, anchor="nw")

        # 右侧详情
        self.panel(0.70, 0.17, 0.27, 0.79, radius=16)
        self._detail_title = self.text(0.715, 0.22, "记录详情", anchor="w", size=12, weight="bold")

        self._detail_rows = []
        for key, label in (
            ("status", "状态"), ("mode", "计时模式"), ("clock", "时钟样式"),
            ("start", "开始时间"), ("end", "结束时间"), ("plan", "计划时长"),
            ("actual", "实际时长"), ("paused", "暂停情况"), ("span", "目标区间"),
        ):
            label_item = self.text(0.715, 0.30, label, anchor="w", size=10, fill=theme["text_muted"])
            value_item = self.text(0.955, 0.30, "—", anchor="e", size=10)
            self._detail_items[key] = value_item
            self._detail_rows.append((key, label_item, value_item))

        self._note_label_items["before"] = self.text(0.715, 0.60, "计时前备注", anchor="w",
                                                    size=10, fill=theme["text_muted"])
        self._note_widgets["before"] = themed_text(self.canvas, theme, height=2, width=24)
        self._note_item_ids["before"] = self.widget(
            self._note_widgets["before"], 0.715, 0.66, anchor="nw")

        self._note_label_items["after"] = self.text(0.715, 0.72, "计时后备注", anchor="w",
                                                   size=10, fill=theme["text_muted"])
        self._note_widgets["after"] = themed_text(self.canvas, theme, height=2, width=24)
        self._note_item_ids["after"] = self.widget(
            self._note_widgets["after"], 0.715, 0.78, anchor="nw")

        self._save_button = self.button(0.80, 0.90, "保存修改", self._save, width=112, height=38,
                                        radius=12, kind="primary", font=UI_FONT)
        self._delete_button = self.button(0.895, 0.90, "删除记录", self._delete, width=112,
                                          height=38, radius=12, kind="danger", font=UI_FONT)

        if not records:
            self._empty_item = self.text(0.5, 0.55, "暂无历史记录，去「计时」页面开始第一段专注吧",
                                         anchor="center", size=12, fill=theme["text_muted"])

        self._reload_tree(records)
        if records:
            self._select_first()

    # ================================================================= 布局
    def on_layout(self, width: int, height: int, ox: int, oy: int) -> None:
        if self._tree_item_id is not None:
            tree_w = max(360, width * 0.645)
            tree_h = max(200, height * 0.77)
            self.canvas.coords(self._tree_item_id, ox + 0.03 * width, oy + 0.19 * height)
            self.canvas.itemconfigure(self._tree_item_id, width=int(tree_w), height=int(tree_h))

        # 详情卡片内容自上而下堆叠，避免标签与输入框重叠
        x_label = ox + 0.715 * width
        x_value = ox + 0.955 * width
        cursor = oy + 0.17 * height + 18

        if self._detail_title is not None:
            self.canvas.coords(self._detail_title, x_label, cursor + 9)
        cursor += 16 + 14

        for _key, label_item, value_item in self._detail_rows:
            self.canvas.coords(label_item, x_label, cursor + 9)
            self.canvas.coords(value_item, x_value, cursor + 9)
            cursor += 24

        cursor += 12
        box_w = max(170, x_value - x_label + 4)
        for key in ("before", "after"):
            label_item = self._note_label_items.get(key)
            if label_item is not None:
                self.canvas.coords(label_item, x_label, cursor + 7)
            cursor += 14 + 5
            item = self._note_item_ids.get(key)
            if item is not None:
                self.canvas.coords(item, x_label, cursor)
                self.canvas.itemconfigure(item, width=int(box_w), height=42)
            cursor += 42 + 14

        center_x = (x_label + x_value) / 2
        if self._save_button:
            self._save_button.set_pos(center_x - 58, cursor + 17)
        if self._delete_button:
            self._delete_button.set_pos(center_x + 58, cursor + 17)

    # ================================================================= 数据
    def _reload_tree(self, records=None) -> None:
        if self.tree is None:
            return
        self.tree.delete(*self.tree.get_children())
        records = self.app.storage.sorted_records() if records is None else records
        for record in records:
            note = (record.note_before or record.note_after or "").replace("\n", " ")
            if len(note) > 22:
                note = note[:22] + "…"
            self.tree.insert(
                "", "end", iid=record.id,
                values=(short_datetime(record.start_time), record.mode_label,
                        self._plan_text(record), format_hms(record.actual_seconds),
                        record.status_label, note),
                tags=(record.status,),
            )

    @staticmethod
    def _plan_text(record) -> str:
        """正向计时没有计划时长，显示为「—」。"""
        return format_hms(record.planned_seconds) if record.planned_seconds else "—"

    def _select_first(self) -> None:
        children = self.tree.get_children()
        if children:
            self.tree.selection_set(children[0])
            self.tree.focus(children[0])

    def _on_select(self, _event=None) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        self.selected_id = selection[0]
        self._show_detail(self.selected_id)

    def _show_detail(self, record_id: str) -> None:
        record = self.app.storage.get_record(record_id)
        if record is None:
            return
        theme = self.theme
        color = theme["success"] if record.status == STATUS_COMPLETED else (
            theme["warning"] if record.status == STATUS_INTERRUPTED else theme["accent"])
        values = {
            "status": record.status_label,
            "mode": record.mode_label,
            "clock": record.clock_label,
            "start": record.start_time or "—",
            "end": record.end_time or "—",
            "plan": self._plan_text(record),
            "actual": format_hms(record.actual_seconds),
            "paused": f"{record.paused_count} 次 / {format_duration(record.paused_seconds)}",
            "span": record.span_label or "—",
        }
        for key, item in self._detail_items.items():
            self.canvas.itemconfigure(item, text=values.get(key, "—"))
            if key == "status":
                self.canvas.itemconfigure(item, fill=color)

        for key in ("before", "after"):
            widget = self._note_widgets.get(key)
            if widget is None:
                continue
            widget.configure(state="normal")
            widget.delete("1.0", "end")
            widget.insert("1.0", record.note_before if key == "before" else record.note_after)

    def _save(self) -> None:
        if not self.selected_id:
            return
        record = self.app.storage.get_record(self.selected_id)
        if record is None:
            return
        record.note_before = self._note_widgets["before"].get("1.0", "end").strip()
        record.note_after = self._note_widgets["after"].get("1.0", "end").strip()
        self.app.storage.update_record(record)
        self._reload_tree()
        self.tree.selection_set(record.id)
        messagebox.showinfo("保存成功", "备注已更新。")

    def _delete(self) -> None:
        if not self.selected_id:
            return
        record = self.app.storage.get_record(self.selected_id)
        if record is None:
            return
        if not messagebox.askyesno("删除确认", "确定要删除这条记录吗？删除后不可恢复。"):
            return
        self.app.storage.delete_record(record.id)
        self.selected_id = None
        self.app.refresh_view()
