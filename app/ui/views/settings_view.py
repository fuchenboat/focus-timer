"""设置视图：主题配色、自定义背景、提醒声音、快捷时长与数据目录。"""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk

from ... import config, sound
from ...config import APP_NAME, APP_VERSION, PRESET_POOL, THEME_LABELS
from ..canvas_kit import UI_FONT, UI_FONT_SMALL
from .base import BaseView

MAX_PRESETS = 4


class SettingsView(BaseView):
    name = "settings"

    def __init__(self, app, canvas):
        self._theme_buttons: dict[str, object] = {}
        self._preset_buttons: list[tuple[int, object]] = []
        self._sound_button = None
        self._bg_name_item = None
        self._overlay_label = None
        self._overlay_hint_item = None
        self._overlay_var = None
        self._scale_widget = None
        self._scale_item = None
        self._labels: dict[str, int] = {}
        super().__init__(app, canvas)

    # ================================================================= 构建
    def build(self) -> None:
        theme = self.theme
        settings = self.app.settings
        labels = self._labels

        self.text(0.03, 0.06, "设置", anchor="w", size=16, weight="bold")

        # ---------------- 主题配色 ----------------
        self.panel(0.03, 0.09, 0.45, 0.33, radius=16)
        labels["theme_title"] = self.text(0.055, 0.13, "主题色彩", anchor="w", size=12, weight="bold")
        self._theme_buttons = {}
        for key, label in THEME_LABELS.items():
            button = self.button(0.5, 0.5, label, lambda k=key: self.app.apply_theme(k),
                                 width=104, height=40, radius=12, kind="chip", font=UI_FONT)
            button.set_selected(settings.get("theme") == key)
            self._theme_buttons[key] = button
        labels["theme_hint"] = self.text(0.055, 0.32, "黑色 / 白色 / 护眼三套配色，点击立即生效",
                                         anchor="w", size=9, fill=theme["text_faint"])

        # ---------------- 背景图片 ----------------
        self.panel(0.51, 0.09, 0.46, 0.33, radius=16)
        labels["bg_title"] = self.text(0.535, 0.13, "自定义背景", anchor="w", size=12, weight="bold")
        name = settings.get("background_image") or "未设置（使用纯色背景）"
        self._bg_name_item = self.text(
            0.535, 0.18, name, anchor="w", size=10,
            fill=theme["text_muted"] if settings.get("background_image") else theme["text_faint"])
        self._pick_button = self.button(0.5, 0.5, "选择图片", self._pick_background,
                                        width=110, height=38, radius=11, kind="secondary", font=UI_FONT)
        self._clear_button = self.button(0.5, 0.5, "清除背景", self._clear_background,
                                         width=110, height=38, radius=11, kind="secondary", font=UI_FONT)
        self._overlay_hint_item = self.text(0.535, 0.27, "背景遮罩（数值越大文字越清晰）",
                                            anchor="w", size=9, fill=theme["text_faint"])
        self._overlay_label = self.text(0.945, 0.27, "", anchor="e", size=9, fill=theme["text_muted"])

        self._overlay_var = tk.DoubleVar(value=float(settings.get("background_overlay", 0.55)))
        self._scale_widget = ttk.Scale(self.canvas, from_=0.0, to=0.9, orient="horizontal",
                                       variable=self._overlay_var, style="App.Horizontal.TScale",
                                       command=self._on_scale_move)
        self._scale_widget.bind("<ButtonRelease-1>", self._on_scale_apply)
        self._scale_item = self.widget(self._scale_widget, 0.535, 0.35, anchor="w")
        self._update_overlay_label()

        # ---------------- 提醒 ----------------
        self.panel(0.03, 0.45, 0.45, 0.19, radius=16)
        labels["sound_title"] = self.text(0.055, 0.49, "计时结束提醒", anchor="w", size=12, weight="bold")
        self._sound_button = self.button(0.5, 0.5, self._sound_label(), self._toggle_sound,
                                         width=132, height=38, radius=11, kind="secondary", font=UI_FONT)
        self._test_button = self.button(0.5, 0.5, "试听", self._test_sound,
                                        width=84, height=38, radius=11, kind="ghost", font=UI_FONT)
        labels["sound_hint"] = self.text(0.055, 0.60, "计时结束/中断时播放提示音并弹出备注窗口",
                                         anchor="w", size=9, fill=theme["text_faint"])

        # ---------------- 数据 ----------------
        self.panel(0.51, 0.45, 0.46, 0.19, radius=16)
        labels["data_title"] = self.text(0.535, 0.49, "数据文件", anchor="w", size=12, weight="bold")
        self._data_path_item = self.text(0.535, 0.535, config.DATA_DIR, anchor="w", size=9,
                                         fill=theme["text_faint"])
        self._open_dir_button = self.button(0.5, 0.5, "打开数据目录", self._open_data_dir,
                                            width=132, height=38, radius=11, kind="secondary",
                                            font=UI_FONT)

        # ---------------- 快捷时长 ----------------
        self.panel(0.03, 0.66, 0.94, 0.30, radius=16)
        labels["preset_title"] = self.text(0.055, 0.70, "快捷时长按钮", anchor="w", size=12, weight="bold")
        labels["preset_hint"] = self.text(0.30, 0.705, f"选中后会出现在计时页（最多 {MAX_PRESETS} 个）",
                                          anchor="w", size=9, fill=theme["text_faint"])
        selected = set(settings.get("presets") or config.DEFAULT_PRESETS)
        self._preset_buttons = []
        for minutes in PRESET_POOL:
            label = f"{minutes // 60} 小时" if minutes % 60 == 0 else f"{minutes} 分"
            button = self.button(0.5, 0.5, label, lambda m=minutes: self._toggle_preset(m),
                                 width=74, height=36, radius=11, kind="chip", font=UI_FONT_SMALL)
            button.set_selected(minutes in selected)
            self._preset_buttons.append((minutes, button))

        self.text(0.5, 0.985, f"{APP_NAME} v{APP_VERSION}", anchor="center", size=9,
                  fill=theme["text_faint"])

    # ================================================================= 布局
    def on_layout(self, width: int, height: int, ox: int, oy: int) -> None:
        def title(item_key, x_rel, top):
            item = self._labels.get(item_key)
            if item is not None:
                self.canvas.coords(item, ox + x_rel * width, top + 8)

        def hint(item_key, x_rel, top):
            item = self._labels.get(item_key)
            if item is not None:
                self.canvas.coords(item, ox + x_rel * width, top + 7)

        # ---- 主题配色 ----
        c = oy + 0.09 * height + 20
        title("theme_title", 0.055, c)
        c += 16 + 14
        self.place_row(list(self._theme_buttons.values()), ox + 0.055 * width, c + 20, gap=10)
        c += 40 + 18
        hint("theme_hint", 0.055, c)

        # ---- 自定义背景 ----
        c = oy + 0.09 * height + 20
        title("bg_title", 0.535, c)
        c += 16 + 10
        if self._bg_name_item is not None:
            self.canvas.coords(self._bg_name_item, ox + 0.535 * width, c + 7)
        c += 14 + 12
        self.place_row([self._pick_button, self._clear_button], ox + 0.535 * width, c + 19, gap=10)
        c += 38 + 18
        if self._overlay_hint_item is not None:
            self.canvas.coords(self._overlay_hint_item, ox + 0.535 * width, c + 7)
        if self._overlay_label is not None:
            self.canvas.coords(self._overlay_label, ox + 0.945 * width, c + 7)
        c += 14 + 8
        if self._scale_item is not None:
            self.canvas.coords(self._scale_item, ox + 0.535 * width, c + 10)
            self.canvas.itemconfigure(self._scale_item, width=int(min(0.35 * width, 250)))

        # ---- 提醒 ----
        c = oy + 0.45 * height + 20
        title("sound_title", 0.055, c)
        c += 16 + 14
        self.place_row([self._sound_button, self._test_button], ox + 0.055 * width, c + 19, gap=10)
        c += 38 + 16
        hint("sound_hint", 0.055, c)

        # ---- 数据 ----
        c = oy + 0.45 * height + 20
        title("data_title", 0.535, c)
        c += 16 + 8
        if self._data_path_item is not None:
            self.canvas.coords(self._data_path_item, ox + 0.535 * width, c + 7)
        c += 14 + 14
        if self._open_dir_button is not None:
            self._open_dir_button.set_pos(ox + 0.535 * width + 66, c + 19)

        # ---- 快捷时长（自动换行） ----
        c = oy + 0.66 * height + 20
        title("preset_title", 0.055, c)
        hint("preset_hint", 0.30, c + 1)
        c += 16 + 18
        start_x = ox + 0.055 * width
        limit_x = ox + 0.955 * width
        x = start_x
        for _minutes, button in self._preset_buttons:
            if x + button.w > limit_x:
                x = start_x
                c += 42
            button.set_pos(x + button.w / 2, c + 18)
            x += button.w + 8

    # ================================================================= 交互
    def _sound_label(self) -> str:
        return f"提醒声音：{'开启' if self.app.settings.get('sound_enabled', True) else '关闭'}"

    def _toggle_sound(self) -> None:
        settings = self.app.settings
        settings["sound_enabled"] = not settings.get("sound_enabled", True)
        self.app.storage.save_settings()
        if self._sound_button:
            self._sound_button.set_text(self._sound_label())

    def _test_sound(self) -> None:
        sound.play_test(enabled=bool(self.app.settings.get("sound_enabled", True)))

    def _pick_background(self) -> None:
        path = filedialog.askopenfilename(
            title="选择背景图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif *.webp"), ("所有文件", "*.*")],
        )
        if not path:
            return
        try:
            self.app.set_background(path)
        except Exception as exc:  # 图片损坏 / 无权限
            from ..dialogs import show_message

            show_message(self.app.root, self.theme, "设置失败", f"无法使用该图片：{exc}")

    def _clear_background(self) -> None:
        self.app.clear_background()

    def _update_overlay_label(self) -> None:
        if self._overlay_label is not None and self._overlay_var is not None:
            percent = int(round(self._overlay_var.get() * 100))
            self.canvas.itemconfigure(self._overlay_label, text=f"{percent}%")

    def _on_scale_move(self, _value=None) -> None:
        self._update_overlay_label()

    def _on_scale_apply(self, _event=None) -> None:
        self.app.update_overlay(self._overlay_var.get())

    def _toggle_preset(self, minutes: int) -> None:
        settings = self.app.settings
        presets = list(settings.get("presets") or config.DEFAULT_PRESETS)
        if minutes in presets:
            if len(presets) <= 1:
                return
            presets.remove(minutes)
        else:
            if len(presets) >= MAX_PRESETS:
                from ..dialogs import show_message

                show_message(self.app.root, self.theme, "数量已达上限",
                             f"快捷时长最多选择 {MAX_PRESETS} 个，请先取消其他选项。")
                return
            presets.append(minutes)
        presets.sort(key=lambda m: PRESET_POOL.index(m) if m in PRESET_POOL else 999)
        settings["presets"] = presets
        self.app.storage.save_settings()
        self.app.refresh_view()

    def _open_data_dir(self) -> None:
        try:
            os.startfile(config.DATA_DIR)  # noqa: S606 - Windows 打开资源管理器
        except Exception:
            pass
