"""主题配色管理：黑色 / 白色 / 护眼 三套配色。"""
from __future__ import annotations

THEMES = {
    "dark": {
        "bg": "#14161a",
        "surface": "#1e2128",
        "surface2": "#272b34",
        "surface3": "#333a47",
        "text": "#eceef1",
        "text_muted": "#9aa2ae",
        "text_faint": "#6d7480",
        "accent": "#4c8dff",
        "accent_hover": "#6ba1ff",
        "accent_text": "#ffffff",
        "success": "#2fae67",
        "success_hover": "#43c47b",
        "danger": "#d9534a",
        "danger_hover": "#e8685f",
        "warning": "#d9a13b",
        "border": "#333a46",
        "track": "#2c313c",
        "shadow": "#0c0e12",
    },
    "light": {
        "bg": "#f2f4f7",
        "surface": "#ffffff",
        "surface2": "#eef0f4",
        "surface3": "#e0e4ea",
        "text": "#1f2328",
        "text_muted": "#5f6672",
        "text_faint": "#9aa1ad",
        "accent": "#3b82f6",
        "accent_hover": "#2f74e6",
        "accent_text": "#ffffff",
        "success": "#22a05c",
        "success_hover": "#1f8f52",
        "danger": "#dc4b3f",
        "danger_hover": "#c93f34",
        "warning": "#d99a24",
        "border": "#dfe3e9",
        "track": "#e6e9ef",
        "shadow": "#c9ced7",
    },
    "eye": {
        "bg": "#c8e6c9",
        "surface": "#dcefdd",
        "surface2": "#cbe7cd",
        "surface3": "#b8ddbb",
        "text": "#1e3a26",
        "text_muted": "#456b4f",
        "text_faint": "#6f9379",
        "accent": "#2f9e5a",
        "accent_hover": "#37b167",
        "accent_text": "#ffffff",
        "success": "#2f9e5a",
        "success_hover": "#37b167",
        "danger": "#c25b4d",
        "danger_hover": "#d16a5c",
        "warning": "#c1912f",
        "border": "#aed5b3",
        "track": "#bfe0c3",
        "shadow": "#9dc5a3",
    },
}


class Theme:
    """主题对象，支持以 theme["accent"] 方式取值。"""

    def __init__(self, name: str = "dark"):
        self.name = "dark"
        self.colors: dict = THEMES["dark"]
        self.set(name)

    def set(self, name: str) -> None:
        if name not in THEMES:
            name = "dark"
        self.name = name
        self.colors = THEMES[name]

    def __getitem__(self, key: str) -> str:
        return self.colors[key]

    def get(self, key: str, default: str = "#000000") -> str:
        return self.colors.get(key, default)
