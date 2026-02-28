@echo off
chcp 65001 >nul
title 红灯笼智能助理
cd /d "%~dp0"

echo ==========================================
echo      红灯笼智能助理启动器
echo ==========================================
echo.

:: 检查虚拟环境是否存在
if not exist "venv\Scripts\python.exe" (
    echo [错误] 虚拟环境不存在！
    echo 请先创建虚拟环境并安装依赖。
    pause
    exit /b 1
)

echo [1/3] 正在激活虚拟环境...
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [错误] 激活虚拟环境失败！
    pause
    exit /b 1
)

echo [2/3] 虚拟环境已激活
echo [3/3] 正在启动红灯笼智能助理...
echo.
echo ==========================================
echo.

:: 启动主程序
python main.py

:: 程序退出后的处理
echo.
echo ==========================================
echo 红灯笼智能助理已退出
echo ==========================================
pause
