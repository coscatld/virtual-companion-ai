package com.example.vr_gfriend.common.Interceptor;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.SignatureAlgorithm;
import org.springframework.stereotype.Component;

import java.util.Date;

@Component
public class JwtUtils {
    private static final String SIGN_KEY = "YourSecretKeyForSigningTokensMakeItLongEnough"; // 密钥
    private static final Long EXPIRE_TIME = 43200000L; // 有效期 12 小时

    // 生成 Token
    public String createToken(String userId) {
        return Jwts.builder()
                .setSubject("USER_INFO")
                .claim("userId", userId) // 把 userId 存入载荷
                .setExpiration(new Date(System.currentTimeMillis() + EXPIRE_TIME))
                .signWith(SignatureAlgorithm.HS256, SIGN_KEY)
                .compact();
    }

    // 解析 Token 获取 userId
    public String getUserIdFromToken(String token) {
        Claims claims = Jwts.parser()
                .setSigningKey(SIGN_KEY)
                .parseClaimsJws(token)
                .getBody();
        return claims.get("userId", String.class);
    }
}

