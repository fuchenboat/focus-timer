"""提醒声音：使用 Windows 内置 winsound 播放提示音，无需外部音频文件。"""
from __future__ import annotations

import threading

try:
    import winsound  # type: ignore
except Exception:  # pragma: no cover - 非 Windows 平台
    winsound = None

_FINISH_MELODY = [(784, 160), (988, 160), (1175, 160), (988, 120), (1175, 320)]
_TICK_MELODY = [(660, 90)]


def _play(melody) -> None:
    if winsound is None:
        return

    def run() -> None:
        try:
            for freq, duration in melody:
                winsound.Beep(freq, duration)
        except Exception:
            pass

    threading.Thread(target=run, daemon=True).start()


def play_finish(enabled: bool = True, repeat: int = 2) -> None:
    """计时结束提醒音。"""
    if not enabled or winsound is None:
        return

    def run() -> None:
        try:
            for _ in range(max(1, repeat)):
                for freq, duration in _FINISH_MELODY:
                    winsound.Beep(freq, duration)
        except Exception:
            pass

    threading.Thread(target=run, daemon=True).start()


def play_test(enabled: bool = True) -> None:
    """试听。"""
    if not enabled:
        return
    _play(_TICK_MELODY)
