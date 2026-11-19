package com.example.vr_gfriend.common.Interceptor;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtParser;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.Key;
import java.time.Duration;
import java.time.Instant;
import java.util.Date;

@Component
public class JwtUtils {
    private static final String SUBJECT = "USER_INFO";
    private final Key signingKey;
    private final JwtParser parser;

    public JwtUtils(@Value("${ga.auth.jwt-secret}") String secret) {
        signingKey = secret.isBlank()
                ? Keys.secretKeyFor(SignatureAlgorithm.HS256)
                : Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
        parser = Jwts.parserBuilder().setSigningKey(signingKey).requireSubject(SUBJECT).build();
    }

    public String createToken(String userId) {
        Instant now = Instant.now();
        return Jwts.builder()
                .setSubject(SUBJECT)
                .claim("userId", userId)
                .setIssuedAt(Date.from(now))
                .setExpiration(Date.from(now.plus(Duration.ofHours(12))))
                .signWith(signingKey, SignatureAlgorithm.HS256)
                .compact();
    }

    public String getUserIdFromToken(String token) {
        Claims claims = parser.parseClaimsJws(token).getBody();
        String userId = claims.get("userId", String.class);
        if (userId == null || userId.isBlank() || claims.getExpiration() == null) {
            throw new IllegalArgumentException("令牌缺少身份或有效期");
        }
        return userId;
    }

    public String getUserIdFromAuthorization(String authorization) {
        if (authorization == null || authorization.isBlank()) {
            throw new IllegalArgumentException("令牌不能为空");
        }
        String token = authorization.strip();
        if (token.regionMatches(true, 0, "Bearer ", 0, "Bearer ".length())) {
            token = token.substring("Bearer ".length()).strip();
        }
        return getUserIdFromToken(token);
    }
}
