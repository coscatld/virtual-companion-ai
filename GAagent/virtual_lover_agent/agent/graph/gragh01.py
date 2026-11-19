from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from virtual_lover_agent.app.config import ProviderSettings


def create_agent(settings: ProviderSettings, *, public_tools: bool = False):
    tools = []
    if public_tools:
        from virtual_lover_agent.skills.tools.flight_search_box.flight_search import flight_search
        from virtual_lover_agent.skills.tools.news_search.news_search import news_search
        from virtual_lover_agent.skills.tools.web_search_box.web_search import web_search

        tools.extend([web_search, flight_search, news_search])

    model = ChatOpenAI(
        api_key=settings.api_key or "not-needed",
        model=settings.model,
        base_url=settings.base_url,
        temperature=0.7,
        max_tokens=1024,
        timeout=45,
        max_retries=1,
        streaming=True,
    )
    return create_react_agent(model, tools)
