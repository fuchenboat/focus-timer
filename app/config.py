"""全局配置：应用信息、路径、默认设置与常量。"""
from __future__ import annotations

import os
import sys

APP_NAME = "时间专注助手"
APP_ID = "TimeFocusAssistant"
APP_VERSION = "1.0.0"

# 快捷时长预设（分钟）
DEFAULT_PRESETS = [30, 60, 120]
# 快捷时长可选池（供设置页勾选）
PRESET_POOL = [5, 10, 15, 20, 25, 30, 45, 60, 90, 120, 150, 180]

# 主题显示名
THEME_LABELS = {"dark": "黑色", "light": "白色", "eye": "护眼"}

MIN_MINUTES = 1
MAX_MINUTES = 24 * 60

# 界面尺寸
HEADER_HEIGHT = 66
DEFAULT_WINDOW_SIZE = (1100, 760)
MIN_WINDOW_SIZE = (960, 700)


def _project_root() -> str:
    """项目根目录（app 包的上一级）。"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_resource_dir() -> str:
    """资源目录：打包后为临时解压目录，开发时为项目根目录。"""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return _project_root()


def get_base_dir() -> str:
    """程序所在目录：打包后为 exe 所在目录，开发时为项目根目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return _project_root()


def _is_writable(path: str) -> bool:
    try:
        os.makedirs(path, exist_ok=True)
        probe = os.path.join(path, ".__wtest__")
        with open(probe, "w", encoding="utf-8") as fh:
            fh.write("ok")
        os.remove(probe)
        return True
    except Exception:
        return False


def get_data_dir() -> str:
    """数据目录：优先使用程序同级 data 目录，不可写则回退到用户目录。"""
    preferred = os.path.join(get_base_dir(), "data")
    if _is_writable(preferred):
        return preferred
    fallback = os.path.join(os.path.expanduser("~"), "." + APP_ID)
    os.makedirs(fallback, exist_ok=True)
    return fallback


DATA_DIR = get_data_dir()
RECORDS_FILE = os.path.join(DATA_DIR, "records.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")
BACKGROUND_DIR = os.path.join(DATA_DIR, "backgrounds")

DEFAULT_SETTINGS = {
    "theme": "dark",
    "background_image": "",
    "background_overlay": 0.55,
    "sound_enabled": True,
    "presets": DEFAULT_PRESETS,
    "last_mode": "countdown",
    "last_clock": "digital",
    "window_size": list(DEFAULT_WINDOW_SIZE),
}
