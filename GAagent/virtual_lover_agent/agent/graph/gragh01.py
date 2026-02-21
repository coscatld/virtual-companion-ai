import asyncio

from virtual_lover_agent.skills.memory.cognitive_browser import cognitive_browser
from virtual_lover_agent.skills.tools.flight_search_box.flight_search import flight_search
from virtual_lover_agent.skills.tools.news_search.news_search import news_search
from virtual_lover_agent.skills.tools.read_local_file_box.read_local_file import read_local_file
from virtual_lover_agent.skills.tools.web_search_box.web_search import web_search
from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI
import os

load_dotenv()
model = os.getenv("deepseek_model")
base_url = os.getenv("deepseek_url")
api_key = os.getenv("deepseek_api_key")

llm03 = ChatOpenAI(
    api_key=api_key,
    model=model,
    base_url=base_url,
    temperature=0.7,
    streaming=True,
)
llm02 = ChatOllama(
    model = "qwen2.5:7b",
    temperature=0.7,
    streaming=True,
)
llm01 = ChatOpenAI(
    api_key=api_key,
    model=model,
    base_url=base_url,
    temperature=0.7,
    streaming=True,
)
tools = [
         web_search,
         flight_search,
         read_local_file,
         news_search,
         cognitive_browser]
agent_graph = create_react_agent(llm01,tools)


async def main():
    result = await agent_graph.ainvoke({

        "messages": [

            ("user",
             "use browser search LangChain agent tutorial on google")

        ]

    })

    print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())