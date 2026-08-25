#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x "stt-venv/bin/python" ]; then
    echo "还没有安装依赖，请先运行：./install.sh"
    exit 1
fi

exec ./stt-venv/bin/python push_to_talk.py "$@"
