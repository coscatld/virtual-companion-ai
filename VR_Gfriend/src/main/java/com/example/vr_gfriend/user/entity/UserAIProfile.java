package com.example.vr_gfriend.user.entity;

import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@TableName("user_ai_profile")
public class UserAIProfile {

    private Long id;
    private String userId;

    private String aiName;// 名字
    private String personalityTags;//性格
    private String interests;//兴趣
    private String systemPrompt;// 给 LangChain 的提示词
    private Integer aiAffinityScore;//亲密度
    private Integer activeLevel;//活跃度
    private LocalDateTime updatedAt;
    //todo：AI多模态升级
    private String avatarUrl;//外貌
    private String voiceId;//音色
}

