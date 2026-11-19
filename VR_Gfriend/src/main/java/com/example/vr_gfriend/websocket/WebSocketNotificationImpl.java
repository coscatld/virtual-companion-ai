package com.example.vr_gfriend.websocket;

import com.example.vr_gfriend.common.Interceptor.AudioHandshakeInterceptor;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.*;
import org.springframework.web.socket.handler.ConcurrentWebSocketSessionDecorator;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
@RequiredArgsConstructor
public class WebSocketNotificationImpl extends TextWebSocketHandler implements NotificationService, SubProtocolCapable {
    private final ObjectMapper json;
    private final Map<String, Map<String, WebSocketSession>> users = new ConcurrentHashMap<>();

    @Override
    public List<String> getSubProtocols() {
        return List.of(AudioHandshakeInterceptor.SUBPROTOCOL);
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws IOException {
        String userId = (String) session.getAttributes().get(AudioHandshakeInterceptor.USER_ID);
        if (userId == null) {
            session.close(CloseStatus.POLICY_VIOLATION);
            return;
        }
        users.compute(userId, (id, sessions) -> {
            if (sessions == null) {
                sessions = new ConcurrentHashMap<>();
            }
            sessions.put(session.getId(), new ConcurrentWebSocketSessionDecorator(session, 10_000, 256 * 1024));
            return sessions;
        });
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        String userId = (String) session.getAttributes().get(AudioHandshakeInterceptor.USER_ID);
        if (userId != null) {
            users.computeIfPresent(userId, (id, sessions) -> {
                sessions.remove(session.getId());
                return sessions.isEmpty() ? null : sessions;
            });
        }
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable error) throws IOException {
        if (session.isOpen()) {
            session.close(CloseStatus.SERVER_ERROR);
        }
    }

    @Override
    public void push(String userId, String content, Instant generatedAt) {
        Map<String, WebSocketSession> sessions = users.get(userId);
        if (sessions == null || sessions.isEmpty()) {
            return;
        }
        try {
            TextMessage message = new TextMessage(json.writeValueAsString(
                    Map.of("type", "briefing", "text", content, "generatedAt", generatedAt.toString())));
            sessions.values().forEach(session -> send(session, message));
        } catch (IOException error) {
            log.warn("Unable to encode briefing notification", error);
        }
    }

    private void send(WebSocketSession session, TextMessage message) {
        try {
            if (session.isOpen()) {
                session.sendMessage(message);
            }
        } catch (IOException | RuntimeException error) {
            log.debug("Unable to send scheduled briefing to a WebSocket session", error);
            afterConnectionClosed(session, CloseStatus.SERVER_ERROR);
            try {
                session.close(CloseStatus.SERVER_ERROR);
            } catch (IOException closeError) {
                log.debug("Unable to close notification WebSocket", closeError);
            }
        }
    }
}
