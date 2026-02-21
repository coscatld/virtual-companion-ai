import os

from dotenv import load_dotenv
from langchain_core.tools import tool
from serpapi import GoogleSearch

load_dotenv()
SEARCH_API_KEY = os.getenv("SEARCH_API_KEY")

@tool("news_search")
async def news_search(query: str) -> str:
    """
    专门用来查询新闻的工具。
    当用户询问“今天有什么大新闻”、“最近的科技动态”或需要特定领域的实时资讯时使用此工具。
    它会专注于最近 3 天的权威新闻源。

    Args:
        query: 新闻搜索关键词，如 "China AI news" 或 "今日头条"。
    """
    if not SEARCH_API_KEY:
        return "错误：未配置 API Key (SEARCH_API_KEY 或 tavily_api_key)，无法使用新闻搜索。"

    params = {
        "api_key": SEARCH_API_KEY,
        "engine": "google_news",  # 指定使用 Google News 引擎
        "q": query,  # 搜索词
        "gl": "cn",  # 地理位置定位 (cn: 中国)
        "hl": "zh-cn"  # 语言设置 (简体中文)
    }

    try:
        search = GoogleSearch(params)
        results = search.get_dict()

        # 提取新闻结果
        news_results = results.get("news_results", [])

        if not news_results:
            return f"抱歉，未找到关于 '{query}' 的相关新闻。"

        # 格式化输出 (取前 5 条)
        formatted_news = []
        for i, news in enumerate(news_results[:5], 1):
            title = news.get("title", "无标题")
            source = news.get("source", {}).get("name", "未知来源")
            date = news.get("date", "未知时间")
            link = news.get("link", "#")
            snippet = news.get("snippet", "暂无摘要")

            item = (
                f"{i}. 【{title}】\n"
                f"   - 来源: {source} ({date})\n"
                f"   - 摘要: {snippet}\n"
                f"   - 链接: {link}\n"
            )
            formatted_news.append(item)

        return f"为您找到关于 '{query}' 的最新新闻：\n\n" + "\n".join(formatted_news)

    except Exception as e:
        return f"新闻查询工具发生错误: {str(e)}"