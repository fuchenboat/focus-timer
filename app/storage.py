"""数据存储：records.json 与 settings.json 的读写，背景图片的保存。"""
from __future__ import annotations

import json
import os
import shutil
import time

from . import config
from .models import STATUS_RUNNING, Record


class Storage:
    """负责所有持久化数据，JSON 格式。"""

    def __init__(self) -> None:
        self.records: list[Record] = []
        self.settings: dict = dict(config.DEFAULT_SETTINGS)
        self.load()

    # ------------------------------------------------------------------ 读写
    def load(self) -> None:
        self.settings = dict(config.DEFAULT_SETTINGS)
        self.records = []

        if os.path.exists(config.SETTINGS_FILE):
            try:
                with open(config.SETTINGS_FILE, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, dict):
                    self.settings.update(data)
            except Exception:
                pass

        if os.path.exists(config.RECORDS_FILE):
            try:
                with open(config.RECORDS_FILE, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if isinstance(data, list):
                    self.records = [Record.from_dict(item) for item in data if isinstance(item, dict)]
            except Exception:
                self.records = []

    @staticmethod
    def _atomic_write(path: str, payload) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
        for _ in range(5):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                time.sleep(0.05)
        shutil.move(tmp, path)

    def save_records(self) -> None:
        self._atomic_write(config.RECORDS_FILE, [r.to_dict() for r in self.records])

    def save_settings(self) -> None:
        self._atomic_write(config.SETTINGS_FILE, self.settings)

    # ------------------------------------------------------------------ 记录
    def add_record(self, record: Record) -> None:
        self.records.append(record)
        self.save_records()

    def update_record(self, record: Record) -> None:
        for idx, item in enumerate(self.records):
            if item.id == record.id:
                self.records[idx] = record
                break
        self.save_records()

    def delete_record(self, record_id: str) -> None:
        self.records = [r for r in self.records if r.id != record_id]
        self.save_records()

    def get_record(self, record_id: str):
        for item in self.records:
            if item.id == record_id:
                return item
        return None

    def sorted_records(self) -> list[Record]:
        """按开始时间倒序。"""
        return sorted(self.records, key=lambda r: r.start_time or r.created_at, reverse=True)

    def running_records(self) -> list[Record]:
        return [r for r in self.records if r.status == STATUS_RUNNING]

    def total_focus_seconds(self) -> int:
        return sum(int(r.actual_seconds or 0) for r in self.records)

    def completed_count(self) -> int:
        from .models import STATUS_COMPLETED

        return sum(1 for r in self.records if r.status == STATUS_COMPLETED)

    # ------------------------------------------------------------------ 背景图
    def save_background(self, source_path: str) -> str:
        """把用户选择的图片复制到数据目录，返回相对文件名。"""
        os.makedirs(config.BACKGROUND_DIR, exist_ok=True)
        ext = os.path.splitext(source_path)[1].lower() or ".png"
        filename = f"background_{int(time.time())}{ext}"
        target = os.path.join(config.BACKGROUND_DIR, filename)
        shutil.copyfile(source_path, target)
        # 清理旧图片
        for name in os.listdir(config.BACKGROUND_DIR):
            full = os.path.join(config.BACKGROUND_DIR, name)
            if os.path.isfile(full) and full != target:
                try:
                    os.remove(full)
                except OSError:
                    pass
        return filename

    def background_abspath(self) -> str:
        name = self.settings.get("background_image") or ""
        if not name:
            return ""
        path = os.path.join(config.BACKGROUND_DIR, name)
        return path if os.path.exists(path) else ""

    def clear_background(self) -> None:
        self.settings["background_image"] = ""
        try:
            if os.path.isdir(config.BACKGROUND_DIR):
                for name in os.listdir(config.BACKGROUND_DIR):
                    full = os.path.join(config.BACKGROUND_DIR, name)
                    if os.path.isfile(full):
                        os.remove(full)
        except OSError:
            pass
        self.save_settings()
