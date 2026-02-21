package com.example.vr_gfriend.common.Interceptor;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

@Component
@RequiredArgsConstructor
public class JwtInterceptor implements HandlerInterceptor {

    private final JwtUtils jwtUtils;

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        // 1. 从 Header 获取 Token
        String token = request.getHeader("Authorization");

        // 2. 判定并解析
        if (token != null && !token.isEmpty()) {
            try {
                // 如果解析失败（过期或伪造），这里会抛出异常
                String userId = jwtUtils.getUserIdFromToken(token);

                // 3. 存入 ThreadLocal 供后续业务使用
                UserContext.setUserId(userId);
                return true;
            } catch (Exception e) {
                // Token 无效
                response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                return false;
            }
        }

        // 4. 无 Token 访问受限接口
        response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        return false;
    }

    @Override
    public void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) {
        // 必须清理，否则在线程池环境下会引起内存泄漏或数据污染
        UserContext.remove();
    }
}
