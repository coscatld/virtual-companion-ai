package com.example.vr_gfriend.Vector;

import org.springframework.stereotype.Service;
import java.util.List;
import java.util.ArrayList;

@Service
public class VectorStoreService {
    
    /**
     * TODO: 引入真实的 Spring AI VectorStore 或者 MilvusClient
     * 这里使用 Mock 返回来占位，演示在不阻断主流程的情况下调取出 RAG 召回集
     * 
     * @param userId 哪个用户的回忆
     * @param query 当前聊天的句子，用于向量检索最相似的过去记忆
     * @param topK 获取几条回忆
     */
    public List<String> searchSimilarMemories(String userId, String query, int topK) {
        List<String> memories = new ArrayList<>();
        
        // 此处应包含: 
        // 1. 调用 Embedding 模型把 query 变成 List<Float>
        // 2. 将向量在 Chroma/Milvus 库中利用 cosine 距离查找这个 userId 下的数据
        // 3. 返回回忆的 Text
        
        System.out.println("🔍 [VectorDB] 正在为用户 " + userId + " 检索关于 '" + query + "' 的长段记忆...");
        
        // 假数据：演示触发机制
        if(query.contains("日本") || query.contains("旅游")) {
            memories.add("2024年3月：用户提到过想在签证过期前去大阪看海游馆。");
        } else if (query.contains("猫") || query.contains("狗")) {
            memories.add("2023年底：提及过自己养了一只叫‘布丁’的布偶猫。");
        }
        
        return memories;
    }
}
