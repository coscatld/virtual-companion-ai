package com.example.vr_gfriend.rsocket;

import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;

import java.time.Duration;

@RestController
@RequestMapping("/api")
@CrossOrigin // 允许 Vue 跨域
public class ChatController {

    @Autowired
    private AgentClientService agentClientService;

    @PostConstruct
    public void init() {
        System.out.println("🔥 ChatController (gRPC Edition) 已加载");
    }

    // 访问地址：http://localhost:8080/api/chat/stream?msg=你好
    @GetMapping(value = "/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE + ";charset=UTF-8")
    public Flux<ServerSentEvent<String>> chat(@RequestParam String msg) {
        System.out.println("🔥 [Controller] 收到前端请求: " + msg);
        
        return agentClientService.streamChat(msg)
                // 每次收到后端的一个字，就打包成 SSE 给前端
                .map(response -> {
                    System.out.println("✅ [gRPC] Python 回复: " + response.getDelta());
                    
                    // 如果 Python 发送了结束标记，我们也可以附加特殊标记
                    String payload = response.getDelta();
                    if (response.getIsEnd()) {
                        payload += "\n[END]";
                    }
                    
                    return ServerSentEvent.builder(payload)
                            .id(String.valueOf(System.currentTimeMillis()))
                            .event("message")
                            .build();
                })
                // 如果超过20秒没有任何字吐出来，直接掐断流
                .timeout(Duration.ofSeconds(20))
                .onErrorResume(e -> Flux.just(
                        ServerSentEvent.builder("后端 AI 服务超时或发生异常，请稍后再试。")
                                .event("error")
                                .build()
                ));
    }
}
