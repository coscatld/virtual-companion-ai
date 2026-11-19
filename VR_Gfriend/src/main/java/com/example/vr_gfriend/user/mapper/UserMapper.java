package com.example.vr_gfriend.user.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.vr_gfriend.user.entity.User;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface UserMapper extends BaseMapper<User> {
    int insertBaseUser(User user);
    int updateUserProfile(User user);
    int advanceToCompanionStage(@Param("userId") String userId);
    int upgradePassword(@Param("userId") String userId, @Param("previousPassword") String previousPassword,
                        @Param("hashedPassword") String hashedPassword);
    User selectByUserId(@Param("userId") String userId);
    User selectByEmail(@Param("email") String email);
    User selectByPhone(@Param("phone") String phone);
}
