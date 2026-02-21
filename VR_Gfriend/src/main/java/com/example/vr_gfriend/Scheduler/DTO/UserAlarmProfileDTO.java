package com.example.vr_gfriend.Scheduler.DTO;

import lombok.Data;

@Data
public class UserAlarmProfileDTO {
    private String userId;
    private String city;          // 用户填写的城市
    private String cronExpression;// 用户填写的提醒时间 (前端转为 Cron，如 "0 30 7 * * ?")
    private String scheduleFilePath; // 用户上传或指定的授权文件路径
    private boolean enabled;      // 开关
}
