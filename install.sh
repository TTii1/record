#!/usr/bin/env bash
# 公司电脑离线/内网安装脚本
# 前提：公司有 pip 镜像，Python 3.8+ 已安装，并且本目录包含 models/ 模型文件
set -euo pipefail
cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "错误：找不到 python3，请先安装 Python 3.8+。"
    exit 1
fi

if [ ! -d "models/faster-whisper-medium" ] && [ ! -d "models/faster-whisper-small" ]; then
    echo "错误：当前目录没有找到模型目录（models/faster-whisper-medium 或 models/faster-whisper-small）。"
    echo "如果还没有模型，请在有网的电脑上运行：python download_model.py --model medium"
    exit 1
fi

echo "创建虚拟环境..."
if [ ! -d "stt-venv" ]; then
    "$PYTHON_BIN" -m venv stt-venv
fi

PIP="$(pwd)/stt-venv/bin/pip"
echo "使用 pip: $PIP"

# 如果设置了 PIP_INDEX_URL 环境变量，则使用内网镜像
# 例：PIP_INDEX_URL=http://mirror.internal/simple ./install.sh
if [ -n "${PIP_INDEX_URL:-}" ]; then
    "$PIP" install -i "$PIP_INDEX_URL" -r requirements.txt
else
    "$PIP" install -r requirements.txt
fi

echo
echo "检查系统依赖..."
missing=()
if ! ldconfig -p 2>/dev/null | grep -q libportaudio; then
    missing+=("libportaudio2")
fi
if ! command -v xclip >/dev/null 2>&1 && ! command -v xsel >/dev/null 2>&1; then
    missing+=("xclip 或 xsel")
fi
if [ "${#missing[@]}" -gt 0 ]; then
    echo "提示：可能缺少系统包：${missing[*]}"
    echo "如果粘贴或录音失败，请安装对应系统包（例如 sudo apt install libportaudio2 xclip）"
fi

echo
echo "安装完成。运行：./start.sh"
