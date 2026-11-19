package com.example.vr_gfriend.websocket;

import java.time.Instant;

public interface NotificationService {
    void push(String userId, String content, Instant generatedAt);
}
