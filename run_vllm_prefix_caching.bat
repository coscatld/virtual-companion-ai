@echo off
setlocal

rem Set GA_VLLM_EXECUTABLE to an absolute WSL path if vLLM lives in a virtual environment.
if not defined GA_VLLM_EXECUTABLE set "GA_VLLM_EXECUTABLE=vllm"
if not defined GA_LLM_MODEL set "GA_LLM_MODEL=Qwen/Qwen2.5-7B-Instruct"
if not defined GA_VLLM_PORT set "GA_VLLM_PORT=8000"

wsl.exe --exec "%GA_VLLM_EXECUTABLE%" serve "%GA_LLM_MODEL%" --host 127.0.0.1 --port "%GA_VLLM_PORT%" --enable-prefix-caching
exit /b %errorlevel%
