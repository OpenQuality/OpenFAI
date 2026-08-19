#!/bin/bash
# FAI系统启动脚本

echo "=================================="
echo "FAI质量评审系统启动脚本"
echo "=================================="

# 切换到项目目录
cd /workspace/projects

# 安装依赖
echo "[1/5] 安装Python依赖..."
pip3 install -r requirements.txt -q

# 清理paddleocr自动拉入的冲突opencv包
# paddleocr声明依赖opencv-python和opencv-contrib-python，
# 但这些包在无头服务器上因缺少libGL导致import cv2失败。
# 使用opencv-python-headless替代（功能相同但无GUI依赖）。
pip3 uninstall -y opencv-python opencv-contrib-python 2>/dev/null || true
pip3 install --force-reinstall --no-deps opencv-python-headless 2>/dev/null || true

# 运行数据库迁移
echo "[2/5] 运行数据库迁移..."
python3 manage.py makemigrations --noinput
python3 manage.py migrate --noinput

# 收集静态文件
echo "[3/5] 收集静态文件..."
python3 manage.py collectstatic --noinput

# 创建演示数据
echo "[4/5] 创建演示数据..."
python3 manage.py shell < init_data.py

# 启动服务
echo "[5/5] 启动开发服务器..."
echo ""
echo "=================================="
echo "系统启动成功!"
echo "访问地址: http://0.0.0.0:5000"
echo "登录账号: admin / admin123"
echo "=================================="
echo ""

python3 manage.py runserver 0.0.0.0:5000
