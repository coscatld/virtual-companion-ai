import datetime
import uuid
import chromadb
from chromadb.utils import embedding_functions


EMBEDDING_FUNC = embedding_functions.DefaultEmbeddingFunction()

DB_PATH = "./agent_memory_db"


class SkillRetriever:

    def __init__(self):

        self.client = chromadb.PersistentClient(path=DB_PATH)

        self.collection = self.client.get_or_create_collection(
            name="agent_skill_memory",
            embedding_function=EMBEDDING_FUNC
        )

    # =====================================
    # 技能检索
    # =====================================
    def save_skill(
            self,
            query: str,
            tools: list,
            result: str
    ):

        # ========= 基础过滤 =========

        if not query:
            return

        if not result or len(result) < 80:
            print("⚠️ 技能过短，跳过学习")
            return

        timestamp = datetime.now().isoformat()

        # ========= 构建 Skill Document =========

        tool_chain = ",".join(tools)

        skill_doc = f"""
            TASK:
            {query}
            TOOLS USED:
            {tool_chain}
            SUCCESSFUL RESPONSE:
            {result[:1200]}
            """

        # ========= 去重（极重要）=========
        exist = self.collection.query(
            query_texts=[query],
            n_results=1
        )

        if exist["documents"]:

            old_doc = exist["documents"][0][0]

            # 相似任务就不重复存
            if query in old_doc:
                print("⚠️ 相似技能已存在，跳过")
                return

        # ========= 写入 =========

        skill_id = f"skill_{timestamp}"

        self.collection.add(
            documents=[skill_doc],
            metadatas=[
                {
                    "query": query,
                    "tools": tool_chain,
                    "timestamp": timestamp
                }
            ],
            ids=[skill_id]
        )
        print("🧠 技能记忆保存成功")

    # =====================================
    # 技能检索
    # =====================================
    def retrieve_related_skills(
            self,
            query: str,
            top_k: int = 3,
            similarity_threshold: float = 1.5
    ) -> str:

        try:

            results = self.collection.query(

                query_texts=[query],

                n_results=top_k,

                include=["documents", "distances"]

            )

            docs = results.get("documents", [[]])[0]
            distances = results.get("distances", [[]])[0]

            if not docs:
                return ""

            selected_docs = []

            # 距离越小越相似
            for doc, dist in zip(docs, distances):

                if dist <= similarity_threshold:

                    selected_docs.append(doc)

            if not selected_docs:
                return ""

            skill_prompt = "\n\n".join(selected_docs)

            print(f"🧠 Skill Recall {len(selected_docs)} 条")

            return f"""
=== Past Successful Skills ===

{skill_prompt}

Use them as reference if relevant.
"""

        except Exception as e:

            print("Skill Retrieve Error:", e)

            return ""

    # =====================================
    # 技能保存
    # =====================================
    def save_skill(
            self,
            query: str,
            tools: list,
            result: str
    ):

        # 防止垃圾技能
        if not tools or len(set(tools)) < 1:
            return

        skill_doc = f"""
            TASK:
            {query}
            
            TOOLS USED:
            {",".join(set(tools))}
            
            SUCCESSFUL RESPONSE SUMMARY:
            {result[:400]}
            """

        try:

            self.collection.add(

                documents=[skill_doc],

                ids=[str(uuid.uuid4())],

                metadatas=[

                    {
                        "task": query,
                        "tools": ",".join(set(tools))
                    }

                ]

            )

            print("✅ Skill Stored.")

        except Exception as e:

            print("Skill Save Error:", e)