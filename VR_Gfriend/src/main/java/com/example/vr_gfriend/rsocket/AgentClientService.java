package com.example.vr_gfriend.rsocket;

import com.example.vr_gfriend.Vector.VectorStoreService;
import com.example.vr_gfriend.common.Interceptor.UserContext;
import com.example.vr_gfriend.common.method.methods;
import com.example.vr_gfriend.user.entity.UserAIProfile;
import com.example.vr_gfriend.user.mapper.UserAIProfileMapper;
import io.grpc.ManagedChannel;
import io.grpc.ManagedChannelBuilder;
import io.grpc.stub.StreamObserver;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.script.DefaultRedisScript;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Service;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;
import reactor.core.scheduler.Schedulers;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.TimeUnit;

import com.example.vr_gfriend.common.proto.AgentProto;
import com.example.vr_gfriend.common.proto.AgentServiceGrpc;

@Slf4j
@Service
public class AgentClientService {

    @Autowired
    private UserAIProfileMapper userAIProfileMapper;
    @Autowired
    private RedisTemplate<String, Object> redisTemplate;
    @Autowired
    private VectorStoreService vectorStoreService;
    @Autowired
    private methods methods;

    private ManagedChannel channel;
    private AgentServiceGrpc.AgentServiceStub asyncStub;

    private static final String PROFILE_CACHE_KEY = "vr:profile:";
    private static final String HISTORY_CACHE_KEY = "vr:history:";
    private static final long EXPIRE_TIME = 3600; // 缓存 1 小时

    // Redis Lua Script 用于保证写入和裁剪的原子性
    // 从 19 (10轮) 缩减到 9 (5轮 QA)，大幅节约 Token 和 Context Window
    private static final String LUA_SCRIPT =
            "redis.call('RPUSH', KEYS[1], ARGV[1]) \n" +
            "redis.call('LTRIM', KEYS[1], -50, -1) \n" +
            "local expireTime = tonumber(ARGV[2]) \n" +
            "if expireTime then \n" +
            "    redis.call('EXPIRE', KEYS[1], math.floor(expireTime)) \n" +
            "end \n" +
            "return 1";

    public AgentClientService() {
        // 创建 gRPC Channel 和 Stub
        this.channel = ManagedChannelBuilder.forAddress("localhost", 7000)
                .usePlaintext() // 不使用 TLS，本地开发
                .build();
        this.asyncStub = AgentServiceGrpc.newStub(channel);
    }

    @PreDestroy
    public void shutdown() {
        if (channel != null && !channel.isShutdown()) {
            channel.shutdown();
        }
    }

    // 流式对话接口 (主入口)
    public Flux<AgentProto.ChatResponse> streamChat(String content) {
        String userId = UserContext.getUserId();
        
        if (userId == null) {
            log.warn("🚨 Authentication failed: userId is null in Request Context. Falling back to anonymous.");
            userId = "Anonymous_User";
        }
        
        final String currentUserId = userId; // 为了 Lambda 里能用

        // Tip：在响应式流 (Flux/Mono) 中，绝对禁止直接在外部主线程调用阻塞 IO
        // 因此我们使用 Mono.fromCallable(把一个“同步阻塞函数”转换成响应式Mono[0 或 1 个结果的异步数据流])把它转移到 Schedulers.boundedElastic(进入处理耗时的I/O线程池)
        // flatMapMany接受单值contextPair，并且不断转化成Flux
        return Mono.fromCallable(() -> buildContext(currentUserId, content))
                .subscribeOn(Schedulers.boundedElastic())
                .flatMapMany(contextPair -> {
                    
                    String pureSystemPrompt = contextPair[0];
                    String userMessageWithHistory = contextPair[1];

                    // 同样，保存用户短期记忆也是 Redis 阻塞操作，异步调度
                    saveShortTermMemory(currentUserId, "User: " + content);

                    // 组装 gRPC 的 Request Protobuf 对象
                    // 必须保证 systemPrompt 绝对纯净（无变化），以便 vLLM 能够命中 Prefix Caching
                    AgentProto.ChatRequest request = AgentProto.ChatRequest.newBuilder()
                            .setUserId(currentUserId)
                            .setSystemPrompt(pureSystemPrompt)
                            .setUserMessage(userMessageWithHistory)
                            .build();

                    // 为了将 gRPC 基于 Observer (Callback) 的接口转为 Reactor (Flux) 的流
                    return Flux.<AgentProto.ChatResponse>create(emitter -> {
                        // 1. 准备一个缓冲区
                        StringBuilder aiReplyBuffer = new StringBuilder();
                        // 2. 定义 gRPC 的接球手 (StreamObserver)
                        StreamObserver<AgentProto.ChatResponse> responseObserver = new StreamObserver<AgentProto.ChatResponse>() {
                            /**
                             * 把gRPC的value，传给WebFlux
                             * @param value
                             */
                            @Override
                            public void onNext(AgentProto.ChatResponse value) {
                                if (value.getDelta() != null && !value.getDelta().isEmpty()) {
                                    aiReplyBuffer.append(value.getDelta());
                                }
                                emitter.next(value);
                            }

                            @Override
                            public void onError(Throwable t) {
                                log.error("❌ gRPC 调用失败", t);
                                emitter.next(AgentProto.ChatResponse.newBuilder()
                                        .setDelta("\n\n(抱歉，后端大脑失去连接...)")
                                        .build());
                                emitter.complete();
                            }

                            @Override
                            public void onCompleted() {
                                // 完整回答结束时，存到 Redis
                                String fullReply = aiReplyBuffer.toString();
                                if (!fullReply.isEmpty()) {
                                    saveShortTermMemory(currentUserId, "AI: " + fullReply);
                                }
                                emitter.complete();
                            }
                        };

                        // 发起真实的 gRPC 请求
                        asyncStub.chatStream(request, responseObserver);

                        // Emitter 取消时的资源释放策略 (前端断开时)
                        emitter.onDispose(() -> {
                            // 可选：取消后端的流
                        });
                    });
                });
    }

    /**
     * 构建上下文: 分别返回 纯净的 System Prompt 和 带有历史记录的用户输入
     * 只有这样分类，才能激活 vLLM 大模型的 Prefix Caching (前缀缓存) 机制
     * @return String[2] -> [0] Pure System Prompt, [1] User Message With History
     */
    private String[] buildContext(String userId, String currentMessage) {
        // 查redis
        UserAIProfile profile = (UserAIProfile) redisTemplate.opsForValue().get(PROFILE_CACHE_KEY + userId);

        // 查MySQL
        if (profile == null) {
            profile = userAIProfileMapper.selectByUserId(userId);
            if (profile != null) {
                redisTemplate.opsForValue().set(PROFILE_CACHE_KEY + userId,
                        profile, EXPIRE_TIME, TimeUnit.SECONDS);
            }
        }

        // 1. 组装纯净版人设 (System Prefix) - 必须确保多次调用无任何变化！
        String pureSystemPrompt = profile != null ? methods.buildSystemPrompt(profile).toString() : "You are a helpful AI assistant.";

        // 2. 将 VectorStore(长期记忆 RAG) 插入 (查询含有跟当次输入相关的回忆)
        List<String> longTermMemories = vectorStoreService.searchSimilarMemories(userId, currentMessage, 3);
        
        StringBuilder userSideContext = new StringBuilder();
        
        if (longTermMemories != null && !longTermMemories.isEmpty()) {
            userSideContext.append("<LongTerm_Memories>\n");
            for (String m : longTermMemories) {
                userSideContext.append(m).append("\n");
            }
            userSideContext.append("</LongTerm_Memories>\n\n");
        }

        // 3. 查redis获取历史对话记录 (短记忆)
        List<Object> recentHistoryObj = redisTemplate.opsForList()
                .range(HISTORY_CACHE_KEY + userId, 0, 9);
        if (recentHistoryObj != null && !recentHistoryObj.isEmpty()) {
            userSideContext.append("<Chat_History>\n");
            // 将从 Redis 获取的不可变/特殊 List 包装为可修改的 ArrayList
            List<Object> mutableHistory = new ArrayList<>(recentHistoryObj);
            Collections.reverse(mutableHistory); // 时间顺序翻转
            for (Object h : mutableHistory) {
                if (h != null) userSideContext.append(h.toString()).append("\n");
            }
            userSideContext.append("</Chat_History>\n\n");
        }
        
        // 最后附加当次用户的输入
        userSideContext.append("Current User Query: ").append(currentMessage);

        return new String[]{pureSystemPrompt, userSideContext.toString()};
    }

    // 异步保存短期记忆
    @Async
    public void saveShortTermMemory(String userId, String msg) {
        String key = HISTORY_CACHE_KEY + userId;
        
        // 采用 Lua 脚本执行原子性：插入同时裁剪列表
        // 注意: redisTemplate 使用 JdkSerializationRedisSerializer 时，ARGV 参数会被序列化为 Java 字节流
        // Lua 脚本收到的不是纯字符串，会触发 "arguments must be strings or integers" 错误
        // 解决方案：使用 StringRedisTemplate (所有键值均为纯字符串) 或用纯字符串序列化
        DefaultRedisScript<Long> redisScript = new DefaultRedisScript<>();
        redisScript.setScriptText(LUA_SCRIPT);
        redisScript.setResultType(Long.class);

        try {
            // 使用 StringRedisTemplate 序列化行为执行 Lua 脚本
            // redisTemplate 是 RedisTemplate<String, Object> —— 值是 Object 序列化 (非纯字符串)
            // 改为直接使用 opsForList + expire 实现同样效果，避免 Lua 序列化冲突
            redisTemplate.opsForList().rightPush(key, msg);
            redisTemplate.opsForList().trim(key, -50, -1);
            redisTemplate.expire(key, EXPIRE_TIME, TimeUnit.SECONDS);
        } catch (Exception e) {
            log.error("Failed to save short-term memory to Redis", e);
        }
    }
}
