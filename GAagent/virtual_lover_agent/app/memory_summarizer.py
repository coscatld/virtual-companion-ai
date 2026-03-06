import asyncio
import logging
import json
from datetime import datetime
import redis.asyncio as redis
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 初始化专门用于总结的小模型 (指向本地 vLLM 端口)
# 注意：vLLM 的默认 openai 兼容端口是 8000
VLLM_BASE_URL = os.getenv("vllm_summary_url", "http://127.0.0.1:8000/v1")
VLLM_MODEL = os.getenv("vllm_model", "qwen/Qwen2.5-1.5B-Instruct") 
REDIS_HOST = os.getenv("redis_host", "localhost")
REDIS_PORT = int(os.getenv("redis_port", "6379"))

llm_summarizer = ChatOpenAI(
    model=VLLM_MODEL,
    base_url=VLLM_BASE_URL,
    # 给小模型随便传个key，vLLM不需要校验
    api_key="vllm_local",
    temperature=0.3, # 总结任务需要低温度，保持事实客观
    max_tokens=150
)

# 总结 Prompt 模板
SUMMARY_PROMPT = PromptTemplate.from_template("""
你是一个智能记忆压缩助手。请阅读以下用户与AI伴侣的历史对话，并提取最重要的核心事实（如偏好、事件、计划、情绪变化）。
要求：
1. 必须用第三人称陈述句。
2. 忽略寒暄语和没有价值的闲聊内容。
3. 如果历史记录中没有实质性信息，请回复"NO_INFO"。
4. 总结字数控制在 50 字以内。

历史对话记录：
{dialogue_history}

摘要提炼：
""")

async def summarize_history(redis_client, user_id: str, history_list: list):
    """提取历史记录并生成总结"""

    dialogue_text = "\n".join(history_list)
    
    chain = SUMMARY_PROMPT | llm_summarizer
    response = await chain.ainvoke({"dialogue_history": dialogue_text})
    summary_text = response.content.strip()

    if summary_text and summary_text != "NO_INFO":
        logging.info(f"[Summarizer] User {user_id} generated summary: {summary_text}")
        
        # 将摘要存入 RAG 长记忆队列中，等待 Java 端 / 或者 Python Vector Worker 入库
        # 这里用一个中转 List 'vr:long_term_queue'，通知向量数据库该建索引了
        memory_item = {
            "user_id": user_id,
            "summary": summary_text,
            "timestamp": datetime.now().isoformat()
        }
        await redis_client.lpush("vr:long_term_queue", json.dumps(memory_item))
        return True
    return False

async def memory_pruning_worker():
    """后台死循环协程：监督 Redis 里的短记忆长度，实施修剪过滤"""
    logging.info("🚀 Memory Pruning Worker started. Scanning Redis for overflow histories...")
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    
    while True:
        try:
            # 扫描所有 vr:history:* 键
            # 警告：真实生产环境数据量大时，应改用 SCAN 游标，这里用 keys 仅为演示和低并发用
            keys = await r.keys("vr:history:*")
            
            for key in keys:
                user_id = key.split(":")[-1]
                # 获取该用户的对话条数
                length = await r.llen(key)

                # 如果积攒的短记忆大于等于 12 条 (6轮 QA)
                if length >= 12:
                    logging.info(f"Triggering summarization for {user_id} (Length: {length})")

                    # 假设新的聊天记录是追加到队尾 (rpush)，那么最旧的6条在前面，索引是 0 到 5。
                    # 或者如果是追加到队头 (lpush)，最旧的6条是在最后面，需要调参。
                    # 一般记忆推荐 lrange(key, 0, 5) 或者 lrange(key, -6, -1) 来正确获取。
                    old_history = await r.lrange(key, 0, 5)  # <--- 修改成这样（假设旧消息存第一位）

                    if old_history:
                        # 交给vllm处理再删记录
                        success = await summarize_history(r, user_id, old_history)
                        if success:
                            # 如果旧消息存头上，成功后则从第6条开始保留最新记录
                            await r.ltrim(key, 6, -1)  # <--- 修改逻辑：保留索引6到末尾的最新日志

            # 巡检间隔 30 秒，避免 CPU 空转
            await asyncio.sleep(30)
            
        except Exception as e:
            logging.error(f"Worker Error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(memory_pruning_worker())
