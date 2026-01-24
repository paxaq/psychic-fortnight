#!/bin/bash
# 声音复刻工具 - 环境安装脚本

set -e

echo "=========================================="
echo "  Qwen 声音复刻工具 - 环境安装"
echo "=========================================="
echo

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ -f /etc/debian_version ]]; then
        echo "debian"
    elif [[ -f /etc/redhat-release ]]; then
        echo "redhat"
    else
        echo "unknown"
    fi
}

OS=$(detect_os)
echo "检测到系统: $OS"
echo

# 安装系统依赖
echo "[1/4] 安装系统依赖..."
case $OS in
    macos)
        if ! command -v brew &> /dev/null; then
            echo "错误: 请先安装 Homebrew (https://brew.sh)"
            exit 1
        fi
        brew install portaudio
        ;;
    debian)
        sudo apt-get update
        sudo apt-get install -y portaudio19-dev python3-venv python3-dev
        ;;
    redhat)
        sudo yum install -y portaudio portaudio-devel python3-devel
        ;;
    *)
        echo "警告: 未知操作系统，请手动安装 portaudio"
        ;;
esac
echo "✓ 系统依赖安装完成"
echo

# 创建虚拟环境
echo "[2/4] 创建 Python 虚拟环境..."
if [[ ! -d "venv" ]]; then
    python3 -m venv venv
    echo "✓ 虚拟环境创建完成"
else
    echo "✓ 虚拟环境已存在"
fi
echo

# 激活虚拟环境并安装依赖
echo "[3/4] 安装 Python 依赖..."
source venv/bin/activate
pip install --upgrade pip -q
pip install python-dotenv pyaudio requests "dashscope>=1.23.9" -q
echo "✓ Python 依赖安装完成"
echo

# 创建 .env 文件
echo "[4/4] 配置环境变量..."
if [[ ! -f ".env" ]]; then
    cp .env.example .env
    echo "✓ 已创建 .env 文件，请编辑并填入 API Key"
    echo "  nano .env"
else
    echo "✓ .env 文件已存在"
fi
echo

echo "=========================================="
echo "  安装完成！"
echo "=========================================="
echo
echo "使用方法:"
echo "  1. 编辑 .env 文件，填入 DASHSCOPE_API_KEY"
echo "  2. 准备一段声音录音 (10-20秒 MP3/WAV)"
echo "  3. 运行: source venv/bin/activate && python voice_clone.py"
echo
