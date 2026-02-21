package com.example.vr_gfriend.Scheduler.service;

import com.example.vr_gfriend.Scheduler.DTO.UserAlarmProfileDTO;
import com.example.vr_gfriend.common.Interceptor.UserContext;
import com.example.vr_gfriend.common.method.methods;
import com.example.vr_gfriend.common.proto.AgentProto;
import com.example.vr_gfriend.rsocket.AgentClientService;
import com.example.vr_gfriend.user.entity.UserAIProfile;
import com.example.vr_gfriend.user.mapper.UserAIProfileMapper;
import com.example.vr_gfriend.websocket.NotificationService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import lombok.extern.slf4j.Slf4j;

/**
 * 负责查人设、拼 Prompt、调 RSocket、推 WebSocket。
 */
@Slf4j
@Service
public class DailyBriefingService {
    @Autowired
    private AgentClientService client;
    @Autowired
    private UserAIProfileMapper userAIProfileMapper;
    @Autowired
    private methods methods;
    @Autowired
    private NotificationService notificationService;

    /**
     * 测试接口
     * @param userId
     * @return
     */
    public Flux<String> generateDailyBriefing(String userId) {
        // 1. 获取用户 AI 配置
        UserAIProfile profile = userAIProfileMapper.selectByUserId(userId);
        if (profile == null) {
            return Flux.error(new RuntimeException("未找到用户配置"));
        }

        // 2. 构建 Prompt
        String systemPrompt = methods.buildSystemPrompt(profile).toString();

        // 3. 构建简单的触发消息
        String triggerMessage = String.format("我是%s。请给我一份今天的早报。", userId);
        AgentProto.ChatRequest request = methods.callAgent(userId, systemPrompt, triggerMessage);

        // 2. 在这里执行真正的 RSocket 请求
        return client.streamChat(String.valueOf(request))
                .map(AgentProto.ChatResponse::getDelta);
    }

    /**
     * 设定闹钟
     * @param dto
     */
    public void triggerCustomBriefing(UserAlarmProfileDTO dto) {
        String userId = UserContext.getUserId();

        //prompt：促使Agent使用工具
        String triggerMessage = String.format(
                "我是%s。现在是早报时间！\n" +
                        "1. 我现在的城市是：%s，请查一下天气和新闻。\n" +
                        "2. 我的工作安排在文件：%s 中，请使用【read_local_file】工具读取它，并总结我今天的待办事项。\n" +
                        "3. 综合以上信息，给我一份元气满满的早报！",
                userId,
                dto.getCity(),
                dto.getScheduleFilePath() // <--- 注入文件路径
        );
        //拼接画像
        UserAIProfile profile =userAIProfileMapper.selectByUserId(userId);
        methods.buildSystemPrompt(profile);
        // 获取人设
        String systemPrompt = methods.buildSystemPrompt(profile).toString();

        // 发送请求给 Python
        AgentProto.ChatRequest request = methods.callAgent(userId,systemPrompt,triggerMessage);

        client.streamChat(String.valueOf(request))
                .map(AgentProto.ChatResponse::getDelta)
                .reduce(new StringBuilder(), StringBuilder::append)
                .subscribe(
                        fullContent -> {
                            log.info("✅ 早报生成完毕，准备推送:\n{}", fullContent);
                            notificationService.push(userId, fullContent.toString());
                        },
                        error -> log.error("❌ 早报生成失败", error)
                );
    }
}
