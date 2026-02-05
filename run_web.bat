@echo off
chcp 65001 >nul
echo ================================================
echo   技术参数提取与比对平台 - 启动中...
echo ================================================
echo.

:: 检查 streamlit 是否安装
python -c "import streamlit" 2>nul
if errorlevel 1 (
    echo [提示] 正在安装必要依赖...
    pip install streamlit openpyxl -q
    echo.
)

:: 启动 Web 应用
echo [启动] 正在打开浏览器...
echo [地址] http://localhost:8501
echo.
echo 按 Ctrl+C 可停止服务
echo ================================================
streamlit run web_app.py --server.port 8501

pause
