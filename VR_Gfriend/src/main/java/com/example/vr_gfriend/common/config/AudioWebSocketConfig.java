package com.example.vr_gfriend.common.config;

import com.example.vr_gfriend.Audio.CompanionAudioHandler;
import com.example.vr_gfriend.common.Interceptor.AudioHandshakeInterceptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;

/**
 * 注册 /audio 专属通道。
 */
@Configuration
@EnableWebSocket
public class AudioWebSocketConfig implements WebSocketConfigurer {

    @Autowired
    private CompanionAudioHandler companionAudioHandler;

    @Autowired
    private AudioHandshakeInterceptor audioHandshakeInterceptor;

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(companionAudioHandler, "/audio")
                .setAllowedOrigins("*")
                .addInterceptors(audioHandshakeInterceptor);
    }
}
