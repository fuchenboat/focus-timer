@echo off
chcp 65001 >nul
setlocal
cd /d %~dp0

set PY=.venv\Scripts\python.exe

if not exist "%PY%" (
    echo [1/3] 正在创建虚拟环境 .venv ...
    python -m venv --system-site-packages .venv
    if errorlevel 1 goto :error
    "%PY%" -m pip install --upgrade pip
)

echo [2/3] 正在安装依赖 ...
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo [3/3] 正在打包，请稍候 ...
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed ^
    --name "focus-timer" ^
    --distpath "." ^
    --workpath "build" ^
    --specpath "build" ^
    --icon "assets\icon.ico" ^
    --add-data "assets;assets" ^
    main.py
if errorlevel 1 goto :error

echo.
echo ============================================
echo  打包完成：focus-timer.exe（项目根目录）
echo  双击该 exe 即可运行，数据保存在同目录 data 文件夹
echo ============================================
pause
exit /b 0

:error
echo.
echo 构建失败，请查看上方错误信息。
pause
exit /b 1
