package com.example.vr_gfriend.user.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.vr_gfriend.user.entity.User;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface UserMapper extends BaseMapper<User> {
    int insertBaseUser(User user);
    int updateUserProfile(User user);
    User selectByUserId(String userId);
    User selectByEmail(String email);
    User selectByPhone(String phone);
}
