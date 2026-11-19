import asyncio

from langchain_core.tools import tool
from langchain_community.utilities import DuckDuckGoSearchAPIWrapper

#test_ddgs
# 初始化搜索包装器
# region="wt-wt" 表示全球搜索，"cn-zh" 表示偏向中文结果
# time="d" 表示限定过去一天（获取最新信息），不填则不限时间
ddg_wrapper = DuckDuckGoSearchAPIWrapper(region="cn-zh", max_results=5)

@tool("web_search")
async def web_search(query: str) -> str:
    """
    一个通用的互联网搜索引擎。
    【适用场景】：
    1. 当你不知道当前的日期、时间、天气时。
    2. 当用户询问最新的新闻、电影、热点事件时。
    3. 当你需要查询具体的 factual 知识（如"某某的生日"）时。

    【使用说明】：
    输入 query 应为简洁的搜索关键词，例如 "杭州周末天气" 或 "最新上映的科幻电影"。
    """
    try:
        results = await asyncio.to_thread(ddg_wrapper.run, query)

        if not results:
            return "抱歉，搜索引擎没有返回有效结果，请尝试通过提问获取更多上下文。"

        return results

    except Exception:
        return "搜索工具暂时不可用。"

if __name__ == "__main__":
    import asyncio
    print(asyncio.run(web_search.ainvoke("福州到东京2月17号的机票价格")))
