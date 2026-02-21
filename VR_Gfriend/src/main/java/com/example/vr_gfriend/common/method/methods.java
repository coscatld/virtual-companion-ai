package com.example.vr_gfriend.common.method;

import com.example.vr_gfriend.common.proto.AgentProto;
import com.example.vr_gfriend.user.entity.UserAIProfile;
import org.springframework.stereotype.Service;

@Service
public class methods {
    /**
     * 辅助方法：构建人设 Prompt
     */
    public StringBuilder buildSystemPrompt(UserAIProfile profile) {
        StringBuilder prompt = new StringBuilder();
        prompt.append("你现在的角色是：").append(profile.getAiName()).append("。\n");
        prompt.append("你的性格是：").append(profile.getPersonalityTags()).append("。\n");
        prompt.append("你的任务介绍是：").append(profile.getSystemPrompt()).append("\n");
        prompt.append("请保持这个设定进行对话。\n\n");
        return prompt;
    }
    public AgentProto.ChatRequest callAgent(String userId, String systemPrompt, String userMessage) {
        AgentProto.ChatRequest request = AgentProto.ChatRequest.newBuilder()
                .setUserId(userId)
                .setSystemPrompt(systemPrompt)
                .setUserMessage(userMessage)
                .build();
        return request;
    }
    public static long generateUidFromPhone(String phone) {
        // 1. 使用 Java 内置的 hashCode (或者用 MurmurHash 性能更好)
        // 加上一个盐值 Salt 增加随机性，防止被反推
        String salt = "MySecretGame_2026";
        int hash = (phone + salt).hashCode();

        // 2. 取绝对值并映射到 9 位数范围 (100,000,000 - 999,999,999)
        return (Math.abs(hash) % 900000000L) + 100000000L;
    }
}
