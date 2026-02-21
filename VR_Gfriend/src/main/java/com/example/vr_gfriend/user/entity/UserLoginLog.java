package com.example.vr_gfriend.user.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import java.time.LocalDateTime;

@TableName("user_login_log")
public class UserLoginLog {

    private Long id;
    private String userId;

    private LocalDateTime loginTime;
    private String loginIp;
    private String deviceInfo;
}

