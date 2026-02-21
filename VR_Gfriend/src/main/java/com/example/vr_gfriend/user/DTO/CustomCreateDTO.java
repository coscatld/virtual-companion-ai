package com.example.vr_gfriend.user.DTO;

import jakarta.validation.constraints.NotBlank;
import lombok.Data;

import java.util.List;

// 2. 自定义创建 DTO (当用户觉得模板不好时使用)
@Data
public class CustomCreateDTO {
    @NotBlank(message = "AI昵称不能为空")
    private String aiName;

    private List<String> personalityTags; // 前端传数组 ["高冷", "毒舌"]
    private List<String> interests;       // ["编程", "游戏"]

    // 用户可以直接写一段描述，或者由后端根据标签生成
    private String description;
}
