package com.example.vr_gfriend.Audio;

import com.example.vr_gfriend.common.Interceptor.AudioHandshakeInterceptor;
import com.example.vr_gfriend.common.proto.AgentProto;
import com.example.vr_gfriend.agent.AgentClientService;
import com.example.vr_gfriend.agent.InferenceQuota;
import com.example.vr_gfriend.user.service.CompanionProfileService;
import com.example.vr_gfriend.user.service.CompanionProfileService.InternalCompanion;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.protobuf.ByteString;
import io.grpc.Context;
import io.grpc.stub.StreamObserver;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.http.HttpStatus;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.socket.*;
import org.springframework.web.socket.handler.BinaryWebSocketHandler;
import org.springframework.web.socket.handler.ConcurrentWebSocketSessionDecorator;

import java.io.IOException;
import java.util.List;
import java.util.Map;

@Slf4j
@Component
@RequiredArgsConstructor
public class CompanionAudioHandler extends BinaryWebSocketHandler implements SubProtocolCapable {
    private static final String CONNECTION = CompanionAudioHandler.class.getName();
    private static final int MAX_FRAME_BYTES = 256 * 1024;
    private static final int MAX_TURN_BYTES = 8 * 1024 * 1024;

    private final AgentClientService agent;
    private final CompanionProfileService profiles;
    private final ObjectMapper json;
    private final InferenceQuota quota;

    @Override
    public List<String> getSubProtocols() {
        return List.of(AudioHandshakeInterceptor.SUBPROTOCOL);
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws IOException {
        session.setBinaryMessageSizeLimit(MAX_FRAME_BYTES);
        String userId = (String) session.getAttributes().get(AudioHandshakeInterceptor.USER_ID);
        if (userId == null) {
            session.close(CloseStatus.POLICY_VIOLATION);
            return;
        }

        Connection connection = new Connection(session, profiles.internalCompanion(userId));
        session.getAttributes().put(CONNECTION, connection);
        connection.start();
    }

    @Override
    protected void handleBinaryMessage(WebSocketSession session, BinaryMessage message) throws IOException {
        Connection connection = (Connection) session.getAttributes().get(CONNECTION);
        if (connection != null) {
            connection.sendToAgent(message);
        }
    }

    @Override
    public void handleTransportError(WebSocketSession session, Throwable error) throws IOException {
        release(session);
        if (session.isOpen()) {
            session.close(CloseStatus.SERVER_ERROR);
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) {
        release(session);
    }

    private static void release(WebSocketSession session) {
        Connection connection = (Connection) session.getAttributes().remove(CONNECTION);
        if (connection != null) {
            connection.rpc.close();
        }
    }

    private final class Connection implements StreamObserver<AgentProto.AudioResponse> {
        private final WebSocketSession socket;
        private final InternalCompanion companion;
        private final Context.CancellableContext rpc = Context.current().withCancellation();
        private StreamObserver<AgentProto.AudioRequest> requestStream;
        private int turnSize;
        private boolean responding;

        private Connection(WebSocketSession socket, InternalCompanion companion) {
            this.socket = new ConcurrentWebSocketSessionDecorator(socket, 10_000, MAX_TURN_BYTES + MAX_FRAME_BYTES);
            this.companion = companion;
        }

        private void start() {
            rpc.run(() -> requestStream = agent.streamAudio(this));
        }

        private synchronized void sendToAgent(BinaryMessage message) throws IOException {
            if (rpc.isCancelled()) {
                return;
            }
            if (responding) {
                return;
            }
            int length = message.getPayloadLength();
            if (length > MAX_FRAME_BYTES || turnSize + length > MAX_TURN_BYTES) {
                sendEvent(Map.of("type", "error", "text", "录音超过大小限制。"));
                socket.close(CloseStatus.TOO_BIG_TO_PROCESS);
                return;
            }
            if (length == 0 && turnSize == 0) {
                return;
            }
            if (length == 0) {
                try {
                    quota.claimVoice(companion.userId());
                } catch (ResponseStatusException denied) {
                    sendEvent(Map.of("type", "error", "text", denied.getReason()));
                    close(denied.getStatusCode() == HttpStatus.TOO_MANY_REQUESTS
                            ? CloseStatus.POLICY_VIOLATION : CloseStatus.SERVICE_RESTARTED);
                    return;
                }
            }
            turnSize += length;
            responding = length == 0;

            var request = AgentProto.AudioRequest.newBuilder()
                    .setAudioChunk(ByteString.copyFrom(message.getPayload().asReadOnlyBuffer()))
                    .setSessionId(socket.getId())
                    .setUserId(companion.userId())
                    .setSystemPrompt(companion.systemPrompt())
                    .setCompanionId(companion.companionId());
            if (companion.voiceId() != null) {
                request.setVoiceId(companion.voiceId());
            }
            requestStream.onNext(request.build());
        }

        @Override
        public void onNext(AgentProto.AudioResponse response) {
            try {
                if (!response.getAiText().isEmpty() || !response.getUserText().isEmpty()) {
                    sendEvent(Map.of("type", "transcript", "text", response.getAiText(),
                            "userText", response.getUserText()));
                }
                if (!response.getAiAudioChunk().isEmpty()) {
                    String contentType = response.getAudioContentType().isEmpty() ? "audio/wav" : response.getAudioContentType();
                    sendEvent(Map.of("type", "audio", "contentType", contentType));
                    socket.sendMessage(new BinaryMessage(response.getAiAudioChunk().asReadOnlyByteBuffer()));
                }
                if (!response.getError().isEmpty()) {
                    sendEvent(Map.of("type", "error", "text", voiceErrorMessage(response.getError())));
                }
                if (response.getIsEnd()) {
                    finishTurn();
                }
            } catch (IOException | RuntimeException error) {
                close(CloseStatus.SERVER_ERROR);
            }
        }

        private synchronized void finishTurn() throws IOException {
            turnSize = 0;
            responding = false;
            sendEvent(Map.of("type", "done"));
        }

        @Override
        public void onError(Throwable error) {
            if (rpc.isCancelled()) {
                return;
            }
            log.warn("Audio agent stream failed", error);
            try {
                sendEvent(Map.of("type", "error", "text", "语音服务暂时不可用，请稍后再试。"));
            } catch (IOException | RuntimeException sendError) {
                log.debug("Audio WebSocket closed before the error could be delivered", sendError);
            } finally {
                close(CloseStatus.SERVER_ERROR);
            }
        }

        @Override
        public void onCompleted() {
            close(CloseStatus.NORMAL);
        }

        private void sendEvent(Map<String, String> event) throws IOException {
            if (socket.isOpen()) {
                socket.sendMessage(new TextMessage(json.writeValueAsString(event)));
            }
        }

        private void close(CloseStatus status) {
            rpc.close();
            try {
                if (socket.isOpen()) {
                    socket.close(status);
                }
            } catch (IOException error) {
                log.debug("Unable to close audio WebSocket", error);
            }
        }
    }

    private static String voiceErrorMessage(String code) {
        return switch (code) {
            case "audio_too_large" -> "录音超过大小限制。";
            case "invalid_audio" -> "录音格式无效，请重新录制。";
            case "voice_disabled" -> "语音服务尚未配置。";
            case "speech_not_recognized" -> "没有识别到可转写的语音，请再试一次。";
            case "recognition_unavailable" -> "语音识别暂时不可用。";
            case "synthesis_unavailable", "audio_reply_too_large" -> "语音回复暂时无法播放。";
            default -> "语音服务暂时不可用，请稍后再试。";
        };
    }
}
