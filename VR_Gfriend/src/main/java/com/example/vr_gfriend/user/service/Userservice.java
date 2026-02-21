package com.example.vr_gfriend.user.service;

import com.example.vr_gfriend.user.DTO.*;

import java.util.List;

public interface Userservice {
    String registerUser(Register_Step1 user);
    String loginUser(LoginDTO dto);
    boolean updateUserProfile(String userId, Register_step2 dto);
    List<AITemplate> getTemplateList() throws Exception;
    boolean applyTemplate(String userId, TemplateSelectDTO dto) throws Exception;
    boolean createCustomProfile(String userId, CustomCreateDTO dto) throws Exception;
}
