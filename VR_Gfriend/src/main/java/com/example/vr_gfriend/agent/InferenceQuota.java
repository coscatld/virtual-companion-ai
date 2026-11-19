package com.example.vr_gfriend.agent;

import io.lettuce.core.ClientOptions;
import io.lettuce.core.RedisClient;
import io.lettuce.core.RedisConnectionException;
import io.lettuce.core.RedisException;
import io.lettuce.core.RedisURI;
import io.lettuce.core.ScriptOutputType;
import io.lettuce.core.SocketOptions;
import io.lettuce.core.api.StatefulRedisConnection;
import jakarta.annotation.PreDestroy;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.Duration;

@Service
public class InferenceQuota {
    private static final String KEY_PREFIX = "ga:enterprise:inference:";
    private static final Duration REDIS_TIMEOUT = Duration.ofSeconds(2);
    private static final String CLAIM_WINDOW = """
            local count = redis.call('GET', KEYS[1])
            if not count then
                redis.call('SET', KEYS[1], 1, 'PX', 60000)
                return 0
            end
            if tonumber(count) >= tonumber(ARGV[1]) then
                return math.max(redis.call('PTTL', KEYS[1]), 1)
            end
            redis.call('INCR', KEYS[1])
            return 0
            """;

    private final RedisClient client;
    private final int textLimit;
    private final int voiceLimit;
    private volatile StatefulRedisConnection<String, String> connection;
    private long nextConnectAttempt;

    public InferenceQuota(@Value("${ga.enterprise.redis-url}") String redisUrl,
                          @Value("${ga.enterprise.text-requests-per-minute}") int textLimit,
                          @Value("${ga.enterprise.voice-turns-per-minute}") int voiceLimit) {
        this.textLimit = textLimit;
        this.voiceLimit = voiceLimit;
        if (redisUrl.isBlank()) {
            client = null;
            return;
        }
        if (textLimit < 1 || voiceLimit < 1) {
            throw new IllegalArgumentException("Enterprise inference quotas must be positive");
        }
        RedisURI uri = RedisURI.create(redisUrl);
        uri.setTimeout(REDIS_TIMEOUT);
        client = RedisClient.create(uri);
        client.setOptions(ClientOptions.builder()
                .socketOptions(SocketOptions.builder().connectTimeout(REDIS_TIMEOUT).build())
                .disconnectedBehavior(ClientOptions.DisconnectedBehavior.REJECT_COMMANDS)
                .build());
    }

    public void claimText(String userId) {
        claim("text", userId, textLimit, "对话和早报预览请求过于频繁，请稍后再试。");
    }

    public void claimVoice(String userId) {
        claim("voice", userId, voiceLimit, "语音请求过于频繁，请稍后再试。");
    }

    private void claim(String kind, String userId, int limit, String message) {
        if (client == null) {
            return;
        }
        String key = KEY_PREFIX + kind + ":" + userId;
        long retryAfterMillis;
        try {
            retryAfterMillis = connection().sync().eval(CLAIM_WINDOW, ScriptOutputType.INTEGER,
                    new String[]{key}, Integer.toString(limit));
        } catch (RedisException error) {
            throw new ResponseStatusException(HttpStatus.SERVICE_UNAVAILABLE, "请求额度服务暂时不可用。", error);
        }
        if (retryAfterMillis > 0) {
            throw new LimitExceeded(message, (retryAfterMillis + 999) / 1000);
        }
    }

    private StatefulRedisConnection<String, String> connection() {
        var current = connection;
        if (current == null) {
            synchronized (this) {
                current = connection;
                if (current == null) {
                    if (nextConnectAttempt != 0 && System.nanoTime() - nextConnectAttempt < 0) {
                        throw new RedisConnectionException("Redis connection is temporarily unavailable");
                    }
                    try {
                        current = client.connect();
                        connection = current;
                    } catch (RedisException error) {
                        nextConnectAttempt = System.nanoTime() + REDIS_TIMEOUT.toNanos();
                        throw error;
                    }
                }
            }
        }
        return current;
    }

    @PreDestroy
    void shutdown() {
        if (client != null) {
            client.shutdown();
        }
    }

    private static final class LimitExceeded extends ResponseStatusException {
        private final HttpHeaders headers = new HttpHeaders();

        private LimitExceeded(String message, long retryAfterSeconds) {
            super(HttpStatus.TOO_MANY_REQUESTS, message);
            headers.set(HttpHeaders.RETRY_AFTER, Long.toString(retryAfterSeconds));
        }

        @Override
        public HttpHeaders getHeaders() {
            return headers;
        }
    }
}
