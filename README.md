# GA · AI 伴侣

GA 提供企业版和个人版。企业版由 Spring Boot 处理账户、分发和简报，再通过 Python 智能体访问企业配置的模型 API。个人版由 FastAPI 单独运行，内置浏览器终端和 SQLite，可连接本机 Ollama 或 vLLM。两版复用 Python 对话、语音和三层记忆规则。[双版本架构](GA_Project_Code_Review/.md)

| 模块 | 职责 |
| --- | --- |
| `my-ai-app` | Vue 界面。注册、伴侣设置、流式文字、录音和语音回复、每日简报 |
| `VR_Gfriend` | Spring Boot 控制面。JWT、MySQL 账户与伴侣、简报调度、浏览器 SSE / WebSocket 与 gRPC 桥接 |
| `GAagent` | 两个 Python 入口。企业智能体使用 gRPC、Redis 与模型 API，个人终端使用 FastAPI、SQLite 和内置网页 |
| 模型服务 | 企业由部署方提供 API，个人可使用本机 vLLM 或 Ollama。两版分别配置语音 Beta |

## 运行个人版

个人版可以从源码直接启动，也可以安装 wheel 或运行 Docker 镜像。个人版用 `GA_DATA_DIR` 保存令牌、伴侣配置和三层记忆。

```powershell
cd GAagent
python -m venv .venv-personal
& .\.venv-personal\Scripts\python.exe -m pip install .
$env:GA_LLM_PROVIDER = 'mock'
$env:GA_ASR_PROVIDER = 'mock'
$env:GA_TTS_PROVIDER = 'mock'
& .\.venv-personal\Scripts\ga.exe
```

在另一个终端执行 `.\.venv-personal\Scripts\ga.exe token`，用令牌连接 `http://127.0.0.1:8081`。Docker、wheel 和 sdist 的命令见 [个人版说明](GAagent/README.md)。

构建产物位于 `GAagent/dist/`。可从仓库根目录载入已构建的个人版 Docker 镜像。

```powershell
docker load -i .\GAagent\dist\ga-personal-0.1.1-docker.tar.gz
```

## 运行企业版

需要 Java 17、Maven 3.9、Python 3.11+、Node.js 22.12+ 和 MySQL 8 / Redis 7。以下 PowerShell 命令从仓库根目录运行，分别在独立终端启动各进程。用自己的密码和服务令牌替换示例值。Java 和 Python 使用相同的 `GA_INTERNAL_TOKEN`。

### 1. 启动存储

已有 MySQL 和 Redis 时，可以创建一个空的 `aigf` 数据库，并在后续命令里使用对应地址和凭据。也可以启动仓库提供的两个本地容器。

```powershell
$env:GA_MYSQL_PASSWORD = '<你的开发数据库密码>'
docker compose up -d
```

Compose 将 MySQL 和 Redis 绑定到本机的 `13306` 和 `16379`。两者使用独立数据卷。Java 启动时执行建表脚本。已有数据库请先核对 `VR_Gfriend/src/main/resources/schema.sql`，脚本只补建缺失表。

### 2. 启动 Python 节点

企业智能体使用独立的 Python 环境。以下变量在启动企业智能体的终端设置。已有 `GAagent/.env` 的配置可加载，终端变量优先。将示例 API 地址、模型名和密钥替换为部署方提供的值。

```powershell
cd GAagent
python -m venv .venv-enterprise
& .\.venv-enterprise\Scripts\python.exe -m pip install -r requirements-enterprise.txt
$env:GA_REDIS_URL = 'redis://127.0.0.1:16379/0'
$env:GA_INTERNAL_TOKEN = '<与 Java 一致的服务令牌>'
$env:GA_ENTERPRISE_LLM_BASE_URL = 'https://api.example.com/v1'
$env:GA_ENTERPRISE_LLM_MODEL = '<服务商提供的模型名>'
$env:GA_ENTERPRISE_LLM_API_KEY = '<企业模型 API 密钥>'
& .\.venv-enterprise\Scripts\python.exe -m virtual_lover_agent.enterprise
```

企业智能体监听 gRPC `127.0.0.1:7000`。个人版的 FastAPI 健康检查在 `/health/live` 和 `/health/ready`，接口文档在 `/docs`。

### 3. 启动 Java 控制面

```powershell
$env:GA_MYSQL_URL = 'jdbc:mysql://127.0.0.1:13306/aigf?serverTimezone=UTC'
$env:GA_MYSQL_USER = 'ga'
$env:GA_MYSQL_PASSWORD = '<你的开发数据库密码>'
$env:GA_ENTERPRISE_REDIS_URL = 'redis://127.0.0.1:16379/0'
$env:GA_INTERNAL_TOKEN = '<与 Python 一致的服务令牌>'
$env:GA_JWT_SECRET = '<至少 32 字节的随机签名密钥>'
mvn -f VR_Gfriend/pom.xml spring-boot:run
```

默认 HTTP 端口 `8080`，gRPC 目标是 `static://127.0.0.1:7000`。默认简报时区为 `Asia/Shanghai`，可通过 `GA_BRIEFING_TIMEZONE` 修改。简报由服务定时生成，在线页面通过 WebSocket 接收。每个账户的最新简报存在 MySQL 中，重新打开页面可查看。

配置 `GA_ENTERPRISE_REDIS_URL` 后，Java 使用 Redis 协调各实例的模型请求配额。默认每个账户每分钟可发起 30 次文字生成和 12 轮语音，分别通过 `GA_ENTERPRISE_TEXT_REQUESTS_PER_MINUTE` 和 `GA_ENTERPRISE_VOICE_TURNS_PER_MINUTE` 配置。

### 4. 启动 Vue

```powershell
cd my-ai-app
npm ci
npm run dev
```

打开 `http://localhost:5173`，注册并选择伴侣后即可对话。首次录音需要浏览器授权。手机浏览器通过 HTTPS 使用麦克风。

企业 Vue 本机开发时通过 Vite 代理访问 Java。需要更改代理目标时设置 `GA_GATEWAY_URL`。

`npm run build` 生成静态产物。部署时让反向代理转发 `/api`、`/admin`、`/audio` 和 `/ws`。对话 SSE 路径需关闭响应缓冲，语音和简报路径需透传 WebSocket 升级。也可在构建时为 `VITE_API_BASE_URL` 指定独立 HTTPS 源，并配置 Java 的 `GA_ALLOWED_ORIGINS`。

## 接入模型

### 企业模型 API

企业版需要显式提供 `GA_ENTERPRISE_LLM_BASE_URL` 和 `GA_ENTERPRISE_LLM_MODEL`。API 需要认证时配置 `GA_ENTERPRISE_LLM_API_KEY`。同一企业端点也可用于摘要，或者用 `GA_ENTERPRISE_SUMMARY_BASE_URL`、`GA_ENTERPRISE_SUMMARY_MODEL` 和 `GA_ENTERPRISE_SUMMARY_API_KEY` 另配。用 `GA_ENTERPRISE_LLM_PROVIDER=mock` 可以在开发环境模拟模型回复。

已有企业部署若使用了 `GA_LLM_*`、`GA_SUMMARY_*` 或语音变量，请在企业环境中改用相应的 `GA_ENTERPRISE_` 前缀。旧版配置中的 `deepseek_url` 与 `deepseek_model` 如果成对设置，仍可用于企业模型 API。

### 个人本地模型

个人版通过以下变量配置模型。地址填写完整的 API 基址，包括服务要求的 `/v1` 或兼容路径。

| 用途 | 环境变量 |
| --- | --- |
| 对话 | `GA_LLM_PROVIDER=openai`，`GA_LLM_BASE_URL`、`GA_LLM_MODEL`、`GA_LLM_API_KEY` |
| 摘要 | `GA_SUMMARY_BASE_URL`、`GA_SUMMARY_MODEL`、`GA_SUMMARY_API_KEY` |
| 语音 Beta | 识别和合成分别设置，详见 [数字人 Beta](GA_Project_Code_Review/Voice_Avatar_Beta.md) |

在已安装 vLLM 的 Linux / WSL 环境执行 `vllm serve Qwen/Qwen2.5-7B-Instruct --host 127.0.0.1 --port 8000 --enable-prefix-caching` 可作为对话服务。摘要服务可在另一个端口运行较小模型，也可将两个用途指向同一个已加载的模型。[vLLM 快速启动](https://docs.vllm.ai/en/stable/getting_started/quickstart/)

使用 Ollama 时，先用 `ollama list` 确认本机模型，再把该模型名填入 `GA_LLM_MODEL`。在启动 GA 的 PowerShell 中配置如下。示例使用本机已有的 `qwen2.5:7b`。[Ollama 兼容 API](https://docs.ollama.com/api/openai-compatibility) · [Qwen2.5 模型列表](https://ollama.com/library/qwen2.5)

```powershell
$env:GA_LLM_PROVIDER = 'openai'
$env:GA_LLM_BASE_URL = 'http://127.0.0.1:11434/v1'
$env:GA_LLM_MODEL = 'qwen2.5:7b'
$env:GA_LLM_API_KEY = 'ollama'
```

个人版未设置摘要端点时复用以上模型。Docker Desktop 容器可通过 `host.docker.internal` 使用宿主机可访问的模型端口。[Docker Desktop 网络](https://docs.docker.com/desktop/features/networking/)

## 三层记忆

1. **近期对话**。文字和语音在完整回合结束后写入，用户与伴侣上下文相互隔离。
2. **滚动摘要**。超过 10 轮时后台压缩最旧的 3 轮，近期保留 4 条摘要。压缩与归档提交成功后才移除已处理的原始回合。
3. **长期归档**。更早的摘要进入长期归档，当前消息可通过中英文 BM25 召回最多 3 条。当前实现按用户扫描摘要归档并在 Python 进程内评分。

个人版使用 SQLite 存储相同的三层记忆。企业版兼容旧 Redis 对话和待归档摘要。仓库中的早期 Chroma 浏览器记忆快照是独立数据。简报和系统提示各自独立于用户对话历史。

## 接口与验证

- 浏览器文字使用 `POST /api/chat/stream`，请求为 `{"message":"你好"}`，接收 `message`、`done` 和 `error` SSE 事件。`GET /api/chat/history` 返回当前伴侣仍保留在近期记忆里的完整对话回合。
- 浏览器语音使用 `/audio` WebSocket。客户端发送单声道 PCM16 WAV 的二进制帧，以空二进制帧结束一轮。回复包含转写、类型、一个完整音频和结束事件。
- 个人终端使用 `ga token` 获取 Bearer Token。FastAPI 的 `POST /v1/chat/stream` 返回 SSE，`POST /v1/voice` 接收 `Content-Type: audio/wav` 并返回转写、伴侣文本和 Base64 音频。
- gRPC 以 `VR_Gfriend/src/main/proto/agent_proto.proto` 为契约。Java 由 Maven 生成绑定。更新 Python 绑定时先安装 `grpcio-tools==1.78.1`，再从仓库根目录执行 `python GAagent/generate_proto.py`。

```powershell
mvn -f VR_Gfriend/pom.xml test
cd my-ai-app
npm run build
```

Python 记忆测试从 `GAagent` 目录运行。安装 `fakeredis` 后执行 `python -m unittest discover -s tests -p 'test_dialogue_memory.py' -v`。

原始项目审查见 [GA_Project_Code_Review.md](GA_Project_Code_Review.md)。`AImodel` 里的 EchoMimic 数字人素材和运行环境是独立实验项目。此应用的对话页支持文本及录音语音回复。
