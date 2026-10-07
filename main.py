"""时间专注助手 —— 程序入口。

开发环境运行： python main.py
打包 exe：     双击 build.bat
"""
from __future__ import annotations

import os
import traceback


def _log_fatal(detail: str) -> None:
    try:
        from app import config

        with open(os.path.join(config.DATA_DIR, "error.log"), "a", encoding="utf-8") as fh:
            fh.write(detail + "\n")
    except Exception:
        pass


def main() -> None:
    try:
        from app.ui.app import TimeFocusApp

        TimeFocusApp().run()
    except Exception:
        detail = traceback.format_exc()
        _log_fatal(detail)
        try:
            import tkinter as tk
            from tkinter import messagebox

            root = tk.Tk()
            root.withdraw()
            messagebox.showerror("时间专注助手 启动失败", detail[-1500:])
            root.destroy()
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
