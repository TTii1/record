# 离线语音转文字（按住右 Ctrl 说话）

面向中文日常办公场景的本地语音输入工具：

- 按住 **右 Ctrl** 开始录音
- 松开 **右 Ctrl** 自动识别
- 识别结果自动复制并粘贴到当前输入框
- 纯 CPU 运行，默认使用 faster-whisper-medium + int8
- 模型已放在 `models/faster-whisper-small` 和 `models/faster-whisper-medium`，不需要再联网下载

---

## 一、目录说明

```text
.
├── models/
│   ├── faster-whisper-small/     # 快速模式（约 460MB）
│   └── faster-whisper-medium/    # 高准确模式（约 1.5GB）
├── push_to_talk.py               # 主程序
├── config.py                     # 配置：模型路径、语言、识别参数
├── download_model.py             # 从 ModelScope 下载模型（国内可访问）
├── requirements.txt              # Python 依赖（公司内网 pip 镜像安装）
├── install.sh                    # 公司电脑安装脚本
├── start.sh                      # 启动脚本
└── package.sh                    # 打包脚本
```

## 二、当前电脑准备（已完成）

1. 已从 ModelScope 下载 `faster-whisper-small` 和 `faster-whisper-medium`
2. 默认使用 `faster-whisper-medium`，可以在 `config.py` 中切回 `small`
3. 已写好转写/粘贴脚本
3. 打包使用：

```bash
./package.sh
```

会生成 `stt-offline.tar.gz`。

## 三、公司电脑安装

把 `stt-offline.tar.gz` 拷贝到公司电脑后解压：

```bash
tar -xzf stt-offline.tar.gz
cd stt-offline
```

### 1. 安装 Python 依赖

公司有内网 pip 镜像，直接执行：

```bash
./install.sh
```

如果你的内网 pip 镜像地址需要手动指定：

```bash
PIP_INDEX_URL=http://你的内网pip镜像/simple ./install.sh
```

### 2. 启动

```bash
./start.sh
```

看到 `按住 右Ctrl 开始说话` 后，把光标放到任意输入框，按住右 Ctrl 说话，松开后文字会自动进去。

---

## 四、使用说明

- **开始**：按住右 Ctrl
- **结束**：松开右 Ctrl，自动识别并粘贴
- **取消**：按住右 Ctrl 后如果按了其他字母/数字键，会当作普通 Ctrl 快捷键并取消本次录音
- **退出**：在终端按 Ctrl+C

> 注意：这个设计会让右 Ctrl 优先作为“按住说话”的开关。如果你经常需要使用 Ctrl+C / Ctrl+V 等组合键，程序会尽量识别为普通快捷键并取消录音，但如果你在按住右 Ctrl 的同时说话，不会触发其他按键，所以正常说话不受影响。

## 五、GPU 加速（可选）

`config.py` 里默认是自动检测：

```python
DEVICE = "auto"
COMPUTE_TYPE = "auto"
```

意思是：

- 有 NVIDIA GPU：自动使用 GPU + float16
- 没有 NVIDIA GPU（包括 AMD 显卡/核显、Intel 核显）：自动使用 CPU + int8
- 如果 GPU 加载失败：自动回退到 CPU，不会直接崩溃

注意：当前 faster-whisper 方案的 GPU 加速只支持 **NVIDIA CUDA**，不支持 AMD 显卡或 AMD 核显。

如果你的电脑有 NVIDIA 独立显卡，并且 `faster-whisper` 依赖的 `ctranslate2` 带 CUDA 支持，就会自动启用 GPU。

如果想强制使用 CPU：

```python
DEVICE = "cpu"
```

如果想强制使用 GPU：

```python
DEVICE = "cuda"
```

---

## 六、切换模型

当前默认使用 `medium`，中文准确率更高，CPU 上会稍慢一点。

如果觉得慢，可以切回 `small`，修改 `config.py`：

```python
MODEL_DIR = os.path.join(BASE_DIR, "models", "faster-whisper-small")
```

如果需要重新下载模型，在能访问 ModelScope 的电脑上执行：

```bash
python download_model.py --model small
python download_model.py --model medium
```

## 七、常见问题

### 1. 没有声音 / 录音失败

检查麦克风权限和系统录音设备：

```bash
arecord -l
```

并确认系统已安装：

```bash
sudo apt install libportaudio2
```

### 2. 不能自动粘贴

自动粘贴依赖 X11 下的剪贴板工具。先安装：

```bash
sudo apt install xclip
```

如果是 Wayland 桌面，`pynput` 的全局按键监听可能受限，建议使用 X11/Xorg 会话，或者安装 `wl-clipboard` 并自行调整粘贴方式。

### 3. 公司电脑不能访问 HuggingFace

本项目模型来自 ModelScope，国内可以访问。

如果模型文件丢失，可以重新下载：

```bash
pip install -r requirements-download.txt
python download_model.py --model medium
# 如果也想保留 small 快速模型：
python download_model.py --model small
```

### 4. CPU 速度

默认 `medium + int8`，日常短句通常松开后 1~4 秒内出字。如果觉得慢，可以把 `config.py` 中的 `BEAM_SIZE` 改成 `1`，或者把模型切回 `small`。

### 5. 开头吞字/录不上开头

程序默认会保留按下按键前 0.3 秒的麦克风音频，作为“预录音”补到开头，避免说话太快导致第一个字没录进去。

如果还是觉得开头被吞，可以把 `config.py` 中的 `PREROLL_SECONDS` 调大，例如改成 `0.5`。

### 6. 准确率偏低

当前默认使用 `medium`，中文准确率明显比 `small` 好。如果你更看重速度，可以切回 `small`：

```python
MODEL_DIR = os.path.join(BASE_DIR, "models", "faster-whisper-small")
```
