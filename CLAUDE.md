# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python example project demonstrating Alibaba's Qwen Text-to-Speech (TTS) voice cloning API. It enables voice cloning from audio samples and real-time speech synthesis using the DashScope SDK.

## Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Run the example
python example.py

# Install dependencies (if needed)
pip install dashscope>=1.23.9 pyaudio requests
```

## Environment Setup

Create a `.env` file in the project root (see `.env.example`):
```
DASHSCOPE_API_KEY=your-api-key-here
```

Place a voice audio file (10-20 seconds, ≥24kHz sample rate) in the project root before running.

## Architecture

**Two-Step Voice Cloning Process:**

1. **Voice Enrollment** - Upload audio to `qwen-voice-enrollment` model → returns voice parameter
2. **Speech Synthesis** - Send text + voice parameter to `qwen3-tts-vc-realtime` model → streams audio output

**Key Components in example.py:**

- `create_voice()` - REST API call to create custom voice from audio file (Base64 encoded)
- `init_dashscope_api_key()` - Initializes DashScope SDK authentication
- `MyCallback` - Event handler class for real-time TTS WebSocket streaming
- Audio playback uses PyAudio with threading for non-blocking I/O

**API Details:**
- Voice creation endpoint: `https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization`
- Real-time synthesis: WebSocket at `wss://dashscope.aliyuncs.com/api-ws/v1/realtime`
- Audio streaming format: PCM 24000Hz mono 16-bit

## Audio Requirements

- Formats: WAV (16-bit), MP3, M4A
- Sample rate: ≥24 kHz
- Duration: 10-20 seconds (max 60 seconds)
- File size: <10 MB

## Reference Documentation

See `Qwen-TTS声音复刻API参考.md` for complete API reference including request/response parameters, error codes, and recording best practices.
