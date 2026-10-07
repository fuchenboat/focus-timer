"""弹窗：结束备注输入框与通用提示框。"""
from __future__ import annotations

import tkinter as tk

from .canvas_kit import UI_FONT, UI_FONT_BOLD, UI_FONT_SMALL, themed_text


class _BaseDialog(tk.Toplevel):
    def __init__(self, parent, theme, title, width, height):
        super().__init__(parent)
        self.theme = theme
        self.result = None
        self.configure(bg=theme["surface"])
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        parent.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        py = parent.winfo_rooty() + (parent.winfo_height() - height) // 3
        self.geometry(f"{width}x{height}+{max(0, px)}+{max(0, py)}")

    def _on_close(self):
        self.result = None
        self.destroy()

    def _finish(self, modal=True):
        self.destroy()
        return self.result


class NoteDialog(_BaseDialog):
    """计时结束 / 中断时填写结束备注。"""

    def __init__(self, parent, theme, title, message, initial="", ok_text="保存备注", skip_text="跳过"):
        super().__init__(parent, theme, title, 540, 320)

        tk.Label(self, text=title, font=UI_FONT_BOLD, bg=theme["surface"], fg=theme["text"]).pack(
            anchor="w", padx=24, pady=(20, 6))
        tk.Label(self, text=message, font=UI_FONT, bg=theme["surface"], fg=theme["text_muted"],
                 justify="left", wraplength=480).pack(anchor="w", padx=24)

        self.text = themed_text(self, theme, height=5, width=44)
        self.text.pack(fill="both", expand=True, padx=24, pady=14)
        if initial:
            self.text.insert("1.0", initial)

        bar = tk.Frame(self, bg=theme["surface"])
        bar.pack(fill="x", padx=24, pady=(0, 18))
        self._flat_button(bar, skip_text, theme["surface2"], theme["text"], self._on_skip).pack(side="right", padx=(10, 0))
        self._flat_button(bar, ok_text, theme["accent"], theme["accent_text"], self._on_ok).pack(side="right")

        self.bind("<Escape>", lambda _e: self._on_skip())
        self.text.focus_set()

    def _flat_button(self, parent, text, bg, fg, command):
        return tk.Button(parent, text=text, command=command, bg=bg, fg=fg, font=UI_FONT,
                         relief="flat", bd=0, padx=18, pady=7, activebackground=bg,
                         activeforeground=fg, cursor="hand2", highlightthickness=0)

    def _on_ok(self):
        self.result = self.text.get("1.0", "end").strip()
        self.destroy()

    def _on_skip(self):
        self.result = None
        self.destroy()


class MessageDialog(_BaseDialog):
    """通用提示框。"""

    def __init__(self, parent, theme, title, message, ok_text="好的"):
        super().__init__(parent, theme, title, 440, 210)
        tk.Label(self, text=title, font=UI_FONT_BOLD, bg=theme["surface"], fg=theme["text"]).pack(
            anchor="w", padx=24, pady=(22, 8))
        tk.Label(self, text=message, font=UI_FONT, bg=theme["surface"], fg=theme["text_muted"],
                 justify="left", wraplength=390).pack(anchor="w", padx=24)
        bar = tk.Frame(self, bg=theme["surface"])
        bar.pack(fill="x", padx=24, pady=18, side="bottom")
        tk.Button(bar, text=ok_text, command=self.destroy, bg=theme["accent"], fg=theme["accent_text"],
                  font=UI_FONT, relief="flat", bd=0, padx=20, pady=7, activebackground=theme["accent_hover"],
                  activeforeground=theme["accent_text"], cursor="hand2", highlightthickness=0).pack(side="right")
        self.bind("<Return>", lambda _e: self.destroy())
        self.focus_set()


def ask_note(parent, theme, title, message, initial="", ok_text="保存备注", skip_text="跳过"):
    dialog = NoteDialog(parent, theme, title, message, initial, ok_text, skip_text)
    dialog.grab_set()
    parent.wait_window(dialog)
    return dialog.result


def show_message(parent, theme, title, message, ok_text="好的"):
    dialog = MessageDialog(parent, theme, title, message, ok_text)
    dialog.grab_set()
    parent.wait_window(dialog)
    return dialog.result
