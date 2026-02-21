import os
from langchain_core.tools import tool


@tool("read_local_file")
def read_local_file(file_path: str) -> str:
    """
    用于读取用户指定的本地文件内容，支持 txt, md, log 等纯文本格式。
    通常用于获取用户的【日程安排】、【工作计划】或【待办事项】。

    Args:
        file_path: 文件的绝对路径。
    """
    # 1. 安全与路径检查
    if not os.path.exists(file_path):
        return f"错误：找不到文件，路径为 {file_path}"

    if not os.path.isfile(file_path):
        return f"错误：路径 {file_path} 指向的不是一个文件。"

    try:
        # 2. 读取文件 (默认使用 utf-8)
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 3. 简单的长度限制 (防止一个大文件把 LLM 的上下文撑爆)
        max_chars = 4000
        if len(content) > max_chars:
            return (
                f"【文件 {os.path.basename(file_path)} 内容 (前 {max_chars} 字)】:\n"
                f"{content[:max_chars]}\n"
                f"...(剩余内容已截断)..."
            )

        return f"【文件 {os.path.basename(file_path)} 完整内容】:\n{content}"

    except UnicodeDecodeError:
        return "读取失败：文件编码不是 UTF-8，无法读取。"
    except Exception as e:
        return f"读取文件时发生未知错误: {str(e)}"