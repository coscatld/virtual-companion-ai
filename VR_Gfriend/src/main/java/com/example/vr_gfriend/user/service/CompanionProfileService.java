package com.example.vr_gfriend.user.service;

import com.example.vr_gfriend.user.entity.UserAIProfile;
import com.example.vr_gfriend.user.mapper.UserAIProfileMapper;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.Arrays;
import java.util.List;
import java.util.stream.StreamSupport;

@Service
@RequiredArgsConstructor
public class CompanionProfileService {
    public static final String DEFAULT_COMPANION_ID = "default";
    private static final String DEFAULT_PROMPT = "你是一个友善、可靠的个人 AI 伴侣。";
    private final UserAIProfileMapper mapper;
    private final ObjectMapper objectMapper;

    public UserAIProfile findProfile(String userId) {
        return mapper.selectByUserId(userId);
    }

    public InternalCompanion internalCompanion(String userId) {
        UserAIProfile profile = findProfile(userId);
        return new InternalCompanion(userId, DEFAULT_COMPANION_ID,
                profile == null ? DEFAULT_PROMPT : buildSystemPrompt(profile),
                profile == null ? null : profile.getVoiceId());
    }

    public CompanionView publicProfile(String userId) {
        UserAIProfile profile = findProfile(userId);
        if (profile == null) {
            return null;
        }
        return new CompanionView(profile.getAiName(), readLabels(profile.getPersonalityTags()),
                readLabels(profile.getInterests()));
    }

    private String buildSystemPrompt(UserAIProfile profile) {
        return "你现在的角色是：" + profile.getAiName() + "。\n"
                + "你的性格是：" + String.join("、", readLabels(profile.getPersonalityTags())) + "。\n"
                + "你的任务介绍是：" + profile.getSystemPrompt() + "\n"
                + "请保持这个设定进行对话。\n\n";
    }

    private List<String> readLabels(String stored) {
        if (stored == null || stored.isBlank()) {
            return List.of();
        }
        try {
            JsonNode node = objectMapper.readTree(stored);
            if (node.isArray()) {
                return StreamSupport.stream(node.spliterator(), false)
                        .filter(JsonNode::isTextual).map(JsonNode::asText).toList();
            }
            if (node.isTextual()) {
                stored = node.asText();
            } else if (node.isNull()) {
                return List.of();
            }
        } catch (JsonProcessingException ignored) {
            // Older profiles stored comma-separated fields without JSON quoting.
        }
        return Arrays.stream(stored.split("[,，、]")).map(String::strip).filter(label -> !label.isEmpty()).toList();
    }

    public record CompanionView(String name, List<String> tags, List<String> interests) {}

    public record InternalCompanion(String userId, String companionId, String systemPrompt, String voiceId) {}
}
