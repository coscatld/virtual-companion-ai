package com.example.vr_gfriend.websocket;

public interface NotificationService {
    /**
     * 推送消息给指定用户
     * @param userId 用户ID
     * @param content 推送内容
     */
    void push(String userId, String content);
}
