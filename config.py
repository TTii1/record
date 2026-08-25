# -*- coding: utf-8 -*-
"""集中配置：修改这里可以切换模型、语言等。"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 模型目录：默认使用 faster-whisper-medium（更准，CPU 稍慢）
# 如果觉得慢，可以改回 faster-whisper-small
MODEL_DIR = os.path.join(BASE_DIR, "models", "faster-whisper-medium")

# 推理设备：
#   "auto" = 自动检测，有 NVIDIA GPU 就用 GPU，没有就用 CPU
#   "cpu"  = 强制 CPU
#   "cuda" = 强制 NVIDIA GPU
DEVICE = "auto"

# 量化/精度：
#   "auto"    = GPU 用 float16，CPU 用 int8
#   "int8"    = CPU 常用，速度快
#   "float16" = GPU 常用
#   "float32" = 最稳但慢
COMPUTE_TYPE = "auto"

# 录音采样率：faster-whisper 使用 16k 效果最好
SAMPLE_RATE = 16000

# 识别语言：zh = 中文（可识别少量英文）
LANGUAGE = "zh"

# 识别参数
BEAM_SIZE = 5
VAD_FILTER = True

# 中文场景提示词：帮助模型更偏向中文，同时保留英文单词/路径
INITIAL_PROMPT = "以下是简体中文日常办公语音，可能包含少量英文单词、文件路径、网址和技术名称。"

# 最短录音秒数，小于这个长度不识别
MIN_AUDIO_SECONDS = 0.2

# 预录音秒数：按下按键前保留最近这段音频，避免开头第一个字被吞掉
PREROLL_SECONDS = 0.3

# 最长录音秒数，防止一直按住导致异常
MAX_AUDIO_SECONDS = 60

# 录音缓存目录（用于调试，可留空则不保存）
RECORDING_DIR = os.path.join(BASE_DIR, "recordings")
