package com.example.vr_gfriend.Scheduler.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.example.vr_gfriend.Scheduler.DTO.UserAlarmProfileDTO;
import com.example.vr_gfriend.Scheduler.entity.UserAlarmProfileEntity;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface UserAlarmMapper extends BaseMapper<UserAlarmProfileEntity> {
    int save(UserAlarmProfileDTO settings);
}
