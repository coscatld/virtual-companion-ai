package com.example.vr_gfriend.user;

import com.example.vr_gfriend.common.Interceptor.UserContext;
import com.example.vr_gfriend.user.entity.User;
import com.example.vr_gfriend.user.mapper.UserMapper;
import com.example.vr_gfriend.user.service.CompanionProfileService;
import com.example.vr_gfriend.user.service.CompanionProfileService.InternalCompanion;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

@RestController
public class InternalCompanionController {
    private final CompanionProfileService profiles;
    private final UserMapper users;
    private final byte[] internalToken;

    public InternalCompanionController(CompanionProfileService profiles, UserMapper users,
                                       @Value("${ga.internal-token}") String internalToken) {
        this.profiles = profiles;
        this.users = users;
        this.internalToken = internalToken.getBytes(StandardCharsets.UTF_8);
    }

    @GetMapping("/internal/mobile/companion")
    public InternalCompanion companion(@RequestHeader(name = "X-GA-Internal-Token", required = false) String supplied) {
        if (internalToken.length == 0 || supplied == null ||
                !MessageDigest.isEqual(internalToken, supplied.getBytes(StandardCharsets.UTF_8))) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "服务凭据无效");
        }
        String userId = UserContext.getUserId();
        User user = users.selectByUserId(userId);
        if (user == null || !Integer.valueOf(1).equals(user.getStatus())) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "账号不可用");
        }
        return profiles.internalCompanion(userId);
    }
}
