#!/bin/bash
# ============================================================
# 聚合天气后端服务 - 启动脚本
# ============================================================
# 使用方式:
#   bash start.sh
#
# 访问地址:
#   前端页面:  http://localhost:8000
#   API 文档:  http://localhost:8000/docs
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_VENV="C:/Users/pro 14/.workbuddy/binaries/python/envs/default/Scripts/python.exe"

if [ -f "$PYTHON_VENV" ]; then
    "$PYTHON_VENV" "$SCRIPT_DIR/app.py"
else
    echo "Python venv 未找到，请先运行:"
    echo "  pip install fastapi uvicorn"
    python "$SCRIPT_DIR/app.py"
fi
