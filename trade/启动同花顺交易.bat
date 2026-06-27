@echo off
chcp 65001 >nul
title 同花顺快速交易助手

echo ====================================================================
echo 同花顺快速交易助手
echo ====================================================================
echo.
echo 使用前请确保:
echo 1. 同花顺软件已启动并登录
echo 2. 已安装 Python 和 pyautogui
echo.
echo 按任意键启动...
pause >nul

cd /d E:\量化研究\workspace\stock
call .venv\Scripts\activate
python quick_ths.py

pause
