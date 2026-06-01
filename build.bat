@echo off
echo ========================================
echo PID上位机 - 打包脚本
echo ========================================
echo.

echo [1/4] 检查Python环境...
python --version
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python
    pause
    exit /b 1
)

echo.
echo [2/4] 安装依赖包...
pip install -r requirements.txt
if errorlevel 1 (
    echo 错误: 依赖包安装失败
    pause
    exit /b 1
)

echo.
echo [3/4] 打包exe文件...
pyinstaller --onefile --windowed --name "PID上位机" main.py
if errorlevel 1 (
    echo 错误: 打包失败
    pause
    exit /b 1
)

echo.
echo [4/4] 打包完成！
echo exe文件位置: dist\PID上位机.exe
echo.

pause
