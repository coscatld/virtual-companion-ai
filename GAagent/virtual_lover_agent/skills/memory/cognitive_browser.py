import contextvars
from virtual_lover_agent.skills.memory.CognitiveBrowser import CognitiveBrowser
from langchain_core.tools import tool

# 使用 ContextVar 按协程上下文隔离 Browser 实例，解决并发状态污染单点故障
_browser_session_var = contextvars.ContextVar('browser_session', default=None)

def _get_browser(llm):
    """
    按当前 Asyncio 协程上下文获取对应的 CognitiveBrowser 实例。
    并发请求将会在此处拿掉独立的 browser，防止互相覆盖 Cookie 和网页状态。
    """
    browser = _browser_session_var.get()
    if browser is None:
        browser = CognitiveBrowser(llm=llm)
        _browser_session_var.set(browser)
    return browser


@tool("cognitive_browser")
async def cognitive_browser(task: str) -> str:
    """
    Interact with real websites.

    Use this when:

    - login required
    - javascript rendering needed
    - booking tickets
    - filling forms

    Input:
    natural language instruction.
    """
    # 延迟导入，只在运行时才获取 llm01，此时它已经初始化完毕
    from virtual_lover_agent.agent.graph.gragh01 import llm01

    browser = _get_browser(llm01)
    result = await browser.run(task)

    return result