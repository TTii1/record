#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 ModelScope 下载 faster-whisper 模型到 models/ 目录。

适用场景：国内网络无法访问 HuggingFace，但可以访问 ModelScope。

用法：
    python download_model.py --model small
    python download_model.py --model medium
    python download_model.py --model large-v3
"""
import argparse
import os
import sys

try:
    from modelscope.hub.api import HubApi
except ImportError:
    print("缺少 modelscope，请先执行：pip install -r requirements-download.txt")
    sys.exit(1)

# ModelScope 上的 faster-whisper CTranslate2 格式模型
MODEL_REPOS = {
    "tiny": "pengzhendong/faster-whisper-tiny",
    "base": "pengzhendong/faster-whisper-base",
    "small": "pengzhendong/faster-whisper-small",
    "medium": "pengzhendong/faster-whisper-medium",
    "large-v2": "pengzhendong/faster-whisper-large-v2",
    "large-v3": "pengzhendong/faster-whisper-large-v3",
}


def main():
    parser = argparse.ArgumentParser(description="下载 faster-whisper 模型")
    parser.add_argument(
        "--model",
        default="small",
        choices=list(MODEL_REPOS.keys()),
        help="要下载的模型，默认 small",
    )
    args = parser.parse_args()

    repo_id = MODEL_REPOS[args.model]
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models", f"faster-whisper-{args.model}")
    os.makedirs(output_dir, exist_ok=True)

    print(f"开始从 ModelScope 下载: {repo_id}")
    print(f"保存到: {output_dir}")
    api = HubApi()
    api.download_model(model_id=repo_id, local_dir=output_dir)
    print("模型下载完成。")

    # 如果下载的是 small/medium/large，提醒修改 config.py 中的 MODEL_DIR
    print("如果更换了模型，请修改 config.py 里的 MODEL_DIR 指向新模型目录。")


if __name__ == "__main__":
    sys.exit(main())
