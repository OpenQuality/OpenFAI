#!/bin/bash
# OpenFAI 演示数据一键生成脚本
# 用法: bash init_demo.sh
# 幂等：重复执行不会产生重复数据

set -e

cd "$(dirname "$0")"

echo "=================================================="
echo "  OpenFAI 演示数据初始化"
echo "=================================================="
echo ""

# ── 检测 Python 可执行路径 ──────────────────────────
if [ -f "venv/bin/python" ]; then
    PYTHON="venv/bin/python"
elif [ -f "venv/bin/python3" ]; then
    PYTHON="venv/bin/python3"
elif [ -f "venv/Scripts/python.exe" ]; then
    PYTHON="venv/Scripts/python.exe"
else
    PYTHON=$(command -v python3 || command -v python)
fi

echo "Python: $PYTHON"
echo "路径:   $(pwd)"
echo ""

# ── 检查依赖 ────────────────────────────────────────
if ! "$PYTHON" -c "import django" 2>/dev/null; then
    echo "[错误] Django 未安装，请先执行: pip install -r requirements.txt"
    exit 1
fi

# ── 检查数据库迁移 ───────────────────────────────────
echo "[1/2] 检查数据库迁移..."
"$PYTHON" manage.py migrate --noinput
echo ""

# ── 生成演示数据 ─────────────────────────────────────
echo "[2/2] 生成演示数据..."
echo ""
"$PYTHON" manage.py shell -c "exec(open('demo_data.py', encoding='utf-8').read())"

echo ""
echo "=================================================="
echo "  完成！请访问系统查看演示数据"
echo "=================================================="
