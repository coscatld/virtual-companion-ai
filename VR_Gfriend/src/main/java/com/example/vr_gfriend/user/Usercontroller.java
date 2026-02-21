package com.example.vr_gfriend.user;

import com.example.vr_gfriend.common.Interceptor.UserContext;
import com.example.vr_gfriend.common.Interceptor.JwtUtils;
import com.example.vr_gfriend.common.config.Result;
import com.example.vr_gfriend.user.DTO.*;
import com.example.vr_gfriend.user.service.Userservice;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Qualifier;
import org.springframework.web.bind.annotation.*;

import java.util.List;


@RestController
@RequestMapping("/admin/user")
@RequiredArgsConstructor
public class Usercontroller {
    @Autowired
    @Qualifier("userserviceImpl")
    private Userservice service;
    private final JwtUtils jwtUtils;
    /**
     * 1. 获取注册列表
     * 前端调用此接口开始注册
     */
    @PostMapping("/register")
    public Result register(@Valid @RequestBody Register_Step1 user) {
        String userId = service.registerUser(user);
        String token  = jwtUtils.createToken(userId);
        //将令牌返回给前端（前端存入localStorage）
        return Result.success(token);
    }
    /**
     * 2. 获取用户画像
     * 前端注册后，stage=0，开始填写画像
     */
    @PostMapping("/complete-profile")
    public Result completeProfile(@Valid @RequestBody Register_step2 dto) {
        String userId = UserContext.getUserId();//拦截器
        boolean s = service.updateUserProfile(userId, dto);
        return s ? Result.success("画像填写完成，欢迎进入 AI 世界！") : Result.error("更新失败");
    }
    
    /**
     * 3. 用户登录
     * 支持邮箱或手机号登录
     */
    @PostMapping("/login")
    public Result login(@RequestBody @Valid LoginDTO dto) {
        String token = service.loginUser(dto);
        return token != null ? Result.success(token) : Result.error("登录失败，用户名或密码错误");
    }
    /**
     * 4. 获取模板列表
     * 前端调用此接口渲染“卡片墙”
     */
    @GetMapping("/templates")
    public Result<List<AITemplate>> getTemplates() throws Exception {
        return Result.success(service.getTemplateList());
    }
    /**
     * 5. 快捷应用模板 (Direct Load)
     * 用户在前端点击某个模板的“立即使用”按钮时调用
     */
    @PostMapping("/use-template")
    public Result useTemplate(@RequestBody @Valid TemplateSelectDTO dto) throws Exception {
        String userId = UserContext.getUserId();
        boolean success = service.applyTemplate(userId, dto);
        return success ? Result.success("模板应用成功，AI 已就绪") : Result.error("应用失败");
    }
    /**
     * 6. 自定义 AI (Custom Build)
     * 用户觉得模板不好，手动填写性格、标签后调用
     */
    @PostMapping("/customize")
    public Result customizeAI(@RequestBody @Valid CustomCreateDTO dto) throws Exception {
        String userId = UserContext.getUserId();
        boolean success = service.createCustomProfile(userId, dto);
        return success ? Result.success("专属 AI 创建成功") : Result.error("创建失败");
    }
}
