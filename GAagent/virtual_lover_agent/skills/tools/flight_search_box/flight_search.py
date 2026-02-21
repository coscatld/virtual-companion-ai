from langchain_core.tools import tool
from serpapi import GoogleSearch  # 修改点：直接使用 serpapi 库，而不是 LangChain 的 Wrapper
import os
from dotenv import load_dotenv

load_dotenv()

SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")


@tool("flight_search")
async def flight_search(departure: str, arrival: str, date: str) -> str:
    """
    专门用于查询机票价格的工具。
    参数:
    departure: 出发城市，要使用机场代码 (如 "Fuzhou：FOC", "Shanghai：PVG")
    arrival: 到达城市，要使用机场代码 (如 "Tokyo：NRT", "beijing: PEK")
    date: 出发日期 (格式 YYYY-MM-DD)
    """
    # 构造 SerpApi 所需参数
    params = {
        "api_key": SERPAPI_API_KEY,
        "engine": "google_flights",
        "departure_id": departure,
        "arrival_id": arrival,
        "outbound_date": date,
        "currency": "CNY",
        "hl": "zh-cn",
        "type": "2"#1往返,2单程
    }

    try:
        # 修改点：正确调用 GoogleSearch 获取字典数据
        search = GoogleSearch(params)
        results = search.get_dict()

        # 检查是否出错
        if "error" in results:
            return f"API报错: {results['error']}"

        # 解析最佳航班
        if "best_flights" in results and results['best_flights']:
            best_flight = results['best_flights'][0]
            price = best_flight.get('price', '未知价格')

            # 提取航司信息 (结构较深，需注意)
            flight_segments = best_flight.get('flights', [])
            airline = flight_segments[0].get('airline', '未知航司') if flight_segments else '未知航司'

            duration = best_flight.get('total_duration', '未知时长')

            return f"查到了！{date} 从{departure}飞{arrival}，最推荐的是 {airline} 的航班，价格是 {price}人民币，时长 {duration}分钟。"
        else:
            return "抱歉，暂时没查到当天的航班信息，可能是由于直飞限制或日期太远。"

    except Exception as e:
        return f"查询过程中发生错误: {str(e)}"


if __name__ == "__main__":
    import asyncio

    # 测试代码
    print(asyncio.run(flight_search.ainvoke({
        "departure": "FOC",
        "arrival": "PEK",
        "date": "2026-02-23"
    })))