# 时间专注助手

一个 Windows 桌面端的时间专注 / 计时记录小工具。双击 exe 即可运行，数据以 JSON 格式保存在本地，不联网、不上传。

**直接使用**：下载仓库根目录的 `时间专注助手.exe`，双击即可运行，无需安装 Python。首次运行会在 exe 同级目录生成 `data` 文件夹存放记录。

## 功能

**三种计时模式**

| 模式 | 说明 |
| --- | --- |
| 倒计时 | 30 分钟 / 1 小时 / 2 小时等快捷时长，也可自定义 1–1440 分钟 |
| 目标时刻 | 设定「09:00 → 11:00」这样的区间做模拟计时，倒数到结束时刻 |
| 正向计时 | 从 0 开始累加，点「结束计时」或直接关闭软件，都会记录本次时长 |

**其他**

- 电子时钟 / 传统时钟两种表盘，开始时选择；传统时钟指针始终顺时针走动
- 暂停 / 继续 / 结束计时；计时前、计时后都可以写备注
- 计时结束提醒：播放提示音 + 窗口置顶闪烁 + 弹出窗口补充结束备注
- 历史记录：查看每次计时的详情、修改备注、删除记录，并统计累计专注时长
- 主题配色：黑色 / 白色 / 护眼三套，点击即时切换
- 自定义背景：可上传自己的图片，带遮罩强度调节保证文字清晰
- 数据落盘：计时一开始就写入 JSON，中途关软件也不会丢记录

## 运行与打包

环境要求：Windows + Python 3.10 以上

直接运行源码：

```bash
python main.py
```

打包成单文件 exe：

```bash
双击 build.bat
```

首次运行会自动创建 `.venv` 并安装依赖，打包产物 `时间专注助手.exe` 直接输出到项目根目录，双击即可运行。

## 数据文件

首次运行后会在程序同级目录生成 `data` 文件夹：

```
data/
├── records.json      每次计时的记录
├── settings.json     主题、背景、快捷时长等设置
└── backgrounds/      上传的背景图片
```

`records.json` 中单条记录示例：

```json
{
  "id": "8f3c1a2b7d90",
  "mode": "countdown",
  "clock_type": "analog",
  "planned_seconds": 1800,
  "actual_seconds": 1800,
  "start_time": "2026-10-07 09:00:00",
  "end_time": "2026-10-07 09:30:00",
  "status": "completed",
  "note_before": "整理周报",
  "note_after": "顺利写完",
  "paused_count": 0,
  "paused_seconds": 0
}
```

`status` 取值：`completed`（正常完成）/ `interrupted`（提前中断）/ `running`（进行中，异常退出后下次启动会自动标记为中断）。

## 目录结构

```
时间专注助手/
├── 时间专注助手.exe         打包好的程序，双击即可运行
├── main.py                  程序入口
├── build.bat                一键打包脚本（产物输出到根目录）
├── requirements.txt
├── assets/icon.ico          应用图标
├── app/                     ——— 业务代码 ———
│   ├── config.py            路径、默认配置、常量
│   ├── theme.py             黑 / 白 / 护眼三套配色
│   ├── models.py            计时记录数据模型
│   ├── storage.py           records.json / settings.json 读写
│   ├── timer_engine.py      计时内核（倒计时 / 目标时刻 / 正向计时 / 暂停）
│   ├── sound.py             结束提醒音
│   ├── utils.py             时间格式化与解析
│   └── ui/
│       ├── app.py           主窗口、导航、计时会话管理
│       ├── canvas_kit.py    圆角按钮、面板、ttk 样式
│       ├── analog_clock.py  传统时钟表盘绘制
│       ├── wallpaper.py     背景壁纸处理
│       ├── dialogs.py       结束备注弹窗
│       └── views/           计时 / 历史 / 设置三个页面
└── build/                   打包中间产物（不纳入版本控制）
```

## 技术说明

界面使用 Python 标准库自带的 Tkinter，并用 Canvas 手绘圆角按钮、面板和时钟表盘；背景图片用 Pillow 等比铺满并按主题色叠加遮罩。整个程序只依赖 Pillow（运行时）和 PyInstaller（打包时），打包后为单个 exe，无需安装 Python。
