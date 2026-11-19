package com.example.vr_gfriend.user.service;

import com.example.vr_gfriend.common.Interceptor.JwtUtils;
import com.example.vr_gfriend.user.DTO.*;
import com.example.vr_gfriend.user.entity.User;
import com.example.vr_gfriend.user.entity.UserAIProfile;
import com.example.vr_gfriend.user.mapper.UserAIProfileMapper;
import com.example.vr_gfriend.user.mapper.UserMapper;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.core.io.ClassPathResource;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.http.HttpStatus;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.List;
import java.util.UUID;
import java.util.regex.Pattern;

@Service
@RequiredArgsConstructor
public class UserserviceImpl implements Userservice {
    private static final Pattern BCRYPT = Pattern.compile("^\\$2[aby]\\$\\d{2}\\$[./A-Za-z0-9]{53}$");
    private final UserMapper userMapper;
    private final UserAIProfileMapper aiProfileMapper;
    private final ObjectMapper objectMapper;
    private final JwtUtils jwtUtils;
    private final BCryptPasswordEncoder passwords = new BCryptPasswordEncoder();

    @Override
    @Transactional
    public String registerUser(Register_Step1 dto) {
        User user = new User();
        user.setUserId(UUID.randomUUID().toString().replace("-", ""));
        user.setEmail(present(dto.getEmail()) ? dto.getEmail() : null);
        user.setPhone(present(dto.getPhone()) ? dto.getPhone() : null);
        user.setPasswordHash(passwords.encode(dto.getPassword()));
        user.setRegisterType(user.getEmail() == null ? 1 : 0);
        user.setRegisterStage(0);
        user.setStatus(1);
        try {
            userMapper.insertBaseUser(user);
        } catch (DuplicateKeyException e) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "此邮箱或手机号已注册");
        }
        return user.getUserId();
    }

    @Override
    public String loginUser(LoginDTO dto) {
        User user = present(dto.getEmail())
                ? userMapper.selectByEmail(dto.getEmail()) : userMapper.selectByPhone(dto.getPhone());
        if (user == null || !Integer.valueOf(1).equals(user.getStatus())) {
            return null;
        }
        String storedPassword = user.getPasswordHash();
        if (BCRYPT.matcher(storedPassword).matches()) {
            if (!passwords.matches(dto.getPassword(), storedPassword)) {
                return null;
            }
        } else {
            if (!MessageDigest.isEqual(storedPassword.getBytes(StandardCharsets.UTF_8),
                    dto.getPassword().getBytes(StandardCharsets.UTF_8))) {
                return null;
            }
            userMapper.upgradePassword(user.getUserId(), storedPassword, passwords.encode(dto.getPassword()));
        }
        return jwtUtils.createToken(user.getUserId());
    }

    @Override
    @Transactional
    public boolean updateUserProfile(String userId, Register_step2 dto) {
        User user = new User();
        user.setUserId(userId);
        user.setUsername(dto.getUsername());
        user.setNickname(dto.getNickname());
        user.setGender(dto.getGender());
        user.setBirthday(dto.getBirthday());
        user.setAvatarUrl(dto.getAvatarUrl());
        return userMapper.updateUserProfile(user) > 0;
    }

    @Override
    public List<AITemplate> getTemplateList() throws IOException {
        try (InputStream input = new ClassPathResource("templates/ai_templates.json").getInputStream()) {
            return objectMapper.readValue(input, new TypeReference<List<AITemplate>>() {});
        }
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean applyTemplate(String userId, TemplateSelectDTO dto) throws IOException {
        AITemplate template = getTemplateList().stream()
                .filter(item -> item.getTemplateId().equals(dto.getTemplateId()))
                .findFirst()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "模板不存在"));
        String name = present(dto.getAiName()) ? dto.getAiName() : template.getName();
        return createCompanion(userId, name, template.getTags(), template.getInterests(),
                template.getInitPrompt().replace("{name}", name));
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public boolean createCustomProfile(String userId, CustomCreateDTO dto) throws IOException {
        String prompt = "你是一个虚拟伴侣，名字叫" + dto.getAiName() + "。";
        if (dto.getPersonalityTags() != null && !dto.getPersonalityTags().isEmpty()) {
            prompt += "你的性格关键词是：" + String.join("、", dto.getPersonalityTags()) + "。";
        }
        if (dto.getInterests() != null && !dto.getInterests().isEmpty()) {
            prompt += "你的兴趣是：" + String.join("、", dto.getInterests()) + "。";
        }
        if (present(dto.getDescription())) {
            prompt += "详细设定：" + dto.getDescription() + "。";
        }
        return createCompanion(userId, dto.getAiName(), dto.getPersonalityTags(), dto.getInterests(),
                prompt + "请根据以上设定与用户进行自然对话。");
    }

    private boolean createCompanion(String userId, String name, List<String> tags,
                                    Object interests, String prompt) throws IOException {
        if (aiProfileMapper.selectByUserId(userId) != null || userMapper.advanceToCompanionStage(userId) != 1) {
            throw new ResponseStatusException(HttpStatus.CONFLICT, "请先完善个人资料，或使用已有伴侣");
        }
        UserAIProfile profile = new UserAIProfile();
        profile.setUserId(userId);
        profile.setAiName(name);
        profile.setPersonalityTags(objectMapper.writeValueAsString(tags));
        profile.setInterests(objectMapper.writeValueAsString(interests));
        profile.setSystemPrompt(prompt);
        profile.setAiAffinityScore(0);
        if (aiProfileMapper.insert(profile) != 1) {
            throw new IllegalStateException("伴侣资料未保存");
        }
        return true;
    }

    private static boolean present(String value) {
        return value != null && !value.isBlank();
    }
}
