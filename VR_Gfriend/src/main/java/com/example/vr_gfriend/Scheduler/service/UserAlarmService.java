package com.example.vr_gfriend.Scheduler.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.example.vr_gfriend.Scheduler.DTO.UserAlarmProfileDTO;
import com.example.vr_gfriend.Scheduler.entity.UserAlarmProfileEntity;
import com.example.vr_gfriend.Scheduler.mapper.UserAlarmMapper;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * 存入闹钟服务
 */
@Service
public class UserAlarmService {

    @Autowired
    private UserAlarmMapper userAlarmMapper; // MyBatis-Plus Mapper

    @Autowired
    private DynamicTaskService dynamicTaskService;

    /**
     * 核心事务方法：保存配置并刷新定时器
     */
    @Transactional(rollbackFor = Exception.class)
    public void saveAndSchedule(UserAlarmProfileDTO dto) {
        // 1. DTO 转 Entity
        UserAlarmProfileEntity entity = new UserAlarmProfileEntity();
        BeanUtils.copyProperties(dto, entity);

        // 2. 数据库操作：查询该用户是否已存在配置
        QueryWrapper<UserAlarmProfileEntity> query = new QueryWrapper<>();
        query.eq("user_id", entity.getUserId());
        UserAlarmProfileEntity oldEntity = userAlarmMapper.selectOne(query);

        if (oldEntity != null) {
            // 更新
            entity.setId(oldEntity.getId());
            userAlarmMapper.updateById(entity);
        } else {
            // 新增
            userAlarmMapper.insert(entity);
        }

        // 3. 数据库落盘成功后，更新内存中的定时任务
        dynamicTaskService.updateTask(dto);
    }
}
