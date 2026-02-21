package com.example.vr_gfriend.user.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;
import java.time.LocalDate;
import java.time.LocalDateTime;

@Data
@TableName("user")
public class User {

    private Long id;
    private String userId;

    private String email;
    private String phone;
    private String passwordHash;
    private Integer registerType; //0手机，1邮箱
    private Integer registerStage;//0注册1完善资料2初始化AI
    private Integer status;//1正常

    private String username;
    private String nickname;//称号
    private String avatarUrl;//头像
    private Integer gender;//性别0男1女2其他3未知
    private LocalDate birthday;

    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
