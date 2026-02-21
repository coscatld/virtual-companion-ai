package com.example.vr_gfriend.Scheduler.service;

import com.example.vr_gfriend.Scheduler.DTO.UserAlarmProfileDTO;
import org.springframework.scheduling.TaskScheduler;
import org.springframework.scheduling.support.CronTrigger;
import org.springframework.stereotype.Service;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ScheduledFuture;

/**
 * 内存操作-管理 TaskScheduler
 */
@Service
public class DynamicTaskService {

    private final TaskScheduler taskScheduler;
    private final DailyBriefingService dailyBriefingService;

    // 内存中缓存正在运行的任务，以便可以取消/更新
    private final Map<String, ScheduledFuture<?>> scheduledTasks = new ConcurrentHashMap<>();

    public DynamicTaskService(TaskScheduler taskScheduler, DailyBriefingService dailyBriefingService) {
        this.taskScheduler = taskScheduler;
        this.dailyBriefingService = dailyBriefingService;
    }

    /**
     * 更新或新增用户的定时任务
     */
    public void updateTask(UserAlarmProfileDTO dto) {
        String userId = dto.getUserId();

        // 1. 无论如何，先取消旧任务（防止重复）
        ScheduledFuture<?> oldTask = scheduledTasks.get(userId);
        if (oldTask != null) {
            oldTask.cancel(false);
            scheduledTasks.remove(userId);
        }

        // 2. 如果用户关闭了闹钟，直接返回
        if (!dto.isEnabled()) {
            System.out.println("⏹ 用户 " + userId + " 的闹钟已禁用");
            return;
        }

        // 3. 注册新任务
        try {
            ScheduledFuture<?> future = taskScheduler.schedule(
                    () -> {
                        // === ⏰ 触发时刻：调用执行逻辑 ===
                        // 关键点：这里直接把 config 传过去，里面包含了 userId 和 filePath
                        dailyBriefingService.triggerCustomBriefing(dto);
                    },
                    new CronTrigger(dto.getCronExpression())
            );

            scheduledTasks.put(userId, future);
            System.out.println("✅ 用户 " + userId + " 的定时任务已启动: " + dto.getCronExpression());

        } catch (IllegalArgumentException e) {
            System.err.println("❌ Cron 格式错误: " + dto.getCronExpression());
        }
    }
}
