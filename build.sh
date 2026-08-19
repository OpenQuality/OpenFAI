#!/bin/bash
# FAI系统构建脚本
# 安装Python依赖并清理opencv包冲突
# paddleocr声明依赖opencv-python和opencv-contrib-python，
# 但这些包在无头服务器上因缺少libGL导致import cv2失败。
# 使用opencv-python-headless替代（功能相同但无GUI依赖）。

set -e

echo "[build] 安装Python依赖..."
pip3 install -r requirements.txt

echo "[build] 清理冲突的opencv包..."
pip3 uninstall -y opencv-python opencv-contrib-python 2>/dev/null || true

echo "[build] 确保opencv-python-headless正确安装..."
pip3 install --force-reinstall --no-deps opencv-python-headless 2>/dev/null || true

echo "[build] 构建完成"
