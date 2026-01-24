# Qwen Voice Easy Clone

使用阿里云 Qwen TTS API 轻松复刻你的声音，让 AI 用你的声音说话。

## 功能特点

- 🎙️ **声音复刻** - 上传 10-20 秒录音，创建专属音色
- 💾 **音色管理** - 保存、复用、删除已创建的音色
- 📝 **多行输入** - 支持多行文本输入，连续 3 次回车开始合成
- 🎵 **WAV 输出** - 合成的音频保存为 WAV 文件

## 快速开始

### 1. 安装

```bash
git clone https://github.com/paxaq/qwen-voice-easy-clone.git
cd qwen-voice-easy-clone
./setup.sh
```

### 2. 配置 API Key

获取 API Key: https://help.aliyun.com/zh/model-studio/get-api-key

```bash
cp .env.example .env
nano .env  # 填入 DASHSCOPE_API_KEY
```

### 3. 准备声音样本

准备一段你的声音录音：
- 时长：10-20 秒
- 格式：MP3、WAV、M4A、FLAC、OGG
- 要求：清晰人声，背景安静

### 4. 运行

```bash
source venv/bin/activate
./voice_clone.py
```

## 使用流程

```
╔══════════════════════════════════════════════════════════════╗
║           🎙️  Qwen 声音复刻工具  🎙️                          ║
╚══════════════════════════════════════════════════════════════╝

✅ API Key 已配置

────────────────────────────────────────────────────────────

📚 已保存的音色:
   [1] 我的声音 (来源: voice.mp3, 创建: 2026-01-24)
   [n] 创建新音色
   [d] 删除音色

🎵 请选择 (输入序号/n/d，q 退出): 1

✅ 已选择音色: 我的声音

────────────────────────────────────────────────────────────

🎤 进入语音合成模式
   支持多行输入，连续按3次回车开始合成
   合成的音频保存到 output/ 目录
   输入 q 退出

────────────────────────────────────────────────────────────

💬 请输入要合成的文字 (连续3个空行结束，输入 q 退出):
你好，这是一段测试文本。
今天天气真不错！


🔗 连接已建立
🎬 会话已创建
📥 正在接收音频... 完成

💾 音频已保存: output/tts_20260124_120530.wav
   文件大小: 156.2 KB
```

## 文件结构

```
qwen-voice-easy-clone/
├── voice_clone.py     # 主程序
├── setup.sh           # 安装脚本
├── .env.example       # 配置示例
├── .env               # 配置文件（需创建）
├── voices.json        # 已保存的音色（自动生成）
└── output/            # 合成的音频文件
    └── tts_*.wav
```

## 环境要求

- Python 3.10+
- Linux / macOS / Windows

## 依赖

- `dashscope` >= 1.23.9
- `python-dotenv`
- `requests`

## API 参考

本项目使用阿里云 DashScope API：

| 功能 | 模型 |
|------|------|
| 声音复刻 | qwen-voice-enrollment |
| 语音合成 | qwen3-tts-vc-realtime-2026-01-15 |

详细文档：https://help.aliyun.com/zh/model-studio/qwen-tts

## License

MIT
