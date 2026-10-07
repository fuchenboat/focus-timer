"""背景壁纸管理：把用户上传的图片铺满窗口，并按主题做半透明覆盖以保证可读性。"""
from __future__ import annotations

import os
import tkinter as tk

from PIL import Image, ImageTk


def cover_resize(image: Image.Image, width: int, height: int) -> Image.Image:
    """等比缩放并居中裁剪，使图片刚好铺满目标尺寸。"""
    width = max(1, int(width))
    height = max(1, int(height))
    src_w, src_h = image.size
    if src_w <= 0 or src_h <= 0:
        return image.resize((width, height))
    scale = max(width / src_w, height / src_h)
    new_size = (max(1, int(src_w * scale + 0.5)), max(1, int(src_h * scale + 0.5)))
    resized = image.resize(new_size, Image.LANCZOS)
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


class Wallpaper:
    """负责绘制窗口背景（图片或纯色）。"""

    def __init__(self, canvas: tk.Canvas) -> None:
        self.canvas = canvas
        self._photo = None
        self._cache_key = None
        self._cache_image = None

    def draw(self, width: int, height: int, path: str, overlay_alpha: float, bg_color: str) -> None:
        self.canvas.delete("wallpaper")
        if width <= 1 or height <= 1:
            return

        drawn = False
        if path and os.path.exists(path):
            key = (path, width, height, round(float(overlay_alpha), 3), bg_color)
            if key != self._cache_key:
                try:
                    self._cache_image = self._render(path, width, height, overlay_alpha, bg_color)
                    self._cache_key = key
                except Exception:
                    self._cache_image = None
                    self._cache_key = None
            if self._cache_image is not None:
                self._photo = self._cache_image
                self.canvas.create_image(0, 0, anchor="nw", image=self._photo, tags=("wallpaper",))
                drawn = True

        if not drawn:
            self.canvas.create_rectangle(0, 0, width, height, fill=bg_color, outline="", tags=("wallpaper",))

        self.canvas.tag_lower("wallpaper")

    def _render(self, path: str, width: int, height: int, alpha: float, bg_color: str):
        image = Image.open(path).convert("RGB")
        image = cover_resize(image, width, height)
        alpha = max(0.0, min(0.95, float(alpha)))
        overlay = Image.new("RGB", image.size, bg_color)
        return ImageTk.PhotoImage(Image.blend(image, overlay, alpha))
