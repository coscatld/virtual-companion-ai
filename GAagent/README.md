# GA Personal Agent

GA 个人版是一套自托管的 FastAPI 伴侣终端。浏览器界面支持流式文字、录音和伴侣设置。三层对话记忆和伴侣配置保存在同一个本机 SQLite 数据库。

个人入口在 `virtual_lover_agent/personal/`，与企业入口 `virtual_lover_agent/enterprise/` 复用同一套对话和记忆核心。此安装包只提供个人终端及其依赖。企业智能体的部署方式见仓库根目录的 README。

## 安装发行包

需要 Python 3.11 或更新版本。在本地构建后，可安装发行目录下的 wheel。

```powershell
python -m pip install .\dist\ga_personal_agent-0.1.1-py3-none-any.whl
$env:GA_LLM_PROVIDER = 'mock'
$env:GA_ASR_PROVIDER = 'mock'
$env:GA_TTS_PROVIDER = 'mock'
ga
```

在另一个终端运行 `ga token`，把访问令牌填入 `http://127.0.0.1:8081` 的终端页面。也可以通过 `GA_PERSONAL_TOKEN` 指定自己的令牌。它与数据库使用同一个 `GA_DATA_DIR`。浏览器需要安全上下文才能录音，本机地址可直接使用。

默认文本模型连接 `http://127.0.0.1:8000/v1`。通过 `GA_LLM_BASE_URL`、`GA_LLM_MODEL` 和 `GA_LLM_API_KEY` 配置已部署的 OpenAI 兼容服务。个人版可以用同一个模型生成摘要，也能用 `GA_SUMMARY_BASE_URL` 和 `GA_SUMMARY_MODEL` 单独配置。语音由 `GA_ASR_PROVIDER` 和 `GA_TTS_PROVIDER` 各自启用。语音接口使用原始单声道 PCM16 WAV。

## 构建发行包

```powershell
python -m pip install build
python -m build
```

生成的 wheel 和 sdist 可用于本地安装或分发。

## 构建 Docker 镜像

在本目录执行以下命令。

```powershell
docker build -t ga-personal:0.1.1 .
docker run --name ga-personal --rm -p 127.0.0.1:8081:8081 -v ga-personal-data:/data -e GA_LLM_PROVIDER=mock -e GA_ASR_PROVIDER=mock -e GA_TTS_PROVIDER=mock ga-personal:0.1.1
docker exec ga-personal ga token
```

令牌命令在另一个终端执行。数据卷保存记忆和设置。连接宿主机上的模型服务时，在容器环境变量里设置容器可访问的模型地址。
