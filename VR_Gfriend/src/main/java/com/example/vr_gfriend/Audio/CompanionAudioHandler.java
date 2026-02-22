package com.example.vr_gfriend.Audio;

import com.example.vr_gfriend.common.proto.AgentProto;
import com.example.vr_gfriend.common.proto.AudioServiceGrpc;
import io.grpc.stub.StreamObserver;
import org.springframework.web.socket.BinaryMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.handler.BinaryWebSocketHandler;

import java.nio.ByteBuffer;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import lombok.extern.slf4j.Slf4j;
import net.devh.boot.grpc.client.inject.GrpcClient;
import com.example.vr_gfriend.user.entity.UserAIProfile;
import com.example.vr_gfriend.user.mapper.UserAIProfileMapper;
import com.example.vr_gfriend.common.method.methods;

@Slf4j
@Component
public class CompanionAudioHandler extends BinaryWebSocketHandler {

    @GrpcClient("agentService")
    private AudioServiceGrpc.AudioServiceStub asyncStub;//连接GAgent的客户端

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;
    @Autowired
    private UserAIProfileMapper userAIProfileMapper;
    @Autowired
    private methods methods;

    // 维护每个 WebSocket 会话对应的 gRPC 请求流
    private final ConcurrentHashMap<String, StreamObserver<AgentProto.AudioRequest>> grpcStreams = new ConcurrentHashMap<>();

    // 可以在此保留空构造由于自动注入
    public CompanionAudioHandler() {
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) {
        String userId = (String) session.getAttributes().get("userId");
        if(userId == null) userId = "Anonymous";
        
        // Fetch System Prompt,调取用户的个性化配置
        String PROFILE_CACHE_KEY = "vr:profile:";
        UserAIProfile profile = (UserAIProfile) redisTemplate.opsForValue().get(PROFILE_CACHE_KEY + userId);
        if (profile == null) {
            profile = userAIProfileMapper.selectByUserId(userId);
            if (profile != null) {
                redisTemplate.opsForValue().set(PROFILE_CACHE_KEY + userId, profile, 3600, java.util.concurrent.TimeUnit.SECONDS);
            }
        }
        String pureSystemPrompt = profile != null ? methods.buildSystemPrompt(profile).toString() : "You are a helpful AI assistant.";
        
        // 直接将提示信息保存到会话属性中，以便稍后进行数据块组装
        session.getAttributes().put("systemPrompt", pureSystemPrompt);

        log.info("Audio WebSocket Connection Established for User: {}", userId);
        
        // 1. 当 Vue3 连上 Java 时，Java 立即向 Python 发起一个 gRPC 流式请求
        StreamObserver<AgentProto.AudioResponse> responseObserver = new StreamObserver<AgentProto.AudioResponse>() {
            @Override
            public void onNext(AgentProto.AudioResponse response) {
                // Python 返回了 AI 的声音！将它推回给 Vue3
                try {
                    ByteBuffer buffer = ByteBuffer.wrap(response.getAiAudioChunk().toByteArray());
                    session.sendMessage(new BinaryMessage(buffer));
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
            @Override
            public void onError(Throwable t) {}
            @Override
            public void onCompleted() {}
        };

        // 创建发往 Python 的数据流，并保存起来
        StreamObserver<AgentProto.AudioRequest> requestObserver = asyncStub.streamAudioChat(responseObserver);
        grpcStreams.put(session.getId(), requestObserver);
    }

    @Override
    protected void handleBinaryMessage(WebSocketSession session, BinaryMessage message) {
        // 2. 核心透传逻辑：Vue3 发来了一段 500ms 的录音碎片
        ByteBuffer byteBuffer = message.getPayload();
        byte[] audioBytes = new byte[byteBuffer.remaining()];
        byteBuffer.get(audioBytes);

        if (audioBytes.length == 0) {
            // 构造一个携带空字节的 request 发给 Python 即可，让 Python 去判断截断
            AgentProto.AudioRequest eofRequest = AgentProto.AudioRequest.newBuilder()
                    .setAudioChunk(com.google.protobuf.ByteString.EMPTY)
                    .setSessionId(session.getId())
                    .build();
            StreamObserver<AgentProto.AudioRequest> requestObserver = grpcStreams.get(session.getId());
            if (requestObserver != null) {
                requestObserver.onNext(eofRequest); // 不要调用 onCompleted()!
            }
            return;
        }

        String userId = (String) session.getAttributes().get("userId");
        if(userId == null) userId = "Anonymous";
        
        String systemPrompt = (String) session.getAttributes().get("systemPrompt");
        if(systemPrompt == null) systemPrompt = "You are a helpful AI assistant.";

        // 打包成 gRPC 对象
        AgentProto.AudioRequest request = AgentProto.AudioRequest.newBuilder()
                .setAudioChunk(com.google.protobuf.ByteString.copyFrom(audioBytes))
                .setSessionId(session.getId())
                .setUserId(userId)
                .setSystemPrompt(systemPrompt)
                .build();

        // 3. 直接通过之前建立好的通道，推给 Python 中台
        StreamObserver<AgentProto.AudioRequest> requestObserver = grpcStreams.get(session.getId());
        if (requestObserver != null) {
            requestObserver.onNext(request);
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, org.springframework.web.socket.CloseStatus status) {
        // 4. 用户挂断，通知 Python 结束推理
        StreamObserver<AgentProto.AudioRequest> requestObserver = grpcStreams.remove(session.getId());
        if (requestObserver != null) {
            requestObserver.onCompleted();
        }
    }
}
