package com.example.vr_gfriend.Scheduler.service;

import com.baomidou.mybatisplus.core.conditions.query.QueryWrapper;
import com.example.vr_gfriend.Scheduler.DTO.UserAlarmProfileDTO;
import com.example.vr_gfriend.Scheduler.entity.UserAlarmProfileEntity;
import com.example.vr_gfriend.Scheduler.mapper.UserAlarmMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.BeanUtils;
import org.springframework.boot.context.event.ApplicationReadyEvent;
import org.springframework.context.event.EventListener;
import org.springframework.http.HttpStatus;
import org.springframework.scheduling.support.CronExpression;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.Locale;

@Slf4j
@Service
@RequiredArgsConstructor
public class UserAlarmService {
    private final UserAlarmMapper mapper;
    private final DynamicTaskService tasks;

    public synchronized void saveAndSchedule(UserAlarmProfileDTO dto) {
        try {
            dto.setCronExpression(toCron(dto.getCronExpression()));
            CronExpression cron = CronExpression.parse(dto.getCronExpression());
            if (dto.isEnabled() && cron.next(LocalDateTime.now()) == null) {
                throw new IllegalArgumentException("No future trigger");
            }
        } catch (RuntimeException error) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "请输入有效时间（HH:mm）或 Cron 表达式");
        }
        mapper.save(dto);
        tasks.updateTask(dto);
    }

    public UserAlarmProfileDTO findSettings(String userId) {
        var entity = mapper.selectOne(new QueryWrapper<UserAlarmProfileEntity>().eq("user_id", userId));
        return entity == null ? null : toSettings(entity);
    }

    @EventListener(ApplicationReadyEvent.class)
    public synchronized void restoreScheduledTasks() {
        for (var entity : mapper.selectList(new QueryWrapper<UserAlarmProfileEntity>().eq("enabled", true))) {
            try {
                tasks.updateTask(toSettings(entity));
            } catch (IllegalArgumentException error) {
                log.warn("Unable to restore an invalid briefing schedule", error);
            }
        }
    }

    private static String toCron(String input) {
        if (input == null || input.isBlank()) {
            return "0 0 8 * * ?";
        }
        String value = input.strip();
        if (!value.matches("[0-9]{2}:[0-9]{2}")) {
            return value;
        }
        LocalTime time = LocalTime.parse(value);
        return String.format(Locale.ROOT, "0 %d %d * * ?", time.getMinute(), time.getHour());
    }

    private static UserAlarmProfileDTO toSettings(UserAlarmProfileEntity entity) {
        var dto = new UserAlarmProfileDTO();
        BeanUtils.copyProperties(entity, dto);
        return dto;
    }
}
