@echo off
echo.
echo ========================================================
echo   启动带有前缀缓存 (Prefix Caching) 的 vLLM 服务
echo ========================================================
echo.
echo 注意：vLLM 官方推荐在 WSL2 (Linux 子系统) 中运行。
echo 请确保您所在的环境已安装 vLLM，并且显存足够。
echo.

set MODEL_PATH="qwen/Qwen2.5-7B-Instruct"
set PORT=8000
set GPU_MEMORY_UTIL=0.9

echo 正在启动 vLLM Engine...
echo 使用模型: %MODEL_PATH%
echo 启用特性: --enable-prefix-caching (极致加速长人设对话)

python -m vllm.entrypoints.openai.api_server ^
    --model %MODEL_PATH% ^
    --port %PORT% ^
    --gpu-memory-utilization %GPU_MEMORY_UTIL% ^
    --enable-prefix-caching ^
    --max-model-len 8192

pause
