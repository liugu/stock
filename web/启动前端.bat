@echo off
chcp 65001 >nul
echo ========================================
echo 智能选股系统 - 前端服务
echo ========================================
echo.
echo 访问地址: http://localhost:5173
echo.
echo ========================================
cd /d %~dp0
npm run dev
pause
