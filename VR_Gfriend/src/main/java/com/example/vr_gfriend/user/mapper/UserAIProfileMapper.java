package com.example.vr_gfriend.user.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.vr_gfriend.user.entity.UserAIProfile;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;


@Mapper
public interface UserAIProfileMapper extends BaseMapper<UserAIProfile> {
    UserAIProfile selectByUserId(@Param("userId")String userId);
}