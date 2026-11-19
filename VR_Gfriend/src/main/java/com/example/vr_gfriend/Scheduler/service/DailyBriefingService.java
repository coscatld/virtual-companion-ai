package com.example.vr_gfriend.Scheduler.service;

import com.example.vr_gfriend.Scheduler.DTO.UserAlarmProfileDTO;
import com.example.vr_gfriend.common.proto.AgentProto;
import com.example.vr_gfriend.agent.AgentClientService;
import com.example.vr_gfriend.websocket.NotificationService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.scheduler.Schedulers;

import java.time.Duration;
import java.time.Instant;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Service
@RequiredArgsConstructor
public class DailyBriefingService {
    private final AgentClientService client;
    private final NotificationService notifications;
    private final JdbcTemplate jdbc;
    private final Set<String> inProgress = ConcurrentHashMap.newKeySet();

    public Flux<String> generateDailyBriefing(String userId, UserAlarmProfileDTO settings) {
        String city = settings == null ? null : settings.getCity();
        String cityContext = city == null || city.isBlank() ? "" : "用户所在城市：" + city + "。";
        String task = "请生成一份简洁的每日早报。" + cityContext
                + "结合可核实的天气和时事，给出今天可执行的建议。请清楚标注无法核实的实时信息。";
        return client.streamChat(userId, task, true)
                .timeout(Duration.ofSeconds(60))
                .map(AgentProto.ChatResponse::getDelta)
                .filter(text -> !text.isEmpty());
    }

    public Briefing latest(String userId) {
        return jdbc.query("SELECT content, generated_at_ms FROM user_briefing WHERE user_id = ?",
                (row, index) -> new Briefing(row.getString("content"),
                        Instant.ofEpochMilli(row.getLong("generated_at_ms"))), userId)
                .stream().findFirst().orElse(null);
    }

    public void triggerCustomBriefing(UserAlarmProfileDTO settings) {
        String userId = settings.getUserId();
        if (!inProgress.add(userId)) {
            return;
        }
        generateDailyBriefing(userId, settings)
                .reduceWith(StringBuilder::new, StringBuilder::append)
                .filter(content -> !content.isEmpty())
                .publishOn(Schedulers.boundedElastic())
                .doOnNext(content -> {
                    String text = content.toString();
                    long generatedAt = Instant.now().toEpochMilli();
                    jdbc.update("""
                            INSERT INTO user_briefing (user_id, content, generated_at_ms) VALUES (?, ?, ?)
                            ON DUPLICATE KEY UPDATE content = VALUES(content), generated_at_ms = VALUES(generated_at_ms)
                            """, userId, text, generatedAt);
                    notifications.push(userId, text, Instant.ofEpochMilli(generatedAt));
                })
                .doFinally(signal -> inProgress.remove(userId))
                .subscribe(content -> {}, error -> log.warn("Scheduled briefing generation failed", error));
    }

    public record Briefing(String text, Instant generatedAt) {}
}
