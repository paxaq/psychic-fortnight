#!/usr/bin/env python3
# coding=utf-8
"""
声音复刻工具 - 用户友好版本
使用阿里云 Qwen TTS 进行声音复刻和语音合成
"""

import os
import sys
import json
import requests
import base64
import pathlib
import threading
import time
import wave
import subprocess
import shutil
from datetime import datetime
import dashscope
from dotenv import load_dotenv
from dashscope.audio.qwen_tts_realtime import QwenTtsRealtime, QwenTtsRealtimeCallback, AudioFormat

# 加载 .env 文件
load_dotenv()

# ======= 配置 =======
TARGET_MODEL = "qwen3-tts-vc-realtime-2026-01-15"
ENROLLMENT_MODEL = "qwen-voice-enrollment"

# API 地址
# 声音复刻 API（创建自定义音色）
VOICE_ENROLLMENT_URL = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization"
# 实时语音合成 WebSocket
WS_URL = os.getenv("DASHSCOPE_WS_URL", "wss://dashscope.aliyuncs.com/api-ws/v1/realtime")

# 输出目录
OUTPUT_DIR = pathlib.Path("output")
# 音色存储文件
VOICES_FILE = pathlib.Path("voices.json")


def load_voices() -> dict:
    """加载已保存的音色"""
    if VOICES_FILE.exists():
        try:
            with open(VOICES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_voice(name: str, voice: str, source_file: str = None):
    """保存音色到文件"""
    voices = load_voices()
    voices[name] = {
        "voice": voice,
        "source_file": source_file,
        "created_at": datetime.now().isoformat(),
        "model": TARGET_MODEL
    }
    with open(VOICES_FILE, 'w', encoding='utf-8') as f:
        json.dump(voices, f, ensure_ascii=False, indent=2)


def delete_voice(name: str) -> bool:
    """删除已保存的音色"""
    voices = load_voices()
    if name in voices:
        del voices[name]
        with open(VOICES_FILE, 'w', encoding='utf-8') as f:
            json.dump(voices, f, ensure_ascii=False, indent=2)
        return True
    return False


def clear_screen():
    """清屏"""
    os.system('clear' if os.name != 'nt' else 'cls')


def print_banner():
    """打印欢迎横幅"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║           🎙️  Qwen 声音复刻工具  🎙️                          ║
║                                                              ║
║        复刻你的声音，让 AI 用你的声音说话！                  ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_divider():
    """打印分隔线"""
    print("\n" + "─" * 60 + "\n")


def check_api_key():
    """检查 API Key 是否已配置"""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("❌ 错误：未找到 DASHSCOPE_API_KEY")
        print("\n请在项目目录创建 .env 文件并添加：")
        print("  DASHSCOPE_API_KEY=你的API密钥")
        print("\n或设置环境变量：")
        print("  export DASHSCOPE_API_KEY=\"你的API密钥\"")
        print("\n获取 API Key：https://help.aliyun.com/zh/model-studio/get-api-key")
        return None
    return api_key


def get_audio_mime_type(file_path: str) -> str:
    """根据文件扩展名获取 MIME 类型"""
    ext = pathlib.Path(file_path).suffix.lower()
    mime_types = {
        '.mp3': 'audio/mpeg',
        '.wav': 'audio/wav',
        '.m4a': 'audio/mp4',
        '.flac': 'audio/flac',
        '.ogg': 'audio/ogg'
    }
    return mime_types.get(ext, 'audio/mpeg')


def validate_audio_file(file_path: str) -> tuple[bool, str]:
    """验证音频文件"""
    path = pathlib.Path(file_path)

    if not path.exists():
        return False, f"文件不存在: {file_path}"

    if not path.is_file():
        return False, f"路径不是文件: {file_path}"

    # 检查文件大小（最大 10MB）
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > 10:
        return False, f"文件过大: {size_mb:.1f}MB（最大 10MB）"

    # 检查扩展名
    valid_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg'}
    if path.suffix.lower() not in valid_extensions:
        return False, f"不支持的格式: {path.suffix}（支持: mp3, wav, m4a, flac, ogg）"

    return True, "文件验证通过"


def create_voice(file_path: str, api_key: str, voice_name: str = "my_voice") -> str:
    """创建复刻音色"""
    file_path_obj = pathlib.Path(file_path)
    mime_type = get_audio_mime_type(file_path)

    print(f"\n📤 正在上传音频文件...")
    print(f"   文件: {file_path_obj.name}")
    print(f"   大小: {file_path_obj.stat().st_size / 1024:.1f} KB")
    print(f"   格式: {mime_type}")

    base64_str = base64.b64encode(file_path_obj.read_bytes()).decode()
    data_uri = f"data:{mime_type};base64,{base64_str}"

    payload = {
        "model": ENROLLMENT_MODEL,
        "input": {
            "action": "create",
            "target_model": TARGET_MODEL,
            "preferred_name": voice_name,
            "audio": {"data": data_uri}
        }
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    print(f"\n🔄 正在创建音色，请稍候...")

    try:
        resp = requests.post(VOICE_ENROLLMENT_URL, json=payload, headers=headers, timeout=60)
    except requests.Timeout:
        raise RuntimeError("请求超时，请检查网络连接")
    except requests.RequestException as e:
        raise RuntimeError(f"网络请求失败: {e}")

    if resp.status_code != 200:
        error_msg = resp.json().get('message', resp.text) if resp.text else '未知错误'
        raise RuntimeError(f"创建音色失败 (HTTP {resp.status_code}): {error_msg}")

    try:
        voice = resp.json()["output"]["voice"]
        print(f"\n✅ 音色创建成功！")
        return voice
    except (KeyError, ValueError) as e:
        raise RuntimeError(f"解析响应失败: {e}")


def ensure_output_dir():
    """确保输出目录存在"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def has_ffmpeg() -> bool:
    """检查是否安装了 ffmpeg"""
    return shutil.which('ffmpeg') is not None


def convert_wav_to_mp3(wav_path: pathlib.Path, mp3_path: pathlib.Path, bitrate: str = "128k") -> bool:
    """将 WAV 文件转换为 MP3"""
    try:
        subprocess.run([
            'ffmpeg', '-y', '-i', str(wav_path),
            '-codec:a', 'libmp3lame', '-b:a', bitrate,
            str(mp3_path)
        ], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def save_pcm_to_wav(pcm_data: bytes, output_path: pathlib.Path, sample_rate: int = 24000, channels: int = 1, sample_width: int = 2):
    """将 PCM 数据保存为 WAV 文件"""
    # 确保目录存在
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output_path), 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data)


def generate_output_filename() -> pathlib.Path:
    """生成输出文件名"""
    ensure_output_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return OUTPUT_DIR / f"tts_{timestamp}.wav"


class TTSCallback(QwenTtsRealtimeCallback):
    """TTS 流式回调处理器 - 保存到文件"""

    def __init__(self, output_path: pathlib.Path, show_progress: bool = True):
        self.complete_event = threading.Event()
        self.error = None
        self.show_progress = show_progress
        self.audio_received = False
        self.output_path = output_path
        self.audio_chunks = []
        self.saved = False

    def on_open(self) -> None:
        if self.show_progress:
            print("🔗 连接已建立")

    def on_close(self, close_status_code, close_msg) -> None:
        if self.show_progress and close_status_code:
            print(f"🔌 连接关闭")

    def on_event(self, response: dict) -> None:
        try:
            event_type = response.get('type', '')

            if event_type == 'session.created':
                if self.show_progress:
                    print("🎬 会话已创建")

            elif event_type == 'response.audio.delta':
                if not self.audio_received:
                    if self.show_progress:
                        print("📥 正在接收音频...", end="", flush=True)
                    self.audio_received = True
                audio_data = base64.b64decode(response['delta'])
                self.audio_chunks.append(audio_data)

            elif event_type == 'response.done':
                if self.audio_received and self.show_progress:
                    print(" 完成")

            elif event_type == 'session.finished':
                # 在会话结束时保存文件
                self._save_audio()
                self.complete_event.set()

            elif event_type == 'error':
                self.error = response.get('error', {}).get('message', '未知错误')
                self.complete_event.set()

        except Exception as e:
            self.error = str(e)
            self.complete_event.set()

    def _save_audio(self):
        """保存音频文件"""
        if self.audio_chunks and not self.saved:
            pcm_data = b''.join(self.audio_chunks)
            save_pcm_to_wav(pcm_data, self.output_path)
            self.saved = True

    def wait_for_finished(self, timeout: float = 300) -> bool:
        """等待完成，返回是否成功"""
        return self.complete_event.wait(timeout=timeout)


def synthesize_speech(text: str, voice: str, api_key: str) -> pathlib.Path | None:
    """使用复刻音色合成语音，保存到文件"""
    dashscope.api_key = api_key

    output_path = generate_output_filename()
    callback = TTSCallback(output_path, show_progress=True)

    tts = QwenTtsRealtime(
        model=TARGET_MODEL,
        callback=callback,
        url=WS_URL
    )

    try:
        tts.connect()
        tts.update_session(
            voice=voice,
            response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
            mode='server_commit'
        )

        # 分段发送文本（每句之间稍作停顿）
        sentences = text.replace('。', '。|').replace('！', '！|').replace('？', '？|').replace('，', '，|').split('|')
        sentences = [s.strip() for s in sentences if s.strip()]

        for sentence in sentences:
            tts.append_text(sentence)
            time.sleep(0.05)

        tts.finish()
        callback.wait_for_finished()

        if callback.error:
            print(f"\n❌ 合成出错: {callback.error}")
            return None

        if callback.audio_chunks:
            # 转换为 MP3
            if has_ffmpeg():
                mp3_path = output_path.with_suffix('.mp3')
                print(f"\n🔄 正在转换为 MP3...", end="", flush=True)
                if convert_wav_to_mp3(output_path, mp3_path):
                    output_path.unlink()  # 删除 WAV 文件
                    file_size = mp3_path.stat().st_size / 1024
                    print(f" 完成")
                    print(f"\n💾 音频已保存: {mp3_path}")
                    print(f"   文件大小: {file_size:.1f} KB")
                    return mp3_path
                else:
                    print(f" 失败，保留 WAV 格式")
                    file_size = output_path.stat().st_size / 1024
                    print(f"\n💾 音频已保存: {output_path}")
                    print(f"   文件大小: {file_size:.1f} KB")
                    return output_path
            else:
                file_size = output_path.stat().st_size / 1024
                print(f"\n💾 音频已保存: {output_path}")
                print(f"   文件大小: {file_size:.1f} KB")
                print(f"   提示: 安装 ffmpeg 可自动转换为 MP3")
                return output_path
        else:
            print(f"\n❌ 未收到音频数据")
            return None

    except Exception as e:
        print(f"\n❌ 合成失败: {e}")
        return None


def select_voice_file() -> str:
    """让用户选择音频文件"""
    print("\n📁 请输入音频文件路径")
    print("   支持格式: MP3, WAV, M4A, FLAC, OGG")
    print("   建议时长: 10-20 秒清晰人声")
    print("   最大大小: 10 MB")
    print()

    # 列出当前目录下的音频文件
    audio_extensions = {'.mp3', '.wav', '.m4a', '.flac', '.ogg'}
    current_dir = pathlib.Path('.')
    audio_files = [f for f in current_dir.iterdir()
                   if f.is_file() and f.suffix.lower() in audio_extensions]

    if audio_files:
        print("   当前目录下的音频文件:")
        for i, f in enumerate(audio_files, 1):
            size_kb = f.stat().st_size / 1024
            print(f"   [{i}] {f.name} ({size_kb:.1f} KB)")
        print()

    while True:
        user_input = input("🎵 输入文件路径或序号 (输入 q 退出): ").strip()

        if user_input.lower() == 'q':
            return None

        # 检查是否输入了序号
        if user_input.isdigit() and audio_files:
            idx = int(user_input) - 1
            if 0 <= idx < len(audio_files):
                file_path = str(audio_files[idx])
            else:
                print("❌ 无效的序号，请重新输入")
                continue
        else:
            file_path = user_input

        # 验证文件
        valid, msg = validate_audio_file(file_path)
        if valid:
            return file_path
        else:
            print(f"❌ {msg}")


def read_multiline_input() -> str:
    """读取多行输入，连续三个空行结束"""
    print("\n💬 请输入要合成的文字 (连续3个空行结束，输入 q 退出):")
    lines = []
    empty_count = 0

    while True:
        try:
            line = input()
        except (EOFError, KeyboardInterrupt):
            return None

        # 单独一行 q 表示退出
        if line.strip().lower() in ('q', 'quit', 'exit', '退出') and not lines:
            return None

        # 统计连续空行
        if line == "":
            empty_count += 1
            if empty_count >= 3 and lines:
                # 移除末尾的空行
                while lines and lines[-1] == "":
                    lines.pop()
                break
        else:
            empty_count = 0

        lines.append(line)

    return '\n'.join(lines)


def interactive_synthesis(voice: str, api_key: str):
    """交互式语音合成"""
    print_divider()
    print("🎤 进入语音合成模式")
    print("   支持多行输入，连续按3次回车开始合成")
    print("   合成的音频保存到 output/ 目录")
    print("   输入 q 退出")
    print_divider()

    while True:
        text = read_multiline_input()

        if text is None:
            break

        text = text.strip()
        if not text:
            continue

        print()
        synthesize_speech(text, voice, api_key)

    print("\n👋 感谢使用，再见！")


def select_or_create_voice(api_key: str) -> str | None:
    """选择已有音色或创建新音色"""
    voices = load_voices()

    # 显示已有音色
    if voices:
        print("📚 已保存的音色:")
        voice_list = list(voices.items())
        for i, (name, info) in enumerate(voice_list, 1):
            created = info.get('created_at', '未知')[:10]
            source = info.get('source_file', '未知')
            print(f"   [{i}] {name} (来源: {source}, 创建: {created})")
        print(f"   [n] 创建新音色")
        print(f"   [d] 删除音色")
        print()

        while True:
            choice = input("🎵 请选择 (输入序号/n/d，q 退出): ").strip().lower()

            if choice == 'q':
                return None

            if choice == 'n':
                break  # 创建新音色

            if choice == 'd':
                del_input = input("   输入要删除的音色序号: ").strip()
                if del_input.isdigit():
                    idx = int(del_input) - 1
                    if 0 <= idx < len(voice_list):
                        name = voice_list[idx][0]
                        if delete_voice(name):
                            print(f"   ✅ 已删除音色: {name}")
                            voices = load_voices()
                            voice_list = list(voices.items())
                            if not voices:
                                print("\n   没有已保存的音色，将创建新音色")
                                break
                            # 重新显示列表
                            print("\n📚 已保存的音色:")
                            for i, (name, info) in enumerate(voice_list, 1):
                                created = info.get('created_at', '未知')[:10]
                                source = info.get('source_file', '未知')
                                print(f"   [{i}] {name} (来源: {source}, 创建: {created})")
                            print(f"   [n] 创建新音色")
                            print(f"   [d] 删除音色")
                            print()
                continue

            if choice.isdigit():
                idx = int(choice) - 1
                if 0 <= idx < len(voice_list):
                    name, info = voice_list[idx]
                    print(f"\n✅ 已选择音色: {name}")
                    return info['voice']
                else:
                    print("❌ 无效的序号")
            else:
                print("❌ 无效的输入")
    else:
        print("📚 暂无已保存的音色，将创建新音色")

    # 创建新音色
    print_divider()
    print("📌 创建新音色")
    print("   准备一段你的声音录音（10-20秒），用于声音复刻")

    file_path = select_voice_file()
    if not file_path:
        return None

    # 输入音色名称
    while True:
        voice_name = input("\n📝 请为这个音色命名: ").strip()
        if not voice_name:
            print("❌ 名称不能为空")
            continue
        if voice_name in voices:
            overwrite = input(f"   音色 '{voice_name}' 已存在，是否覆盖？(y/n): ").strip().lower()
            if overwrite != 'y':
                continue
        break

    print_divider()
    print("📌 正在创建音色...")

    try:
        voice = create_voice(file_path, api_key, voice_name)
        # 保存音色
        save_voice(voice_name, voice, pathlib.Path(file_path).name)
        print(f"\n💾 音色已保存为: {voice_name}")
        return voice
    except Exception as e:
        print(f"\n❌ 创建音色失败: {e}")
        return None


def main():
    """主函数"""
    clear_screen()
    print_banner()

    # 检查 API Key
    api_key = check_api_key()
    if not api_key:
        sys.exit(1)

    print("✅ API Key 已配置")
    print_divider()

    # 选择或创建音色
    voice = select_or_create_voice(api_key)
    if not voice:
        print("\n👋 已取消，再见！")
        sys.exit(0)

    print_divider()
    print("🎉 音色已就绪！")
    print("   现在可以让 AI 用你的声音说话了")
    print(f"   合成的音频将保存到 {OUTPUT_DIR}/ 目录")

    # 进入交互模式
    interactive_synthesis(voice, api_key)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 已取消，再见！")
        sys.exit(0)
