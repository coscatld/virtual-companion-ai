package com.example.vr_gfriend.agent;

import com.example.vr_gfriend.common.proto.AgentProto;
import com.example.vr_gfriend.common.proto.AgentServiceGrpc;
import com.example.vr_gfriend.common.proto.AudioServiceGrpc;
import com.example.vr_gfriend.user.service.CompanionProfileService;
import com.example.vr_gfriend.user.service.CompanionProfileService.InternalCompanion;
import io.grpc.Context;
import io.grpc.Metadata;
import io.grpc.stub.MetadataUtils;
import io.grpc.stub.StreamObserver;
import net.devh.boot.grpc.client.inject.GrpcClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

import java.util.concurrent.TimeUnit;
import java.util.List;

@Service
public class AgentClientService {
    @GrpcClient("agentService")
    private AgentServiceGrpc.AgentServiceStub chatStub;
    @GrpcClient("agentService")
    private AgentServiceGrpc.AgentServiceBlockingStub historyStub;
    @GrpcClient("agentService")
    private AudioServiceGrpc.AudioServiceStub audioStub;
    private final Metadata credentials = new Metadata();
    private final CompanionProfileService profiles;

    public AgentClientService(CompanionProfileService profiles, @Value("${ga.internal-token}") String serviceToken) {
        this.profiles = profiles;
        if (!serviceToken.isBlank()) {
            credentials.put(Metadata.Key.of("x-ga-internal-token", Metadata.ASCII_STRING_MARSHALLER), serviceToken);
        }
    }

    public Flux<AgentProto.ChatResponse> streamChat(String userId, String message) {
        return streamChat(userId, message, false);
    }

    public Flux<AgentProto.ChatResponse> streamChat(String userId, String message, boolean skipMemoryWrite) {
        return Mono.fromCallable(() -> profiles.internalCompanion(userId))
                .subscribeOn(Schedulers.boundedElastic())
                .flatMapMany(companion -> streamChat(AgentProto.ChatRequest.newBuilder()
                        .setUserId(userId)
                        .setCompanionId(companion.companionId())
                        .setSystemPrompt(companion.systemPrompt())
                        .setUserMessage(message)
                        .setSkipMemoryWrite(skipMemoryWrite)
                        .build()));
    }

    private Flux<AgentProto.ChatResponse> streamChat(AgentProto.ChatRequest request) {
        return Flux.create(sink -> {
            Context.CancellableContext call = Context.current().withCancellation();
            sink.onDispose(call::close);
            call.run(() -> chatStub.withInterceptors(MetadataUtils.newAttachHeadersInterceptor(credentials))
                    .withDeadlineAfter(120, TimeUnit.SECONDS)
                    .chatStream(request, new StreamObserver<>() {
                        private boolean receivedEnd;

                        @Override
                        public void onNext(AgentProto.ChatResponse response) {
                            if ("error".equals(response.getEmotion())) {
                                sink.error(new IllegalStateException("Agent returned an error frame"));
                                return;
                            }
                            if (receivedEnd) {
                                sink.error(new IllegalStateException("Agent sent a frame after the end of the turn"));
                                return;
                            }
                            receivedEnd = response.getIsEnd();
                            sink.next(response);
                        }

                        @Override
                        public void onError(Throwable error) {
                            sink.error(error);
                        }

                        @Override
                        public void onCompleted() {
                            if (receivedEnd) {
                                sink.complete();
                            } else {
                                sink.error(new IllegalStateException("Agent ended the stream before completing the turn"));
                            }
                        }
                    }));
        });
    }

    public Mono<List<AgentProto.HistoryMessage>> recentHistory(String userId) {
        AgentProto.RecentTurnsRequest request = AgentProto.RecentTurnsRequest.newBuilder()
                .setUserId(userId)
                .setCompanionId(CompanionProfileService.DEFAULT_COMPANION_ID)
                .build();
        return Mono.fromCallable(() -> historyStub.withInterceptors(MetadataUtils.newAttachHeadersInterceptor(credentials))
                        .withDeadlineAfter(10, TimeUnit.SECONDS)
                        .getRecentTurns(request)
                        .getMessagesList())
                .subscribeOn(Schedulers.boundedElastic());
    }

    public StreamObserver<AgentProto.AudioRequest> streamAudio(StreamObserver<AgentProto.AudioResponse> observer) {
        return audioStub.withInterceptors(MetadataUtils.newAttachHeadersInterceptor(credentials))
                .streamAudioChat(observer);
    }
}
