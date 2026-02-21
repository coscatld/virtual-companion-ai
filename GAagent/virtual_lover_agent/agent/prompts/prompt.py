
from langchain_core.messages import SystemMessage, HumanMessage


def construct_agent_inputs(java_system_prompt: str, user_msg: str, relevant_memory: str = "",
                           skill_info: str = "") -> dict:
    """
    构建输入，融合：人设 + 情感记忆(Java) + 技能记忆(Python VectorDB) + 当前问题
    """

    # 1. 基础人设 (来自 Java)
    base_prompt = java_system_prompt

    # 2. 注入情感/对话记忆 (来自 Java RAG)
    memory_section = ""
    if relevant_memory:
        memory_section = (
            f"\n\n【回忆胶囊 (Context)】：\n"
            f"以下是你和用户之前的相关对话记忆：\n"
            f"{relevant_memory}\n"
        )

    # 3. 注入技能记忆 (来自 Python ChromaDB)
    # 这是告诉 Agent "面对这种问题，标准做法是什么"
    skill_section = ""
    if skill_info:
        skill_section = (
            f"\n\n【技能经验 (SOP)】：\n"
            f"检测到涉及类似任务，请参考以下过往的成功经验/步骤来执行：\n"
            f"{skill_info}\n"
        )

    # 4. 润色指令
    meta_instruction = (
        "\n\n【重要指令】：\n"
        "1. 参考【技能经验】中的步骤使用工具，但不要在回复中直接念出步骤。\n"
        "2. 最终回复必须结合【人设】语气进行润色，不要输出生硬的数据。\n"
    )

    # 拼接最终的 Prompt
    full_system_prompt = base_prompt + memory_section + skill_section + meta_instruction

    return {
        "messages": [
            SystemMessage(content=full_system_prompt),
            HumanMessage(content=user_msg)
        ]
    }