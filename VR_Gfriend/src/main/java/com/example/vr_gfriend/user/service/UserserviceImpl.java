package com.example.vr_gfriend.user.service;

import com.example.vr_gfriend.common.Interceptor.JwtUtils;
import com.example.vr_gfriend.common.method.methods;
import com.example.vr_gfriend.user.DTO.*;
import com.example.vr_gfriend.user.mapper.UserAIProfileMapper;
import com.example.vr_gfriend.user.mapper.UserMapper;
import com.example.vr_gfriend.user.entity.User;
import com.example.vr_gfriend.user.entity.UserAIProfile;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.io.IOException;
import java.util.List;
import java.util.UUID;


@Service
public class UserserviceImpl implements Userservice {
    @Autowired
    private UserMapper userMapper;
    @Autowired
    private UserAIProfileMapper aiProfileMapper;
    @Autowired
    private ObjectMapper objectMapper;
    @Autowired
    private JwtUtils jwtUtils;
    @Autowired
    private methods methods;

    @Override
    @Transactional
    public String registerUser(Register_Step1 dto) {
        String userId = UUID.randomUUID().toString().replace("-", "");
        User user = new User();
        user.setUserId(userId);
        user.setEmail(dto.getEmail());
        user.setPhone(dto.getPhone());
        user.setPasswordHash(dto.getPassword());

        user.setRegisterType(dto.getEmail() != null?0:1);
        user.setRegisterStage(0);
        user.setStatus(1);
        userMapper.insertBaseUser(user);
        return userId;
    }

    @Override
    public String loginUser(LoginDTO dto) {
        User user = null;
        
        // 根据邮箱或手机号查询用户
        if (dto.getEmail() != null && !dto.getEmail().isEmpty()) {
            user = userMapper.selectByEmail(dto.getEmail());
        } else if (dto.getPhone() != null && !dto.getPhone().isEmpty()) {
            user = userMapper.selectByPhone(dto.getPhone());
        }
        
        // 验证用户是否存在
        if (user == null) {
            return null; // 用户不存在
        }
        
        // 验证密码 todo:添加BCrypt加密
        if (!user.getPasswordHash().equals(dto.getPassword())) {
            return null; // 密码错误
        }
        
        // 生成并返回 JWT token
        return jwtUtils.createToken(user.getUserId());
    }

    @Override
    @Transactional
    public boolean updateUserProfile(String userId, Register_step2 dto) {
        User currentUser = userMapper.selectByUserId(userId);

        if (currentUser != null && Integer.valueOf(1).equals(currentUser.getRegisterStage())) {
            //todo:throw new Exception("请勿重复提交画像");
            return false;
        }
        // 复制前端传来的更新字段
        User user = new User();
        user.setUserId(userId);
        user.setUsername(dto.getUsername());
        user.setNickname(dto.getNickname());
        user.setGender(dto.getGender());
        user.setBirthday(dto.getBirthday());
        user.setAvatarUrl(dto.getAvatarUrl());

        // 执行更新
        return userMapper.updateUserProfile(user) > 0;
    }

    // 读取 JSON 文件 (保持不变)
    @Override
    public List<AITemplate> getTemplateList() throws Exception {
        try {
            ClassPathResource resource = new ClassPathResource("ai_templates.json");
            return objectMapper.readValue(resource.getInputStream(),
                    new TypeReference<List<AITemplate>>() {});
        } catch (IOException e) {
            throw new Exception("模板库加载失败");
        }
    }

    // ================== 场景 1：直接应用模板 ==================
    @Override
    @Transactional
    public boolean applyTemplate(String userId, TemplateSelectDTO dto) throws Exception {
        // 1. 校验状态 (防止重复初始化)
        checkUserStage(userId);

        // 2. 从内存/JSON中找到对应的模板数据
        AITemplate tpl = getTemplateList().stream()
                .filter(t -> t.getTemplateId().equals(dto.getTemplateId()))
                .findFirst()
                .orElseThrow(() -> new Exception("模板 ID 不存在"));

        // 3. 确定 AI 名字
        String finalName = (dto.getAiName() != null && !dto.getAiName().isEmpty())
                ? dto.getAiName() : tpl.getName();

        // 4. 替换 Prompt 中的占位符
        String systemPrompt = tpl.getInitPrompt().replace("{name}", finalName);

        // 5. 存入数据库
        UserAIProfile profile = new UserAIProfile();
        profile.setUserId(userId);
        profile.setAiName(finalName);
        profile.setPersonalityTags(
                objectMapper.writeValueAsString(tpl.getTags())
        );
        profile.setInterests(
                objectMapper.writeValueAsString(tpl.getInterests())
        );
        profile.setSystemPrompt(systemPrompt);
        profile.setAiAffinityScore(0);

        aiProfileMapper.insert(profile);

        // 6. 更新用户状态
        updateUserStage(userId);
        return true;
    }

    // ================== 场景 2：自定义创建 ==================
    @Override
    @Transactional
    public boolean createCustomProfile(String userId, CustomCreateDTO dto) throws Exception {
        // 1. 校验状态
        checkUserStage(userId);

        // 2. 动态构建 System Prompt
        String builtPrompt = buildPromptFromTags(dto.getAiName(), dto.getPersonalityTags(), dto.getDescription());

        // 3. 存入数据库
        UserAIProfile profile = new UserAIProfile();
        profile.setUserId(userId);
        profile.setAiName(dto.getAiName());
        // 将 List 转为 JSON 字符串存储
        profile.setPersonalityTags(
                objectMapper.writeValueAsString(dto.getPersonalityTags())
        );
        profile.setInterests(
                objectMapper.writeValueAsString(dto.getInterests())
        );
        profile.setSystemPrompt(builtPrompt);
        profile.setAiAffinityScore(0);

        aiProfileMapper.insert(profile);

        // 4. 更新用户状态
        updateUserStage(userId);
        return true;
    }
    private void checkUserStage(String userId) throws Exception {
        User user = userMapper.selectByUserId(userId);
        if (user == null || user.getRegisterStage() != 1) {
            throw new Exception("当前状态不可初始化 AI，请检查流程");
        }
    }

    private void updateUserStage(String userId) {
        User user = new User();
        user.setUserId(userId);
        user.setRegisterStage(2); // 标记为 AI 已初始化
        userMapper.updateById(user);
    }

    //Prompt拼装
    private String buildPromptFromTags(String name, List<String> tags, String desc) {
        StringBuilder sb = new StringBuilder();
        sb.append("你是一个虚拟伴侣，名字叫").append(name).append("。");
        if (tags != null && !tags.isEmpty()) {
            sb.append("你的性格关键词是：").append(String.join("、", tags)).append("。");
        }
        if (desc != null && !desc.isEmpty()) {
            sb.append("详细设定：").append(desc);
        }
        sb.append("请根据以上设定与用户进行自然对话。");
        return sb.toString();
    }
}
