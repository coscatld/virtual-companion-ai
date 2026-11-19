package com.example.vr_gfriend.user;

import com.example.vr_gfriend.common.Interceptor.JwtUtils;
import com.example.vr_gfriend.common.Interceptor.UserContext;
import com.example.vr_gfriend.common.config.Result;
import com.example.vr_gfriend.user.DTO.*;
import com.example.vr_gfriend.user.entity.User;
import com.example.vr_gfriend.user.mapper.UserMapper;
import com.example.vr_gfriend.user.service.CompanionProfileService;
import com.example.vr_gfriend.user.service.CompanionProfileService.CompanionView;
import com.example.vr_gfriend.user.service.Userservice;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@RestController
@RequestMapping("/admin/user")
@RequiredArgsConstructor
public class Usercontroller {
    private final Userservice service;
    private final UserMapper userMapper;
    private final CompanionProfileService profiles;
    private final JwtUtils jwtUtils;

    @PostMapping("/register")
    public Result<String> register(@Valid @RequestBody Register_Step1 user) {
        return Result.success(jwtUtils.createToken(service.registerUser(user)));
    }

    @PostMapping("/complete-profile")
    public Result<String> completeProfile(@Valid @RequestBody Register_step2 dto) {
        if (!service.updateUserProfile(UserContext.getUserId(), dto)) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "个人资料已完成或账号不可用");
        }
        return Result.success("个人资料已保存");
    }

    @PostMapping("/login")
    public Result<String> login(@RequestBody @Valid LoginDTO dto) {
        String token = service.loginUser(dto);
        if (token == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "账号或密码错误");
        }
        return Result.success(token);
    }

    @GetMapping("/me")
    public Result<UserView> currentUser() {
        String userId = UserContext.getUserId();
        User user = userMapper.selectByUserId(userId);
        if (user == null || !Integer.valueOf(1).equals(user.getStatus())) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "账号不可用");
        }
        int stage = profiles.findProfile(userId) == null ? user.getRegisterStage() : 2;
        return Result.success(new UserView(stage, user.getUsername(), user.getNickname()));
    }

    @GetMapping("/companion")
    public Result<CompanionView> companion() {
        return Result.success(profiles.publicProfile(UserContext.getUserId()));
    }

    @GetMapping("/templates")
    public Result<List<AITemplate>> getTemplates() throws Exception {
        return Result.success(service.getTemplateList());
    }

    @PostMapping("/use-template")
    public Result<String> useTemplate(@RequestBody @Valid TemplateSelectDTO dto) throws Exception {
        service.applyTemplate(UserContext.getUserId(), dto);
        return Result.success("模板应用成功");
    }

    @PostMapping("/customize")
    public Result<String> customizeAI(@RequestBody @Valid CustomCreateDTO dto) throws Exception {
        service.createCustomProfile(UserContext.getUserId(), dto);
        return Result.success("专属 AI 创建成功");
    }

    public record UserView(int registerStage, String username, String nickname) {}
}
