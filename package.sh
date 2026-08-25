#!/usr/bin/env bash
# 在有网/当前电脑上打包，生成 stt-offline.tar.gz
# 打包内容包括：代码 + 模型 + 说明文件（不包含 Python 依赖，因为公司有 pip 镜像）
set -euo pipefail
cd "$(dirname "$0")"

rm -f stt-offline.tar.gz

tmp_archive="$(mktemp /tmp/stt-offline.XXXXXX.tar.gz)"
trap 'rm -f "$tmp_archive"' EXIT

echo "打包中..."
tar \
    --exclude='./stt-venv' \
    --exclude='./build-venv' \
    --exclude='./.git' \
    --exclude='./__pycache__' \
    --exclude='./recordings' \
    --exclude='./*.tar.gz' \
    -czf "$tmp_archive" .

mv "$tmp_archive" stt-offline.tar.gz
trap - EXIT

echo "完成：$(pwd)/stt-offline.tar.gz"
ls -lh stt-offline.tar.gz
