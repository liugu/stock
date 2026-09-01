@echo off
REM 启动DOGE网格守护进程（开机自启用）
REM 防止重复启动：先杀掉已有的grid_daemon
wmic process where "commandline like '%%grid_daemon.py%%'" call terminate >nul 2>&1
REM 启动守护进程（后台方式，隐藏窗口）
start "" /min "E:\量化研究\workspace\stock\venv\Scripts\pythonw.exe" "E:\量化研究\workspace\stock\backtest\doge_grid\grid_daemon.py"