package com.example.vr_gfriend.agent;

import com.example.vr_gfriend.common.Interceptor.UserContext;
import com.example.vr_gfriend.common.config.Result;
import com.example.vr_gfriend.common.proto.AgentProto;
import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.List;

@Slf4j
@RestController
@RequestMapping("/api/chat")
@RequiredArgsConstructor
public class ChatController {
    private final AgentClientService agent;
    private final InferenceQuota quota;

    @GetMapping("/history")
    public Mono<Result<List<HistoryTurn>>> history() {
        return agent.recentHistory(UserContext.getUserId())
                .map(messages -> Result.success(messages.stream()
                        .map(message -> new HistoryTurn(message.getRole(), message.getContent()))
                        .toList()))
                .onErrorMap(error -> {
                    log.warn("Chat history unavailable", error);
                    return new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "对话历史暂时不可用");
                });
    }

    @PostMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> chat(@Valid @RequestBody ChatInput input) {
        return stream(input.message(), "done", "ok");
    }

    @GetMapping(value = "/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> legacyChat(@RequestParam String msg) {
        if (msg.isBlank() || msg.length() > 12000) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请输入 1 至 12000 个字符");
        }
        return stream(msg, "message", "\n[END]");
    }

    private Flux<ServerSentEvent<String>> stream(String message, String finalEvent, String finalData) {
        String userId = UserContext.getUserId();
        quota.claimText(userId);
        return agent.streamChat(userId, message)
                .timeout(Duration.ofSeconds(60))
                .map(AgentProto.ChatResponse::getDelta)
                .filter(delta -> !delta.isEmpty())
                .map(delta -> event("message", delta))
                .concatWithValues(event(finalEvent, finalData))
                .onErrorResume(error -> {
                    log.warn("Chat agent stream failed", error);
                    return Flux.just(event("error", "AI 服务暂时不可用，请稍后再试。"));
                });
    }

    private static ServerSentEvent<String> event(String name, String data) {
        return ServerSentEvent.builder(data.replace("\r\n", "\n").replace('\r', '\n')).event(name).build();
    }

    public record ChatInput(@NotBlank(message = "请输入消息") @Size(max = 12000) String message) {}

    public record HistoryTurn(String role, String content) {}
}
