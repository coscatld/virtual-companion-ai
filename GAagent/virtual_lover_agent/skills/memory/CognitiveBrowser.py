from datetime import datetime
from typing import Dict, Optional

import json
from playwright.async_api import async_playwright, Page
import chromadb
from chromadb.utils import embedding_functions


# --- 配置区域 ---
# 实际使用中建议换成 OpenAI 或 HuggingFace 的 Embedding
EMBEDDING_FUNC = embedding_functions.DefaultEmbeddingFunction()
DB_PATH = "./agent_memory_db"


class CognitiveBrowser:
    def __init__(self, llm):
        self.llm = llm
        self.playwright = None
        self.browser = None
        self.context: Optional = None
        self.page: Optional[Page] = None

        # 初始化记忆库 (Episodic Memory)
        self.chroma_client = chromadb.PersistentClient(path=DB_PATH)
        self.memory_collection = self.chroma_client.get_or_create_collection(
            name="browser_episodic_memory",
            embedding_function=EMBEDDING_FUNC
        )

        # 核心：SoM 注入脚本
        # 改进点：增强了可见性检查，增加了对 aria-label 的优先读取，模拟无障碍树的逻辑
        self.som_script = r"""
        () => {
            document.querySelectorAll('.agent-som-label').forEach(el => el.remove());
            document.querySelectorAll('[data-agent-id]').forEach(el => el.removeAttribute('data-agent-id'));

            const selectors = [
                'a[href]','button','input','textarea','select',
                '[role="button"]','[role="link"]','[role="checkbox"]',
                '[role="menuitem"]','[role="tab"]','[contenteditable="true"]'
            ];

            let idCounter = 1;
            const interactiveMap = [];

            function isVisible(el) {
                const rect = el.getBoundingClientRect();
                if (rect.width < 5 || rect.height < 5) return false;
                const style = window.getComputedStyle(el);
                return style.display !== 'none' &&
                       style.visibility !== 'hidden' &&
                       style.opacity !== '0';
            }

            document.querySelectorAll(selectors.join(',')).forEach(el => {
                if (!isVisible(el)) return;

                const aid = idCounter++;
                el.setAttribute('data-agent-id', aid);

                const rect = el.getBoundingClientRect();

                const label = document.createElement('div');
                label.className = 'agent-som-label';
                label.textContent = aid;

                Object.assign(label.style,{
                    position:'absolute',
                    left:`${window.scrollX + rect.left}px`,
                    top:`${window.scrollY + rect.top}px`,
                    background:'#ff0000',
                    color:'#fff',
                    fontSize:'10px',
                    padding:'1px 3px',
                    zIndex:'2147483647',
                    pointerEvents:'none'
                });

                document.body.appendChild(label);

                let name =
                    el.innerText ||
                    el.getAttribute('aria-label') ||
                    el.getAttribute('placeholder') ||
                    "";

                name = name.replace(/\\s+/g,' ').trim().slice(0,50);

                interactiveMap.push({
                    id: aid,
                    role: el.getAttribute('role') || el.tagName.toLowerCase(),
                    name: name,
                    value: el.value || ''
                });
            });

            return interactiveMap;
        }
        """

    async def start(self):
        self.playwright = await async_playwright().start()
        # 启动浏览器，headless=False 方便调试观察 SoM 标记
        self.browser = await self.playwright.chromium.launch(headless=False, args=["--start-maximized"])
        self.context = await self.browser.new_context(viewport={'width': 1920, 'height': 1080})
        self.page = await self.context.new_page()

    async def stop(self):
        if self.page: await self.page.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()

    async def perception(self) -> Dict:
        """
        感知阶段：注入 SoM，获取页面状态描述
        返回：结构化的页面描述数据
        """
        # 1. 执行 JS 注入，获取交互元素列表
        interactive_elements = await self.page.evaluate(self.som_script)

        # 2. 获取基本页面信息
        title = await self.page.title()
        url = self.page.url

        # 3. 构造给 LLM 看的 Prompt 文本 (Accessibility Tree 风格)
        # 使用 Markdown 表格形式，节省 Token 且对 LLM 友好
        obs_text = f"Page: {title}\nURL: {url}\n\nInteractive Elements:\n"
        obs_text += "| ID | Role | Name/Label | Current Value |\n"
        obs_text += "|----|------|------------|---------------|\n"

        for el in interactive_elements:
            obs_text += f"| {el['id']} | {el['role']} | {el['name']} | {el['value']} |\n"

        return {
            "text_observation": obs_text,
            "raw_elements": interactive_elements,
            "title": title,
            "url": url
        }

    async def act(self, action: Dict):
        """
        执行阶段：根据 LLM 的指令操作浏览器
        action 格式示例: {"name": "click", "target_id": 12}
        """
        action_name = action.get("name")
        target_id = action.get("target_id")
        value = action.get("value")

        log_msg = f"Executing: {action_name} on ID {target_id}"
        if value: log_msg += f" with value '{value}'"
        print(f"🤖 {log_msg}")

        try:
            # 使用 Playwright 强大的定位器，直接通过注入的属性定位
            target = self.page.locator(f'[data-agent-id="{target_id}"]')

            if action_name == "click":
                # 等待元素可点击，增强稳定性
                await target.click(timeout=5000)

            elif action_name == "type":
                await target.fill(value)

            elif action_name == "scroll":
                await self.page.evaluate("window.scrollBy(0, 500)")

            elif action_name == "goto":
                await self.page.goto(value)

            elif action_name == "done":
                print("✅ Task Completed.")
                return

            # 等待页面加载或网络空闲 (关键：防止操作过快)
            try:
                await self.page.wait_for_load_state("networkidle", timeout=3000)
            except:
                pass  # 超时则继续，不必强求完全空闲

            return log_msg  # 返回执行日志用于存入记忆

        except Exception as e:
            print(f"❌ Execution Failed: {str(e)}")
            return f"Failed: {action_name} - {str(e)}"

    def remember(self, observation: str, action_log: str, metadata: Dict):
        """
        记忆固化：将 (状态 + 动作) 存入向量库
        """
        timestamp = datetime.now().isoformat()

        # 构造存入向量库的内容。
        # 技巧：将 observation 和 action 结合，这样检索时能匹配到“在什么情况下做了什么”
        memory_content = f"""
        [Context]
        Title: {metadata['title']}
        URL: {metadata['url']}
        Interactive Elements Summary: {observation[:500]}... (truncated)


        {action_log}
        """

        self.memory_collection.add(
            documents=[memory_content],
            metadatas=[{
                "url": metadata['url'],
                "action": action_log,
                "timestamp": timestamp
            }],
            ids=[f"mem_{timestamp}"]
        )
        print("🧠 Memory Stored.")

    def recall(self, current_task: str, current_url: str) -> str:
        """
        记忆检索：基于当前任务和URL，找回相关的历史经验
        """
        # 构造查询向量，包含任务意图和当前环境
        query_text = f"Task: {current_task}, Environment: {current_url}"

        results = self.memory_collection.query(
            query_texts=[query_text],
            n_results=2  # 只取最相关的2条，避免污染上下文
        )

        if not results['documents']:
            return "No relevant past experience."

        docs = results["documents"]

        flat_docs = [d for group in docs for d in group]

        return "\n".join(flat_docs)

    async def run(self, task: str):

        await self.start()

        try:
            await self.page.goto("https://google.com")
            for step in range(10):
                perception = await self.perception()
                memory = self.recall(
                    task,
                    perception["url"]
                )

                llm_prompt = f"""
                Task:
                {task}
                Past Experience:
                {memory}
                Observation:
                {perception["text_observation"]}
                Decide next action.
                Return JSON:
                {{"name":"click","target_id":1}}
                """
                response = await self.llm.ainvoke(llm_prompt)
                action = json.loads(response.content)
                log = await self.act(action)
                self.remember(
                    perception["text_observation"],
                    log,
                    perception
                )
                if action["name"] == "done":
                    break
            return "Task Finished"
        finally:
            await self.stop()


