@echo off
chcp 65001 >nul
echo ========================================
echo        MRP 数据库备份
echo ========================================
echo.

if not exist "mes.db" (
    echo 错误：找不到数据库文件 mes.db
    echo 请确保在正确的目录下运行此脚本
    pause
    exit /b 1
)

set backup_name=mes_backup_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%.db
set backup_name=%backup_name: =0%

echo 正在备份数据库...
copy "mes.db" "backup\%backup_name%" >nul

if exist "backup\%backup_name%" (
    echo 备份成功：backup\%backup_name%
) else (
    echo 备份失败！
)

echo.
pause
