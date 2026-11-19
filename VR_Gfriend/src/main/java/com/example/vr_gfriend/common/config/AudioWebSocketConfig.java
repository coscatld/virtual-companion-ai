package com.example.vr_gfriend.common.config;

import com.example.vr_gfriend.Audio.CompanionAudioHandler;
import com.example.vr_gfriend.common.Interceptor.AudioHandshakeInterceptor;
import com.example.vr_gfriend.websocket.WebSocketNotificationImpl;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

@Configuration
@EnableWebSocket
public class AudioWebSocketConfig implements WebSocketConfigurer {
    private final CompanionAudioHandler audio;
    private final WebSocketNotificationImpl notifications;
    private final AudioHandshakeInterceptor authentication;
    private final String[] allowedOrigins;

    public AudioWebSocketConfig(CompanionAudioHandler audio, WebSocketNotificationImpl notifications,
                                AudioHandshakeInterceptor authentication,
                                @Value("${ga.web.allowed-origins}") String[] allowedOrigins) {
        this.audio = audio;
        this.notifications = notifications;
        this.authentication = authentication;
        this.allowedOrigins = allowedOrigins;
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(audio, "/audio")
                .setAllowedOrigins(allowedOrigins)
                .addInterceptors(authentication);
        registry.addHandler(notifications, "/ws/briefing")
                .setAllowedOrigins(allowedOrigins)
                .addInterceptors(authentication);
    }
}
