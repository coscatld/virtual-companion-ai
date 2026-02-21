import os
from langchain_core.tools import tool
from tavily import TavilyClient

tavily_api_key = os.getenv("TAVILY_API_KEY")
tavily_client = TavilyClient(api_key=tavily_api_key) if tavily_api_key else None


@tool("web_search_tavily")
async def web_search_tavily(query: str) -> str:
    """
    一个深度的互联网搜索引擎，专用于辅助回答复杂问题。
    【适用场景】：
    1. 需要阅读网页正文才能回答的问题（如"详细介绍一下这篇论文"）。
    2. 需要整合多个来源的信息时。
    3. 用户询问具体的生活攻略、评测、教程时。

    【返回内容】：
    包含搜索结果的标题、来源链接以及页面的核心文本内容。
    """
    if not tavily_client:
        return "错误：未配置 TAVILY_API_KEY，无法使用高级搜索功能。"

    try:
        # search_depth="advanced" 会进行深度爬取，虽然稍慢但质量极高
        response = tavily_client.search(
            query=query,
            search_depth="advanced",
            max_results=3,  # 限制结果数量，节省 Token
            include_answer=True,  # 让 Tavily 先生成一个简短回答
            include_raw_content=False  # 不需要原始 HTML，只要清洗后的文本
        )

        # 构造结构化数据给 AI
        context = []

        # 1. Tavily 的智能摘要
        if response.get("answer"):
            context.append(f"【AI 智能摘要】: {response['answer']}\n")

        # 2. 详细网页内容
        for res in response.get("results", []):
            context.append(f"---")
            context.append(f"【标题】: {res.get('title')}")
            context.append(f"【链接】: {res.get('url')}")
            # content 是清洗后的正文，AI 读这个最舒服
            context.append(f"【正文片段】: {res.get('content')[:500]}...")  # 截断一下防止太长

        return "\n".join(context)

    except Exception as e:
        return f"深度搜索失败: {str(e)}"


if __name__ == "__main__":
    import asyncio
    print(asyncio.run(web_search_tavily.ainvoke("LangGraph 是什么")))