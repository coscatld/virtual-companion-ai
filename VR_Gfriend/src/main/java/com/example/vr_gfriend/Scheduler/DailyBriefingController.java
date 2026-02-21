package com.example.vr_gfriend.Scheduler;

import com.example.vr_gfriend.Scheduler.DTO.UserAlarmProfileDTO;
import com.example.vr_gfriend.Scheduler.service.DailyBriefingService;
import com.example.vr_gfriend.Scheduler.service.DynamicTaskService;
import com.example.vr_gfriend.Scheduler.service.UserAlarmService;
import com.example.vr_gfriend.common.Interceptor.UserContext;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import reactor.core.publisher.Flux;

@RestController
@RequestMapping("/api/briefing")
public class DailyBriefingController {
    @Autowired
    private DynamicTaskService dynamicTaskService;
    @Autowired
    private DailyBriefingService dailyBriefingService;
    @Autowired
    private UserAlarmService userAlarmService;

    /**
     * 前端提交设置表单
     * JSON: { "userId": "u1", "city": "Beijing", "time": "08:30", "filePath": "/tmp/work.txt" }
     */
    @PostMapping("/set")
    public String setAlarm(@RequestBody UserAlarmProfileDTO dto) {
        String userId = UserContext.getUserId();
        dto.setUserId(userId);
        //将 "08:30" turn to Cron表达式("0 30 8 * * ?")
        if (dto.getCronExpression() == null || !dto.getCronExpression().contains(" ")) {
            dto.setCronExpression(convertToCron(dto.getCronExpression()));
        }
        userAlarmService.saveAndSchedule(dto);
        return "设置成功！闹钟将在指定时间触发，并读取文件：" + dto.getScheduleFilePath();
    }
    /**
     * 手动触发测试 (直接返回流数据)
     */
    @GetMapping("/test/{userId}")
    public Flux<String> testBriefing(@PathVariable String userId) {
        return dailyBriefingService.generateDailyBriefing(userId);
    }

    // 简单的转换工具: "08:30" -> "0 30 8 * * ?"
    private String convertToCron(String time) {
        if (time == null || !time.contains(":")) {
            // 默认 早上8点
            return "0 0 8 * * ?";
        }
        String[] parts = time.split(":");
        int hour = Integer.parseInt(parts[0]);
        int minute = Integer.parseInt(parts[1]);
        return String.format("0 %d %d * * ?", minute, hour);
    }
}
