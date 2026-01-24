声音复刻依托大模型进行特征提取，无需训练即可复刻声音。仅需提供 10~20 秒的音频，即可生成高度相似且听感自然的定制音色。声音复刻与语音合成是前后关联的两个步骤。本文档聚焦于介绍声音复刻的参数和接口细节，语音合成请参见[实时语音合成-通义千问](https://help.aliyun.com/zh/model-studio/qwen-tts-realtime)。

**用户指南**：关于模型介绍和选型建议请参见[实时语音合成-通义千问](https://help.aliyun.com/zh/model-studio/qwen-tts-realtime)。

## **音频要求**

高质量的输入音频是获得优质复刻效果的基础。

| **项目** | **要求** |
| --- | --- |
| **支持格式** | WAV (16bit)、MP3、M4A |
| **音频时长** | 推荐10~20秒，最长不得超过60秒 |
| **文件大小** | ＜ 10 MB |
| **采样率** | ≥ 24 kHz |
| **声道** | 单声道 |
| **内容** | 音频必须包含至少3秒连续清晰朗读（无背景音），其余部分仅允许短暂停顿（≤2秒）；整段音频应避免背景音乐、噪音或其他人声，确保核心朗读内容质量；请使用正常说话音频作为输入，不要上传歌曲或唱歌音频，以确保复刻效果准确和可用 |
| **语言** | 中文（zh）、英文（en）、德语（de）、意大利语（it）、葡萄牙语（pt）、西班牙语（es）、日语（ja）、韩语（ko）、法语（fr）、俄语（ru） |

## 快速开始：从复刻到合成

![image](https://help-static-aliyun-doc.aliyuncs.com/assets/img/zh-CN/0170858671/CAEQYxiBgMCNsMj91BkiIDdiMWQyMmQ0MzMzNjRjNGU4OGViYTU2MTE1OTExNTg05899512_20251120114927.389.svg)

### 1\. 工作流程

声音复刻与语音合成是紧密关联的两个独立步骤，遵循“先创建，后使用”的流程：

1.  创建音色
    
    调用[创建音色](#1eaa57d82did9)接口，上传一段音频。系统会分析该音频，创建一个专属的复刻音色。**此步骤必须指定**`**target_model**`**，声明创建的音色将由哪个语音合成模型驱动。**
    
    若已有创建好的音色（调用[查询音色列表](#401d33226330i)接口查看），可跳过这一步直接进行下一步。
    
2.  使用音色进行语音合成
    
    调用语音合成接口，传入上一步获得的音色。**此步骤指定的语音合成模型必须和上一步的**`**target_model**`**一致。**
    

### 2\. 模型配置与准备工作

选择合适的模型并完成准备工作。

#### 模型配置

声音复刻时需要指定以下两个模型：

-   声音复刻模型：qwen-voice-enrollment
    
-   驱动音色的语音合成模型：
    
    -   qwen3-tts-vc-realtime-2026-01-15
        
    -   qwen3-tts-vc-realtime-2025-11-27
        

#### 准备工作

1.  **获取API Key**：[获取API Key](https://help.aliyun.com/zh/model-studio/get-api-key)，为安全起见，推荐将API Key配置到环境变量。
    
2.  **安装SDK**：确保已[安装最新版DashScope SDK](https://help.aliyun.com/zh/model-studio/install-sdk)。
    
3.  **准备待复刻音频**：音频需符合[音频要求](https://help.aliyun.com/zh/model-studio/cosyvoice-clone-api#音频要求与最佳实践)。
    

### 3\. 端到端示例

以下示例演示了如何在语音合成中使用声音复刻生成的专属音色，实现与原音高度相似的输出效果。

-   **关键原则**：声音复刻时，`target_model`（驱动音色的语音合成模型）必须与后续调用语音合成接口时指定的语音合成模型一致，否则会合成失败。
    
-   示例使用本地音频文件 `voice.mp3` 进行声音复刻，运行代码时，请注意替换。
    

## Python

```
# coding=utf-8
# Installation instructions for pyaudio:
# APPLE Mac OS X
#   brew install portaudio
#   pip install pyaudio
# Debian/Ubuntu
#   sudo apt-get install python-pyaudio python3-pyaudio
#   or
#   pip install pyaudio
# CentOS
#   sudo yum install -y portaudio portaudio-devel && pip install pyaudio
# Microsoft Windows
#   python -m pip install pyaudio

import pyaudio
import os
import requests
import base64
import pathlib
import threading
import time
import dashscope  # DashScope Python SDK 版本需要不低于1.23.9
from dashscope.audio.qwen_tts_realtime import QwenTtsRealtime, QwenTtsRealtimeCallback, AudioFormat

# ======= 常量配置 =======
DEFAULT_TARGET_MODEL = "qwen3-tts-vc-realtime-2026-01-15"  # 声音复刻、语音合成要使用相同的模型
DEFAULT_PREFERRED_NAME = "guanyu"
DEFAULT_AUDIO_MIME_TYPE = "audio/mpeg"
VOICE_FILE_PATH = "voice.mp3"  # 用于声音复刻的本地音频文件的相对路径

TEXT_TO_SYNTHESIZE = [
    '对吧~我就特别喜欢这种超市，',
    '尤其是过年的时候',
    '去逛超市',
    '就会觉得',
    '超级超级开心！',
    '想买好多好多的东西呢！'
]

def create_voice(file_path: str,
                 target_model: str = DEFAULT_TARGET_MODEL,
                 preferred_name: str = DEFAULT_PREFERRED_NAME,
                 audio_mime_type: str = DEFAULT_AUDIO_MIME_TYPE) -> str:
    """
    创建音色，并返回 voice 参数
    """
    # 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key = "sk-xxx"
    api_key = os.getenv("DASHSCOPE_API_KEY")

    file_path_obj = pathlib.Path(file_path)
    if not file_path_obj.exists():
        raise FileNotFoundError(f"音频文件不存在: {file_path}")

    base64_str = base64.b64encode(file_path_obj.read_bytes()).decode()
    data_uri = f"data:{audio_mime_type};base64,{base64_str}"

    # 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：https://dashscope-intl.aliyuncs.com/api/v1/services/audio/tts/customization
    url = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization"
    payload = {
        "model": "qwen-voice-enrollment", # 不要修改该值
        "input": {
            "action": "create",
            "target_model": target_model,
            "preferred_name": preferred_name,
            "audio": {"data": data_uri}
        }
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    resp = requests.post(url, json=payload, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f"创建 voice 失败: {resp.status_code}, {resp.text}")

    try:
        return resp.json()["output"]["voice"]
    except (KeyError, ValueError) as e:
        raise RuntimeError(f"解析 voice 响应失败: {e}")

def init_dashscope_api_key():
    """
    初始化 dashscope SDK 的 API key
    """
    # 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    # 若没有配置环境变量，请用百炼API Key将下行替换为：dashscope.api_key = "sk-xxx"
    dashscope.api_key = os.getenv("DASHSCOPE_API_KEY")

# ======= 回调类 =======
class MyCallback(QwenTtsRealtimeCallback):
    """
    自定义 TTS 流式回调
    """
    def __init__(self):
        self.complete_event = threading.Event()
        self._player = pyaudio.PyAudio()
        self._stream = self._player.open(
            format=pyaudio.paInt16, channels=1, rate=24000, output=True
        )

    def on_open(self) -> None:
        print('[TTS] 连接已建立')

    def on_close(self, close_status_code, close_msg) -> None:
        self._stream.stop_stream()
        self._stream.close()
        self._player.terminate()
        print(f'[TTS] 连接关闭 code={close_status_code}, msg={close_msg}')

    def on_event(self, response: dict) -> None:
        try:
            event_type = response.get('type', '')
            if event_type == 'session.created':
                print(f'[TTS] 会话开始: {response["session"]["id"]}')
            elif event_type == 'response.audio.delta':
                audio_data = base64.b64decode(response['delta'])
                self._stream.write(audio_data)
            elif event_type == 'response.done':
                print(f'[TTS] 响应完成, Response ID: {qwen_tts_realtime.get_last_response_id()}')
            elif event_type == 'session.finished':
                print('[TTS] 会话结束')
                self.complete_event.set()
        except Exception as e:
            print(f'[Error] 处理回调事件异常: {e}')

    def wait_for_finished(self):
        self.complete_event.wait()

# ======= 主执行逻辑 =======
if __name__ == '__main__':
    init_dashscope_api_key()
    print('[系统] 初始化 Qwen TTS Realtime ...')

    callback = MyCallback()
    qwen_tts_realtime = QwenTtsRealtime(
        model=DEFAULT_TARGET_MODEL,
        callback=callback,
        # 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime
        url='wss://dashscope.aliyuncs.com/api-ws/v1/realtime'
    )
    qwen_tts_realtime.connect()
    
    qwen_tts_realtime.update_session(
        voice=create_voice(VOICE_FILE_PATH), # 将voice参数替换为复刻生成的专属音色
        response_format=AudioFormat.PCM_24000HZ_MONO_16BIT,
        mode='server_commit'
    )

    for text_chunk in TEXT_TO_SYNTHESIZE:
        print(f'[发送文本]: {text_chunk}')
        qwen_tts_realtime.append_text(text_chunk)
        time.sleep(0.1)

    qwen_tts_realtime.finish()
    callback.wait_for_finished()

    print(f'[Metric] session_id={qwen_tts_realtime.get_session_id()}, '
          f'first_audio_delay={qwen_tts_realtime.get_first_audio_delay()}s')
```

## Java

需要导入Gson依赖，若是使用Maven或者Gradle，添加依赖方式如下：

### Maven

在`pom.xml`中添加如下内容：

```
<!-- https://mvnrepository.com/artifact/com.google.code.gson/gson -->
<dependency>
    <groupId>com.google.code.gson</groupId>
    <artifactId>gson</artifactId>
    <version>2.13.1</version>
</dependency>
```

### Gradle

在`build.gradle`中添加如下内容：

```
// https://mvnrepository.com/artifact/com.google.code.gson/gson
implementation("com.google.code.gson:gson:2.13.1")
```

```
import com.alibaba.dashscope.audio.qwen_tts_realtime.*;
import com.alibaba.dashscope.exception.NoApiKeyException;
import com.google.gson.Gson;
import com.google.gson.JsonObject;

import javax.sound.sampled.*;
import java.io.*;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.file.*;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import java.util.Queue;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicReference;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.atomic.AtomicBoolean;

public class Main {
    // ===== 常量定义 =====
    // 声音复刻、语音合成要使用相同的模型
    private static final String TARGET_MODEL = "qwen3-tts-vc-realtime-2026-01-15";
    private static final String PREFERRED_NAME = "guanyu";
    // 用于声音复刻的本地音频文件的相对路径
    private static final String AUDIO_FILE = "voice.mp3";
    private static final String AUDIO_MIME_TYPE = "audio/mpeg";
    private static String[] textToSynthesize = {
            "对吧~我就特别喜欢这种超市",
            "尤其是过年的时候",
            "去逛超市",
            "就会觉得",
            "超级超级开心！",
            "想买好多好多的东西呢！"
    };

    // 生成 data URI
    public static String toDataUrl(String filePath) throws IOException {
        byte[] bytes = Files.readAllBytes(Paths.get(filePath));
        String encoded = Base64.getEncoder().encodeToString(bytes);
        return "data:" + AUDIO_MIME_TYPE + ";base64," + encoded;
    }

    // 调用 API 创建 voice
    public static String createVoice() throws Exception {
        // 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
        // 若没有配置环境变量，请用百炼API Key将下行替换为：String apiKey = "sk-xxx"
        String apiKey = System.getenv("DASHSCOPE_API_KEY");

        String jsonPayload =
                "{"
                        + "\"model\": \"qwen-voice-enrollment\"," // 不要修改该值
                        + "\"input\": {"
                        +     "\"action\": \"create\","
                        +     "\"target_model\": \"" + TARGET_MODEL + "\","
                        +     "\"preferred_name\": \"" + PREFERRED_NAME + "\","
                        +     "\"audio\": {"
                        +         "\"data\": \"" + toDataUrl(AUDIO_FILE) + "\""
                        +     "}"
                        + "}"
                        + "}";

        HttpURLConnection con = (HttpURLConnection) new URL("https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization").openConnection();
        con.setRequestMethod("POST");
        con.setRequestProperty("Authorization", "Bearer " + apiKey);
        con.setRequestProperty("Content-Type", "application/json");
        con.setDoOutput(true);

        try (OutputStream os = con.getOutputStream()) {
            os.write(jsonPayload.getBytes(StandardCharsets.UTF_8));
        }

        int status = con.getResponseCode();
        System.out.println("HTTP 状态码: " + status);

        try (BufferedReader br = new BufferedReader(
                new InputStreamReader(status >= 200 && status < 300 ? con.getInputStream() : con.getErrorStream(),
                        StandardCharsets.UTF_8))) {
            StringBuilder response = new StringBuilder();
            String line;
            while ((line = br.readLine()) != null) {
                response.append(line);
            }
            System.out.println("返回内容: " + response);

            if (status == 200) {
                JsonObject jsonObj = new Gson().fromJson(response.toString(), JsonObject.class);
                return jsonObj.getAsJsonObject("output").get("voice").getAsString();
            }
            throw new IOException("创建语音失败: " + status + " - " + response);
        }
    }

    // 实时PCM音频播放器类
    public static class RealtimePcmPlayer {
        private int sampleRate;
        private SourceDataLine line;
        private AudioFormat audioFormat;
        private Thread decoderThread;
        private Thread playerThread;
        private AtomicBoolean stopped = new AtomicBoolean(false);
        private Queue<String> b64AudioBuffer = new ConcurrentLinkedQueue<>();
        private Queue<byte[]> RawAudioBuffer = new ConcurrentLinkedQueue<>();

        // 构造函数初始化音频格式和音频线路
        public RealtimePcmPlayer(int sampleRate) throws LineUnavailableException {
            this.sampleRate = sampleRate;
            this.audioFormat = new AudioFormat(this.sampleRate, 16, 1, true, false);
            DataLine.Info info = new DataLine.Info(SourceDataLine.class, audioFormat);
            line = (SourceDataLine) AudioSystem.getLine(info);
            line.open(audioFormat);
            line.start();
            decoderThread = new Thread(new Runnable() {
                @Override
                public void run() {
                    while (!stopped.get()) {
                        String b64Audio = b64AudioBuffer.poll();
                        if (b64Audio != null) {
                            byte[] rawAudio = Base64.getDecoder().decode(b64Audio);
                            RawAudioBuffer.add(rawAudio);
                        } else {
                            try {
                                Thread.sleep(100);
                            } catch (InterruptedException e) {
                                throw new RuntimeException(e);
                            }
                        }
                    }
                }
            });
            playerThread = new Thread(new Runnable() {
                @Override
                public void run() {
                    while (!stopped.get()) {
                        byte[] rawAudio = RawAudioBuffer.poll();
                        if (rawAudio != null) {
                            try {
                                playChunk(rawAudio);
                            } catch (IOException e) {
                                throw new RuntimeException(e);
                            } catch (InterruptedException e) {
                                throw new RuntimeException(e);
                            }
                        } else {
                            try {
                                Thread.sleep(100);
                            } catch (InterruptedException e) {
                                throw new RuntimeException(e);
                            }
                        }
                    }
                }
            });
            decoderThread.start();
            playerThread.start();
        }

        // 播放一个音频块并阻塞直到播放完成
        private void playChunk(byte[] chunk) throws IOException, InterruptedException {
            if (chunk == null || chunk.length == 0) return;

            int bytesWritten = 0;
            while (bytesWritten < chunk.length) {
                bytesWritten += line.write(chunk, bytesWritten, chunk.length - bytesWritten);
            }
            int audioLength = chunk.length / (this.sampleRate*2/1000);
            // 等待缓冲区中的音频播放完成
            Thread.sleep(audioLength - 10);
        }

        public void write(String b64Audio) {
            b64AudioBuffer.add(b64Audio);
        }

        public void cancel() {
            b64AudioBuffer.clear();
            RawAudioBuffer.clear();
        }

        public void waitForComplete() throws InterruptedException {
            while (!b64AudioBuffer.isEmpty() || !RawAudioBuffer.isEmpty()) {
                Thread.sleep(100);
            }
            line.drain();
        }

        public void shutdown() throws InterruptedException {
            stopped.set(true);
            decoderThread.join();
            playerThread.join();
            if (line != null && line.isRunning()) {
                line.drain();
                line.close();
            }
        }
    }

    public static void main(String[] args) throws Exception {
        QwenTtsRealtimeParam param = QwenTtsRealtimeParam.builder()
                .model(TARGET_MODEL)
                // 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：wss://dashscope-intl.aliyuncs.com/api-ws/v1/realtime
                .url("wss://dashscope.aliyuncs.com/api-ws/v1/realtime")
                // 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
                // 若没有配置环境变量，请用百炼API Key将下行替换为：.apikey("sk-xxx")
                .apikey(System.getenv("DASHSCOPE_API_KEY"))
                .build();
        AtomicReference<CountDownLatch> completeLatch = new AtomicReference<>(new CountDownLatch(1));
        final AtomicReference<QwenTtsRealtime> qwenTtsRef = new AtomicReference<>(null);

        // 创建实时音频播放器实例
        RealtimePcmPlayer audioPlayer = new RealtimePcmPlayer(24000);

        QwenTtsRealtime qwenTtsRealtime = new QwenTtsRealtime(param, new QwenTtsRealtimeCallback() {
            @Override
            public void onOpen() {
                // 连接建立时的处理
            }
            @Override
            public void onEvent(JsonObject message) {
                String type = message.get("type").getAsString();
                switch(type) {
                    case "session.created":
                        // 会话创建时的处理
                        break;
                    case "response.audio.delta":
                        String recvAudioB64 = message.get("delta").getAsString();
                        // 实时播放音频
                        audioPlayer.write(recvAudioB64);
                        break;
                    case "response.done":
                        // 响应完成时的处理
                        break;
                    case "session.finished":
                        // 会话结束时的处理
                        completeLatch.get().countDown();
                    default:
                        break;
                }
            }
            @Override
            public void onClose(int code, String reason) {
                // 连接关闭时的处理
            }
        });
        qwenTtsRef.set(qwenTtsRealtime);
        try {
            qwenTtsRealtime.connect();
        } catch (NoApiKeyException e) {
            throw new RuntimeException(e);
        }
        QwenTtsRealtimeConfig config = QwenTtsRealtimeConfig.builder()
                .voice(createVoice()) // 将voice参数替换为复刻生成的专属音色
                .responseFormat(QwenTtsRealtimeAudioFormat.PCM_24000HZ_MONO_16BIT)
                .mode("server_commit")
                .build();
        qwenTtsRealtime.updateSession(config);
        for (String text:textToSynthesize) {
            qwenTtsRealtime.appendText(text);
            Thread.sleep(100);
        }
        qwenTtsRealtime.finish();
        completeLatch.get().await();

        // 等待音频播放完成并关闭播放器
        audioPlayer.waitForComplete();
        audioPlayer.shutdown();
        System.exit(0);
    }
}
```

## **API参考**

使用不同 API 时，请确保使用同一账号进行操作。

### **创建音色**

上传用于复刻的音频，创建自定义音色。

-   **URL**
    
    中国内地：
    
    ```
    POST https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization
    ```
    
    国际：
    
    ```
    POST https://dashscope-intl.aliyuncs.com/api/v1/services/audio/tts/customization
    ```
    
-   **请求头**
    
    | **参数** | **类型** | **是否必须** | **说明** |
    | --- | --- | --- | --- |
    | Authorization | string | 支持  | 鉴权令牌，格式为`Bearer <your_api_key>`，使用时，将“`<your_api_key>`”替换为实际的API Key。 |
    | Content-Type | string | 支持  | 请求体中传输的数据的媒体类型。固定为`application/json`。 |
    
-   **消息体**
    
    包含所有请求参数的消息体如下，对于可选字段，在实际业务中可根据需求省略。
    
    **重要**
    
    注意区分如下参数：
    
    -   `model`：声音复刻模型，固定为`qwen-voice-enrollment`
        
    -   `target_model`：驱动音色的语音合成模型，须和后续调用语音合成接口时使用的语音合成模型一致，否则合成会失败
        
    
    ```
    {
        "model": "qwen-voice-enrollment",
        "input": {
            "action": "create",
            "target_model": "qwen3-tts-vc-realtime-2026-01-15",
            "preferred_name": "guanyu",
            "audio": {
                "data": "https://xxx.wav"
            },
            "text": "可选项，填入audio.data对应的文本",
            "language": "可选项，填入audio.data对应的语种，如zh"
        }
    }
    ```
    
-   **请求参数**
    
    | **参数** | **类型** | **默认值** | **是否必须** | **说明** |
    | --- | --- | --- | --- | --- |
    | model | string | \\- | 支持  | 声音复刻模型，固定为`qwen-voice-enrollment`。 |
    | action | string | \\- | 支持  | 操作类型，固定为`create`。 |
    | target\\_model | string | \\- | 支持  | 驱动音色的语音合成模型，支持的模型有： - qwen3-tts-vc-realtime-2026-01-15 - qwen3-tts-vc-realtime-2025-11-27 必须与后续调用语音合成接口时使用的语音合成模型一致，否则合成会失败。 |
    | preferred\\_name | string | \\- | 支持  | 为音色指定一个便于识别的名称（仅允许数字、大小写字母和下划线，不超过16个字符）。建议选用与角色、场景相关的标识。 > 该关键字会在复刻的音色名中出现，例如关键字为“guanyu”，最终音色名为“qwen-tts-vc-guanyu-voice-20250812105009984-838b” |
    | audio.data | string | \\- | 支持  | 用于复刻的音频（录制时需遵循[录音操作指南](#8d342f3949vge)，音频需满足[音频要求](#音频要求与最佳实践)）。 可通过以下两种方式提交音频数据： 1. [Data URL](https://www.rfc-editor.org/rfc/rfc2397) 格式：`data:<mediatype>;base64,<data>` - `<mediatype>`：MIME类型 - WAV：`audio/wav` - MP3：`audio/mpeg` - M4A：`audio/mp4` - `<data>`：音频转成的Base64编码的字符串 Base64编码会增大体积，请控制原文件大小，确保编码后仍小于10MB - 示例：`data:audio/wav;base64,SUQzBAAAAAAAI1RTU0UAAAAPAAADTGF2ZjU4LjI5LjEwMAAAAAAAAAAAAAAA//PAxABQ/BXRbMPe4IQAhl9` **点击查看示例代码** Python ``` import base64, pathlib # input.mp3为用于声音复刻的本地音频文件，请替换为自己的音频文件路径，确保其符合音频要求 file_path = pathlib.Path("input.mp3") base64_str = base64.b64encode(file_path.read_bytes()).decode() data_uri = f"data:audio/mpeg;base64,{base64_str}" ``` Java ``` import java.nio.file.*; import java.util.Base64; public class Main { /** * filePath为用于声音复刻的本地音频文件，请替换为自己的音频文件路径，确保其符合音频要求 */ public static String toDataUrl(String filePath) throws Exception { byte[] bytes = Files.readAllBytes(Paths.get(filePath)); String encoded = Base64.getEncoder().encodeToString(bytes); return "data:audio/mpeg;base64," + encoded; } // 使用示例 public static void main(String[] args) throws Exception { System.out.println(toDataUrl("input.mp3")); } } ``` 2. 音频URL（推荐将音频[上传至OSS](https://help.aliyun.com/zh/oss/user-guide/simple-upload#a632b50f190j8)） - 文件大小不超过10MB - URL必须公网可访问且无需鉴权 |
    | text | string | \\- | 不支持 | 与`audio.data`音频内容相匹配的文本。 传入该参数后，服务端会对比音频与该文本的差异，若差异过大，将返回Audio.PreprocessError。 |
    | language | string | \\- | 不支持 | `audio.data`音频对应的语种。 支持`zh`（中文）、`en`（英文）、`de`（德语）、`it`（意大利语）、`pt`（葡萄牙语）、`es`（西班牙语）、`ja`（日语）、`ko`（韩语）、`fr`（法语）、`ru`（俄语）。 若使用该参数，设置的语种要和实际用于复刻的音频的语种一致。 |
    
-   **响应参数**
    
    **点击查看响应示例**
    
    ```
    {
        "output": {
            "voice": "yourVoice",
            "target_model": "qwen3-tts-vc-realtime-2026-01-15"
        },
        "usage": {
            "count": 1
        },
        "request_id": "yourRequestId"
    }
    ```
    
    需关注的参数如下：
    
    | **参数** | **类型** | **说明** |
    | --- | --- | --- |
    | voice | string | 音色名称，可直接用于语音合成接口的`voice`参数。 |
    | target\\_model | string | 驱动音色的语音合成模型，支持的模型有： - qwen3-tts-vc-realtime-2026-01-15 - qwen3-tts-vc-realtime-2025-11-27 必须与后续调用语音合成接口时使用的语音合成模型一致，否则合成会失败。 |
    | request\\_id | string | Request ID。 |
    | count | integer | 本次请求实际计入费用的“创建音色”次数，本次请求的费用为 count×0.01元。 创建音色时，count恒为1。 |
    
-   **示例代码**
    
    **重要**
    
    注意区分如下参数：
    
    -   `model`：声音复刻模型，固定为`qwen-voice-enrollment`
        
    -   `target_model`：驱动音色的语音合成模型，须和后续调用语音合成接口时使用的语音合成模型一致，否则合成会失败
        
    
    ## cURL
    
    若未将API Key配置到环境变量，需将示例中的`$DASHSCOPE_API_KEY`替换为实际的API Key。
    
    ```
    # ======= 重要提示 =======
    # 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：https://dashscope-intl.aliyuncs.com/api/v1/services/audio/tts/customization
    # 新加坡地域和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    # === 执行时请删除该注释 ===
    
    curl -X POST https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization \
    -H "Authorization: Bearer $DASHSCOPE_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "qwen-voice-enrollment",
        "input": {
            "action": "create",
            "target_model": "qwen3-tts-vc-realtime-2026-01-15",
            "preferred_name": "guanyu",
            "audio": {
                "data": "https://xxx.wav"
            }
        }
    }'
    ```
    
    ## Python
    
    ```
    import os
    import requests
    import base64, pathlib
    
    target_model = "qwen3-tts-vc-realtime-2026-01-15"
    preferred_name = "guanyu"
    audio_mime_type = "audio/mpeg"
    
    file_path = pathlib.Path("input.mp3")
    base64_str = base64.b64encode(file_path.read_bytes()).decode()
    data_uri = f"data:{audio_mime_type};base64,{base64_str}"
    
    # 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key = "sk-xxx"
    api_key = os.getenv("DASHSCOPE_API_KEY")
    # 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：https://dashscope-intl.aliyuncs.com/api/v1/services/audio/tts/customization
    url = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization"
    
    payload = {
        "model": "qwen-voice-enrollment", # 不要修改这个值
        "input": {
            "action": "create",
            "target_model": target_model,
            "preferred_name": preferred_name,
            "audio": {
                "data": data_uri
            }
        }
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # 发送 POST 请求
    resp = requests.post(url, json=payload, headers=headers)
    
    if resp.status_code == 200:
        data = resp.json()
        voice = data["output"]["voice"]
        print(f"生成的 voice 参数为: {voice}")
    else:
        print("请求失败:", resp.status_code, resp.text)
    ```
    
    ## Java
    
    ```
    import com.google.gson.Gson;
    import com.google.gson.JsonObject;
    
    import java.io.*;
    import java.net.HttpURLConnection;
    import java.net.URL;
    import java.nio.file.*;
    import java.util.Base64;
    
    public class Main {
        private static final String TARGET_MODEL = "qwen3-tts-vc-realtime-2026-01-15";
        private static final String PREFERRED_NAME = "guanyu";
        private static final String AUDIO_FILE = "input.mp3";
        private static final String AUDIO_MIME_TYPE = "audio/mpeg";
    
        public static String toDataUrl(String filePath) throws Exception {
            byte[] bytes = Files.readAllBytes(Paths.get(filePath));
            String encoded = Base64.getEncoder().encodeToString(bytes);
            return "data:" + AUDIO_MIME_TYPE + ";base64," + encoded;
        }
    
        public static void main(String[] args) {
            // 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
            // 若没有配置环境变量，请用百炼API Key将下行替换为：String apiKey = "sk-xxx"
            String apiKey = System.getenv("DASHSCOPE_API_KEY");
            // 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：https://dashscope-intl.aliyuncs.com/api/v1/services/audio/tts/customization
            String apiUrl = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization";
    
            try {
                // 构造 JSON 请求体（注意内部的引号需转义）
                String jsonPayload =
                        "{"
                                + "\"model\": \"qwen-voice-enrollment\"," // 不要修改该值
                                + "\"input\": {"
                                +     "\"action\": \"create\","
                                +     "\"target_model\": \"" + TARGET_MODEL + "\","
                                +     "\"preferred_name\": \"" + PREFERRED_NAME + "\","
                                +     "\"audio\": {"
                                +         "\"data\": \"" + toDataUrl(AUDIO_FILE) + "\""
                                +     "}"
                                + "}"
                                + "}";
    
                HttpURLConnection con = (HttpURLConnection) new URL(apiUrl).openConnection();
                con.setRequestMethod("POST");
                con.setRequestProperty("Authorization", "Bearer " + apiKey);
                con.setRequestProperty("Content-Type", "application/json");
                con.setDoOutput(true);
    
                // 发送请求体
                try (OutputStream os = con.getOutputStream()) {
                    os.write(jsonPayload.getBytes("UTF-8"));
                }
    
                int status = con.getResponseCode();
                InputStream is = (status >= 200 && status < 300)
                        ? con.getInputStream()
                        : con.getErrorStream();
    
                StringBuilder response = new StringBuilder();
                try (BufferedReader br = new BufferedReader(new InputStreamReader(is, "UTF-8"))) {
                    String line;
                    while ((line = br.readLine()) != null) {
                        response.append(line);
                    }
                }
    
                System.out.println("HTTP 状态码: " + status);
                System.out.println("返回内容: " + response.toString());
    
                if (status == 200) {
                    // 解析 JSON
                    Gson gson = new Gson();
                    JsonObject jsonObj = gson.fromJson(response.toString(), JsonObject.class);
                    String voice = jsonObj.getAsJsonObject("output").get("voice").getAsString();
                    System.out.println("生成的 voice 参数为: " + voice);
                }
    
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }
    ```
    

### **查询音色列表**

分页查询已创建的音色列表。

-   **URL**
    
    中国内地：
    
    ```
    POST https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization
    ```
    
    国际：
    
    ```
    POST https://dashscope-intl.aliyuncs.com/api/v1/services/audio/tts/customization
    ```
    
-   **请求头**
    
    | **参数** | **类型** | **是否必须** | **说明** |
    | --- | --- | --- | --- |
    | Authorization | string | 支持  | 鉴权令牌，格式为`Bearer <your_api_key>`，使用时，将“`<your_api_key>`”替换为实际的API Key。 |
    | Content-Type | string | 支持  | 请求体中传输的数据的媒体类型。固定为`application/json`。 |
    
-   **消息体**
    
    包含所有请求参数的消息体如下，对于可选字段，在实际业务中可根据需求省略。
    
    **重要**
    
    `model`：声音复刻模型，固定为`qwen-voice-enrollment`，请勿修改。
    
    ```
    {
        "model": "qwen-voice-enrollment",
        "input": {
            "action": "list",
            "page_size": 2,
            "page_index": 0
        }
    }
    ```
    
-   **请求参数**
    
    | **参数** | **类型** | **默认值** | **是否必须** | **说明** |
    | --- | --- | --- | --- | --- |
    | model | string | \\- | 支持  | 声音复刻模型，固定为`qwen-voice-enrollment`。 |
    | action | string | \\- | 支持  | 操作类型，固定为`list`。 |
    | page\\_index | integer | 0   | 不支持 | 页码索引。取值范围：\\[0, 1000000\\]。 |
    | page\\_size | integer | 10  | 不支持 | 每页包含数据条数。取值范围：\\[0, 1000000\\]。 |
    
-   **响应参数**
    
    **点击查看响应示例**
    
    ```
    {
        "output": {
            "voice_list": [
                {
                    "voice": "yourVoice1",
                    "gmt_create": "2025-08-11 17:59:32",
                    "target_model": "qwen3-tts-vc-realtime-2026-01-15"
                },
                {
                    "voice": "yourVoice2",
                    "gmt_create": "2025-08-11 17:38:10",
                    "target_model": "qwen3-tts-vc-realtime-2026-01-15"
                }
            ]
        },
        "usage": {
            "count": 0
        },
        "request_id": "yourRequestId"
    }
    ```
    
    需关注的参数如下：
    
    | **参数** | **类型** | **说明** |
    | --- | --- | --- |
    | voice | string | 音色名称，可直接用于语音合成接口的`voice`参数。 |
    | gmt\\_create | string | 创建音色的时间。 |
    | target\\_model | string | 驱动音色的语音合成模型，支持的模型有： - qwen3-tts-vc-realtime-2026-01-15 - qwen3-tts-vc-realtime-2025-11-27 必须与后续调用语音合成接口时使用的语音合成模型一致，否则合成会失败。 |
    | request\\_id | string | Request ID。 |
    | count | integer | 本次请求实际计入费用的“创建音色”次数，本次请求的费用为 count×0.01元。 查询音色不计费，因此`count`恒为0。 |
    
-   **示例代码**
    
    **重要**
    
    `model`：声音复刻模型，固定为`qwen-voice-enrollment`，请勿修改。
    
    ## cURL
    
    若未将API Key配置到环境变量，需将示例中的`$DASHSCOPE_API_KEY`替换为实际的API Key。
    
    ```
    # ======= 重要提示 =======
    # 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：https://dashscope-intl.aliyuncs.com/api/v1/services/audio/tts/customization
    # 新加坡地域和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    # === 执行时请删除该注释 ===
    
    curl --location --request POST 'https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization' \
    --header 'Authorization: Bearer $DASHSCOPE_API_KEY' \
    --header 'Content-Type: application/json' \
    --data '{
        "model": "qwen-voice-enrollment",
        "input": {
            "action": "list",
            "page_size": 10,
            "page_index": 0
        }
    }'
    ```
    
    ## Python
    
    ```
    import os
    import requests
    
    # 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key = "sk-xxx"
    api_key = os.getenv("DASHSCOPE_API_KEY")
    # 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：https://dashscope-intl.aliyuncs.com/api/v1/services/audio/tts/customization
    url = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization"
    
    payload = {
        "model": "qwen-voice-enrollment", # 不要修改该值
        "input": {
            "action": "list",
            "page_size": 10,
            "page_index": 0
        }
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    print("HTTP 状态码:", response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        voice_list = data["output"]["voice_list"]
    
        print("查询到的音色列表：")
        for item in voice_list:
            print(f"- 音色: {item['voice']}  创建时间: {item['gmt_create']}  模型: {item['target_model']}")
    else:
        print("请求失败:", response.text)
    ```
    
    ## Java
    
    ```
    import com.google.gson.Gson;
    import com.google.gson.JsonArray;
    import com.google.gson.JsonObject;
    
    import java.io.BufferedReader;
    import java.io.InputStreamReader;
    import java.io.OutputStream;
    import java.net.HttpURLConnection;
    import java.net.URL;
    
    public class Main {
        public static void main(String[] args) {
            // 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
            // 若没有配置环境变量，请用百炼API Key将下行替换为：String apiKey = "sk-xxx"
            String apiKey = System.getenv("DASHSCOPE_API_KEY");
            // 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：https://dashscope-intl.aliyuncs.com/api/v1/services/audio/tts/customization
            String apiUrl = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization";
    
            // JSON 请求体（旧版本 Java 无 """ 多行字符串）
            String jsonPayload =
                    "{"
                            + "\"model\": \"qwen-voice-enrollment\"," // 不要修改该值
                            + "\"input\": {"
                            +     "\"action\": \"list\","
                            +     "\"page_size\": 10,"
                            +     "\"page_index\": 0"
                            + "}"
                            + "}";
    
            try {
                HttpURLConnection con = (HttpURLConnection) new URL(apiUrl).openConnection();
                con.setRequestMethod("POST");
                con.setRequestProperty("Authorization", "Bearer " + apiKey);
                con.setRequestProperty("Content-Type", "application/json");
                con.setDoOutput(true);
    
                try (OutputStream os = con.getOutputStream()) {
                    os.write(jsonPayload.getBytes("UTF-8"));
                }
    
                int status = con.getResponseCode();
                BufferedReader br = new BufferedReader(new InputStreamReader(
                        status >= 200 && status < 300 ? con.getInputStream() : con.getErrorStream(), "UTF-8"));
    
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = br.readLine()) != null) {
                    response.append(line);
                }
                br.close();
    
                System.out.println("HTTP 状态码: " + status);
                System.out.println("返回 JSON: " + response.toString());
    
                if (status == 200) {
                    Gson gson = new Gson();
                    JsonObject jsonObj = gson.fromJson(response.toString(), JsonObject.class);
                    JsonArray voiceList = jsonObj.getAsJsonObject("output").getAsJsonArray("voice_list");
    
                    System.out.println("\n 查询到的音色列表：");
                    for (int i = 0; i < voiceList.size(); i++) {
                        JsonObject voiceItem = voiceList.get(i).getAsJsonObject();
                        String voice = voiceItem.get("voice").getAsString();
                        String gmtCreate = voiceItem.get("gmt_create").getAsString();
                        String targetModel = voiceItem.get("target_model").getAsString();
    
                        System.out.printf("- 音色: %s  创建时间: %s  模型: %s\n",
                                voice, gmtCreate, targetModel);
                    }
                }
    
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }
    ```
    

### **删除音色**

删除指定音色，释放对应额度。

-   **URL**
    
    中国内地：
    
    ```
    POST https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization
    ```
    
    国际：
    
    ```
    POST https://dashscope-intl.aliyuncs.com/api/v1/services/audio/tts/customization
    ```
    
-   **请求头**
    
    | **参数** | **类型** | **是否必须** | **说明** |
    | --- | --- | --- | --- |
    | Authorization | string | 支持  | 鉴权令牌，格式为`Bearer <your_api_key>`，使用时，将“`<your_api_key>`”替换为实际的API Key。 |
    | Content-Type | string | 支持  | 请求体中传输的数据的媒体类型。固定为`application/json`。 |
    
-   **消息体**
    
    包含所有请求参数的消息体如下，对于可选字段，在实际业务中可根据需求省略：
    
    **重要**
    
    `model`：声音复刻模型，固定为`qwen-voice-enrollment`，请勿修改。
    
    ```
    {
        "model": "qwen-voice-enrollment",
        "input": {
            "action": "delete",
            "voice": "yourVoice"
        }
    }
    ```
    
-   **请求参数**
    
    | **参数** | **类型** | **默认值** | **是否必须** | **说明** |
    | --- | --- | --- | --- | --- |
    | model | string | \\- | 支持  | 声音复刻模型，固定为`qwen-voice-enrollment`。 |
    | action | string | \\- | 支持  | 操作类型，固定为`delete`。 |
    | voice | string | \\- | 支持  | 待删除的音色。 |
    
-   **响应参数**
    
    **点击查看响应示例**
    
    ```
    {
        "usage": {
            "count": 0
        },
        "request_id": "yourRequestId"
    }
    ```
    
    需关注的参数如下：
    
    | **参数** | **类型** | **说明** |
    | --- | --- | --- |
    | request\\_id | string | Request ID。 |
    | count | integer | 本次请求实际计入费用的“创建音色”次数，本次请求的费用为 count×0.01元。 删除音色不计费，因此`count`恒为0。 |
    
-   **示例代码**
    
    **重要**
    
    `model`：声音复刻模型，固定为`qwen-voice-enrollment`，请勿修改。
    
    ## cURL
    
    若未将API Key配置到环境变量，需将示例中的`$DASHSCOPE_API_KEY`替换为实际的API Key。
    
    ```
    # ======= 重要提示 =======
    # 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：https://dashscope-intl.aliyuncs.com/api/v1/services/audio/tts/customization
    # 新加坡地域和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    # === 执行时请删除该注释 ===
    
    curl --location --request POST 'https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization' \
    --header 'Authorization: Bearer $DASHSCOPE_API_KEY' \
    --header 'Content-Type: application/json' \
    --data '{
        "model": "qwen-voice-enrollment",
        "input": {
            "action": "delete",
            "voice": "yourVoice"
        }
    }'
    ```
    
    ## Python
    
    ```
    import os
    import requests
    
    # 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
    # 若没有配置环境变量，请用百炼API Key将下行替换为：api_key = "sk-xxx"
    api_key = os.getenv("DASHSCOPE_API_KEY")
    # 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：https://dashscope-intl.aliyuncs.com/api/v1/services/audio/tts/customization
    url = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization"
    
    voice_to_delete = "yourVoice"  # 要删除的音色（替换为真实值）
    
    payload = {
        "model": "qwen-voice-enrollment", # 不要修改该值
        "input": {
            "action": "delete",
            "voice": voice_to_delete
        }
    }
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    print("HTTP 状态码:", response.status_code)
    
    if response.status_code == 200:
        data = response.json()
        request_id = data["request_id"]
    
        print(f"删除成功")
        print(f"Request ID: {request_id}")
    else:
        print("请求失败:", response.text)
    ```
    
    ## Java
    
    ```
    import com.google.gson.Gson;
    import com.google.gson.JsonObject;
    
    import java.io.BufferedReader;
    import java.io.InputStreamReader;
    import java.io.OutputStream;
    import java.net.HttpURLConnection;
    import java.net.URL;
    
    public class Main {
        public static void main(String[] args) {
            // 新加坡和北京地域的API Key不同。获取API Key：https://help.aliyun.com/zh/model-studio/get-api-key
            // 若没有配置环境变量，请用百炼API Key将下行替换为：String apiKey = "sk-xxx"
            String apiKey = System.getenv("DASHSCOPE_API_KEY");
            // 以下为北京地域url，若使用新加坡地域的模型，需将url替换为：https://dashscope-intl.aliyuncs.com/api/v1/services/audio/tts/customization
            String apiUrl = "https://dashscope.aliyuncs.com/api/v1/services/audio/tts/customization";
            String voiceToDelete = "yourVoice"; // 要删除的音色（替换为真实值）
    
            // 构造 JSON 请求体（字符串拼接，兼容 Java 8）
            String jsonPayload =
                    "{"
                            + "\"model\": \"qwen-voice-enrollment\"," // 不要修改该值
                            + "\"input\": {"
                            +     "\"action\": \"delete\","
                            +     "\"voice\": \"" + voiceToDelete + "\""
                            + "}"
                            + "}";
    
            try {
                // 建立 POST 连接
                HttpURLConnection con = (HttpURLConnection) new URL(apiUrl).openConnection();
                con.setRequestMethod("POST");
                con.setRequestProperty("Authorization", "Bearer " + apiKey);
                con.setRequestProperty("Content-Type", "application/json");
                con.setDoOutput(true);
    
                // 发送请求体
                try (OutputStream os = con.getOutputStream()) {
                    os.write(jsonPayload.getBytes("UTF-8"));
                }
    
                int status = con.getResponseCode();
                BufferedReader br = new BufferedReader(new InputStreamReader(
                        status >= 200 && status < 300 ? con.getInputStream() : con.getErrorStream(), "UTF-8"));
    
                StringBuilder response = new StringBuilder();
                String line;
                while ((line = br.readLine()) != null) {
                    response.append(line);
                }
                br.close();
    
                System.out.println("HTTP 状态码: " + status);
                System.out.println("返回 JSON: " + response.toString());
    
                if (status == 200) {
                    Gson gson = new Gson();
                    JsonObject jsonObj = gson.fromJson(response.toString(), JsonObject.class);
                    String requestId = jsonObj.get("request_id").getAsString();
    
                    System.out.println("删除成功");
                    System.out.println("Request ID: " + requestId);
                }
    
            } catch (Exception e) {
                e.printStackTrace();
            }
        }
    }
    ```
    

### **语音合成**

如何使用声音复刻生成的专属音色合成个性化的声音，请参见[快速开始：从复刻到合成](#bb60d81324wsu)。

**用于声音复刻的语音合成模型（如 qwen3-tts-vc-realtime-2026-01-15）为专用模型，仅支持使用复刻生成的音色，不支持Chelsie、Serena、Ethan、Cherry等公共预设音色。**

## **音色配额与自动清理规则**

-   **总数限制**：1000个音色/账号
    
    > 当前接口不提供音色数量查询功能，可通过调用[查询音色列表](#401d33226330i)接口自行统计音色数目
    
-   **自动清理**：若单个音色在过去一年内未被用于任何语音合成请求，系统将自动将其删除
    

## **计费说明**

声音复刻和语音合成分开计费：

-   声音复刻：[创建音色](#1eaa57d82did9)按0.01 元/个计费，创建失败不计费
    
    **说明**
    
    免费额度说明（仅中国站北京地域和国际站新加坡地域有免费额度）：
    
    -   阿里云百炼开通后90天内，可享1000次免费音色创建机会。
        
    -   创建失败不占用免费次数。
        
    -   删除音色不会恢复免费次数。
        
    -   免费额度用完或超出 90 天有效期后，创建音色将按0.01 元/个的价格计费。
        
    
-   使用复刻生成的专属音色进行语音合成：按量（文本字符数）计费，详情请参见[实时语音合成-通义千问](https://help.aliyun.com/zh/model-studio/qwen-tts-realtime#a162110bff6c4)
    

## **版权与合法性**

您需对所提供声音的所有权及合法使用权负责，请注意阅读[服务协议](https://terms.alicdn.com/legal-agreement/terms/b_platform_service_agreement/20240229113512917/20240229113512917.html)。

## 录音操作指南

### **录音设备**

推荐使用具备降噪功能的麦克风，或在安静环境下使用手机近距离录音，以保证音源纯净。

### **录音环境**

#### **场地**

-   建议在 10 平方米以内的小型封闭空间录音。
    
-   优先选择配有吸音材料（如吸音棉、地毯、窗帘）的房间。
    
-   避免空旷大厅、会议室、教室等高混响场所。
    

#### **噪音控制**

-   室外噪音：关闭门窗，避免交通、施工等干扰。
    
-   室内噪音：关闭空调、风扇、日光灯镇流器等设备；可通过手机录制环境音并放大播放，识别潜在噪音源。
    

#### **混响控制**

-   混响会导致声音模糊、清晰度下降。
    
-   减少光滑表面反射：拉上窗帘、打开衣柜门、铺放衣物或床单覆盖桌面/柜面。
    
-   利用不规则物体（如书架、软包家具）实现声波漫反射。
    

### **录音文案**

-   文案内容灵活，建议与目标应用场景一致（例如，若用于客服场景，文案应为客服对话风格），但必须确保不包含任何敏感或非法词汇（如政治、色情、暴力相关内容），否则会导致复刻失败。
    
-   避免短句（如“你好”、“是的”），应使用完整句子。
    
-   保持语义连贯，朗读时避免频繁停顿（建议至少连续 3 秒无中断）。
    
-   可带入目标情绪（如亲切、严肃），但需避免过度夸张的戏剧化朗读，保持语调自然。
    

### **操作建议**

以普通卧室为例：

1.  关闭门窗，隔绝外部噪音。
    
2.  关闭空调、电扇等电器。
    
3.  拉上窗帘，减少玻璃反射。
    
4.  在桌面铺放衣物或毛毯，降低桌面反射。
    
5.  提前熟悉文案，设定角色语气，自然演绎。
    
6.  与录音设备保持约 10 厘米距离，避免喷麦或信号过弱。
    

## **错误信息**

如遇报错问题，请参见[错误信息](https://help.aliyun.com/zh/model-studio/error-code)进行排查。

 span.aliyun-docs-icon { color: transparent !important; font-size: 0 !important; } span.aliyun-docs-icon:before { color: black; font-size: 16px; } span.aliyun-docs-icon.icon-size-20:before { font-size: 20px; } span.aliyun-docs-icon.icon-size-22:before { font-size: 22px; } span.aliyun-docs-icon.icon-size-24:before { font-size: 24px; } span.aliyun-docs-icon.icon-size-26:before { font-size: 26px; } span.aliyun-docs-icon.icon-size-28:before { font-size: 28px; }
