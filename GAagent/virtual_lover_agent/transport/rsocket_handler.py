from rsocket.payload import Payload
from rsocket.routing.request_router import RequestRouter
from rsocket.routing.routing_request_handler import RoutingRequestHandler
from rsocket.streams.stream_from_async_generator import StreamFromAsyncGenerator

from virtual_lover_agent.agent.graph.gragh01 import agent_graph
from virtual_lover_agent.agent.prompts.prompt import construct_agent_inputs
from virtual_lover_agent.protos import agent_proto_pb2
from virtual_lover_agent.skills.memory import skill_retriever

router = RequestRouter()


# ======================================================
#  部分 A:业务逻辑
# ======================================================
async def response_stream_generator(msg:str,system_prompt:str):
    relevant_memory_from_java = ""#todo：java传relevant_memory

    #Python检索技能记忆
    retrieved_skill = skill_retriever.retrieve_related_skills(query=msg)

    if retrieved_skill:
        print(f"✅ 命中技能记忆: {retrieved_skill[:50]}...")
    #构建prompt
    inputs = construct_agent_inputs(
        java_system_prompt=system_prompt,
        user_msg=msg,
        relevant_memory=relevant_memory_from_java,
        skill_info=retrieved_skill  #注入技能
    )
    used_tools = set()  # 本轮用了哪些工具
    final_answer = ""  # 最终回答累计

    async for event in agent_graph.astream_events(inputs, version="v1"):
        kind = event["event"]

        # --- 情况 1: LLM 正在生成回复 (打字机效果) ---
        if kind == "on_chat_model_stream":
            content = event["data"]["chunk"].content
            if content:
                final_answer += content
                # 封装成 Protobuf
                response = agent_proto_pb2.ChatResponse()
                response.delta = content
                # 序列化并 yield 给 Java
                yield (Payload(data=response.SerializeToString()),False)

        # --- 情况 2: Agent 决定调用工具 (可选：通知前端正在搜索) ---
        elif kind == "on_tool_start":
            tool_name = event['name']
            used_tools.add(tool_name)
            response = agent_proto_pb2.ChatResponse()
            # 可以定义一个特殊格式告诉前端在转圈圈，或者直接用文字
            response.delta = f"\n[系统: 正在调用 {tool_name} 查询...]\n"
            yield (Payload(data=response.SerializeToString()),False)

    try:
       if used_tools and len(final_answer) > 50:
           print("🧠 开始写入技能记忆")

           skill_retriever.save_skill(
               query=msg,
               tools=list(used_tools),
               result=final_answer
           )

    except Exception as e:print("Skill Save Error:", e)



# ======================================================
#  部分 B: 路由处理器
#  这里负责解包请求，并返回一个 RSocket 能看懂的 Stream 对象
# ======================================================
@router.stream("chatStream")
async def chat_stream(payload: Payload, composite_metadata):
    # 1. 解码 Java 发来的请求
    request = agent_proto_pb2.ChatRequest()
    request.ParseFromString(payload.data)
    user_msg = request.user_message
    user_prompt = request.system_prompt

    return StreamFromAsyncGenerator(lambda: response_stream_generator(user_msg,user_prompt))


def handler_factory():
    return RoutingRequestHandler(router)