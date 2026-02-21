package com.example.vr_gfriend.common.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.codec.protobuf.ProtobufDecoder;
import org.springframework.http.codec.protobuf.ProtobufEncoder;
import org.springframework.messaging.rsocket.RSocketStrategies;

@Configuration
public class RSocketConfig {
    @Bean
    public RSocketStrategies rSocketStrategies() {
        return RSocketStrategies.builder()
                .encoders(encoders -> encoders.add(new ProtobufEncoder())) // 必须加：允许发送 Protobuf
                .decoders(decoders -> decoders.add(new ProtobufDecoder())) // 必须加：允许接收 Protobuf
                .build();
    }
}
