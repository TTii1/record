#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
按住右 Ctrl 说话，松开后自动转写并粘贴到当前输入框。

依赖安装（公司内网 pip 镜像）：
    pip install -r requirements.txt

运行：
    python push_to_talk.py

提示：
    - 按住右 Ctrl 开始录音
    - 松开右 Ctrl 自动识别并粘贴
    - 如果按住右 Ctrl 后又按了其他字母/数字键，会当作普通 Ctrl 快捷键并取消本次录音
    - 按 Ctrl+C 退出
"""
import collections
import os
import subprocess
import sys
import threading
import time

import numpy as np
import pyperclip
import sounddevice as sd
from pynput import keyboard
from faster_whisper import WhisperModel

from config import (
    BEAM_SIZE,
    COMPUTE_TYPE,
    DEVICE,
    INITIAL_PROMPT,
    LANGUAGE,
    MAX_AUDIO_SECONDS,
    MIN_AUDIO_SECONDS,
    MODEL_DIR,
    PREROLL_SECONDS,
    RECORDING_DIR,
    SAMPLE_RATE,
    VAD_FILTER,
)

# 自动选择设备
def _resolve_device():
    if DEVICE == "auto":
        try:
            import ctranslate2

            if ctranslate2.get_cuda_device_count() > 0:
                print("检测到 NVIDIA GPU，使用 GPU 加速。", flush=True)
                return "cuda"
        except Exception:
            pass
        print("未检测到可用 GPU，使用 CPU。", flush=True)
        return "cpu"
    return DEVICE


def _resolve_compute_type(device):
    if COMPUTE_TYPE != "auto":
        return COMPUTE_TYPE
    return "float16" if device == "cuda" else "int8"

# 修饰键：按住右 Ctrl 时如果按下这些键不取消录音
_MODIFIER_KEYS = {
    keyboard.Key.ctrl_r,
    keyboard.Key.ctrl_l,
    keyboard.Key.ctrl,
    keyboard.Key.shift,
    keyboard.Key.shift_l,
    keyboard.Key.shift_r,
    keyboard.Key.alt,
    keyboard.Key.alt_l,
    keyboard.Key.alt_r,
    keyboard.Key.alt_gr,
    keyboard.Key.cmd,
    keyboard.Key.cmd_l,
    keyboard.Key.cmd_r,
}


class PushToTalkApp:
    def __init__(self):
        if not os.path.isdir(MODEL_DIR):
            print(f"错误：找不到模型目录：{MODEL_DIR}")
            print("请先运行：python download_model.py --model small")
            sys.exit(1)

        print("正在加载模型，请稍候...")
        self.device = _resolve_device()
        self.compute_type = _resolve_compute_type(self.device)
        try:
            model_kwargs = {"device": self.device, "compute_type": self.compute_type}
            if self.device == "cpu":
                model_kwargs["cpu_threads"] = 0  # 0 = 自动使用所有 CPU 线程
            self.model = WhisperModel(MODEL_DIR, **model_kwargs)
        except Exception as exc:
            if self.device == "cuda":
                print(f"GPU 加载失败（{exc}），自动回退到 CPU int8。", file=sys.stderr)
                self.device = "cpu"
                self.compute_type = "int8"
                self.model = WhisperModel(
                    MODEL_DIR,
                    device="cpu",
                    compute_type="int8",
                    cpu_threads=0,
                )
            else:
                raise
        print(f"模型加载完成。设备: {self.device}, 精度: {self.compute_type}")

        self.keyboard_controller = keyboard.Controller()
        self.lock = threading.Lock()

        self.recording = False
        self.busy = False
        self.cancelled = False
        self.frames = []
        self.stream = None
        self.record_started_at = 0.0
        # 始终保留最近一小段音频，按下按键时把这段补到录音开头
        self.audio_buffer = collections.deque(maxlen=int(SAMPLE_RATE * PREROLL_SECONDS))

        os.makedirs(RECORDING_DIR, exist_ok=True)

        # 启动后常驻录音流，用于预录音，避免按下按键后设备启动延迟导致开头被吞
        try:
            self.stream = sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="float32",
                callback=self._audio_callback,
            )
            self.stream.start()
            print(f"麦克风已就绪，预录音 {PREROLL_SECONDS:.1f}s", flush=True)
        except Exception as exc:
            print(f"启动麦克风失败：{exc}", file=sys.stderr)
            print("请检查麦克风是否可用，或安装系统依赖：sudo apt install libportaudio2", file=sys.stderr)
            sys.exit(1)

    # ---------- 录音 ----------

    def _audio_callback(self, indata, frames, time_info, status):
        if status:
            print(f"录音状态: {status}", file=sys.stderr)
        # 始终保留最近一小段音频
        self.audio_buffer.extend(indata[:, 0])
        if self.recording:
            self.frames.append(indata.copy())

    def start_recording(self):
        with self.lock:
            if self.recording or self.busy:
                return False

            # 把按下按键前 PREROLL_SECONDS 的音频补到开头
            preroll = np.array(self.audio_buffer, dtype=np.float32).reshape(-1, 1) if self.audio_buffer else np.empty((0, 1), dtype=np.float32)
            self.frames = [preroll] if len(preroll) else []
            self.cancelled = False
            self.recording = True
            self.record_started_at = time.time()
            print("\n[录音中] 松开右 Ctrl 结束", flush=True)
            self._notify("录音中", "松开右 Ctrl 结束")
            return True

    def stop_recording(self):
        with self.lock:
            if not self.recording:
                return None

            self.recording = False
            # 常驻录音流不关闭，方便下一次快速开始

            if self.cancelled:
                self.frames = []
                return None

            if not self.frames:
                return None

            audio = np.concatenate(self.frames, axis=0).flatten().astype(np.float32)
            self.frames = []
            # 在同一个锁内标记 busy，避免刚松开又被立刻触发新的录音
            self.busy = True
            return audio

    def cancel_recording(self):
        with self.lock:
            if not self.recording:
                return
            self.recording = False
            self.cancelled = True
            self.frames = []

    # ---------- 键盘事件 ----------

    def on_press(self, key):
        try:
            if key == keyboard.Key.ctrl_r:
                self.start_recording()
            elif self.recording and not self._is_modifier(key):
                # 按住 Ctrl 时如果按了其他非修饰键，说明可能是普通 Ctrl 快捷键
                # 取消本次录音，避免把 Ctrl+C / Ctrl+V 误当成语音输入
                self.cancel_recording()
                print("[已取消] 检测到 Ctrl 组合键，不转写", flush=True)
        except Exception as exc:
            print(f"按键处理异常：{exc}", file=sys.stderr)

    def on_release(self, key):
        try:
            if key == keyboard.Key.ctrl_r:
                audio = self.stop_recording()
                if audio is None:
                    return
                # 在后台线程识别，避免阻塞键盘监听
                threading.Thread(target=self._finish_and_paste, args=(audio,), daemon=True).start()
        except Exception as exc:
            print(f"释放按键处理异常：{exc}", file=sys.stderr)

    @staticmethod
    def _is_modifier(key):
        return key in _MODIFIER_KEYS

    # ---------- 识别和粘贴 ----------

    def _finish_and_paste(self, audio):
        try:
            duration = len(audio) / SAMPLE_RATE
            if duration < MIN_AUDIO_SECONDS:
                print("[太短，已忽略]", flush=True)
                return
            if duration > MAX_AUDIO_SECONDS:
                print(f"[超过最长录音 {MAX_AUDIO_SECONDS}s，本次不识别]", flush=True)
                return

            # 可选：保存录音用于调试
            self._save_debug_audio(audio)

            print(f"[识别中] 音频 {duration:.1f}s ...", flush=True)
            segments, info = self.model.transcribe(
                audio,
                language=LANGUAGE,
                beam_size=BEAM_SIZE,
                vad_filter=VAD_FILTER,
                initial_prompt=INITIAL_PROMPT,
            )
            text = "".join(segment.text.strip() for segment in segments).strip()
            if not text:
                print("[未识别到文字]", flush=True)
                return

            pyperclip.copy(text)
            time.sleep(0.05)  # 等待剪贴板就绪
            self._paste()
            print(f"[已输入] {text}", flush=True)
            self._notify("识别完成", text)
        except Exception as exc:
            print(f"识别失败：{exc}", file=sys.stderr)
        finally:
            self.busy = False

    def _paste(self):
        """模拟 Ctrl+V 粘贴到当前焦点输入框。"""
        try:
            with self.keyboard_controller.pressed(keyboard.Key.ctrl):
                self.keyboard_controller.press("v")
                self.keyboard_controller.release("v")
        except Exception as exc:
            print(f"自动粘贴失败，请手动 Ctrl+V。错误：{exc}", file=sys.stderr)

    def _save_debug_audio(self, audio):
        try:
            import wave

            path = os.path.join(RECORDING_DIR, time.strftime("%Y%m%d-%H%M%S.wav"))
            with wave.open(path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes((audio * 32767).astype(np.int16).tobytes())
        except Exception:
            pass

    @staticmethod
    def _notify(title, message):
        try:
            subprocess.Popen(
                ["notify-send", title, message],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


def main():
    if not os.path.isdir(MODEL_DIR):
        print(f"错误：找不到模型目录：{MODEL_DIR}")
        print("请先运行：python download_model.py --model small")
        return 1

    app = PushToTalkApp()

    print("\n使用方法：")
    print("  按住 右Ctrl 开始说话，松开后自动转写并粘贴到当前输入框")
    print("  按 Ctrl+C 退出")
    print("=" * 60, flush=True)

    with keyboard.Listener(
        on_press=app.on_press,
        on_release=app.on_release,
    ) as listener:
        listener.join()

    return 0


if __name__ == "__main__":
    sys.exit(main())
