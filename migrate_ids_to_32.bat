@echo off
chcp 65001 > nul
cd /d %~dp0
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
) else (
    echo [提示] 未找到 .venv，将使用当前 Python 环境。
)

python -m scripts.migrate_ids_to_32
pause
