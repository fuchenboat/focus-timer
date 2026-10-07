"""主窗口：画布背景 + 顶部导航 + 视图切换 + 计时会话管理。"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import messagebox

from .. import config, sound
from ..config import APP_NAME
from ..models import STATUS_COMPLETED, STATUS_INTERRUPTED, STATUS_RUNNING, Record, now_str
from ..storage import Storage
from ..theme import Theme
from ..timer_engine import TimerEngine
from ..utils import current_hm, format_duration, format_hms, shift_hm
from .canvas_kit import TITLE_FONT, UI_FONT, UI_FONT_SMALL, CanvasButton, configure_ttk_styles
from .dialogs import ask_note
from .views.history_view import HistoryView
from .views.settings_view import SettingsView
from .views.timer_view import TimerView
from .wallpaper import Wallpaper


class TimeFocusApp:
    TICK_MS = 200

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.minsize(*config.MIN_WINDOW_SIZE)
        self._apply_window_icon()

        self.storage = Storage()
        self.settings = self.storage.settings
        self.theme = Theme(self.settings.get("theme", "dark"))
        self.engine = TimerEngine()
        self.session: dict | None = None
        self._finishing = False
        self._tick_id = None

        presets = self.settings.get("presets") or config.DEFAULT_PRESETS
        now_hm = current_hm()
        self.timer_config = {
            "mode": self.settings.get("last_mode", "countdown"),
            "clock_type": self.settings.get("last_clock", "digital"),
            "preset_minutes": presets[0] if presets else 30,
            "use_custom": False,
            "custom_minutes": "45",
            "target_start": now_hm,
            "target_end": shift_hm(now_hm, 60),
            "note_before": "",
        }

        width, height = self.settings.get("window_size") or config.DEFAULT_WINDOW_SIZE
        width = max(config.MIN_WINDOW_SIZE[0], int(width))
        height = max(config.MIN_WINDOW_SIZE[1], int(height))
        self.root.geometry(f"{width}x{height}")

        self.canvas = tk.Canvas(self.root, highlightthickness=0, bd=0, bg=self.theme["bg"])
        self.canvas.pack(fill="both", expand=True)
        self.wallpaper = Wallpaper(self.canvas)

        self._header_items: list[int] = []
        self.nav_buttons: dict[str, CanvasButton] = {}
        self.current_view = None
        self.current_key = "timer"
        self._size = (0, 0)
        self._status_cache = ""

        self.view_classes = {"timer": TimerView, "history": HistoryView, "settings": SettingsView}

        self._cleanup_stale_sessions()
        configure_ttk_styles(self.theme, self.root)

        self.root.update_idletasks()
        self._size = (self.root.winfo_width(), self.root.winfo_height())
        self._build_header()
        self._layout_all()
        self.show_view("timer", force=True)

        self.root.bind("<Configure>", self._on_configure)
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._tick_id = self.root.after(self.TICK_MS, self._tick)

    def _apply_window_icon(self) -> None:
        icon = os.path.join(config.get_resource_dir(), "assets", "icon.ico")
        if os.path.exists(icon):
            try:
                self.root.iconbitmap(icon)
            except tk.TclError:
                pass

    # ------------------------------------------------------------------ 尺寸
    @property
    def content_box(self):
        w = max(1, self._size[0])
        h = max(1, self._size[1])
        return w, max(1, h - config.HEADER_HEIGHT), 0, config.HEADER_HEIGHT

    def _on_configure(self, event) -> None:
        if event.widget is not self.root:
            return
        size = (event.width, event.height)
        if size == self._size:
            return
        self._size = size
        self._layout_all()

    def _layout_all(self) -> None:
        width, height = self._size
        if width <= 1 or height <= 1:
            return
        self.wallpaper.draw(width, height, self.storage.background_abspath(),
                            self.settings.get("background_overlay", 0.55), self.theme["bg"])
        self._layout_header(width, height)
        if self.current_view is not None:
            cw, ch, ox, oy = self.content_box
            self.current_view.relayout(cw, ch, ox, oy)

    # ------------------------------------------------------------------ 顶部栏
    def _build_header(self) -> None:
        theme = self.theme
        self._header_items = []
        self.nav_buttons = {}
        self._status_cache = ""

        self.header_panel = self.canvas.create_rectangle(
            0, 0, 0, 0, fill=theme["surface"], outline="", tags=("header",))
        self.header_line = self.canvas.create_line(
            0, 0, 0, 0, fill=theme["border"], width=1, tags=("header",))
        self.header_title = self.canvas.create_text(
            0, 0, text=APP_NAME, anchor="w", fill=theme["text"], font=TITLE_FONT, tags=("header",))
        self.header_subtitle = self.canvas.create_text(
            0, 0, text="保持专注 · 记录每一段时间", anchor="w",
            fill=theme["text_muted"], font=UI_FONT_SMALL, tags=("header",))
        self.status_text = self.canvas.create_text(
            0, 0, text="", anchor="e", fill=theme["accent"], font=UI_FONT, tags=("header",))
        self._header_items.extend([self.header_panel, self.header_line, self.header_title,
                                   self.header_subtitle, self.status_text])

        for key, label in (("timer", "计时"), ("history", "历史"), ("settings", "设置")):
            button = CanvasButton(self.canvas, theme, label, lambda k=key: self.show_view(k),
                                  width=84, height=38, radius=11, kind="ghost", font=UI_FONT)
            button.set_visible(True)
            self.nav_buttons[key] = button

    def _layout_header(self, width: int, height: int) -> None:
        hh = config.HEADER_HEIGHT
        self.canvas.coords(self.header_panel, 0, 0, width, hh)
        self.canvas.coords(self.header_line, 0, hh, width, hh)
        stipple = "gray50" if self.has_wallpaper() else ""
        self.canvas.itemconfigure(self.header_panel, stipple=stipple)
        self.canvas.coords(self.header_title, 26, 24)
        self.canvas.coords(self.header_subtitle, 27, 46)

        right = width - 20
        for key in ("settings", "history", "timer"):
            button = self.nav_buttons.get(key)
            if button:
                button.set_pos(right - 42, hh / 2)
                right -= 92
        self.canvas.coords(self.status_text, right - 8, hh / 2)

    def _update_status(self) -> None:
        theme = self.theme
        text = ""
        color = theme["accent"]
        if self.session is not None:
            if self.engine.is_paused:
                text = f"已暂停 · {format_hms(self.engine.display_seconds)}"
                color = theme["warning"]
            else:
                text = f"专注中 · {format_hms(self.engine.display_seconds)}"
                color = theme["accent"]
        if text != self._status_cache:
            self._status_cache = text
            self.canvas.itemconfigure(self.status_text, text=text, fill=color)

    # ------------------------------------------------------------------ 视图
    def show_view(self, key: str, force: bool = False) -> None:
        if self.current_view is not None and self.current_key == key and not force:
            return
        if self.current_view is not None:
            self.current_view.destroy()
            self.current_view = None
        cls = self.view_classes.get(key)
        if cls is None:
            return
        self.current_key = key
        self.current_view = cls(self, self.canvas)
        cw, ch, ox, oy = self.content_box
        self.current_view.relayout(cw, ch, ox, oy)
        self.current_view.on_show()
        for name, button in self.nav_buttons.items():
            button.set_selected(name == key)

    def refresh_view(self) -> None:
        self.show_view(self.current_key, force=True)

    # ------------------------------------------------------------------ 主题/外观
    def has_wallpaper(self) -> bool:
        return bool(self.storage.background_abspath())

    def panel_fill(self) -> str:
        return self.theme["surface"]

    def panel_stipple(self) -> str:
        return "gray50" if self.has_wallpaper() else ""

    def apply_theme(self, name: str) -> None:
        self.settings["theme"] = name
        self.theme.set(name)
        self.storage.save_settings()
        self.canvas.configure(bg=self.theme["bg"])
        self.rebuild()

    def set_background(self, path: str) -> None:
        filename = self.storage.save_background(path)
        self.settings["background_image"] = filename
        self.storage.save_settings()
        self.refresh_view()
        self._layout_all()

    def clear_background(self) -> None:
        self.storage.clear_background()
        self.refresh_view()
        self._layout_all()

    def update_overlay(self, value: float) -> None:
        self.settings["background_overlay"] = round(float(value), 3)
        self.storage.save_settings()
        self._layout_all()

    def rebuild(self) -> None:
        if self.current_view is not None:
            self.current_view.destroy()
            self.current_view = None
        self._destroy_header()
        configure_ttk_styles(self.theme, self.root)
        self._build_header()
        self._layout_all()
        self.show_view(self.current_key, force=True)
        self._update_status()

    def _destroy_header(self) -> None:
        for item in self._header_items:
            self.canvas.delete(item)
        self._header_items = []
        for button in self.nav_buttons.values():
            button.destroy()
        self.nav_buttons = {}

    # ------------------------------------------------------------------ 计时会话
    def start_session(self, mode: str, clock_type: str, planned_seconds: int,
                      target_start: str, target_end: str, note_before: str) -> None:
        if self.session is not None:
            return
        engine = self.engine
        if mode == "target":
            engine.configure_target(target_start, target_end)
            planned = int(engine.total)
        elif mode == "countup":
            engine.configure_countup()
            planned = 0
        else:
            engine.configure_countdown(planned_seconds)
            planned = int(planned_seconds)
        engine.mode = mode
        engine.clock_type = clock_type

        record = Record(
            mode=mode,
            clock_type=clock_type,
            planned_seconds=planned,
            start_time=now_str(),
            status=STATUS_RUNNING,
            note_before=note_before,
            target_start=target_start if mode == "target" else "",
            target_end=target_end if mode == "target" else "",
        )
        self.storage.add_record(record)
        self.session = {"record": record}

        self.settings["last_mode"] = mode
        self.settings["last_clock"] = clock_type
        self.storage.save_settings()

        engine.start()
        self.show_view("timer", force=True)
        self._update_status()

    def toggle_pause(self) -> None:
        if self.session is None:
            return
        self.engine.toggle_pause()
        self._update_status()
        if self.current_view is not None:
            self.current_view.tick()

    def request_stop(self) -> None:
        """用户主动结束。正向计时没有预设终点，结束即视为「已完成」。"""
        if self.session is None:
            return
        self.finish_session(completed=self.engine.mode == "countup")

    def finish_session(self, completed: bool) -> None:
        if self.session is None or self._finishing:
            return
        self._finishing = True
        record: Record = self.session["record"]
        engine = self.engine
        engine.stop()

        record.actual_seconds = int(round(engine.elapsed))
        record.end_time = now_str()
        record.status = STATUS_COMPLETED if completed else STATUS_INTERRUPTED
        record.paused_count = engine.paused_count
        record.paused_seconds = int(round(engine.paused_seconds))
        self.storage.update_record(record)
        self.session = None

        enabled = bool(self.settings.get("sound_enabled", True))
        if completed:
            sound.play_finish(enabled=enabled)
            self._flash_window()
        self.show_view("timer", force=True)
        self._update_status()
        self.root.update_idletasks()

        if record.mode == "countup":
            title = "正向计时结束"
            message = (f"本次共计时 {format_duration(record.actual_seconds)}，已保存到历史记录。\n"
                       f"可以补充一条结束备注（也可以跳过）。")
        elif completed:
            title = "计时结束"
            message = (f"本次专注已完成，共 {format_duration(record.actual_seconds)}。\n"
                       f"可以补充一条结束备注（也可以跳过）。")
        else:
            title = "计时已中断"
            message = (f"本次计时提前结束，已记录 {format_duration(record.actual_seconds)}。\n"
                       f"可以补充一条结束备注（也可以跳过）。")
        note = ask_note(self.root, self.theme, title, message, initial=record.note_after or "")
        if note:
            record.note_after = note
            self.storage.update_record(record)
        self._finishing = False

    def _flash_window(self) -> None:
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.after(1500, lambda: self.root.attributes("-topmost", False))
        except tk.TclError:
            pass

    def _cleanup_stale_sessions(self) -> None:
        """把上次异常退出时仍在进行中的记录标记为中断。"""
        stale = self.storage.running_records()
        if not stale:
            return
        for record in stale:
            record.status = STATUS_INTERRUPTED
            record.end_time = record.end_time or now_str()
            suffix = "程序退出，计时自动中断"
            record.note_after = f"{record.note_after} {suffix}".strip()
        self.storage.save_records()

    # ------------------------------------------------------------------ 主循环
    def _tick(self) -> None:
        try:
            if self.session is not None and not self._finishing:
                # 只有存在预设终点的模式才自动结束，正向计时需手动结束
                if (self.engine.total > 0 and self.engine.state == "running"
                        and self.engine.remaining <= 0):
                    self.finish_session(completed=True)
            self._update_status()
            if self.current_view is not None:
                self.current_view.tick()
        finally:
            self._tick_id = self.root.after(self.TICK_MS, self._tick)

    # ------------------------------------------------------------------ 退出
    def on_close(self) -> None:
        if self.session is not None:
            record: Record = self.session["record"]
            is_countup = record.mode == "countup"
            if is_countup:
                question = (f"当前正向计时已进行 {format_duration(self.engine.elapsed)}，\n"
                            f"退出将保存本次时长并结束计时，确定退出吗？")
            else:
                question = "当前还有正在进行的计时，退出将记为「已中断」，确定退出吗？"
            if not messagebox.askyesno("退出确认", question):
                return
            self.engine.stop()
            record.actual_seconds = int(round(self.engine.elapsed))
            record.end_time = now_str()
            record.paused_count = self.engine.paused_count
            record.paused_seconds = int(round(self.engine.paused_seconds))
            if is_countup:
                # 正向计时以「关闭软件」作为正常结束方式
                record.status = STATUS_COMPLETED
            else:
                record.status = STATUS_INTERRUPTED
                record.note_after = (record.note_after + " 退出程序中断").strip()
            self.storage.update_record(record)
            self.session = None
        try:
            self.settings["window_size"] = [self.root.winfo_width(), self.root.winfo_height()]
            self.storage.save_settings()
        except Exception:
            pass
        if self._tick_id is not None:
            try:
                self.root.after_cancel(self._tick_id)
            except tk.TclError:
                pass
            self._tick_id = None
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()
