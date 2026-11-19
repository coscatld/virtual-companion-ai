package com.example.vr_gfriend.common.Interceptor;

import io.jsonwebtoken.JwtException;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.server.ServerHttpRequest;
import org.springframework.http.server.ServerHttpResponse;
import org.springframework.http.server.ServletServerHttpRequest;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.WebSocketHandler;
import org.springframework.web.socket.server.HandshakeInterceptor;

import java.util.Arrays;
import java.util.Map;

@Component
@RequiredArgsConstructor
public class AudioHandshakeInterceptor implements HandshakeInterceptor {
    public static final String SUBPROTOCOL = "ga.jwt";
    public static final String USER_ID = "userId";
    private static final String TOKEN_PROTOCOL_PREFIX = "jwt.";
    private final JwtUtils jwtUtils;

    @Override
    public boolean beforeHandshake(ServerHttpRequest request, ServerHttpResponse response,
                                   WebSocketHandler handler, Map<String, Object> attributes) {
        String authorization = request.getHeaders().getFirst(HttpHeaders.AUTHORIZATION);
        if (authorization == null) {
            authorization = request.getHeaders().getOrEmpty("Sec-WebSocket-Protocol").stream()
                    .flatMap(header -> Arrays.stream(header.split(",")))
                    .map(String::strip)
                    .filter(protocol -> protocol.startsWith(TOKEN_PROTOCOL_PREFIX))
                    .map(protocol -> protocol.substring(TOKEN_PROTOCOL_PREFIX.length()))
                    .findFirst().orElse(null);
        }
        if (authorization == null && request.getURI().getPath().equals("/audio")
                && request instanceof ServletServerHttpRequest servletRequest) {
            authorization = servletRequest.getServletRequest().getParameter("token");
        }

        try {
            attributes.put(USER_ID, jwtUtils.getUserIdFromAuthorization(authorization));
            return true;
        } catch (JwtException | IllegalArgumentException e) {
            response.setStatusCode(HttpStatus.UNAUTHORIZED);
            return false;
        }
    }

    @Override
    public void afterHandshake(ServerHttpRequest request, ServerHttpResponse response,
                               WebSocketHandler handler, Exception exception) {
    }
}
