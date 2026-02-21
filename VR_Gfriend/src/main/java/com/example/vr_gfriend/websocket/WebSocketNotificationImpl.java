package com.example.vr_gfriend.websocket;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

@Slf4j
@Service
public class WebSocketNotificationImpl implements NotificationService {

    @Autowired
    private SimpMessagingTemplate messagingTemplate;

    @Override
    public void push(String userId, String content) {
        // 推送路径：/user/{userId}/queue/briefing
        // 前端需订阅：/user/queue/briefing
        messagingTemplate.convertAndSendToUser(
                userId,
                "/queue/briefing",
                content
        );
        log.info("🚀 WebSocket 推送成功 -> 用户: {}", userId);
    }
}
