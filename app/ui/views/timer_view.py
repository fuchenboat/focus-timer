"""计时视图：支持倒计时 / 目标时刻两种模式，电子与传统两种时钟。"""
from __future__ import annotations

import tkinter as tk

from ... import config
from ...models import CLOCK_LABELS
from ...utils import format_duration, format_hms, parse_hm, span_minutes
from ..analog_clock import AnalogClock
from ..canvas_kit import UI_FONT_SMALL, create_round_rect, redraw_round_rect, themed_entry
from ..dialogs import show_message
from .base import BaseView


class TimerView(BaseView):
    name = "timer"

    def __init__(self, app, canvas):
        self.cfg = app.timer_config
        self._pixel_widgets: dict[str, tuple[tk.Widget, int]] = {}
        self._analog: AnalogClock | None = None
        self._clock_item = None
        self._status_item = None
        self._info_item = None
        self._sub_item = None
        self._note_item = None
        self._caption_item = None
        self._prog_track = None
        self._prog_fill = None
        self._prog_geom = (0, 0, 0, 0)
        self._pause_button = None
        self._stop_button = None
        self._start_button = None
        self._mode_buttons: dict[str, object] = {}
        self._clock_buttons: dict[str, object] = {}
        self._preset_buttons: list = []
        self._custom_button = None
        self._arrow_item = None
        self._custom_hint_item = None
        self._label_mode = None
        self._label_clock = None
        self._label_span = None
        self._label_note = None
        self._hint_item = None
        self._preview_item = None
        self._vars: dict[str, tk.StringVar] = {}

        super().__init__(app, canvas)

    # ================================================================= 构建
    def build(self) -> None:
        if self.app.session is not None:
            self._build_running()
        else:
            self._build_setup()

    # ------------------------------------------------------------ 设置状态界面
    def _build_setup(self) -> None:
        theme = self.theme
        cfg = self.cfg

        # 左侧配置卡片 / 右侧预览卡片
        self.panel(0.032, 0.06, 0.45, 0.88, radius=18)
        self.panel(0.50, 0.06, 0.468, 0.88, radius=18)

        self._label_mode = self.text(0.058, 0.115, "计时模式", anchor="w", size=10,
                                     fill=theme["text_muted"])

        self._mode_buttons = {}
        for key, label in (("countdown", "倒计时"), ("target", "目标时刻"), ("countup", "正向计时")):
            button = self.button(0.5, 0.5, label, lambda k=key: self._set_mode(k),
                                 width=110, height=38, radius=11, kind="chip")
            button.set_selected(cfg["mode"] == key)
            self._mode_buttons[key] = button

        self._label_clock = self.text(0.058, 0.245, "时钟样式", anchor="w", size=10,
                                      fill=theme["text_muted"])
        self._clock_buttons = {}
        for key, label in (("digital", "电子时钟"), ("analog", "传统时钟")):
            button = self.button(0.5, 0.5, label, lambda k=key: self._set_clock(k),
                                 width=118, height=38, radius=11, kind="chip")
            button.set_selected(cfg["clock_type"] == key)
            self._clock_buttons[key] = button

        self._label_span = self.text(0.058, 0.375,
                                     "计时说明" if cfg["mode"] == "countup" else "时长 / 区间",
                                     anchor="w", size=10, fill=theme["text_muted"])

        if cfg["mode"] == "countdown":
            self._preset_buttons = []
            for minutes in (self.app.settings.get("presets") or config.DEFAULT_PRESETS):
                button = self.button(0.5, 0.5, self._preset_label(minutes),
                                     lambda m=minutes: self._set_preset(m),
                                     width=96, height=36, radius=11, kind="chip", font=UI_FONT_SMALL)
                button.set_selected(not cfg["use_custom"] and cfg["preset_minutes"] == minutes)
                self._preset_buttons.append(button)
            self._custom_button = self.button(0.5, 0.5, "自定义",
                                              self._set_custom, width=80, height=36,
                                              radius=11, kind="chip", font=UI_FONT_SMALL)
            self._custom_button.set_selected(cfg["use_custom"])

            self._vars["custom_minutes"] = tk.StringVar(value=str(cfg["custom_minutes"]))
            self._vars["custom_minutes"].trace_add("write", lambda *_: self._on_custom_change())
            entry = themed_entry(self.canvas, theme, width=6, justify="center",
                                 textvariable=self._vars["custom_minutes"])
            item = self.widget(entry, 0.0, 0.0, anchor="w")
            self._pixel_widgets["custom_minutes"] = (entry, item)
            self._custom_hint_item = self.text(0.058, 0.555, "自定义分钟数（1 - 1440）",
                                               anchor="w", size=9, fill=theme["text_faint"])
        elif cfg["mode"] == "target":
            self._vars["target_start"] = tk.StringVar(value=cfg["target_start"])
            self._vars["target_start"].trace_add("write", lambda *_: self._refresh_preview())
            self._vars["target_end"] = tk.StringVar(value=cfg["target_end"])
            self._vars["target_end"].trace_add("write", lambda *_: self._refresh_preview())
            start_entry = themed_entry(self.canvas, theme, width=8, justify="center",
                                       textvariable=self._vars["target_start"])
            end_entry = themed_entry(self.canvas, theme, width=8, justify="center",
                                     textvariable=self._vars["target_end"])
            si = self.widget(start_entry, 0.0, 0.0, anchor="w")
            ei = self.widget(end_entry, 0.0, 0.0, anchor="w")
            self._pixel_widgets["target_start"] = (start_entry, si)
            self._pixel_widgets["target_end"] = (end_entry, ei)
            self._arrow_item = self.text(0.0, 0.0, "→", anchor="center", size=13,
                                         fill=theme["text_muted"])
            self._hint_item = self.text(0.058, 0.555, "开始时刻 → 结束时刻（24 小时制，例如 09:00 → 11:00）",
                                        anchor="w", size=9, fill=theme["text_faint"])
        else:
            self._hint_item = self.text(0.058, 0.555, "启动后从 0 开始正向累加，结束或关闭软件即记录时长",
                                        anchor="w", size=9, fill=theme["text_faint"])

        self._label_note = self.text(0.058, 0.645, "计时前备注", anchor="w", size=10,
                                     fill=theme["text_muted"])
        self._vars["note_before"] = tk.StringVar(value=cfg.get("note_before", ""))
        self._vars["note_before"].trace_add("write", lambda *_: self._sync_note())
        note_entry = themed_entry(self.canvas, theme, width=40, justify="left",
                                  textvariable=self._vars["note_before"])
        ni = self.widget(note_entry, 0.0, 0.0, anchor="w")
        self._pixel_widgets["note_before"] = (note_entry, ni)

        self._start_button = self.button(0.5, 0.5, "开始计时", self._start, width=220, height=54,
                                         radius=16, kind="primary", font=("Microsoft YaHei UI", 14, "bold"))

        # 右侧预览
        self._caption_item = self.text(0.734, 0.115, "时钟预览", anchor="center", size=10,
                                       fill=theme["text_muted"])
        if cfg["clock_type"] == "digital":
            self._clock_item = self.text(0.734, 0.50, "00:00:00", anchor="center", size=40,
                                         weight="bold", family="Consolas", fill=theme["text"])
        else:
            self._analog = AnalogClock(self.canvas, theme)
        self._preview_item = self.text(0.734, 0.86, "", anchor="center", size=11,
                                       fill=theme["text_muted"])
        self._refresh_preview()

    # ------------------------------------------------------------ 运行中界面
    def _build_running(self) -> None:
        theme = self.theme
        cfg = self.cfg
        engine = self.app.engine

        self._status_item = self.text(0.5, 0.075, "已暂停" if engine.is_paused else "专注中",
                                      anchor="center", size=16, weight="bold",
                                      fill=theme["warning"] if engine.is_paused else theme["accent"])
        self._info_item = self.text(0.5, 0.13, self._running_info_text(), anchor="center",
                                    size=10, fill=theme["text_muted"])

        if cfg["clock_type"] == "digital":
            self._clock_item = self.text(0.5, 0.45, format_hms(engine.remaining), anchor="center",
                                         size=64, weight="bold", family="Consolas",
                                         fill=theme["text"])
        else:
            self._analog = AnalogClock(self.canvas, theme)
        self._sub_item = self.text(0.5, 0.63, "", anchor="center", size=10,
                                   fill=theme["text_muted"])

        if engine.mode != "countup":
            self._prog_track = create_round_rect(self.canvas, 0, 0, 0, 0, 6,
                                                 fill=theme["track"], outline="")
            self._prog_fill = create_round_rect(self.canvas, 0, 0, 0, 0, 6,
                                                fill=theme["accent"], outline="")
            self._items.extend([self._prog_track, self._prog_fill])

        note = cfg.get("note_before", "")
        self._note_item = self.text(0.5, 0.825, f"备注：{note}" if note else "",
                                    anchor="center", size=10, fill=theme["text_faint"])

        self._pause_button = self.button(0.44, 0.905, self._pause_label(), self.app.toggle_pause,
                                         width=150, height=48, radius=14, kind="secondary",
                                         font=("Microsoft YaHei UI", 12, "bold"))
        self._stop_button = self.button(0.58, 0.905, "结束计时", self._confirm_stop,
                                        width=150, height=48, radius=14, kind="danger",
                                        font=("Microsoft YaHei UI", 12, "bold"))

    def _running_info_text(self) -> str:
        cfg = self.cfg
        engine = self.app.engine
        clock_label = CLOCK_LABELS.get(cfg["clock_type"], "")
        if engine.mode == "countup":
            return f"正向计时 · 已进行 {format_duration(engine.elapsed)} · {clock_label}"
        if engine.mode == "target":
            return f"目标时刻 · {engine.target_start} → {engine.target_end} · {clock_label}"
        return f"倒计时 · {format_duration(engine.total)} · {clock_label}"

    def _pause_label(self) -> str:
        return "继续计时" if self.app.engine.is_paused else "暂停计时"

    # ================================================================= 布局
    def on_layout(self, width: int, height: int, ox: int, oy: int) -> None:
        if self.app.session is not None:
            self._layout_running(width, height, ox, oy)
        else:
            self._layout_setup(width, height, ox, oy)

    def _layout_setup(self, width: int, height: int, ox: int, oy: int) -> None:
        """左侧配置卡片按顺序自上而下堆叠，避免文字与控件重叠。"""
        cfg = self.cfg
        x0 = ox + 0.058 * width
        limit_x = ox + 0.482 * width - 16
        card_left = ox + 0.032 * width
        card_width = 0.45 * width
        inner_width = card_width - 56

        label_h = 16
        label_gap = 10
        block_gap = 26
        cursor = oy + 0.085 * height

        def place_label(item):
            if item is not None:
                self.canvas.coords(item, x0, cursor + label_h / 2)
            return label_h + label_gap

        # 计时模式
        cursor += place_label(self._label_mode)
        self.place_row(list(self._mode_buttons.values()), x0, cursor + 19)
        cursor += 38 + block_gap

        # 时钟样式
        cursor += place_label(self._label_clock)
        self.place_row(list(self._clock_buttons.values()), x0, cursor + 19)
        cursor += 38 + block_gap

        # 时长 / 区间
        cursor += place_label(self._label_span)
        if cfg["mode"] == "countdown":
            rows = self.place_wrapped(self._preset_buttons + [self._custom_button],
                                      x0, cursor + 18, limit_x, gap=8, row_h=44)
            cursor += 36 + (rows - 1) * 44 + 24
            cursor += place_label(self._custom_hint_item)
            self._place_widget("custom_minutes", x0, cursor + 15, width=90)
            cursor += 30 + block_gap
        elif cfg["mode"] == "target":
            self._place_widget("target_start", x0, cursor + 19, width=96)
            arrow_x = x0 + 96 + 20
            if self._arrow_item is not None:
                self.canvas.coords(self._arrow_item, arrow_x, cursor + 19)
            self._place_widget("target_end", arrow_x + 26, cursor + 19, width=96)
            cursor += 38 + 22
            cursor += place_label(self._hint_item)
            cursor += block_gap
        else:
            cursor += place_label(self._hint_item)
            cursor += block_gap

        # 计时前备注
        cursor += place_label(self._label_note)
        self._place_widget("note_before", x0, cursor + 15, width=inner_width)

        if self._start_button:
            self._start_button.set_pos(card_left + card_width / 2, oy + 0.885 * height)

        # 右侧预览时钟
        cx = ox + 0.734 * width
        cy = oy + 0.49 * height
        if self._analog is not None:
            radius = max(56, min(width * 0.105, height * 0.19))
            self._analog.build(cx, cy, radius)
            self._refresh_preview()
        if self._clock_item is not None:
            size = int(max(26, min(46, width * 0.042)))
            self.canvas.itemconfigure(self._clock_item, font=("Consolas", size, "bold"))
            self.canvas.coords(self._clock_item, cx, cy)

    def _place_widget(self, key: str, x: float, y: float, width: int | None = None) -> None:
        entry = self._pixel_widgets.get(key)
        if not entry:
            return
        _widget, item = entry
        self.canvas.coords(item, x, y)
        if width:
            self.canvas.itemconfigure(item, width=int(width))

    # ------------------------------------------------------------ 运行中布局
    def _layout_running(self, width: int, height: int, ox: int, oy: int) -> None:
        cx = ox + 0.5 * width
        cy = oy + 0.45 * height
        clock_bottom = cy

        if self._analog is not None:
            radius = max(66, min(width * 0.12, height * 0.185))
            self._analog.build(cx, cy, radius)
            clock_bottom = cy + radius + 20
        if self._clock_item is not None:
            size = int(max(40, min(88, width * 0.068)))
            self.canvas.itemconfigure(self._clock_item, font=("Consolas", size, "bold"))
            self.canvas.coords(self._clock_item, cx, cy)
            clock_bottom = cy + size * 0.62
        if self._sub_item is not None:
            self.canvas.coords(self._sub_item, cx, clock_bottom + 20)

        bar_width = min(620, width * 0.56)
        bar_x = cx - bar_width / 2
        bar_y = oy + 0.765 * height
        bar_h = 10
        self._prog_geom = (bar_x, bar_y, bar_width, bar_h)
        if self._prog_track is not None:
            redraw_round_rect(self.canvas, self._prog_track, bar_x, bar_y,
                              bar_x + bar_width, bar_y + bar_h, bar_h / 2)
        self._update_progress(self.app.engine.progress)

        # 两个操作按钮以中线对称摆放，避免窄窗口下相互重叠
        gap = 20
        button_y = oy + 0.905 * height
        if self._pause_button is not None:
            offset = (self._pause_button.w + gap) / 2
            self._pause_button.set_pos(cx - offset, button_y)
        if self._stop_button is not None:
            offset = (self._stop_button.w + gap) / 2
            self._stop_button.set_pos(cx + offset, button_y)

    def _update_progress(self, progress: float) -> None:
        if self._prog_fill is None:
            return
        x, y, w, h = self._prog_geom
        progress = max(0.0, min(1.0, progress))
        if progress <= 0.002:
            self.canvas.itemconfigure(self._prog_fill, state="hidden")
            return
        self.canvas.itemconfigure(self._prog_fill, state="normal")
        redraw_round_rect(self.canvas, self._prog_fill, x, y, x + max(6, w * progress), y + h, h / 2)

    # ================================================================= 交互
    def _set_mode(self, mode: str) -> None:
        if self.cfg["mode"] == mode:
            return
        self.cfg["mode"] = mode
        self.app.refresh_view()

    def _set_clock(self, clock: str) -> None:
        if self.cfg["clock_type"] == clock:
            return
        self.cfg["clock_type"] = clock
        self.app.refresh_view()

    def _set_preset(self, minutes: int) -> None:
        self.cfg["preset_minutes"] = minutes
        self.cfg["use_custom"] = False
        self.app.refresh_view()

    def _set_custom(self) -> None:
        if self.cfg["use_custom"]:
            return
        self.cfg["use_custom"] = True
        self.app.refresh_view()

    def _on_custom_change(self) -> None:
        var = self._vars.get("custom_minutes")
        if var:
            self.cfg["custom_minutes"] = var.get()
        self._refresh_preview()

    def _sync_note(self) -> None:
        var = self._vars.get("note_before")
        if var:
            self.cfg["note_before"] = var.get()

    # ------------------------------------------------------------ 预览与开始
    def _planned_seconds(self) -> int:
        cfg = self.cfg
        if cfg["mode"] == "countup":
            return 0
        if cfg["mode"] == "target":
            start = parse_hm(self._var_text("target_start", cfg["target_start"]))
            end = parse_hm(self._var_text("target_end", cfg["target_end"]))
            if not start or not end:
                return 0
            return span_minutes(f"{start[0]:02d}:{start[1]:02d}", f"{end[0]:02d}:{end[1]:02d}") * 60
        if cfg["use_custom"]:
            try:
                minutes = int(str(self._var_text("custom_minutes", cfg["custom_minutes"])).strip())
            except ValueError:
                return 0
            if minutes < config.MIN_MINUTES or minutes > config.MAX_MINUTES:
                return 0
            return minutes * 60
        return int(cfg["preset_minutes"]) * 60

    def _var_text(self, key: str, fallback: str = "") -> str:
        var = self._vars.get(key)
        return var.get() if var else fallback

    def _refresh_preview(self) -> None:
        theme = self.theme
        if self.app.session is not None:
            return
        cfg = self.cfg

        if cfg["mode"] == "countup":
            if self._clock_item is not None:
                self.canvas.itemconfigure(self._clock_item, text="00:00:00")
            if self._analog is not None:
                self._analog.update(0, 0, 0, 0.0, sub_text="00:00:00", running=False)
            if self._preview_item is not None:
                self.canvas.itemconfigure(self._preview_item, text="正向计时 · 从 0 开始累加",
                                          fill=theme["text_muted"])
            return

        seconds = self._planned_seconds()
        text = format_hms(seconds) if seconds > 0 else "--:--:--"

        if self._clock_item is not None:
            self.canvas.itemconfigure(self._clock_item, text=text)
        if self._analog is not None:
            total = max(1, seconds)
            hours, rem = divmod(int(total), 3600)
            minutes, secs = divmod(rem, 60)
            self._analog.update(hours, minutes, secs, 0.0,
                                sub_text=text if seconds > 0 else "", running=False)

        if self._preview_item is not None:
            if cfg["mode"] == "target":
                start = parse_hm(self._var_text("target_start", cfg["target_start"]))
                end = parse_hm(self._var_text("target_end", cfg["target_end"]))
                if start and end and seconds > 0:
                    label = (f"{start[0]:02d}:{start[1]:02d} → {end[0]:02d}:{end[1]:02d}"
                             f"（共 {format_duration(seconds)}）")
                else:
                    label = "请输入正确的时间，例如 09:00"
                    self.canvas.itemconfigure(self._preview_item, fill=theme["danger"])
                    self.canvas.itemconfigure(self._preview_item, text=label)
                    return
            else:
                label = f"倒计时 · {format_duration(seconds)}" if seconds > 0 else "请输入 1 - 1440 分钟"
            color = theme["text_muted"] if seconds > 0 else theme["danger"]
            self.canvas.itemconfigure(self._preview_item, text=label, fill=color)

    def _start(self) -> None:
        cfg = self.cfg
        self._sync_note()
        note = cfg.get("note_before", "").strip()
        if cfg["mode"] == "countup":
            self.app.start_session("countup", cfg["clock_type"], 0, "", "", note)
        elif cfg["mode"] == "target":
            start = parse_hm(self._var_text("target_start"))
            end = parse_hm(self._var_text("target_end"))
            if not start or not end:
                show_message(self.app.root, self.theme, "时间格式不正确",
                             "请输入 24 小时制时间，例如 09:00 或 21:30。")
                return
            cfg["target_start"] = f"{start[0]:02d}:{start[1]:02d}"
            cfg["target_end"] = f"{end[0]:02d}:{end[1]:02d}"
            self.app.start_session("target", cfg["clock_type"], 0,
                                   cfg["target_start"], cfg["target_end"], note)
        else:
            seconds = self._planned_seconds()
            if seconds <= 0:
                show_message(self.app.root, self.theme, "时长不正确",
                             f"请输入 {config.MIN_MINUTES} - {config.MAX_MINUTES} 之间的分钟数。")
                return
            self.app.start_session("countdown", cfg["clock_type"], seconds, "", "", note)

    def _confirm_stop(self) -> None:
        from tkinter import messagebox

        if self.app.engine.mode == "countup":
            question = "确定结束本次正向计时吗？\n结束后会记录本次已计时的时长。"
        else:
            question = "确定要提前结束本次计时吗？\n结束后将记为「已中断」并保存到历史记录。"
        if messagebox.askyesno("结束计时", question):
            self.app.request_stop()

    # ================================================================= 刷新
    def tick(self) -> None:
        if self.app.session is None:
            return
        engine = self.app.engine
        theme = self.theme

        if self._clock_item is not None:
            self.canvas.itemconfigure(self._clock_item,
                                      text=format_hms(engine.display_seconds))

        sub = ""
        if engine.mode == "target":
            sim = engine.simulated_datetime
            sub = f"模拟当前 {sim.hour:02d}:{sim.minute:02d} · 目标 {engine.target_end} 结束"
        elif engine.mode == "countup":
            sub = "秒表计时中，随时可结束并保存本次时长"
        if self._sub_item is not None:
            self.canvas.itemconfigure(self._sub_item, text=sub)

        if self._analog is not None:
            hour, minute, second = engine.clock_parts()
            self._analog.update(hour, minute, second, engine.progress,
                                sub_text=format_hms(engine.display_seconds),
                                running=engine.is_running)

        self._update_progress(engine.progress)

        if self._status_item is not None:
            if engine.is_paused:
                self.canvas.itemconfigure(self._status_item, text="已暂停", fill=theme["warning"])
            else:
                self.canvas.itemconfigure(self._status_item, text="专注中", fill=theme["accent"])
        if self._pause_button is not None:
            self._pause_button.set_text(self._pause_label())
        if self._info_item is not None:
            self.canvas.itemconfigure(self._info_item, text=self._running_info_text())

    def on_hide(self) -> None:
        if self._analog is not None:
            self._analog.destroy()
            self._analog = None

    @staticmethod
    def _preset_label(minutes: int) -> str:
        if minutes % 60 == 0:
            return f"{minutes // 60} 小时"
        return f"{minutes} 分钟"
